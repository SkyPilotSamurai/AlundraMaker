"""Editable, re-importable sprite sheets: one PNG per animation, frame by frame.

python tools/export_animation_sheets.py [--catalogue 0] [--map 163] [--meia] [--out DIR]

For each animation of the class you get "<anim> <name>.png":
* one row per direction slot (0-3, as the game numbers them), frames left to
  right in play order; a direction the animation does not have is left out;
* every cell in a file is the same size and the sprite's origin (the point the
  game positions) is at the same spot in every cell, so frames line up;
* cells are separated by a 2-pixel grey gutter; the dark strip on the left names
  the direction and the strip on top numbers the frames. Only pixels inside the
  cells count; leave the gutters and strips as they are;
* empty pixels are transparent; "T" in the top strip marks a frame the game
  draws rotated/scaled: shown as the game draws it, but not importable yet.
The same picture (image set) can appear in several cells and animations; an
importer uses one edited copy per image set (see the manifest's "image_set").
manifest.json lists every file, cell rectangle, origin and image set.
--meia exports the frames as Start as Meia builds them. Output comes from the
game's data: keep it under game/, never commit it.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUTTER, LEFT, TOP, PAD = 2, 52, 14, 4
GUTTER_COLOUR = (90, 96, 108, 255); STRIP_COLOUR = (28, 32, 40, 255)


def export(session, map_id=163, catalogue=0, out=None):
    from PIL import Image, ImageDraw
    from animation_preview import available_animations, load_animation, animation_reader
    from entity_preview import is_transformed
    import struct
    preview, _ = animation_reader(session, map_id, catalogue)
    table = preview.header[3]
    record = preview.start + struct.unpack_from('<i', session.data, preview.start + table + (catalogue & 255) * 4)[0]
    frames_base = preview.start + struct.unpack_from('<4I', session.data, record)[3]

    def rotated(iset):
        pos = frames_base + iset * 2
        return is_transformed(session.data, pos, session.data[pos + 1])
    from player_attacks import PLAYER_ANIMATIONS, words
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    manifest = dict(format='alundra-editor-animation-sheets-v1', catalogue_index=catalogue, map_id=map_id,
                    gutter=GUTTER, files=[])
    for a in available_animations(session, map_id, catalogue):
        drawn_sheet = render_animation(session, map_id, catalogue, a, rotated)
        if drawn_sheet is None:
            continue
        sheet, filename, entry = drawn_sheet
        sheet.save(out / filename)
        manifest['files'].append(entry)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')
    return out, len(manifest['files']), sum(len(f['cells']) for f in manifest['files'])


def rotated_test(session, map_id, catalogue):
    """function(image set) -> True when the game draws that picture rotated/scaled."""
    import struct
    from animation_preview import animation_reader
    from entity_preview import is_transformed
    preview, _ = animation_reader(session, map_id, catalogue)
    table = preview.header[3]
    record = preview.start + struct.unpack_from('<i', session.data, preview.start + table + (catalogue & 255) * 4)[0]
    frames_base = preview.start + struct.unpack_from('<4I', session.data, record)[3]
    return lambda iset: is_transformed(session.data, frames_base + iset * 2, session.data[frames_base + iset * 2 + 1])


def render_animation(session, map_id, catalogue, a, rotated=None):
    """(sheet image, file name, manifest entry) for one animation (a: available_animations row), or None."""
    from PIL import Image, ImageDraw
    from animation_preview import load_animation
    from player_attacks import PLAYER_ANIMATIONS, words
    if rotated is None:
        rotated = rotated_test(session, map_id, catalogue)
    if True:
        rows = []
        for direction in range(4):
            if not a['direction_frames'][direction]:
                continue
            clip = load_animation(session, map_id, catalogue, a['index'], direction, fallback_direction=False)
            rows.append((direction, clip.frames))
        if not rows:
            return None
        drawn = [f for _, frames in rows for f in frames if f.image is not None]
        left = min([f.left for f in drawn] + [0]) - PAD; top = min([f.top for f in drawn] + [0]) - PAD
        right = max([f.left + f.image.width for f in drawn] + [1]) + PAD
        bottom = max([f.top + f.image.height for f in drawn] + [1]) + PAD
        cw, ch = right - left, bottom - top
        columns = max(len(frames) for _, frames in rows)
        width = LEFT + columns * (cw + GUTTER) + GUTTER; height = TOP + len(rows) * (ch + GUTTER) + GUTTER
        sheet = Image.new('RGBA', (width, height), GUTTER_COLOUR)
        draw = ImageDraw.Draw(sheet)
        draw.rectangle([0, 0, width - 1, TOP - 1], fill=STRIP_COLOUR); draw.rectangle([0, 0, LEFT - 1, height - 1], fill=STRIP_COLOUR)
        name = PLAYER_ANIMATIONS.get(a['index']) if catalogue == 0 else None
        label = f"{a['index']:02X}" + (f" {words(name)}" if name else '')
        filename = re.sub(r'[^A-Za-z0-9 ()_-]', '', label) + '.png'
        cells = []
        for c in range(columns):
            draw.text((LEFT + GUTTER + c * (cw + GUTTER) + 2, 1), f'{c}', fill=(200, 210, 225, 255))
        for r, (direction, frames) in enumerate(rows):
            y0 = TOP + GUTTER + r * (ch + GUTTER)
            draw.text((4, y0 + 2), f'dir {direction}', fill=(200, 210, 225, 255))
            for c, f in enumerate(frames):
                x0 = LEFT + GUTTER + c * (cw + GUTTER)
                sheet.paste((0, 0, 0, 0), (x0, y0, x0 + cw, y0 + ch))
                entry = dict(direction=direction, frame=c, image_set=f.image_set_index, cell=[x0, y0, cw, ch],
                             origin=[x0 - left, y0 - top], delay_raw=f.delay_raw,
                             transformed=f.image is None or rotated(f.image_set_index))
                if f.image is not None:
                    sheet.alpha_composite(f.image.convert('RGBA'), (x0 - left + f.left, y0 - top + f.top))
                    entry['box'] = [x0 - left + f.left, y0 - top + f.top, f.image.width, f.image.height]
                if entry['transformed']:
                    draw.text((LEFT + GUTTER + c * (cw + GUTTER) + 2 + 8 * len(str(c)), 1), 'T', fill=(255, 110, 110, 255))
                cells.append(entry)
            for c in range(len(frames), columns):   # no frame here: grey
                x0 = LEFT + GUTTER + c * (cw + GUTTER)
                sheet.paste(GUTTER_COLOUR, (x0, y0, x0 + cw, y0 + ch))
        return sheet, filename, dict(file=filename, animation=a['index'], name=name, cell_size=[cw, ch], cells=cells)


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'tools'))
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalogue', type=int, default=0)
    parser.add_argument('--map', type=int, default=163)
    parser.add_argument('--meia', action='store_true')
    parser.add_argument('--basic-attack', action='store_true', help='with --meia: Meia basic attack')
    parser.add_argument('--fallback', action='store_true', help='with --basic-attack: Alundra for missing actions')
    parser.add_argument('--out')
    args = parser.parse_args()
    from copy import copy
    from editor_session import EditSession
    session = EditSession((ROOT / 'game' / 'disc' / 'DATA' / 'DATAS.BIN').read_bytes(), None, verify=False)
    if args.meia:
        from player_costume import apply_costume
        session = copy(session); session.data = bytearray(session.data)
        apply_costume(session, basic_attack=args.basic_attack, alundra_fallback=args.basic_attack and args.fallback)
        session = EditSession(bytes(session.data), None, verify=False)
    name = ('alundra' if args.catalogue == 0 else f'class-{args.catalogue}') + ('-as-meia' if args.meia else '') + ('-basic-attack' if args.meia and args.basic_attack else '') + ('-fallback' if args.meia and args.basic_attack and args.fallback else '')
    out = args.out or ROOT / 'game' / 'sprite-sheets' / f'{name}-animations'
    folder, files, cells = export(session, args.map, args.catalogue, out)
    print(f'Wrote {files} animation sheets ({cells} frames) to {folder}')
