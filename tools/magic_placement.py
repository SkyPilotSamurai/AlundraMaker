"""Magic spawn placement (user 2026-10-26, docs/2026-10-26-magic-spawn-placement.txt).

Every magic spawn is jal 0x8003A860(a0 Alundra, a1 0, a2 class, a3 x, sp+0x10 y, sp+0x14 z,
sp+0x18 dir) (stock US 1.1, static). Each of the nine call sites is re-pointed at a 2-word stub
(j common; addiu t9,zero,site); common reads the site's two config bytes and, unless the mode is
0 (the magic's own placement), rewrites a3 / 0x10(sp) / 0x14(sp), then j 0x8003A860 (ra is the
magic's own return). Only caller-saved registers t0-t9 and hi/lo are used.
Modes: 1 from Alundra (his x, y, z: slot 0 0x801AC6F8 + 0x114/0x118/0x11C), 2 from above (Alundra's
x, y; z + 0x1000000 = 16 tiles, as Earth Book), 3 a point 0-10 tiles away: along Alundra's facing
(slot 0 + 0x8C), or a random direction and distance 0..n when random is set (own LCG in the block;
the game's RNG is not touched). Tile = 0x100000 (16 px in 16.16; tile index = pos >> 20).
Direction vectors are the game's s16[32] tables 0x80023654 / 0x80023694 (the player code scales
them by target_dir the same way); one tile = 1365 x the x value (768 * 1365 ~ 0x100000) and 2048 x the y value (512 * 2048),
measured in BizHawk 2026-10-27 (one scale for both made y 2/3 as far).
Enemy tracking 0-10 (2026-10-27): a site with tracking calls 0x8003A860 itself (ra saved in the
block) and records the new entity (pointer, serial at +4) in a 16-entry ring. item_tick 0x80036BB0
(lui v0,0x801F; lw v0,0x121C(v0) -> j track; nop; track replays both) moves each live one (same
serial, status +0x10 non-zero) toward the nearest slot 1-63 entity with status, life +0x14 and max
life +0x18 above 0, by at most n * 0x6000 a frame on x and y. The hook is before item_tick's
'item in use' check, so it runs every frame item_tick is called, also after the magic ends (BizHawk 2026-10-27).
Frames it lasts 0-9999 (0: its own): the same ring counts them down once a frame and removes the
entity with 0x8003B0C8 at 0. It can only shorten a spawn: one that ends on its own first is dropped.
Colour per item (2026-10-27): hue / saturation make recoloured copies of the spawned class's palettes
in spare palette slots 0x88-0x9F (VRAM x 256, y 0x1E8-0x1FF, empty in play in BizHawk); after the
spawn they are loaded with LoadImage 0x800877F8 and the entity's palette base (+0x1B4; global 0x60,
docs/2026-10-26-portrait-without-speaker.txt) is pointed at them, so the original class keeps its
colours everywhere else. Classes with more than 4 palettes, or no room left, keep their own colours.
Other graphics per item (2026-10-27): 'sprite' = a global class whose sprite record the spawn routine
looks up instead (its 0x8003A424 call at 0x8003A8B4 goes through 'lookup', which swaps a1 while our
spawn asks), so the entity is set up from that record (+0x64, size bytes, animations); its class
(+0x68: behaviour, balance / damage, 0x8003A5F8) is the spawned class. (Swapping +0x64 after the
spawn drew garbage in BizHawk: the animation state was set up from the old record.) After the spawn the
size / flag words +0x6C-0x84 are rebuilt from the class's own record as 0x8003A5F8 builds them, so it
moves as its class (BizHawk: the swapped record alone changed the fire's height by 18 px).
Class data 'magic_placement' = {site (str): {'mode', 'tiles', 'random', 'tracking', 'frames', 'hue', 'saturation', 'sprite'}}."""
import struct

SPAWN = 0x8003A860
SITES = (0x80035B84, 0x80035E0C, 0x80035FFC, 0x800362A0, 0x800363A4, 0x800364C0, 0x8003685C, 0x80036958, 0x80036AE4)
# magic_spawns class site (the a2 word) -> its spawn call
FOR_SPRITE = {0x80035B40: 0x80035B84, 0x80035E00: 0x80035E0C, 0x80035FF0: 0x80035FFC, 0x80036294: 0x800362A0,
              0x80036370: 0x800363A4, 0x800364B4: 0x800364C0, 0x80036860: 0x8003685C, 0x800368EC: 0x80036958,
              0x80036AD8: 0x80036AE4}
MODES = ('Magic default', 'From Alundra', 'From above', 'Point near Alundra')
DIR_X, DIR_Y, PLAYER = 0x80023654, 0x80023694, 0x801AC6F8
JAL = 0x0C000000 | (SPAWN >> 2 & 0x3FFFFFF)
R = {n: i for i, n in enumerate('zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split())}


def _i(op, rs, rt, imm): return op << 26 | R[rs] << 21 | R[rt] << 16 | (imm & 0xFFFF)
def _r(fn, rs, rt, rd, sa=0): return R[rs] << 21 | R[rt] << 16 | R[rd] << 11 | sa << 6 | fn
def addiu(rt, rs, v): return _i(9, rs, rt, v)
def andi(rt, rs, v): return _i(12, rs, rt, v)
def ori(rt, rs, v): return _i(13, rs, rt, v)
def lui(rt, v): return _i(15, 'zero', rt, v)
def lw(rt, v, rs): return _i(35, rs, rt, v)
def lh(rt, v, rs): return _i(33, rs, rt, v)
def lbu(rt, v, rs): return _i(36, rs, rt, v)
def sw(rt, v, rs): return _i(43, rs, rt, v)
def addu(rd, rs, rt): return _r(0x21, rs, rt, rd)
def sll(rd, rt, sa): return _r(0, 'zero', rt, rd, sa)
def srl(rd, rt, sa): return _r(2, 'zero', rt, rd, sa)
def mult(rs, rt): return _r(0x18, rs, rt, 'zero')
def mflo(rd): return _r(0x12, 'zero', 'zero', rd)
def subu(rd, rs, rt): return _r(0x23, rs, rt, rd)
def xor(rd, rs, rt): return _r(0x26, rs, rt, rd)
def slt(rd, rs, rt): return _r(0x2A, rs, rt, rd)
def sra(rd, rt, sa): return _r(3, 'zero', rt, rd, sa)
def jr(rs): return _r(8, rs, 'zero', 'zero')
def or_(rd, rs, rt): return _r(0x25, rs, rt, rd)
def lhu(rt, v, rs): return _i(37, rs, rt, v)
NOP = 0


def _hl(v):
    lo = v & 0xFFFF
    return ((v >> 16) + (lo >= 0x8000)) & 0xFFFF, lo


def _assemble(base, prog):
    labels, pc = {}, base
    for x in prog:
        if isinstance(x, str): labels[x] = pc
        else: pc += 4
    out, pc = [], base
    for x in prog:
        if isinstance(x, str): continue
        if isinstance(x, tuple):
            if x[0] in ('j', 'jal'):
                t = labels[x[1]] if isinstance(x[1], str) else x[1]
                x = (0x08000000 if x[0] == 'j' else 0x0C000000) | (t >> 2 & 0x3FFFFFF)
            elif x[0] == 'blez':
                x = _i(6, x[1], 'zero', (labels[x[2]] - pc - 4) >> 2)
            else:
                off = (labels[x[-1]] - pc - 4) >> 2
                x = _i(dict(beq=4, bne=5)[x[0]], x[1], x[2], off)
        out.append(x); pc += 4
    return out, labels


def _program(config, seed, data):
    ph, pl = _hl(PLAYER); ch, cl = _hl(config); sh, sl = _hl(seed); dh, dl = _hl(data); eh, el = _hl(PLAYER + 0x294); xh, xl = _hl(DIR_X); yh, yl = _hl(DIR_Y)
    prog = []
    for i in range(len(SITES)):
        prog += [f's{i}', ('j', 'common'), addiu('t9', 'zero', i)]
    prog += ['common',
        lui('t8', ch), addiu('t8', 't8', cl), sll('t9', 't9', 3), addu('t8', 't8', 't9'),
        lbu('t0', 0, 't8'), lbu('t1', 1, 't8'), lbu('v1', 2, 't8'),   # mode, tiles | random, tracking
        ('beq', 't0', 'zero', 'after'), NOP,
        lui('t2', ph), addiu('t2', 't2', pl),
        lw('t3', 0x114, 't2'), lw('t4', 0x118, 't2'), lw('t5', 0x11C, 't2'),
        addiu('t6', 'zero', 2), ('bne', 't0', 't6', 'notabove'), lui('t6', 0x100),
        addu('t5', 't5', 't6'),
        'notabove',
        addiu('t6', 'zero', 3), ('bne', 't0', 't6', 'store'), andi('t7', 't1', 0x7F),
        ('beq', 't7', 'zero', 'store'), sll('t7', 't7', 8),   # t7 = n tiles * 256
        andi('t6', 't1', 0x80), ('bne', 't6', 'zero', 'random'), NOP,
        lw('t6', 0x8C, 't2'), ('j', 'vector'), andi('t6', 't6', 0x1F),
        'random',
        lui('t9', sh), lw('t0', sl, 't9'), lui('t1', 0x41C6), ori('t1', 't1', 0x4E6D),
        mult('t0', 't1'), mflo('t0'), addiu('t0', 't0', 0x3039), sw('t0', sl, 't9'),
        srl('t6', 't0', 16), andi('t6', 't6', 0x1F),       # direction 0..31
        srl('t1', 't0', 8), andi('t1', 't1', 0xFF), addiu('t1', 't1', 1),
        mult('t7', 't1'), mflo('t7'), srl('t7', 't7', 8),  # distance 0..n tiles * 256
        'vector',
        sll('t6', 't6', 1), addiu('t1', 'zero', 1365),
        mult('t7', 't1'), mflo('t1'), NOP, NOP, srl('t1', 't1', 8),   # x scale: 768 * 1365 = one tile
        sll('t7', 't7', 3),                                            # y scale: 512 * 2048 = one tile
        lui('t0', xh), addu('t0', 't0', 't6'), lh('t0', xl, 't0'), NOP,
        mult('t0', 't1'), mflo('t0'), addu('t3', 't3', 't0'),
        lui('t0', yh), addu('t0', 't0', 't6'), lh('t0', yl, 't0'), NOP,
        mult('t0', 't7'), mflo('t0'), addu('t4', 't4', 't0'),
        'store',
        addu('a3', 't3', 'zero'), sw('t4', 0x10, 'sp'), sw('t5', 0x14, 'sp'),
        'after',
        lhu('t6', 4, 't8'), lbu('t5', 3, 't8'), lhu('t4', 6, 't8'),   # t6 = frames it lasts (0: its own), t5 = colour variant, t4 = sprite + 1
        or_('t7', 'v1', 't6'), or_('t7', 't7', 't5'), or_('t7', 't7', 't4'),
        ('beq', 't7', 'zero', 'go'), NOP,
        # tracking / length / colour: spawn, then use the entity
        lui('t9', dh), addiu('t9', 't9', dl),
        sw('ra', D_RA, 't9'), sw('v1', D_TRACK, 't9'), sw('t6', D_LIFE, 't9'), sw('t5', D_VAR, 't9'), sw('t4', D_SPR, 't9'),
        ('jal', SPAWN), NOP,
        lui('t9', dh), addiu('t9', 't9', dl),
        lw('t0', D_SPR, 't9'), sw('zero', D_SPR, 't9'),   # the graphics override ends with this spawn
        sw('v0', D_V0, 't9'),
        ('beq', 't0', 'zero', 'colour'), NOP,
        ('beq', 'v0', 'zero', 'colour'), NOP,
        # other graphics: size / flag bytes back from the class's own record (0x8003A424(0, class))
        lw('a1', 0x68, 'v0'), addu('a0', 'zero', 'zero'), addiu('a2', 't9', D_TMP), ('jal', SPRITE_RECORD), addiu('a3', 't9', D_TMP + 4),
        lui('t9', dh), addiu('t9', 't9', dl), lw('t1', D_V0, 't9'),
        ('beq', 'v0', 'zero', 'colour'), NOP,
        lhu('t2', 0x10, 'v0'), lbu('t3', 0x12, 'v0'), NOP, sll('t3', 't3', 16), or_('t2', 't2', 't3'), sw('t2', 0x6C, 't1'),
        lbu('t2', 0x13, 'v0'), lbu('t3', 0x14, 'v0'), sw('t2', 0x70, 't1'), sw('t3', 0x78, 't1'),
        lbu('t2', 0x15, 'v0'), lbu('t3', 0x16, 'v0'), sw('t2', 0x7C, 't1'), sw('t3', 0x80, 't1'),
        lbu('t2', 0x17, 'v0'), NOP, sw('t2', 0x84, 't1'),
        'colour',
        lw('v0', D_V0, 't9'), lw('t0', D_VAR, 't9'), NOP,
        ('beq', 'v0', 'zero', 'record'), NOP,
        ('beq', 't0', 'zero', 'record'), addiu('t0', 't0', -1),
        # colour variant: load its recoloured palette copies (LoadImage 0x800877F8) into the spare
        # palette slots and point the entity's palette base (+0x1B4) at them
        sll('t1', 't0', 7), sll('t2', 't0', 5), addu('t1', 't1', 't2'), sll('t2', 't0', 3), addu('t1', 't1', 't2'),   # t0 * 168
        addiu('t1', 't1', D_VARIANTS), addu('t1', 't1', 't9'),
        sw('t1', D_VPTR, 't9'), lw('t2', 4, 't1'), addiu('t3', 't1', 8),
        'pal',
        sw('t2', D_CNT, 't9'), sw('t3', D_PTR, 't9'),
        addu('a0', 't3', 'zero'), ('jal', LOADIMAGE), addiu('a1', 't3', 8),
        lui('t9', dh), addiu('t9', 't9', dl),
        lw('t3', D_PTR, 't9'), lw('t2', D_CNT, 't9'), addiu('t3', 't3', 40), addiu('t2', 't2', -1),
        ('bne', 't2', 'zero', 'pal'), NOP,
        lw('t1', D_VPTR, 't9'), lw('v0', D_V0, 't9'), lw('t1', 0, 't1'), NOP,
        sw('t1', 0x1B4, 'v0'),
        # tracking / length: remember it in a ring of 16 (pointer, serial, strength, frames left)
        'record',
        lw('ra', D_RA, 't9'), lw('v0', D_V0, 't9'), lw('t3', D_TRACK, 't9'), lw('t4', D_LIFE, 't9'), lw('t0', D_INDEX, 't9'),
        or_('t5', 't3', 't4'), ('beq', 't5', 'zero', 'ret'), NOP,
        ('beq', 'v0', 'zero', 'ret'), sll('t1', 't0', 4),
        addu('t1', 't1', 't9'),
        lw('t2', 4, 'v0'), NOP,
        sw('v0', D_RING, 't1'), sw('t2', D_RING + 4, 't1'), sw('t3', D_RING + 8, 't1'), sw('t4', D_RING + 12, 't1'),
        addiu('t0', 't0', 1), andi('t0', 't0', 15), sw('t0', D_INDEX, 't9'),
        'ret',
        jr('ra'), NOP,
        'go',
        ('j', SPAWN), NOP,
        # once a frame (item_tick 0x80036BB0, while a magic is in use)
        'track',
        lui('t0', dh), addiu('t0', 't0', dl), addiu('t0', 't0', D_RING), addiu('t1', 'zero', 16),
        'loop',
        lw('t2', 0, 't0'), NOP, ('beq', 't2', 'zero', 'next'), NOP,
        lw('t3', 4, 't2'), lw('t4', 4, 't0'), NOP, ('bne', 't3', 't4', 'drop'), NOP,
        lw('t3', 0x10, 't2'), NOP, ('beq', 't3', 'zero', 'drop'), NOP,
        # frames it lasts: count down, remove it (0x8003B0C8) at 0
        lw('t3', 12, 't0'), NOP, ('beq', 't3', 'zero', 'chase'), addiu('t3', 't3', -1),
        ('bne', 't3', 'zero', 'chase'), sw('t3', 12, 't0'),
        lui('t9', dh), addiu('t9', 't9', dl),
        sw('ra', D_TRA, 't9'), sw('t0', D_T0, 't9'), sw('t1', D_T1, 't9'),
        ('jal', REMOVE), addu('a0', 't2', 'zero'),
        lui('t9', dh), addiu('t9', 't9', dl),
        lw('ra', D_TRA, 't9'), lw('t0', D_T0, 't9'), lw('t1', D_T1, 't9'),
        ('j', 'drop'), NOP,
        # tracking: move toward the nearest live slot 1-63 entity with life, n * 0x6000 a frame on x and y
        'chase',
        lw('t3', 8, 't0'), NOP, ('beq', 't3', 'zero', 'next'), NOP,
        lui('t4', eh), addiu('t4', 't4', el), addiu('t5', 'zero', 63), lui('t6', 0x7FFF), ori('t6', 't6', 0xFFFF), addu('t7', 'zero', 'zero'),
        lw('a0', 0x114, 't2'), lw('a1', 0x118, 't2'),
        'scan',
        ('beq', 't4', 't2', 'snext'), NOP,
        lw('t8', 0x10, 't4'), NOP, ('beq', 't8', 'zero', 'snext'), NOP,
        lw('t8', 0x14, 't4'), NOP, ('blez', 't8', 'snext'), NOP,
        lw('t8', 0x18, 't4'), NOP, ('blez', 't8', 'snext'), NOP,
        lw('t8', 0x114, 't4'), lw('t9', 0x118, 't4'), subu('t8', 't8', 'a0'),
        sra('a2', 't8', 31), xor('t8', 't8', 'a2'), subu('t8', 't8', 'a2'),
        subu('t9', 't9', 'a1'), sra('a2', 't9', 31), xor('t9', 't9', 'a2'), subu('t9', 't9', 'a2'),
        addu('t8', 't8', 't9'), slt('a2', 't8', 't6'), ('beq', 'a2', 'zero', 'snext'), NOP,
        addu('t6', 't8', 'zero'), addu('t7', 't4', 'zero'),
        'snext',
        addiu('t5', 't5', -1), ('bne', 't5', 'zero', 'scan'), addiu('t4', 't4', 0x294),
        ('beq', 't7', 'zero', 'next'), NOP,
        sll('a3', 't3', 13), sll('a2', 't3', 14), addu('a3', 'a3', 'a2'),   # step = n * 0x6000
        subu('t9', 'zero', 'a3'),
        lw('t8', 0x114, 't7'), NOP, subu('t8', 't8', 'a0'),
        slt('a2', 'a3', 't8'), ('beq', 'a2', 'zero', 'xlo'), NOP, addu('t8', 'a3', 'zero'),
        'xlo', slt('a2', 't8', 't9'), ('beq', 'a2', 'zero', 'xok'), NOP, addu('t8', 't9', 'zero'),
        'xok', addu('a0', 'a0', 't8'), sw('a0', 0x114, 't2'),
        lw('t8', 0x118, 't7'), NOP, subu('t8', 't8', 'a1'),
        slt('a2', 'a3', 't8'), ('beq', 'a2', 'zero', 'ylo'), NOP, addu('t8', 'a3', 'zero'),
        'ylo', slt('a2', 't8', 't9'), ('beq', 'a2', 'zero', 'yok'), NOP, addu('t8', 't9', 'zero'),
        'yok', addu('a1', 'a1', 't8'), sw('a1', 0x118, 't2'),
        ('j', 'next'), NOP,
        'drop', sw('zero', 0, 't0'),
        'next',
        addiu('t1', 't1', -1), ('bne', 't1', 'zero', 'loop'), addiu('t0', 't0', 16),
        lui('v0', 0x801F), lw('v0', 0x121C, 'v0'), ('j', TICK + 8), NOP,
        # 0x8003A860's sprite record lookup (jal 0x8003A424 at 0x8003A8B4, t registers dead across it):
        # while a spawn of ours asks for other graphics, look up that sprite instead (a1 = index)
        'lookup',
        lui('t8', dh), addiu('t8', 't8', dl), lw('t8', D_SPR, 't8'), NOP,
        ('beq', 't8', 'zero', 'stock_lookup'), NOP,
        addiu('a1', 't8', -1),
        'stock_lookup',
        ('j', SPRITE_RECORD), NOP]
    return prog


# block data: wrapper ra, its tracking and length, ring index, tracker ra / t0 / t1, then the ring
D_RA, D_TRACK, D_LIFE, D_INDEX, D_TRA, D_T0, D_T1, D_V0, D_VAR, D_VPTR, D_CNT, D_PTR = 0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44
D_SPR, D_TMP = 48, 52   # sprite + 1 for this spawn; two scratch words for 0x8003A424
D_RING = 64
SPRITE_RECORD = 0x8003A424   # (is_map, index, &tpage, &clut) -> sprite record; global: table 0x801F3958
LOOKUP_CALL = 0x8003A8B4     # in 0x8003A860: jal 0x8003A424 (record for the entity's +0x64, size bytes, animations)
D_VARIANTS = D_RING + 16 * 16   # colour variants: base, count, 4 x (RECT x, y, w, h; 16 colours)
VARIANT_SIZE = 8 + 4 * 40
LOADIMAGE = 0x800877F8   # LoadImage(RECT *, data) - references its own "LoadImage" debug string
SPARE_SLOTS = range(0x88, 0xA0)   # palette slots (0x8012E2A0 index) empty in play: VRAM x 256, y 0x1E8-0x1FF (BizHawk 2026-10-27)
REMOVE = 0x8003B0C8   # remove an entity (status 4, no contents / break effect; remake player.remove_entity)
TICK, TICK_STOCK = 0x80036BB0, (0x3C02801F, 0x8C42121C)   # item_tick: lui v0,0x801F; lw v0,0x121C(v0)


def _words(base):
    n = len(_assemble(base, _program(base, base, base))[0])
    config = base + 4 * n; seed = config + 8 * len(SITES); data = seed + 4
    words, labels = _assemble(base, _program(config, seed, data))
    return words, labels, config, seed


DATA_SIZE = D_VARIANTS
SIZE = (lambda w: w[3] + 4 + DATA_SIZE - 0x80010000)(_words(0x80010000))


def settings(definitions):
    """{site: (mode, tiles, random, tracking, frames, hue, saturation, class)} from the magic item classes; None when nothing is changed."""
    out = {}
    for row in definitions:
        if row.get('kind') != 'item' or row.get('clone_of'):
            continue
        for key, value in ((row.get('data') or {}).get('magic_placement') or {}).items():
            site = int(key)
            if site not in SITES:
                raise ValueError(f"{row.get('name')}: unknown magic spawn call {key}")
            mode, tiles, rnd, track, life = value.get('mode', 0), value.get('tiles', 0), bool(value.get('random')), value.get('tracking', 0), value.get('frames', 0)
            hue, sat = value.get('hue', 0), value.get('saturation', 100)
            sprite = value.get('sprite')
            if sprite is not None and (type(sprite) is not int or not 0 <= sprite < 151):
                raise ValueError(f"{row.get('name')}: sprite must be a global class (0-150)")
            if type(hue) is not int or type(sat) is not int or not -180 <= hue <= 180 or not 0 <= sat <= 200:
                raise ValueError(f"{row.get('name')}: hue is -180 to 180, saturation 0 to 200")
            sprite_site = next(a for a, b in FOR_SPRITE.items() if b == site)
            import magic_spawns
            stock = next(st for item in magic_spawns.SITES.values() for a, st, _ in item if a == sprite_site)
            cls = magic_spawns.current(row, sprite_site, stock)
            if mode not in (0, 1, 2, 3) or type(tiles) is not int or not 0 <= tiles <= 10:
                raise ValueError(f"{row.get('name')}: spawn point must be 0-10 tiles")
            if type(track) is not int or not 0 <= track <= 10:
                raise ValueError(f"{row.get('name')}: enemy tracking must be 0-10")
            if type(life) is not int or not 0 <= life <= 9999:
                raise ValueError(f"{row.get('name')}: frames must be 0-9999")
            v = (mode, tiles, rnd, track, life, hue, sat, cls, sprite)
            if out.get(site, v) != v:
                raise ValueError(f"{row.get('name')}: shares its magic with another item; give both the same placement")
            out[site] = v
    return out if any(m or t or f or (h, sa) != (0, 100) or sp is not None for m, _, _, t, f, h, sa, _, sp in out.values()) else None


def _off(exe, address):
    load, length = struct.unpack_from('<II', exe, 0x18)
    if not load <= address <= load + length - 4: raise ValueError(f'Magic placement: {address:08X} outside the executable')
    return 0x800 + address - load


def validate(exe):
    for site in SITES:
        if struct.unpack_from('<I', exe, _off(exe, site))[0] != JAL:
            raise ValueError(f'Magic placement: spawn call {site:08X} differs from the stock game')
    if struct.unpack_from('<I', exe, _off(exe, LOOKUP_CALL))[0] != 0x0C000000 | (SPRITE_RECORD >> 2 & 0x3FFFFFF):
        raise ValueError('Magic placement: sprite lookup call 0x8003A8B4 differs from the stock game')
    if struct.unpack_from('<II', exe, _off(exe, TICK)) != TICK_STOCK:
        raise ValueError('Magic placement: item_tick 0x80036BB0 differs from the stock game')


def variants(chosen, datas):
    """Colour variants {(class, hue, sat): (base, [(slot, palette words)])}: each recoloured copy of a
    class's palettes goes to spare slots base + palette (the entity adds its palette base to each
    piece's palette number); variants never share a slot."""
    from global_sprite_recolor import palettes_of, _bank
    from local_sprite_recolor import shift_hue
    bank = _bank(datas); table = bank.start + bank.header[5]; out = {}; taken = set()
    for site in SITES:
        v = chosen.get(site)
        if not v or (v[5], v[6]) == (0, 100) or (v[7], v[5], v[6]) in out: continue
        cls, hue, sat = v[7], v[5], v[6]
        used = sorted(palettes_of(datas, cls))
        if not used or len(used) > 4: continue   # (more than 4 palettes: left in its own colours)
        base = next((b for b in range(SPARE_SLOTS[0] - used[0], SPARE_SLOTS[-1] - used[-1] + 1)
                     if all(b + q in SPARE_SLOTS and b + q not in taken for q in used)), None)
        if base is None: continue   # no room: left in its own colours
        taken |= {base + q for q in used}
        out[(cls, hue, sat)] = (base, [(base + q, shift_hue(list(struct.unpack_from('<16H', datas, table + 32 * q)), hue, sat)) for q in used])
    return out


class Block:
    def __init__(self, chosen, datas=None):
        self.chosen = chosen; self.variants = variants(chosen, datas) if datas is not None else {}
        self.length = SIZE + VARIANT_SIZE * len(self.variants)
    def __call__(self, address):
        words, _, config, seed = _words(address)
        raw = bytearray(struct.pack(f'<{len(words)}I', *words)); raw += bytes(self.length - len(raw))
        keys = list(self.variants)
        data = seed + 4 - address
        for k, key in enumerate(keys):
            base, copies = self.variants[key]; o = data + D_VARIANTS + VARIANT_SIZE * k
            struct.pack_into('<II', raw, o, base, len(copies))
            for j, (slot, colours) in enumerate(copies):
                struct.pack_into('<4H16H', raw, o + 8 + 40 * j, (slot // 32) * 64, 0x1E0 + slot % 32, 16, 1, *colours)
        for i, site in enumerate(SITES):
            mode, tiles, rnd, track, life, hue, sat, cls, sprite = self.chosen.get(site, (0, 0, False, 0, 0, 0, 100, 0, None))
            o = config - address + 8 * i
            raw[o] = mode; raw[o + 1] = tiles | (0x80 if rnd else 0); raw[o + 2] = track
            raw[o + 3] = keys.index((cls, hue, sat)) + 1 if (cls, hue, sat) in self.variants else 0
            struct.pack_into('<HH', raw, o + 4, life, 0 if sprite is None else sprite + 1)
        struct.pack_into('<I', raw, seed - address, 0x2545F491)
        return bytes(raw)


def patch_hooks(exe, address):
    """exe: validated bytearray; address: where Block was placed."""
    labels = _words(address)[1]
    for i, site in enumerate(SITES):
        struct.pack_into('<I', exe, _off(exe, site), 0x0C000000 | (labels[f's{i}'] >> 2 & 0x3FFFFFF))
    struct.pack_into('<II', exe, _off(exe, TICK), 0x08000000 | (labels['track'] >> 2 & 0x3FFFFFF), 0)
    struct.pack_into('<I', exe, _off(exe, LOOKUP_CALL), 0x0C000000 | (labels['lookup'] >> 2 & 0x3FFFFFF))
    return {'feature': 'magic_placement', 'module': 'ALUN_CD.EXE', 'code': hex(address),
            'sites': [hex(s) for s in SITES], 'stock': 'jal 0x8003A860', 'new': 'jal stub (j common; addiu t9,zero,site)'}
