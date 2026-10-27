"""Delete maps the project added (map 483 and up).

The game's own maps 0-482 cannot be deleted: its tables, doors and story
scripts address them by number. Clear one instead (Map > Clear current map) or
save a new blank map over it (map_create.blank_existing_map).

Deleting a new map takes its block out of DATAS, moves every map above it down
one number, and follows every reference to those numbers:
  * the door (portal) records of every map: doors leading to the deleted map
    are emptied, doors leading to a later map keep leading there;
  * the project document: events, placements, instances, names, music, new map
    slots and the start point.
All of it is one undo step.
"""
import struct
from copy import deepcopy
from map_slots import STOCK_MAPS, map_count, offsets, serialize
from map_names import map_label

# document fields that hold a map number
SCALAR_KEYS = ('map_id', 'donor_map_id', 'donor_origin_map', 'destination_map',
               'template_map', 'copied_from', 'observed_map', 'dialogue_sprite_map',
               'home_map', 'source_map')
LIST_KEYS = ('observed_maps', 'fixed_donor')
# document tables keyed by the map number as text
MAP_TABLES = ('map_names', 'map_music', 'new_map_slots')


def can_delete(session, m):
    """Raise unless map m is one this project added and can be taken out."""
    if type(m) is not int:
        raise ValueError('Choose a map to delete')
    if m < STOCK_MAPS:
        raise ValueError(f'{map_label(m)} is one of the game\'s own maps and cannot be deleted. '
                         'Use Map > Clear current map, or New Map saved over it.')
    if m >= map_count(session.data):
        raise ValueError(f'Map {m} does not exist')
    values = offsets(session.data)
    if values[m] < len(session.original):
        raise ValueError('Only maps this project added can be deleted')
    if (values[m + 1] - values[m]) % 2048:
        raise ValueError('That map block is not sector aligned; reload the mod')
    return True


def doors_to(session, m):
    """[(map, warp index, offset)] of every door on another map leading to m."""
    from warp_editor import warps
    found = []
    for other in range(map_count(session.data)):
        if other == m:
            continue
        try:
            rows = warps(session, other)
        except (ValueError, IndexError, struct.error):
            continue
        found += [(other, index, offset) for index, offset, p in rows if p.destination_map == m]
    return found


def references(session, document, m):
    """What points at map m (shown before deleting)."""
    document = document or {}
    graphs = [g for g in document.get('event_graphs') or [] if g.get('map_id') == m]
    commands = []
    for g in document.get('event_graphs') or []:
        if g.get('map_id') == m:
            continue
        def scan(node):
            if isinstance(node, dict):
                if 'type' in node and node.get('map_id') == m:
                    commands.append((g.get('id'), node.get('type')))
                for value in node.values():
                    scan(value)
            elif isinstance(node, list):
                for value in node:
                    scan(value)
        scan(g.get('pages') or [])
    return dict(doors=doors_to(session, m), events=graphs, warp_commands=commands,
                instances=[i for i in document.get('instances') or [] if i.get('map_id') == m])


def _renumber_doors(session, m, label):
    from dataclasses import replace
    from warp_editor import warps
    for other in range(map_count(session.data)):
        if other == m:
            continue                      # its own records go with the block
        try:
            rows = warps(session, other)
        except (ValueError, IndexError, struct.error):
            continue
        gone = []
        for index, offset, p in rows:
            if p.destination_map == m:
                gone.append(index)
            elif p.destination_map > m:
                session.replace(offset, replace(p, destination_map=p.destination_map - 1).encode(), label)
        # Doors to the deleted map are removed with the later doors moved up:
        # an emptied slot would end the table and switch off the doors after it.
        from warp_editor import delete_warp
        for index in reversed(gone):
            delete_warp(session, other, index)


def _remove_block(session, m, label):
    """Take map m's block out of the grown data and rewrite the offset tables."""
    values = offsets(session.data)
    start, end = values[m], values[m + 1]
    size = end - start
    body = bytearray(session.data[:start])
    body += bytes(session.data[end:values[-1]])          # the old extended table is rebuilt
    new_values = values[:m] + [v - size for v in values[m + 1:]]
    data = serialize(body, new_values)
    n = len(session.original)
    changes = [(o, bytes(data[o:o + 4])) for o in range(0, 0x800, 4)
               if data[o:o + 4] != session.data[o:o + 4]]
    session.set_tail(bytes(data[n:]), label, changes)


def remap_document(document, m):
    """A copy of the document with map m gone and later maps one number lower."""
    doc = deepcopy(document)
    doc['event_graphs'] = [g for g in doc.get('event_graphs') or [] if g.get('map_id') != m]
    doc['instances'] = [i for i in doc.get('instances') or [] if i.get('map_id') != m]

    def shift(value):
        return None if value == m else (value - 1 if value > m else value)

    def warps_to_deleted(node):
        # an event command that warps to the deleted map (it would have no destination)
        return isinstance(node, dict) and 'type' in node and node.get('map_id') == m

    def walk(node):
        if isinstance(node, list):
            node[:] = [v for v in node if not warps_to_deleted(v)]
        if isinstance(node, dict):
            for key, value in list(node.items()):
                if key in SCALAR_KEYS and type(value) is int:
                    node[key] = shift(value)
                elif key in LIST_KEYS and isinstance(value, list):
                    node[key] = [shift(v) for v in value if not (type(v) is int and v == m)]
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(doc)

    for key in MAP_TABLES:
        table = doc.get(key)
        if isinstance(table, dict):
            doc[key] = {str(shift(int(k))): v for k, v in table.items()
                        if str(k).isdigit() and int(k) != m}
    doc['created_maps'] = [shift(v) for v in doc.get('created_maps') or [] if v != m]
    return doc


def _forget_caches(session, m):
    pending = getattr(session, '_pending_textures', None)
    if pending:
        session._pending_textures = {(k - 1 if k > m else k): v for k, v in pending.items() if k != m}
    if hasattr(session, '_texture_cache'):
        session._texture_cache = {}


def delete_map(session, document, m):
    """Delete new map m. One undo step; returns the map number that was removed."""
    can_delete(session, m)
    label = f'Delete map {m}'
    with session.group(label):
        _renumber_doors(session, m, label)
        _remove_block(session, m, label)
        if document is not None:
            session.replace_document(document, remap_document(document, m), label)
    _forget_caches(session, m)
    return m