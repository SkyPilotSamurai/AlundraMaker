"""Nirude Face Statue (catalogue 346) placed with an activation (user 2026-10-24): it cannot be
destroyed until it is activated (Active By Default, or Activate Switch from another event), then
breaks the stock way, and breaking runs the event's Deactivate actions once.

Stock evidence (static, DATAS map 17 = Overworld E1 (Nirude sector), entities 6/7/8, sprite 90,
hooks C 86/87/88, D 86/87/88; decoded with event_editor.instructions):
  D 6: 05 0680 FF - a hit sets room flag 0x8006.
  C 6: 30 C704 -> broken (flag 0x04C7 set: 2B, 1A 03 broken face, FF); 1A 0D (dormant face);
       36 C604 (waits for flag 0x04C6); BD 5500, 1A 0B, 1D 01, BE 5500 (wakes up);
       then three stages of five hits: 73 05 { 1A s, 1D 01, hit, 1A 4+s, 1D 01 } 74, 1A 7+s, 1D 01
       (s = 0, 1, 2), hit = 2A (hittable), wait until 0x8006, 2B, 06 0680 (called with 78 / 7D);
       then 05 C704 (broken, a permanent game flag) and the broken face 1A 03.
  So the stock face takes 15 hits from any attack that reaches it once its flag is set, and stays
  broken for good.
This program keeps those ops and that order. The two story flags become this event's project
switches (activated: its object state; broken: its broken switch) and 0x8006 becomes its own room
flag 0x8760 + n (no stock map script uses 8760-877F: scan of all 483 maps' event roots, ops
05 / 06 / 30 / 31 / 36, 2026-10-24)."""
import struct

FLAG_BASE = 0x8760
MAX_PER_MAP = 32
CATALOGUE = 346


def is_face(definition):
    source = (definition or {}).get('source', {})
    return source.get('catalogue_index') == CATALOGUE and not source.get('variant')


def touched_program(flag):
    return bytes((0x05,)) + struct.pack('<H', flag) + bytes((0xFF,))


def tick_program(flag, active_test, broken_test, set_broken):
    """C program. active_test / broken_test: project conditions (Result true when on)."""
    from event_logic_compile import _Assembler
    a = _Assembler(); f = struct.pack('<H', flag)
    a.data.extend(broken_test); a.branch(3, 'broken')
    a.data.extend(bytes((0x1A, 0x0D)))                    # dormant face
    a.label('dormant')
    a.data.extend(active_test); a.branch(3, 'wake')
    a.data.append(0x00); a.branch(2, 'dormant')           # yield, test again
    a.label('wake')
    a.data.extend(bytes((0xBD, 0x55, 0x00, 0x1A, 0x0B, 0x1D, 0x01, 0xBE, 0x55, 0x00)))
    for stage in range(3):
        a.data.extend(bytes((0x73, 0x05)))
        a.label(f'stage{stage}')
        a.data.extend(bytes((0x1A, stage, 0x1D, 0x01, 0x2A)))
        a.label(f'wait{stage}')
        a.data.extend(bytes((0x37, 0x01)))
        a.branch(0x31, f'wait{stage}', operand=flag)     # until hit (flag set): wait
        a.data.extend(bytes((0x2B, 0x06)) + f + bytes((0x1A, 4 + stage, 0x1D, 0x01)))
        a.branch(0x74, f'stage{stage}')                    # five hits per stage
        a.data.extend(bytes((0x1A, 7 + stage, 0x1D, 0x01)))
    a.data.extend(set_broken)
    a.label('broken')
    a.data.extend(bytes((0x2B, 0x1A, 0x03, 0xFF)))
    return a.finish()


def next_flag(map_id, counts):
    n = counts.get(map_id, 0)
    if n >= MAX_PER_MAP:
        raise ValueError(f'Map {map_id}: at most {MAX_PER_MAP} Nirude Face Statues with an activation')
    counts[map_id] = n + 1
    return FLAG_BASE + n


def install(datas, map_id, hooks, counts, active_test, broken_test, set_broken):
    """Append this statue's C and D programs; returns (datas, hooks, report)."""
    from native_script_allocation import append_native_process
    flag = next_flag(map_id, counts)
    datas, c = append_native_process(datas, map_id, 'C', tick_program(flag, active_test, broken_test, set_broken))
    datas, d = append_native_process(datas, map_id, 'D', touched_program(flag))
    row = bytearray(hooks)
    row[2] = c['hook_value']; row[3] = d['hook_value']
    return datas, bytes(row), {'room_flag': flag, 'C': c, 'D': d, 'hits': 15, 'source': 'map 17 entity 6 C 86 / D 86'}
