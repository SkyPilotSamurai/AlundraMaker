"""Step-on switch press tests that only count some things (user 2026-10-26).

The game's own tests count anything: 3F 'anything standing on this' (8003F1E0) and
3C 'anything solid on these tiles' (8003EFEC). These two editor opcodes are the same
loops over the actor table (801AC6F8, stride 0x294, count at 801E93EC) with one more
check: the actor is Alundra (slot 0) or its catalogue id (+0x68) is in PRESSERS.
Enemies, vases, wooden crates, spike balls and platforms never press.
  F0       : something allowed stands on this actor        (like 3F, 1 byte)
  F1 x1 x2 y1 y2 z1 z2 : something allowed on these tiles   (like 3C, 7 bytes)
Not verified in game."""
import struct

RIDE = 0xF0
BOX = 0xF1
SIZES = {RIDE: 1, BOX: 7}
# Spring Bean 1, Barrel 290, Rock 293, Pushable Pillar (One Tile) 298, Carryable Ice Block 304,
# Ice Pillar 390, Pushable Pillar 430 (Power Glove Rock 234 left out, user 2026-10-26)
PRESSERS = (1, 290, 293, 298, 304, 390, 430)
ACTORS = 0x801AC6F8
STRIDE = 0x294
COUNT_HI, COUNT_LO = 0x801E, -0x6C14   # lw (0x801E93EC)


class _M:
    def __init__(s): s.w = []; s.lab = {}; s.br = []
    def i(s, op, rs, rt, im): s.w.append(op << 26 | rs << 21 | rt << 16 | (im & 0xFFFF))
    def r(s, rs, rt, rd, f): s.w.append(rs << 21 | rt << 16 | rd << 11 | f)
    def nop(s): s.w.append(0)
    def lw(s, rt, rs, off, op=35): s.i(op, rs, rt, off); s.nop()
    def b(s, op, rs, rt, label): s.br.append((len(s.w), label)); s.i(op, rs, rt, 0); s.nop()
    def bltz(s, rs, label): s.br.append((len(s.w), label)); s.w.append(1 << 26 | rs << 21); s.nop()
    def L(s, label): s.lab[label] = len(s.w)
    def li(s, rt, v): s.i(15, 0, rt, (v + 0x8000) >> 16); s.i(9, rt, rt, v)
    def ret(s, size): s.w.append(0x03E00008); s.i(9, 0, 2, size)   # jr ra; v0 = instruction size
    def finish(s):
        for at, label in s.br: s.w[at] |= (s.lab[label] - at - 1) & 0xFFFF
        return struct.pack('<%dI' % len(s.w), *s.w)


def _allowed(m, slot, actor, tmp, tmp2):
    m.b(4, slot, 0, 'yes')                 # slot 0: Alundra
    m.lw(tmp, actor, 0x68, 37)             # lhu catalogue id
    for c in PRESSERS:
        m.i(9, 0, tmp2, c); m.b(4, tmp, tmp2, 'yes')


def emit_ride():
    """F0. a0 = this actor, a3 = context (+2C result)."""
    m = _M(); V0, V1, A0, A1, A2, A3, T1, T2 = 2, 3, 4, 5, 6, 7, 9, 10
    m.i(15, 0, A2, COUNT_HI); m.lw(A2, A2, COUNT_LO)
    m.li(V1, ACTORS); m.r(0, 0, A1, 0x21)
    m.bltz(A2, 'none')
    m.L('loop')
    m.lw(T1, V1, 0x10); m.i(9, T1, T1, -2); m.i(11, T1, T1, 2); m.b(4, T1, 0, 'next')   # status 2 or 3
    m.lw(T1, V1, 0x20); m.b(5, T1, 0, 'next')
    m.lw(T1, V1, 0x12C); m.b(5, T1, A0, 'next')    # standing on this actor
    _allowed(m, A1, V1, T1, T2)
    m.L('next')
    m.i(9, A1, A1, 1); m.i(9, V1, V1, STRIDE); m.r(A2, A1, T1, 0x2A); m.b(4, T1, 0, 'loop')
    m.L('none'); m.i(43, A3, 0, 0x2C); m.ret(1)
    m.L('yes'); m.i(9, 0, T1, 1); m.i(43, A3, T1, 0x2C); m.ret(1)
    return m.finish()


def emit_box():
    """F1 x1 x2 y1 y2 z1 z2. a2 -> opcode pointer, a3 = context."""
    m = _M(); V0, V1, A1, A2, A3 = 2, 3, 5, 6, 7
    T0, T1, T2, T3, T4, T5, T6, T7, T8, T9 = 8, 9, 10, 11, 12, 13, 14, 15, 24, 25
    m.lw(V0, A2, 0)
    for reg, k in ((T7, 1), (T6, 2), (T5, 3), (T4, 4), (T3, 5), (T2, 6)): m.lw(reg, V0, k, 36)
    m.i(15, 0, T1, COUNT_HI); m.lw(T1, T1, COUNT_LO)
    m.li(V1, ACTORS); m.r(0, 0, T0, 0x21)
    m.bltz(T1, 'none')
    m.L('loop')
    m.lw(T8, V1, 0x10); m.i(9, T8, T9, -1); m.i(11, T9, T9, 2); m.b(5, T9, 0, 'live')   # status 1, 2
    m.i(9, 0, T9, 3); m.b(5, T8, T9, 'next')                                             # or 3
    m.L('live')
    m.lw(T9, V1, 0x6C); m.i(12, T9, T9, 0x80); m.b(4, T9, 0, 'next')
    m.lw(T9, V1, 0xB4); m.i(12, T9, T9, 0x80); m.b(5, T9, 0, 'next')
    m.lw(T9, V1, 0x28); m.b(5, T9, 0, 'next')
    for off, lo, hi in ((0x120, T7, T6), (0x124, T5, T4), (0x128, T3, T2)):
        m.lw(T9, V1, off)
        m.r(T9, lo, V0, 0x2A); m.b(5, V0, 0, 'next')   # below the box
        m.r(hi, T9, V0, 0x2A); m.b(5, V0, 0, 'next')   # above it
    _allowed(m, T0, V1, T9, V0)
    m.L('next')
    m.i(9, T0, T0, 1); m.i(9, V1, V1, STRIDE); m.r(T1, T0, T9, 0x2A); m.b(4, T9, 0, 'loop')
    m.L('none'); m.i(43, A3, 0, 0x2C); m.ret(7)
    m.L('yes'); m.i(9, 0, T9, 1); m.i(43, A3, T9, 0x2C); m.ret(7)
    return m.finish()
