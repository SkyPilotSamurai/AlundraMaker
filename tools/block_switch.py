"""Block Switch Orb: the orb from Giles' nightmare (maps 41 / 42) that raises
and lowers the Red and Blue Blocks, as a placeable database object.

What the game does (map 41, B3):
* the orb is map 41's own effect sprite 0 (an orb on a short stand; animation 0
  dark, 1 glowing), placed by the map's effect table (flags C0: own sprite,
  shown from the start);
* a map-event program tests whether an attack hits the orb (95 x y z w h - mask
  0809 element 0); when it does and the orb's colour is not already down, it
  lowers that colour and raises the other (flags 02AD = blue down, 02AE = red
  down), plays sound F2 and makes this orb dark and the other one glow (92).
* the blocks (catalogue 361) wait on those flags: lowered / raised.

Placed copies of the blocks run their map-41 scripts with the flags moved to
room flags (82AD / 82AE, behavior_transplant), so the orb uses the same room
flags. Here each orb is its own map-event program (whole map, so it always
runs): it glows while its colour is up and goes dark while it is down, and it
can start with its colour already lowered ("Active by default"). The orb
sprite is copied from map 41 into the map's effect bank (import_local_effect).
"""
import struct

DONOR_MAP = 41
DONOR_EFFECT = 0
FLAGS = {'blue': 0x82AD, 'red': 0x82AE}
HIT_MASK = 0x0809
SOUND = 0xF2
MAX_PAGES = 5
MAX_PALETTES = 41


def kind_of(definition):
    source = (definition or {}).get('source', {})
    return source.get('lowers', 'blue') if source.get('variant') == 'block_switch' else None


# --- the orb sprite -----------------------------------------------------------

def effect_assets(data, map_id, index):
    """Bounds, pieces, pages and palettes of map-local effect `index`."""
    from local_sprite_import import layout
    b, h, s, e, sh = layout(data, map_id)
    table = [struct.unpack_from('<i', data, s + sh[4] + 4 * i)[0] for i in range((sh[5] - sh[4]) // 4)]
    entries = []
    for value in table:
        if value == 0:
            break
        entries.append(value)
    if not 0 <= index < len(entries) or entries[index] in (0, -1):
        raise ValueError(f'Map {map_id} has no effect sprite {index}')
    relative = entries[index]
    base = s + relative
    first = struct.unpack_from('<h', data, base)[0]
    if not 0 < first <= 512 or first % 2:
        raise ValueError('Unsupported effect record')
    end = base + first
    image_sets = set()
    for a in range(first // 2):
        p = base + struct.unpack_from('<h', data, base + 2 * a)[0]
        for _ in range(256):
            flag = data[p]
            if not flag & 0x80:
                p += 2 if flag == 0 else 1
                break
            k = struct.unpack_from('<H', data, p + 1)[0] * 2
            if k != 0xFFFF * 2:
                image_sets.add(k)
            p += 3
        end = max(end, p)
    quads = []
    for k in image_sets:
        at = base + k
        count = data[at + 1]
        if count > 64 or at + 2 + 14 * count > e:
            raise ValueError('Effect image set outside its section')
        quads += [at + 2 + 14 * i for i in range(count)]
        end = max(end, at + 2 + 14 * count)
    return dict(record=base, relative=relative, end=end, quads=sorted(set(quads)),
                pages={data[q] & 7 for q in quads}, palettes={data[q + 1] for q in quads},
                table=entries)


def import_local_effect(data, target_map, donor_map, index):
    """Copy map-local effect sprite `index` of donor_map into target_map's effect
    bank (texture pages and palettes it uses included). Returns (data, new index).
    Like local_sprite_import.import_local_sprite: nothing of the target moves;
    the section is rebuilt with the new record, then its palettes and record
    lists after it (the effect table grows into the old palette room)."""
    from local_sprite_import import layout, sprite_assets
    from map_block_repack import replace_section
    from map_loader_constraints import validate_layout
    from texture_codec import unpack_ez, pack_ez
    from native_class_placement import record_cluster
    tb, th, ts, te, tsh = layout(data, target_map)
    db, dh, ds, de, dsh = layout(data, donor_map)
    donor = effect_assets(data, donor_map, index)
    table = []
    for i in range((tsh[5] - tsh[4]) // 4):
        value = struct.unpack_from('<i', data, ts + tsh[4] + 4 * i)[0]
        if value == 0:
            break
        table.append(value)
    slot = len(table)
    used = set()
    for i in range((tsh[4] - tsh[3]) // 4):
        p = struct.unpack_from('<i', data, ts + tsh[3] + 4 * i)[0]
        if p not in (0, -1):
            try:
                used |= sprite_assets(data, target_map, i)['pages']
            except ValueError:
                pass
    for i in range(slot):
        try:
            used |= effect_assets(data, target_map, i)['pages']
        except ValueError:
            used |= set(range(MAX_PAGES))
    if any(p >= MAX_PAGES for p in donor['pages']):
        raise ValueError('Effect uses a texture page past the native bound')
    draw, _ = unpack_ez(data[db + dh[4]:db + dh[5]], limit=262144)
    traw, _ = unpack_ez(data[tb + th[4]:tb + th[5]], limit=262144)
    page_map = {}
    for old in sorted(donor['pages']):
        chunk = draw[old * 32768:(old + 1) * 32768]
        same = next((p for p in range(len(traw) // 32768) if traw[p * 32768:(p + 1) * 32768] == chunk), None)
        if same is not None:
            page_map[old] = same
    free = [p for p in range(MAX_PAGES) if p not in used and p not in page_map.values()]
    for old in sorted(donor['pages']):
        if old not in page_map:
            if not free:
                raise ValueError(f'Map {target_map} has no free texture page for the Block Switch Orb')
            page_map[old] = free.pop(0)
    needed = max([len(traw)] + [(p + 1) * 32768 for p in page_map.values()])
    traw = bytearray(traw + bytes(needed - len(traw)))
    for old, new in page_map.items():
        traw[new * 32768:(new + 1) * 32768] = draw[old * 32768:(old + 1) * 32768]
    tcount = (tsh[6] - tsh[5]) // 32
    dcount = (dsh[6] - dsh[5]) // 32
    tpad = bytes(data[ts + tsh[5] + 32 * tcount:ts + tsh[6]])
    if tpad != bytes(4):
        raise ValueError('Unsupported target palette table terminator')
    palettes = [bytes(data[q:q + 32]) for q in range(ts + tsh[5], ts + tsh[5] + 32 * tcount, 32)]
    mapping = {}
    for i in sorted(donor['palettes']):
        if i >= dcount:
            raise ValueError('Effect palette outside its table')
        palette = bytes(data[ds + dsh[5] + 32 * i:ds + dsh[5] + 32 * i + 32])
        if palette not in palettes:
            palettes.append(palette)
        mapping[i] = palettes.index(palette)
    if len(palettes) > MAX_PALETTES:
        raise ValueError('Palette count past the native bound')
    section = bytearray(data[ts:te])
    section.extend(bytes((-len(section)) % 4))
    start = len(section)
    payload = bytearray(data[donor['record']:donor['end']])
    for q in donor['quads']:
        q -= donor['record']
        payload[q] = (payload[q] & 0xF8) | page_map[payload[q] & 7]
        payload[q + 1] = mapping[payload[q + 1]]
    section.extend(payload)
    section.extend(bytes((-len(section)) % 4))
    roots = list(tsh)
    # the effect table keeps its place and grows into the old palettes' room
    if tsh[4] + 4 * (slot + 2) > tsh[6]:
        raise ValueError(f'Map {target_map} has no room for another effect sprite')
    roots[5] = len(section)
    section.extend(b''.join(palettes) + tpad)
    shift = len(section) - tsh[6]
    section.extend(data[ts + tsh[6]:ts + tsh[0]])
    for i in range(6, 12):
        roots[i] = tsh[i] + shift
    cluster = record_cluster(data, target_map)
    roots[0] = len(section)
    section.extend(b''.join(cluster['entities']) + cluster['entity_terminator'])
    roots[1] = len(section)
    section.extend(cluster['effects'])
    roots[2] = len(section)
    section.extend(b''.join(cluster['events']) + bytes(4))
    section.extend(bytes((-len(section)) % 4))
    struct.pack_into('<12I', section, 0, *roots)
    struct.pack_into('<ii', section, tsh[4] + 4 * slot, start, 0)
    page_head = bytes(data[tb + th[4]:tb + th[4] + 6])   # read before data may change in place
    result = replace_section(data, target_map, 3, section)
    packed = pack_ez(bytes(traw), page_head)
    packed += bytes((-len(packed)) % 4)
    result = replace_section(result, target_map, 4, packed)
    validate_layout(result)
    check = effect_assets(result, target_map, slot)
    if check['pages'] != set(page_map.values()):
        raise ValueError('Effect page remapping failed')
    return bytearray(result), slot


# --- the program ----------------------------------------------------------------

def orb_program(x, y, z, effect, lowers, active, keep=None):
    """B program of one orb at tile (x, y), floor height z, map effect entry
    `effect`. Glows while its colour is up (hit it to lower that colour and
    raise the other), dark while it is down. The colour flags are room flags,
    so everything goes back to the start on entering the room; keep = (test
    on, set on, set off) bytes of the orb's private switch (Keep State Upon
    Leaving Room): it remembers whether its colour is down and puts it back."""
    own, other = FLAGS[lowers], FLAGS['red' if lowers == 'blue' else 'blue']
    hit = bytes((0x95, x, max(0, y - 1), z, 1, 2, 4)) + struct.pack('<H', HIT_MASK) + bytes((0,))
    lower = struct.pack('<BHBH', 0x05, own, 0x06, other)
    if keep:
        test_on, set_on, set_off = keep
        start = test_on + struct.pack('<Bh', 0x04, 3 + len(lower)) + lower
    else:
        set_on = set_off = b''
        start = lower if active else b''
    body = bytearray()
    l0 = 0
    body += b'\x00'
    test_at = len(body)
    body += b'\x30' + struct.pack('<H', own) + b'\x00\x00'
    body += set_off + bytes((0x92, effect, 1))
    body += hit
    miss_at = len(body)
    body += b'\x04\x00\x00'
    body += struct.pack('<BHBH', 0x06, other, 0x05, own) + bytes((0xBD, SOUND, 0))
    back_at = len(body)
    body += b'\x02\x00\x00'
    dark = len(body)
    body += set_on + bytes((0x92, effect, 0))
    back2_at = len(body)
    body += b'\x02\x00\x00'
    struct.pack_into('<h', body, test_at + 3, dark - test_at)
    struct.pack_into('<h', body, miss_at + 1, l0 - miss_at)
    struct.pack_into('<h', body, back_at + 1, l0 - back_at)
    struct.pack_into('<h', body, back2_at + 1, l0 - back2_at)
    return start + bytes(body) + b'\xff'


def install_switches(data, graphs, keep=None):
    """Build every Block Switch Orb: the orb sprite (once per map), an effect
    entry at each orb, its map-event program, and no walking through it.
    graphs: [(graph, lowers)]; keep: {event id: (test on, set on, set off)} for
    orbs that keep their state. Returns (data, reports)."""
    from area_map import grid
    from heal_tile import _View, _entries, MAX_EFFECTS
    from native_script_allocation import append_native_process
    from native_class_placement import record_cluster, append_record_cluster
    reports = []
    by_map = {}
    for graph, lowers in graphs:
        by_map.setdefault(graph['map_id'], []).append((graph, lowers))
    for map_id, rows in by_map.items():
        data, sprite = import_local_effect(data, map_id, DONOR_MAP, DONOR_EFFECT)
        w, h, cells = grid(_View(data), map_id)
        effects = _entries(record_cluster(data, map_id)['effects'])
        placed = []
        for graph, lowers in rows:
            x, y, rw, rh = graph['region']
            if (rw, rh) != (1, 1):
                raise ValueError(f"{graph['name']}: a Block Switch Orb stands on one tile")
            for page in graph.get('pages') or []:
                if page.get('commands') or any(hh.get('commands') for hh in page.get('trigger_actions') or []):
                    raise ValueError(f"{graph['name']}: a Block Switch Orb only raises and lowers the blocks; it takes no actions")
            z = cells[y * w + x]['values'][3]
            if len(effects) >= MAX_EFFECTS:
                raise ValueError(f'Map {map_id} has no room for another effect')
            effects.append(bytes((0, 0, w - 1, h - 1, 0xC0, sprite, 2 * x + 1, 2 * y + 1, 2 * z, 1, 0, 0)))
            placed.append((graph, lowers, x, y, z, len(effects) - 1))
        data, _ = append_record_cluster(data, map_id, effects=b''.join(effects) + bytes(4))
        data = bytearray(data)
        events = []
        for graph, lowers, x, y, z, effect in placed:
            active = bool((graph.get('native_placement') or {}).get('active_by_default'))
            data, allocation = append_native_process(data, map_id, 'B', orb_program(x, y, z, effect, lowers, active, (keep or {}).get(graph['id'])))
            data = bytearray(data)
            events.append(bytes((0, 0, w - 1, h - 1, allocation['hook_value'], 0, 0, 0)))
            at = cells[y * w + x]['offset']
            data[at] = (data[at] & ~0x41) | 0x41      # nobody walks through the orb
            reports.append({'event_id': graph['id'], 'map_id': map_id, 'name': graph.get('name'),
                            'block_switch': lowers, 'tile': [x, y, z], 'effect_entry': effect, 'effect_sprite': sprite,
                            'active_by_default': active, 'keep_state': bool((keep or {}).get(graph['id'])), 'hook_value': allocation['hook_value'], 'bank': 'B',
                            'source': "Giles' nightmare orb (map 41 effect 0, B3)", 'gameplay_verified': False})
        cluster = record_cluster(data, map_id)
        data, _ = append_record_cluster(data, map_id, map_events=cluster['events'] + events)
        data = bytearray(data)
    return data, reports


def preview(session):
    """The orb picture (map 41's effect sprite 0, glowing frame) for the editor."""
    from PIL import Image
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / 'assets/engine/maps/041/effects/000'
    for name in ('16.png',):
        p = root / name
        if p.exists():
            with Image.open(p) as im:
                return im.convert('RGBA')
    return None
