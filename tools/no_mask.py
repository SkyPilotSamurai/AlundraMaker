"""No Mask (user 2026-10-25): pictures the game draws over Alundra.

Rules (the game draws a tile's floor under characters on its own row and earlier
rows, and its wall pieces over them):
- floor picture of tile y: covers Alundra standing on an earlier row q < y whose
  square is up to BODY rows below the picture (a desk front owned by a tile far
  down the map).
- wall piece of tile y: covers him the same way, and also when he stands on tile
  q <= y (its own tile too) on the picture's square or up to two rows below,
  at least as high as tile y (a floor-looking piece over the floor he walks on).
A covering picture is moved into its own tile's floor picture (same square) or
to a tile further up the map than where he stands, only when the editor picture
of the column stays exactly the same."""
from area_map import render_region

BODY = 3   # rows of Alundra above his feet that a picture can cover


def _pictures(cell, y):
    """[(screen row, code, where)] where = ('floor',) or ('wall', index)."""
    v = cell['values']; floor = y - v[3]; out = []
    if v[4] != 0xFFFF: out.append((floor, v[4], ('floor',)))
    if cell.get('walls'):
        shift, codes = cell['walls']
        for i, cd in enumerate(codes):
            if cd != 0xFFFF: out.append((floor + i + 1 - shift, cd, ('wall', i)))
    return out


def _rebased(pieces):
    if not pieces: return None
    lo, hi = min(pieces), max(pieces); shift = 1 - lo
    if not -128 <= shift <= 127 or hi - lo + 1 > 255: return False
    return (shift, [pieces.get(r, 0xFFFF) for r in range(lo, hi + 1)])


def _pieces(cell, y):
    v = cell['values']; floor = y - v[3]
    return {r - floor: cd for r, cd, where in _pictures(cell, y) if where[0] == 'wall'}


def _walk(cells, width, height, tx):
    return [(q, q - cells[q * width + tx]['values'][3], cells[q * width + tx]['values'][3]) for q in range(height)
            if not cells[q * width + tx]['values'][0] & 1 and cells[q * width + tx]['values'][4] != 0xFFFF]


def covered(walk, y, h, r, where):
    """Rows q of walkable tiles where Alundra is drawn under this picture."""
    out = [q for q, s, hq in walk if q < y and r < s <= r + BODY]
    if where[0] == 'wall':
        out += [q for q, s, hq in walk if q <= y and r <= s <= r + 2 and hq >= h]
    return sorted(set(out))


def find_masking(cells, width, height):
    """[(x, y, screen row, code, where, [rows q it covers Alundra on])] for the map."""
    found = []
    for tx in range(width):
        walk = _walk(cells, width, height, tx)
        for y in range(height):
            cell = cells[y * width + tx]
            for r, cd, where in _pictures(cell, y):
                qs = covered(walk, y, cell['values'][3], r, where)
                if qs: found.append((tx, y, r, cd, where, qs))
    return found


def fix_column(renderer, cells, width, height, margin, tx):
    """cells: row-major list of {'values': 6-tuple, 'walls': (shift, codes) or None}.
    Fixes column tx in place. Returns (moved count, changed (x, y) tiles)."""
    def col():
        return [cells[y * width + tx] for y in range(height)]
    def picture(over=None):
        rows = [over.get(y, c) if over else c for y, c in enumerate(col())]
        return render_region(renderer, rows, 1, margin, (0, 0, 24, height * 16 + margin)).tobytes()
    moved = 0; changed = set(); tried = set()
    want = picture()
    progress = True
    while progress:
        progress = False
        walk = _walk(cells, width, height, tx)
        for y in range(height - 1, -1, -1):
            cell = cells[y * width + tx]
            for r, cd, where in _pictures(cell, y):
                if (y, r, cd, where) in tried: continue
                qs = covered(walk, y, cell['values'][3], r, where)
                if not qs: continue
                tried.add((y, r, cd, where))
                v = list(cell['values']); floor = y - v[3]
                options = []
                if where[0] == 'wall':
                    p = _pieces(cell, y); p.pop(r - floor, None); rest = _rebased(p)
                    if rest is False: continue
                    if r == floor:   # into its own floor picture (drawn under him)
                        options.append({y: {'values': tuple(v[:4] + [cd] + v[5:]), 'walls': rest}})
                    src = {'values': tuple(v), 'walls': rest}
                else:
                    v[4] = 0xFFFF; src = {'values': tuple(v), 'walls': cell.get('walls')}
                limit = min(qs)
                for b in range(min(limit, y) - 1, -1, -1):
                    owner = cells[b * width + tx]; bf = b - owner['values'][3]
                    p = _pieces(owner, b)
                    if r - bf in p: continue
                    p[r - bf] = cd; walls = _rebased(p)
                    if walls is False: continue
                    options.append({y: src, b: {'values': owner['values'], 'walls': walls}})
                for over in options:
                    if picture(over) != want: continue
                    for k, c in over.items(): cells[k * width + tx] = c; changed.add((tx, k))
                    moved += 1; progress = True
                    break
                if progress: break
            if progress: break
    return moved, changed


def fix_map(renderer, cells, width, height, margin):
    moved = 0; changed = set()
    for tx in range(width):
        n, c = fix_column(renderer, cells, width, height, margin, tx)
        moved += n; changed |= c
    return moved, changed


def choose_owner(renderer, cells, width, height, margin, tx, sr, code):
    """Placing `code` on screen square (tx, sr) on top of what is drawn there: the tile
    that gets it as a piece. It must not be drawn over Alundra (covered() is empty)
    and the picture must end up exactly on top. Returns (row, walls) or None."""
    from PIL import Image
    col = [cells[y * width + tx] for y in range(height)]
    def picture(over=None):
        rows = [over.get(y, c) if over else c for y, c in enumerate(col)]
        return render_region(renderer, rows, 1, margin, (0, 0, 24, height * 16 + margin))
    base = picture(); tile = renderer.tile(code)
    want = base.copy(); want.paste(tile, (0, sr * 16 + margin), tile); want = want.tobytes()
    if want == base.tobytes(): return None
    drawn = [y for y in range(height) for r, cd, where in _pictures(col[y], y) if r == sr]
    first = max(drawn) if drawn else 0
    walk = _walk(cells, width, height, tx)
    for b in range(first, height):
        owner = col[b]; hb = owner['values'][3]
        if covered(walk, b, hb, sr, ('wall',)): continue
        p = _pieces(owner, b); rel = sr - (b - hb)
        if rel in p: continue
        p[rel] = code; walls = _rebased(p)
        if walls is False: continue
        if picture({b: {'values': owner['values'], 'walls': walls}}).tobytes() == want:
            return b, walls
    return None


def picture_covers(cells, width, height, tx, y, r, where):
    """Rows q of walkable tiles in column tx where Alundra is drawn under this picture of tile y."""
    return covered(_walk(cells, width, height, tx), y, cells[y * width + tx]['values'][3], r, where)


def fix_picture(renderer, cells, width, height, margin, tx, y, r, cd, where, skip_slopes=False):
    """Move one picture (tile y's floor or wall piece drawn on screen row r) so it is drawn behind
    Alundra, the way fix_column does it, only when the column looks exactly the same.
    Returns the changed rows or None when no such move exists."""
    def picture(over=None):
        rows = [over.get(k, cells[k * width + tx]) if over else cells[k * width + tx] for k in range(height)]
        return render_region(renderer, rows, 1, margin, (0, 0, 24, height * 16 + margin)).tobytes()
    qs = picture_covers(cells, width, height, tx, y, r, where)
    if not qs: return None
    want = picture(); cell = cells[y * width + tx]
    v = list(cell['values']); floor = y - v[3]; options = []
    if where[0] == 'wall':
        p = _pieces(cell, y); p.pop(r - floor, None); rest = _rebased(p)
        if rest is False: return None
        if r == floor: options.append({y: {'values': tuple(v[:4] + [cd] + v[5:]), 'walls': rest}})
        src = {'values': tuple(v), 'walls': rest}
    else:
        v[4] = 0xFFFF; src = {'values': tuple(v), 'walls': cell.get('walls')}
    for b in range(min(min(qs), y) - 1, -1, -1):
        owner = cells[b * width + tx]; bf = b - owner['values'][3]
        if skip_slopes and owner['values'][2] & 3:   # Draw all behind Alundra leaves slopes alone
            continue
        p = _pieces(owner, b)
        p[r - bf] = cd; walls = _rebased(p)   # may replace a piece on that square; kept only if the column looks the same (user 2026-10-25)
        if walls is False: continue
        options.append({y: src, b: {'values': owner['values'], 'walls': walls}})
    for over in options:
        if picture(over) == want:
            for k, c in over.items(): cells[k * width + tx] = c
            return sorted(over)
    return None


def push_back(renderer, cells, width, height, margin, tx, y, r, cd, where):
    """Tile fix "Draw further back" (user 2026-10-25): move tile y's picture on screen row r
    to a tile further up the map (drawn earlier), so objects/events standing on row y or
    rows before it (a gate under an arch, say) are drawn over it. Only when the column
    looks exactly the same. Returns the changed rows or None."""
    def picture(over=None):
        rows = [over.get(k, cells[k * width + tx]) if over else cells[k * width + tx] for k in range(height)]
        return render_region(renderer, rows, 1, margin, (0, 0, 24, height * 16 + margin)).tobytes()
    want = picture(); cell = cells[y * width + tx]
    v = list(cell['values']); floor = y - v[3]
    if where[0] == 'wall':
        p = _pieces(cell, y); p.pop(r - floor, None); rest = _rebased(p)
        if rest is False: return None
        src = {'values': tuple(v), 'walls': rest}
    else:
        v[4] = 0xFFFF; src = {'values': tuple(v), 'walls': cell.get('walls')}
    for b in range(y - 1, -1, -1):
        owner = cells[b * width + tx]; bf = b - owner['values'][3]
        p = _pieces(owner, b); p[r - bf] = cd; walls = _rebased(p)
        if walls is False: continue
        over = {y: src, b: {'values': owner['values'], 'walls': walls}}
        if picture(over) == want:
            for k, c in over.items(): cells[k * width + tx] = c
            return sorted(over)
    return None


def draw_all_behind(renderer, cells, width, height, margin, blank=None, keep=None, masked=()):
    """Draw all behind Alundra (the editor button, also run by every build before Fix Masks):
    Draw behind him on every picture drawn over Alundra, slopes left alone, only where the
    map looks exactly the same. A tile whose floor picture moves gets the see-through
    picture `blank` (when there is one) so it keeps its floor and height. Returns the count."""
    count = 0; tried = set(); progress = True
    while progress:
        progress = False
        for tx, ty, r, cd, where, qs in find_masking(cells, width, height):
            if (tx, ty, r, cd) in tried: continue
            tried.add((tx, ty, r, cd))
            if cells[ty * width + tx]['values'][2] & 3: continue
            if (tx, ty) in masked or layered(cells, width, height, tx, ty, r, where): continue   # layered masks stay (user 2026-10-26)
            try: moved = fix_picture(renderer, cells, width, height, margin, tx, ty, r, cd, where, skip_slopes=True)
            except Exception: moved = None
            if moved:
                c = cells[ty * width + tx]
                if c['values'][4] == 0xFFFF and blank is not None:
                    v = list(c['values']); v[4] = blank; cells[ty * width + tx] = dict(c, values=tuple(v))
                count += 1; progress = True; break
    return count


def blank_code(renderer, cells):
    """A tile picture with every pixel see-through, or None."""
    for cd in sorted({c['values'][4] for c in cells if c['values'][4] != 0xFFFF} | set(range(1024))):
        try:
            if renderer.tile(cd).convert('RGBA').getchannel('A').getbbox() is None: return cd
        except Exception: continue
    return None


def picture_hash(renderer, cd):
    import hashlib
    try: return hashlib.md5(renderer.tile(cd).convert('RGBA').tobytes()).hexdigest()
    except Exception: return None


_STOCK_MASKS = {}


def stock_mask_pictures(original):
    """Pictures the original game draws over Alundra on purpose (railings, arches...): the md5 of
    every tile picture find_masking reports on the 483 stock maps of `original` (DATAS bytes).
    Kept in private-inputs/editor-cache after the first time (about 10 seconds)."""
    import hashlib, json
    from pathlib import Path
    key = hashlib.sha256(original).hexdigest()[:16]
    if key in _STOCK_MASKS: return _STOCK_MASKS[key]
    cache = Path(__file__).resolve().parents[1] / 'private-inputs' / 'editor-cache' / f'stock_mask_pictures_{key}.json'
    try:
        found = set(json.loads(cache.read_text(encoding='utf-8')))
    except Exception:
        from editor_session import EditSession
        from area_map import MapRenderer
        from map_area_copy import cells_of
        session = EditSession(bytes(original), allow_compatible=True) if 'allow_compatible' in EditSession.__init__.__code__.co_varnames else EditSession(bytes(original))
        found = set()
        for m in range(483):
            try:
                w, hh, cells = cells_of(session, m); r = MapRenderer(session, m)
                for tx, ty, rr, cd, where, qs in find_masking(cells, w, hh):
                    h = picture_hash(r, cd)
                    if h: found.add(h)
            except Exception:
                continue
        try:
            cache.parent.mkdir(parents=True, exist_ok=True); cache.write_text(json.dumps(sorted(found)), encoding='utf-8')
        except Exception:
            pass
    _STOCK_MASKS[key] = found
    return found


def layered(cells, width, height, tx, y, r, where):
    """True when this picture (tile y's floor or wall piece on screen row r) is layered over another
    picture on the same screen square: another tile's picture, or another piece of its own stack."""
    for k in range(height):
        for rr, cd, w2 in _pictures(cells[k * width + tx], k):
            if rr == r and (k, w2) != (y, where): return True
    return False


def masked_tiles(document, m):
    """Tiles placed with the Mask layer on map m: {(x, y)}."""
    out = set()
    for r in ((document or {}).get('masked_tiles') or {}).get(str(m), []) or []:
        try:
            if isinstance(r, dict):
                for k in ('mask', 'origin'):
                    if r.get(k): out.add(tuple(r[k][:2]))
            else: out.add(tuple(r[:2]))
        except Exception: continue
    return out
