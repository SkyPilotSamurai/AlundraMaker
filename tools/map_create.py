"""Blank maps: clear a map's tiles, and make new maps.

New Map first uses the 17 brand-new map slots 483-499 (map_slots.py): a copy
of an unused original map block is appended to DATAS and blanked. When all 17
are in use, the editor offers Expand Maps (maps 500 and up, create_expanded_map;
after that New Map keeps adding them) or asks which existing map to save over
(Unused Maps or Game Maps tab) and blanks that one (blank_existing_map).

Blank means: every tile an empty floor at height 1 (walls removed), no
characters, events or warps, and the old tile art erased so all 960 tile slots
are free. Tiles then come from "Add map tiles".
"""
import struct
from area_map import grid
from map_names import map_is_reported_unused, map_label
from portal_records import Portal

BLANK_CELL = (0, 0, 4, 1, 0xFFFF, -1)   # walkability, ground, slope, height 1, no tile, no walls
EMPTY_PORTAL = Portal(0, 0, 255, 255, 0, 0, 0, 0, 0)


def clear_tiles_payload(session, m):
    w, h, cells = grid(session, m)
    start = cells[0]['offset']; end = cells[-1]['offset'] + 8
    payload = bytearray(session.data[start:end])
    for cell in cells:
        struct.pack_into('<4BHh', payload, cell['offset'] - start, *BLANK_CELL)
    return start, bytes(payload)


def clear_map_tiles(session, m):
    """Every tile: empty floor at height 1, walls removed. One undo step."""
    start, payload = clear_tiles_payload(session, m)
    session.replace(start, payload, f'Clear map {m}')


def record_edits(session, m):
    """Edits that remove characters, events and warps (table terminators / unused warp records)."""
    from map_inspector import inspect_map
    from warp_editor import warps
    info = inspect_map(bytes(session.data), m); edits = []
    if info['entities']:
        edits.append((int(info['entities'][0]['offset'], 16), bytes(20)))
    if info['events']:
        edits.append((int(info['events'][0]['offset'], 16), bytes(8)))
    for index, offset, _ in warps(session, m):
        edits.append((offset, EMPTY_PORTAL.encode()))
    return edits


def apply_edits(session, edits, label):
    """Several byte patches inside one map block as a single undo step."""
    start = min(o for o, raw in edits); stop = max(o + len(raw) for o, raw in edits)
    payload = bytearray(session.data[start:stop])
    for offset, raw in edits:
        payload[offset - start:offset - start + len(raw)] = raw
    session.replace(start, bytes(payload), label)


def blank_texture_edit(session, m):
    """Empty the slot's old tile art so imported tiles have room (zeros pack tiny)."""
    from texture_codec import pack_ez, unpack_ez
    old, start, end = session.texture(m)
    raw = bytes(len(old)); packed = pack_ez(raw, bytes(session.data[start:start + 6]))
    if unpack_ez(packed)[0] != raw or len(packed) > end - start:
        raise ValueError('Could not blank the new map texture')
    return start, packed + bytes(end - start - len(packed))


def map_block(data, m):
    start, end = struct.unpack_from('<2I', data, 0x28 + 4 * m)
    return bytes(data[start:end])


def free_map_slots(session, document):
    """Unused game maps this mod has not changed or used yet."""
    taken = set(document.get('created_maps', []))
    taken |= {g.get('map_id') for g in document.get('event_graphs', [])}
    taken |= {int(k) for k in document.get('map_music', {})}
    result = []
    for m in range(1, 483):
        if not map_is_reported_unused(m) or m in taken:
            continue
        if map_block(session.data, m) != map_block(session.original, m):
            continue
        try:
            grid(session, m)
        except ValueError:
            continue
        result.append(m)
    return result


def blank_existing_map(session, document, m):
    """Save a new blank map over existing map m (one undo step)."""
    start, payload = clear_tiles_payload(session, m)
    apply_edits(session, record_edits(session, m) + [(start, payload), blank_texture_edit(session, m)], f'New map over map {m}')
    if m not in document.setdefault('created_maps', []):
        document['created_maps'].append(m)
    return m, map_label(m)


def template_map(session):
    """Smallest original map the game never uses: copied as the new slot's block."""
    from map_slots import STOCK_MAPS
    offsets = struct.unpack_from(f'<{STOCK_MAPS + 1}I', session.original, 0x28)
    unused = [m for m in range(1, STOCK_MAPS) if map_is_reported_unused(m)]
    return min(unused, key=lambda m: offsets[m + 1] - offsets[m])


def create_new_slot(session, document):
    """Append a blank map in the next free new slot (483-499). One undo step."""
    from editor_session import EditSession
    from map_slots import extra_count, STOCK_MAPS, EXTRA_SLOTS, MAX_MAP_BYTES, TABLE
    k = extra_count(session.data)
    if k >= EXTRA_SLOTS:
        raise SlotsFull()
    m = STOCK_MAPS + k; source = template_map(session)
    offsets = struct.unpack_from(f'<{STOCK_MAPS + 1}I', session.original, TABLE)
    block = session.original[offsets[source]:offsets[source + 1]]
    if len(block) > MAX_MAP_BYTES or len(block) % 2048:
        raise ValueError('Template map block is not loadable')
    end = len(session.data)
    if struct.unpack_from('<I', session.data, TABLE + 4 * m)[0] != end:
        raise ValueError('New map slots are out of order; reload the mod')
    trial = EditSession(bytes(session.data) + block, None, verify=False)
    struct.pack_into('<I', trial.data, TABLE + 4 * (m + 1), end + len(block))
    blank_existing_map(trial, {}, m)
    entry = TABLE + 4 * (m + 1)
    session.set_tail(bytes(trial.data[len(session.original):]), f'New map {m}',
                     [(entry, bytes(trial.data[entry:entry + 4]))])
    slots = document.setdefault('new_map_slots', {})
    slots[str(m)] = {'template_map': source}
    return m, f'New Map {k + 1}'


def create_expanded_map(session, document):
    """Expand Maps: add map 500, 501, ... (after all 17 new slots). One undo step."""
    from editor_session import EditSession
    from map_slots import extra_count, offsets, serialize, EXTRA_SLOTS, MAX_MAPS, EXT_WORD, STOCK_MAPS, TABLE
    if extra_count(session.data) < EXTRA_SLOTS:
        return create_new_slot(session, document)
    values = offsets(session.data); m = len(values) - 1
    if m >= MAX_MAPS:
        raise ValueError(f'The editor supports up to {MAX_MAPS} maps')
    source = template_map(session)
    stock = struct.unpack_from(f'<{STOCK_MAPS + 1}I', session.original, TABLE)
    block = session.original[stock[source]:stock[source + 1]]
    data = serialize(bytes(session.data[:values[-1]]) + block, values + [values[-1] + len(block)])
    trial = EditSession(bytes(data), None, verify=False)
    blank_existing_map(trial, {}, m)
    session.set_tail(bytes(trial.data[len(session.original):]), f'New map {m}',
                     [(EXT_WORD, bytes(trial.data[EXT_WORD:EXT_WORD + 4]))])
    document.setdefault('new_map_slots', {})[str(m)] = {'template_map': source}
    document['expanded_maps'] = True
    return m, f'New Map {m - STOCK_MAPS + 1}'


def create_copy_of_map(session, document, source):
    """New map that is a full copy of `source` as it is now (tiles, walls,
    heights, characters, events, warps). Uses the next new slot (483-499), or
    an expanded map once those are used and maps were expanded. One undo step."""
    from editor_session import EditSession
    from map_slots import extra_count, offsets, serialize, EXTRA_SLOTS, STOCK_MAPS, TABLE, EXT_WORD, block_range
    start, end = block_range(session.data, source)
    block = bytes(session.data[start:end])
    k = extra_count(session.data)
    if k < EXTRA_SLOTS:
        m = STOCK_MAPS + k; tail_end = len(session.data)
        if struct.unpack_from('<I', session.data, TABLE + 4 * m)[0] != tail_end:
            raise ValueError('New map slots are out of order; reload the mod')
        data = bytearray(session.data) + block
        struct.pack_into('<I', data, TABLE + 4 * (m + 1), tail_end + len(block))
        entry = TABLE + 4 * (m + 1)
        session.set_tail(bytes(data[len(session.original):]), f'New map {m} (copy of map {source})',
                         [(entry, bytes(data[entry:entry + 4]))])
    else:
        if not document.get('expanded_maps'):
            raise SlotsFull()
        values = offsets(session.data); m = len(values) - 1
        data = serialize(bytes(session.data[:values[-1]]) + block, values + [values[-1] + len(block)])
        session.set_tail(bytes(data[len(session.original):]), f'New map {m} (copy of map {source})',
                         [(EXT_WORD, bytes(data[EXT_WORD:EXT_WORD + 4]))])
    slots = document.setdefault('new_map_slots', {})
    slots[str(m)] = {'template_map': source if source < STOCK_MAPS else slots.get(str(source), {}).get('template_map', 0),
                     'copied_from': source}
    return m


def _free_graph_id(base, used):
    """The next free ID in the same shape as `base` ('graph:17' -> 'graph:18')."""
    import re
    text = str(base or 'event')
    match = re.match(r'^(.*?)(\d+)$', text)
    stem, n = (match.group(1), int(match.group(2)) + 1) if match else (text + '-', 2)
    while f'{stem}{n}' in used:
        n += 1
    return f'{stem}{n}'


def copy_map_document(document, source, target):
    """Give a copied map its own copies of the project's events on `source`.

    Each copy keeps its pages, commands and native placement but gets its own
    ID, so its self switches and chest flag are its own. A donor on the source
    map becomes a donor on the copy: the copy's block holds the same characters
    at the same entity indices, with their map-local sprite banks and scripts.
    Without that, a copied boss (a map-local catalogue 256+ sprite) cannot be
    placed on the new map at all (native_class_placement rejects foreign local
    assets). The source map's music follows too; extra_maps_runtime.block_for
    also carries the sound bank its copied objects actually play in."""
    from copy import deepcopy
    graphs = document.setdefault('event_graphs', [])
    used = {g.get('id') for g in graphs}
    made = []
    for graph in [g for g in list(graphs) if g.get('map_id') == source]:
        row = deepcopy(graph)
        row['id'] = _free_graph_id(graph.get('id'), used); used.add(row['id'])
        row['map_id'] = target
        row.pop('chest_flag', None)          # its own saved "already opened" bit
        row.pop('compiled', None)
        placement = row.get('native_placement')
        if isinstance(placement, dict) and placement.get('donor_map_id') == source:
            placement['donor_origin_map'] = source
            placement['donor_map_id'] = target
        for page in row.get('pages') or []:
            page.pop('chest_flag', None)
        graphs.append(row); made.append(row)
    music = document.get('map_music') or {}
    if str(source) in music:
        document.setdefault('map_music', {})[str(target)] = music[str(source)]
    return made


class SlotsFull(ValueError):
    def __init__(self):
        super().__init__('All 17 new map slots are in use')


def overwrite_choices(session, document):
    """(unused maps, game maps) the user can save a new map over."""
    from map_slots import STOCK_MAPS
    free = set(free_map_slots(session, document))
    unused = [m for m in range(1, STOCK_MAPS) if map_is_reported_unused(m)]
    game = [m for m in range(1, STOCK_MAPS) if not map_is_reported_unused(m)]
    return [m for m in unused], game, free


def create_map(session, document):
    """Next new slot; once all 17 are used, raises SlotsFull (the editor asks:
    save over a map, or Expand Maps) unless maps were already expanded."""
    from map_slots import extra_count, EXTRA_SLOTS
    if extra_count(session.data) >= EXTRA_SLOTS and document.get('expanded_maps'):
        return create_expanded_map(session, document)
    return create_new_slot(session, document)