"""Water tiles for the tile picker's Water tab (user request 2026-10-11).

Like the Bushes tab: every different water picture of the original game,
gathered from all maps, and painted together with its logic. Water is
recognised from the tile record, not the picture (survey of all 483 maps,
docs 2026-10-11): ground byte 2 / 8 / 18 / 24, or walkability bit 0x20 (water
edge), or walkability 24 with ground 4 (running water). The slope byte keeps
stairs and currents: a low nibble of 5..7 is a slope / stair, the high bits a
current direction.

Floors: a flat water tile - painting gives the target tile this picture and
the water's walkability, ground and slope bytes; its height stays.
Stairs: the same for sloped water and currents.
Walls: the wall stack of a water tile (falls, water edges), as in Tiles >
Walls. Which byte means exactly what in the game is inferred from where the
game uses it, not decoded from its code."""
import hashlib

WATER_GROUNDS = {2, 8, 18, 24}
EDGE = 0x20


def is_water(values):
    walk, ground, slope = values[0], values[1], values[2]
    return ground in WATER_GROUNDS or bool(walk & EDGE) or (walk == 24 and ground == 4)


def is_stair(values):
    return (values[2] & 0x0F) in (5, 6, 7) or values[2] >= 64


def water_styles(session, maps=None):
    """{'floors': [...], 'stairs': [...], 'walls': [...]} most used first."""
    from area_map import MapRenderer, grid
    from bush_catalogue import _stack_picture
    found = {'floors': {}, 'stairs': {}, 'walls': {}}
    for m in (range(0, 483) if maps is None else maps):
        try:
            _, _, cells = grid(session, m)
        except Exception:
            continue
        if not any(is_water(c['values']) for c in cells):
            continue
        try:
            renderer = MapRenderer(session, m)
        except Exception:
            continue
        for c in cells:
            v = c['values']
            if not is_water(v):
                continue
            if v[4] != 0xFFFF:
                kind = 'stairs' if is_stair(v) else 'floors'
                try:
                    image = renderer.tile(v[4]).convert('RGBA')
                except Exception:
                    continue
                key = (hashlib.sha1(image.tobytes()).hexdigest(), v[0], v[1], v[2])
                row = found[kind].get(key)
                if row is None:
                    row = found[kind][key] = dict(kind='water_' + kind, map=m, x=c['x'], y=c['y'], code=v[4],
                        walk=v[0], ground=v[1], slope=v[2], image=image, uses=0, key=f"{m}:{c['x']}:{c['y']}")
                row['uses'] += 1
            if c['walls']:
                shift = c['walls'][0][2]; codes = [code for _, code, _, _ in c['walls']]
                try:
                    image, floor_row = _stack_picture(renderer, shift, codes)
                except Exception:
                    continue
                if not image.getbbox():
                    continue
                key = (hashlib.sha1(image.tobytes()).hexdigest(), shift)
                row = found['walls'].get(key)
                if row is None:
                    row = found['walls'][key] = dict(kind='walls', map=m, x=c['x'], y=c['y'], shift=shift, codes=codes,
                        image=image, floor_row=floor_row, uses=0, key=f"{m}:{c['x']}:{c['y']}")
                row['uses'] += 1
    return {k: sorted(v.values(), key=lambda r: -r['uses']) for k, v in found.items()}


def cached_water_styles(session, rescan=False):
    """water_styles() of the original game, kept on the session and on disk."""
    import pickle
    from io import BytesIO
    from pathlib import Path
    from PIL import Image
    styles = getattr(session, '_water_styles', None)
    if styles is not None and not rescan:
        return styles
    from stock_source import catalogue_base
    original = catalogue_base(session)   # this computer's original game (2026-10-16)
    digest = hashlib.sha256(original).hexdigest()[:16]
    cache = Path(__file__).resolve().parents[1] / 'game' / 'editor-cache' / f'water-styles-v1-{digest}.pickle'
    if not rescan:
        try:
            rows = pickle.loads(cache.read_bytes())
            for group in rows.values():
                for row in group:
                    row['image'] = Image.open(BytesIO(row['image'])).convert('RGBA')
            session._water_styles = rows
            return rows
        except Exception:
            pass
    from editor_session import EditSession
    source = session if original == bytes(session.data) else EditSession(original, verify=False)
    styles = water_styles(source)
    session._water_styles = styles
    try:
        out = {}
        for kind, group in styles.items():
            out[kind] = []
            for row in group:
                buffer = BytesIO(); row['image'].save(buffer, 'PNG')
                out[kind].append(dict(row, image=buffer.getvalue()))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps(out))
    except Exception:
        pass
    return styles


def place_water(session, database, target, tiles, style, grid=None):
    """Give each tile the water picture and its walkability / ground / slope
    (one undo step); its height and wall stack stay."""
    from map_tile_import import import_tiles
    from bush_catalogue import _cells, _store
    tiles = list(dict.fromkeys(tiles)); label = f"Place water on {len(tiles)} tile(s)"
    with session.group(label):
        mapping = {}
        if style['map'] != target:
            try:
                mapping = import_tiles(session, database, target, style['map'], [style['code']], defer=True, original=True)
            except ValueError as error:
                if 'padding space' not in str(error) and 'No unused blank' not in str(error):
                    raise
                mapping = import_tiles(session, database, target, style['map'], [style['code']], erase_unused=True, defer=True, original=True)
        code = mapping.get(style['code'], style['code'])
        w, h, cells = _cells(session, target, grid); changed = 0
        for x, y in tiles:
            if 0 <= x < w and 0 <= y < h:
                cell = cells[y * w + x]; v = list(cell['values'])
                v[0], v[1], v[2], v[4] = style['walk'], style['ground'], style['slope'], code
                cell['values'] = tuple(v); changed += 1
        if changed:
            _store(session, target, grid, cells, label)
    return changed


def stair_styles(session, maps=None):
    """Every different stair / slope tile of the game (slope byte low nibble
    5..7): picture plus walkability, ground and slope, most used first."""
    from area_map import MapRenderer, grid
    found = {}
    for m in (range(0, 483) if maps is None else maps):
        try:
            _, _, cells = grid(session, m)
        except Exception:
            continue
        if not any((c['values'][2] & 0x0F) in (5, 6, 7) and c['values'][4] != 0xFFFF for c in cells):
            continue
        try:
            renderer = MapRenderer(session, m)
        except Exception:
            continue
        for c in cells:
            v = c['values']
            if (v[2] & 0x0F) not in (5, 6, 7) or v[4] == 0xFFFF:
                continue
            try:
                image = renderer.tile(v[4]).convert('RGBA')
            except Exception:
                continue
            key = (hashlib.sha1(image.tobytes()).hexdigest(), v[0], v[1], v[2])
            row = found.get(key)
            if row is None:
                row = found[key] = dict(kind='stairs', map=m, x=c['x'], y=c['y'], code=v[4],
                    walk=v[0], ground=v[1], slope=v[2], image=image, uses=0, key=f"{m}:{c['x']}:{c['y']}")
            row['uses'] += 1
    return sorted(found.values(), key=lambda r: -r['uses'])


def cached_stair_styles(session, rescan=False):
    import pickle
    from io import BytesIO
    from pathlib import Path
    from PIL import Image
    styles = getattr(session, '_stair_styles', None)
    if styles is not None and not rescan:
        return styles
    from stock_source import catalogue_base
    original = catalogue_base(session)   # this computer's original game (2026-10-16)
    digest = hashlib.sha256(original).hexdigest()[:16]
    cache = Path(__file__).resolve().parents[1] / 'game' / 'editor-cache' / f'stair-styles-v1-{digest}.pickle'
    if not rescan:
        try:
            rows = pickle.loads(cache.read_bytes())
            for row in rows:
                row['image'] = Image.open(BytesIO(row['image'])).convert('RGBA')
            session._stair_styles = rows
            return rows
        except Exception:
            pass
    from editor_session import EditSession
    source = session if original == bytes(session.data) else EditSession(original, verify=False)
    styles = stair_styles(source)
    session._stair_styles = styles
    try:
        out = []
        for row in styles:
            buffer = BytesIO(); row['image'].save(buffer, 'PNG'); out.append(dict(row, image=buffer.getvalue()))
        cache.parent.mkdir(parents=True, exist_ok=True); cache.write_bytes(pickle.dumps(out))
    except Exception:
        pass
    return styles
