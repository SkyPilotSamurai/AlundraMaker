"""Melzas fights where he is placed (2026-10-19).

Melzas's class AI (stock ALUN_CD.EXE, function 0x8007C334) spawns its doubles and
teleports to points read from two absolute tables of his own room, map 327:
  0x800280B0: 3 points (216,656) (456,656) (336,688)          set at 0x8007C4B8
  0x800280C8: 4 points (216,720) (216,848) (456,848) (456,720) set at 0x8007C4E4
(16.16 pixel pairs, file offset 0x88B0; `lui s5,0x8003; addiu s5,s5,lo`).
Placed elsewhere he vanished to those spots, off screen (BizHawk 2026-10-19).
His orbs (class 420, AI C58 0x8007CCE4) circle a fixed room centre (0x150, 0x310) =
pixel (336, 784), set by `lui` at 0x8007CE10/CE1C; Melzas's own AI uses the same centre
at 0x8007C694..C7E0 (CENTRE_SITES). Each such `lui` moves into a `jal` delay slot; its
stub adds the map's offset and then runs the instruction that followed it.

The two `lui s5` instructions become `jal` to a routine that, on a map listed here,
gives s5 a copy of the table moved by that map's placement offset, and on any other
map (his own room included) the original table. Injected code, not vanilla.
"""
import struct

CURRENT_MAP = 0x801F5358
SITES = ((0x8007C4B8, 0x80B0), (0x8007C4E4, 0x80C8))
STOCK_WORDS = {0x8007C4B8: (0x3C158003, 0x26B580B0), 0x8007C4E4: (0x3C158003, 0x26B580C8)}
# (address, register, axis 0=x 1=y): stock `lui reg, 0x150 (x) / 0x310 (y)`
CENTRE_SITES = ((0x8007C694, 7, 0), (0x8007C708, 20, 1), (0x8007C720, 7, 0), (0x8007C7A0, 21, 1),
                (0x8007C7E0, 7, 0), (0x8007CE10, 2, 0), (0x8007CE1C, 2, 1))
# Heights: the spawns also use fixed room heights (lui 0x140 = 320, 0x148 = 328; his room's floor).
# Paired: the next instruction is another such `lui`, done in the same stub (axis 2 = height).
PAIRED = {0x8007C694: (2, 1), 0x8007C708: (18, 2), 0x8007C7A0: (20, 2)}
# 0x8007C694 also covers 0x8007C69C `sw v0,0x10(sp)` and 0x8007C6A0 `lui v0,0x140` (its next is a jal):
# that stub returns past both.
FIRST_SPAWN = 0x8007C694
Z_IMM = {0x8007C708: 0x148, 0x8007C7A0: 0x148, FIRST_SPAWN: 0x140}
POINTS = 4            # copied per call (the 3-point table reads one more word pair; harmless)


def _lui(reg, axis, z=0x148):
    return 0x3C000000 | reg << 16 | (z if axis == 2 else 0x0310 if axis else 0x0150)


def verify(exe, load=0x80020000):
    for at, words in STOCK_WORDS.items():
        if struct.unpack_from('<II', exe, at - load + 0x800) != words:
            raise ValueError('Melzas point-table code is not the verified stock code')
    for at, reg, axis in CENTRE_SITES:
        if struct.unpack_from('<I', exe, at - load + 0x800)[0] != _lui(reg, axis):
            raise ValueError('Melzas centre code is not the verified stock code')
    for at, word in ((0x8007C698, _lui(2, 1)), (0x8007C69C, 0xAFA20010), (0x8007C6A0, _lui(2, 2, 0x140)),
                     (0x8007C70C, _lui(18, 2)), (0x8007C7A4, _lui(20, 2))):
        if struct.unpack_from('<I', exe, at - load + 0x800)[0] != word:
            raise ValueError('Melzas centre code is not the verified stock code')


def emit_centre(list_address, base_address, exe, load=0x80020000):
    """(code, {site: stub address}): a shared lookup (t1 = dx, t2 = dy of the current map,
    0 elsewhere) and one stub per CENTRE_SITES entry."""
    words = []

    def ins(op, rs, rt, imm): words.append(op << 26 | rs << 21 | rt << 16 | (imm & 0xFFFF))
    def li(rt, value): ins(15, 0, rt, (value + 0x8000) >> 16); ins(9, rt, rt, value)
    def addu(d, a, b): words.append(a << 21 | b << 16 | d << 11 | 0x21)
    T0, T1, T2, T3, SP, RA = 8, 9, 10, 11, 29, 31
    li(T0, CURRENT_MAP); ins(35, T0, T0, 0); li(T3, list_address)
    loop = len(words)
    ins(35, T3, T1, 0); ins(9, 0, T2, -1)
    none_at = len(words); ins(4, T1, T2, 0); words.append(0)
    hit_at = len(words); ins(4, T1, T0, 0); words.append(0)
    ins(9, T3, T3, 16); words.append(0x10000000 | ((loop - len(words) - 1) & 0xFFFF)); words.append(0)
    hit = len(words); ins(35, T3, T1, 4); ins(35, T3, T2, 8); ins(35, T3, T0, 12); words.append(RA << 21 | 8); words.append(0)
    none = len(words); words.append(T1 << 11 | 0x21); words.append(T2 << 11 | 0x21); words.append(T0 << 11 | 0x21)  # 0
    words.append(RA << 21 | 8); words.append(0)
    for at, target in ((none_at, none), (hit_at, hit)):
        words[at] = (words[at] & 0xFFFF0000) | ((target - at - 1) & 0xFFFF)
    stubs = {}
    for at, reg, axis in CENTRE_SITES:
        stubs[at] = base_address + 4 * len(words)
        ins(9, SP, SP, -24); ins(43, SP, RA, 0)
        for k, r in enumerate((T0, T1, T2, T3)): ins(43, SP, r, 4 + 4 * k)
        words.append(0x0C000000 | ((base_address >> 2) & 0x3FFFFFF)); words.append(0)      # jal lookup
        pick = lambda axis: (T1, T2, T0)[axis]
        addu(reg, reg, pick(axis))
        if at in PAIRED:
            reg2, axis2 = PAIRED[at]; words.append(_lui(reg2, axis2, Z_IMM.get(at, 0x148))); addu(reg2, reg2, pick(axis2))
        if at == FIRST_SPAWN:      # sw v0,0x10(sp) on the caller's frame, then v0 = height
            ins(43, SP, 2, 0x10 + 24); words.append(_lui(2, 2, 0x140)); addu(2, 2, T0)
        ins(35, SP, RA, 0)
        for k, r in enumerate((T0, T1, T2, T3)): ins(35, SP, r, 4 + 4 * k)
        if at == FIRST_SPAWN:
            ins(9, RA, RA, 8)       # return past 0x8007C69C / 0x8007C6A0
        ins(9, SP, SP, 24)
        if at not in PAIRED:
            words.append(struct.unpack_from('<I', exe, at + 4 - load + 0x800)[0])   # the instruction that followed
        words.append(RA << 21 | 8); words.append(0)
    return b''.join(struct.pack('<I', w) for w in words), stubs


def patch_centre(output, stubs, load):
    """Each site: `jal stub` with the stock `lui` in its delay slot (stub adds the offset)."""
    for at, reg, axis in CENTRE_SITES:
        struct.pack_into('<II', output, at - load + 0x800, 0x0C000000 | ((stubs[at] >> 2) & 0x3FFFFFF), _lui(reg, axis))


def data_block(places):
    """List (map, dx, dy as 16.16), ended by -1, then a 4-point scratch table."""
    rows = b''.join(struct.pack('<iiii', m, d[0] << 16, d[1] << 16, (d[2] if len(d) > 2 else 0) << 16)
                    for m, d in sorted(places.items()))
    return rows + struct.pack('<i', -1) + bytes(8 * POINTS)


def emit(list_address, scratch_address):
    """(code for site 1, code for site 2) sharing one body; each starts with the site's low half."""
    words = []

    def ins(op, rs, rt, imm): words.append(op << 26 | rs << 21 | rt << 16 | (imm & 0xFFFF))
    def li(rt, value): ins(15, 0, rt, (value + 0x8000) >> 16); ins(9, rt, rt, value)
    T0, T1, T2, T3, T4, S5, SP, RA = 8, 9, 10, 11, 12, 21, 29, 31
    # entry 1 / entry 2: finish `s5 = table` (lui s5,0x8003 ran in the jal delay slot)
    ins(9, S5, S5, SITES[0][1]); words.append(0x10000000 | 2); words.append(0)      # b body
    ins(9, S5, S5, SITES[1][1])
    body = len(words)
    ins(9, SP, SP, -24)
    for k, r in enumerate((T0, T1, T2, T3, T4)): ins(43, SP, r, 4 * k)
    li(T0, CURRENT_MAP); ins(35, T0, T0, 0); words.append(0)
    li(T1, list_address)
    loop = len(words)
    ins(35, T1, T2, 0); words.append(0)                          # t2 = map
    ins(15, 0, T3, 0xFFFF); ins(13, T3, T3, 0xFFFF)              # t3 = -1
    done_branch = len(words); ins(4, T2, T3, 0); words.append(0)  # beq t2,-1 -> done
    hit_branch = len(words); ins(4, T2, T0, 0); words.append(0)   # beq t2,map -> hit
    ins(9, T1, T1, 16); words.append(0x10000000 | ((loop - len(words) - 1) & 0xFFFF)); words.append(0)
    hit = len(words)
    ins(35, T1, T2, 4); ins(35, T1, T3, 8); li(T0, scratch_address)
    for k in range(POINTS):
        ins(35, S5, T4, 8 * k); words.append(0); words.append(T4 << 21 | T2 << 16 | T4 << 11 | 0x21)  # addu t4,t4,t2
        ins(43, T0, T4, 8 * k)
        ins(35, S5, T4, 8 * k + 4); words.append(0); words.append(T4 << 21 | T3 << 16 | T4 << 11 | 0x21)
        ins(43, T0, T4, 8 * k + 4)
    words.append(T0 << 21 | S5 << 11 | 0x21)                      # move s5, t0
    done = len(words)
    for k, r in enumerate((T0, T1, T2, T3, T4)): ins(35, SP, r, 4 * k)
    words.append(RA << 21 | 8)                                    # jr ra
    ins(9, SP, SP, 24)
    for at, target in ((done_branch, done), (hit_branch, hit)):
        words[at] = (words[at] & 0xFFFF0000) | ((target - at - 1) & 0xFFFF)
    return b''.join(struct.pack('<I', w) for w in words), (0, 3)


def patch_sites(output, code_address, load):
    """Each site: `jal entry` then the stock `lui s5,0x8003` in its delay slot."""
    for (at, _), entry in zip(SITES, (0, 3)):
        target = code_address + 4 * entry
        struct.pack_into('<II', output, at - load + 0x800, 0x0C000000 | ((target >> 2) & 0x3FFFFFF), 0x3C158003)
