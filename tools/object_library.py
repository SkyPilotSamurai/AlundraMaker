"""The game object library: every object, NPC, enemy and boss of the original
game, taken out of the disc data into game/object-library, so the
editor uses them without reading (or depending on) the original maps.

    python tools/object_library.py build      extract everything (resumable; run again until done)
    python tools/object_library.py status     what is there

Layout (all bytes are the original game's, unchanged):
  index.json                  source DATAS.BIN sha256, map fingerprints, every class with its
                              name, kind and behaviours (variants), and where its files are
  objects/CCC-name/object.json  one class (catalogue number CCC):
        variants: each distinct behaviour of the class in the game (behavior_transplant):
          donor map + entity index, the entity record, its six hooks, and for every map-local
          hook the copied program (as it is copied onto another map) with the references it
          makes into its home map (texts as text, effect entries as bytes, spawned templates
          with their class);
        sprite: the sprite's own asset bytes (animations, frames, collision, image sets) per
          variant map, the texture pages (pages/SHA1.bin, 32 KB each) and palettes it uses;
          global sprites (CCC < 256) point at global/sprite_bank.bin
  objects/CCC-name/preview.png  the class's picture
  pages/SHA1.bin              texture pages (shared, by content)
  global/sprite_bank.bin      the global sprite bank (header offsets in index.json)
  maps/MMM.blk.gz             every original map block, byte for byte (what the compiler copies
                              donors from); objects never need the original DATAS.BIN again
"""
import gzip, hashlib, json, re, struct, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / 'game/object-library'
FORMAT = 'alundra-object-library-v1'
STOCK_MAPS = 483


def _slug(name):
    return re.sub(r'[^A-Za-z0-9]+', '-', name or 'unnamed').strip('-')[:48] or 'unnamed'


def _sha1(raw):
    return hashlib.sha1(raw).hexdigest()


# --- reading -------------------------------------------------------------------

_index_cache = {}


def index(root=LIBRARY):
    """The library index, or None when there is no (complete) library."""
    path = root / 'index.json'
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return None
    hit = _index_cache.get(path)
    if hit and hit[0] == stamp:
        return hit[1]
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if value.get('format') != FORMAT:
        return None
    _index_cache[path] = (stamp, value)
    return value


def available(root=LIBRARY):
    ix = index(root)
    return bool(ix and ix.get('complete'))


_block_cache = {}


def map_block(m, root=LIBRARY):
    """Original map m's block from the library (bytes), or None."""
    key = (str(root), m)
    if key in _block_cache:
        return _block_cache[key]
    path = root / 'maps' / f'{m:03d}.blk.gz'
    try:
        raw = gzip.decompress(path.read_bytes())
    except OSError:
        return None
    ix = index(root)
    if ix and ix.get('map_fingerprints') and _sha1(raw) != ix['map_fingerprints'][m]:
        raise ValueError(f'Object library: map {m} is damaged (fingerprint differs)')
    if len(_block_cache) > 64:
        _block_cache.pop(next(iter(_block_cache)))
    _block_cache[key] = raw
    return raw


def original_data(root=LIBRARY):
    """The original DATAS.BIN put back together from the library (checked
    against its sha256), or None."""
    ix = index(root)
    if not ix:
        return None
    try:
        parts = [(root / 'global' / 'head.bin').read_bytes()]
    except OSError:
        return None
    for m in range(STOCK_MAPS):
        block = map_block(m, root)
        if block is None:
            return None
        parts.append(block)
    data = b''.join(parts)
    if hashlib.sha256(data).hexdigest() != ix['source_sha256']:
        return None
    return data


def object_info(catalogue, root=LIBRARY):
    ix = index(root)
    row = (ix or {}).get('objects', {}).get(str(catalogue))
    if not row:
        return None
    try:
        return json.loads((root / row['folder'] / 'object.json').read_text())
    except (OSError, ValueError):
        return None


def variants(catalogue, root=LIBRARY):
    """The class's behaviours as behavior_transplant.behaviour_variants lists them."""
    info = object_info(catalogue, root)
    if info is None:
        return None
    return [v['summary'] for v in info.get('variants', [])]


def preview(catalogue, root=LIBRARY):
    ix = index(root)
    row = (ix or {}).get('objects', {}).get(str(catalogue))
    if not row:
        return None
    path = root / row['folder'] / 'preview.png'
    if not path.exists():
        return None
    from PIL import Image
    with Image.open(path) as im:
        return im.convert('RGBA')


def refresh_previews(snapshot, root=LIBRARY, progress=print):
    """Redraw stored preview.png files with the current decoder (2026-10-22: semi-transparent
    pieces, e.g. the additive Giant Slime body, were stored opaque and too dark).
    Returns the catalogue numbers whose picture changed."""
    from PIL import ImageChops
    from database_catalogue import _reference_image_uncached
    ix = index(root) or {}; changed = []
    for key, row in ix.get('objects', {}).items():
        folder = root / row['folder']; path = folder / 'preview.png'
        if not path.exists():
            continue
        try:
            info = json.loads((folder / 'object.json').read_text())
        except (OSError, ValueError):
            continue
        maps = [v['donor_map'] for v in info.get('variants', [])] or [m for m, _ in info.get('placements', [])] or [0]
        live = {'kind': info.get('kind'), 'name': info.get('name'), 'data': {},
                'source': {'catalogue_index': int(key), 'observed_maps': maps, 'variant': 'library-refresh'}}
        try:
            image = _reference_image_uncached(snapshot, live)
        except Exception:
            continue
        if image is None:
            continue
        from PIL import Image
        with Image.open(path) as old:
            old = old.convert('RGBA')
        if old.size == image.size and not ImageChops.difference(old, image).getbbox():
            continue
        image.save(path); changed.append(int(key))
    progress(f'refreshed {len(changed)} previews')
    return changed


# --- building ------------------------------------------------------------------

def _names(stock):
    from content_database import ContentDatabase
    db = ContentDatabase()
    db.populate_catalogue(stock)
    out = {}
    for row in db.definitions:
        source = row.get('source', {})
        cat = source.get('catalogue_index')
        if type(cat) is int and not source.get('variant') and cat not in out:
            out[cat] = (row['name'], row['kind'], row)
    return out


def _placements(stock):
    from native_class_placement import record_cluster
    found = {}
    for m in range(STOCK_MAPS):
        try:
            entities = record_cluster(stock, m)['entities']
        except Exception:
            continue
        for i, raw in enumerate(entities):
            found.setdefault(raw[6] + (256 if raw[5] & 128 else 0), []).append((m, i))
    return found


def _sprite(stock, m, catalogue, pages_dir):
    """Local sprite assets of catalogue on map m: payload, pages, palettes."""
    from local_sprite_import import layout, sprite_assets
    from texture_codec import unpack_ez
    assets = sprite_assets(stock, m, catalogue - 256)
    b, h, s, e, sh = layout(stock, m)
    texture, _ = unpack_ez(stock[b + h[4]:b + h[5]], limit=262144)
    pages = {}
    for p in sorted(assets['pages']):
        chunk = bytes(texture[p * 32768:(p + 1) * 32768])
        digest = _sha1(chunk)
        path = pages_dir / f'{digest}.bin'
        if not path.exists():
            path.write_bytes(chunk)
        pages[str(p)] = digest
    palettes = {str(i): bytes(stock[s + sh[5] + 32 * i:s + sh[5] + 32 * i + 32]).hex() for i in sorted(assets['palettes'])}
    payload = bytes(stock[assets['record']:assets['end']])
    return {'map': m, 'sprite_id': catalogue - 256, 'payload_relative': assets['relative'],
            'roots': list(assets['roots']), 'payload_sha1': _sha1(payload), 'payload_hex': payload.hex(),
            'quads': [q - assets['record'] for q in assets['quads']], 'pages': pages, 'palettes': palettes}


def _variant(stock, snapshot, catalogue, summary):
    from native_class_placement import record_cluster
    from behavior_transplant import program_span, local_text, _catalogue
    m, i = summary['donor_map'], summary['entity_index']
    cluster = record_cluster(stock, m)
    raw = cluster['entities'][i]
    effects = [cluster['effects'][k:k + 12] for k in range(0, max(0, len(cluster['effects']) - 4), 12)]
    programs = {}
    for n, value in enumerate(raw[10:16]):
        if not value & 0x80:
            continue
        bank = 'ABCDEF'[n]
        try:
            code, info = program_span(stock, m, bank, value & 0x7F, snapshot)
        except ValueError as exc:
            programs[bank] = {'missing': str(exc)}
            continue
        refs = []
        for ref in info.get('map_refs', []):
            kind = ref[0]
            if kind == 'text':
                text = local_text(stock, m, ref[2])
                refs.append({'kind': 'text', 'at': ref[1], 'index': ref[2],
                             'text': text.decode('latin-1') if text is not None else None})
            elif kind in ('spawn', 'select'):
                t = ref[2]
                refs.append({'kind': kind, 'at': ref[1], 'template': t,
                             'template_class': _catalogue(cluster['entities'][t]) if t < len(cluster['entities']) else None})
            elif kind == 'effect':
                refs.append({'kind': 'effect', 'at': ref[1], 'entry': ref[2], 'size': ref[3],
                             'entry_bytes': effects[ref[2]].hex() if ref[2] < len(effects) else None})
        programs[bank] = {'root': value & 0x7F, 'code_hex': code.hex(), 'map_refs': refs,
                          'game_flags_made_room_flags': info.get('game_flags_made_room_flags')}
    return {'donor_map': m, 'entity_index': i, 'record_hex': bytes(raw).hex(), 'hooks_hex': bytes(raw[10:16]).hex(),
            'programs': programs, 'summary': summary}


def build(stock, root=LIBRARY, budget=150, progress=print):
    """Extract into root. Resumable: returns True when everything is there."""
    from behavior_transplant import behaviour_variants
    from editor_session import EditSession
    from map_slots import offsets
    t0 = time.time()
    root.mkdir(parents=True, exist_ok=True)
    for sub in ('objects', 'pages', 'global', 'maps'):
        (root / sub).mkdir(exist_ok=True)
    source = hashlib.sha256(stock).hexdigest()
    state_path = root / 'build-state.json'
    try:
        state = json.loads(state_path.read_text())
        if state.get('source_sha256') != source:
            state = {}
    except (OSError, ValueError):
        state = {}
    state.setdefault('source_sha256', source)
    o = offsets(stock)
    if not state.get('maps_done'):
        prints = []
        for m in range(STOCK_MAPS):
            block = bytes(memoryview(stock)[o[m]:o[m + 1]])
            prints.append(_sha1(block))
            path = root / 'maps' / f'{m:03d}.blk.gz'
            if not path.exists():
                path.write_bytes(gzip.compress(block, 6))
            if time.time() - t0 > budget:
                state_path.write_text(json.dumps(state))
                progress(f'maps: {m + 1}/{STOCK_MAPS}')
                return False
        state['map_fingerprints'] = prints
        start, sheet = struct.unpack_from('<2I', stock)
        end = struct.unpack_from('<I', stock, 0x14)[0]
        (root / 'global' / 'sprite_bank.bin').write_bytes(bytes(stock[start:end]))
        (root / 'global' / 'head.bin').write_bytes(bytes(stock[:o[0]]))   # everything before the maps
        state['global_bank'] = {'start': start, 'sheet': sheet, 'end': end,
                                'note': 'sprite_bank.bin = DATAS.BIN[start:end]; sheet = texture start'}
        state['maps_done'] = True
        state_path.write_text(json.dumps(state))
        progress('maps: done')
    if not (root / 'global' / 'head.bin').exists():
        (root / 'global' / 'head.bin').write_bytes(bytes(stock[:o[0]]))
    if 'names' not in state:
        names = _names(stock)
        state['names'] = {str(c): [n, k] for c, (n, k, _) in names.items()}
        state['placements'] = {str(c): v for c, v in _placements(stock).items()}
        state_path.write_text(json.dumps(state))
    done = set(state.get('objects_done', []))
    snapshot = EditSession(bytes(stock), None, verify=False)
    todo = sorted(set(int(c) for c in state['placements']) | set(int(c) for c in state['names']))
    for catalogue in todo:
        if catalogue in done:
            continue
        name, kind = state['names'].get(str(catalogue), [f'Class {catalogue}', 'object'])
        folder = root / 'objects' / f'{catalogue:03d}-{_slug(name)}'
        folder.mkdir(exist_ok=True)
        info = {'catalogue': catalogue, 'name': name, 'kind': kind,
                'placements': state['placements'].get(str(catalogue), []), 'variants': [], 'sprite': None}
        cache = {}
        for summary in behaviour_variants(stock, catalogue, cache):
            info['variants'].append(_variant(stock, snapshot, catalogue, summary))
        if catalogue >= 256:
            sprites = {}
            maps = list(dict.fromkeys([v['donor_map'] for v in info['variants']] + [m for m, _ in info['placements']][:1]))
            for m in maps:
                try:
                    sprites[str(m)] = _sprite(stock, m, catalogue, root / 'pages')
                except (ValueError, IndexError, struct.error) as exc:
                    sprites[str(m)] = {'map': m, 'error': str(exc)}
            info['sprite'] = {'bank': 'map', 'by_map': sprites}
        else:
            info['sprite'] = {'bank': 'global', 'sprite_id': catalogue, 'file': 'global/sprite_bank.bin'}
        try:
            from database_catalogue import _reference_image_uncached
            maps = [v['donor_map'] for v in info['variants']] or [m for m, _ in info['placements']] or [0]
            row = {'kind': kind, 'name': name, 'data': {},
                   'source': {'catalogue_index': catalogue, 'observed_maps': maps}}
            image = _reference_image_uncached(snapshot, row)
            if image is not None:
                image.save(folder / 'preview.png')
                info['preview'] = 'preview.png'
        except Exception as exc:
            info['preview_error'] = str(exc)
        (folder / 'object.json').write_text(json.dumps(info, indent=1))
        done.add(catalogue)
        state['objects_done'] = sorted(done)
        state.setdefault('folders', {})[str(catalogue)] = str(folder.relative_to(root)).replace('\\', '/')
        state_path.write_text(json.dumps(state))
        if time.time() - t0 > budget:
            progress(f'objects: {len(done)}/{len(todo)}')
            return False
    objects = {}
    for c in todo:
        name, kind = state['names'].get(str(c), [f'Class {c}', 'object'])
        objects[str(c)] = {'name': name, 'kind': kind, 'folder': state['folders'][str(c)]}
    (root / 'index.json').write_text(json.dumps({
        'format': FORMAT, 'complete': True, 'source_sha256': source,
        'built': time.strftime('%Y-%m-%d %H:%M:%S'), 'map_fingerprints': state['map_fingerprints'],
        'global_bank': state['global_bank'], 'objects': objects}, indent=1))
    progress(f'library complete: {len(objects)} classes, {STOCK_MAPS} maps')
    return True


def status(root=LIBRARY):
    ix = index(root)
    if ix:
        return f"complete: {len(ix['objects'])} classes, built {ix['built']}"
    try:
        state = json.loads((root / 'build-state.json').read_text())
        return f"in progress: maps {'done' if state.get('maps_done') else 'not done'}, objects {len(state.get('objects_done', []))}"
    except (OSError, ValueError):
        return 'not built'


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if 'tkinter' not in sys.modules:
        from unittest.mock import MagicMock
        for m in ['tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog', 'PIL.ImageTk', 'zoom_canvas']:
            sys.modules[m] = MagicMock()
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if cmd == 'build':
        stock = (ROOT / 'game/disc/DATA/DATAS.BIN').read_bytes()
        budget = float(sys.argv[2]) if len(sys.argv) > 2 else 150
        print('done' if build(stock, budget=budget) else 'run again to continue')
    else:
        print(status())
