"""Copy whole areas of another map (floor, walls, heights, slopes, collision).

Format (xcasadio DatasBin/Map.cs, MapTile.cs): section 1 of a map block is
  w, h, w2, h2 (4 bytes) | 256 map-copy rectangles x 6 bytes | w*h cells x 8
  (walkability, ground, slope, height, tile id, wall-list offset in halfwords
  or -1) | wall lists (signed shift, count, count x tile id).
An area copy writes the source cells into the destination rectangle, imports
every floor/wall tile picture they use (map_tile_import, palettes matched),
rebuilds the wall lists of the whole map and stores the map block again as
one undo step. Map-copy rectangles (used by story scripts) are left alone.
"""
import struct
from area_map import grid

HEADER = 4 + 256 * 6


def apply_block(session, m, block, label):
    """Store map m's block as one undo step.

    Same padded size: written in place. New maps (483+, after the original
    data) may grow freely. An original map can only use its own spare space."""
    from map_block_repack import pointers, replace_block, sections
    sections(block)
    values = pointers(session.data); start, end = values[m], values[m + 1]
    padded = bytes(block) + bytes((-len(block)) % 2048)
    if len(padded) == end - start:
        session.replace(start, padded, label)
        return
    if start < len(session.original):
        raise ValueError(f'Map {m} is an original map with no spare room for this change; '
                         'build on a new map (Map > New Map) instead')
    new = replace_block(session.data, m, bytes(block))
    n = len(session.original)
    changes = [(o, bytes(new[o:o + 4])) for o in range(0, 0x800, 4) if new[o:o + 4] != session.data[o:o + 4]]
    session.set_tail(bytes(new[n:]), label, changes)


def _map_section(session, m):
    from map_block_repack import pointers, sections
    values = pointers(session.data)
    block = bytes(session.data[values[m]:values[m + 1]])
    h = sections(block)
    return block, h


def rebuild_grid(session, m, cells_out, label):
    """cells_out: list (row-major) of dicts with values (6-tuple) and walls
    (shift, [codes]) or None. Rebuilds section 1 and stores the block."""
    block, h = _map_section(session, m)
    section = block[h[1]:h[2]]
    w, hh = section[0], section[1]
    if len(cells_out) != w * hh:
        raise ValueError('Cell count differs from the map grid')
    pool = bytearray(); seen = {}
    cell_bytes = bytearray()
    for cell in cells_out:
        walk, ground, slope, height, tile, _ = cell['values']
        pointer = -1
        walls = cell.get('walls')
        if walls:
            shift, codes = walls
            key = (shift, tuple(codes))
            if key not in seen:
                seen[key] = len(pool) // 2
                pool += struct.pack('<bB', shift, len(codes)) + struct.pack(f'<{len(codes)}H', *codes)
            pointer = seen[key]
            if pointer > 32767:
                raise ValueError('Too many different wall stacks on this map')
        cell_bytes += struct.pack('<4BHh', walk, ground, slope, max(0, min(255, height)), tile, pointer)
    new_section = bytes(section[:HEADER]) + bytes(cell_bytes) + bytes(pool)
    new_section += bytes((-len(new_section)) % 4)
    if len(new_section) < len(section):
        new_section += bytes(len(section) - len(new_section))
    delta = len(new_section) - len(section)
    new_block = bytearray(block[:h[1]] + new_section + block[h[2]:])
    shifted = [v + (delta if i > 1 else 0) for i, v in enumerate(h)]
    struct.pack_into('<7I', new_block, 0, *shifted)
    apply_block(session, m, bytes(new_block), label)


def cells_of(session, m):
    w, hh, cells = grid(session, m)
    out = []
    for c in cells:
        walls = None
        if c['walls']:
            walls = (c['walls'][0][2], [code for _, code, _, _ in c['walls']])
        out.append(dict(values=tuple(c['values']), walls=walls))
    return w, hh, out


def copy_area(session, database, source, rect, target, at, height_delta=0, erase_unused=False,
              skip_empty=True, picture_only=None):
    """Copy rect (x, y, w, h) of `source` to `target` with its top-left at `at`.

    Floor tiles, wall stacks, heights (+height_delta), slopes and collision come
    along; tile pictures are imported into the target. Empty source cells are
    skipped (the target keeps what it has) unless skip_empty is False.
    picture_only (tile event graphics): None copies everything; False/True keep the
    target's height and collision and copy only the floor picture, plus the source's
    wall pieces (drawn over the player) when True.
    Returns the number of cells written."""
    group = session.group(f'Copy area from map {source}') if hasattr(session, 'group') else None
    if group is not None:
        with group:
            return _copy_area(session, database, source, rect, target, at, height_delta, erase_unused, skip_empty, picture_only)
    return _copy_area(session, database, source, rect, target, at, height_delta, erase_unused, skip_empty, picture_only)


def _copy_area(session, database, source, rect, target, at, height_delta, erase_unused, skip_empty, picture_only=None):
    from map_tile_import import import_tiles
    x0, y0, rw, rh = rect; ax, ay = at
    sw, sh, src = cells_of(session, source)
    codes = []
    for y in range(y0, y0 + rh):
        for x in range(x0, x0 + rw):
            if not (0 <= x < sw and 0 <= y < sh):
                continue
            cell = src[y * sw + x]
            if cell['values'][4] != 0xFFFF:
                codes.append(cell['values'][4])
            if cell['walls'] and picture_only is not False:
                codes.extend(c for c in cell['walls'][1] if c != 0xFFFF)
    mapping = {}
    if codes and source != target:
        try:
            mapping = import_tiles(session, database, target, source, codes, erase_unused=erase_unused)
        except ValueError as error:
            if erase_unused or ('padding space' not in str(error) and 'No unused blank' not in str(error)):
                raise
            mapping = import_tiles(session, database, target, source, codes, erase_unused=True)
    remap = (lambda code: code if code == 0xFFFF or source == target else mapping.get(code, code))
    tw, th, dst = cells_of(session, target)
    written = 0
    for y in range(rh):
        for x in range(rw):
            sx, sy, tx, ty = x0 + x, y0 + y, ax + x, ay + y
            if not (0 <= sx < sw and 0 <= sy < sh and 0 <= tx < tw and 0 <= ty < th):
                continue
            cell = src[sy * sw + sx]
            if skip_empty and cell['values'][4] == 0xFFFF and not cell['walls']:
                continue
            walk, ground, slope, height, tile, _ = cell['values']
            if picture_only is not None:
                old = dst[ty * tw + tx]; v = old['values']
                walls = (cell['walls'][0], [remap(c) for c in cell['walls'][1]]) if picture_only and cell['walls'] else old['walls']
                dst[ty * tw + tx] = dict(values=(v[0], v[1], v[2], v[3], remap(tile), -1), walls=walls)
                written += 1
                continue
            walls = None
            if cell['walls']:
                walls = (cell['walls'][0], [remap(c) for c in cell['walls'][1]])
            dst[ty * tw + tx] = dict(values=(walk, ground, slope, height + height_delta, remap(tile), -1), walls=walls)
            written += 1
    rebuild_grid(session, target, dst, f'Copy area from map {source}')
    return written


def raise_area(session, target, rect, delta, label='Raise area'):
    """Add `delta` to the height of every tile in rect (stairs, platforms)."""
    tw, th, dst = cells_of(session, target)
    x0, y0, rw, rh = rect
    for y in range(max(0, y0), min(th, y0 + rh)):
        for x in range(max(0, x0), min(tw, x0 + rw)):
            c = dst[y * tw + x]; v = list(c['values'])
            v[3] = max(0, min(255, v[3] + delta)); c['values'] = tuple(v)
    rebuild_grid(session, target, dst, label)


def clear_area(session, target, rect, label='Clear area'):
    """Empty tiles (no floor, no walls, height 1) in rect."""
    tw, th, dst = cells_of(session, target)
    x0, y0, rw, rh = rect
    for y in range(max(0, y0), min(th, y0 + rh)):
        for x in range(max(0, x0), min(tw, x0 + rw)):
            dst[y * tw + x] = dict(values=(0, 0, 4, 1, 0xFFFF, -1), walls=None)
    rebuild_grid(session, target, dst, label)
