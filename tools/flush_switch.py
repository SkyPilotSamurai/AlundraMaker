"""Flush step-on switch: the step-on switch (class 301, map-local slot 45)
drawn as only its glowing top, level with the floor, usable on any map.

What it is: a copy of the switch's own sprite record, put into a free
map-local sprite slot of the map being built, with
* every frame cut to the top 16 texture rows (the lit face) and drawn
  centred on the tile at floor level (corners y -8..8 instead of -24..8);
* the collision box sunk below the floor (top level with the tiles) so Alundra walks onto it.
Texture pages and palettes are the switch's own (identical pages are shared,
nothing is redrawn). The sprite's built-in callbacks stay those of the
switch, so the editor's recovered floor-switch controller (class 301) drives
it unchanged. Not verified in game: whether the native standing test (3E)
fires on a 1-unit-high actor needs an emulator check.
"""
import struct

SWITCH_SLOT = 45          # class 301 = 256 + 45
DONOR_MAP = 1             # the recovered floor-switch donor map
FACE_ROWS = 16            # texture rows of the lit top face
UNUSED_SLOTS = tuple(c - 256 for c in (0x1B3, 0x1B4, 0x1B7, 0x1BA, 0x1C3, 0x1C9, 0x1D2))   # never placed and no sprite on any stock map


def _free_slot(data, target_map, keep=()):
    from local_sprite_import import layout
    from native_class_placement import record_cluster
    _, _, ts, _, tsh = layout(data, target_map)
    in_use = {raw[6] for raw in record_cluster(data, target_map)['entities'] if raw[5] & 128} | set(keep)
    count = (tsh[4] - tsh[3]) // 4
    # Only slots of classes no stock map ever uses (the catalogue's unused
    # source definitions 1A0-1D2), so no class AI/balance identity is borrowed.
    for slot in UNUSED_SLOTS:
        if slot >= count or slot in in_use:
            continue
        if struct.unpack_from('<i', data, ts + tsh[3] + slot * 4)[0] in (0, -1):
            return slot
    raise ValueError(f'Map {target_map} has no free character slot for the flush switch')


def copy_sprite(data, target_map, donor_map, donor_slot, target_slot):
    """local_sprite_import.import_local_sprite, but into a different slot (and
    the donor may be the target map itself)."""
    from local_sprite_import import layout, sprite_assets, MAX_PAGES, MAX_PALETTES
    from texture_codec import unpack_ez, pack_ez
    from map_block_repack import replace_section
    from map_loader_constraints import validate_layout
    from native_class_placement import record_cluster
    tb, th, ts, te, tsh = layout(data, target_map)
    db, dh, ds, de, dsh = layout(data, donor_map)
    donor = sprite_assets(data, donor_map, donor_slot)
    if any(p >= MAX_PAGES for p in donor['pages']):
        raise ValueError('Switch sprite outside the five-page bound')
    draw, _ = unpack_ez(data[db + dh[4]:db + dh[5]], limit=262144)
    traw, _ = unpack_ez(data[tb + th[4]:tb + th[5]], limit=262144)
    has_effects = False
    for at in range(ts + tsh[4], ts + tsh[5], 4):
        value = struct.unpack_from('<i', data, at)[0]
        if value == 0:
            break
        if value != -1:
            has_effects = True
    used = set()
    for i in range((tsh[4] - tsh[3]) // 4):
        p = struct.unpack_from('<i', data, ts + tsh[3] + i * 4)[0]
        if p not in (0, -1):
            try:
                used.update(sprite_assets(data, target_map, i)['pages'])
            except ValueError:
                pass
    if has_effects:
        used.update(range((len(traw) + 32767) // 32768))
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
                raise ValueError(f'Map {target_map} has no free sprite texture page for the flush switch')
            page_map[old] = free.pop(0)
    needed = max([len(traw)] + [(p + 1) * 32768 for p in page_map.values()])
    traw = bytearray(traw + bytes(needed - len(traw)))
    for old, new in page_map.items():
        traw[new * 32768:(new + 1) * 32768] = draw[old * 32768:(old + 1) * 32768]
    tcount = (tsh[6] - tsh[5]) // 32; dcount = (dsh[6] - dsh[5]) // 32
    tpad = bytes(data[ts + tsh[5] + 32 * tcount:ts + tsh[6]])
    if tpad != bytes(4):
        raise ValueError('Unsupported target palette table terminator')
    palettes = [bytes(data[q:q + 32]) for q in range(ts + tsh[5], ts + tsh[5] + 32 * tcount, 32)]
    mapping = {}
    for index in sorted(donor['palettes']):
        if index >= dcount:
            raise ValueError('Donor palette outside native table')
        palette = bytes(data[ds + dsh[5] + index * 32:ds + dsh[5] + index * 32 + 32])
        if palette not in palettes:
            palettes.append(palette)
        mapping[index] = palettes.index(palette)
    if len(palettes) > MAX_PALETTES:
        raise ValueError(f'Map {target_map} has no free sprite palette for the flush switch')
    section = bytearray(data[ts:te]); section.extend(bytes((-len(section)) % 4))
    start = len(section); payload = bytearray(data[donor['record']:donor['end']])
    delta = start - donor['relative']
    struct.pack_into('<4I', payload, 0, *[p + delta for p in donor['roots']])
    for q in donor['quads']:
        q -= donor['record']
        payload[q] = (payload[q] & 0xf8) | page_map[payload[q] & 7]
        payload[q + 1] = mapping[payload[q + 1]]
    section.extend(payload); section.extend(bytes((-len(section)) % 4))
    roots = list(tsh); roots[5] = len(section); section.extend(b''.join(palettes) + tpad)
    shift = len(section) - tsh[6]
    section.extend(data[ts + tsh[6]:ts + tsh[0]])
    for i in range(6, 12):
        roots[i] = tsh[i] + shift
    cluster = record_cluster(data, target_map)
    roots[0] = len(section); section.extend(b''.join(cluster['entities']) + cluster['entity_terminator'])
    roots[1] = len(section); section.extend(cluster['effects'])
    roots[2] = len(section); section.extend(b''.join(cluster['events']) + bytes(4))
    section.extend(bytes((-len(section)) % 4)); struct.pack_into('<12I', section, 0, *roots)
    struct.pack_into('<I', section, tsh[3] + target_slot * 4, start)
    result = replace_section(bytes(data), target_map, 3, section)
    packed = pack_ez(bytes(traw), bytes(data[tb + th[4]:tb + th[4] + 6])); packed += bytes((-len(packed)) % 4)
    result = replace_section(result, target_map, 4, packed); validate_layout(result)
    return bytearray(result)


BOX = (-8, -8, -1, 16, 16, 1)   # one tile, a 1-unit slab whose top is level with the floor
# (the engine treats sizes as inclusive: size-1; a 0 size wraps to a huge box)


def flatten(data, target_map, slot):
    """Cut the copied switch to its lit top face, drawn centred on the tile at
    floor level, with a one-tile, zero-height hit box."""
    from local_sprite_import import layout, sprite_assets
    from entity_animation import parse_map_sprite_animations
    _, _, ts, _, _ = layout(data, target_map)
    a = sprite_assets(data, target_map, slot)
    data = bytearray(data)
    for q in a['quads']:
        page, pal, sx, sy, w, h = struct.unpack_from('<6B', data, q)
        corners = list(struct.unpack_from('<8b', data, q + 6))
        if not w or not h:
            continue
        h = min(h, FACE_ROWS)
        top = -(h // 2)
        for i in (1, 3):
            corners[i] = top
        for i in (5, 7):
            corners[i] = top + h
        struct.pack_into('<6B8b', data, q, page, pal, sx, sy, w, h, *corners)
    struct.pack_into('<3b3B', data, a['record'] + 24, *BOX)
    seen = set()
    for anim in parse_map_sprite_animations(bytes(data), target_map, slot):
        for stream in anim.streams:
            if stream is None:
                continue
            for frame in stream.frames:
                if frame.collision_raw == -1 or frame.collision_raw in seen:
                    continue
                seen.add(frame.collision_raw)
                struct.pack_into('<3b3B', data, ts + a['roots'][2] + frame.collision_raw, *BOX)
    return data


def hide_plate(data, target_map, slot):
    """Pattern plate (class 364), Flush With Floor: the actor keeps running the plate's program but is
    not drawn (every picture piece shrunk to a point) and not solid (header bit 0x80 cleared), so Alundra
    walks over the squares its picture is drawn into (heal_tile.install_plate_pictures). A solid plate on
    flat floor always blocks him: the game rests its box on the floor (BizHawk 2026-10-25)."""
    from local_sprite_import import sprite_assets
    a = sprite_assets(data, target_map, slot)
    data = bytearray(data)
    flags = struct.unpack_from('<H', data, a['record'] + 0x10)[0]
    struct.pack_into('<H', data, a['record'] + 0x10, flags & ~0x80)
    for q in a['quads']:
        struct.pack_into('<8b', data, q + 6, *([0] * 8))
    return data


def install_flush_switch(data, target_map, keep=()):
    """(new data, local slot) with the flush switch sprite on target_map."""
    slot = _free_slot(data, target_map, keep)
    data = copy_sprite(data, target_map, DONOR_MAP, SWITCH_SLOT, slot)
    return flatten(data, target_map, slot), slot


def install_hidden_switch(data, target_map, keep=()):
    """(new data, local slot) for Step On Switch (Floor) (user 2026-10-25): the step-on switch
    (class 301) copied into a free slot and flattened like the flush switch (box top level with
    the floor), then not drawn (every picture piece shrunk to a point, as hide_plate). It stays
    solid, so Alundra and objects resting on it press it like every step-on switch; its picture
    is the floor tile drawn under it (heal_tile.install_plates). Not verified in game."""
    from local_sprite_import import sprite_assets
    slot = _free_slot(data, target_map, keep)
    data = flatten(copy_sprite(data, target_map, DONOR_MAP, SWITCH_SLOT, slot), target_map, slot)
    a = sprite_assets(data, target_map, slot)
    data = bytearray(data)
    for q in a['quads']:
        struct.pack_into('<8b', data, q + 6, *([0] * 8))
    return bytes(data), slot


def install_flush_plate(data, target_map, keep=()):
    """(new data, local slot) with a Flush With Floor copy of the map's pattern plate sprite (slot 364-256)."""
    slot = _free_slot(data, target_map, keep)
    data = copy_sprite(data, target_map, target_map, 364 - 256, slot)
    return hide_plate(data, target_map, slot), slot


def preview(image, offset):
    """Editor picture of the flush switch from the normal switch's frame."""
    left, top = offset
    face = image.crop((0, 0, image.width, min(FACE_ROWS, image.height)))
    return face, (left, -(face.height // 2))


