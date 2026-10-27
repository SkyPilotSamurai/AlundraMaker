"""Use Tile events (2026-10-21): an event whose graphic is a map tile picked from any map.

The editor never paints the tile onto the event's map. The tile is shown at the event in the
map view and in the event window, and only the game build puts its picture there (see
apply_tile_graphics): the floor picture, plus its wall pieces when Use as mask is ticked.
Walking and heights at that spot are left as they are, so the event has no hitbox.
"""


def tile_image(session, tile):
    """PIL image of the picked tile (its floor picture, else its first wall piece), or None."""
    from area_map import MapRenderer, grid
    try:
        w, h, cells = grid(session, tile['map'])
        cell = cells[tile['y'] * w + tile['x']]
        code = cell['values'][4]
        if code == 0xFFFF and cell['walls']:
            code = cell['walls'][0][1]
        if code == 0xFFFF:
            return None
        return MapRenderer(session, tile['map']).tile(code)
    except (ValueError, IndexError, KeyError):
        return None


def apply_tile_graphics(session, database, graphs):
    """Game build only: put each Use Tile event's picture at its tile in `session` (a build copy)."""
    from map_area_copy import copy_area
    done = 0
    for graph in graphs:
        placement = graph.get('native_placement') or {}
        tile = placement.get('tile_graphic')
        if not tile:
            continue
        x, y = graph['region'][:2]
        copy_area(session, database, tile['map'], (tile['x'], tile['y'], 1, 1), int(graph['map_id']), (x, y),
                  skip_empty=False, picture_only=bool(placement.get('tile_mask')))
        done += 1
    return done
