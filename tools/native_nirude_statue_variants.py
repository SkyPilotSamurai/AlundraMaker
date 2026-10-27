"""Nirude Face Statue variants that shoot (user 2026-10-24: "the one that shoot fire or lasers in
Nirude dungeon ... have those as different objects"). Separate from the plain statue's compile path
(native_nirude_face); these entries carry source.variant = 'nirude_statue' and statue_variant = key.

Stock evidence (static, DATAS USA Rev 1, decoded with event_editor.reachable_instructions,
2026-10-24; docs/2026-10-24-nirude-statue-variants.txt):
  The statue class (catalogue 346, same sprite / animations.json on every map) never shoots by
  itself: its C program is the hit cycle (wake 1A 0B, three stages of ten hits, 05 <broken flag>)
  and D sets its hit flag. The shots are spawned by the ROOM (bank B) scripts from map templates:
    fire        map 35 B 3: per statue k: 30 <83E8+k> skip, 2C <t> / 04 skip, 2D <t>, 00 00
                (templates 14-18, Fireball 319, C 7: BD 4E01, BD 5501, 1A 09, 1C 01, 1A 02, 24,
                BE 5501, 19 = straight flight until blocked); 5 statues -> about every 11 frames.
    homing      map 38 B 4: 37 5A, 37 1E, then per statue: 2C <t> / 04, 30 <83E8+k>, 2D <t>, 37 1E
                (templates 16-18, Fireball 319 C 8: 1A 09, then 1A 01 and 27 face the player every
                30 frames until blocked); 3 statues -> one slot every 90 frames.
    laser       map 36 B 4: 37 78, then per statue: 37 3C, 30 <83E8+k>, (2D <t>, 37 05) x 9-10, 00 00
                (templates 13-21 below statue 10, Laser Orb 251 C 13: 1A 00, 37 1E, 19); the
                three columns in turn, 331 frames a round.
  An emitter below keeps the room loop of ONE stock statue (its own templates and broken flag);
  the other statues' slots become one wait so the stock period stays. The donor templates are
  brought with translate_map_refs / copy_template (the Launcher template-copy fix,
  docs/2026-10-22-launcher-generator.txt), positions moved with the placement; there are no
  3B tile boxes in these loops.
  Room flags: the statue's hit flag (set by its D), broken flag (set by its C) and an active flag
  become 0x8700 + 3n / + 3n+1 / + 3n+2 per placement on a map (no stock script uses 8600-87CF: scan of all
  483 maps' roots, flag ops 05/06/30/31/32/35/36/33/34; tool ranges 8760+ faces, 8780+ stools,
  87A0+ room guards, 87C0+ signs), so two copies do not share hits. The map-35 statue's wait for
  story flag 01AB is passed (its room's intro sets it), as start_now does for bosses.
Page triggers (user 2026-10-24, "connect page commands on the shooting Nirude statues"): like the
plain face (native_nirude_face), a variant is dormant (1A 0D) and does not fire until activated
(Active By Default, or Activate Switch from another event); the Activate actions run once when it
becomes active, its Deactivate actions once when it breaks, and it stays broken (project switch).
A Hit page gets the stock hit spot on its tile (_expand_hit_pages); the statue keeps its own reaction.
"""
import struct

FLAG_BASE = 0x8700
MAX_PER_MAP = 32
CATALOGUE = 346

# key: name, statue donor (map, entity), projectile templates on the donor map, emitter builder
VARIANTS = {
    'fire': dict(name='Nirude Face Statue (Fire)', statue=(35, 9), templates=(14,), room='35 B 3'),
    'homing': dict(name='Nirude Face Statue (Homing Fire)', statue=(38, 13), templates=(16,), room='38 B 4'),
    'laser': dict(name='Nirude Face Statue (Laser)', statue=(36, 10), templates=tuple(range(13, 22)), room='36 B 4'),
}


def variant_of(definition):
    source = (definition or {}).get('source', {})
    key = source.get('statue_variant')
    return key if source.get('variant') == 'nirude_statue' and key in VARIANTS else None


def emitter_program(key, broken, templates, active=None):
    """B program for one statue (donor template numbers; translated when installed). active: a room
    flag the statue's C sets once it is activated; the loop waits for it first (36)."""
    from event_logic_compile import _Assembler
    a = _Assembler()
    if active is not None:
        a.data.extend(bytes((0x36,)) + struct.pack('<H', active))
    if key == 'fire':                      # 35 B 3 (after its story wait): 37 78, loop
        a.data.extend(b'\x37\x78')
        a.label('loop'); a.data.append(0x00)
        a.branch(0x30, 'next', operand=broken)
        a.data.extend(bytes((0x2C, templates[0]))); a.branch(0x04, 'next')
        a.data.extend(bytes((0x2D, templates[0])))
        a.label('next'); a.data.extend(b'\x00\x00\x37\x08')   # own 2 yields + the 4 other statues' 8
        a.branch(0x02, 'loop')
    elif key == 'homing':                  # 38 B 4
        a.data.extend(b'\x37\x5a\x37\x1e')
        a.label('loop')
        a.data.extend(bytes((0x2C, templates[0]))); a.branch(0x04, 'next')
        a.branch(0x30, 'next', operand=broken)
        a.data.extend(bytes((0x2D, templates[0])))
        a.label('next'); a.data.extend(b'\x37\x1e\x37\x3c')   # own 30 + the 2 other statues' 60
        a.branch(0x02, 'loop')
    elif key == 'laser':                   # 36 B 4
        a.data.extend(b'\x37\x78')
        a.label('loop'); a.data.extend(b'\x37\x3c')
        a.branch(0x30, 'next', operand=broken)
        for t in templates:
            a.data.extend(bytes((0x2D, t, 0x37, 0x05)))
        a.data.extend(b'\x00\x00')
        a.label('next'); a.data.extend(b'\x37\xe0')           # the 2 other columns: 2 x (60 + 50 + 2)
        a.branch(0x02, 'loop')
    else:
        raise ValueError(f'Unknown Nirude statue variant {key!r}')
    return a.finish() + b'\xff'


def emitter_refs(code):
    """translate_map_refs rows for the emitter's 2D spawns and 2C tests."""
    refs, at = [], 0
    sizes = {0x36: 3, 0x00: 1, 0x02: 3, 0x04: 3, 0x2C: 2, 0x2D: 2, 0x30: 5, 0x37: 2, 0xFF: 1}
    while at < len(code):
        op = code[at]
        if op == 0x2D:
            refs.append(('spawn', at, code[at + 1], 2))
        elif op == 0x2C:
            refs.append(('select', at, code[at + 1], 2, 1, 0x2C))
        at += sizes[op]
    return refs


def next_flags(map_id, counts):
    n = counts.get(map_id, 0)
    if n >= MAX_PER_MAP:
        raise ValueError(f'Map {map_id}: at most {MAX_PER_MAP} shooting Nirude Face Statues')
    counts[map_id] = n + 1
    return FLAG_BASE + 3 * n, FLAG_BASE + 3 * n + 1, FLAG_BASE + 3 * n + 2   # hit, broken, active


def _own_program(data, session, donor_map, bank, index, mapping):
    """The donor's C / D span (program_span) with its room flags moved; other flag waits passed."""
    from behavior_transplant import program_span, FLAG_OPCODES, _skip
    from event_editor import reachable_instructions
    code, info = program_span(data, donor_map, bank, index, session)
    rows = reachable_instructions(session, donor_map, f'{bank} {index}')
    low = min(r[0] for r in rows); entry = 3 if info['entry_jump'] else 0
    code = bytearray(code); moved = []
    positions = [(offset - low + entry, op, size) for offset, op, size in rows]
    for offset, op, size in rows:
        if op not in FLAG_OPCODES or size < 3:
            continue
        at = offset - low + entry
        flag = struct.unpack_from('<H', code, at + 1)[0]
        if flag in mapping:
            struct.pack_into('<H', code, at + 1, mapping[flag]); moved.append(hex(flag))
        elif op == 0x36:
            code[at:at + 3] = _skip(3); moved.append(f'wait {flag:#x} passed')
    return bytes(code), positions, moved


BRANCHES = (0x02, 0x03, 0x04, 0x30, 0x31, 0x74, 0x78)


def tick_program(stock, positions, broken, active, active_test, broken_test, set_broken):
    """C: the plain face's activation (native_nirude_face.tick_program) around the donor's own C.
    Broken (project switch on): 05 <broken room flag> (its emitter stops), 2B, 1A 03, FF.
    Not active: 1A 0D (dormant face), test again every frame. Active: 05 <active room flag> (its
    emitter starts), then the donor's C unchanged; its 05 <broken room flag> also sets the broken switch."""
    from event_logic_compile import _Assembler
    flag = lambda v: struct.pack('<H', v)
    at05 = [at for at, op, size in positions if op == 0x05 and stock[at + 1:at + 3] == flag(broken)]
    if len(at05) != 1:
        raise ValueError('Donor statue program does not set its broken flag once')
    cut = at05[0] + 3
    for at, op, size in positions:
        if op in BRANCHES and at + size - 2 >= 0 and at + struct.unpack_from('<h', stock, at + size - 2)[0] >= cut:
            raise ValueError('Donor statue program branches past its broken flag')
    a = _Assembler()
    a.data.extend(broken_test); a.branch(3, 'broken')
    a.data.extend(bytes((0x1A, 0x0D)))
    a.label('dormant')
    a.data.extend(active_test); a.branch(3, 'wake')
    a.data.append(0x00); a.branch(2, 'dormant')
    a.label('wake')
    a.data.extend(bytes((0x05,)) + flag(active))
    a.data.extend(stock[:cut]); a.data.extend(set_broken); a.data.extend(stock[cut:])   # its tail ends with FF
    a.label('broken')
    a.data.extend(bytes((0x05,)) + flag(broken) + bytes((0x2B, 0x1A, 0x03, 0xFF)))
    return a.finish()


def install(datas, map_id, key, cache, shift, counts, active_test, broken_test, set_broken):
    """Append the statue's C / D and its emitter (B). Returns (datas, C/D hook values,
    emitter hook value, report). `cache` is the build's behaviour cache (transplant_hooks)."""
    from behavior_transplant import translate_map_refs, program_span
    from native_class_placement import record_cluster
    from native_script_allocation import append_native_process
    variant = VARIANTS[key]
    if '_snapshot' not in cache:
        from editor_session import EditSession
        cache['_snapshot'] = EditSession.readonly(bytes(datas))
    session = cache['_snapshot']
    donor_map, entity = variant['statue']
    raw = record_cluster(session.data, donor_map)['entities'][entity]
    if any(raw[10:12]) or any(raw[14:16]) or not raw[12] & 0x80 or not raw[13] & 0x80:
        raise ValueError(f'{variant["name"]}: donor {donor_map}/{entity} hooks are not C / D map programs')
    _, dinfo = program_span(session.data, donor_map, 'D', raw[13] & 0x7F, session)
    _, cinfo = program_span(session.data, donor_map, 'C', raw[12] & 0x7F, session)
    hit = [r[2] for r in dinfo['map_refs'] if r[0] == 'flagset']
    broken = [r[2] for r in cinfo['map_refs'] if r[0] == 'flagset' and r[2] not in hit]
    if len(set(hit)) != 1 or len(set(broken)) != 1:
        raise ValueError(f'{variant["name"]}: donor hit / broken flags not found')
    new_hit, new_broken, new_active = next_flags(map_id, counts)
    mapping = {hit[0]: new_hit, broken[0]: new_broken}
    c_stock, c_rows, c_moved = _own_program(session.data, session, donor_map, 'C', raw[12] & 0x7F, mapping)
    c_code = tick_program(c_stock, c_rows, new_broken, new_active, active_test, broken_test, set_broken)
    d_code, _, _ = _own_program(session.data, session, donor_map, 'D', raw[13] & 0x7F, mapping)
    datas, c = append_native_process(datas, map_id, 'C', c_code)
    datas, d = append_native_process(datas, map_id, 'D', d_code)
    code = emitter_program(key, new_broken, variant['templates'], new_active)
    datas, code, done = translate_map_refs(datas, map_id, donor_map, code, emitter_refs(code), session.data,
                                           cache, shift, boss_templates=True, as_boss=False)
    if map_id != donor_map and not any('copied_to' in r for r in done):
        raise ValueError(f'{variant["name"]}: its projectile templates could not be brought onto map {map_id}: {done}')
    datas, b = append_native_process(datas, map_id, 'B', code)
    return datas, (c['hook_value'], d['hook_value']), b['hook_value'], {
        'variant': key, 'donor': [donor_map, entity], 'stock_room_program': variant['room'],
        'hit_flag': hex(new_hit), 'broken_flag': hex(new_broken), 'active_flag': hex(new_active), 'statue_flags_moved': c_moved,
        'templates': done, 'emitter_hook': b['hook_value'], 'gameplay_verified': False}
