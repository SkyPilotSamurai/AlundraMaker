"""Build-time rule (user 2026-10-25): Edit heights is absolute. A walkable cell whose
square the Edit heights view draws as a grey (covered / wall / height-0 / face) square
plays as a wall: it is exported no-walk for everyone (byte0 |= 0x41, as stock walls).
Only created maps and maps whose tile grid differs from the stock grid are touched;
stock maps stay byte-identical. The view code itself is reused, so the rule is
exactly what is drawn in the 'Lowest tiles' view (user 2026-10-25: Lowest tiles shows
the movable area; Highest tiles only shows upper surfaces and never makes a covered
low cell walkable). A walkable cell under a square that shows a NUMBER
exports at that number's height (user 2026-10-25: 'any tile that shares a tile should
match the height shown'); byte0 flags and the picture are kept."""
import struct
from copy import copy
from types import SimpleNamespace, MethodType
from area_map import grid
from map_slots import STOCK_MAPS, map_count, map_base

MARGIN = 16 * 300   # any constant: positions only need to be consistent


class _Var:
    def __init__(self, v): self.v = v
    def get(self): return self.v


class _Canvas:
    """Records grey squares by tag so later canvas.delete(tag) removes them."""
    def __init__(self): self.greys = {}
    def grey(self, x, y, tags):
        for t in tags: self.greys.setdefault(t, set()).add((x, y))
    def delete(self, tag): self.greys.pop(tag, None)
    def __getattr__(self, name): return lambda *a, **k: None


def grey_cells(session, m, document=None):
    """Walkable cells (x, y) drawn as grey squares in Edit heights for map m."""
    return view_rules(session, m, document)[0]


def view_rules(session, m, document=None):
    """(grey cells to block, {cell: shown height} for cells under another tile's number)."""
    from area_ui import AreaPanel
    w, h, cells = grid(session, m)
    canvas = _Canvas()
    view = SimpleNamespace(
        canvas=canvas, map_crop_top=0, margin=MARGIN,
        editor=SimpleNamespace(database=SimpleNamespace(document=document or {}), current_map=m, session=session),
        grid_cells=cells, grid_width=w, grid_height=h, pending_heights=set(),
        mark_walls=_Var(False), height_edit=_Var(True), height_show=_Var('Lowest'),
        show_wall_pit_heights=_Var(False), last_height_edit=None)
    view.elevation_enabled = lambda: True
    view.grey_square = lambda x, y, tags: canvas.grey(x, y, tags)
    view.raise_height_numbers = lambda: None
    view.stop_height = MethodType(AreaPanel.stop_height, view)
    AreaPanel._redraw_height_display(view)
    greys = set().union(*canvas.greys.values()) if canvas.greys else set()
    top = {}   # Lowest tiles: the number shown is the lowest top in the square
    for c in cells:
        v = c['values']
        if v[4] == 0xFFFF or v[0] & 1: continue
        sq = (c['x'] * 24, (c['y'] - v[3]) * 16 + MARGIN)
        top[sq] = min(top.get(sq, 999), v[3])
    out = []; heights = {}; behind = walk_behind_floor(cells, w, h)
    for c in cells:
        v = c['values']
        if v[0] & 1: continue
        t = (c['x'], c['y'])
        sq = view.height_floor.get(t, (c['x'] * 24, (c['y'] - v[3]) * 16 + MARGIN))
        shown = view.height_stack.get(sq)
        if (sq in greys and shown in (None, t) or sq in greys and t not in view.height_floor):
            if v[4] == 0xFFFF and t in behind: continue   # floor you walk behind (no picture of its own): stays walkable
            out.append(t)   # drawn grey: a wall / covered square
        elif shown is not None and shown != t:
            if v[4] == 0xFFFF and t in behind: continue   # floor you walk behind keeps its own height (user 2026-10-26)
            number = top.get(sq, cells[shown[1] * w + shown[0]]['values'][3])
            if number != v[3]: heights[t] = number   # under a shown number: plays at that height
    walls = {(c, r) for c, r, _ in (document or {}).get('wall_squares', {}).get(str(m), [])}   # Wall mode squares
    for c in cells:
        t = (c['x'], c['y'])
        if not c['values'][0] & 1 and (c['x'], c['y'] - c['values'][3]) in walls:
            heights.pop(t, None)
            if t not in out: out.append(t)
    return sorted(out), heights


SKIP_INVISIBLE_FLOOR = {27}   # maps left as they are (user 2026-10-25: 'skip map 27')


def walk_behind_floor(cells, w, h):
    """Floor you walk behind (user 2026-10-26: behind the bookshelves, as the game's own maps):
    walkable tiles joined at their own height to walkable floor that has a picture. {(x, y)}"""
    def h_of(t): return cells[t[1] * w + t[0]]['values']
    real = set(); seen = set()
    for c in cells:
        t0 = (c['x'], c['y'])
        if t0 in seen or c['values'][0] & 1: continue
        comp = [t0]; seen.add(t0); i = 0; pic = False
        while i < len(comp):
            t = comp[i]; i += 1; v = h_of(t)
            if v[4] != 0xFFFF: pic = True
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                n = (t[0] + dx, t[1] + dy)
                if 0 <= n[0] < w and 0 <= n[1] < h and n not in seen:
                    nv = h_of(n)
                    if not nv[0] & 1 and nv[3] == v[3]: seen.add(n); comp.append(n)
        if pic: real.update(comp)
    return real


def invisible_floor(session, m, document=None):
    """Walkable tiles with no picture of their own and nothing drawn on their square (user 2026-10-25:
    a tile with no picture should not be walkable when nothing shows there). Tiles inside a warp area
    or an event region are kept, so exits and triggers still work. Returns [(x, y)]."""
    from area_map import MapRenderer
    w, h, cells = grid(session, m)
    r = MapRenderer(session, m); r.render()
    margin = max((c['values'][3] for c in cells), default=0) * 16
    keep = set()
    try:
        from warp_editor import warps
        for _, _, p in warps(session, m):
            keep |= {(x, y) for x in range(p.x1, p.x2 + 1) for y in range(p.y1, p.y2 + 1)}
    except Exception:
        pass
    for g in (document or {}).get('event_graphs', []):
        if g.get('map_id') == m and g.get('region'):
            x, y, rw, rh = g['region'][:4]
            keep |= {(a, b) for a in range(x, x + max(1, rw)) for b in range(y, y + max(1, rh))}
    real = walk_behind_floor(cells, w, h)
    out = []
    for c in cells:
        v = c['values']; t = (c['x'], c['y'])
        if v[0] & 1 or v[4] != 0xFFFF or t in keep: continue
        if t in real and c['walls'] is not None:
            # behind something: kept when its square has something drawn on it (the shelf in front)
            hits = r.surface_hits.get((c['x'], c['y'] - v[3] + margin // 16), [])
            if any(hh[5] != 0xFFFF for hh in hits) or any(code != 0xFFFF for _, code, _, _ in c['walls']): continue
        # a drop-off (user 2026-10-25, map 492: 'I walk into the wall and fall down'): no floor picture of
        # its own and next to a walkable floor more than one step higher - he walks off into it and falls
        drop = False
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = c['x'] + dx, c['y'] + dy
            if 0 <= nx < w and 0 <= ny < h:
                n = cells[ny * w + nx]['values']
                if not n[0] & 1 and n[4] != 0xFFFF and n[3] > v[3] + 1: drop = True; break
        if drop: out.append(t); continue
        if any(code != 0xFFFF for _, code, _, _ in c['walls']): continue
        hits = r.surface_hits.get((c['x'], c['y'] - v[3] + margin // 16), [])
        if any(hh[5] != 0xFFFF for hh in hits): continue
        out.append(t)
    return out


def _grid_bytes(data, m):
    base = map_base(data, m); hd = struct.unpack_from('<7I', data, base)
    return bytes(data[base + hd[1]:base + hd[2]])


def project_maps(session):
    original = session.original
    stock = map_count(original)
    for m in range(map_count(session.data)):
        if m >= STOCK_MAPS or m >= stock:
            yield m
        else:
            try:
                if _grid_bytes(session.data, m) != _grid_bytes(original, m): yield m
            except Exception:
                yield m


def apply_height_view_blocking(session, progress=lambda text: None):
    """Return (session, {map: [(x, y), ...]}). The session is copied when changed."""
    doc = getattr(session, 'content_database', None) or {}
    changes = {}; raised = {}; unseen = {}
    try: maps = list(project_maps(session))
    except (struct.error, ValueError, IndexError): return session, changes   # not a map archive
    for m in maps:
        try:
            cells, heights = view_rules(session, m, doc)
        except ValueError:
            continue
        hidden = []
        if m not in SKIP_INVISIBLE_FLOOR:
            try: hidden = invisible_floor(session, m, doc)
            except Exception as exc: progress(f'Warning: map {m}: invisible floor check skipped ({exc})')
            # a cell under a shown number plays at that number (it shows there): not invisible and
            # not a drop-off. It was judged at its old height and walled the way between two floors
            # (user 2026-10-26, map 489: the 3s could not be walked into the 4s).
            hidden = [t for t in hidden if t not in heights]
        if cells or heights or hidden: changes[m] = cells; raised[m] = heights; unseen[m] = hidden
    if not changes: return session, changes
    session = copy(session); session.data = bytearray(session.data)
    for m, cells in changes.items():
        w, _, grid_cells = grid(session, m)
        # Only Wall mode squares are made no-walk: a grey (covered) square stays walkable
        # (user 2026-10-25: 'I should absolutely be able to walk on these grey tiles').
        walls = {(c, r) for c, r, _ in (doc.get('wall_squares') or {}).get(str(m), [])}
        for x, y in cells:
            c = grid_cells[y * w + x]
            if (x, y - c['values'][3]) in walls:
                session.data[c['offset']] |= 0x41
        for x, y in unseen.get(m, []):   # no picture and nothing drawn on its square: nobody walks there
            session.data[grid_cells[y * w + x]['offset']] |= 0x41
        if unseen.get(m): progress(f'Map {m}: {len(unseen[m])} walkable tiles with nothing drawn or dropping off a ledge made no-walk')
        for (x, y), hgt in raised[m].items():
            c = grid_cells[y * w + x]
            if c['values'][4] != 0xFFFF or any(code != 0xFFFF for _, code, _, _ in c['walls']):
                continue   # it draws a picture: a new height would move it in game (user 2026-10-25)
            session.data[c['offset'] + 3] = hgt
        progress(f'Map {m}: {len(cells)} covered cells made no-walk, {len(raised[m])} heights set to the shown number (Edit heights view)')
    session.height_view_heights = raised
    return session, changes
