"""Trees for the tile picker's Trees tab: the whole tree - crown, trunk, its
foot with the roots and the shadow it throws on the floor - without the floor
around it.

How the game builds a standing tree: a row of 2-4 floor tiles (the tree's
foot) each carrying a tall stack of pieces drawn above the floor (trunk and
crown), with raised, blocking tiles right behind them (what Alundra bumps
into). The roots and the shadow are painted into floor pictures: the foot's
own tiles and the ones beside and in front of it.

A floor picture of the tree keeps only what is not floor: pixels with the
map's main floor colours (or one shade away, the tree's own palette copy of
the grass) become see-through, so the roots and the darker shadow stay and
the grass goes. Placed with Layer On Top, those pictures are drawn over the
floor of the map they are put on.
"""
from collections import Counter, defaultdict



def _cells(session, m):
    from area_map import grid
    return grid(session, m)


def _green(image):
    pixels = [p for p in image.getdata() if p[3]]
    if not pixels:
        return 0
    return sum(1 for r, g, b, a in pixels if g >= r - 6 and g > b + 15 and g > 40) / len(pixels)   # leaves: green to olive


def _stone(image):
    """Grey stone and boards (walls, fences): light and colourless."""
    pixels = [p for p in image.getdata() if p[3]]
    return sum(1 for r, g, b, a in pixels if max(r, g, b) - min(r, g, b) < 24 and r + g + b > 240) / len(pixels) if pixels else 0


def _bright(image):
    pixels = [p for p in image.getdata() if p[3]]
    return sum(1 for r, g, b, a in pixels if r + g + b > 450) / len(pixels) if pixels else 0


class _Map:
    def __init__(self, session, m, renderer=None):
        from area_map import MapRenderer
        self.session, self.m = session, m
        self.w, self.h, self.cells = _cells(session, m)
        self.renderer = renderer or MapRenderer(session, m)
        self._green = {}
        self._words = {}
        # the common floor: pictures of plain floor tiles (no pieces, walkable),
        # the most used ones covering 3/4 of that floor
        count = Counter(c['values'][4] for c in self.cells
                        if not c['walls'] and c['values'][4] != 0xFFFF and not c['values'][0] & 1)
        total = sum(count.values()); acc = 0; self.common = []
        for code, n in count.most_common():
            if n < 3 or (acc > total * 0.75 and len(self.common) >= 3):
                break
            self.common.append(code); acc += n
        self.count = count
        self.pieces = Counter(code for c in self.cells if c['walls'] for _, code, _, _ in c['walls'])
        # every picture on the screen grid: (col, row) -> [(cell index, slot, code)]
        # slot -1 is the floor picture, else the wall piece index
        self.screen = defaultdict(list)
        for i, c in enumerate(self.cells):
            x, y, v = c['x'], c['y'], c['values']
            top = y - v[3]
            if v[4] != 0xFFFF:
                self.screen[(x, top)].append((i, -1, v[4]))
            if c['walls']:
                shift = c['walls'][0][2]
                for k, (_, code, _, _) in enumerate(c['walls']):
                    if code != 0xFFFF:
                        self.screen[(x, top + k + 1 - shift)].append((i, k, code))

    def green(self, code):
        if code not in self._green:
            try:
                self._green[code] = _green(self.renderer.tile(code).convert('RGBA'))
            except Exception:
                self._green[code] = 0
        return self._green[code]

    def stony(self, code):
        """Boards and stone (fences, walls, cliffs): grey and colourless."""
        key = ('stone', code)
        if key not in self._green:
            try:
                image = self.renderer.tile(code).convert('RGBA')
                pixels = [p for p in image.getdata() if p[3]]
                grey = sum(1 for r, g, b, a in pixels if max(r, g, b) - min(r, g, b) < 28)
                self._green[key] = bool(pixels) and grey > 0.5 * len(pixels)
            except Exception:
                self._green[key] = False
        return self._green[key]

    def words(self, code):
        if code not in self._words:
            from heal_tile import tile_words
            self._words[code] = tile_words(self.session, self.m, code)
        return self._words[code]

    def raised(self, i):
        """A tile standing higher than the floor in front of it."""
        c = self.cells[i]; x, y = c['x'], c['y']
        if y + 1 >= self.h:
            return False
        return c['values'][3] > self.cells[(y + 1) * self.w + x]['values'][3]

    def floor_cut(self, code):
        """('floor', None) plain floor, ('cut', words) floor with something
        painted on it (roots, shadow), ('whole', None) not floor at all."""
        refs = [f for f in self.common if f != code]
        if not refs:
            return 'whole', None
        words = self.words(code)
        scored = [(sum(1 for a, b in zip(words, self.words(f)) if a == b), f) for f in refs]
        best = max(s for s, _ in scored)
        if best >= 380:
            return 'floor', None
        # a darker copy of the floor (shadow) shares no pixel: compare brightness too
        def lum(wd):
            return (wd & 31) + ((wd >> 5) & 31) + ((wd >> 10) & 31)
        # the floor's main colours (its scattered dark specks would match a shadow)
        tally = Counter()
        for s, f in scored:
            tally.update(wd for wd in self.words(f) if wd)
        total = sum(tally.values()) or 1
        floor_colours = {wd for wd, n in tally.items() if n >= total * 0.02}
        def rgb(wd):
            return (wd & 31, (wd >> 5) & 31, (wd >> 10) & 31)
        floor_rgb = [rgb(f) for f in floor_colours]
        near = {}
        def is_floor(wd):
            # the same colour, or one a step away (the tree's own palette copy of
            # the grass); a shadow is several steps darker and stays
            if wd not in near:
                r, g, b = rgb(wd)
                near[wd] = wd in floor_colours or any(abs(r - fr) + abs(g - fg) + abs(b - fb) <= 2 for fr, fg, fb in floor_rgb)
            return near[wd]
        out = [0 if wd and is_floor(wd) else wd for wd in words]
        # lone grass specks left in the cleared floor go too
        for k in range(384):
            if out[k]:
                x, y = k % 24, k // 24
                if not any(0 <= x + dx < 24 and 0 <= y + dy < 16 and out[(y + dy) * 24 + x + dx]
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    out[k] = 0
        kept = sum(1 for wd in out if wd)
        if kept < 12:
            return 'floor', None
        if kept > 370:
            return 'whole', None
        return 'cut', out


def tree_rows(mp, base, slots):
    """Rows like map_object_catalogue.object_rows: (dx, dy, values (height above
    base), walls); pieces that are not the tree's are left out (0xFFFF)."""
    cells = [mp.cells[i] for i in slots]
    x0 = min(c['x'] for c in cells); y0 = min(c['y'] for c in cells)
    rows = []
    for i, s in sorted(slots.items(), key=lambda kv: (mp.cells[kv[0]]['y'], mp.cells[kv[0]]['x'])):
        c = mp.cells[i]; v = list(c['values'][:5]); v[3] -= base
        if -1 not in s:
            v[4] = 0xFFFE if not mp.raised(i) else 0xFFFF    # keeps the floor it is put on
        walls = None
        if c['walls']:
            shift = c['walls'][0][2]
            codes = [code if k in s else 0xFFFF for k, (_, code, _, _) in enumerate(c['walls'])]
            if any(code != 0xFFFF for code in codes):
                walls = (shift, codes)
        rows.append((c['x'] - x0, c['y'] - y0, tuple(v), walls))
    return rows


def tree_picture(mp, rows, cuts, where=False):
    """The tree's picture (see-through around it). cuts: {(dx, dy): words}.
    where=True also returns the picture's top-left (left, top) in row pixels."""
    from PIL import Image
    pieces = []
    for dx, dy, v, walls in rows:
        y = dy * 16 - v[3] * 16
        if (dx, dy) in cuts:
            pieces.append((_words_image(cuts[(dx, dy)]), dx * 24, y))
        elif v[4] not in (0xFFFF, 0xFFFE):
            pieces.append((v[4], dx * 24, y))
        if walls:
            shift, codes = walls
            pieces += [(code, dx * 24, y + (k + 1 - shift) * 16) for k, code in enumerate(codes) if code != 0xFFFF]
    if not pieces:
        blank = Image.new('RGBA', (24, 16), (0, 0, 0, 0))
        return (blank, (0, 0)) if where else blank
    left = min(p[1] for p in pieces); top = min(p[2] for p in pieces)
    right = max(p[1] for p in pieces) + 24; bottom = max(p[2] for p in pieces) + 16
    image = Image.new('RGBA', (right - left, bottom - top), (0, 0, 0, 0))
    for code, x, y in pieces:
        tile = code if not isinstance(code, int) else mp.renderer.tile(code).convert('RGBA')
        image.alpha_composite(tile, (x - left, y - top))
    return (image, (left, top)) if where else image


def _main_part(image):
    """The pixels of the picture's biggest joined piece."""
    w, h = image.size; px = image.load()
    opaque = {(x, y) for y in range(h) for x in range(w) if px[x, y][3]}
    best = set(); seen = set()
    for start in opaque:
        if start in seen:
            continue
        part = {start}; stack = [start]; seen.add(start)
        while stack:
            x, y = stack.pop()
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1), (x + 1, y + 1), (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1)):
                if q in opaque and q not in seen:
                    seen.add(q); part.add(q); stack.append(q)
        if len(part) > len(best):
            best = part
    return best


def clean_tree(mp, rows, cuts):
    """Leave out loose bits that are not joined to the tree: specks of a
    shadow, a stone or a flower beside the foot. Cut floor pictures lose those
    pixels; a piece lying wholly outside the tree is dropped."""
    image, (left, top) = tree_picture(mp, rows, cuts, where=True)
    main = _main_part(image)
    new_cuts = {}; new_rows = []
    for dx, dy, v, walls in rows:
        y = dy * 16 - v[3] * 16
        if (dx, dy) in cuts:
            words = list(cuts[(dx, dy)])
            for k in range(384):
                if words[k] and (dx * 24 - left + k % 24, y - top + k // 24) not in main:
                    words[k] = 0
            if any(words):
                new_cuts[(dx, dy)] = words
            else:
                v = tuple(v[:4]) + (0xFFFE,)
        def inside(code, py):
            try:
                pic = mp.renderer.tile(code).convert('RGBA').load()
            except Exception:
                return True
            return any(pic[i, j][3] and (dx * 24 - left + i, py - top + j) in main for j in range(16) for i in range(24))
        if (dx, dy) not in cuts and v[4] not in (0xFFFF, 0xFFFE) and not inside(v[4], y):
            v = tuple(v[:4]) + ((0xFFFE if v[3] == 0 else 0xFFFF),)
        if walls:
            shift, codes = walls
            codes = [c if c == 0xFFFF or inside(c, y + (k + 1 - shift) * 16) else 0xFFFF for k, c in enumerate(codes)]
            walls = (shift, codes) if any(c != 0xFFFF for c in codes) else None
        new_rows.append((dx, dy, v, walls))
    return new_rows, new_cuts


def _words_image(words):
    from PIL import Image
    image = Image.new('RGBA', (24, 16), (0, 0, 0, 0))
    image.putdata([(((w & 31) << 3), (((w >> 5) & 31) << 3), (((w >> 10) & 31) << 3), 255) if w else (0, 0, 0, 0)
                   for w in words])
    return image


def _dark_words(words):
    kept = [w for w in words if w]
    if not kept:
        return False
    lum = sum((w & 31) + ((w >> 5) & 31) + ((w >> 10) & 31) for w in kept) / len(kept)
    return lum < 30          # of 93: shadow and roots, not paths, stones or flowers


def find_standing_trees(session, m, renderer=None):
    """Trees the way the game builds a standing tree: a row of floor tiles (the
    tree's foot) each carrying a tall stack of pieces drawn above the floor (the
    trunk and the crown), with the raised tiles right behind them blocking the way.
    Returns (map view, [(base, {cell: slots}, {cell: words})])."""
    mp = _Map(session, m, renderer)
    def stack_above(c):
        if not c['walls']:
            return []
        shift = c['walls'][0][2]
        return [code for k, (_, code, _, _) in enumerate(c['walls']) if k + 1 - shift < 0 and code != 0xFFFF]
    seeds = {}
    for i, c in enumerate(mp.cells):
        above = stack_above(c)
        if len(above) >= 3 and sum(mp.green(code) for code in above) / len(above) >= 0.25:
            seeds[(c['x'], c['y'])] = i
    found = []; used = set()
    for (x, y) in sorted(seeds, key=lambda p: (p[1], p[0])):
        if (x, y) in used:
            continue
        run = []
        while (x, y) in seeds and len(run) < 6:
            run.append((x, y)); used.add((x, y)); x += 1
        if len(run) not in (2, 3, 4):
            continue
        base = mp.cells[seeds[run[0]]]['values'][3]
        if any(mp.cells[seeds[p]]['values'][3] != base for p in run):
            continue
        member = {seeds[p]: {-1} | set(range(len(mp.cells[seeds[p]]['walls']))) for p in run}
        xs = [p[0] for p in run]; y0 = run[0][1]
        # behind: the raised tiles the trunk stands on (they block), up to 3 rows
        for px in range(min(xs), max(xs) + 1):
            for back in (1, 2, 3):
                if y0 - back < 0:
                    break
                j = (y0 - back) * mp.w + px; c = mp.cells[j]
                if c['values'][3] > base and c['values'][0] & 1:
                    member[j] = {-1} | set(range(len(c['walls'] or [])))
                else:
                    break
        # beside and in front: the foot's edge and the shadow painted on the floor
        for px in range(min(xs) - 1, max(xs) + 2):
            for py in (y0, y0 + 1, y0 + 2):
                if not (0 <= px < mp.w and 0 <= py < mp.h):
                    continue
                j = py * mp.w + px; c = mp.cells[j]
                if j in member or c['values'][3] != base or c['values'][4] == 0xFFFF:
                    continue
                if py > y0 and (px, py - 1) not in {(mp.cells[k]['x'], mp.cells[k]['y']) for k in member}:
                    continue
                kind, words = mp.floor_cut(c['values'][4])
                if kind == 'cut' and mp.count.get(c['values'][4], 0) <= 12 and _dark_words(words):
                    member[j] = {-1}   # roots or shadow: dark; a path or flowers are not
        cut = {}
        for j, s in list(member.items()):
            c = mp.cells[j]
            if c['values'][3] == base and -1 in s and c['values'][4] != 0xFFFF:
                kind, words = mp.floor_cut(c['values'][4])
                if kind == 'floor':
                    s.discard(-1)
                elif kind == 'cut':
                    cut[j] = words
        found.append((base, member, cut, len(run)))
    return mp, found


def find_raised_trees(mp):
    """Trees built as a raised block: its tops are the crown (leaves seen from
    above, blocking the way) and the pieces hanging under it are the crown's
    front and the trunk down to the ground (palms, young trees).
    [(base, {cell: slots}, {cell: words}, width)]"""
    crown = set()
    for i, c in enumerate(mp.cells):
        v = c['values']
        if not (v[0] & 1 and mp.raised(i)):
            continue
        pics = ([v[4]] if v[4] != 0xFFFF else []) + [code for _, code, _, _ in (c['walls'] or []) if code != 0xFFFF]
        if len(pics) >= 2 and sum(mp.green(code) for code in pics) / len(pics) >= 0.5:
            crown.add((c['x'], c['y']))   # leaves seen from above or hanging in front
    found = []; seen = set()
    for start in sorted(crown, key=lambda p: (p[1], p[0])):
        if start in seen:
            continue
        group = set(); stack = [start]
        while stack:
            p = stack.pop()
            if p in group or p not in crown:
                continue
            group.add(p); seen.add(p)
            stack += [(p[0] + dx, p[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
        xs = [p[0] for p in group]; ys = [p[1] for p in group]
        if not 2 <= max(xs) - min(xs) + 1 <= 5 or max(ys) - min(ys) + 1 > 3 or len(group) < 3:
            continue
        # the ground in front of the block: the tree stands on it
        front = []
        for x in set(xs):
            y = max(py for px, py in group if px == x) + 1
            if y < mp.h:
                front.append(mp.cells[y * mp.w + x]['values'][3])
        if not front:
            continue
        base = min(front)
        if any(mp.cells[y * mp.w + x]['values'][3] <= base for x, y in group):
            continue
        member = {}
        for x, y in group:
            j = y * mp.w + x; c = mp.cells[j]
            member[j] = {-1} | set(range(len(c['walls'] or [])))
        # its shadow and foot on the ground in front
        for x in range(min(xs) - 1, max(xs) + 2):
            for dy in (1, 2, 3):
                y = max(ys) + dy
                if not (0 <= x < mp.w and 0 <= y < mp.h):
                    continue
                j = y * mp.w + x; c = mp.cells[j]
                if c['values'][3] != base or c['values'][4] == 0xFFFF:
                    continue
                kind, words = mp.floor_cut(c['values'][4])
                if kind == 'cut' and mp.count.get(c['values'][4], 0) <= 12 and _dark_words(words):
                    member[j] = {-1}
        cut = {}
        for j, s_ in list(member.items()):
            c = mp.cells[j]
            if c['values'][3] == base and -1 in s_ and c['values'][4] != 0xFFFF:
                kind, words = mp.floor_cut(c['values'][4])
                if kind == 'floor':
                    s_.discard(-1)
                elif kind == 'cut':
                    cut[j] = words
        found.append((base, member, cut, max(xs) - min(xs) + 1))
    return found


def _fresh_green(image):
    """Bright green, not olive: palm fronds (the round trees' leaves are olive)."""
    pixels = [p for p in image.getdata() if p[3]]
    if not pixels:
        return 0
    return sum(1 for r, g, b, a in pixels if g > r + 8 and g > b + 8 and g > 40) / len(pixels)


def find_screen_trees(mp):
    """Trees found on the screen grid (palms): a joined crown of bright green
    pictures (wall pieces or raised tops, never ground), then everything drawn
    straight below it down to the ground - the trunk - that is not plain floor.
    [(base, {cell: slots}, {cell: words}, 0)]"""
    fresh = {}
    def green(code):
        if code not in fresh:
            try:
                fresh[code] = _fresh_green(mp.renderer.tile(code).convert('RGBA'))
            except Exception:
                fresh[code] = 0
        return fresh[code]
    seeds = set()
    for (col, row), pieces in mp.screen.items():
        for i, slot, code in pieces:
            if green(code) >= 0.3 and (slot != -1 or mp.cells[i]['values'][0] & 1):   # leaves you cannot walk on
                seeds.add((col, row))
    found = []; used = set()
    for start in sorted(seeds, key=lambda p: (p[1], p[0])):
        if start in used:
            continue
        crown = set(); stack = [start]
        while stack:
            p = stack.pop()
            if p in crown or p not in seeds:
                continue
            crown.add(p)
            stack += [(p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)]
        used |= crown
        cols = [p[0] for p in crown]; rows = [p[1] for p in crown]
        if not 2 <= max(cols) - min(cols) + 1 <= 5 or not 1 <= max(rows) - min(rows) + 1 <= 5 or len(crown) < 2:
            continue          # (a shrub's crown may be one row: two fronds side by side)
        body = set(crown)
        owners = {i for p in crown for i, slot, code in mp.screen.get(p, []) if green(code) >= 0.3}
        low = min(mp.cells[i]['values'][3] for i in owners) - 1 if owners else -1
        for col in range(min(cols), max(cols) + 1):
            row = max([r for c, r in crown if c == col] or [max(rows)]) + 1
            for _ in range(6):
                keep = False
                for i, slot, code in mp.screen.get((col, row), []):
                    if slot != -1 and mp.pieces[code] <= 40 and mp.cells[i]['values'][3] >= low:
                        keep = True                      # the trunk, drawn as pieces (a fence in front stands lower)
                    elif slot == -1 and mp.floor_cut(code)[0] == 'cut':
                        keep = True                      # its foot on the ground
                if not keep:
                    break
                body.add((col, row)); row += 1
        if len(body) - len(crown) < 1:
            continue                                     # nothing under the crown: not standing on the ground
        slots = {}
        for p in body:
            for i, slot, code in mp.screen.get(p, []):
                slots.setdefault(i, set()).add(slot)
        base = min(mp.cells[i]['values'][3] for i in slots)
        cut = {}
        for i, s_ in slots.items():
            c = mp.cells[i]
            if -1 in s_ and not mp.raised(i) and c['values'][4] != 0xFFFF:
                kind, words = mp.floor_cut(c['values'][4])
                if kind == 'floor':
                    s_.discard(-1)
                elif kind == 'cut':
                    cut[i] = words
        found.append((base, slots, cut, 0))
    return found


# Trees the game only ever shows partly covered (behind a fence or a ledge),
# taken apart by hand: the cells and the pictures of each that are the tree.
# The pineapple palm (map 8): its fronds are the two tiles' pictures and its
# round bulb the two pieces hanging under them; the fence and cliff in front
# are left out.
ISOLATED = {
    8: [(8, [((37, 37), (-1, 0, 1)), ((38, 37), (-1, 0, 1))])],
}


def isolated_trees(mp, m):
    out = []
    for base, parts in ISOLATED.get(m, []):
        slots = {}
        for (x, y), keep in parts:
            c = mp.cells[y * mp.w + x]
            have = {-1} | set(range(len(c['walls'] or [])))
            slots[y * mp.w + x] = set(keep) & have
        out.append((base, slots))
    return out


def standing_trees(session, m, renderer=None):
    """[(base, rows, cuts, image, (x0, y0))] like map_trees, for standing trees."""
    mp, found = find_standing_trees(session, m, renderer)
    found = found + find_screen_trees(mp)
    out = []
    for base, slots, cut, run in found:
        rows = tree_rows(mp, base, slots)
        cells = [mp.cells[i] for i in slots]
        x0 = min(c['x'] for c in cells); y0 = min(c['y'] for c in cells)
        cuts = {(mp.cells[i]['x'] - x0, mp.cells[i]['y'] - y0): words for i, words in cut.items()}
        rows, cuts = clean_tree(mp, rows, cuts)
        image = tree_picture(mp, rows, cuts)
        if image.height < 56 or _stone(image) > 0.04 or _green(image) < 0.25:
            continue
        if run == 2 and image.width > 64 or run == 4 and image.width > 120:
            continue          # a crown cut by its neighbour (trees standing in a clump)
        top = image.crop((0, 0, image.width, max(1, image.height * 2 // 5)))
        if image.width >= 64 and _fresh_green(top) >= 0.5 and image.height < 100 and run != 0:
            continue          # a palm whose trunk is hidden (behind a ledge): not whole
        if run == 0 and _leaves_at_foot(image):
            continue          # a palm with a bush or grass grown up around its trunk
        if _edge_cut(image) or not _has_foot(image) or not _single(image):
            continue          # only one whole tree and nothing else in the picture
        out.append((base, rows, cuts, image, (x0, y0)))
    for base, slots in isolated_trees(mp, m):
        rows = tree_rows(mp, base, slots)
        cells = [mp.cells[i] for i in slots]
        x0 = min(c['x'] for c in cells); y0 = min(c['y'] for c in cells)
        out.append((base, rows, {}, tree_picture(mp, rows, {}), (x0, y0)))
    return out


def _edge_cut(image):
    """A crown sliced straight down one side: part of a clump, not a whole tree."""
    w, h = image.size; px = image.load(); top = h * 2 // 3
    for x in (0, w - 1):
        column = sum(1 for y in range(top) if px[x, y][3])
        if column > top * 0.6:
            return True
    return False


def _has_foot(image):
    """The trunk and its foot are there: the lowest quarter is not empty."""
    w, h = image.size; px = image.load(); top = h * 3 // 4
    filled = sum(1 for y in range(top, h) for x in range(w) if px[x, y][3])
    return filled >= 0.25 * w * (h - top)


def _single(image):
    """One tree on its own: the picture is one piece (bits of roots and shadow
    under it aside - no stones or bits of another tile beside it) and about as
    wide on the left as on the right (no part of a neighbouring crown or a
    fence joined to it)."""
    w, h = image.size; px = image.load()
    opaque = {(x, y) for y in range(h) for x in range(w) if px[x, y][3]}
    if not opaque:
        return False
    seen = set(); parts = []
    for start in opaque:
        if start in seen:
            continue
        stack = [start]; seen.add(start); part = []
        while stack:
            x, y = stack.pop(); part.append((x, y))
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1), (x + 1, y + 1), (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1)):
                if q in opaque and q not in seen:
                    seen.add(q); stack.append(q)
        parts.append(part)
    parts.sort(key=len, reverse=True)
    main = parts[0]
    left = min(x for x, _ in main); right = max(x for x, _ in main)
    for part in parts[1:]:
        roots = all(y >= h * 3 // 4 and left <= x <= right for x, y in part)
        if not roots and len(part) > 3:
            return False   # something beside the tree
    if sum(len(p) for p in parts[1:]) > 0.05 * len(main):
        return False
    same = sum(1 for (x, y) in main if (left + right - x, y) in opaque)
    if same < 0.8 * len(main):
        return False
    # nothing standing beside it: the outer edges are crown only, not a post or a wall
    # whole from base to top: the foot and the crown's top are not cut or
    # joined to something on one side
    for band in (range(0, h // 4), range(h * 3 // 4, h)):
        inband = [(x, y) for (x, y) in main if y in band]
        if inband:
            mirrored = sum(1 for (x, y) in inband if (left + right - x, y) in opaque)
            if mirrored < 0.8 * len(inband):
                return False
    low = h // 2
    for x in (left, left + 1, right - 1, right):
        run = best = 0
        for y in range(low, h):
            run = run + 1 if (x, y) in opaque else 0
            best = max(best, run)
        if best > 26:
            return False      # a post or a wall running down beside it
    return True


def tree_signature(image):
    """What a tree looks like, small: trees that only differ in their palette,
    their shadow's edge or a few pixels get the same signature."""
    from PIL import Image
    box = image.getbbox() or (0, 0, image.width, image.height)
    small = image.crop(box).resize((12, 16), Image.BILINEAR)
    sig = []
    for r, g, b, a in small.getdata():
        sig.append(0 if a < 128 else 1 + min(3, (r + g + b) // 192))
    return tuple(sig)


def same_tree(a, b):
    """Two signatures for the same tree (a few cells of 192 may differ: a
    shadow's edge). Trees in other colours or with other roots stay apart."""
    return sum(1 for x, y in zip(a, b) if x != y) <= 4


def unique_trees(trees):
    """One of each tree: [(signature, tree, uses)], the tree as it is found most
    often in the game standing for all its variants."""
    groups = []
    for tree, sig in trees:
        for g in groups:
            if same_tree(g['sig'], sig):
                g['members'].append((tree, sig)); break
        else:
            groups.append({'sig': sig, 'members': [(tree, sig)]})
    # a tree whose crown is another's but shows much less trunk is cut off
    # (standing behind a ledge or a bush): only whole ones stay
    def picture(t):
        return next((x for x in (t if isinstance(t, tuple) else (t,)) if hasattr(x, 'getbbox')), None)
    heights = {id(g): max((picture(t).height if picture(t) else 0) for t, _ in g['members']) for g in groups}
    def crown(g):
        image = picture(g['members'][0][0])
        return crown_signature(image) if image is not None else None
    crowns = {id(g): crown(g) for g in groups}
    keep = []
    for g in groups:
        taller = [h for o in groups if o is not g and crowns[id(o)] is not None and crowns[id(g)] is not None
                  and same_crown(crowns[id(o)], crowns[id(g)]) for h in [heights[id(o)]]]
        if taller and heights[id(g)] < 0.8 * max(taller):
            continue
        keep.append(g)
    groups = keep
    out = []
    for g in groups:
        tally = Counter(sig for _, sig in g['members'])
        best_sig = tally.most_common(1)[0][0]
        tree = next(t for t, s_ in g['members'] if s_ == best_sig)
        out.append((best_sig, tree, len(g['members'])))
    return sorted(out, key=lambda u: -u[2])


def crown_signature(image):
    """The top of a tree (its crown), small, for spotting the same crown."""
    from PIL import Image
    box = image.getbbox() or (0, 0, image.width, image.height)
    top = image.crop((box[0], box[1], box[2], min(box[3], box[1] + 40))).resize((12, 8), Image.BILINEAR)
    return tuple(0 if a < 128 else 1 + min(3, (r + g + b) // 192) for r, g, b, a in top.getdata())


def same_crown(a, b):
    return sum(1 for x, y in zip(a, b) if x != y) <= 10


def _leaves_at_foot(image):
    """Leaves beside a palm's trunk, low down: something else is in the picture."""
    w, h = image.size; px = image.load(); n = 0; total = 0
    for y in range(h * 3 // 4, h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if not a:
                continue
            total += 1
            if g >= r - 6 and g > b + 15 and g > 40 and max(r, g, b) - min(r, g, b) > 50:
                n += 1      # saturated leaves; the trunk is grey
    return total and n > 0.15 * total
