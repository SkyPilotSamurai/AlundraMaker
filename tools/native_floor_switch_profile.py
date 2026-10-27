"""Bounded floor-switch301 recovery, excluding the donor room's puzzle chain.

This profile is original reconstructed bytecode, not a transplanted room script.
Native3E checks whether the player is standing on this actor; animation4 and
1C01 come from map1 C17. The latch is private session state, not donor01EB.
Gameplay remains unverified until a real exported standing/animation test.
"""
import hashlib
from event_logic_compile import _Assembler, compile_logic
from project_state_runtime import compile_project_command, compile_project_condition

SOURCE_MAP = 1
SOURCE_ENTITY = 16
CLASS_ID = 301
SOURCE_HASHES = {
    'record': 'e03f3a75d2fddd0230593d1eebee47d690b0570bbd910e0db14d680fc4c0e6b5',
    'A 17': '63a063dda610129e3c0bc6b2cc9f16b8b5f744054a0f13494e4d7544d534ec30',
    'C 17': 'd6baccd711c5017ff86c23d10148a5fc93442676c1a074d518c97040bfc924bd',
}


def verify_source(datas):
    """Require the exact recovered donor record and both dependent programs."""
    from editor_session import EditSession
    from event_editor import instructions
    from map_inspector import inspect_map
    session = EditSession.readonly(datas)
    row = inspect_map(datas, SOURCE_MAP)['entities'][SOURCE_ENTITY]
    offset = int(row['offset'], 16)
    actual = {'record': hashlib.sha256(datas[offset:offset+20]).hexdigest()}
    for key in ('A 17', 'C 17'):
        code = b''.join(bytes(datas[pos:pos+size]) for pos, _, size in
                        instructions(session, SOURCE_MAP, key))
        actual[key] = hashlib.sha256(code).hexdigest()
    if actual != SOURCE_HASHES:
        raise ValueError('Floor-switch donor differs from recovered US1.1 controller')
    return actual


ANYTHING_TEST = 0x3F   # native 'anything standing on this' (8003F1E0): 169 stock 301 switches
# Editor F0 (native_press_filter): like 3F, but only Alundra, Spring Bean, barrels and pushable / ice
# pillars count - not enemies, vases, wooden crates, spike balls or platforms (user 2026-10-26).
PRESS_TEST = 0xF0
PLAYER_TEST = 0x3E     # native 'player standing on this' (8003F1B4): 143 stock 301 switches
BEAN_SETTLE_FRAMES = 8 # a thrown Spring Bean rides a switch 3 frames, then despawns (2026-10-22 trace)


def _wait_press(asm, target, ignore_spring_bean):
    """Branch to target unless something stands on this switch.

    Ignore Spring Bean: the press must still hold after BEAN_SETTLE_FRAMES,
    which a thrown bean (gone 3 frames after landing) never does; objects
    that stay on the switch still press it, and the player presses at once."""
    if not ignore_spring_bean:
        asm.data.append(PRESS_TEST); asm.branch(4, target)
        return
    done = f'{target}_pressed_{len(asm.data)}'
    asm.data.append(PLAYER_TEST); asm.branch(3, done)          # the player presses at once
    asm.data.append(PRESS_TEST); asm.branch(4, target)
    asm.data.extend(bytes((0x37, BEAN_SETTLE_FRAMES, PRESS_TEST))); asm.branch(4, target)
    asm.label(done)


def compile_floor_switch(registry, latch_id, commands=None, *, leaf_emitter=None, while_pressured=False, release_commands=None, can_deactivate=False, ignore_spring_bean=False):
    """Return A/C programs and evidence; one activation per private latch.

    The caller installs these on the copied actor and injects private state.
    No D/F interaction hook is invented: this is a standing-triggered switch.
    Commands are compiled after native press animation wait. Caller may reset
    the latch explicitly, but repeat/release semantics are not presumed.
    """
    registry.get('switches', latch_id)
    condition = {'type': 'switch', 'switch_scope': 'project',
                 'switch_id': latch_id, 'value': True}
    assignment = dict(condition, type='set_switch')
    test = compile_project_condition(condition, registry)
    set_latch = compile_project_command(assignment, registry)
    # A17's donor85 call controls room-owned content; only its already-pressed
    # animation selection is retained in this isolated actor load program.
    load = _Assembler()
    load.data.extend(test); load.branch(4, 'end')
    load.data.extend(bytes((0x1A, 1)))
    load.label('end'); load.data.append(0xFF)
    controller = _Assembler()
    clear_latch = compile_project_command(dict(assignment, value=False), registry)
    remote = True   # Activate / Deactivate Switch commands (user 2026-10-11)
    if remote:
        controller.data.extend(test); controller.branch(3, 'held')   # loaded already pressed
        controller.label('poll'); controller.data.append(0)
        controller.data.extend(test); controller.branch(3, 'pressed')  # a command activated it
        _wait_press(controller, 'poll', ignore_spring_bean)
        controller.data.extend(set_latch)
        controller.label('pressed')
    else:
        controller.data.extend(test); controller.branch(3, 'end')
        controller.label('poll'); controller.data.append(0)
        _wait_press(controller, 'poll', ignore_spring_bean)
        controller.data.extend(set_latch)
    controller.data.extend(bytes((0xBD, 0x3C, 0, 0x1A, 4, 0x1C, 1)))   # press click BD3C (maps 306 / 307), press animation
    def emit(row):
        if row.get('switch_scope') == 'project' or row.get('variable_scope') == 'project':
            return compile_project_command(row, registry)
        if leaf_emitter is not None:
            return leaf_emitter(row)
        raise ValueError('Floor continuation command needs a verified native leaf compiler')
    continuation = compile_logic(commands or [],
        leaf_emitter=emit,
        project_condition_emitter=lambda row: compile_project_condition(row, registry))
    if while_pressured:
        # While Pressured (user 2026-10-11): ON only while Alundra stands on it.
        # Press -> latch ON, press animation, Activate actions; step off -> latch
        # OFF, raised animation, Deactivate actions; then wait for the next press.
        release = compile_logic(release_commands or [], leaf_emitter=emit,
            project_condition_emitter=lambda row: compile_project_condition(row, registry))
        clear_latch = compile_project_command(dict(assignment, value=False), registry)
        load = _Assembler(); load.data.extend(clear_latch); load.data.append(0xFF)
        controller = _Assembler()
        controller.label('poll'); controller.data.append(0)
        _wait_press(controller, 'poll', ignore_spring_bean)  # nothing on it: keep waiting
        controller.data.extend(set_latch)
        controller.data.extend(bytes((0xBD, 0x3C, 0, 0x1A, 4, 0x1C, 1)))  # press click BD3C, native press animation
        controller.data.extend(continuation)
        controller.label('hold'); controller.data.extend(bytes((0, PRESS_TEST)))
        controller.branch(3, 'hold')                       # still standing: stay pressed
        controller.data.extend(clear_latch)
        controller.data.extend(bytes((0x1A, 0)))           # raised again
        controller.data.extend(release)
        controller.branch(2, 'poll')
        controller.data.append(0xFF)
        return {'A': load.finish(), 'C': controller.finish()}, {
            'class_id': CLASS_ID, 'trigger': 'while anything stands on actor', 'latch_id': latch_id,
            'while_pressured': True, 'ignore_spring_bean': ignore_spring_bean, 'release_length': len(release),
            'continuation_length': len(continuation), 'gameplay_verified': False,
            'source_hashes': dict(SOURCE_HASHES)}
    controller.data.extend(continuation)
    if remote:
        # stays pressed until a command deactivates it; then up again, Deactivate actions, re-armed
        release = compile_logic(release_commands or [], leaf_emitter=emit,
            project_condition_emitter=lambda row: compile_project_condition(row, registry))
        controller.label('held'); controller.data.append(0)
        if can_deactivate:
            # Can Deactivate: step off, then on again: it comes up (Deactivate actions)
            controller.data.extend(test); controller.branch(4, 'released')
            controller.data.append(PRESS_TEST); controller.branch(3, 'held')        # still standing on it
            controller.label('off_wait'); controller.data.append(0)
            controller.data.extend(test); controller.branch(4, 'released')
            _wait_press(controller, 'off_wait', ignore_spring_bean)            # wait for the next step
            controller.data.extend(clear_latch); controller.data.extend(bytes((0xBD, 0x3C, 0)))
        else:
            controller.data.extend(test); controller.branch(3, 'held')
        controller.label('released')
        controller.data.extend(bytes((0x1A, 0)))
        controller.data.extend(release)
        controller.branch(2, 'poll')
    controller.label('end'); controller.data.append(0xFF)
    return {'A': load.finish(), 'C': controller.finish()}, {
        'class_id': CLASS_ID, 'donor_map': SOURCE_MAP, 'donor_entity': SOURCE_ENTITY,
        'native_animation': 4, 'latched_load_animation': 1,
        'trigger': 'anything standing on actor', 'latch_id': latch_id, 'ignore_spring_bean': ignore_spring_bean,
        'donor_flag_removed': '01EB', 'excluded_room_opcodes': ['85', 'BD'],
        'gameplay_verified': False, 'memory_card_persistent': False,
        'continuation_length': len(continuation), 'source_hashes': dict(SOURCE_HASHES),
    }


# --- Step On Switch (Floor): a tile-tested controller (2026-10-25) -------------
# Nothing solid stands on the square, so Alundra walks onto it from squares of the
# same height. A whole-map B program tests the square itself:
#   3B x x y y z z  Alundra in the tile box (0x8003EF44; the healing tiles' test)
#   3C x x y y z z  any solid entity, not held, in the box (0x8003EFEC): blocks,
#                   statues, pots and the like resting on it
# (z = the square's height, as heal_tile.tile_program). Not verified in game.

def _tile_box(op, x, y, z):
    return bytes((op, x, x, y, y, z, z))


def _wait_tile_press(asm, target, x, y, z, ignore_spring_bean):
    """Branch to target unless Alundra or something solid is on the square.
    Ignore Spring Bean: an object must still be there after BEAN_SETTLE_FRAMES
    (a thrown bean is gone 3 frames after landing); Alundra presses at once."""
    done = f'{target}_on_{len(asm.data)}'
    asm.data.extend(_tile_box(0x3B, x, y, z)); asm.branch(3, done)
    # F1 (native_press_filter): 3C, but only Spring Bean, barrels and pushable / ice pillars (user 2026-10-26)
    asm.data.extend(_tile_box(0xF1, x, y, z)); asm.branch(4, target)
    if ignore_spring_bean:
        asm.data.extend(bytes((0x37, BEAN_SETTLE_FRAMES)))
        asm.data.extend(_tile_box(0xF1, x, y, z)); asm.branch(4, target)
    asm.label(done)


def compile_tile_floor_switch(registry, slots, fs, press_code, lit_code, release_code, room_guard=None):
    """B program of a Step On Switch (Floor). fs: the compiler's _floor_switch entry
    (tile, z, state_id and the options). press_code: click, lit picture and Activate
    actions (already compiled, page conditions included); lit_code: only the lit
    picture (entering the room already on); release_code: unlit picture and
    Deactivate actions. Ends with FF."""
    import struct
    x, y = fs['tile']; z = fs['z']
    cond = {'type': 'switch', 'switch_scope': 'project', 'switch_id': fs['state_id'], 'value': True}
    test = compile_project_condition(cond, registry, slots)
    on = compile_project_command(dict(cond, type='set_switch'), registry, slots)
    off = compile_project_command(dict(cond, type='set_switch', value=False), registry, slots)
    asm = _Assembler()
    if room_guard is not None:
        # back to its start (Active By Default) once per visit, unless Keep State Upon Leaving Room
        body = (on if fs.get('active_by_default') else off) + struct.pack('<BH', 0x05, room_guard)
        asm.data.extend(struct.pack('<BHh', 0x30, room_guard, 5 + len(body)) + body)
    if fs.get('while_pressed'):
        asm.data.extend(off)
    else:
        asm.data.extend(test); asm.branch(4, 'poll')
        asm.data.extend(lit_code); asm.branch(2, 'held')      # entering the room already on
    asm.label('poll'); asm.data.append(0)
    if not fs.get('while_pressed'):
        asm.data.extend(test); asm.branch(3, 'remote')          # Activate Switch from another event
    _wait_tile_press(asm, 'poll', x, y, z, fs.get('ignore_spring_bean'))
    asm.data.extend(on)
    asm.label('remote')
    asm.data.extend(press_code)
    if fs.get('while_pressed'):
        asm.label('hold'); asm.data.append(0)
        _wait_tile_press(asm, 'up', x, y, z, False)
        asm.branch(2, 'hold')                                    # still pressed
        asm.label('up'); asm.data.extend(off)
    else:
        asm.label('held'); asm.data.append(0)
        asm.data.extend(test); asm.branch(4, 'released')        # Deactivate Switch from another event
        if fs.get('can_deactivate'):
            # step off, then on again: it comes up
            _wait_tile_press(asm, 'off_wait', x, y, z, False)
            asm.branch(2, 'held')                                # still on it
            asm.label('off_wait'); asm.data.append(0)
            asm.data.extend(test); asm.branch(4, 'released')
            _wait_tile_press(asm, 'off_wait', x, y, z, fs.get('ignore_spring_bean'))
            asm.data.extend(off); asm.data.extend(bytes((0xBD, 0x3C, 0)))
        else:
            asm.branch(2, 'held')
        asm.label('released')
    asm.data.extend(release_code)
    asm.branch(2, 'poll')
    return asm.finish() + bytes((0xFF,))
