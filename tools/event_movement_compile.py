"""Sprite-validated SELF walking route bytecode, with native physics limits.

Requires a moving animation with positive native speed and a zero-speed idle.
Routes use native distance waits or distance/ForceAdjusted waits. This is not
a pathfinder; native AI and endpoint overshoot still require emulator tests.
"""
import struct

DIRECTIONS = {'down': 0, 'left': 8, 'up': 16, 'right': 24}


def compile_movement_command(data, catalogue_id, command, *, map_id=None):
    """Compile an authored fixed route for its own native actor only."""
    if command.get('mode') not in ('walk_tiles', 'route'):
        raise ValueError('This movement mode has no verified native compiler yet; choose a fixed tile route')
    if catalogue_id is None:
        raise ValueError('Walking needs a database actor; a graphic-free touch region cannot walk')
    if command.get('target') not in ('self', 'this_event'):
        raise ValueError('Walking currently targets This event; another actor needs verified context switching')
    speed=command.get('movement_speed',100)
    if type(speed) is not int or not 1<=speed<=400:raise ValueError('Movement speed must be1..400 percent')
    if speed!=100:raise ValueError('Custom route speed needs a private per-actor animation/controller; shared sprite speed must not be patched')
    blocked=command.get('blocked_behavior','wait')
    if blocked not in ('wait','skip'):raise ValueError('Blocked movement must wait or skip')
    route=command.get('route')
    if command['mode']=='walk_tiles':
        count=command.get('tiles');direction=command.get('direction')
        if type(count) is not int or not 1 <= count <= 255 or direction not in DIRECTIONS:
            raise ValueError('Walk needs1..255 tiles and a cardinal direction')
        route=[direction]*count
    return compile_verified_self_route(data,catalogue_id,route,map_id=map_id,
        moving_animation=command.get('moving_animation'),idle_animation=command.get('idle_animation'),skip_impossible=blocked=='skip')


def animation_profile(data, catalogue_id, map_id=None):
    if not isinstance(data, (bytes, bytearray, memoryview)) or len(data) < 8:
        raise ValueError('Sprite data is missing or truncated')
    if type(catalogue_id) is not int or not 0 <= catalogue_id <= 511:
        raise ValueError('Native sprite catalogue ID must be 0..511')
    if catalogue_id < 256:
        start, end = struct.unpack_from('<2I', data)
    else:
        from map_slots import map_exists, map_base
        if not map_exists(data, map_id):
            raise ValueError('Map-local movement needs an existing map')
        base = map_base(data, map_id)
        if not 0 <= base <= len(data) - 28:
            raise ValueError('Map header is outside data')
        sections = struct.unpack_from('<7I', data, base)
        start, end = base + sections[3], base + sections[4]
    if not 0 <= start < start + 48 <= end <= len(data):
        raise ValueError('Invalid sprite bank')
    h = struct.unpack_from('<12I', data, start)
    table, table_end = h[3:5]
    if not 48 <= table <= table_end <= end - start or (table_end - table) % 4:
        raise ValueError('Invalid native sprite table')
    index = catalogue_id & 255
    if index >= (table_end - table) // 4:
        raise ValueError('Sprite absent from bank')
    pointer = struct.unpack_from('<i', data, start + table + index * 4)[0]
    if not 48 <= pointer <= end - start - 32:
        raise ValueError('Sprite header absent or outside bank')
    sets, animations, collision, frames = struct.unpack_from('<4I', data, start + pointer)
    if not pointer + 32 <= sets < animations <= collision <= frames < end - start:
        raise ValueError('Animation regions invalid')
    count, padding = divmod(animations - sets, 14)
    if not 1 <= count <= 256 or padding > 3:
        raise ValueError('Native animation set table malformed')
    rows = []
    for number, offset in enumerate(range(sets, sets+count*14, 14)):
        directions, speed, acceleration = struct.unpack_from('<4H', data, start + offset), struct.unpack_from('<H', data, start + offset + 8)[0], data[start + offset + 13] & 15
        valid = [value != 65535 and animations + value + 5 <= collision for value in directions]
        rows.append({'animation_id': number, 'speed': speed, 'acceleration': acceleration,
                     'directions_valid': valid, 'native_offset': start + offset})
    return rows


def compile_verified_self_route(data, catalogue_id, route, *, moving_animation,
                                idle_animation, map_id=None, skip_impossible=False):
    """Compile09direction/1Aanimation/1Edistance for the current logic actor.

    Caller selects existing sprite animations rather than assuming animation1
    walks for every enemy/NPC. Other actor targets need verified context switching
    and are deliberately outside this helper. Stops at idle and yields once.
    """
    if not isinstance(route, list) or not 1 <= len(route) <= 255 or any(not isinstance(step, str) or step not in DIRECTIONS for step in route):
        raise ValueError('Route must contain1..255 cardinal tile steps')
    rows = animation_profile(data, catalogue_id, map_id)
    for value in (moving_animation, idle_animation):
        if type(value) is not int or not 0 <= value < len(rows):
            raise ValueError('Choose an existing native sprite animation')
    moving, idle = rows[moving_animation], rows[idle_animation]
    needed={DIRECTIONS[step]//8 for step in route}
    if moving['speed'] <= 0 or not all(moving['directions_valid'][d] for d in needed):
        raise ValueError('Walking animation needs positive speed and all four directions')
    if idle['speed'] != 0 or not all(idle['directions_valid'][d] for d in needed):
        raise ValueError('Idle animation must stop native motion and have all directions')
    output = bytearray()
    for step in route:
        # Native world geometry has24pixel X tiles and16pixel Y tiles.
        distance = 24 if step in ('left', 'right') else 16
        output.extend((9, DIRECTIONS[step], 0x1A, moving_animation, 0x1F if skip_impossible else 0x1E))
        output.extend(struct.pack('<H', distance))
    output.extend((0x1A, idle_animation, 0))
    return bytes(output)


def compile_facing_command(command, *, has_actor):
    """Native SELF target direction: 27 toward player, 0A reverse, 09 angle."""
    if not has_actor:
        raise ValueError('Facing needs a character or object; an invisible region has no facing')
    if command.get('target') not in ('this_event','self'):
        raise ValueError('Facing currently targets This event')
    direction=command.get('direction')
    if direction=='player':return bytes((0x27,))
    if direction=='away_from_player':return bytes((0x27,0x0A))
    if direction in DIRECTIONS:return bytes((0x09,DIRECTIONS[direction]))
    raise ValueError('Unknown facing direction')
