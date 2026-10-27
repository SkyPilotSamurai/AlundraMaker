"""Stool (Pushable): the Sanctuary library stool (catalogue 383, map 137 entities 1-11) moved one
tile in any of the four directions (user 2026-10-23). Event options (native_placement):
push_directions (Moves: Up / Down / Left / Right, default all), move_once, target_tile
({'x','y'}: ending a move there runs the Activate actions, leaving it the Deactivate actions).

Stock evidence (static, DATAS map 137 entity 2, hooks A 82 / C 83 / F 82; object library):
  F (talk; also fired when Alundra walks into it): 05 800B FF - set a room flag.
  C: waits for the flag; 57 (jump by Alundra's facing; operand order down, up, left, right:
     research/us_decomp/vm_ops/audit_30_5F.md, handler 0x8003F8FC); down/up -> clear the flag;
     right -> 09 18 (face right), BD 0137 (sound 311 "Move chair"), 1A 04 (animation 4, speed
     160, all four directions valid), 1F 0018 (wait until moved 24 pixels or blocked), 1A 03;
     left the same with 09 08. It also keeps the stool inside tiles 7..11 of row 35 with absolute
     tile-box tests (07) and has a puzzle branch (room flags 8001 / 8015); those are
     room-specific and not used here.
This program uses the same ops: F sets the stool's own room flag (0x8780 + n, no stock map
script uses 8780-879F); C waits for it and moves one tile in Alundra's facing: 24 pixels on X,
16 on Y (a tile is 24 x 16 pixels). Collision stops it as in stock (1F ends when blocked).
A direction that is not ticked only clears the flag. 6E (Test: blocked, audit_60_7F.md
0x800404B0) after the move tells a real move from a blocked one (Move Once, target tile).
Target tile: 07 (this character inside a one-tile box, any height) after every move and once
on entering the map; a project switch remembers on/off so Activate / Deactivate run on changes
only, and a reload (the stool is back at its placed tile) runs Deactivate when it was on."""
import struct

DIRECTIONS = ('down', 'up', 'left', 'right')          # op 57 operand order
FACING = {'down': 0x00, 'up': 0x10, 'left': 0x08, 'right': 0x18}
DISTANCE = {'down': 16, 'up': 16, 'left': 24, 'right': 24}
PUSH_SOUND = 311
FLAG_BASE = 0x8780
MAX_PER_MAP = 32
VARIANT = 'push_stool'
SWITCH = 301                # Switch (Step On): its box is 24 x 16 x 16 px (BizHawk, map 494 2026-10-23)
HOP_FORCE = 0x500           # 5 px per frame up; gravity 0.5 px/frame^2 (remake/physics.py): ~25 px peak
HOP_RISE = 5                # frames up before it moves (about 18 px, over the 16 px switch)
DONOR = (137, 2)


def allowed(placement):
    """The ticked directions (native_placement['push_directions']; absent: all four)."""
    chosen = (placement or {}).get('push_directions')
    if chosen is None: return list(DIRECTIONS)
    return [d for d in DIRECTIONS if d in chosen]


def target_of(placement):
    tile = (placement or {}).get('target_tile')
    if not isinstance(tile, dict): return None
    x, y = tile.get('x'), tile.get('y')
    if type(x) is not int or type(y) is not int or not 0 <= x <= 127 or not 0 <= y <= 127:
        raise ValueError('Stool target tile must be inside the map')
    return x, y


def talk_program(flag):
    return bytes((0x05,)) + struct.pack('<H', flag) + bytes((0xFF,))


def tick_program(flag, directions=DIRECTIONS, once=False, target=None, on=b'', off=b'', state=None, switches=()):
    """C program. state = (test: Result true when it is on, set on, set off) for a target tile.
    switches: map templates of Switch (Step On) actors (16 px tall): a push blocked by one hops
    (1B vertical force) and lands on it; with 0x4000 cleared it rides it, which the switch's 3F sees."""
    from event_logic_compile import _Assembler
    a = _Assembler(); f = struct.pack('<H', flag)

    def check(after):
        # on the target tile -> on (if it was off: remember, Activate); else off (if it was on: Deactivate)
        x, y = target
        test, set_on, set_off = state
        a.data.extend(bytes((0x07, 0x80, x, x, y, y, 0x00, 0xFF))); a.branch(4, f'off{after}')
        a.data.extend(test); a.branch(3, after)
        a.data.extend(set_on + bytes(on)); a.branch(2, after)
        a.label(f'off{after}')
        a.data.extend(test); a.branch(4, after)
        a.data.extend(set_off + bytes(off)); a.branch(2, after)

    a.data.extend(bytes((0x37, 0x01)))                   # wait 1 frame (stock C starts so)
    switches = [t for t in switches if 0 <= t < 0x80]
    if switches:
        # the stool's flags (+0x6C, BizHawk: 0x36181) have gravity 0x100 and 0x4000, which keeps it
        # from riding anything (remake/physics.py check_riding, 0x800364C8): clear 0x4000 (63)
        a.data.extend(bytes((0x63, 0x80)) + struct.pack('<H', 0x4000))
    if target:
        check('loop')
    a.label('loop')
    if switches:
        # On a switch, Alundra walking into it bumps the switch (it is in front of the stool):
        # 43 85 acts on what the stool stands on, AA 81 tests that Alundra bumped into it,
        # 43 86 acts on the stool again (audit_30_5F.md 0x8003F2C8, audit_A0_C4.md 0x80041CFC)
        a.data.append(0x00); a.branch(0x30, 'go', flag)
        a.data.extend(bytes((0x43, 0x85))); a.branch(4, 'loop')
        a.data.extend(bytes((0xAA, 0x81))); a.branch(3, 'bumped')
        a.data.extend(bytes((0x43, 0x86))); a.branch(2, 'loop')
        a.label('bumped'); a.data.extend(bytes((0x43, 0x86)))
    else:
        a.data.extend(bytes((0x00, 0x36)) + f)           # yield; wait until the flag is set
    a.label('go')
    switch_at = len(a.data)
    a.data.append(0x57)
    for d in DIRECTIONS:
        a.fixups.append((len(a.data), switch_at, d if d in directions else 'done')); a.data.extend(bytes(2))
    tested = once or target or switches
    for d in DIRECTIONS:
        if d not in directions: continue
        a.label(d)
        a.data.extend(bytes((0x09, FACING[d], 0xBD)) + struct.pack('<H', PUSH_SOUND) + bytes((0x1A, 0x04, 0x1F))
                      + struct.pack('<H', DISTANCE[d]))
        if tested:
            a.data.append(0x6E)                          # Result: blocked
        a.data.extend(bytes((0x1A, 0x03)))
        if switches:
            a.branch(4, 'moved')                         # it moved
            for t in switches:                           # blocked by a step-on switch?
                a.data.extend(bytes((0xA9, t))); a.branch(3, f'hop{d}')
            a.data.append(0x6E); a.branch(2, 'moved')
            a.label(f'hop{d}')
            a.data.extend(bytes((0x1B,)) + struct.pack('<H', HOP_FORCE) + bytes((0x37, HOP_RISE, 0x1A, 0x04, 0x1F))
                          + struct.pack('<H', DISTANCE[d]) + bytes((0x6E, 0x1A, 0x03)))
        a.branch(2, 'moved' if tested else 'done')
    if tested:
        a.label('moved')
        a.branch(3, 'done')                              # blocked: it did not move
        end = 'rest' if once else 'done'
        if target:
            check(end)
        else:
            a.branch(2, end)
    a.label('done')
    a.data.extend(bytes((0x06,)) + f)
    a.branch(2, 'loop')
    if once:
        a.label('rest')                                  # moved once: clear the flag, rest
        a.data.extend(bytes((0x06,)) + f)
        a.label('idle'); a.data.append(0x00); a.branch(2, 'idle')
    a.data.append(0xFF)
    return a.finish()


def is_stool(definition):
    return (definition or {}).get('source', {}).get('variant') == VARIANT


def next_flag(map_id, counts):
    n = counts.get(map_id, 0)
    if n >= MAX_PER_MAP:
        raise ValueError(f'Map {map_id}: at most {MAX_PER_MAP} pushable stools')
    counts[map_id] = n + 1
    return FLAG_BASE + n


def switch_templates(datas, map_id, group, definitions, actor_indices):
    """Map templates of the Switch (Step On) actors on this map: stock records and placed events."""
    from native_class_placement import record_cluster
    out = []
    for i, raw in enumerate(record_cluster(datas, map_id)['entities']):
        if raw[6] + (256 if raw[5] & 128 else 0) == SWITCH: out.append(i)
    for g in group:
        page = (g.get('pages') or [{}])[0]
        d = definitions.get(page.get('class_id', g.get('class_id'))) or {}
        if d.get('source', {}).get('catalogue_index') == SWITCH and g['id'] in actor_indices:
            out.append(actor_indices[g['id']])
    return sorted(set(out))


def install(datas, map_id, hooks, graph, counts, on=b'', off=b'', state=None, append_f=True, switches=()):
    """Append this stool's C (and F) programs; returns (datas, hooks, report).
    counts: {map_id: stools so far} for this export (one room flag each). append_f=False:
    the caller appends F (report['F_code'])."""
    from native_script_allocation import append_native_process
    flag = next_flag(map_id, counts)
    placement = graph.get('native_placement') or {}
    directions, once, target = allowed(placement), bool(placement.get('move_once')), target_of(placement)
    if state is None:
        target = None                                    # no Activate / Deactivate actions: nothing to run
    datas, c = append_native_process(datas, map_id, 'C', tick_program(flag, directions, once, target, on, off, state, switches))
    hooks = bytearray(hooks); hooks[2] = c['hook_value']
    report = {'room_flag': hex(flag), 'directions': directions, 'move_once': once,
              'target_tile': list(target) if target else None, 'C': c}
    if not append_f:
        return datas, bytes(hooks), dict(report, F_code=talk_program(flag))
    datas, f = append_native_process(datas, map_id, 'F', talk_program(flag))
    hooks[5] = f['hook_value']
    return datas, bytes(hooks), dict(report, F=f)
