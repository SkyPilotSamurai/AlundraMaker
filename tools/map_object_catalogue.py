"""Map objects: furniture and decorations made of map tiles (the database /
tile picker's Map Objects tab, after Bushes).

Two kinds:
* raised  - stools, tables, beds, bookshelves, crates...: a block of tiles
  standing higher than the floor around it. Placed, it keeps its heights
  above the tile you click (so it blocks and can be jumped on as in the game),
  with its walkability, ground and slope, and its pictures (top and faces).
* overlay - rugs and floor decorations: only their floor pictures are laid
  over the tiles; the tiles keep their height and logic.

Found in the game: a raised object is a group of joined tiles higher than a
level floor all around it (the side behind it may be a higher wall); an
overlay is a group of joined floor tiles at the floor's height whose pictures
use a palette the floor around them does not, inside one room. Pictures that
look alike are listed once. You can also save any area of a map as your own.
"""
import hashlib

MAX_SIDE = 6
MAX_RISE = 6
KEEP_FLOOR = 0xFFFE      # a tile of the object that shows the floor it is placed on
ROW_VERSION = 2          # styles with rows written by this version (0xFFFF = no picture)

# Map Objects sub-tabs (Trees is its own tab).
CATEGORIES = (('furniture', 'Furniture'), ('stairs', 'Stairs'),
              ('other', 'Other'))      # no Ladders tab (user 2026-10-18): ladders show under Stairs      # no Rugs tab (user request 2026-10-15): rugs show under Other
CATEGORY_NAMES = dict(CATEGORIES + (('trees', 'Trees'),))


def _cells(session, m):
    from area_map import grid
    w, h, cells = grid(session, m)
    return w, h, cells


def _empty(c):
    return c['values'][4] == 0xFFFF and not c['walls']


def words_image(words):
    """A 24x16 picture from 384 colour words (0 = see-through)."""
    from PIL import Image
    image = Image.new('RGBA', (24, 16), (0, 0, 0, 0))
    image.putdata([(((w & 31) << 3) | ((w & 31) >> 2), (((w >> 5) & 31) << 3) | (((w >> 5) & 31) >> 2),
                    (((w >> 10) & 31) << 3) | (((w >> 10) & 31) >> 2), 255) if w else (0, 0, 0, 0) for w in words])
    return image


def object_picture(renderer, rows, kind='raised', cut=None):
    """Picture of an object without the floor around it: rows = [(dx, dy,
    values, walls(shift, codes) or None)]. Tiles showing plain floor are left
    out; a floor-level tile whose picture is drawn over the floor (a trunk's
    foot, a table leg on boards) shows only the part that is not floor
    (`cut`: {(dx, dy): words})."""
    from PIL import Image
    cut = cut or {}
    pieces = []
    for dx, dy, v, walls in rows:
        y = dy * 16 - v[3] * 16
        if (dx, dy) in cut:
            pieces.append((words_image(cut[(dx, dy)]), dx * 24, y))
        elif v[4] not in (0xFFFF, KEEP_FLOOR) and (kind == 'overlay' or v[3] > 0 or kind == 'raised'):
            pieces.append((v[4], dx * 24, y))
        if walls:
            shift, codes = walls
            pieces += [(code, dx * 24, y + (i + 1 - shift) * 16) for i, code in enumerate(codes)]
    pieces = [p for p in pieces if not isinstance(p[0], int) or p[0] not in (0xFFFF, KEEP_FLOOR)]
    if not pieces:
        return Image.new('RGBA', (24, 16), (0, 0, 0, 0)), 0, 0
    left = min(p[1] for p in pieces); top = min(p[2] for p in pieces)
    right = max(p[1] for p in pieces) + 24; bottom = max(p[2] for p in pieces) + 16
    image = Image.new('RGBA', (right - left, bottom - top), (0, 0, 0, 0))
    for code, x, y in pieces:
        tile = code if not isinstance(code, int) else renderer.tile(code).convert('RGBA')
        image.alpha_composite(tile, (x - left, y - top))
    return image, left, top


_FLOOR_WORDS = {}


def floor_cut(session, m, code):
    """A floor-level picture with its floor taken out. The game paints things
    standing on the floor (a trunk's foot, roots, a stool's legs) into floor
    tiles; the pixels equal to the map's plain floor at the same place are made
    see-through. Returns ('floor', None) for plain floor, ('cut', words) when
    part of the tile is floor, ('whole', None) when none of it is."""
    from heal_tile import tile_words
    key = (id(session), m, len(session.data))
    if key not in _FLOOR_WORDS:
        floors = []
        for f in floor_codes(session, m):
            try:
                floors.append(tile_words(session, m, f))
            except Exception:
                pass
        _FLOOR_WORDS[key] = floors
    floors = _FLOOR_WORDS[key]
    words = tile_words(session, m, code)
    if not floors:
        return 'whole', None
    scores = [sum(1 for a, b in zip(words, f) if a == b) for f in floors]
    best = max(scores)
    if best >= 384:
        return 'floor', None
    if best < 64:
        return 'whole', None
    near = [f for f, n in zip(floors, scores) if n >= max(64, best * 0.6)]
    out = [0 if any(w == f[i] for f in near) else w for i, w in enumerate(words)]
    if sum(1 for w in out if w) < 12:
        return 'floor', None   # only specks left: floor with a few odd pixels
    return 'cut', out


def object_cut(session, m, rows):
    """{(dx, dy): words} for the object's floor-level tiles drawn over floor,
    and the rows with plain floor marked KEEP_FLOOR."""
    cut = {}; out = []
    for dx, dy, v, walls in rows:
        if v[3] == 0 and v[4] not in (0xFFFF, KEEP_FLOOR):
            kind, words = floor_cut(session, m, v[4])
            if kind == 'floor':
                v = tuple(v[:4]) + (KEEP_FLOOR,)
            elif kind == 'cut':
                cut[(dx, dy)] = words
        out.append((dx, dy, v, walls))
    return out, cut


def _components(w, h, member):
    seen = set(); out = []
    for start in member:
        if start in seen:
            continue
        stack = [start]; seen.add(start); group = []
        while stack:
            x, y = stack.pop(); group.append((x, y))
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in member and n not in seen:
                    seen.add(n); stack.append(n)
        out.append(group)
    return out


def _wall(c):
    return bool(c['values'][0] & 0x40)


def find_objects(session, m):
    """[(kind, base, [(x, y)])] on map m."""
    from collections import Counter
    w, h, cells = _cells(session, m)
    at = lambda x, y: cells[y * w + x] if 0 <= x < w and 0 <= y < h else None
    found = []
    levels = Counter(c['values'][3] for c in cells if not _empty(c) and not _wall(c) and not c['walls'])
    for base, count in levels.items():
        if count < 6:
            continue
        plain = lambda c: c is not None and not _empty(c) and not _wall(c) and not c['walls'] and c['values'][3] == base
        member = set()
        for c in cells:
            if _empty(c) or _wall(c):
                continue
            hh = c['values'][3]
            if base < hh <= base + MAX_RISE or (hh == base and c['walls']):
                member.add((c['x'], c['y']))
        for group in _components(w, h, member):
            xs = [p[0] for p in group]; ys = [p[1] for p in group]
            if max(xs) - min(xs) >= MAX_SIDE or max(ys) - min(ys) >= MAX_SIDE:
                continue
            gs = set(group); ok = True; floor_sides = 0; edges = 0
            for x, y in group:
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if n in gs:
                        continue
                    c = at(*n); edges += 1
                    if plain(c):
                        floor_sides += 1
                    elif c is not None and not _empty(c) and (_wall(c) or c['values'][3] > base + MAX_RISE):
                        pass   # the room's wall beside / behind it
                    else:
                        ok = False; break
                if not ok:
                    break
            raised = any(cells[y * w + x]['values'][3] > base for x, y in group)
            if ok and raised and floor_sides >= 2 and floor_sides * 2 >= edges:
                found.append(('raised', base, sorted(group, key=lambda p: (p[1], p[0]))))
        # rugs: floor tiles at this level in a palette the floor around them does not use
        floor_palette = Counter(c['values'][4] >> 12 for c in cells if plain(c))
        if not floor_palette:
            continue
        main = floor_palette.most_common(1)[0][0]
        rug = {(c['x'], c['y']) for c in cells if plain(c) and c['values'][4] >> 12 != main and c['values'][4] & 1023 < 960}
        for group in _components(w, h, rug):
            xs = [p[0] for p in group]; ys = [p[1] for p in group]
            if len(group) < 4 or max(xs) - min(xs) >= 12 or max(ys) - min(ys) >= 12:
                continue
            if len(group) != (max(xs) - min(xs) + 1) * (max(ys) - min(ys) + 1):
                continue   # rugs are rectangles
            gs = set(group)
            around = [at(x + dx, y + dy) for x, y in group for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (x + dx, y + dy) not in gs]
            if not all(plain(c) and c['values'][4] >> 12 == main for c in around):
                continue   # a rug lies inside the floor
            if len({cells[y * w + x]['values'][4] for x, y in group}) < 3:
                continue   # patterned, not a patch of another floor
            found.append(('overlay', base, sorted(group, key=lambda p: (p[1], p[0]))))
    return found


def _dark(image):
    """Mostly black (shadows, the void around rooms): not an object."""
    pixels = [p for p in image.getdata() if p[3]]
    if not pixels:
        return True
    dark = sum(1 for r, g, b, a in pixels if r + g + b < 72)
    return dark * 2 > len(pixels)


def _green(image):
    pixels = [p for p in image.getdata() if p[3]]
    if not pixels:
        return 0
    return sum(1 for r, g, b, a in pixels if g > r + 8 and g > b + 8 and g > 40) / len(pixels)


def _bright(image):
    pixels = [p for p in image.getdata() if p[3]]
    return sum(1 for r, g, b, a in pixels if r + g + b > 450) / len(pixels) if pixels else 0


def is_tree(image):
    """A tree's picture: mostly leaves, at least two tiles wide and three
    high, nothing lit or white (houses with green roofs have both)."""
    return image.width >= 40 and image.height >= 48 and _green(image) >= 0.3 and _bright(image) <= 0.005


def find_trees(session, m, renderer=None):
    """Trees, two ways the game builds them:
    * a raised block whose top and front faces are mostly green (the crown
      standing on its trunk), on the floor in front of it;
    * floor tiles whose green pieces all stand above the floor (the crown),
      with the raised, blocking tiles behind them (the trunk's top).
    [('raised', base, [(x, y)])]"""
    from area_map import MapRenderer
    w, h, cells = _cells(session, m)
    renderer = renderer or MapRenderer(session, m)
    at = lambda x, y: cells[y * w + x] if 0 <= x < w and 0 <= y < h else None
    tile_green = {}
    def green_tile(code):
        if code not in tile_green:
            tile_green[code] = _green(renderer.tile(code).convert('RGBA')) if code != 0xFFFF else 0
        return tile_green[code]
    found = []
    # 1. green raised blocks
    crown = {(c['x'], c['y']) for c in cells if not _empty(c) and not _wall(c) and c['walls']
             and len(c['walls']) >= 2 and green_tile(c['values'][4]) >= 0.5}
    # the rest of the crown's top: joined green tiles about as high
    grow = list(crown)
    while grow:
        x, y = grow.pop()
        top = at(x, y)['values'][3]
        for n in ((x + 1, y), (x - 1, y), (x, y - 1)):
            c = at(*n)
            if (n not in crown and c is not None and not _empty(c) and not _wall(c)
                    and c['values'][3] >= top - 2 and green_tile(c['values'][4]) >= 0.5):
                crown.add(n); grow.append(n)
    for group in _components(w, h, crown):
        xs = [p[0] for p in group]; ys = [p[1] for p in group]
        if max(xs) - min(xs) >= 8 or max(ys) - min(ys) >= 6 or len(group) < 2:
            continue
        gs = set(group); front = []
        for x in set(xs):
            bottom = max(y for gx, y in group if gx == x)
            c = at(x, bottom + 1)
            if c is not None and not _empty(c) and (x, bottom + 1) not in gs:
                front.append(c['values'][3])
        if not front:
            continue
        base = min(front)
        rise = max(at(x, y)['values'][3] for x, y in group) - base
        if not 3 <= rise <= 16 or any(at(x, y)['values'][3] <= base for x, y in group):
            continue
        group = sorted(group, key=lambda p: (p[1], p[0]))
        picture = object_picture(renderer, object_rows(session, m, base, group))[0]
        if _green(picture) >= 0.3 and _bright(picture) <= 0.005:
            found.append(('raised', base, group))   # mostly leaves; a green roof has lit windows and walls
    # 2. crowns drawn above the floor, with the trunk's raised top behind
    leaves = {}
    for c in cells:
        if not c['walls'] or _empty(c):
            continue
        shift = c['walls'][0][2]; codes = [code for _, code, _, _ in c['walls']]
        if shift < 2 or len(codes) < 2:
            continue   # the crown stands above the floor
        g = _green(object_picture(renderer, [(0, 0, (0, 0, 0, 0, 0xFFFF), (shift, codes))])[0])
        if g >= 0.15:
            leaves[(c['x'], c['y'])] = (c['values'][3], g)
    seen = set()
    for (x, y), (base, g) in sorted(leaves.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if (x, y) in seen or g < 0.3:
            continue
        while (x - 1, y) in leaves and leaves[(x - 1, y)][0] == base and (x - 1, y) not in seen:
            x -= 1   # the crown's left edge may be less green
        run = []
        while (x, y) in leaves and leaves[(x, y)][0] == base and len(run) < 8:
            run.append((x, y)); seen.add((x, y)); x += 1
        trunk = []
        for lx, ly in run:
            for back in (1, 2):
                c = at(lx, ly - back)
                if c is not None and c['values'][3] > base and c['values'][0] & 1 and not _wall(c):
                    trunk.append((lx, ly - back))
                else:
                    break
        if len(run) >= 2 and trunk:
            found.append(('raised', base, sorted(run + trunk, key=lambda p: (p[1], p[0]))))
    return found


def tree_whole(session, m, base, group):
    """The whole tree: the crown and trunk found, plus what stands in front of
    them down to the floor - raised trunk tiles and floor tiles whose picture
    is not plain floor (the trunk's foot, roots) - at most 4 rows down."""
    w, h, cells = _cells(session, m)
    floor = floor_codes(session, m)
    at = lambda x, y: cells[y * w + x] if 0 <= x < w and 0 <= y < h else None
    gs = set(group)
    for x in sorted({p[0] for p in group}):
        y = max(py for px, py in gs if px == x)
        for _ in range(4):
            c = at(x, y + 1)
            if c is None or _empty(c) or _wall(c) or (x, y + 1) in gs:
                break
            hh = c['values'][3]
            if base < hh <= base + MAX_RISE * 3:
                gs.add((x, y + 1)); y += 1; continue      # trunk standing in front
            if hh == base and c['values'][4] not in floor and c['values'][4] != 0xFFFF:
                gs.add((x, y + 1)); y += 1; continue      # its foot drawn into the floor
            break
    return sorted(gs, key=lambda p: (p[1], p[0]))


def tree_rows(rows):
    """A tree's floor-level tiles keep only the pieces drawn above the floor
    (its crown); a layer lying on the floor (grass, a bush) is the floor's."""
    out = []
    for dx, dy, v, walls in rows:
        if walls and v[3] == 0:
            shift, codes = walls
            kept = [(i + 1 - shift, c) for i, c in enumerate(codes) if i + 1 - shift < 0 and c != 0xFFFF]
            if kept:
                top = min(o for o, _ in kept); last = max(o for o, _ in kept)
                stack = [0xFFFF] * (last - top + 1)
                for o, c in kept:
                    stack[o - top] = c
                walls = (1 - top, stack)
            else:
                walls = None
        out.append((dx, dy, v, walls))
    return out


def classify(style, map_name=''):
    """Sub-tab of a game object: rugs, stairs, ladders, furniture or other.
    Ladders are narrow climbs (stair-slope tiles, the object at most 3 tiles
    wide); stairs have stair or side-ramp tiles; furniture is found indoors."""
    if style['kind'] == 'overlay':
        return 'rugs'
    rows = style['rows']
    slopes = [r for r in rows if r[2][2] & 3]
    if slopes:
        width = max(r[0] for r in rows) - min(r[0] for r in rows) + 1
        climb = {r[1] for r in slopes if r[2][2] & 3 == 1}
        return 'stairs'   # ladders included (no Ladders tab)
    name = map_name.lower()
    indoors = any(k in name for k in ('house', 'inside', 'inoa village', 'shop', 'ship', 'bar', 'cabin',
                                       'manor', 'sanctuary', 'well', 'keep 1'))
    return 'furniture' if indoors else 'other'


_FLOOR_CODES = {}


def floor_codes(session, m):
    """Tile pictures map m uses as plain floor (tiles with no pieces): an
    object's tile showing one of these is floor, not part of the object."""
    key = (id(session), m, len(session.data))
    if key not in _FLOOR_CODES:
        from collections import Counter
        w, h, cells = _cells(session, m)
        count = Counter(c['values'][4] for c in cells if not c['walls'] and not _empty(c) and not c['values'][0] & 1)
        _FLOOR_CODES[key] = {code for code, n in count.items() if n >= 2 and code != 0xFFFF}
    return _FLOOR_CODES[key]


def object_rows(session, m, base, group, kind='raised'):
    """Rows (dx, dy, values with height above `base`, walls). A tile whose
    picture is the map's plain floor gets KEEP_FLOOR: placed, it keeps the
    floor already there (0xFFFF stays "no picture", as in the game)."""
    w, h, cells = _cells(session, m)
    floor = floor_codes(session, m)
    x0 = min(p[0] for p in group); y0 = min(p[1] for p in group)
    rows = []
    for x, y in group:
        c = cells[y * w + x]; v = list(c['values']); v[3] -= base
        if kind == 'raised' and v[4] in floor:
            v[4] = KEEP_FLOOR
        walls = (c['walls'][0][2], [code for _, code, _, _ in c['walls']]) if c['walls'] else None
        rows.append((x - x0, y - y0, tuple(v[:5]), walls))
    return rows


def object_styles(session, maps=None):
    from area_map import MapRenderer
    from tree_catalogue import standing_trees, tree_signature, unique_trees
    styles = {}
    all_trees = []
    for m in (range(0, 483) if maps is None else maps):
        try:
            found = find_objects(session, m)
            renderer = MapRenderer(session, m)
            trees = standing_trees(session, m, renderer)   # whole trees, with their shadows
        except Exception:
            continue
        if not found and not trees:
            continue
        try:
            from map_names import map_label
            label = map_label(m)
        except Exception:
            label = ''
        tree_cells = set()
        for base, rows, cuts, image, (tx, ty) in trees:
            tree_cells |= {(tx + r[0], ty + r[1]) for r in rows}
            all_trees.append(((m, base, rows, cuts, image, tx, ty), tree_signature(image)))
        found = [f for f in found if not set(f[2]) & tree_cells]   # parts of a tree
        for kind, base, group in found:
            whole_tree = False
            rows = object_rows(session, m, base, group, kind)
            rows, cut = object_cut(session, m, rows) if kind == 'raised' else (rows, {})
            image, left, top = object_picture(renderer, rows, kind, cut)
            if not image.getbbox() or _dark(image):
                continue
            digest = hashlib.sha1(kind.encode() + image.tobytes() + repr(image.size).encode()).hexdigest()
            style = styles.get(digest)
            if style is None:
                x0 = min(p[0] for p in group); y0 = min(p[1] for p in group)
                style = styles[digest] = dict(key=f'{m}:{x0}:{y0}', kind=kind, map=m, x=x0, y=y0, base=base,
                                              cells=[(r[0], r[1]) for r in rows], rows=rows, image=image,
                                              cut=cut, v=ROW_VERSION, uses=0, maps=[])
                style['category'] = classify(style, label)
            style['uses'] += 1
            if m not in style['maps']:
                style['maps'].append(m)
    # Trees: one of each, as it stands most often in the game
    for sig, (m, base, rows, cuts, image, tx, ty), uses in unique_trees(all_trees):
        styles['tree:' + repr(sig)] = dict(key=f'{m}:{tx}:{ty}', kind='raised', map=m, x=tx, y=ty, base=base,
                                           cells=[(r[0], r[1]) for r in rows], rows=rows, image=image, cut=cuts,
                                           v=ROW_VERSION, uses=uses, maps=[m], category='trees')
    return sorted(styles.values(), key=lambda s: (-s['uses'], s['map'], s['y'], s['x']))


def _trees_with_floor(session, styles):
    """Trees' picker pictures with the floor at their base (as they are
    placed): drawn from their rows without taking the floor out."""
    from area_map import MapRenderer
    for style in styles:
        if style.get('category') != 'trees' or style.get('floor_kept'):
            continue
        try:
            renderer = MapRenderer(session, style['map'])
            image, _, _ = object_picture(renderer, style['rows'], style['kind'], None)
        except Exception:
            continue
        if image.getbbox():
            style['image'] = image; style['floor_kept'] = True
    return styles


def cached_object_styles(session, rescan=False):
    """object_styles() of the original game, kept on the session and in
    private-inputs/editor-cache (keyed by the original data), like the bushes."""
    import pickle
    from io import BytesIO
    from pathlib import Path
    from PIL import Image
    styles = getattr(session, '_map_object_styles', None)
    if styles is not None and not rescan:
        return styles
    from stock_source import catalogue_base
    original = catalogue_base(session)   # this computer's original game (2026-10-16)
    digest = hashlib.sha256(original).hexdigest()[:16]
    cache = Path(__file__).resolve().parents[1] / 'private-inputs' / 'editor-cache' / f'map-objects-v11-{digest}.pickle'
    if not rescan:
        try:
            rows = pickle.loads(cache.read_bytes())
            for row in rows:
                if row.get('category') == 'ladders':row['category'] = 'stairs'   # cached before the Ladders tab was removed
                row['image'] = Image.open(BytesIO(row['image'])).convert('RGBA')
            session._map_object_styles = _trees_with_floor(session, rows)
            return rows
        except Exception:
            pass
    from editor_session import EditSession
    source = session if original == bytes(session.data) else EditSession(original, verify=False)
    styles = _trees_with_floor(source, object_styles(source))
    session._map_object_styles = styles
    try:
        rows = []
        for row in styles:
            buffer = BytesIO(); row['image'].save(buffer, 'PNG')
            rows.append(dict(row, image=buffer.getvalue()))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps(rows))
    except Exception:
        pass
    return styles


def object_name(document, style, index):
    names = document.get('map_object_names') or {}
    if style.get('builtin'):
        return style['name']
    if style.get('user'):
        return style.get('name') or f'My object {index + 1}'
    kind = {'rugs': 'Rug', 'trees': 'Tree', 'stairs': 'Stairs', 'ladders': 'Ladder', 'furniture': 'Furniture'}.get(
        style.get('category'), 'Rug' if style['kind'] == 'overlay' else 'Object')
    return names.get(style['key']) or f"{kind} {index + 1} (map {style['map']})"


def user_objects(document):
    """Map objects saved by the user (document['map_objects'])."""
    out = []
    for row in document.get('map_objects') or []:
        if isinstance(row, dict) and row.get('rows'):
            rows = [(r[0], r[1], tuple(r[2]), (r[3][0], list(r[3][1])) if r[3] else None) for r in row['rows']]
            if row.get('v') != ROW_VERSION and row.get('kind') == 'raised':
                # saved before 0xFFFE existed: "no picture" on a raised tile meant "keep the floor"
                rows = [(dx, dy, v[:4] + (KEEP_FLOOR,) if v[4] == 0xFFFF and v[3] > 0 else v, wl) for dx, dy, v, wl in rows]
            cut = {(c[0], c[1]): list(c[2]) for c in row.get('cut') or []}
            out.append(dict(row, user=True, rows=rows, cut=cut))
    return out


def object_from_area(session, m, rect, kind, name, category=None):
    """A map object from rect (x, y, w, h) of map m. Raised: the tiles higher
    than the lowest floor in the area, and floor tiles that carry pieces;
    overlay: every tile's floor picture."""
    w, h, cells = _cells(session, m)
    x0, y0, rw, rh = rect
    area = [cells[y * w + x] for y in range(y0, y0 + rh) for x in range(x0, x0 + rw) if 0 <= x < w and 0 <= y < h]
    area = [c for c in area if not _empty(c)]
    if not area:
        raise ValueError('The area has no tiles')
    # the floor: the lowest tile in the area or right around it
    ring = [cells[y * w + x] for y in range(y0 - 1, y0 + rh + 1) for x in range(x0 - 1, x0 + rw + 1)
            if 0 <= x < w and 0 <= y < h and not (x0 <= x < x0 + rw and y0 <= y < y0 + rh)]
    ring = [c for c in ring if not _empty(c) and not _wall(c)]
    base = min(c['values'][3] for c in area + ring)
    if kind == 'raised':
        chosen = [c for c in area if c['values'][3] > base or c['walls']]
        if not any(c['values'][3] > base for c in chosen):
            raise ValueError('Nothing in the area stands higher than its floor; save it as an overlay instead')
    else:
        chosen = [c for c in area if c['values'][4] != 0xFFFF]
    if kind == 'raised':   # floor tiles in the area with something drawn into them (a trunk's foot)
        floor = floor_codes(session, m)
        chosen += [c for c in area if c not in chosen and c['values'][3] == base and c['values'][4] not in floor
                   and c['values'][4] != 0xFFFF]
    group = [(c['x'], c['y']) for c in chosen]
    rows = object_rows(session, m, base, group, kind)
    if category == 'trees':
        rows = tree_rows(rows)
    rows, cut = object_cut(session, m, rows) if kind == 'raised' else (rows, {})
    from area_map import MapRenderer
    image, _, _ = object_picture(MapRenderer(session, m), rows, kind, cut)
    row = dict(key=f'user:{m}:{x0}:{y0}:{rw}:{rh}:{name}', kind=kind, map=m, x=min(p[0] for p in group),
               y=min(p[1] for p in group), base=base, name=name, v=ROW_VERSION,
               rows=[[r[0], r[1], list(r[2]), [r[3][0], list(r[3][1])] if r[3] else None] for r in rows],
               cut=[[dx, dy, list(words)] for (dx, dy), words in cut.items()])
    style = dict(row, rows=rows)
    row['category'] = category or ('rugs' if kind == 'overlay' else classify(style))
    return row, image


def _place_panel(session, target, at, style, grid):
    """A panel's pictures drawn over the floors they land on (new tile
    pictures made for this map). Bottom-left corner at `at`."""
    from heal_tile import compose_in_editor, tile_words
    w, h, cells = grid
    rows = style['rows']
    bx, by = at
    ax, ay = bx - min(r[0] for r in rows), by - max(r[1] for r in rows)
    picks = []
    for dx, dy, v, _ in rows:
        x, y = ax + dx, ay + dy
        if 0 <= x < w and 0 <= y < h:
            picks.append((x, y, tile_words(session, style['map'], v[4])))
    return list(compose_in_editor(session, target, picks, grid))


def panel_top_left(style, at):
    rows = style['rows']
    return at[0] - min(r[0] for r in rows), at[1] - max(r[1] for r in rows)


def merge_walls(under, over):
    """Wall stack `over` laid on `under`: each piece keeps its place (offset
    from the floor); where both have one, `over` wins."""
    pieces = {}
    for stack in (under, over):
        if stack:
            shift, codes = stack
            for i, code in enumerate(codes):
                if code != 0xFFFF:
                    pieces[i + 1 - shift] = code
    if not pieces:
        return None
    top = min(pieces); last = max(pieces)
    return (1 - top, [pieces.get(o, 0xFFFF) for o in range(top, last + 1)])


def place_object(session, database, target, at, style, grid, layer=True):
    """Stamp `style` with its bottom-left tile at `at` on map `target`, into
    `grid` (w, h, cells of map_area_copy.cells_of rows). Raised objects stand
    on the height of the tile at `at`. Returns the tiles changed.

    layer (Layer On Top, the default): the object is laid over what is there.
    Its floor-level tiles keep their floor: the object's part of the picture
    (floor taken out) is drawn over it and its pieces join the tile's own.
    Without layer, the object's tiles replace the tiles under it."""
    from map_tile_import import import_tiles
    w, h, cells = grid
    rows = style['rows']
    if style['kind'] == 'panel':
        return _place_panel(session, target, at, style, grid)
    # the tile you click is the object's bottom-left corner; it builds right and up
    bx, by = at
    if not (0 <= bx < w and 0 <= by < h):
        return []
    base = cells[by * w + bx]['values'][3]
    ax, ay = bx - min(r[0] for r in rows), by - max(r[1] for r in rows)
    raised = style['kind'] == 'raised'
    # Trees keep the floor tiles at their base (user request 2026-10-15): their
    # floor-level tiles are the tree's own tiles, floor included, not a picture
    # laid over the floor that is there. Every object stands on the height of
    # the tile clicked and builds up from it.
    whole_floor = style.get('category') == 'trees'
    cut = {} if whole_floor else (style.get('cut') or {})
    keep = (KEEP_FLOOR,) if style.get('v') == ROW_VERSION or style.get('builtin') else (KEEP_FLOOR, 0xFFFF)
    drawn = []   # floor-level pictures drawn over the floor: (x, y, words)
    codes = []
    for dx, dy, v, walls in rows:
        if v[4] not in (0xFFFF, KEEP_FLOOR) and (not raised or v[3] > 0 or not layer or whole_floor):
            codes.append(v[4])
        if raised and walls:
            codes.extend(c for c in walls[1] if c != 0xFFFF)
    mapping = {}
    if codes and style['map'] != target:
        try:
            mapping = import_tiles(session, database, target, style['map'], codes, defer=True, original=not style.get('user'))
        except ValueError as error:
            if 'padding space' not in str(error) and 'No unused blank' not in str(error):
                raise
            mapping = import_tiles(session, database, target, style['map'], codes, erase_unused=True, defer=True, original=not style.get('user'))
    remap = lambda code: code if code in (0xFFFF, KEEP_FLOOR) else mapping.get(code, code)
    changed = []
    for dx, dy, v, walls in rows:
        x, y = ax + dx, ay + dy
        if not (0 <= x < w and 0 <= y < h):
            continue
        cell = cells[y * w + x]; old = list(cell['values'])
        own = (walls[0], [remap(c) for c in walls[1]]) if walls else None
        if not raised:
            if v[4] not in (0xFFFF, KEEP_FLOOR):
                old[4] = remap(v[4]); cell['values'] = tuple(old)
        elif v[3] > 0:
            top = old[4] if v[4] in keep else remap(v[4])   # floor-only tiles keep the floor already there
            cell['values'] = (v[0], v[1], v[2], max(0, min(255, base + v[3])), top, -1)
            cell['walls'] = own
        else:   # a floor-level tile of the object
            old[0] = v[0] | (old[0] & 0x40); old[3] = base
            if v[4] not in (0xFFFF, KEEP_FLOOR):
                if whole_floor:   # the tree's own floor tile
                    old[4] = remap(v[4])
                elif layer:   # its picture over the floor that is there
                    from heal_tile import tile_words
                    words = cut.get((dx, dy)) or tile_words(session, style['map'], v[4])
                    drawn.append((x, y, list(words)))
                else:
                    old[4] = remap(v[4])
            cell['values'] = tuple(old)
            cell['walls'] = merge_walls(cell.get('walls'), own) if layer else (own or cell.get('walls'))
        changed.append((x, y))
    if drawn:
        from heal_tile import compose_in_editor
        compose_in_editor(session, target, drawn, grid)
    return changed


def object_category(document, style):
    """The tab an object shows in: 'trees', or one of the Map Objects sub-tabs
    (CATEGORIES). A right-click in the tile picker moves it (kept in
    document['map_object_categories'])."""
    chosen = (document.get('map_object_categories') or {}).get(style.get('key'))
    if chosen in CATEGORY_NAMES:
        return chosen
    if chosen == 'rugs':
        return 'other'
    auto = style.get('category')
    if chosen == 'objects' and auto == 'trees':
        return 'other'           # moved out of Trees before the sub-tabs existed
    if auto in CATEGORY_NAMES:
        return auto
    return 'other'


# The save rooms' warp panel (map 452, tiles 14-15, 16-17; its two warp
# records there lead out of the room): placed like a map object, drawn over
# the floor it is put on, then a warp is put on its four tiles.
WARP_PANEL_MAP = 452
WARP_PANEL_TILES = ((0, 0, 14, 16), (1, 0, 15, 16), (0, 1, 14, 17), (1, 1, 15, 17))
WARP_PANEL_FLAGS = 85     # the save room panel's own warp flags


def builtin_objects(session):
    """Objects listed first in Map Objects: the Warp Panel."""
    cache = getattr(session, '_builtin_map_objects', None)
    if cache is not None:
        return cache
    from area_map import MapRenderer
    from PIL import Image
    w, h, cells = _cells(session, WARP_PANEL_MAP)
    renderer = MapRenderer(session, WARP_PANEL_MAP)
    rows = []
    image = Image.new('RGBA', (48, 32), (0, 0, 0, 0))
    for dx, dy, x, y in WARP_PANEL_TILES:
        code = cells[y * w + x]['values'][4]
        rows.append((dx, dy, (0, 0, 0, 0, code), None))
        image.alpha_composite(renderer.tile(code).convert('RGBA'), (dx * 24, dy * 16))
    cache = [dict(key='builtin:warp_panel', kind='panel', map=WARP_PANEL_MAP, rows=rows, image=image,
                  name='Warp Panel', warp_panel=True, builtin=True, uses=0, maps=[WARP_PANEL_MAP])]
    try:
        session._builtin_map_objects = cache
    except AttributeError:
        pass
    return cache
