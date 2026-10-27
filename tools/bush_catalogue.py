"""Cuttable bushes: map tiles, not objects (docs/2026-10-09-cuttable-bushes.txt).

A bush is a map tile whose first byte has bit 0x02 ('cuttable') and whose wall
stack (the raised layers drawn over and above the floor) is the bush picture.
The sword (ALUN_CD 8003B104) clears the bit and the wall stack, spawns the leaf
effect, rolls a drop and plays sound 31; the floor and height stay.

This module lists every different bush picture in the game (the database's
Bushes tab) and puts a bush on / takes it off any tile. Only the bush is
moved: the target tile keeps its own floor, height, slope and ground.

A wall stack lists layers top to bottom; layer i is drawn (i + 1 - shift) * 16
pixels below the floor, so the first `shift` layers stand on and above the
floor (the bush) and the rest hang below it (the cliff face of a raised tile).
Only the first part is the bush; the cliff face always stays the tile's own.
Note: the game removes the whole stack when the bush is cut, cliff face too."""
import hashlib
import struct

CUTTABLE = 0x02


def _cells(session, target, grid):
    """(w, h, cells) to edit: the editor's pending grid when given (edits are
    only shown until save/build), else the map's cells from the game data."""
    if grid is not None:
        return grid
    from map_area_copy import cells_of
    return cells_of(session, target)


def _store(session, target, grid, cells, label):
    if grid is None:
        from map_area_copy import rebuild_grid
        rebuild_grid(session, target, cells, label)


def split_stack(walls):
    """(shift, codes) -> (bush codes on/above the floor, codes below it)."""
    if not walls:
        return [], []
    shift, codes = walls
    shift = max(0, min(len(codes), shift))
    return list(codes[:shift]), list(codes[shift:])


def _stack_picture(renderer, shift, codes):
    from PIL import Image
    offsets = [(i + 1 - shift) * 16 for i in range(len(codes))]
    top = min(offsets + [0]); bottom = max(offsets + [0]) + 16
    image = Image.new('RGBA', (24, bottom - top), (0, 0, 0, 0))
    for code, offset in zip(codes, offsets):
        image.alpha_composite(renderer.tile(code), (0, offset - top))
    return image, -top


_HAS_CUTTABLE = None


def _has_cuttable_tile(session, m):
    """Quick test on the raw map grid: any cell whose first byte has bit 0x02."""
    import re
    global _HAS_CUTTABLE
    if _HAS_CUTTABLE is None:
        _HAS_CUTTABLE = re.compile(b'[' + b''.join(re.escape(bytes((v,))) for v in range(256) if v & CUTTABLE) + b']')
    base, h = session.layout(m); start = base + h[1]
    w, height = session.data[start:start + 2]
    first = start + 4 + 256 * 6; end = first + w * height * 8
    if not w or not height or end > base + h[2]:
        return False
    return _HAS_CUTTABLE.search(bytes(session.data[first:end:8])) is not None


def bush_styles(session, maps=None):
    """Every different bush picture: list of dicts (key, map, x, y, shift,
    codes, image, floor_row, uses, maps), most used first. key is
    'map:x:y' of the first bush found with that picture."""
    from area_map import MapRenderer, grid
    styles = {}
    candidates = range(0, 2547) if maps is None else maps
    for m in candidates:
        try:
            if not _has_cuttable_tile(session, m):
                continue
            w, h, cells = grid(session, m)
        except Exception:
            continue
        bushes = [c for c in cells if c['values'][0] & CUTTABLE and c['walls']]
        if not bushes:
            continue
        renderer = MapRenderer(session, m); seen = {}
        for c in bushes:
            codes, _ = split_stack((c['walls'][0][2], [code for _, code, _, _ in c['walls']]))
            if not codes:
                continue
            stack = tuple(codes)
            if stack not in seen:   # one picture per different stack on this map
                shift = len(codes)   # the bush alone: its bottom layer sits on the floor
                image, floor_row = _stack_picture(renderer, shift, codes)
                seen[stack] = (hashlib.sha1(image.tobytes() + bytes((shift & 255,))).hexdigest(), shift, image, floor_row)
            digest, shift, image, floor_row = seen[stack]
            style = styles.get(digest)
            if style is None:
                style = styles[digest] = dict(key=f"{m}:{c['x']}:{c['y']}", map=m, x=c['x'], y=c['y'],
                                              shift=shift, codes=codes, image=image, floor_row=floor_row,
                                              uses=0, maps=[])
            style['uses'] += 1
            if m not in style['maps']:
                style['maps'].append(m)
    return sorted(styles.values(), key=lambda s: (-s['uses'], s['map'], s['y'], s['x']))


def cached_bush_styles(session, rescan=False):
    """bush_styles() of the original game, without empty pictures. Scanning
    takes seconds (every map's texture), so the result is kept on the session
    and in private-inputs/editor-cache (keyed by the original data) for the
    next start. The tile picker's and the database's Bushes tabs share it."""
    import pickle
    from io import BytesIO
    from pathlib import Path
    from PIL import Image
    styles = getattr(session, '_bush_styles', None)
    if styles is not None and not rescan:
        return styles
    from stock_source import catalogue_base
    original = catalogue_base(session)   # this computer's original game (2026-10-16)
    digest = hashlib.sha256(original).hexdigest()[:16]
    cache = Path(__file__).resolve().parents[1] / 'private-inputs' / 'editor-cache' / f'bush-styles-v1-{digest}.pickle'
    if not rescan:
        try:
            rows = pickle.loads(cache.read_bytes())
            for row in rows:
                row['image'] = Image.open(BytesIO(row['image'])).convert('RGBA')
            session._bush_styles = rows
            return rows
        except Exception:
            pass
    from editor_session import EditSession
    source = session if original == bytes(session.data) else EditSession(original, verify=False)
    styles = [s for s in bush_styles(source) if s['image'].getbbox()]
    session._bush_styles = styles
    try:
        rows = []
        for row in styles:
            buffer = BytesIO(); row['image'].save(buffer, 'PNG')
            rows.append(dict(row, image=buffer.getvalue()))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps(rows))
    except Exception:
        pass   # no cache file: scanned again next start
    return styles


def bush_name(document, style, index):
    return (document.get('bush_names') or {}).get(style['key']) or f"Bush {index + 1} (map {style['map']})"


def place_bush(session, database, target, tiles, style, grid=None):
    """Put the bush of `style` on each (x, y) of `tiles` on map `target` as one
    undo step. The bush picture is imported into the target map's tile set
    when it comes from another map. Returns the number of tiles changed."""
    from map_area_copy import cells_of, rebuild_grid
    from map_tile_import import import_tiles
    tiles = list(dict.fromkeys(tiles))
    label = f"Place bush on {len(tiles)} tile(s)"
    with session.group(label):
        mapping = {}
        if style['map'] != target:
            try:
                mapping = import_tiles(session, database, target, style['map'], style['codes'], defer=True, original=True)
            except ValueError as error:   # same rule as Copy area: make room only when needed
                if 'padding space' not in str(error) and 'No unused blank' not in str(error):
                    raise
                mapping = import_tiles(session, database, target, style['map'], style['codes'], erase_unused=True, defer=True, original=True)
        codes = [code if code == 0xFFFF else mapping.get(code, code) for code in style['codes']]
        w, h, cells = _cells(session, target, grid)
        changed = 0
        for x, y in tiles:
            if not (0 <= x < w and 0 <= y < h):
                continue
            cell = cells[y * w + x]; values = list(cell['values'])
            values[0] |= CUTTABLE
            _, below = split_stack(cell['walls'])   # keep the tile's own cliff face
            cell['values'] = tuple(values); cell['walls'] = (len(codes), list(codes) + below)
            changed += 1
        if changed:
            _store(session, target, grid, cells, label)
    return changed


def remove_bush(session, target, tiles, grid=None):
    """Take the bush off each tile (as if cut, but for good): clears the
    cuttable bit and the wall stack. Tiles without a bush are left alone."""
    from map_area_copy import cells_of, rebuild_grid
    w, h, cells = _cells(session, target, grid)
    changed = 0
    for x, y in dict.fromkeys(tiles):
        if not (0 <= x < w and 0 <= y < h):
            continue
        cell = cells[y * w + x]; values = list(cell['values'])
        if not values[0] & CUTTABLE:
            continue
        values[0] &= ~CUTTABLE & 0xFF
        _, below = split_stack(cell['walls'])
        cell['values'] = tuple(values); cell['walls'] = (0, below) if below else None
        changed += 1
    if changed:
        _store(session, target, grid, cells, f"Remove bush from {changed} tile(s)")
    return changed


def is_bush(cell):
    return bool(cell['values'][0] & CUTTABLE)


# -- Walls and floors (tile picker categories) ------------------------------
def floor_codes(session, m):
    """Floor tile codes used on map m, most used first."""
    from collections import Counter
    from area_map import grid
    _, _, cells = grid(session, m)
    counts = Counter(c['values'][4] for c in cells if c['values'][4] != 0xFFFF)
    return [code for code, _ in counts.most_common()]


def wall_stacks(session, m):
    """Every different wall stack of map m (shift, codes, image, uses), most
    used first. A wall stack is everything a tile shows above and below its
    floor: cliff faces, building fronts, pillars, bushes."""
    from area_map import MapRenderer, grid
    _, _, cells = grid(session, m)
    renderer = MapRenderer(session, m); stacks = {}
    for c in cells:
        if not c['walls']:
            continue
        key = (c['walls'][0][2], tuple(code for _, code, _, _ in c['walls']))
        if key not in stacks:
            image, floor_row = _stack_picture(renderer, key[0], list(key[1]))
            if not image.getbbox():
                continue
            stacks[key] = dict(kind='walls', map=m, x=c['x'], y=c['y'], shift=key[0], codes=list(key[1]),
                               image=image, floor_row=floor_row, uses=0, key=f"{m}:{c['x']}:{c['y']}")
        stacks[key]['uses'] += 1
    return sorted(stacks.values(), key=lambda s: -s['uses'])


def place_walls(session, database, target, tiles, style, grid=None):
    """Give each tile the whole wall stack of `style` (one undo step); the
    tile keeps its floor, height and walkability. Pictures from another map
    are imported into the map's tile set."""
    from map_area_copy import cells_of, rebuild_grid
    from map_tile_import import import_tiles
    tiles = list(dict.fromkeys(tiles)); label = f"Place walls on {len(tiles)} tile(s)"
    with session.group(label):
        mapping = {}
        if style['map'] != target:
            try:
                mapping = import_tiles(session, database, target, style['map'], style['codes'], defer=True, original=True)
            except ValueError as error:
                if 'padding space' not in str(error) and 'No unused blank' not in str(error):
                    raise
                mapping = import_tiles(session, database, target, style['map'], style['codes'], erase_unused=True, defer=True, original=True)
        codes = [code if code == 0xFFFF else mapping.get(code, code) for code in style['codes']]
        w, h, cells = _cells(session, target, grid); changed = 0
        for x, y in tiles:
            if 0 <= x < w and 0 <= y < h:
                cells[y * w + x]['walls'] = (style['shift'], list(codes)); changed += 1
        if changed:
            _store(session, target, grid, cells, label)
    return changed


def remove_walls(session, target, tiles, grid=None):
    """Take every wall layer off each tile (the floor stays)."""
    from map_area_copy import cells_of, rebuild_grid
    w, h, cells = _cells(session, target, grid); changed = 0
    for x, y in dict.fromkeys(tiles):
        if 0 <= x < w and 0 <= y < h and cells[y * w + x]['walls']:
            cells[y * w + x]['walls'] = None; changed += 1
    if changed:
        _store(session, target, grid, cells, f"Remove walls from {changed} tile(s)")
    return changed


# -- Floor layers -----------------------------------------------------------
# A wall layer drawn exactly where the floor is (layer index shift - 1) lies on
# top of the floor: the game uses it to layer floor pictures (a rug on boards,
# a path edge over grass). Only that one layer is changed here.
def place_layer(session, target, tiles, code, grid=None):
    """Put picture `code` (already in this map's tile set) on top of each
    tile's floor as one undo step; other wall layers stay."""
    from map_area_copy import cells_of, rebuild_grid
    w, h, cells = _cells(session, target, grid); changed = 0
    for x, y in dict.fromkeys(tiles):
        if not (0 <= x < w and 0 <= y < h):
            continue
        cell = cells[y * w + x]
        shift, codes = cell['walls'] if cell['walls'] else (0, [])
        codes = list(codes)
        if shift >= 1 and shift <= len(codes):
            codes[shift - 1] = code            # replace the layer on the floor
        elif shift <= 0:
            # pieces only below the floor (a raised tile's face): the layer goes on
            # the floor itself, the pieces stay on their squares (user 2026-10-25)
            codes = [code] + [0xFFFF] * (-shift) + codes; shift = 1
        else:
            # pieces above the floor but none on it: fill up to the floor slot
            codes = codes + [0xFFFF] * (shift - 1 - len(codes)) + [code]
        cell['walls'] = (shift, codes); changed += 1
    if changed:
        _store(session, target, grid, cells, f"Layer floor on {changed} tile(s)")
    return changed


def remove_layer(session, target, tiles, grid=None):
    """Take the layer lying on the floor off each tile (other layers stay)."""
    from map_area_copy import cells_of, rebuild_grid
    w, h, cells = _cells(session, target, grid); changed = 0
    for x, y in dict.fromkeys(tiles):
        if not (0 <= x < w and 0 <= y < h) or not cells[y * w + x]['walls']:
            continue
        shift, codes = cells[y * w + x]['walls']
        if not 1 <= shift <= len(codes):
            continue
        above, below = list(codes[:shift - 1]), list(codes[shift:])
        if above:
            # keep the layers above the floor: put an empty picture on the floor
            codes = above + [0xFFFF] + below
            cells[y * w + x]['walls'] = (shift, codes)
        else:
            cells[y * w + x]['walls'] = (0, below) if below else None
        changed += 1
    if changed:
        _store(session, target, grid, cells, f"Remove floor layer from {changed} tile(s)")
    return changed


# -- Floors of every map (tile picker Floors tab) ---------------------------
FLOOR_COLUMNS = 20
FAMILY_ORDER = ('Greens', 'Yellows', 'Browns', 'Oranges', 'Reds', 'Pinks and purples', 'Blues',
                'Teals', 'Greys', 'Light', 'Dark')


def floor_look(image):
    """(family, sort key) of a floor picture: its colour family (by the hue,
    saturation and brightness of its average colour), then brightness, hue
    and roughness, so similar-looking floors end up next to each other."""
    import colorsys
    from PIL import ImageStat
    rgb = image.convert('RGB'); alpha = image.getchannel('A')
    stat = ImageStat.Stat(rgb, mask=alpha)
    if not stat.count or not stat.count[0]:
        return 'Dark', (0, 0, 0)
    r, g, b = (v / 255 for v in stat.mean)
    h, sat, val = colorsys.rgb_to_hsv(r, g, b); hue = h * 360
    rough = sum(stat.stddev) / 3 / 255
    if val < 0.16:
        family = 'Dark'
    elif sat < 0.16:
        family = 'Light' if val > 0.75 else 'Greys'
    elif hue < 15 or hue >= 345:
        family = 'Reds'
    elif hue < 45:
        family = 'Browns' if val < 0.6 else 'Oranges'
    elif hue < 70:
        family = 'Yellows' if val >= 0.45 else 'Browns'
    elif hue < 165:
        family = 'Greens'
    elif hue < 200:
        family = 'Teals'
    elif hue < 260:
        family = 'Blues'
    else:
        family = 'Pinks and purples'
    return family, (round(val * 6), round(hue / 20), round(rough * 10), val)


def organise_floors(images):
    """Indexes of `images` grouped by look: [(family, [index, ...]), ...]."""
    groups = {}
    for index, image in enumerate(images):
        family, key = floor_look(image)
        groups.setdefault(family, []).append((key, index))
    return [(family, [index for _, index in sorted(groups[family])])
            for family in FAMILY_ORDER if family in groups]


def floor_sheet(images, columns=FLOOR_COLUMNS, title=None):
    """Picture sheet of floors ordered by look (similar pictures next to each
    other, no headings). Returns (sheet, blocks): blocks = [(top y, [index, ...])]."""
    from PIL import Image
    order = [index for _, members in organise_floors(images) for index in members]
    rows = max(1, (len(order) + columns - 1) // columns)
    sheet = Image.new('RGBA', (columns * 24, rows * 16), (31, 34, 40, 255))
    for n, index in enumerate(order):
        sheet.alpha_composite(images[index], (n % columns * 24, n // columns * 16))
    floor_sheet.names = []
    return sheet, [(0, order)]


def wall_codes(session, m):
    """Every wall tile code of map m's wall stacks, most used first."""
    from collections import Counter
    from area_map import grid
    _, _, cells = grid(session, m)
    counts = Counter(code for c in cells for _, code, _, _ in c['walls'] if code != 0xFFFF)
    return [code for code, _ in counts.most_common()]


def wall_catalogue(session, rescan=False, build=True):
    """floor_catalogue() for the single wall tiles of every map."""
    return floor_catalogue(session, rescan, build, kind='walls')


def floor_catalogue(session, rescan=False, build=True, kind='floors'):
    """Every different floor picture of the original game's maps, grouped by
    look (floor_sheet): dict(entries=[(map, code, uses)], sheet=PIL image,
    blocks=[(top y, [entry index])]). Scanning every map takes many seconds,
    so the result is kept on the session and in private-inputs/editor-cache
    (keyed by the original data). build=False only looks at the caches."""
    import pickle
    from collections import Counter
    from io import BytesIO
    from pathlib import Path
    from PIL import Image
    attribute = '_floor_catalogue' if kind == 'floors' else '_wall_catalogue'
    found = getattr(session, attribute, None)
    if found is not None and not rescan:
        return found
    from stock_source import catalogue_base
    original = catalogue_base(session)   # this computer's original game (2026-10-16)
    digest = hashlib.sha256(original).hexdigest()[:16]
    version = 'v4' if kind == 'floors' else 'v5'
    cache = Path(__file__).resolve().parents[1] / 'private-inputs' / 'editor-cache' / f'{kind}-{version}-{digest}.pickle'
    if not rescan:
        try:
            stored = pickle.loads(cache.read_bytes())
            found = dict(entries=stored['entries'], blocks=stored['blocks'], names=stored.get('names'),
                         stacks=stored.get('stacks', []),
                         sheet=Image.open(BytesIO(stored['sheet'])).convert('RGBA'))
            setattr(session, attribute, found)
            return found
        except Exception:
            pass
    if not build:
        return None
    from area_map import MapRenderer, grid
    from editor_session import EditSession
    source = session if original == bytes(session.data) else EditSession(original, verify=False)
    pictures = {}; uses = Counter(); stacks = {}; stack_uses = Counter()
    for m in range(0, 2547):
        try:
            _, _, cells = grid(source, m)
        except Exception:
            continue
        if kind == 'floors':
            codes = Counter(c['values'][4] for c in cells if c['values'][4] != 0xFFFF)
        else:
            codes = Counter(code for c in cells for _, code, _, _ in c['walls'] if code != 0xFFFF)
        if not codes:
            continue
        renderer = MapRenderer(source, m)
        for code, n in codes.items():
            try:
                image = renderer.tile(code)
            except Exception:
                continue
            if not image.getbbox():
                continue
            key = hashlib.sha1(image.tobytes()).digest()
            if key not in pictures:
                pictures[key] = (m, code, image)
            uses[key] += n
        if kind == 'walls':
            # whole wall stacks as they stand on the map (picture keys, top to bottom)
            for c in cells:
                if not c['walls']:
                    continue
                layers = []
                for _, code, _, _ in c['walls']:
                    try:
                        image = renderer.tile(code)
                    except Exception:
                        image = None
                    layers.append(hashlib.sha1(image.tobytes()).digest() if image is not None and image.getbbox() else None)
                if not any(layers):
                    continue
                skey = tuple(layers)
                if skey not in stacks:
                    stacks[skey] = m
                stack_uses[skey] += 1
    order = sorted(pictures, key=lambda k: (-uses[k], pictures[k][0], pictures[k][1]))
    entries = [(pictures[k][0], pictures[k][1], uses[k]) for k in order]
    sheet, blocks = floor_sheet([pictures[k][2] for k in order])
    stack_rows = []
    if kind == 'walls':
        index_of = {k: i for i, k in enumerate(order)}
        from PIL import Image as _Image
        looks = []
        for skey, m in stacks.items():
            picture = _Image.new('RGBA', (24, 16 * len(skey)), (0, 0, 0, 0))
            for n, k in enumerate(skey):
                if k is not None:
                    picture.alpha_composite(pictures[k][2], (0, n * 16))
            family, look = floor_look(picture)
            looks.append(((FAMILY_ORDER.index(family), look, -stack_uses[skey]),
                          [index_of[k] if k is not None else -1 for k in skey], stack_uses[skey], m))
        stack_rows = [(layers, used, m) for _, layers, used, m in sorted(looks, key=lambda item: item[0])]
    found = dict(entries=entries, sheet=sheet, blocks=blocks, names=list(floor_sheet.names), stacks=stack_rows)
    setattr(session, attribute, found)
    try:
        buffer = BytesIO(); sheet.save(buffer, 'PNG')
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps(dict(entries=entries, blocks=blocks, names=found['names'], stacks=stack_rows,
                                            sheet=buffer.getvalue())))
    except Exception:
        pass
    return found


# -- Single wall tiles (tile picker Walls tab) -------------------------------
def place_face(session, target, tiles, code, grid=None):
    """Add wall tile `code` as a new layer under each tile's lowest layer (a
    cliff or building face one row further down); one undo step."""
    from map_area_copy import cells_of, rebuild_grid
    w, h, cells = _cells(session, target, grid); changed = 0
    for x, y in dict.fromkeys(tiles):
        if 0 <= x < w and 0 <= y < h:
            cell = cells[y * w + x]
            shift, codes = cell['walls'] if cell['walls'] else (0, [])
            cell['walls'] = (shift, list(codes) + [code]); changed += 1
    if changed:
        _store(session, target, grid, cells, f"Add wall tile to {changed} tile(s)")
    return changed


def remove_face(session, target, tiles, grid=None):
    """Take the lowest wall layer off each tile (only layers below the floor)."""
    from map_area_copy import cells_of, rebuild_grid
    w, h, cells = _cells(session, target, grid); changed = 0
    for x, y in dict.fromkeys(tiles):
        if not (0 <= x < w and 0 <= y < h) or not cells[y * w + x]['walls']:
            continue
        shift, codes = cells[y * w + x]['walls']
        if len(codes) <= shift:
            continue   # nothing below the floor
        codes = list(codes[:-1])
        cells[y * w + x]['walls'] = (shift, codes) if codes else None; changed += 1
    if changed:
        _store(session, target, grid, cells, f"Remove wall tile from {changed} tile(s)")
    return changed


def map_wall_stacks(session, m, renderer=None):
    """This map's different wall stacks as they stand on the map, ordered by
    look: [(codes top to bottom (0xFFFF = empty), uses)]."""
    from collections import Counter
    from PIL import Image
    from area_map import MapRenderer, grid
    renderer = renderer or MapRenderer(session, m)
    _, _, cells = grid(session, m)
    counts = Counter(tuple(code for _, code, _, _ in c['walls']) for c in cells if c['walls'])
    rows = []
    for codes, used in counts.items():
        picture = Image.new('RGBA', (24, 16 * len(codes)), (0, 0, 0, 0))
        for n, code in enumerate(codes):
            if code != 0xFFFF:
                picture.alpha_composite(renderer.tile(code), (0, n * 16))
        if not picture.getbbox():
            continue
        family, look = floor_look(picture)
        rows.append(((FAMILY_ORDER.index(family), look, -used), list(codes), used))
    return [(codes, used) for _, codes, used in sorted(rows, key=lambda item: item[0])]


# -- Floors and walls as they stand on the maps (tile picker Floors/Walls) --
# A "column" is what one map cell shows: for Floors its floor with the layers
# on, above and below it; for Walls only its wall layers. Each piece keeps its
# place (dy) as drawn on the map, so the picker shows them as on the maps,
# ordered by look so similar ones sit together.
COLUMN_KINDS = ('floors', 'walls')


def cell_pieces(cell, kind):
    """[(code, dy, is_floor)] of one map cell as drawn: the floor at row
    max(0, shift - 1), layer i at (i + 1 - shift) rows from the floor."""
    shift = cell['walls'][0][2] if cell['walls'] else 0
    floor_y = max(0, shift - 1) * 16
    pieces = []
    if kind == 'floors' and cell['values'][4] != 0xFFFF:
        pieces.append((cell['values'][4], floor_y, True))
    for _, code, _, i in cell['walls']:
        if code != 0xFFFF:
            pieces.append((code, floor_y + (i + 1 - shift) * 16, False))
    if pieces:
        top = min(dy for _, dy, _ in pieces)
        pieces = [(code, dy - top, floor) for code, dy, floor in pieces]
    return pieces


def column_picture(pictures):
    """Compose [(image, dy)] into one 24-pixel-wide picture."""
    from PIL import Image
    height = max([dy + 16 for _, dy in pictures] or [16])
    picture = Image.new('RGBA', (24, height), (0, 0, 0, 0))
    for image, dy in pictures:
        picture.alpha_composite(image, (0, dy))
    return picture


def look_key(picture, used=0):
    family, look = floor_look(picture)
    return (FAMILY_ORDER.index(family), look, -used)


def map_columns(session, m, kind, renderer=None):
    """This map's different columns ordered by look: [([(code, dy, is_floor)], uses)]."""
    from collections import Counter
    from area_map import MapRenderer, grid
    renderer = renderer or MapRenderer(session, m)
    _, _, cells = grid(session, m)
    blank = {}
    def visible(pieces):
        kept = []
        for code, dy, floor in pieces:
            if code not in blank:
                blank[code] = renderer.tile(code).getbbox() is None
            if not blank[code]:
                kept.append((code, dy, floor))
        if not kept:
            return ()
        top = min(dy for _, dy, _ in kept)
        return tuple((code, dy - top, floor) for code, dy, floor in kept)
    counts = Counter(visible(cell_pieces(c, kind)) for c in cells)
    rows = []
    for pieces, used in counts.items():
        if not pieces:
            continue
        picture = column_picture([(renderer.tile(code), dy) for code, dy, _ in pieces])
        if picture.getbbox():
            rows.append((look_key(picture, used), list(pieces), used))
    return [(pieces, used) for _, pieces, used in sorted(rows, key=lambda item: item[0])]


def column_catalogue(session, kind, rescan=False, build=True):
    """Every different column of every map of the original game, ordered by
    look: dict(entries=[(map, code)] (one per tile picture), atlas=PIL image
    (entry i at (i % 20 * 24, i // 20 * 16)), columns=[([(entry, dy,
    is_floor)], uses, map)]). Kept on the session and in
    private-inputs/editor-cache; build=False only looks at the caches."""
    import pickle
    from collections import Counter
    from io import BytesIO
    from pathlib import Path
    from PIL import Image
    attribute = f'_{kind}_columns'
    found = getattr(session, attribute, None)
    if found is not None and not rescan:
        return found
    from stock_source import catalogue_base
    original = catalogue_base(session)   # this computer's original game (2026-10-16)
    digest = hashlib.sha256(original).hexdigest()[:16]
    cache = Path(__file__).resolve().parents[1] / 'private-inputs' / 'editor-cache' / f'{kind}-columns-v2-{digest}.pickle'
    if not rescan:
        try:
            stored = pickle.loads(cache.read_bytes())
            found = dict(entries=stored['entries'], columns=stored['columns'],
                         atlas=Image.open(BytesIO(stored['atlas'])).convert('RGBA'))
            setattr(session, attribute, found)
            return found
        except Exception:
            pass
    if not build:
        return None
    from area_map import MapRenderer, grid
    from editor_session import EditSession
    source = session if original == bytes(session.data) else EditSession(original, verify=False)
    pictures = {}; columns = {}; uses = Counter()
    for m in range(0, 2547):
        try:
            _, _, cells = grid(source, m)
        except Exception:
            continue
        found_cells = [pieces for pieces in (cell_pieces(c, kind) for c in cells) if pieces]
        if not found_cells:
            continue
        renderer = MapRenderer(source, m); keys = {}
        for pieces in found_cells:
            column = []
            for code, dy, floor in pieces:
                if code not in keys:
                    try:
                        image = renderer.tile(code)
                    except Exception:
                        image = None
                    key = hashlib.sha1(image.tobytes()).digest() if image is not None and image.getbbox() else None
                    keys[code] = key
                    if key is not None and key not in pictures:
                        pictures[key] = (m, code, image)
                if keys[code] is not None:
                    column.append((keys[code], dy, floor))
            if column:
                top = min(dy for _, dy, _ in column)   # no empty space above the picture
                column = tuple((k, dy - top, floor) for k, dy, floor in column)
                columns.setdefault(column, m); uses[column] += 1
    order = list(pictures); index_of = {k: i for i, k in enumerate(order)}
    rows = max(1, (len(order) + 19) // 20)
    atlas = Image.new('RGBA', (20 * 24, rows * 16), (0, 0, 0, 0))
    for i, key in enumerate(order):
        atlas.alpha_composite(pictures[key][2], (i % 20 * 24, i // 20 * 16))
    ranked = []
    for column, m in columns.items():
        picture = column_picture([(pictures[k][2], dy) for k, dy, _ in column])
        ranked.append((look_key(picture, uses[column]), [(index_of[k], dy, floor) for k, dy, floor in column], uses[column], m))
    ranked.sort(key=lambda item: item[0])
    found = dict(entries=[pictures[k][:2] for k in order], atlas=atlas,
                 columns=[(pieces, used, m) for _, pieces, used, m in ranked])
    setattr(session, attribute, found)
    try:
        buffer = BytesIO(); atlas.save(buffer, 'PNG')
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps(dict(entries=found['entries'], columns=found['columns'], atlas=buffer.getvalue())))
    except Exception:
        pass
    return found
