"""Experimental portable324 key door; original room flag is never copied."""
import hashlib
import struct
from alundra_memory import parse_exe
from event_logic_compile import _Assembler
from project_state_runtime import compile_project_condition, compile_project_command

STOCK_EXE_SHA = '12f12eafa3e34dac6aca40b52f4f85f95811d40de7e48db77c52a35aa18833a3'
SOURCE_RECORD = bytes.fromhex('0000333b01c04457340e90000000009000000000')
SOURCE_PROGRAMS = {'A 16': bytes.fromhex('31b40207002e80ff'),
                   'F 16': bytes.fromhex('833d01598100041100bd3c00843d05b4022e80020700000d0100ff')}
SLICES = {
    0x83: (0x800409B0, 27), 0x59: (0x8003F960, 26),
    0x84: (0x80040A1C, 20), 0x2E: (0x8003E788, 33),
}


def require_synchronous_continuation(commands):
    """Native F ownership has not survived an authored wait in live testing.

    Keep the tested immediate success path until a retained C handoff is proven.
    Inspect both arms even when the current condition would skip one of them.
    """
    for command in commands:
        if command.get('type') in ('wait', 'show_dialogue'):
            raise ValueError('Key door324 Activate contents cannot wait or show dialogue until a retained native continuation is verified')
        for key in ('then', 'else', 'commands'):
            require_synchronous_continuation(command.get(key, []))


def verify_source(data):
    from editor_session import EditSession
    from native_class_placement import record_cluster
    from event_editor import instructions
    if record_cluster(data, 42)['entities'][16] != SOURCE_RECORD:
        raise ValueError('Key door324 donor differs')
    session = EditSession.readonly(data)
    for root, expected in SOURCE_PROGRAMS.items():
        actual = b''.join(bytes(data[p:p+n]) for p, _, n in instructions(session, 42, root))
        if actual != expected:
            raise ValueError('Key door324 native map program differs')
    return True


def audit(exe, data):
    if hashlib.sha256(exe).hexdigest() != STOCK_EXE_SHA:
        raise ValueError('Exact USA1.1 retail EXE required')
    from editor_session import EditSession
    from native_class_placement import record_cluster
    from event_editor import instructions
    if record_cluster(data, 42)['entities'][16] != SOURCE_RECORD:
        raise ValueError('Native door source record differs')
    session = EditSession.readonly(data)
    for root, expected in SOURCE_PROGRAMS.items():
        actual = b''.join(bytes(data[p:p+n]) for p, _, n in instructions(session, 42, root))
        if actual != expected: raise ValueError('Native key door source program differs')
    load = parse_exe(exe)['load_address']; rows = []
    for opcode, (address, count) in SLICES.items():
        table = 0x8009B814 - load + 0x800
        if struct.unpack_from('<I', exe, table + opcode * 4)[0] != address:
            raise ValueError('Native dispatcher differs')
        offset = address - load + 0x800
        rows.append(dict(opcode=f'{opcode:02X}', virtual_address=f'{address:08X}',
                         file_offset=offset,
                         words=[f'{w:08X}' for w in struct.unpack_from('<' + str(count) + 'I', exe, offset)]))
    for address, count in [(0x8004FAC4, 25), (0x8004FC80, 34), (0x8003B0C8, 15)]:
        offset = address - load + 0x800
        rows.append(dict(virtual_address=f'{address:08X}', file_offset=offset,
                         words=[f'{w:08X}' for w in struct.unpack_from('<' + str(count) + 'I', exe, offset)]))
    return dict(module='Stock ALUN_CD.EXE USA1.1', sha256=STOCK_EXE_SHA, slices=rows,
                observed_source=dict(map=42, entity=16, catalogue=324,
                                     record=SOURCE_RECORD.hex(), programs={k:v.hex() for k,v in SOURCE_PROGRAMS.items()}),
                derived_contract={
                    '83': 'LBU item/threshold; helper8004FAC4 reads signed16 quantity via pointer80119AEC +item*4 +2. Context+2C receives quantity>=threshold boolean. Returns3 bytes.',
                    '59': 'LBU actor selector/animation, actor lookup8003D374, SW animation to selected actor+88. Preserves83 comparison result. Selector81/animation0 is retained from source.',
                    '84': 'LBU item; helper8004FC80 uses LH quantity and SH quantity-1 when nonzero, returns signed16 new count or -1 when zero. Opcode84 converts helper success to boolean at context+2C; returns2 bytes. Does not grant an item.',
                    '2E': 'LBU selector, matching-actor lookup and helper8003B0C8 marks selected actor+10=4, actor+228=-1 and clears linked state. Self80 source call is retained; other selector/lifetime semantics not generalized.'},
                limitations=['Matched bounded instruction slices; no complete function-boundary claim',
                             'Item quantity address is runtime pointer-derived; no universal revision delta',
                             'Original flag02B4 is encoded in source but is excluded from portable profile'])


def compile_door(registry, opened_id, text_ref, after=b''):
    if type(text_ref) is not int or not 128 <= text_ref <= 255:
        raise ValueError('Owned map-local failure text required')
    test = compile_project_condition(dict(type='switch', switch_scope='project',
                                         switch_id=opened_id, value=True), registry)
    set_open = compile_project_command(dict(type='set_switch', switch_scope='project',
                                           switch_id=opened_id, value=True), registry)
    a = _Assembler(); a.data.extend(test); a.branch(4, 'end')
    a.data.extend(bytes.fromhex('2e80')); a.label('end'); a.data.append(255)
    f = _Assembler(); f.data.extend(test); f.branch(3, 'end')
    f.data.extend(bytes.fromhex('833d01598100')); f.branch(4, 'locked')
    f.data.extend(bytes.fromhex('bd3c00843d')); f.data.extend(set_open)
    f.data.extend(after); f.data.extend(bytes.fromhex('2e80')); f.branch(2, 'end')
    # Retail false branch targets0D, skipping the intervening00 padding.
    # Executing00 terminates this invocation before its failure dialogue.
    f.data.append(0); f.label('locked'); f.data.extend(bytes((13, text_ref, 0)))
    f.label('end'); f.data.append(255)
    return {'A': a.finish(), 'F': f.finish()}


def compile_key_door(registry, opened_id, text_ref, after=b''):
    return compile_door(registry, opened_id, text_ref, after), {
        'class_id':324,'source_map':42,'source_entity':16,
        'removed_room_flag':'02B4','opened_id':opened_id,
        'key_item_id':61,'key_name':'Key','quantity_native_width':16,
        'failure':'Native locked dialogue, no consumption or authored continuation',
        'success':'Remove one Key61, set private opened state, run continuation, mark self inactive',
        'activation':'Native approach/touch; continuation before same-update cleanup',
        'memory_card_persistent':False,'gameplay_verified':False}
