"""Custom consumable items: HP / MP effects and Revive (user 2026-10-27).

Stock US 1.1 ALUN_CD.EXE, static: Circle (0x8003514C) uses item id 31..50 through the start jump table
0x8002339C (index id - 31); the consumable cases are `jal use(a0 = id); j 0x80035268; v0 = 1`
(0x800351DC..). Wonder Essence's use 0x80034F90 shows the pieces: life +0x14 / max life +0x18 of
Alundra (slot 0 0x801AC6F8), magic now 0x8004F528 / max 0x8004F45C / set 0x8004F540 / add 0x8004F59C,
sound 0x8004A128 (3 = cannot, 0x30 / 0x31 = heal), remove one 0x8004FC80(id), has 0x8004FAC4(id).
Dying (0x80032F10): when the death animation ends, jal 0x8004FAC4(0x27) at 0x80032F24 and, if Alundra
has one, jal 0x80034F90(0x27) at 0x80032F34 (Wonder Essence revives him, else game over).

Injected (prepend block):
  use(a0 = id): the item's config (table by id - 31); nothing to heal -> sound 3; else HP (amount /
    part of max with a minimum / full) and MP (amount / full), sound 0x31, remove one; returns 1.
  case: the start-table entry of every custom item -> `jal use; move a0,s0; j 0x80035268; v0 = 1`.
  revive_has / revive_use replace the two dying calls: Wonder Essence first (stock), else the first
    custom item with Revive that Alundra has: its HP (full when it has none) and MP, sound 0x30,
    remove one (reviving costs the item).
Class data 'consume' = {'hp': 'none'|'amount'|'part'|'full', 'hp_value', 'hp_min', 'mp': 'none'|'amount'|'full',
'mp_value', 'revive': bool}; 'part' hp_value is the divisor 1/2/4/8/16."""
import struct
from magic_placement import (_assemble, addiu, andi, lui, lw, lh, lbu, lhu, sw, addu, sll, srl, sra, subu, slt, jr, or_, NOP, _hl)

START_TABLE, CASE_DONE = 0x8002339C, 0x80035268
PLAYER = 0x801AC6F8
MAGIC_NOW, MAGIC_MAX, MAGIC_SET, MAGIC_ADD = 0x8004F528, 0x8004F45C, 0x8004F540, 0x8004F59C
SOUND, TAKE, HAS = 0x8004A128, 0x8004FC80, 0x8004FAC4
REVIVE_HAS, REVIVE_USE, WONDER_USE = 0x80032F24, 0x80032F34, 0x80034F90
USABLE = range(31, 51)
HP_MODES, MP_MODES = ('none', 'amount', 'part', 'full'), ('none', 'amount', 'full')
SHIFT = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4}
ENTRY = 8   # flags (1 used, 2 revive), hp mode, hp value u16 (amount or shift), hp minimum u16, mp mode, mp value


def settings(definitions):
    """{item id: config} for custom consumable item classes; None when there are none."""
    out = {}
    for row in definitions:
        c = (row.get('data') or {}).get('consume')
        n = (row.get('source') or {}).get('item_id')
        if row.get('kind') != 'item' or row.get('clone_of') or not c:
            continue
        import magic_spawns
        if magic_spawns.behaves_like(row) != n:
            continue   # set to behave like a magic (Magic category): that takes its Circle case
        if n not in USABLE:
            raise ValueError(f"{row.get('name')}: only items 31-50 can be used with Circle")
        hp, mp = c.get('hp', 'none'), c.get('mp', 'none')
        if hp not in HP_MODES or mp not in MP_MODES:
            raise ValueError(f"{row.get('name')}: unknown HP / MP option")
        hv, hmin, mv = c.get('hp_value', 0), c.get('hp_min', 0), c.get('mp_value', 0)
        if hp == 'part' and hv not in SHIFT:
            raise ValueError(f"{row.get('name')}: HP part must be 1/1, 1/2, 1/4, 1/8 or 1/16")
        if any(type(v) is not int or not 0 <= v <= 999 for v in (hv, hmin, mv)):
            raise ValueError(f"{row.get('name')}: HP and MP values must be 0-999")
        if hp == 'none' and mp == 'none' and not c.get('revive'):
            continue
        out[n] = dict(hp=hp, hp_value=hv, hp_min=hmin, mp=mp, mp_value=mv, revive=bool(c.get('revive')))
    return out or None


def _program(table):
    th, tl = _hl(table); ph, pl = _hl(PLAYER)
    effect = [   # a0 = config entry, a1 = 1: no 'can it heal' check (revive); returns via 'eret'
    ]
    prog = [
        'case', ('jal', 'use'), addu('a0', 's0', 'zero'), ('j', CASE_DONE), addiu('v0', 'zero', 1),
        # use(a0 = id) -> 1
        'use',
        addiu('sp', 'sp', -32), sw('ra', 24, 'sp'), sw('s0', 16, 'sp'), sw('s1', 20, 'sp'),
        addu('s0', 'a0', 'zero'),
        lui('s1', th), addiu('s1', 's1', tl), addiu('t0', 'a0', -31), sll('t0', 't0', 3), addu('s1', 's1', 't0'),
        # can it heal? HP short (mode set) or MP short (mode set)
        lbu('t0', 1, 's1'), lui('t2', ph), addiu('t2', 't2', pl),
        ('beq', 't0', 'zero', 'trymp'), NOP,
        lw('t3', 0x14, 't2'), lw('t4', 0x18, 't2'), NOP, slt('t5', 't3', 't4'),
        ('bne', 't5', 'zero', 'apply'), NOP,
        'trymp',
        lbu('t0', 6, 's1'), NOP, ('beq', 't0', 'zero', 'cannot'), NOP,
        ('jal', MAGIC_NOW), NOP, sw('v0', 28, 'sp'),
        ('jal', MAGIC_MAX), NOP, lw('t3', 28, 'sp'), NOP, slt('t5', 't3', 'v0'),
        ('bne', 't5', 'zero', 'apply'), NOP,
        'cannot',
        ('jal', SOUND), addiu('a0', 'zero', 3),
        ('j', 'out'), NOP,
        'apply',
        ('jal', 'effect'), addu('a0', 's1', 'zero'),
        ('jal', SOUND), addiu('a0', 'zero', 0x31),
        ('jal', TAKE), addu('a0', 's0', 'zero'),
        'out',
        addiu('v0', 'zero', 1), lw('ra', 24, 'sp'), lw('s0', 16, 'sp'), lw('s1', 20, 'sp'), jr('ra'), addiu('sp', 'sp', 32),
        # effect(a0 = config entry): HP then MP
        'effect',
        addiu('sp', 'sp', -24), sw('ra', 16, 'sp'), sw('s0', 20, 'sp'), addu('s0', 'a0', 'zero'),
        lui('t2', ph), addiu('t2', 't2', pl),
        lbu('t0', 1, 's0'), lhu('t1', 2, 's0'), lw('t3', 0x14, 't2'), lw('t4', 0x18, 't2'),
        addiu('t5', 'zero', 3), ('beq', 't0', 't5', 'hpfull'), NOP,
        addiu('t5', 'zero', 1), ('beq', 't0', 't5', 'hpadd'), NOP,
        addiu('t5', 'zero', 2), ('bne', 't0', 't5', 'mp'), NOP,
        # part: max(minimum, max life >> shift)
        _srav('t1', 't4', 't1'), lhu('t5', 4, 's0'), NOP, slt('t6', 't1', 't5'),
        ('beq', 't6', 'zero', 'hpadd'), NOP, addu('t1', 't5', 'zero'),
        'hpadd',
        addu('t3', 't3', 't1'), slt('t6', 't4', 't3'), ('beq', 't6', 'zero', 'hpstore'), NOP,
        'hpfull',
        addu('t3', 't4', 'zero'),
        'hpstore',
        sw('t3', 0x14, 't2'),
        'mp',
        lbu('t0', 6, 's0'), lbu('a0', 7, 's0'), addiu('t5', 'zero', 1),
        ('beq', 't0', 't5', 'mpadd'), NOP,
        addiu('t5', 'zero', 2), ('bne', 't0', 't5', 'eret'), NOP,
        ('jal', MAGIC_MAX), NOP, ('jal', MAGIC_SET), addu('a0', 'v0', 'zero'),
        ('j', 'eret'), NOP,
        'mpadd',
        ('jal', MAGIC_ADD), NOP,
        'eret',
        lw('ra', 16, 'sp'), lw('s0', 20, 'sp'), jr('ra'), addiu('sp', 'sp', 24),
        # dying: does Alundra have Wonder Essence or a custom Revive item?
        'revive_has',
        addiu('sp', 'sp', -24), sw('ra', 16, 'sp'), sw('s0', 20, 'sp'),
        ('jal', HAS), addiu('a0', 'zero', 0x27),
        ('bne', 'v0', 'zero', 'hret'), NOP,
        ('jal', 'find_revive'), NOP,
        'hret',
        lw('ra', 16, 'sp'), lw('s0', 20, 'sp'), jr('ra'), addiu('sp', 'sp', 24),
        # find_revive -> v0 = custom Revive item id Alundra has, 0 none
        'find_revive',
        addiu('sp', 'sp', -24), sw('ra', 16, 'sp'), sw('s0', 20, 'sp'), addiu('s0', 'zero', 31),
        'floop',
        lui('t0', th), addiu('t0', 't0', tl), addiu('t1', 's0', -31), sll('t1', 't1', 3), addu('t0', 't0', 't1'),
        lbu('t1', 0, 't0'), NOP, andi('t1', 't1', 2), ('beq', 't1', 'zero', 'fnext'), NOP,
        ('jal', HAS), addu('a0', 's0', 'zero'),
        ('beq', 'v0', 'zero', 'fnext'), NOP,
        ('j', 'fret'), addu('v0', 's0', 'zero'),
        'fnext',
        addiu('s0', 's0', 1), addiu('t1', 'zero', 51), ('bne', 's0', 't1', 'floop'), NOP,
        addu('v0', 'zero', 'zero'),
        'fret',
        lw('ra', 16, 'sp'), lw('s0', 20, 'sp'), jr('ra'), addiu('sp', 'sp', 24),
        # dying: revive (Wonder Essence as the game, else the custom item; it is used up)
        'revive_use',
        addiu('sp', 'sp', -32), sw('ra', 24, 'sp'), sw('s0', 16, 'sp'), sw('s1', 20, 'sp'),
        ('jal', HAS), addiu('a0', 'zero', 0x27),
        ('beq', 'v0', 'zero', 'custom'), NOP,
        ('jal', WONDER_USE), addiu('a0', 'zero', 0x27),
        ('j', 'rret'), NOP,
        'custom',
        ('jal', 'find_revive'), NOP,
        ('beq', 'v0', 'zero', 'rret'), addu('s0', 'v0', 'zero'),
        lui('s1', th), addiu('s1', 's1', tl), addiu('t0', 's0', -31), sll('t0', 't0', 3), addu('s1', 's1', 't0'),
        lbu('t0', 1, 's1'), NOP, ('bne', 't0', 'zero', 'rheal'), NOP,
        lui('t2', ph), addiu('t2', 't2', pl), lw('t4', 0x18, 't2'), NOP, sw('t4', 0x14, 't2'),   # no HP option: full life
        'rheal',
        ('jal', 'effect'), addu('a0', 's1', 'zero'),
        ('jal', SOUND), addiu('a0', 'zero', 0x30),
        ('jal', TAKE), addu('a0', 's0', 'zero'),
        'rret',
        lw('ra', 24, 'sp'), lw('s0', 16, 'sp'), lw('s1', 20, 'sp'), jr('ra'), addiu('sp', 'sp', 32),
    ]
    return prog


def _srav(rd, rt, rs):   # rd = rt >> rs (arithmetic)
    from magic_placement import R
    return R[rs] << 21 | R[rt] << 16 | R[rd] << 11 | 7


def _words(base):
    n = len(_assemble(base, _program(base))[0])
    table = base + 4 * n
    words, labels = _assemble(base, _program(table))
    return words, labels, table


class Block:
    def __init__(self, chosen):
        self.chosen = chosen
        self.length = 4 * len(_words(0x80010000)[0]) + ENTRY * len(USABLE)
    def __call__(self, address):
        words, _, table = _words(address)
        raw = bytearray(struct.pack(f'<{len(words)}I', *words)); raw += bytes(self.length - len(raw))
        for n, c in self.chosen.items():
            o = table - address + ENTRY * (n - 31)
            hv = SHIFT[c['hp_value']] if c['hp'] == 'part' else c['hp_value']
            struct.pack_into('<BBHHBB', raw, o, 1 | (2 if c['revive'] else 0), HP_MODES.index(c['hp']), hv, c['hp_min'],
                             MP_MODES.index(c['mp']), min(c['mp_value'], 255))
        return bytes(raw)


def _off(exe, address):
    load, length = struct.unpack_from('<II', exe, 0x18)
    if not load <= address <= load + length - 4: raise ValueError(f'Custom consumables: {address:08X} outside the executable')
    return 0x800 + address - load


def validate(exe):
    jal = lambda t: 0x0C000000 | (t >> 2 & 0x3FFFFFF)
    if struct.unpack_from('<I', exe, _off(exe, REVIVE_HAS))[0] != jal(HAS) or struct.unpack_from('<I', exe, _off(exe, REVIVE_USE))[0] != jal(WONDER_USE):
        raise ValueError('Custom consumables: the dying code 0x80032F24 differs from the stock game')


def patch_hooks(exe, address, chosen):
    _, labels, _ = _words(address)
    jal = lambda t: 0x0C000000 | (t >> 2 & 0x3FFFFFF)
    for n in chosen:
        struct.pack_into('<I', exe, _off(exe, START_TABLE + 4 * (n - 31)), labels['case'])
    if any(c['revive'] for c in chosen.values()):
        struct.pack_into('<I', exe, _off(exe, REVIVE_HAS), jal(labels['revive_has']))
        struct.pack_into('<I', exe, _off(exe, REVIVE_USE), jal(labels['revive_use']))
    return {'feature': 'custom_consume', 'module': 'ALUN_CD.EXE', 'code': hex(address), 'items': sorted(chosen)}
