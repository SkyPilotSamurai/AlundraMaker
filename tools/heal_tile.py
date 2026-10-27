"""Healing tiles: the save rooms' floor plates (red = Life, green = Magic) as
placeable objects, and the game's healing sparkle for Recover Life And Magic.

What the game does (save room maps 452-470, 147, 327):
* the plate is a floor tile (map 452: Life at 13,12 code 8085, Magic at 16,12
  code 7085), with see-through corners;
* a map event program (B) waits for the player on that tile and on the ground
  (3B box / 4B restart / 70 on ground / 4B), locks the player, plays sound 31
  (Life) or 36 (Magic), starts the sparkle six times at the player (A3) rising
  around him, shows shared message 10C / 10D, heals (96 80 32 / 97 32),
  unlocks, waits until the player steps off (3B around the tile) and restarts.
* the sparkle is map effect entry type 0E (global effect) in the map's effect
  table (12-byte entries: area x1 y1 x2 y2, flags, type, x, y, z, animation,
  0, 0); animation 0 = Life sparkle, 2 = Magic sparkle. A3's first operand is
  the index of that entry in the map's table (checked on all 60 stock uses).

Here the plate is drawn over the tile's own floor (its corners show the floor
under it), the two sparkle entries are added to the map's effect table when it
has none, and the B program is the save room's own, with this tile's position.
"""
import struct

DONOR_MAP = 452
DONOR_TILE = {'life': (13, 12), 'magic': (16, 12)}
NAMES = {'life': 'Healing Tile (Life)', 'magic': 'Healing Tile (Magic)'}
SPARKLE_TYPE = 0x0E
SPARKLE_ANIM = {'life': 0, 'magic': 2}
MAX_EFFECTS = 16          # stock maps use up to 13 entries
# (dx, dy, dz) of the six sparkles: Life rising, Magic falling (map 379 B1)
LIFE_STEPS = ((0, 0, 8), (0, 0, 12), (0, -4, 16), (0, 4, 20), (0, 8, 24), (0, -8, 28))
MAGIC_STEPS = ((0, 0, 28), (0, 0, 24), (0, 4, 20), (0, -4, 16), (0, 8, 12), (0, -8, 8))


def kind_of(definition):
    source = (definition or {}).get('source', {})
    return source.get('heal_tile') if source.get('variant') == 'heal_tile' else None


# --- the sparkle entries ----------------------------------------------------

def _entries(raw):
    if not raw:
        return []
    if len(raw) < 4 or (len(raw) - 4) % 12 or raw[-4:] != bytes(4):
        raise ValueError('Unsupported map effect table')
    return [raw[i:i + 12] for i in range(0, len(raw) - 4, 12)]


def ensure_effects(data, map_id, wanted):
    """(data, {(type, anim): index}) with a waiting entry (flags 0, whole map)
    for each global effect (type, anim) in map_id's effect table; existing
    waiting entries are reused. A3 / A2 start an entry by its index."""
    from native_class_placement import record_cluster, append_record_cluster
    from area_map import grid
    rows = _entries(record_cluster(data, map_id)['effects'])
    found = {}
    for key in dict.fromkeys(wanted):
        kind, anim = key
        for i, row in enumerate(rows):
            if row[4] == 0 and row[5] == kind and row[9] == anim:
                found[key] = i
                break
    missing = [k for k in dict.fromkeys(wanted) if k not in found]
    if not missing:
        return data, found
    if len(rows) + len(missing) > MAX_EFFECTS:
        raise ValueError(f'Map {map_id} has no room for {len(missing)} more effect(s) (at most {MAX_EFFECTS})')
    w, h, _ = grid(_View(data), map_id)
    for kind, anim in missing:
        found[(kind, anim)] = len(rows)
        rows.append(bytes((0, 0, w - 1, h - 1, 0, kind, 0, 0, 0, anim, 0, 0)))
    data, _ = append_record_cluster(data, map_id, effects=b''.join(rows) + bytes(4))
    return bytearray(data), found


def ensure_sparkles(data, map_id):
    """(data, {'life': index, 'magic': index}) with both sparkle entries in
    map_id's effect table (existing waiting entries are reused)."""
    from native_class_placement import record_cluster, append_record_cluster
    from area_map import grid
    cluster = record_cluster(data, map_id)
    rows = _entries(cluster['effects'])
    found = {}
    for kind, anim in SPARKLE_ANIM.items():
        for i, row in enumerate(rows):
            if row[4] == 0 and row[5] == SPARKLE_TYPE and row[9] == anim:
                found[kind] = i
                break
    missing = [k for k in SPARKLE_ANIM if k not in found]
    if not missing:
        return data, found
    if len(rows) + len(missing) > MAX_EFFECTS:
        raise ValueError(f'Map {map_id} has no room for the healing sparkle effect')
    w, h, _ = grid(_View(data), map_id)
    for kind in missing:
        found[kind] = len(rows)
        rows.append(bytes((0, 0, w - 1, h - 1, 0, SPARKLE_TYPE, 0, 0, 0, SPARKLE_ANIM[kind], 0, 0)))
    data, _ = append_record_cluster(data, map_id, effects=b''.join(rows) + bytes(4))
    return bytearray(data), found


def sparkle_bytes(effects, kinds=('life', 'magic')):
    """The six sparkle starts at the player for the given kinds (in step)."""
    out = bytearray()
    for i in range(6):
        for kind in kinds:
            dx, dy, dz = (LIFE_STEPS if kind == 'life' else MAGIC_STEPS)[i]
            out += struct.pack('<BBBhhh', 0xA3, effects[kind], 0x81, dx, dy, dz)
            if kind == 'magic' and kinds == ('magic',):
                out += bytes((0x92, effects[kind], 2))   # Magic sparkle animation (map 452 B3)
        out += bytes((0x37, 6))
    return bytes(out)


def restore_all_bytes(effects=None):
    """Recover All Life And Magic: Alundra stands, sound 31, both sparkles
    around him (map 379 B1), then C3 (restore life and magic)."""
    if effects is None:
        return bytes((0xC3,))
    return (bytes((0x59, 0x81, 0x00, 0xBD, 0x31, 0x00)) + sparkle_bytes(effects)[:-2]
            + bytes((0x37, 0x10, 0xC3)))   # the last pair waits 16, as on map 379


def tile_program(kind, x, y, z, effects):
    """The save room's B program for a healing tile at x, y (height z)."""
    def box(x1, x2, y1, y2):
        return bytes((0x3B, x1, x2, y1, y2, z, z))
    sound = 0x31 if kind == 'life' else 0x36
    code = bytearray(b'\x00')
    code += box(x, x, y, y) + bytes((0x4B, 0x70, 0x4B))
    code += bytes((0x10, 0x37, 0x01, 0x1A, 0x00, 0xBD, sound, 0x00))
    code += sparkle_bytes(effects, (kind,))
    if kind == 'life':
        code += bytes((0x0D, 0x0C, 0x01, 0x96, 0x80, 0x32))   # shared message 10C, heal life
    else:
        code += bytes((0x0D, 0x0D, 0x01, 0x97, 0x32))         # shared message 10D, restore magic
    code += bytes((0x11, 0x00))
    loop = len(code) - 1                                       # the 00 before the step-off test
    code += box(max(0, x - 1), x + 1, max(0, y - 1), y + 1)
    code += struct.pack('<Bh', 0x03, loop - len(code))       # still on / next to it: wait
    code += bytes((0x49, 0xFF))
    return bytes(code)


# --- the plate picture ------------------------------------------------------

class _View:
    """Read-only game-data view with the editor session's map readers."""
    def __init__(self, data):
        self.data = data
    from editor_session import EditSession as _E
    layout = _E.layout
    texture = _E.texture
    palette = _E.palette
    del _E


def donor_code(data, kind):
    from area_map import grid
    w, h, cells = grid(_View(data), DONOR_MAP)
    x, y = DONOR_TILE[kind]
    return cells[y * w + x]['values'][4]


def _pixels(raw, code):
    from map_tile_import import tile_bytes
    packed = tile_bytes(raw, code & 1023)
    return [v for b in packed for v in (b & 15, b >> 4)]


SWITCH_DONOR = (1, 301)      # Switch (Step On) on map 1: its lit top face is the floor switch picture
FACE_ROWS = 16


def floor_switch_of(definition):
    return (definition or {}).get('source', {}).get('variant') == 'floor_switch'


def switch_face(view):
    """The step-on switch's top face (24x16 RGBA): the top 16 rows of its picture."""
    from PIL import Image
    from native_class_placement import class_preview
    image = class_preview(view, *SWITCH_DONOR)[0].convert('RGBA')
    image = image.crop(image.getbbox())
    face = image.crop((0, 0, image.width, min(FACE_ROWS, image.height)))
    tile = Image.new('RGBA', (24, 16), (0, 0, 0, 0))
    tile.alpha_composite(face, ((24 - face.width) // 2, (16 - face.height) // 2))
    return tile


def _image_words(image):
    out = []
    for r, g, b, a in image.getdata():
        if a < 128:
            out.append(0)
        else:
            w = (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
            out.append(w or 0x8000)
    return out


PANEL_MAP = 452             # the save rooms' warp panel: map 452, tiles 14-15, 16-17
PANEL_TILES = {'panel00': (14, 16), 'panel10': (15, 16), 'panel01': (14, 17), 'panel11': (15, 17)}
PANEL_FLAGS = 85            # its warps' own flags there


def warp_panel_of(definition):
    return (definition or {}).get('source', {}).get('variant') == 'warp_panel'


def panel_code(data, kind):
    from area_map import grid
    w, h, cells = grid(_View(data), PANEL_MAP)
    x, y = PANEL_TILES[kind]
    return cells[y * w + x]['values'][4]


def picture_words(data, kind):
    if kind in PANEL_TILES:
        return tile_words(_View(data), PANEL_MAP, panel_code(data, kind))
    if kind == 'switch':
        return _image_words(switch_face(_View(data)))
    if kind == 'switch_lit':
        return _image_words(switch_face_lit(_View(data)))
    return plate_words(data, kind)


def tile_words(view, m, code):
    """384 colour words (0 = see-through) of tile `code` of map m."""
    words = view.palette(m, (code >> 12) & 15)[0]
    return [words[i] for i in _pixels(view.texture(m)[0], code)]


def plate_words(data, kind):
    """384 15-bit colour words of the plate (0 = see-through)."""
    view = _View(data)
    code = donor_code(data, kind)
    words = view.palette(DONOR_MAP, (code >> 12) & 15)[0]
    return [words[i] for i in _pixels(view.texture(DONOR_MAP)[0], code)]


def _reduce(words):
    """At most 16 colours (0 kept as see-through) for a 24x16 tile."""
    colours = list(dict.fromkeys(words))
    if len(colours) <= 16:
        return colours
    from PIL import Image
    opaque = [w for w in words if w]
    keep = 15 if 0 in colours else 16
    image = Image.new('RGB', (len(opaque), 1))
    image.putdata([((w & 31) << 3, ((w >> 5) & 31) << 3, ((w >> 10) & 31) << 3) for w in opaque])
    q = image.quantize(colors=keep, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:keep * 3]
    out = [0] if 0 in colours else []
    for i in range(keep):
        r, g, b = pal[i * 3:i * 3 + 3]
        word = (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
        out.append(word or 0x8000)
    return list(dict.fromkeys(out))


def _nearest(word, palette):
    if word == 0:
        return palette.index(0) if 0 in palette else 0
    r, g, b = word & 31, (word >> 5) & 31, (word >> 10) & 31
    return min((i for i, w in enumerate(palette) if w), key=lambda i: (
        (r - (palette[i] & 31)) ** 2 + (g - ((palette[i] >> 5) & 31)) ** 2 + (b - ((palette[i] >> 10) & 31)) ** 2))


def compose_tiles(raw, palettes, cells, w, h, picks, map_id=None):
    """Draw pictures over tiles' own floors. picks = [(x, y, words384)]
    (0 = see-through). raw (bytearray texture) and palettes (16 lists) are
    changed in place. Uses a blank, unused tile slot and an exact or free
    palette (else the closest existing one), as the editor's tile import does.
    Returns ({(x, y): code}, {palette: words})."""
    from compile_yield import step; step()   # (the build warm-up steps aside)
    from map_tile_import import write_tile, tile_bytes
    used = [c['values'][4] for c in cells] + [code for c in cells for code in _wall_codes(c)]
    used_tiles = {c & 1023 for c in used if c != 0xFFFF}
    used_pal = {(c >> 12) & 15 for c in used if c != 0xFFFF}
    blank = bytes(192)
    slots = [i for i in range(960) if (i // 10 * 16 + 15) * 128 + i % 10 * 12 + 12 <= len(raw)]
    free_tiles = [i for i in slots if i not in used_tiles and tile_bytes(raw, i) == blank]
    free_pal = [p for p in range(16) if p not in used_pal]
    palette_changes = {}
    new_codes = {}
    merged = []
    for pick in picks:
        x, y, picture = pick[:3]
        if not (0 <= x < w and 0 <= y < h):
            raise ValueError(f'Tile {x},{y} is outside map {map_id}')
        cell = cells[y * w + x]
        under = cell['values'][4]
        if under != 0xFFFF and (under & 1023) < 960:
            uw = palettes[(under >> 12) & 15]
            below = [uw[i] for i in _pixels(raw, under)]
        else:
            below = [0] * 384
        merged.append([p if p else b for p, b in zip(picture, below)])
    # picks with a 4th item (a group) share one palette: the picture's own colours first, then the
    # floor colours under its see-through pixels, most used first (closest colour for the rest)
    shared = {}
    for pick, words in zip(picks, merged):
        if len(pick) > 3:
            own, floor = shared.setdefault(pick[3], ({}, {}))
            for p, wd in zip(pick[2], words):
                bucket = own if p else floor
                bucket[wd] = bucket.get(wd, 0) + 1
    for key, (own, floor) in list(shared.items()):
        colours = list(own) if len(own) <= 16 else _reduce([wd for wd, n in own.items() for _ in range(n)])
        colours += [wd for wd in sorted(floor, key=floor.get, reverse=True) if wd not in colours][:16 - len(colours)]
        shared[key] = colours
    for pick, words in zip(picks, merged):
        x, y = pick[:2]
        colours = shared[pick[3]] if len(pick) > 3 else _reduce(words)
        indices = [colours.index(wd) if wd in colours else _nearest(wd, colours) for wd in words]
        chosen = None
        for p, target in enumerate(palettes):     # a palette that already has every colour
            if all(c in target for c in colours):
                chosen = p
                indices = [target.index(colours[i]) for i in indices]
                break
        if chosen is None and free_pal:
            chosen = free_pal.pop(0)
            target = colours + [0] * (16 - len(colours))
            palettes[chosen] = target
            palette_changes[chosen] = target
        elif chosen is None:
            chosen = min(range(16), key=lambda p: sum(
                (lambda a, b: ((a & 31) - (b & 31)) ** 2 + (((a >> 5) & 31) - ((b >> 5) & 31)) ** 2
                 + (((a >> 10) & 31) - ((b >> 10) & 31)) ** 2)(wd, palettes[p][_nearest(wd, palettes[p])])
                for wd in set(words) if wd))
            indices = [_nearest(wd, palettes[chosen]) for wd in words]
        packed = bytes(indices[i] | (indices[i + 1] << 4) for i in range(0, 384, 2))
        existing = next((i for i in slots if tile_bytes(raw, i) == packed), None)
        if existing is None:
            if not free_tiles:
                raise ValueError(f'Map {map_id} has no blank tile slot left for this picture')
            existing = free_tiles.pop(0)
            write_tile(raw, existing, packed)
        if existing in free_tiles:
            free_tiles.remove(existing)
        used_pal.add(chosen)
        new_codes[(x, y)] = existing | (chosen << 12)
    return new_codes, palette_changes


def _wall_codes(c):
    walls = c.get('walls')
    if not walls:
        return []
    if isinstance(walls, tuple) and len(walls) == 2 and isinstance(walls[1], list):
        return list(walls[1])        # map_area_copy.cells_of rows: (shift, codes)
    return [code for _, code, _, _ in walls]   # area_map.grid rows


def install_plates(data, map_id, tiles):
    """Draw the plates over the floors of `tiles` [(x, y, kind)] on map_id.
    Returns new data."""
    pictures = {}
    picks = []
    for x, y, kind in tiles:
        if kind not in pictures:
            pictures[kind] = picture_words(data, kind)
        picks.append((x, y, pictures[kind]))
    return _install_picks(data, map_id, picks)


def _install_picks(data, map_id, picks):
    """Draw picks [(x, y, words384)] over those squares' floors on map_id. Returns new data."""
    from compile_yield import step; step()   # (the build warm-up steps aside)
    from area_map import grid
    from map_block_repack import replace_section
    from texture_codec import pack_ez, unpack_ez
    data = bytearray(data)
    view = _View(data)
    raw, start, end = view.texture(map_id)
    raw = bytearray(raw)
    w, h, cells = grid(view, map_id)
    palettes = [view.palette(map_id, p)[0] for p in range(16)]
    new_codes, palette_changes = compose_tiles(raw, palettes, cells, w, h, picks, map_id)
    # texture (section 2), then palettes (section 0) and cells (section 1) in place
    old = view.texture(map_id)[0]
    if bytes(raw) != bytes(old):
        stream = pack_ez(bytes(raw), bytes(data[start:start + 6]))
        if unpack_ez(stream)[0] != bytes(raw):
            raise ValueError('Tile texture failed round-trip validation')
        stream += bytes((-len(stream)) % 4)
        if len(stream) <= end - start:
            data[start:end] = stream + bytes(end - start - len(stream))
        else:
            data = bytearray(replace_section(bytes(data), map_id, 2, stream))
    view = _View(data)
    base, hh = view.layout(map_id)
    for p, words in palette_changes.items():
        struct.pack_into('<16H', data, base + hh[0] + 16 + p * 32, *words)
    w, h, cells = grid(view, map_id)
    for (x, y), code in new_codes.items():
        struct.pack_into('<H', data, cells[y * w + x]['offset'] + 4, code)
    return data


def compose_in_editor(session, target, picks, grid):
    """compose_tiles for the editor: the new tile pictures and palettes wait
    in the session (shown at once, compressed into the game data later, like
    imported tiles); the tiles' floor codes change in `grid` (cells_of rows)."""
    w, h, cells = grid
    raw = bytearray(session.texture(target)[0])
    palettes = [session.palette(target, p)[0] for p in range(16)]
    new_codes, palette_changes = compose_tiles(raw, palettes, cells, w, h, picks, target)
    for p, words in palette_changes.items():
        session.defer_palette(session.palette(target, p)[1], struct.pack('<16H', *words))
    session.defer_texture(target, bytes(raw))
    for (x, y), code in new_codes.items():
        v = list(cells[y * w + x]['values']); v[4] = code; cells[y * w + x]['values'] = tuple(v)
    return new_codes


def preview(session, kind):
    """The plate picture (24x16, see-through corners) for the editor."""
    cache = getattr(session, '_heal_tile_previews', None)
    if cache is None:
        cache = {}
        try:
            session._heal_tile_previews = cache
        except AttributeError:
            pass
    if kind not in cache and kind == 'switch':
        cache[kind] = switch_face(session)
    if kind not in cache and kind == 'panel':   # the whole 2x2 warp panel
        from area_map import MapRenderer
        from PIL import Image
        renderer = MapRenderer(session, PANEL_MAP)
        image = Image.new('RGBA', (48, 32), (0, 0, 0, 0))
        for name, (x, y) in PANEL_TILES.items():
            image.alpha_composite(renderer.tile(panel_code(session.data, name)).convert('RGBA'),
                                  ((x - 14) * 24, (y - 16) * 16))
        cache[kind] = image
    if kind not in cache:
        from area_map import MapRenderer
        cache[kind] = MapRenderer(session, DONOR_MAP).tile(donor_code(session.data, kind)).convert('RGBA')
    return cache[kind]


def install_tiles(data, graphs):
    """Build every healing tile event: plate pictures, sparkle entries, B
    programs and map events. graphs: [(graph, kind)]. Returns (data, reports)."""
    from compile_yield import step; step()   # (the build warm-up steps aside)
    from area_map import grid
    from native_script_allocation import append_native_process
    from native_class_placement import record_cluster, append_record_cluster
    reports = []
    by_map = {}
    for graph, kind in graphs:
        by_map.setdefault(graph['map_id'], []).append((graph, kind))
    for map_id, rows in by_map.items():
        tiles = []
        for graph, kind in rows:
            x, y, rw, rh = graph['region']
            if (rw, rh) != (1, 1):
                raise ValueError(f"{graph['name']}: a healing tile covers one tile")
            for page in graph.get('pages') or []:
                if page.get('commands') or any(hh.get('commands') for hh in page.get('trigger_actions') or []):
                    raise ValueError(f"{graph['name']}: a healing tile heals by itself and takes no actions")
                if page.get('conditions'):
                    raise ValueError(f"{graph['name']}: a healing tile has no page conditions")
            tiles.append((x, y, kind))
        data = install_plates(data, map_id, tiles)
        data, effects = ensure_sparkles(data, map_id)
        w, h, cells = grid(_View(data), map_id)
        events = []
        for (graph, kind), (x, y, _) in zip(rows, tiles):
            z = cells[y * w + x]['values'][3]
            data, allocation = append_native_process(data, map_id, 'B', tile_program(kind, x, y, z, effects))
            data = bytearray(data)
            events.append(bytes((0, 0, w - 1, h - 1, allocation['hook_value'], 0, 0, 0)))
            reports.append({'event_id': graph['id'], 'map_id': map_id, 'name': graph.get('name'),
                            'heal_tile': kind, 'tile': [x, y, z], 'sparkle_effect': effects[kind],
                            'hook_value': allocation['hook_value'], 'bank': 'B',
                            'source': 'save room healing tile (map 452 B2/B3)', 'gameplay_verified': False})
        cluster = record_cluster(data, map_id)
        data, _ = append_record_cluster(data, map_id, map_events=cluster['events'] + events)
        data = bytearray(data)
    return data, reports


def panel_tiles(x, y):
    """The warp panel's four tiles when its event stands on (x, y), its
    bottom-left corner: [(tx, ty, picture kind)]."""
    return [(x, y - 1, 'panel00'), (x + 1, y - 1, 'panel10'), (x, y, 'panel01'), (x + 1, y, 'panel11')]


def add_warp_data(data, map_id, rect, destination):
    """A warp on map_id covering rect (x1, y1, x2, y2), like the editor's New
    Warp (record in the first free slot + the floor activation flag 80)."""
    from portal_records import Portal
    from area_map import grid
    from map_slots import map_exists
    view = _View(data)
    m = destination.get('map')
    if type(m) is not int or not 0 < m < 2547 or not map_exists(data, m):
        raise ValueError('The Warp Panel leads to a map that does not exist')
    base, h = view.layout(map_id)
    start = base + h[0] + 0x42c
    for i in range(64):
        p = Portal.read(data, start + i * 12)
        if (p.x1, p.y1, p.x2, p.y2) == (0, 0, 255, 255):
            break
    else:
        raise ValueError(f'Map {map_id} already has 64 warps')
    x1, y1, x2, y2 = rect
    data[start + i * 12:start + i * 12 + 12] = Portal(x1, y1, x2, y2, m, int(destination.get('x', 0)),
                                                      int(destination.get('y', 0)), int(destination.get('z', 0) or 0),
                                                      PANEL_FLAGS).encode()
    w, hh, cells = grid(view, map_id)
    for y in range(max(0, y1), min(hh - 1, y2) + 1):
        for x in range(max(0, x1), min(w - 1, x2) + 1):
            data[cells[y * w + x]['offset'] + 1] |= 0x80
            data[cells[y * w + x]['offset']] |= 0x04     # warp square: taken at once, any facing (stock 452)
    return i


# --- Step On Switch (Floor) turning green (2026-10-18) ------------------------
# The game's own step-on switches change map squares with command 85 (copy a
# square from a strip kept out in the dark part of the map, as map 1 does).
# The floor switch does the same: a lit (green) copy of its square is kept on
# an empty square far from anything, and stepping on it copies that over it.

def switch_face_lit(view):
    """The step-on switch's top face when pressed (animation 1: green)."""
    from PIL import Image
    import animation_preview as A
    from stock_donors import source_for
    m, catalogue = SWITCH_DONOR
    try:
        src = source_for(view, m)
    except Exception:
        src = view
    frame = A.load_animation(src, m, catalogue, 1, 0).frames[0].image.convert('RGBA')
    frame = frame.crop(frame.getbbox())
    face = frame.crop((0, 0, frame.width, min(FACE_ROWS, frame.height)))
    tile = Image.new('RGBA', (24, 16), (0, 0, 0, 0))
    tile.alpha_composite(face, ((24 - face.width) // 2, (16 - face.height) // 2))
    return tile


def spare_squares(data, map_id, count, taken=()):
    """`count` empty squares (no floor, no walls) as far as possible from any
    used square (at least 3 away), or fewer when the map has none."""
    from area_map import grid
    w, h, cells = grid(_View(data), map_id)
    used = [(c['x'], c['y']) for c in cells if c['values'][4] != 0xFFFF or c['values'][5] != -1]
    if not used:
        return []
    INF = 10 ** 9
    dist = [INF] * (w * h)
    from collections import deque
    q = deque()
    for x, y in used:
        dist[y * w + x] = 0; q.append((x, y))
    while q:
        x, y = q.popleft(); d = dist[y * w + x]
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and dist[ny * w + nx] > d + 1:
                dist[ny * w + nx] = d + 1; q.append((nx, ny))
    taken = set(taken)
    free = sorted(((dist[i], i % w, i // w) for i in range(w * h)
                   if dist[i] >= 3 and dist[i] < INF and (i % w, i // w) not in taken), reverse=True)
    out = []
    for d, x, y in free:
        if all(abs(x - a) + abs(y - b) >= 2 for a, b in out):
            out.append((x, y))
        if len(out) == count:
            break
    return out


def install_lit_copies(data, map_id, pairs):
    """pairs = [((x, y) switch square, (sx, sy) spare square)]: the spare square
    becomes an exact copy of the switch square (height, walk bits, walls) with
    the lit switch drawn on it. Returns new data."""
    from area_map import grid
    data = bytearray(data)
    w, h, cells = grid(_View(data), map_id)
    for (x, y), (sx, sy) in pairs:
        src = cells[y * w + x]['offset']; dst = cells[sy * w + sx]['offset']
        data[dst:dst + 8] = data[src:src + 8]
    return install_plates(data, map_id, [(sx, sy, 'switch_lit') for _, (sx, sy) in pairs])


def install_square_copies(data, map_id, pairs, kind):
    """pairs = [((x, y) square, (sx, sy) spare square)]: the spare square becomes an exact copy
    of the square (height, walk bits, walls) with picture `kind` drawn on it (Step On Switch
    (Floor): its unlit copy, put back when it is released). Returns new data."""
    from area_map import grid
    data = bytearray(data)
    w, h, cells = grid(_View(data), map_id)
    for (x, y), (sx, sy) in pairs:
        src = cells[y * w + x]['offset']; dst = cells[sy * w + sx]['offset']
        data[dst:dst + 8] = data[src:src + 8]
    return install_plates(data, map_id, [(sx, sy, kind) for _, (sx, sy) in pairs])


# --- Pattern Plate, Flush With Floor (2026-10-25) ------------------------------
# The plate is drawn in the floor (2x2 squares) like the Step On Switch (Floor):
# each symbol and the lit plate wait on spare 2x2 squares and are copied over it
# (85), so nothing solid stands on the floor (native_pattern_plate_profile flush).

PLATE_DONOR = (29, 364)      # the static pattern plate (map 29 entity 16)


def plate_frames(view, animation, direction):
    """[((animation, direction, frame index), frames shown)] of the game's plate animation; frames with
    the same picture share the first one's key."""
    import animation_preview as A
    from stock_donors import source_for
    m, catalogue = PLATE_DONOR
    try:
        src = source_for(view, m)
    except Exception:
        src = view
    clip = A.load_animation(src, m, catalogue, animation, direction)
    first = {}
    return [(first.setdefault(f.image_set_index, (animation, direction, i)), f.ticks) for i, f in enumerate(clip.frames)]


def plate_picture(view, animation, direction, frame):
    """[(dx, dy, words384)]: that frame of the plate, placed as the game draws it (its origin 24 px
    from the left, 8 px above the bottom of the 48x32 picture), cut into its four squares."""
    from PIL import Image
    import animation_preview as A
    from stock_donors import source_for
    m, catalogue = PLATE_DONOR
    try:
        src = source_for(view, m)
    except Exception:
        src = view
    f = A.load_animation(src, m, catalogue, animation, direction).frames[frame]
    canvas = Image.new('RGBA', (48, 32), (0, 0, 0, 0))
    canvas.alpha_composite(f.image.convert('RGBA'), (24 + f.left, 24 + f.top))
    return [(dx, dy, _image_words(canvas.crop((dx * 24, dy * 16, dx * 24 + 24, dy * 16 + 16))))
            for dy in (0, 1) for dx in (0, 1)]


def spare_blocks(data, map_id, count, taken=()):
    """`count` empty 2x2 squares (top-left corners) at least 3 squares from any
    used square and apart from each other and from `taken` squares."""
    from area_map import grid
    w, h, cells = grid(_View(data), map_id)
    used = [(c['x'], c['y']) for c in cells if c['values'][4] != 0xFFFF or c['values'][5] != -1]
    if not used:
        return []
    from collections import deque
    INF = 10 ** 9
    dist = [INF] * (w * h); q = deque()
    for x, y in used:
        dist[y * w + x] = 0; q.append((x, y))
    while q:
        x, y = q.popleft(); d = dist[y * w + x]
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and dist[ny * w + nx] > d + 1:
                dist[ny * w + nx] = d + 1; q.append((nx, ny))
    busy = set(taken); out = []
    # farthest from anything used first (out of the camera's sight), as spare_squares does
    blocks = sorted(((min(dist[b * w + a] for a, b in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1))), x, y)
                     for y in range(h - 1) for x in range(w - 1)), reverse=True)
    for d, x, y in blocks:
        if not 3 <= d < INF:
            break
        block = [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]
        if not any(abs(a - c) <= 1 and abs(b - e) <= 1 for a, b in block for c, e in busy):
            out.append((x, y)); busy.update(block)
            if len(out) == count:
                return out
    return out


def install_plate_pictures(data, map_id, plates):
    """plates = [((tx, ty) plate top-left, {(sx, sy): plate frame} spare
    blocks, frame shown first)] (plate frame = (animation, direction, frame
    index)): spare blocks become exact copies of the plate's squares with
    that frame drawn on; the plate's squares show the first."""
    from area_map import grid
    data = bytearray(data)
    view = _View(data)
    w, h, cells = grid(view, map_id)
    picks = []; pictures = {}
    for (tx, ty), blocks, base in plates:
        for (sx, sy), key in blocks.items():
            for dy in (0, 1):
                for dx in (0, 1):
                    src = cells[(ty + dy) * w + tx + dx]['offset']; dst = cells[(sy + dy) * w + sx + dx]['offset']
                    data[dst:dst + 8] = data[src:src + 8]
    for (tx, ty), blocks, base in plates:
        for (x0, y0), key in list(blocks.items()) + [((tx, ty), base)]:
            if key not in pictures:
                pictures[key] = plate_picture(view, *key)
            picks += [(x0 + dx, y0 + dy, words, key) for dx, dy, words in pictures[key]]   # one palette per frame
    return _install_picks(data, map_id, picks)
