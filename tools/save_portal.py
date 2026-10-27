"""Save Room Portal: the save rooms' swirling way back as a placeable object.

What the game has (stock DATAS.BIN, checked on save rooms 452-470; source maps 22, 62, 74, 109):
* the 2x2 stone panel (map 452 tiles 14-15 x 16-17, the Warp Panel's picture);
* effect table entry type 0x18 (global effect sprite 24: blue glow, additive, pulsing; 8 frames
  of 10 ticks), flags 0x40, at x = 2*left+1, y = 2*bottom, z = 2*height (452: 0x1D 0x22 0x02);
* the panel's four cells carry ground bit 0x04 (warp square: taken at once, no facing) and 0x80;
* portal records, one per panel row, with flags 0x055 (+ arrival facing in bits 12-13):
  warp effect (flags & 0x70) >> 4 = 5 and warp sound table 0x80028D70[flags & 15] = 74
  (ALUN_CD.EXE; engine/player.py use_portal 0x80031898).
* the way back is a FIXED destination in each save room's own records (452 -> map 62 18,16,
  453 -> 22 26,31, ...): every save room is entered from one place only. The game keeps no
  "previous map / position" for it.

Here: "Return To Previous Location" (default) is resolved by the build from the warps that lead
into the portal's map. One entrance: records to the tile beside it, as the game's own rooms
are wired. Several entrances: a map program notes where Alundra arrived (op 3B on each arrival
area) and sends him back with Change Map 53 (effect 5, sound 74). "Chosen Destination": records
to the picked tile.
"""
import struct

VARIANT = 'save_portal'
NAME = 'Save Room Portal'
DONOR_MAP = 452
SWIRL_SPRITE = 0x18
SWIRL_FLAGS = 0x40
WARP_LOW = 0x055          # warp effect 5, warp sound index 5
WARP_EFFECT = 5
WARP_SOUND = 74           # ALUN_CD.EXE 0x80028D70[5]
MAX_EFFECTS = 16
SIDES = {0: (0, 1), 1: (0, -1), 2: (-1, 0), 3: (1, 0)}   # Down, Up, Left, Right
OPPOSITE = {0: 1, 1: 0, 2: 3, 3: 2}


def portal_of(definition):
    return (definition or {}).get('source', {}).get('variant') == VARIANT


def mode_of(placement):
    return 'destination' if (placement or {}).get('warp_mode') == 'destination' else 'previous'


def rect(x, y):
    """The panel's tiles (x1, y1, x2, y2) when its event stands on (x, y), its bottom-left."""
    return x, y - 1, x + 1, y


def swirl_entry(w, h, x, y, z):
    return bytes((0, 0, w - 1, h - 1, SWIRL_FLAGS, SWIRL_SPRITE, 2 * x + 1, 2 * y, 2 * z, 0, 0, 0))


def _view(data):
    from heal_tile import _View
    return _View(data)


def _portals(data, m):
    from portal_records import Portal
    base, h = _view(data).layout(m)
    start = base + h[0] + 0x42c
    out = []
    for i in range(64):
        p = Portal.read(data, start + i * 12)
        if (p.x1, p.y1, p.x2, p.y2) == (0, 0, 255, 255):
            break
        out.append((i, start + i * 12, p))
    return start, out


def _open(cells, w, h, x, y, rects=()):
    if not (0 <= x < w and 0 <= y < h):
        return False
    c = cells[y * w + x]
    v = c['values']
    if v[4] == 0xFFFF or v[0] & 0x45:             # no floor, blocked (0x01 / 0x40) or a warp square
        return False
    return not any(a <= x <= b and c2 <= y <= d for a, c2, b, d in rects)


def return_point(data, source_map, box, facing):
    """(x, y, z, arrive facing) beside an entrance box (x1, y1, x2, y2) on source_map:
    the side Alundra came from (opposite the way he walks in), else any open side."""
    from area_map import grid
    w, h, cells = grid(_view(data), source_map)
    x1, y1, x2, y2 = box
    rects = [(p.x1, p.y1, p.x2, p.y2) for _, _, p in _portals(data, source_map)[1]]
    came = OPPOSITE.get(facing, 0)
    for side in [came] + [s for s in (0, 1, 2, 3) if s != came]:
        dx, dy = SIDES[side]
        if dx:
            tiles = [(x2 + 1 if dx > 0 else x1 - 1, y) for y in range(y1, y2 + 1)]
        else:
            tiles = [(x, y2 + 1 if dy > 0 else y1 - 1) for x in range(x1, x2 + 1)]
        for tx, ty in tiles:
            if _open(cells, w, h, tx, ty, rects):
                return tx, ty, cells[ty * w + tx]['values'][3], side
    raise ValueError(f'Map {source_map}: no open floor beside the warp at {x1},{y1}')


def entrances(data, target):
    """Warps on other maps that lead to `target`, grouped by touching areas:
    [{'map', 'box', 'facing', 'arrive_box'}] (arrive_box: where they put Alundra on target)."""
    from map_slots import map_count, map_exists
    groups = []
    for m in range(map_count(data)):
        if m == target or not map_exists(data, m):
            continue
        try:
            rows = [p for _, _, p in _portals(data, m)[1] if p.destination_map == target]
        except (ValueError, struct.error, IndexError):
            continue
        mine = []
        for p in rows:
            box = [p.x1, p.y1, p.x2, p.y2]
            arrive = [p.destination_x, p.destination_y, p.destination_x + p.x2 - p.x1, p.destination_y + p.y2 - p.y1]
            for g in mine:
                b = g['box']
                if box[0] <= b[2] + 1 and b[0] <= box[2] + 1 and box[1] <= b[3] + 1 and b[1] <= box[3] + 1:
                    g['box'] = [min(b[0], box[0]), min(b[1], box[1]), max(b[2], box[2]), max(b[3], box[3])]
                    a = g['arrive_box']
                    g['arrive_box'] = [min(a[0], arrive[0]), min(a[1], arrive[1]), max(a[2], arrive[2]), max(a[3], arrive[3])]
                    break
            else:
                mine.append({'map': m, 'box': box, 'facing': p.flags >> 14, 'arrive_box': arrive})
        groups += mine
    return groups


def back_program(own_box, z, routes):
    """B program: routes [(arrive_box, (map, x, y, z))]. Each frame until one is found, the
    arrival area Alundra stands in picks the route (on the panel first: the first route);
    then it waits for him on the panel and sends him back with Change Map (effect 5, sound 74)."""
    def box(b, z1, z2):
        return bytes((0x3B, b[0], b[2], b[1], b[3], z1, z2))
    code = bytearray(b'\x00')
    jumps = []                                    # (at, route index, to the warp itself)
    for k, (arrive, _) in enumerate(routes):
        code += box(arrive, 0, 127)
        jumps.append((len(code), k, False))
        code += b'\x03\x00\x00'
    code += box(own_box, z, z)
    jumps.append((len(code), 0, True))
    code += b'\x03\x00\x00'
    code += struct.pack('<Bh', 0x02, -len(code))  # nothing yet: next frame
    starts, warps = [], []
    for _, (m, x, y, tz) in routes:
        loop = len(code)
        starts.append(loop)
        code += b'\x00' + box(own_box, z, z)
        code += struct.pack('<Bh', 0x04, loop - len(code))
        warps.append(len(code))
        code += struct.pack('<BH5B', 0x53, m, x, y, tz, WARP_EFFECT, WARP_SOUND)
        code += bytes((0x37, 0x3C))
        code += struct.pack('<Bh', 0x02, loop - len(code))
    for at, k, warp in jumps:
        struct.pack_into('<h', code, at + 1, (warps if warp else starts)[k] - at)
    return bytes(code) + b'\xff'


def _write_records(data, m, box, dest, arrive):
    from portal_records import Portal
    from area_map import grid
    start, rows = _portals(data, m)
    if len(rows) + 4 > 64:
        raise ValueError(f'Map {m} has no room for 4 more warps')
    x1, y1, x2, y2 = box
    flags = (arrive << 12) | WARP_LOW
    i = len(rows)
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            data[start + i * 12:start + i * 12 + 12] = Portal(x, y, x, y, dest[0], dest[1], dest[2], dest[3], flags).encode()
            i += 1
    w, h, cells = grid(_view(data), m)
    for y in range(y1, y2 + 1):
        for x in range(x1, x2 + 1):
            o = cells[y * w + x]['offset']
            data[o] |= 0x04
            data[o + 1] |= 0x80
    return list(range(len(rows), i))


def install(data, graphs):
    """Build every Save Room Portal. graphs: event graphs (map_id, region, native_placement).
    Fixed destinations first (they can lead into another portal's map), then the
    previous-location ones. Returns (data, reports)."""
    from area_map import grid
    from heal_tile import install_plates, panel_tiles, _entries
    from map_slots import map_exists
    from native_class_placement import record_cluster, append_record_cluster
    from native_script_allocation import append_native_process
    data = bytearray(data)
    reports = []
    by_map = {}
    for g in graphs:
        x, y = g['region'][:2]
        w, h, _ = grid(_view(data), g['map_id'])
        if not (0 <= x and x + 1 < w and 1 <= y < h):
            raise ValueError(f"{g.get('name')}: the Save Room Portal (2x2) does not fit there")
        by_map.setdefault(g['map_id'], []).append(g)
    for m, rows in by_map.items():
        data = bytearray(install_plates(data, m, [t for g in rows for t in panel_tiles(*g['region'][:2])]))
        w, h, cells = grid(_view(data), m)
        effects = _entries(record_cluster(data, m)['effects'])
        if len(effects) + len(rows) > MAX_EFFECTS:
            raise ValueError(f'Map {m} has no room for the portal swirl (at most {MAX_EFFECTS} effects)')
        for g in rows:
            x, y = g['region'][:2]
            effects.append(swirl_entry(w, h, x, y, cells[y * w + x]['values'][3]))
        data, _ = append_record_cluster(data, m, effects=b''.join(effects) + bytes(4))
        data = bytearray(data)
    ordered = sorted(graphs, key=lambda g: mode_of(g.get('native_placement')) == 'previous')
    programs = {}
    for g in ordered:
        m = g['map_id']
        x, y = g['region'][:2]
        box = rect(x, y)
        w, h, cells = grid(_view(data), m)
        z = cells[y * w + x]['values'][3]
        report = {'event_id': g.get('id'), 'map_id': m, 'name': g.get('name'), 'save_portal': True,
                  'tiles': list(box), 'swirl_effect': SWIRL_SPRITE, 'gameplay_verified': False}
        if mode_of(g.get('native_placement')) == 'destination':
            to = (g.get('native_placement') or {}).get('warp_to')
            if not isinstance(to, dict) or type(to.get('map')) is not int:
                raise ValueError(f"{g.get('name')}: choose where the Save Room Portal leads")
            if not 0 < to['map'] < 2547 or not map_exists(data, to['map']):
                raise ValueError(f"{g.get('name')}: the Save Room Portal leads to a map that does not exist")
            dest = (to['map'], int(to.get('x', 0)), int(to.get('y', 0)), int(to.get('z', 0) or 0))
            report.update(mode='destination', warp_to=list(dest),
                          warp_indices=_write_records(data, m, box, dest, int(to.get('facing', 0)) & 3))
        else:
            routes = []
            for e in entrances(data, m):
                rx, ry, rz, arrive = return_point(data, e['map'], e['box'], e['facing'])
                route = (e['arrive_box'], (e['map'], rx, ry, rz), arrive)
                if all(r[1] != route[1] for r in routes):
                    routes.append(route)
            if not routes:
                raise ValueError(f"{g.get('name')}: no warp leads to map {m}, so there is no previous location; "
                                 "choose a destination for the Save Room Portal")
            report.update(mode='previous', returns=[list(r[1]) for r in routes])
            if len(routes) == 1:
                report['warp_indices'] = _write_records(data, m, box, routes[0][1], routes[0][2])
            else:
                code = back_program(box, z, [(r[0], r[1]) for r in routes])
                data, allocation = append_native_process(data, m, 'B', code)
                data = bytearray(data)
                programs.setdefault(m, []).append(bytes((0, 0, w - 1, h - 1, allocation['hook_value'], 0, 0, 0)))
                report.update(bank='B', hook_value=allocation['hook_value'],
                              arrive_boxes=[list(r[0]) for r in routes])
        reports.append(report)
    for m, events in programs.items():
        cluster = record_cluster(data, m)
        data, _ = append_record_cluster(data, m, map_events=cluster['events'] + events)
        data = bytearray(data)
    return data, reports


# --- the picture ------------------------------------------------------------

def _glow(session):
    """The swirl's fullest frame (global effect 24, additive layer) as RGBA."""
    import sprite_blend
    from entity_preview import cached_preview
    from export_effects import effect_records, parse_effect
    pv = cached_preview(session, 0, True)
    base, anims = parse_effect(pv, effect_records(pv)[SWIRL_SPRITE])
    k = max((f['image'] for f in anims[0]['frames']), key=lambda i: i)
    pos = base + k
    _, count = pv.read('2B', pos)
    layers = sprite_blend.compose(pv, pos, count)[0]
    return (layers.get('add') or layers['normal']).convert('RGBA')


def preview(session):
    """The panel with the swirl drawn on it (48x32)."""
    from heal_tile import preview as panel_preview
    cache = getattr(session, '_save_portal_preview', None)
    if cache is not None:
        return cache
    from PIL import Image, ImageChops
    image = panel_preview(session, 'panel').copy()
    try:
        glow = _glow(session)
        box = glow.getbbox()
        if box:
            glow = glow.crop(box)
            layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
            layer.alpha_composite(glow, ((image.width - glow.width) // 2, (image.height - glow.height) // 2))
            alpha = layer.split()[3]
            lit = ImageChops.add(image.convert('RGB'), Image.composite(layer.convert('RGB'), Image.new('RGB', image.size), alpha))
            lit.putalpha(image.split()[3])
            image = lit
    except Exception:
        pass
    try:
        session._save_portal_preview = image
    except AttributeError:
        pass
    return image
