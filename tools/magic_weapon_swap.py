"""Mod option "Magic & weapon swap" (2026-10-24, docs/2026-10-24-magic-weapon-swap.txt).

After the remake's Mods > Magic & Weapon Swap (remake/lr_swap.py menu_circle / picked_weapon /
keeps_scroll): the game always uses the best item of a group; with this option Circle on a
weapon slot or a magic slot of the inventory menu picks the next item of that group Alundra has,
and the group then uses the picked one.

ALUN_CD.EXE (US 1.1, load 0x80020000), static reading:
  0x8004F810 best_of_group(a0 grp) -> item, -1 none; called by equipped_kind 0x8004F6C0 (through the
             per-group wrappers 0x8004F904..) and selected_item 0x8004F784 (which moves the chosen
             item, stats+0xC, to its group's best).  19 direct jal callers.
  0x80058308 inventory menu input; pad repeat 0x801DDA4E; cursor 0x801531F0 (0..23); Cross 0x40 at
             0x8005869C; cancel mask 0x813 at 0x800586E8; Circle 0x20 unused there.
  Slot item s32[24] 0x800BBD30 (-1: call accessor s32[24] 0x800BBCD0), item records 0x800BBE50 + 10*n
  (+0 group), next_in_group 0x8004FD08(a0 start, a1 grp), has_item 0x8004FAC4, equip 0x8004FB28,
  choose_item 0x8004FB84, menu sound 0x8004A128(1), name retype counter 0x801531B4.
Hooks (prepend allocation, signature-checked):
  0 0x8004F810/14 `addiu sp,-0x18; sw ra,0x10(sp)` -> `j best_hook; nop`: when the pick byte of grp
    (table in the block, 32 bytes) names an item of grp that Alundra has, return it; else stock.
  1 0x800586D8 `lui s0,0x801E` -> `jal circle_hook` (delay slot `addiu s0,s0,-0x25B2` kept; the hook
    sets s0 = 0x801DDA4E itself): Circle on a slot of group 1..6 (weapons) or 16..19 (scroll/book)
    stores the next owned item of the group as the pick, equips the group (weapons) or chooses the
    item (magic), plays sound 1 and retypes the name.
Picks live in the injected block (RAM): zero (stock best) after power-on; not saved."""
import struct

BEST, BEST_STOCK = 0x8004F810, (0x27BDFFE8, 0xAFBF0010, 0x00802821, 0x2CA20020)
MENU_HOOK, MENU_STOCK = 0x800586D8, (0x3C10801E, 0x2610DA4E, 0x96020000, 0x00000000, 0x30420813)
CROSS_CONTEXT = (0x8005869C, (0x30420040, 0x80))   # stock or confirm-button (Square) word
NEXT_IN_GROUP, HAS_ITEM, EQUIP, CHOOSE, SOUND = 0x8004FD08, 0x8004FAC4, 0x8004FB28, 0x8004FB84, 0x8004A128
CALLEE_HEADS = {NEXT_IN_GROUP: 0x27BDFFE8, EQUIP: None, CHOOSE: None, HAS_ITEM: None, SOUND: 0x3C02801F}
CIRCLE = 0x20
GROUPS = tuple(range(1, 7)) + tuple(range(16, 20))

R = dict(zero=0, at=1, v0=2, a0=4, a1=5, t0=8, t1=9, t2=10, t3=11, t4=12, t5=13,
         s0=16, s1=17, s2=18, t9=25, sp=29, ra=31)


def _i(op, rs, rt, imm): return op << 26 | R[rs] << 21 | R[rt] << 16 | (imm & 0xFFFF)
def _r(fn, rs, rt, rd, sa=0): return R[rs] << 21 | R[rt] << 16 | R[rd] << 11 | sa << 6 | fn


def _hi_lo(v): lo = v & 0xFFFF; return ((v >> 16) + (lo >= 0x8000)) & 0xFFFF, lo


def _assemble(base, prog):
    """prog: list of words / ('label',) / (kind, ..., label) branch/jump tuples."""
    labels, pc = {}, base
    for x in prog:
        if isinstance(x, str): labels[x] = pc
        else: pc += 4
    out, pc = [], base
    for x in prog:
        if isinstance(x, str): continue
        if isinstance(x, tuple):
            k = x[0]
            if k in ('j', 'jal'):
                t = labels[x[1]] if isinstance(x[1], str) else x[1]
                x = (0x08000000 if k == 'j' else 0x0C000000) | (t >> 2 & 0x3FFFFFF)
            else:
                off = (labels[x[-1]] - pc - 4) >> 2
                op = dict(beq=4, bne=5, blez=6, bgtz=7)
                if k in op: x = _i(op[k], x[1], x[2] if len(x) == 4 else 'zero', off)
                elif k == 'bltz': x = _i(1, x[1], 'zero', off)
                elif k == 'bgez': x = 1 << 26 | R[x[1]] << 21 | 1 << 16 | (off & 0xFFFF)
                else: raise ValueError(k)
        out.append(x); pc += 4
    return out


NOP = 0
def addiu(rt, rs, v): return _i(9, rs, rt, v)
def sltiu(rt, rs, v): return _i(11, rs, rt, v)
def andi(rt, rs, v): return _i(12, rs, rt, v)
def lui(rt, v): return _i(15, 'zero', rt, v)
def lw(rt, v, rs): return _i(35, rs, rt, v)
def lh(rt, v, rs): return _i(33, rs, rt, v)
def lhu(rt, v, rs): return _i(37, rs, rt, v)
def lbu(rt, v, rs): return _i(36, rs, rt, v)
def sw(rt, v, rs): return _i(43, rs, rt, v)
def sb(rt, v, rs): return _i(40, rs, rt, v)
def addu(rd, rs, rt): return _r(0x21, rs, rt, rd)
def move(rd, rs): return addu(rd, rs, 'zero')
def sll(rd, rt, sa): return _r(0, 'zero', rt, rd, sa)
def jr(rs): return _r(8, rs, 'zero', 'zero')
def jalr(rs): return _r(9, rs, 'zero', 'ra')


def _tenth(dst, src):   # dst = 10 * src
    return [sll(dst, src, 2), addu(dst, dst, src), sll(dst, dst, 1)]


def _build(base, picks):
    ph, pl = _hi_lo(picks)
    best = [
        sltiu('t0', 'a0', 0x20), ('beq', 't0', 'zero', 'stock'), NOP,
        lui('t1', ph), addiu('t1', 't1', pl), addu('t1', 't1', 'a0'), lbu('t2', 0, 't1'), NOP,
        ('beq', 't2', 'zero', 'stock'), NOP, *_tenth('t3', 't2'),
        lui('t4', 0x800C), addu('t4', 't4', 't3'), lh('t4', -0x41B0, 't4'), NOP,
        ('bne', 't4', 'a0', 'stock'), lui('t5', 0x8012),
        lw('t5', -0x6514, 't5'), sll('t3', 't2', 2), addu('t5', 't5', 't3'), lh('t5', 2, 't5'), NOP,
        ('blez', 't5', 'stock'), NOP, jr('ra'), move('v0', 't2'),
        'stock', addiu('sp', 'sp', -0x18), ('j', BEST + 8), sw('ra', 0x10, 'sp')]
    circle = [
        'circle', lui('t0', 0x801E), lhu('t0', -0x25B2, 't0'), NOP, andi('t0', 't0', CIRCLE),
        ('beq', 't0', 'zero', 'out'), NOP,
        addiu('sp', 'sp', -0x20), sw('ra', 0x1C, 'sp'), sw('s1', 0x18, 'sp'), sw('s2', 0x14, 'sp'),
        lui('t0', 0x8015), lw('t0', 0x31F0, 't0'), NOP, sltiu('t1', 't0', 24),
        ('beq', 't1', 'zero', 'ret'), sll('t0', 't0', 2),
        lui('t1', 0x800C), addu('t1', 't1', 't0'), lw('s1', -0x42D0, 't1'), lw('t9', -0x4330, 't1'),
        addiu('t2', 'zero', -1), ('bne', 's1', 't2', 'have'), NOP, jalr('t9'), NOP, move('s1', 'v0'),
        'have', ('blez', 's1', 'ret'), NOP, ('jal', HAS_ITEM), move('a0', 's1'), ('blez', 'v0', 'ret'), NOP,
        *_tenth('t0', 's1'), lui('t1', 0x800C), addu('t1', 't1', 't0'), lh('s2', -0x41B0, 't1'), NOP,
        addiu('t0', 's2', -1), sltiu('t0', 't0', 6), ('bne', 't0', 'zero', 'ok'), addiu('t0', 's2', -16),
        sltiu('t0', 't0', 4), ('beq', 't0', 'zero', 'ret'), NOP,
        'ok', addiu('a0', 's1', 1), ('jal', NEXT_IN_GROUP), move('a1', 's2'), ('bgez', 'v0', 'got'), NOP,
        move('a0', 'zero'), ('jal', NEXT_IN_GROUP), move('a1', 's2'),
        'got', ('bltz', 'v0', 'ret'), NOP, ('beq', 'v0', 's1', 'ret'), NOP,
        lui('t1', ph), addiu('t1', 't1', pl), addu('t1', 't1', 's2'), sb('v0', 0, 't1'), move('s1', 'v0'),
        addiu('t0', 's2', -1), sltiu('t0', 't0', 6), ('beq', 't0', 'zero', 'magic'), NOP,
        ('jal', EQUIP), move('a0', 's2'), ('j', 'snd'), NOP,
        'magic', ('jal', CHOOSE), move('a0', 's1'),
        'snd', ('jal', SOUND), addiu('a0', 'zero', 1), lui('at', 0x8015), sw('zero', 0x31B4, 'at'),
        'ret', lw('ra', 0x1C, 'sp'), lw('s1', 0x18, 'sp'), lw('s2', 0x14, 'sp'), addiu('sp', 'sp', 0x20),
        'out', lui('s0', 0x801E), jr('ra'), addiu('s0', 's0', -0x25B2)]
    return _assemble(base, best + circle), best, circle


def _code_words(base):
    words, best, _ = _build(base, 0)
    picks = base + 4 * len(words)
    words, best, circle = _build(base, picks)
    n_best = len([x for x in best if not isinstance(x, str)])
    return words, base + 4 * n_best, picks


SIZE = 4 * len(_code_words(0x80010000)[0]) + 32


def _off(exe, address, size=4):
    load, length = struct.unpack_from('<II', exe, 0x18)
    if not load <= address <= load + length - size: raise ValueError(f'Magic & weapon swap: {address:08X} outside the executable')
    return 0x800 + address - load


def _words(exe, address, n): return struct.unpack_from(f'<{n}I', exe, _off(exe, address, 4 * n))


def validate(exe):
    if exe[:8] != b'PS-X EXE': raise ValueError('Magic & weapon swap needs a PS-X executable')
    if _words(exe, BEST, 4) != BEST_STOCK: raise ValueError('Magic & weapon swap: best_of_group 0x8004F810 differs')
    if _words(exe, MENU_HOOK, 5) != MENU_STOCK: raise ValueError('Magic & weapon swap: inventory menu input 0x800586D8 differs')
    a, (stock, square_lo) = CROSS_CONTEXT
    w = _words(exe, a, 1)[0]
    if w not in (stock, (stock & ~0xFFFF) | square_lo): raise ValueError('Magic & weapon swap: inventory menu confirm 0x8005869C differs')
    for f, head in CALLEE_HEADS.items():
        if head is not None and _words(exe, f, 1)[0] != head: raise ValueError(f'Magic & weapon swap: callee {f:08X} differs')
    if _words(exe, 0x800BBCD0 + 4 * 12, 4) != (0x8004FA44, 0x8004FA64, 0x8004FA84, 0x8004FAA4):
        raise ValueError('Magic & weapon swap: magic slot accessors differ')


class Block:
    length = SIZE
    def __call__(self, address):
        words = _code_words(address)[0]
        return struct.pack(f'<{len(words)}I', *words) + bytes(32)


def patch_hooks(exe, address):
    """exe: bytearray already validated; address: where Block was placed."""
    _, circle, picks = _code_words(address)
    struct.pack_into('<II', exe, _off(exe, BEST, 8), 0x08000000 | (address >> 2 & 0x3FFFFFF), 0)
    struct.pack_into('<I', exe, _off(exe, MENU_HOOK), 0x0C000000 | (circle >> 2 & 0x3FFFFFF))
    return {'feature': 'magic_weapon_swap', 'module': 'ALUN_CD.EXE', 'best_hook': hex(address),
            'circle_hook': hex(circle), 'picks': hex(picks),
            'sites': [dict(address=hex(BEST), stock='addiu sp,sp,-0x18; sw ra,0x10(sp) (best_of_group)', new='j best_hook; nop'),
                      dict(address=hex(MENU_HOOK), stock='lui s0,0x801E (inventory menu input)', new='jal circle_hook')]}
