"""Bosses fight where they are placed: their native AI's fixed room positions and heights
follow the placement (2026-10-19; Melzas has his own module, native_melzas_points).

SITES[class] lists instructions of the stock US Rev 1 ALUN_CD.EXE (load 0x80020000) that load a
fixed room coordinate into a register: (address, stock word, register, axis 0=x 1=y 2=height).
Each becomes `jal stub` with the stock instruction kept in the delay slot; the stub adds the
offset (placed - donor record, 16.16) of the current map (0x801F5358) when that map has an
event-placed copy of the class (0 elsewhere, his own room included), then runs the stock
instruction that followed the site and returns after it. A site's following instruction must not
be a branch, jump or branch target, and must not use t0-t3 (checked in tests). Injected code.

Zorgia (509, C44 0x80074160, research/us_decomp/ai/80074160_C44.c line 64): every 300 frames spawns
class 511 at one of 5 points of map 321 (table 0x8002784C: (156,632) (516,632) (156,920) (516,920)
(336,768)) at height 0x150 = 336.
Wilda (412, C51 0x80079E4C, decomp lines 419, 589, 643): falling rocks (class EC) at 6 points of map 325
(table 0x80027E90: (48,240) (144,288) (48,336) (144,240) (48,288) (144,336)) at height 3; dust effects at
4 points (table 0x80027E70: (24,208) (264,208) (24,288) (264,288)) at height 0x110 = 272; and a test
"player above y 303" (lui 0x12F, ori 0xFFFF).
"""
import struct

CURRENT_MAP = 0x801F5358
SITES = {
    509: ((0x800741C0, 0x3C020150, 2, 2),     # lui v0,0x150   spawn height
          (0x800741D4, 0x8C27784C, 7, 0),     # lw a3,0x784c(at)  point x
          (0x800741E0, 0x8C227850, 2, 1)),    # lw v0,0x7850(at)  point y
    412: ((0x8007A8D8, 0x8C247E90, 4, 0),     # lw a0,0x7e90(at)  rock point x
          (0x8007A904, 0x8C247E94, 4, 1),     # lw a0,0x7e94(at)  rock point y
          (0x8007A928, 0x3C020003, 2, 2),     # lui v0,3          rock height
          (0x8007ADEC, 0x3C020110, 2, 2),     # lui v0,0x110      dust height
          (0x8007AE0C, 0x8C227E70, 2, 0),     # lw v0,0x7e70(at)  dust point x
          (0x8007AE30, 0x8C287E74, 8, 1),     # lw t0,0x7e74(at)  dust point y (t0: added to its saved copy)
          (0x8007AFF0, 0x3C04012F, 4, 1)),    # lui a0,0x12f      upper-half test y
    # 463 (map 471, home (636,616,224)): A22 0x80063C5C spawns class D1 at (576|720, 608) height 244;
    # C89 0x800640C4: random point around (480,640), x table 0x80026C98 (552,744), y 672, height tests 160 / 399;
    # C90 0x80064E14: x table 0x80026CEC (576,720), y 608, height 160. (0x80026CA0 / 0x80026CF4 are relative.)
    # A22 saves ra only at 0x80063C80, so its first spawn's lui s1,0xf4 (C6C) / lui a3,0x240 (C78) are offset from
    # 0x80063C84 (sw s6,0x38(sp)), after both are loaded: a stub's jal before that point lost A22's return (hang).
    463: ((0x80063C84, 0xAFB60038, 17, 2, ((7, 0),)), (0x80063CA0, 0x3C020260, 2, 1),
          (0x80063CC0, 0x3C150260, 21, 1), (0x80063CDC, 0x3C070240, 7, 0), (0x80063D04, 0x3C1100F4, 17, 2),
          (0x80063D14, 0x3C0702D0, 7, 0, ((2, 1),)),     # its next is lui v0,0x260 (y): added in the same stub
          (0x80063D38, 0x3C150260, 21, 1), (0x80063D58, 0x3C0702D0, 7, 0),
          (0x80064284, 0x3C0501E0, 5, 0), (0x800642C4, 0x3C060280, 6, 1),
          (0x800645BC, 0x8C236C98, 3, 0, ((2, 1),)),     # next lui v0,0x2a0 (y)
          (0x800649D8, 0x3C0200A0, 2, 2), (0x80064AC0, 0x8C226C98, 2, 0), (0x80064AE0, 0x3C0302A0, 3, 1),
          (0x80064AF0, 0x3C02018F, 2, 2),
          (0x80064ED8, 0x3C1500A0, 21, 2, ((20, 1),)),   # lui s4,0x260 just before sits in a branch delay slot
          (0x80064F14, 0x8C286CEC, 8, 0)),
    # Watcher In The Water 485 (map 76, home (444,512,16)), C38 0x80071080 (decomp lines 248-260, 304, 335):
    # spawns near the player clamped to the room (x 300..612, y 376..600): the candidate point is moved into room
    # coordinates before the stock clamp (axes 3/4 = minus) and back after; "player below y 503"; a spawn
    # around (336, 384).
    485: ((0x800716E8, 0x00826821, 13, 3),             # addu t5,a0,v0  candidate x - dx
          (0x8007170C, 0x00822021, 4, 4),              # addu a0,a0,v0  candidate y - dy (t4 = a0 - 32 next)
          (0x80071768, 0x01A03821, 12, 1, ((7, 0),)),  # move a3,t5: t4 + dy before `sw t4`, then a3 + dx
          (0x800718C0, 0x34C6FFFF, 6, 1),              # ori a2 (0x01F7FFFF) player y test
          (0x80071A14, 0x3C070180, 7, 1),              # lui a3,0x180  spawn y 384
          (0x80071A44, 0x3C080150, 8, 0)),             # lui t0,0x150  spawn x 336
    # Nirude (With Body) 495 (map 324, home (360,32,0)), C50 0x8007947C (decomp lines 120-131, 159-165): dust at x 480 / 240
    # height 160; rock spawns at x column*24 + 336 with y <= 831. Both lui t4 (x 480 / 240) reach 0x800796B0.
    495: ((0x800796B0, 0x3C02800A, 12, 0),   # lui v0,0x800a  (t4 = dust x, + dx)
          (0x80079720, 0x3C0200A0, 2, 2),    # lui v0,0xa0    dust height 160
          (0x800798EC, 0x3C030150, 3, 0),    # lui v1,0x150   spawn x 336
          (0x80079920, 0x3442FFFF, 2, 1)),   # ori v0         y limit 0x033FFFFF
    # Zazan 506 (map 153, home (444,208,80)), C43 0x800736A4 (decomp lines 157-159, 266-271): spawns class FC at the
    # 4 points of table 0x800277FC ((252,328) (252,424) (660,328) (660,424)); bounces inside x 264..647, y 256..511.
    506: ((0x80073A88, 0x8C2777FC, 7, 0),
          (0x80073A94, 0x8C227800, 2, 1),
          (0x80073DD8, 0x3C020108, 2, 0),
          (0x80073DE8, 0x3442FFFF, 2, 0),
          (0x80073E18, 0x3C020100, 2, 1),
          (0x80073E28, 0x3442FFFF, 2, 1)),
    # Dark Dragon 479 (map 323, home (324,776,384)), C49 0x800780A4: arena bounds x 144..527, y 624..911 / 943
    # and y <= 863 (decomp lines 136-142, 416, 443-447). lui+ori bounds are offset at the ori (its lui can sit in
    # a branch delay slot). Its circling centres are (own position - table point + constant): they follow it already.
    # The table 0x80027C3C ((192,704) (336,704) (480,704) (336,688)) is offset only where it steers him toward a
    # point (0x80078AAC x / 0x80078AB8 y, decomp line 350); the centre formulas use it as (own position - point).
    479: ((0x80078AAC, 0x8C237C3C, 3, 0), (0x80078AB8, 0x8C227C40, 2, 1), (0x800782B4, 0x3C020090, 2, 0), (0x800782CC, 0x3442FFFF, 2, 0), (0x8007832C, 0x3C020270, 2, 1), (0x80078344, 0x3442FFFF, 2, 1), (0x80078CD4, 0x3442FFFF, 2, 1), (0x80078E5C, 0x3C020090, 2, 0), (0x80078E6C, 0x3442FFFF, 2, 0), (0x80078EA0, 0x3C020270, 2, 1), (0x80078EB0, 0x3442FFFF, 2, 1)),
}


# Room flags a boss's own AI waits for before it fights, set by its home room's intro scene
# (placed elsewhere they are set by a whole-map program as the map starts).
# Wilda: C51 acts only while 0x801E6384 bit 0x10 = flag 8064 (decomp line 125); map 325 C 2 sets it
# after the intro text (05 64 80), B 1 waits for it.
START_FLAGS = {412: (0x8064,),
               463: (0x8001,),
               488: (0x8000,)}   # 488 Corpse Worm: C47 (0x800762E8, decomp line 137) waits for 0x801E6378 bit 1 (stress test 2026-10-21)   # 463: C89 / C90 attack only while 0x801E6378 bit 2 (map 471 B 1 sets 8001 after its intro)


def start_program(flags):
    return b''.join(bytes((0x05, f & 0xFF, f >> 8)) for f in flags) + bytes((0xFF,))


def verify(exe, classes, load=0x80020000):
    for c in classes:
        for at, word, *_ in SITES[c]:
            if struct.unpack_from('<I', exe, at - load + 0x800)[0] != word:
                raise ValueError(f'Boss {c}: native code at {at:08X} is not the verified stock code')


def data_block(places):
    """(bytes, {class: offset in block}): per class, rows (map, dx, dy, dz as 16.16) ended by -1."""
    out, where = b'', {}
    for c in sorted(places):
        where[c] = len(out)
        out += b''.join(struct.pack('<iiii', m, d[0] << 16, d[1] << 16, d[2] << 16) for m, d in sorted(places[c].items()))
        out += struct.pack('<i', -1)
    return out, where


def emit(lists, base_address, exe, load=0x80020000):
    """(code, {site: stub address}); lists = {class: address of its rows}."""
    words = []

    def ins(op, rs, rt, imm): words.append(op << 26 | rs << 21 | rt << 16 | (imm & 0xFFFF))
    def li(rt, value): ins(15, 0, rt, (value + 0x8000) >> 16); ins(9, rt, rt, value)
    def addu(d, a, b): words.append(a << 21 | b << 16 | d << 11 | 0x21)
    def add_axis(d, a, axis):     # axis 0-2: + dx/dy/dz; 3-5: - dx/dy/dz (subu)
        words.append(a << 21 | (T1, T2, T0)[axis % 3] << 16 | d << 11 | (0x23 if axis >= 3 else 0x21))
    T0, T1, T2, T3, SP, RA = 8, 9, 10, 11, 29, 31
    # lookup (t3 = rows): t1, t2, t0 = dx, dy, dz of the current map, else 0
    li(T0, CURRENT_MAP); ins(35, T0, T0, 0)
    loop = len(words)
    ins(35, T3, T1, 0); ins(9, 0, T2, -1)
    none_at = len(words); ins(4, T1, T2, 0); words.append(0)
    hit_at = len(words); ins(4, T1, T0, 0); words.append(0)
    ins(9, T3, T3, 16); words.append(0x10000000 | ((loop - len(words) - 1) & 0xFFFF)); words.append(0)
    hit = len(words); ins(35, T3, T1, 4); ins(35, T3, T2, 8); ins(35, T3, T0, 12); words.append(RA << 21 | 8); words.append(0)
    none = len(words); words.append(T1 << 11 | 0x21); words.append(T2 << 11 | 0x21); words.append(T0 << 11 | 0x21)
    words.append(RA << 21 | 8); words.append(0)
    for at, target in ((none_at, none), (hit_at, hit)):
        words[at] = (words[at] & 0xFFFF0000) | ((target - at - 1) & 0xFFFF)
    stubs = {}
    for c, rows in sorted(lists.items()):
        for at, _, reg, axis, *more in SITES[c]:
            stubs[at] = base_address + 4 * len(words)
            ins(9, SP, SP, -24); ins(43, SP, RA, 0)
            for k, r in enumerate((T0, T1, T2, T3)): ins(43, SP, r, 4 + 4 * k)
            li(T3, rows)
            words.append(0x0C000000 | ((base_address >> 2) & 0x3FFFFFF)); words.append(0)
            if reg in (T0, T1, T2, T3):     # the stub's own registers: add to the saved copy
                slot = 4 + 4 * (T0, T1, T2, T3).index(reg)
                ins(35, SP, T3, slot); words.append(0); add_axis(T3, T3, axis); ins(43, SP, T3, slot)
            else:
                add_axis(reg, reg, axis)
            ins(35, SP, RA, 0)
            for k, r in enumerate((T0, T1, T2, T3)): ins(35, SP, r, 4 + 4 * k)
            ins(9, SP, SP, 24)
            words.append(struct.unpack_from('<I', exe, at + 4 - load + 0x800)[0])   # the instruction after the site
            if more:      # registers the following instruction (or one just before) set: add their offsets too
                ins(9, SP, SP, -24); ins(43, SP, RA, 0)
                for k, r in enumerate((T0, T1, T2, T3)): ins(43, SP, r, 4 + 4 * k)
                li(T3, rows); words.append(0x0C000000 | ((base_address >> 2) & 0x3FFFFFF)); words.append(0)
                for reg2, axis2 in more[0]:
                    add_axis(reg2, reg2, axis2)
                ins(35, SP, RA, 0)
                for k, r in enumerate((T0, T1, T2, T3)): ins(35, SP, r, 4 + 4 * k)
                ins(9, SP, SP, 24)
            words.append(RA << 21 | 8); words.append(0)
    return b''.join(struct.pack('<I', w) for w in words), stubs


def patch(output, exe, lists, stubs, load):
    """Site: `jal stub`, stock instruction in the delay slot (the stub runs the one after it)."""
    for c in lists:
        for at, word, *_ in SITES[c]:
            struct.pack_into('<II', output, at - load + 0x800, 0x0C000000 | ((stubs[at] >> 2) & 0x3FFFFFF), word)
