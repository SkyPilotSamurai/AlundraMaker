"""Water and Lava tabs of the tile picker (user request 2026-10-15).

Every kind of water and lava of the original game, one block per kind: a 3x3
square with the plain water / lava tile in the centre and the edge tiles
around it as they sit in the game (top edge on top, top-left corner top left,
and so on), and beside it everything else drawn on that water or lava -
grass, rocks, inner corners, other patterns of the same surface.

Water is the tile record's water marking (water_catalogue.is_water). Lava is
a floor picture on an animated tile page that is mostly orange (lava is not
marked in the tile record: walkability 128 / ground 0 or 16 / slope 4, the same
as some ordinary floors).

What a square looks like is taken from the screen, as the game draws it: the
water / lava floor plus every piece drawn over that square afterwards (lava
edges are wall pieces of the rock next to it that hang over the lava). A tile
is put in the 3x3 by which of its four neighbours are not the same liquid.
Kinds: the plain tiles of one area; areas sharing a plain picture are one kind.

Painting a tile gives the map tile the liquid picture with its walkability,
ground and slope (the height stays), and the pieces drawn over it become
pieces of that tile on its floor (added to its own wall stack)."""
import hashlib
from collections import Counter

SLOTS = ('nw', 'n', 'ne', 'w', 'c', 'e', 'sw', 's', 'se')
_SIDES = {frozenset(): 'c', frozenset('n'): 'n', frozenset('s'): 's', frozenset('w'): 'w', frozenset('e'): 'e',
          frozenset('nw'): 'nw', frozenset('ne'): 'ne', frozenset('sw'): 'sw', frozenset('se'): 'se'}
CACHE_VERSION = 33


def _hot(image):
    """Share of orange-red pixels."""
    px = [p for p in image.getdata() if p[3]]
    if not px:
        return 0.0
    return sum(1 for r, g, b, a in px if r > 90 and g < r * 0.8 and b < r * 0.45) / len(px)


def _anim_pages(session, m):
    from tile_anims import animations
    try:
        return {a['page'] for a in animations(session, m)}
    except Exception:
        return set()


def map_liquids(session, m):
    """[(liquid, x, y, values, floor code, overlay codes, image)] for every
    water / lava tile of map m, plus (w, h) and a liquid lookup."""
    from area_map import MapRenderer, grid
    from water_catalogue import is_water
    w, h, cells = grid(session, m)
    pages = _anim_pages(session, m)
    renderer = None
    hot = {}
    kind = {}
    for c in cells:
        v = c['values']
        if v[4] == 0xFFFF:
            continue
        if is_water(v):
            kind[(c['x'], c['y'])] = 'water'
        elif v[0] == 24 and (v[1] & 15) == 6:   # sand you sink in (Despair Desert; user 2026-10-18: Sand tab)
            kind[(c['x'], c['y'])] = 'sand'
        elif pages and (v[4] & 1023) // 160 in pages:
            if v[4] not in hot:
                if renderer is None:
                    renderer = MapRenderer(session, m)
                hot[v[4]] = _hot(renderer.tile(v[4]).convert('RGBA'))
            if hot[v[4]] > 0.3:
                kind[(c['x'], c['y'])] = 'lava'
    lava = [hot[cells[y * w + x]['values'][4]] for (x, y), k in kind.items() if k == 'lava']
    if lava and sum(lava) / len(lava) < 0.58:   # lamps / grates on an animated page, not lava
        kind = {at: k for at, k in kind.items() if k != 'lava'}
    # Spikes (user 2026-10-21): every other floor that hurts the player. US 0x8003207C takes the
    # damage from tile flag bits 0x180 of the tiles under his feet: walk byte 0x80, ground byte 0x01
    for c in cells:
        v = c['values']
        if v[4] != 0xFFFF and (c['x'], c['y']) not in kind and (v[0] & 0x80 or v[1] & 1):
            if v[4] not in hot:
                if renderer is None:
                    renderer = MapRenderer(session, m)
                hot[v[4]] = _hot(renderer.tile(v[4]).convert('RGBA'))
            if hot[v[4]] > 0.1:
                continue   # lava (and its edges) hurts too, but it is not a spike (user 2026-10-21)
            kind[(c['x'], c['y'])] = 'spikes'
    if not kind:
        return w, h, kind, []
    if renderer is None:
        renderer = MapRenderer(session, m)
    # what lands on each screen square, in the game's drawing order
    squares = {}
    order = 0
    for c in cells:
        v = c['values']; x, y = c['x'], c['y']; top = y - v[3]
        squares.setdefault((x, top), []).append((order, v[4], 'floor', (x, y))); order += 1
        if c['walls']:
            shift = c['walls'][0][2]
            for i, (_, code, _, _) in enumerate(c['walls']):
                squares.setdefault((x, top + i + 1 - shift), []).append((order, code, 'wall', (x, y))); order += 1
    # shore: tiles next to water / lava that are not marked as it but show it
    # in their picture (grass with the water's edge drawn in, outside the
    # Reptile Lair and elsewhere); kept only if the picture has its colours
    shore = {}; touching = {}
    for c in cells:
        where = (c['x'], c['y'])
        if where in kind or c['values'][4] == 0xFFFF:
            continue
        # up to two tiles away: rock banks can be two tiles thick (south shore of map 16)
        near = Counter(kind[(c['x'] + dx, c['y'] + dy)] for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)
                       if (c['x'] + dx, c['y'] + dy) in kind and kind[(c['x'] + dx, c['y'] + dy)] != 'spikes')   # no shore for spikes
        if near:
            shore[where] = near.most_common(1)[0][0]
            touching[where] = any((c['x'] + dx, c['y'] + dy) in kind for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    out = []
    for c in cells:
        where = (c['x'], c['y'])
        if where not in kind and where not in shore:
            continue
        v = c['values']; square = squares.get((c['x'], c['y'] - v[3]), [])
        mine = next((o for o, code, what, owner in square if what == 'floor' and owner == where), None)
        over = [code for o, code, what, owner in square if mine is not None and o > mine and code != 0xFFFF]
        try:
            base = renderer.tile(v[4]).convert('RGBA')
            image = base.copy()
            for code in over:
                image.alpha_composite(renderer.tile(code).convert('RGBA'))
        except Exception:
            continue
        out.append((kind.get(where) or shore[where], c['x'], c['y'], tuple(v[:3]), v[4], over, image,
                    hashlib.sha1(base.tobytes()).hexdigest(), where in shore))
    # colours only the water of this map uses (in no dry tile further from it):
    # the shallow water drawn into a bank tile is found by them
    wet_colours = set()
    for t in out:
        if not t[8] and t[0] != 'lava':
            wet_colours.update(p[:3] for p in t[6].getdata() if p[3])
    if wet_colours:
        dry = set(); codes = set()   # each tile picture read once (speed): the same colours as before
        for c in cells:
            where = (c['x'], c['y'])
            if where in kind or where in shore or c['values'][4] == 0xFFFF:
                continue
            codes.add(c['values'][4])
        for code in codes:
            dry.update(p[:3] for p in renderer.tile(code).getdata() if p[3])
        only = wet_colours - dry
        out = [t + ([bool(p[3]) and p[:3] in only for p in t[6].getdata()],) if t[8] else t + (None,) for t in out]
    else:
        out = [t + (None,) for t in out]
    out = [t + (touching.get((t[1], t[2]), False),) for t in out]
    return w, h, kind, out


def _all_same(liquid, x, y, w, h, kind):
    """All 8 neighbours are the same liquid (or off the map)."""
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            nx, ny = x + dx, y + dy
            if (dx or dy) and 0 <= nx < w and 0 <= ny < h and kind.get((nx, ny)) != liquid:
                return False
    return True


def _picture_slot(image, colours):
    """Where a picture goes, from which of its sides are not the liquid
    (pixels in the kind's plain colours): 'c', an edge / corner, or 'other'."""
    px = list(image.getdata())
    wet = [bool(p[3]) and p[:3] in colours for p in px]
    if sum(wet) / len(wet) >= 0.97:
        return 'c'
    def share(x0, y0, x1, y1):
        cells = [wet[y * 24 + x] for y in range(y0, y1) for x in range(x0, x1)]
        return sum(cells) / len(cells)
    # the outer 4 pixels on each side
    band = {'n': share(0, 0, 24, 3), 's': share(0, 13, 24, 16), 'w': share(0, 0, 4, 16), 'e': share(20, 0, 24, 16)}
    opposite = {'n': 's', 's': 'n', 'w': 'e', 'e': 'w'}
    # a side is land when its whole border is dry and the border across is wet
    # (a straight edge: diagonals and patches go beside the square)
    dry = frozenset(s for s, v in band.items() if v < 0.15 and band[opposite[s]] > 0.6)
    slot = _SIDES.get(dry)
    return slot if dry and slot else 'other'


WIDTH = 10   # picker columns
PARTS = (('main', 'Main'), ('edges', 'Edges'), ('other', 'Other'))


_PALETTES = {}


def _palette_array(colours):
    import numpy as np
    key = id(colours)
    if key not in _PALETTES:
        _PALETTES[key] = (colours, np.array(sorted(colours), dtype=np.int32).reshape(-1, 3))
    return _PALETTES[key][1]


def _part(row, colours):
    """'main' (all water / lava), 'edges' (water / lava with land along a
    side or in a corner), 'other' (something lying on it), or None (no
    water / lava in the picture)."""
    if row['liquid'] == 'lava':   # any orange-red (lava shows in several palettes)
        # red clearly above green, dark crust included (rock is grey / olive, shadow black)
        wet = [bool(p[3]) and ((p[0] >= 35 and p[0] - p[1] >= 25) or (p[0] > 190 and p[2] < p[0] * 0.6))
               for p in row['image'].getdata()]   # (bright yellow glow too)
    else:
        wet = [bool(p[3]) and p[:3] in colours for p in row['image'].getdata()]
        if row.get('wetmask'):   # a shore tile: its map's water-only colours count too
            wet = [a or b for a, b in zip(wet, row['wetmask'])]
    share = sum(wet) / len(wet)
    if row.get('shore') and share < 0.08:
        # a bank without water in it: rock (grey or grey-brown, not grass, wood or reeds)
        if row['liquid'] == 'lava':
            return None
        grey = sum(1 for p in row['image'].getdata()
                   if p[3] and max(p[:3]) - min(p[:3]) < 45 and 60 < max(p[:3]) < 225) / len(wet)
        return 'edges' if row.get('touches') and grey >= 0.12 else None   # only right next to the water
    if share < 0.02:
        return None
    if share >= 0.93:   # (a few odd pixels or an invisible piece over it: still plain)
        return 'main'
    def dry(x0, y0, x1, y1):
        cells = [wet[y * 24 + x] for y in range(y0, y1) for x in range(x0, x1)]
        return 1 - sum(cells) / len(cells)
    sides = (dry(0, 0, 24, 3), dry(0, 13, 24, 16), dry(0, 0, 3, 16), dry(21, 0, 24, 16))
    corners = (dry(0, 0, 8, 6), dry(16, 0, 24, 6), dry(0, 10, 8, 16), dry(16, 10, 24, 16))
    if max(sides) >= 0.8 or max(corners) >= 0.9:
        return 'edges'
    return 'other'


def _mean(image):
    px = [p for p in image.getdata() if p[3]] or [(0, 0, 0, 0)]
    return tuple(sum(p[i] for p in px) / len(px) for i in range(3))


def _arrange(squares, width=WIDTH, keep=None):
    """Each different picture of a kind once, in a `width`-wide block with no
    empty squares. Filled row by row: each square takes the picture that
    fits best against the one on its left and the one above - first pictures
    that sit that way round in the game (how often), then pictures whose
    touching edge pixels match. Starts from the most used plain tile.
    Returns (tiles, [(x, y, index into tiles)], (w, h))."""
    import numpy as np
    from collections import defaultdict
    index = {}; tiles = []; count = Counter(); right = defaultdict(Counter); down = defaultdict(Counter)
    def ix(row):
        if id(row) not in index:
            index[id(row)] = len(tiles); tiles.append(row)
        return index[id(row)]
    if keep is not None:   # only these pictures (ids of rows)
        squares = {m: {k: v for k, v in here.items() if id(v) in keep} for m, here in squares.items()}
    for here in squares.values():
        for (x, r), row in here.items():
            i = ix(row); count[i] += 1
            other = here.get((x + 1, r))
            if other is not None and other is not row:
                right[i][ix(other)] += 1
            other = here.get((x, r + 1))
            if other is not None and other is not row:
                down[i][ix(other)] += 1
    n = len(tiles)
    if not n:
        return tiles, [], (width, 0)
    px = np.stack([np.asarray(t['image'].convert('RGB'), dtype=np.float32) for t in tiles])   # n, 16, 24, 3
    left_edge, right_edge = px[:, :, 0, :], px[:, :, -1, :]
    top_edge, bottom_edge = px[:, 0, :, :], px[:, -1, :, :]
    free = np.ones(n, bool)
    # tiles that are a mirror of each other go side by side
    from PIL import ImageOps
    looks = {}
    for i, t in enumerate(tiles):
        looks.setdefault(t['image'].tobytes(), i)
    mirror = {}
    for i, t in enumerate(tiles):
        for flip in (ImageOps.mirror, ImageOps.flip):
            j = looks.get(flip(t['image']).tobytes())
            if j is not None and j != i and i not in mirror:
                mirror[i] = j
    plain = [i for i in range(n) if tiles[i].get('plain')]
    first = max(plain or range(n), key=lambda i: count[i])
    w = min(width, n); h = (n + w - 1) // w
    grid = {}; layout = []
    for k in range(n):
        x, y = k % w, k // w
        previous = layout[-1][2] if layout else None
        if k == 0:
            pick = first
        elif previous in mirror and free[mirror[previous]]:
            pick = mirror[previous]
        else:
            cost = np.zeros(n, np.float32); bonus = np.zeros(n, np.float32)
            if x > 0:
                a = grid[(x - 1, y)]
                cost += np.abs(left_edge - right_edge[a]).mean(axis=(1, 2))
                for j, c in right[a].items():
                    bonus[j] += c
            if y > 0:
                a = grid[(x, y - 1)]
                cost += np.abs(top_edge - bottom_edge[a]).mean(axis=(1, 2))
                for j, c in down[a].items():
                    bonus[j] += c
            cost = cost - 40 * np.log1p(bonus)
            cost[~free] = np.inf
            pick = int(np.argmin(cost))
        free[pick] = False; grid[(x, y)] = pick; layout.append((x, y, pick))
    return tiles, layout, (w, h)


SAMPLE_W, SAMPLE_H = 10, 8


def _sample(squares, drawn, shown=frozenset()):
    """The most varied SAMPLE_W x SAMPLE_H screen window of a kind: on the map
    where it shows the most different tiles, with land around them. Returns
    {'map', 'rect': (x, screen row, w, h), 'tiles': [(dx, dy, row)]}."""
    best = None
    for m, here in squares.items():
        w, painted = drawn[m]
        if not here:
            continue
        sw = min(SAMPLE_W, w)
        rows_used = [r for _, r in painted] or [0]
        lo, hi = min(rows_used), max(rows_used)
        sh = min(SAMPLE_H, hi - lo + 1)
        xs = sorted({x for x, _ in here}); rs = sorted({r for _, r in here})
        for x0 in range(max(0, xs[0] - sw + 1), min(w - sw, xs[-1]) + 1, 2):
            for r0 in range(max(lo, rs[0] - sh + 1), min(hi - sh + 1, rs[-1]) + 1, 2):
                inside = [here[(x, r)] for x in range(x0, x0 + sw) for r in range(r0, r0 + sh) if (x, r) in here]
                if not inside:
                    continue
                total = sw * sh
                void = sum(1 for x in range(x0, x0 + sw) for r in range(r0, r0 + sh) if (x, r) not in painted)
                kinds = len({id(t) for t in inside if id(t) not in shown}); share = len(inside) / total
                score = kinds + 0.05 * len(inside) - 0.5 * void
                if not 0.3 <= share <= 0.8:
                    score *= 0.5
                if best is None or score > best[0]:
                    best = (score, m, x0, r0, sw, sh)
    if best is None:
        return None
    _, m, x0, r0, sw, sh = best
    here = squares[m]
    tiles = [(x - x0, r - r0, here[(x, r)]) for x in range(x0, x0 + sw) for r in range(r0, r0 + sh) if (x, r) in here]
    return dict(map=m, rect=(x0, r0, sw, sh), tiles=tiles)


SAMPLES = 3


def _samples(squares, drawn):
    """Up to SAMPLES map pieces, each picked for the tiles the ones before it
    do not show; one that would add fewer than 4 is left out."""
    out, shown = [], set()
    while len(out) < SAMPLES:
        sample = _sample(squares, drawn, shown)
        if sample is None:
            break
        new = {id(r) for _, _, r in sample['tiles']} - shown
        if out and len(new) < 4:
            break
        out.append(sample); shown |= new
        x0, r0, sw, sh = sample['rect']   # not the same piece again
        squares = {m: ({k: v for k, v in here.items() if not (x0 <= k[0] < x0 + sw and r0 <= k[1] < r0 + sh)}
                       if m == sample['map'] else here) for m, here in squares.items()}
    return out


def liquid_styles(session, maps=None):
    """{'water': [kind, ...], 'lava': [kind, ...]}; a kind is {'name',
    'centres': [row, ...] (the plain tiles, most used first), 'slots':
    {slot: [row, ...]} (edges and corners, most used first), 'extra': [row,
    ...], 'uses', 'maps'}. Rows are paintable styles (kind 'liquid')."""
    from area_map import grid as map_grid
    rows = {}           # picture key -> row
    areas = []          # (liquid, plain bases, all bases, [key], map, plain count, [(x, screen row, key)])
    drawn = {}          # map -> (w, screen squares with a picture)
    for m in (range(0, 483) if maps is None else maps):
        try:
            w, h, kind, tiles = map_liquids(session, m)
        except Exception:
            continue
        if not tiles:
            continue
        _, _, cells = map_grid(session, m)
        squares = set()
        for c in cells:
            top = c['y'] - c['values'][3]
            if c['values'][4] != 0xFFFF:
                squares.add((c['x'], top))
            if c['walls']:
                shift = c['walls'][0][2]
                squares.update((c['x'], top + i + 1 - shift) for i, (_, code, _, _) in enumerate(c['walls']) if code != 0xFFFF)
        drawn[m] = (w, squares)
        info = {}; shores = []
        for liquid, x, y, values, code, over, image, base, on_shore, wetmask, touches in tiles:
            key = (liquid, hashlib.sha1(image.tobytes()).hexdigest(), values)
            row = rows.get(key)
            if row is None:
                row = rows[key] = dict(kind='liquid', liquid=liquid, map=m, x=x, y=y, code=code, over=list(over),
                                       walk=values[0], ground=values[1], slope=values[2], image=image, uses=0,
                                       key=f'{liquid}:{m}:{x}:{y}', plain=0)
            row['uses'] += 1
            if on_shore:
                row['shore'] = True
                if wetmask is not None:
                    row['wetmask'] = wetmask
                row['touches'] = row.get('touches') or touches
                shores.append((liquid, x, y, key, y - cells[y * w + x]['values'][3])); continue
            plain = not over and _all_same(liquid, x, y, w, h, kind)
            if plain:
                row['plain'] += 1
            info[(x, y)] = (liquid, plain, key, base, y - cells[y * w + x]['values'][3])
        seen = set(); area_of = {}
        for start, (liquid, _, _, _, _) in info.items():
            if start in seen:
                continue
            stack = [start]; seen.add(start); members = []
            while stack:
                x, y = stack.pop(); members.append(info[(x, y)] + (x,)); area_of[(x, y)] = len(areas)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if (nx, ny) not in seen and (nx, ny) in info and info[(nx, ny)][0] == liquid:
                        seen.add((nx, ny)); stack.append((nx, ny))
            areas.append((liquid, {(liquid, b) for _, p, _, b, _, _ in members if p},
                          {(liquid, b) for _, _, _, b, _, _ in members}, [k for _, _, k, _, _, _ in members], m,
                          sum(1 for _, p, _, _, _, _ in members if p),
                          [(x, r, k) for _, _, k, _, r, x in members]))
        for liquid, x, y, key, r in shores:   # a shore tile goes with the water it touches
            near = next((area_of[(x + dx, y + dy)] for dx in (-1, 0, 1, -2, 2) for dy in (-1, 0, 1, -2, 2)
                         if (x + dx, y + dy) in area_of and areas[area_of[(x + dx, y + dy)]][0] == liquid), None)
            if near is not None:
                areas[near][3].append(key); areas[near][6].append((x, r, key))
    # areas sharing an open-water (plain) floor picture are one kind; areas
    # without open water join the kind whose plain floor they use
    parent = list(range(len(areas)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    owner = {}
    for i, (_, plain, _, _, _, _, _) in enumerate(areas):
        for b in plain:
            if b in owner:
                parent[root(i)] = root(owner[b])
            else:
                owner[b] = i
    for i, (liquid, plain, bases, _, m, _, _) in enumerate(areas):
        if not plain:
            shared = next((owner[b] for b in bases if b in owner), None)
            if shared is None:   # else the biggest open area of that liquid on the same map
                near = [j for j, a in enumerate(areas) if a[4] == m and a[0] == liquid and a[5]]
                shared = max(near, key=lambda j: areas[j][5]) if near else None
            if shared is not None:
                parent[root(i)] = root(shared)
    groups = {}
    for i, area in enumerate(areas):
        groups.setdefault(root(i), []).append(area)
    out = {'water': [], 'lava': [], 'sand': [], 'spikes': []}
    for members in groups.values():
        liquid = members[0][0]
        uses = Counter()
        for _, _, _, keys, _, _, _ in members:
            uses.update(keys)
        # one row per picture (its most used logic)
        best = {}
        for key, n in uses.most_common():
            b = rows[key]['image'].tobytes()
            if b not in best:
                best[b] = key
        keys = list(best.values())
        plain_keys = [k for k in keys if rows[k]['plain']]
        colours = Counter()
        for k in plain_keys:
            colours.update(p[:3] for p in rows[k]['image'].getdata() if p[3])
        if not colours:   # no open water / lava: the most used picture's colours
            colours.update(p[:3] for p in rows[keys[0]]['image'].getdata() if p[3])
        colours = {c for c, n in colours.items() if n >= 2} or set(colours)
        slots = {s: [] for s in SLOTS}; extra = []; dry = []
        for k in keys:
            row = rows[k]
            slot = 'c' if row['plain'] else _picture_slot(row['image'], colours) if colours else 'other'
            if slot == 'c' and row['over']:
                slot = 'other'
            if slot == 'other':
                wet = sum(1 for p in row['image'].getdata() if p[3] and p[:3] in colours) / 384
                (extra if wet >= 0.05 else dry).append(row)   # all covered: last
            else:
                slots[slot].append(row)
        centres = slots.pop('c')
        def light(row):
            px = [p for p in row['image'].getdata() if p[3]] or [(0, 0, 0, 0)]
            return round(sum(p[0] + p[1] + p[2] for p in px) / len(px) / 24)
        centres.sort(key=light)   # like shades together
        maps_used = sorted({rows[k]['map'] for k in uses})
        # the picture shown for each key: its deduplicated row
        shown = {k: rows[best[rows[k]['image'].tobytes()]] for k in uses}
        squares = {}
        for a in members:
            for x, r, k in a[6]:
                here = squares.setdefault(a[4], {})
                if rows[k].get('shore') and (x, r) in here:
                    here[(x + 0.5, r)] = shown[k]   # never hides a water / lava tile on that screen square; kept, unpaired
                    continue
                here[(x, r)] = shown[k]
        # Main (only water / lava), Edges (water / lava and the land at its
        # side or corner), Other (things on it); pictures without any are left out
        parts = {'main': set(), 'edges': set(), 'other': set()}
        for row in {id(r): r for r in shown.values()}.values():
            part = _part(row, colours)
            if part:
                parts[part].add(id(row))
        groups = {}
        for part, ids in parts.items():
            if ids:
                tiles, layout, size = _arrange(squares, keep=ids)
                groups[part] = dict(tiles=tiles, layout=layout, size=size)
        out[liquid].append(dict(liquid=liquid, uses=sum(uses.values()), maps=maps_used, groups=groups))
    # ice: water kinds whose open water is pale and grey-white
    import colorsys
    out['ice'] = []
    for k in list(out['water']):
        main = [r for r in k['groups'].get('main', {}).get('tiles') or [] if not r.get('shore')]
        px = [p for r in main for p in r['image'].getdata() if p[3]]
        if px:
            mean = [sum(p[i] for p in px) / len(px) / 255 for i in range(3)]
            hue, sat, val = colorsys.rgb_to_hsv(*mean)
            # snow-white, or light sky-blue ice (Elene's dream, maps 49-50)
            if (val > 0.66 and sat < 0.15) or (0.53 <= hue <= 0.64 and val > 0.45):   # snow-white (the pale lake outside the Reptile Lair stays water)
                out['water'].remove(k); out['ice'].append(k); k['liquid'] = 'ice'
    # icy tiles left in water kinds (a kind mixing ice and water): moved one by
    # one to an ice kind of their own, keeping their order
    def icy(row):
        px = [p for p in row['image'].getdata() if p[3]]
        if not px:
            return False
        bright = sum(1 for p in px if min(p[:3]) > 175 and max(p[:3]) - min(p[:3]) < 40 and p[2] >= p[0])   # snow: bright, blue-white (not beige stone)
        return bright / len(px) > 0.5
    for k in list(out['water']):
        moved = {}
        for part, g in list(k['groups'].items()):
            order = [g['tiles'][i] for _, _, i in sorted(g['layout'], key=lambda t: (t[1], t[0]))]
            cold = [r for r in order if icy(r)]
            if not cold:
                continue
            warm = [r for r in order if not icy(r)]
            for target, rows_ in ((moved, cold), (k['groups'], warm)):
                if rows_:
                    target[part] = dict(tiles=rows_, layout=[(i % WIDTH, i // WIDTH, i) for i in range(len(rows_))],
                                        size=(WIDTH, (len(rows_) + WIDTH - 1) // WIDTH))
                elif target is k['groups']:
                    del k['groups'][part]
        if moved:
            out['ice'].append(dict(liquid='ice', uses=k['uses'], maps=k['maps'], groups=moved))
            if not k['groups']:
                out['water'].remove(k)
    # 'lava' without any open lava is a lamp or torch on an animated page
    out['lava'] = [k for k in out['lava'] if len(k['groups'].get('main', {}).get('tiles', ())) >= 2]
    # spikes: kinds with a plain spike floor (single damaging edge pieces are not a kind of their own)
    def tips(k):   # share of light, low-colour pixels (the points of the spikes); dirt and dark ground have none
        px = [p for r in k['groups']['main']['tiles'] for p in r['image'].getdata() if p[3]]
        return sum(1 for p in px if max(p[:3]) > 110 and (max(p[:3]) - min(p[:3])) / max(p[:3]) < 0.45) / max(1, len(px))
    out['spikes'] = [k for k in out['spikes'] if len(k['groups'].get('main', {}).get('tiles', ())) >= 2 and k['uses'] >= 4 and tips(k) > 0.004]
    for liquid in out:
        out[liquid].sort(key=lambda k: -k['uses'])
        for n, k in enumerate(out[liquid], 1):
            k['name'] = f"{liquid.capitalize()} {n}"
    return out


def _pack_sample(sample, pack):
    if not sample or 'image' not in sample:
        return None
    from io import BytesIO
    b = BytesIO(); sample['image'].save(b, 'PNG')
    return dict(sample, image=b.getvalue(), tiles=[(x, y, pack(r)) for x, y, r in sample['tiles']])


def cached_liquid_styles(session, rescan=False):
    """liquid_styles() of the original game, kept on the session and on disk."""
    import pickle
    from io import BytesIO
    from pathlib import Path
    from PIL import Image
    styles = getattr(session, '_liquid_styles', None)
    if styles is not None and not rescan:
        return styles
    from stock_source import catalogue_base
    original = catalogue_base(session)   # this computer's original game (2026-10-16)
    digest = hashlib.sha256(original).hexdigest()[:16]
    cache = Path(__file__).resolve().parents[1] / 'game' / 'editor-cache' / f'liquid-styles-v{CACHE_VERSION}-{digest}.pickle'
    def pack(row):
        b = BytesIO(); row['image'].save(b, 'PNG'); return dict(row, image=b.getvalue())
    def unpack(row):
        row['image'] = Image.open(BytesIO(row['image'])).convert('RGBA'); return row
    if not rescan:
        try:
            data = pickle.loads(cache.read_bytes())
            for kinds in data.values():
                for k in kinds:
                    for g in (k.get('groups') or {}).values():
                        g['tiles'] = [unpack(r) for r in g['tiles']]
            session._liquid_styles = data
            return data
        except Exception:
            pass
    from editor_session import EditSession
    source = session if original == bytes(session.data) else EditSession(original, verify=False)
    styles = liquid_styles(source)
    session._liquid_styles = styles
    try:
        data = {liquid: [dict(k, groups={p: dict(g, tiles=[pack(r) for r in g['tiles']]) for p, g in k['groups'].items()})
                         for k in kinds] for liquid, kinds in styles.items()}
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps(data))
    except Exception:
        pass
    return styles


def place_liquid(session, database, target, tiles, style, grid=None):
    """Give each tile the liquid picture, walkability, ground and slope (the
    height stays); the pieces drawn over it in the game are laid on its floor."""
    from map_tile_import import import_tiles
    from bush_catalogue import _cells, _store
    from map_object_catalogue import merge_walls
    tiles = list(dict.fromkeys(tiles)); label = f"Place {style.get('liquid', 'water')} on {len(tiles)} tile(s)"
    codes = [style['code']] + [c for c in style.get('over', []) if c != 0xFFFF]
    with session.group(label):
        mapping = {}
        if style['map'] != target:
            try:
                mapping = import_tiles(session, database, target, style['map'], codes, defer=True, original=True)
            except ValueError as error:
                if 'padding space' not in str(error) and 'No unused blank' not in str(error):
                    raise
                mapping = import_tiles(session, database, target, style['map'], codes, erase_unused=True, defer=True, original=True)
        remap = lambda c: mapping.get(c, c)
        over = [remap(c) for c in style.get('over', [])]
        w, h, cells = _cells(session, target, grid); changed = 0
        for x, y in tiles:
            if 0 <= x < w and 0 <= y < h:
                cell = cells[y * w + x]; v = list(cell['values'])
                v[0], v[1], v[2], v[4] = style['walk'],style['ground'], style['slope'], remap(style['code'])
                cell['values'] = tuple(v)
                # pieces on the floor square (offset 0) are replaced by this tile's overlay
                walls = cell.get('walls')
                if walls:
                    shift, stack = walls
                    keep = [(i + 1 - shift, c) for i, c in enumerate(stack) if i + 1 - shift != 0 and c != 0xFFFF]
                    if keep:
                        top = min(o for o, _ in keep); last = max(o for o, _ in keep); d = dict(keep)
                        walls = (1 - top, [d.get(o, 0xFFFF) for o in range(top, last + 1)])
                    else:
                        walls = None
                if over:
                    # several pieces on one square: only the last drawn shows on top
                    pieces = (1, [over[-1]]) if len(over) == 1 else None
                    if pieces is None:
                        walls = merge_walls(walls, (1, [over[-1]]))
                    else:
                        walls = merge_walls(walls, pieces)
                cell['walls'] = walls
                changed += 1
        if changed:
            _store(session, target, grid, cells, label)
    return changed


def library_picture(kinds, part='main', columns=WIDTH):
    """Picker picture of one sub-tab (part: main / edges / other), one band
    per kind that has such pictures: its name, then each picture once, next
    to the pictures it touches in the game (see _arrange), no empty squares.
    Returns (image, [(x, y, w, h, row)])."""
    from PIL import Image, ImageDraw
    label = 14
    width = columns * 24
    shown = [(k, k['groups'][part]) for k in kinds if part in k.get('groups', {})]
    bands = [label + g['size'][1] * 16 + 10 for _, g in shown]
    image = Image.new('RGBA', (width, max(1, sum(bands))), (31, 34, 40, 255))
    draw = ImageDraw.Draw(image); hits = []; top = 0
    for (k, g), band in zip(shown, bands):
        draw.text((2, top + 1), f"{k['name']}  ({len(g['tiles'])} tiles, used on {len(k.get('maps') or [])} map(s))",
                  fill=(200, 205, 215, 255))
        y0 = top + label
        for x, y, i in g['layout']:
            row = g['tiles'][i]
            image.alpha_composite(row['image'], (x * 24, y0 + y * 16)); hits.append((x * 24, y0 + y * 16, 24, 16, row))
        top += band
    return image, hits
