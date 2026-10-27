"""Lamp Switch (catalogue 398) as a recovered hit switch with Activate contents.

Source: map 24 entity 0, the game's own lamp (C: wait for the hit flag, animation
2 -> 1 lit; D: on any hit, set the flag). Its hit flag is replaced by a private
project switch. Any weapon lights it (its balance record responds to attack
types 1-7: sword, flail, arrows, bombs, fire and ice wand); with Sword Only
Activation ticked, only a sword hit does (command 87: this entity touched by
attack element 0 = attack type 1, the swords). Once lit it stays lit and runs
the event's Activate contents once.
"""
import hashlib
from event_logic_compile import _Assembler, compile_logic
from project_state_runtime import compile_project_command, compile_project_condition

SOURCE_MAP, SOURCE_ENTITY = 24, 0
SOURCE_HASHES = {'record': '062b471ba995c4baefe0844229d5753383a04bcea962076f800756e0db7948d5',
                 'C 1': 'c15e492d5307a864903f539c783193736ac7ccb52256b09c2ae288c968b58e25',
                 'D 1': 'e36a84c731789decfc87e21da07e5130d5f9b94b3b30da553453cca38d1064cc'}
SWORD_ELEMENT = 0   # attack element = attack type - 1 (Bombable Rock 243 checks element 3 = bombs, type 4)


def verify_source(datas):
    from native_class_placement import record_cluster
    from editor_session import EditSession
    from event_editor import instructions
    record = record_cluster(datas, SOURCE_MAP)['entities'][SOURCE_ENTITY]
    hashes = {'record': hashlib.sha256(record).hexdigest()}
    session = EditSession.readonly(datas)
    for key in ('C 1', 'D 1'):
        code = b''.join(bytes(datas[p:p + n]) for p, _, n in instructions(session, SOURCE_MAP, key))
        hashes[key] = hashlib.sha256(code).hexdigest()
    if hashes != SOURCE_HASHES:
        raise ValueError('Lamp switch398 source controller differs')
    return hashes


def compile_lamp_switch(registry, latch_id, request_id, commands=None, *, leaf_emitter=None, sword_only=False, can_deactivate=False, release_commands=None):
    if latch_id == request_id:
        raise ValueError('Lamp latch and hit request need separate switches')
    for identifier in (latch_id, request_id):
        registry.get('switches', identifier)

    def state(identifier, value, condition=False):
        row = {'type': 'switch' if condition else 'set_switch', 'switch_scope': 'project', 'switch_id': identifier, 'value': value}
        return (compile_project_condition if condition else compile_project_command)(row, registry)

    def emit(row):
        if row.get('switch_scope') == 'project' or row.get('variable_scope') == 'project':
            return compile_project_command(row, registry)
        if leaf_emitter: return leaf_emitter(row)
        raise ValueError('Unverified lamp continuation leaf')

    c = _Assembler()
    c.data.extend(state(latch_id, True, True)); c.branch(3, 'lit')
    c.data.extend(bytes((0x1A, 0, 0x2A)))                          # unlit, can be hit
    c.label('poll'); c.data.append(0); c.data.extend(state(request_id, True, True)); c.branch(4, 'poll')
    c.data.extend(state(request_id, False))
    c.data.extend(bytes((0x2B, 0x1A, 2, 0x1C, 1, 0x1A, 1)))   # the game's lighting (maps 102, 429, 22): no sound of its own, animation 2, then 1 (lit)
    c.data.extend(state(latch_id, True))
    continuation = compile_logic(commands or [], leaf_emitter=emit,
                                 project_condition_emitter=lambda row: compile_project_condition(row, registry))
    c.data.extend(continuation)
    if not can_deactivate:
        c.data.append(0); c.data.append(0xFF)
        c.label('lit'); c.data.extend(bytes((0x1A, 1, 0xFF)))
    else:
        # Can Deactivate: hitting the lit lamp puts it out (Deactivate actions), then it can be lit again
        release = compile_logic(release_commands or [], leaf_emitter=emit,
                                project_condition_emitter=lambda row: compile_project_condition(row, registry))
        c.label('lit'); c.data.extend(bytes((0x1A, 1, 0x2A)))
        c.label('lit_poll'); c.data.append(0); c.data.extend(state(request_id, True, True)); c.branch(4, 'lit_poll')
        c.data.extend(state(request_id, False)); c.data.extend(state(latch_id, False))
        c.data.extend(bytes((0xBD, 3, 0, 0x2B, 0x1A, 3, 0x1C, 1, 0x1A, 0)))   # going out as in map 102: sound BD03, animation 3, then unlit
        c.data.extend(release); c.branch(2, 'poll')
        c.data.append(0xFF)
    d = _Assembler()
    if sword_only:
        d.data.extend(bytes((0x87, 0x80, SWORD_ELEMENT))); d.branch(4, 'end')
    d.data.extend(state(request_id, True)); d.label('end'); d.data.append(0xFF)
    return {'C': c.finish(), 'D': d.finish()}, {
        'class_id': 398, 'donor_map': SOURCE_MAP, 'donor_entity': SOURCE_ENTITY, 'latch_id': latch_id, 'request_id': request_id,
        'activation': 'sword only (attack element 0)' if sword_only else 'any weapon the lamp responds to (attack types 1-7)',
        'source_hashes': SOURCE_HASHES, 'continuation_length': len(continuation),
        'gameplay_verified': False, 'memory_card_persistent': False}
