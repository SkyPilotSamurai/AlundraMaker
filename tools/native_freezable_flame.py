"""Launcher option "Fireballs freezable (Ice Wand)" (2026-10-22).

Stock evidence (static, DATAS map 443 entity 10, class 319 Flame): the freezable Flame's
D (touched) program is `87 80 07 / 04 +7 / 2B / 05 800A / FF`: touched by attack element 7
(the Ice Wand element; Ice Pillar 390 tests the same element), it clears class A and sets a room
flag. Its C program waits for that flag, then: clear the flag, solid on (62 80 80 00), hurt off
(63 80 02 00), animation 5, 2 x 60 frames, held while the player stands on it (3E), 30 frames,
animation 8 once, solid off, hurt on, restart (49) into its patrol.

A Launcher's Flame template (map 26) instead flies (animation 3) until hit or blocked (47) and
deactivates. With the option on, each copied Flame template gets this D program and a C program
made of the same native ops: fly; each frame test the flag (freeze as stock, then fly on), blocked
or hit (deactivate). One room flag per template (0x87F0 + n), so one frozen fireball does not
freeze the others. Source-derived composition, not a stock program; test in game.
"""
import struct

FREEZABLE_CATALOGUES = {317: 'Launcher', 342: 'Four-Way Turret'}
FLAME = 319
ICE_ELEMENT = 7
FLAG_BASE = 0x87F0


def touched_program(flag):
    """D: touched by the Ice Wand element -> clear class A, set the room flag (stock 443 D 10)."""
    return bytes((0x87, 0x80, ICE_ELEMENT, 0x04, 0x07, 0x00, 0x2B, 0x05)) + struct.pack('<H', flag) + b'\xFF'


def flight_program(flag):
    """C: fly as the Launcher's Flame; freeze like the stock freezable Flame when the flag is set."""
    f = struct.pack('<H', flag)
    head = bytes((0x2A, 0x1A, 0x03))                       # class A, fly (animation 3)
    loop = bytes((0x00,)) + b'\x30' + f + b'@@'            # yield; jump if flag set -> freeze
    loop += bytes((0x6E, 0x03)) + b'##'                    # blocked -> end
    loop += bytes((0x71, 0x03)) + b'##'                    # hit -> end
    loop += bytes((0x02,)) + b'LL'                         # back to the loop
    end = bytes((0xBD, 0x2F, 0x00, 0x19, 0xFF))            # sound 47, deactivate (stock C 35)
    freeze = b'\x06' + f + bytes((0x62, 0x80, 0x80, 0x00, 0x63, 0x80, 0x02, 0x00, 0x1A, 0x05,
                                  0x37, 0x3C, 0x37, 0x3C, 0x3E, 0x03, 0xFD, 0xFF, 0x37, 0x1E, 0x1A, 0x08, 0x1C, 0x01,
                                  0x63, 0x80, 0x80, 0x00, 0x62, 0x80, 0x02, 0x00, 0x02)) + b'HH'
    code = bytearray(head + loop + end + freeze)
    start, at_end, at_freeze = len(head), len(head) + len(loop), len(head) + len(loop) + len(end)

    def rel(pos, op_start, target):   # native relative jump: from the jump instruction's first byte
        struct.pack_into('<h', code, pos, target - op_start)
    p = code.index(b'@@'); rel(p, p - 3, at_freeze)
    for _ in range(2):
        p = code.index(b'##'); rel(p, p - 1, at_end)
    p = code.index(b'LL'); rel(p, p - 1, start)
    p = code.index(b'HH'); rel(p, p - 1, 0)   # thawed: class A, animation 3, fly on
    return bytes(code)


def make_freezable(data, target_map, raw, number):
    """Give a copied Flame template record (bytearray) the freezable C / D programs."""
    from native_script_allocation import append_native_process
    flag = FLAG_BASE + (number & 0x0F)
    data, c = append_native_process(data, target_map, 'C', flight_program(flag))
    data, d = append_native_process(data, target_map, 'D', touched_program(flag))
    raw[12], raw[13] = c['hook_value'], d['hook_value']
    return data
