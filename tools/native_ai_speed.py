"""Melzas's speed setting also shortens his own waits (user 2026-10-26).

Stock ALUN_CD.EXE US 1.1: Melzas (catalogue 418) runs built-in C program 55 every frame (C table
0x800C6D9C, entry 0x800C6E78 -> 0x8007C32C, a0 = his actor). His waits are the countdown at
actor+0x282 (decremented by one per call: 0x8007C3D0, 0x8007C65C, 0x8007C9C8, 0x8007CAB0) and his
code compares it with exact values (0xB4 / 0x78 / 0x3C at 0x8007C858), so the countdown cannot
simply step faster. Instead the C-table entry points at this wrapper: on a listed map it runs his
program once as usual, then up to factor-1 more times in the same frame while his countdown is
still running (+0x282 != 0) and his target animation (+0x88) has not changed, so every wait ends
factor times sooner and each change of state still happens once per frame. Other maps: one call.
His doubles (catalogue 424, C program 56: entry 0x800C6E7C -> 0x8007CB30, same countdown +0x282
at 0x8007CB94) get the same wrapper on the same maps (user 2026-10-26).
List: [u16 map, u16 factor] ..., u16 0. Original MIPS, not vanilla code."""
import struct

TARGETS = ((0x800C6E78, 0x8007C32C), (0x800C6E7C, 0x8007CB30))   # Melzas C55, doubles C56
CURRENT_MAP = 0x801F5358


def verify(exe, load):
    for entry, original in TARGETS:
        if struct.unpack_from('<I', exe, entry - load + 0x800)[0] != original:
            raise ValueError('Melzas C program entry differs from the stock game')


def emit(list_address, ORIGINAL=TARGETS[0][1]):
    w = []
    def I(op, rs, rt, im): w.append(op << 26 | rs << 21 | rt << 16 | (im & 0xFFFF))
    def li(rt, v): I(15, 0, rt, (v + 0x8000) >> 16); I(9, rt, rt, v)
    lab = {}; br = []
    def b(op, rs, rt, label): br.append((len(w), label)); I(op, rs, rt, 0); w.append(0)
    SP, RA, S0, S1, S2, A0, V0, T0, T1, T2 = 29, 31, 16, 17, 18, 4, 2, 8, 9, 10
    I(9, SP, SP, -0x28); I(43, SP, RA, 0x20); I(43, SP, S0, 0x14); I(43, SP, S1, 0x18); I(43, SP, S2, 0x1C)
    w.append(A0 << 21 | S0 << 11 | 0x21)                       # s0 = actor
    li(T0, CURRENT_MAP); I(35, T0, T0, 0); li(T1, list_address); I(9, 0, S1, 1)
    lab['find'] = len(w)
    I(37, T1, T2, 0); w.append(0)
    b(4, T2, 0, 'run')
    b(5, T2, T0, 'next')
    I(37, T1, S1, 2); br.append((len(w), 'run')); I(4, 0, 0, 0); w.append(0)
    lab['next'] = len(w)
    I(9, T1, T1, 4); br.append((len(w), 'find')); I(4, 0, 0, 0); w.append(0)
    lab['run'] = len(w)
    w.append(0x0C000000 | (ORIGINAL >> 2 & 0x3FFFFFF)); w.append(S0 << 21 | A0 << 11 | 0x21)
    lab['more'] = len(w)
    I(9, S1, S1, -1)
    b(6, S1, 0, 'done')                                        # blez s1
    I(37, S0, T0, 0x282); w.append(0)
    b(4, T0, 0, 'done')                                        # no wait running
    I(35, S0, S2, 0x88)                                        # target animation before
    w.append(0x0C000000 | (ORIGINAL >> 2 & 0x3FFFFFF)); w.append(S0 << 21 | A0 << 11 | 0x21)
    I(35, S0, T0, 0x88); w.append(0)
    b(4, T0, S2, 'more')
    lab['done'] = len(w)
    I(35, SP, RA, 0x20); I(35, SP, S0, 0x14); I(35, SP, S1, 0x18); I(35, SP, S2, 0x1C)
    w.append(0x03E00008); I(9, SP, SP, 0x28)
    for at, label in br:
        w[at] |= (lab[label] - at - 1) & 0xFFFF
    return struct.pack('<%dI' % len(w), *w)


def map_list(factors):
    return b''.join(struct.pack('<HH', m, f) for m, f in sorted(factors.items())) + bytes(4)


def emit_all(list_address):
    """One wrapper per target, back to back (each the same size)."""
    return b''.join(emit(list_address, original) for _, original in TARGETS)


def patch(exe, load, code_address):
    verify(exe, load)
    exe = bytearray(exe); size = len(emit(0))
    for k, (entry, _) in enumerate(TARGETS):
        struct.pack_into('<I', exe, entry - load + 0x800, code_address + k * size)
    return exe
