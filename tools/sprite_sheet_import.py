"""Per-animation sprite sheets from the Database: export, edit, import.

Export writes the same sheet layout as tools/export_animation_sheets.py for one
animation of one class (one row per direction, frames left to right, every
cell the same size with the sprite origin at the same spot). Import reads an
edited copy of that PNG: the layout is rebuilt from the same game data, every
cell is compared with the original, and each changed picture (image set) is
stored in the mod (document['sprite_imports']) as a small PNG + its position
relative to the sprite origin. Nothing changes in the editor's game data; at
build (event_export.prepare_native_event_export) the stored pictures are drawn
into the sprite bank by sprite_frame_replace.replace_image_sets:
* classes 0-255 (global): once;
* classes 256-511 (map-local): on every map that has that class's sprite.
The player (class 0) with Start as Meia on is exported/compared as the costume
builds it, and imports are applied after the costume.
Frames the game draws rotated/scaled ("T") are not imported. A picture keeps
its image set's quad count; one that does not fit is reported and left as it was.
"""
import base64
import io
import struct


def base_session(session, document, catalogue):
    """The game data a sheet is exported from / compared with."""
    from copy import copy
    if catalogue == 0 and ((document or {}).get('mod_options') or {}).get('start_as_meia'):
        from editor_session import EditSession
        from player_costume import apply_costume
        work = copy(session); work.data = bytearray(session.data)
        apply_costume(work, **costume_options(document))
        return EditSession(bytes(work.data), None, verify=False)
    return session


def costume_options(document):
    options = (document or {}).get('mod_options') or {}
    return dict(basic_attack=bool(options.get('meia_basic_attack')),
                alundra_fallback=bool(options.get('meia_alundra_fallback')))


def animation_row(session, map_id, catalogue, animation):
    from animation_preview import available_animations
    for a in available_animations(session, map_id, catalogue):
        if a['index'] == animation:
            return a
    raise ValueError(f'Animation {animation} is not in this class')


def render(session, document, map_id, catalogue, animation):
    """(sheet image, file name, manifest entry) as the game data (plus costume) draws it."""
    from export_animation_sheets import render_animation
    base = base_session(session, document, catalogue)
    drawn = render_animation(base, map_id, catalogue, animation_row(base, map_id, catalogue, animation))
    if drawn is None:
        raise ValueError('This animation has no frames')
    return drawn


def export_sheet(session, document, map_id, catalogue, animation, path):
    sheet, _, entry = render(session, document, map_id, catalogue, animation)
    sheet.save(path)
    return entry


def _png(image):
    buffer = io.BytesIO(); image.save(buffer, 'PNG')
    return base64.b64encode(buffer.getvalue()).decode('ascii')


def _image(text):
    from PIL import Image
    return Image.open(io.BytesIO(base64.b64decode(text))).convert('RGBA')


def changed_pictures(original, edited, entry):
    """{image set: (RGBA picture, left, top)} for cells that differ; plus skipped notes."""
    edited = edited.convert('RGBA'); original = original.convert('RGBA')
    if edited.size != original.size:
        raise ValueError(f'The sheet must stay {original.width}x{original.height} pixels '
                         f'(this one is {edited.width}x{edited.height})')
    out = {}; notes = []
    for cell in entry['cells']:
        x0, y0, cw, ch = cell['cell']
        box = (x0, y0, x0 + cw, y0 + ch)
        a = original.crop(box); b = edited.crop(box)
        # compare what the game would see: alpha threshold and colour of opaque pixels
        def visible(im):
            return bytes(c for p in im.getdata() for c in ((p[0], p[1], p[2], 255) if p[3] >= 128 else (0, 0, 0, 0)))
        if visible(a) == visible(b):
            continue
        if cell.get('transformed'):
            notes.append(f"direction {cell['direction']} frame {cell['frame']} is drawn rotated by the game; not imported")
            continue
        iset = cell['image_set']
        if iset in out:
            continue
        clean = b.copy(); alpha = clean.split()[3].point(lambda v: 255 if v >= 128 else 0); clean.putalpha(alpha)
        bbox = clean.getbbox() or (0, 0, 1, 1)
        ox, oy = cell['origin']
        out[iset] = (clean.crop(bbox), x0 + bbox[0] - ox, y0 + bbox[1] - oy)
    return out, notes


def import_sheet(session, document, map_id, catalogue, animation, path):
    """Store the changed pictures of an edited sheet in the mod. Returns a summary dict."""
    from PIL import Image
    sheet, _, entry = render(session, document, map_id, catalogue, animation)
    with Image.open(path) as edited:
        pictures, notes = changed_pictures(sheet, edited, entry)
    store = document.setdefault('sprite_imports', {})
    row = store.setdefault(str(catalogue), {'map_id': map_id, 'frames': {}, 'animations': []})
    for iset, (image, left, top) in pictures.items():
        row['frames'][str(iset)] = {'png': _png(image), 'left': left, 'top': top, 'animation': animation}
    if pictures and animation not in row['animations']:
        row['animations'].append(animation)
    if not row['frames']:
        store.pop(str(catalogue), None)
    return dict(changed=len(pictures), notes=notes)


def remove_import(document, catalogue, animation):
    store = (document or {}).get('sprite_imports') or {}
    row = store.get(str(catalogue))
    if not row:
        return 0
    gone = [k for k, v in row['frames'].items() if v.get('animation') == animation]
    for k in gone:
        del row['frames'][k]
    row['animations'] = [a for a in row.get('animations', []) if a != animation]
    if not row['frames']:
        store.pop(str(catalogue), None)
    return len(gone)


def imported_animations(document, catalogue):
    row = ((document or {}).get('sprite_imports') or {}).get(str(catalogue)) or {}
    return sorted(row.get('animations', []))


def class_maps_with_sprite(data, catalogue):
    from local_sprite_import import sprite_assets
    from map_block_repack import pointers
    count = len(pointers(data)) - 1
    for m in range(min(count, 2547)):
        try:
            sprite_assets(data, m, catalogue - 256)
        except Exception:
            continue
        yield m


def apply_sprite_imports(exported, document):
    """Draw every stored picture into the built game data. Returns report rows."""
    from sprite_frame_replace import replace_image_sets
    report = []
    for key, row in sorted(((document or {}).get('sprite_imports') or {}).items(), key=lambda kv: int(kv[0])):
        catalogue = int(key)
        pictures = {int(i): (_image(v['png']), int(v['left']), int(v['top'])) for i, v in row.get('frames', {}).items()}
        if not pictures:
            continue
        maps = [None] if catalogue < 256 else list(class_maps_with_sprite(exported.data, catalogue))
        for m in maps:
            try:
                data, info = replace_image_sets(exported.data, catalogue, pictures, map_id=m)
                exported.data = bytearray(data)
                report.append(dict(catalogue_index=catalogue, map_id=m, replaced=len(info['replaced']), kept=info['kept']))
            except Exception as error:
                report.append(dict(catalogue_index=catalogue, map_id=m, skipped=str(error)))
    return report
