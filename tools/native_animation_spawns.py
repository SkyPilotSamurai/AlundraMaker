"""New attacks: spawn a class when an enemy/boss starts an animation.

Native facts (stock USA Rev1 ALUN_CD.EXE, docs/2026-10-05-native-animation-attack-routing.txt
and this module's disassembly checks):
* 800393A4 is the per-entity animation updater (s0 = entity). It reloads the
  animation when entity+88 (target animation) differs from entity+90 (current)
  or the direction set changed; both paths reach 80039408 with a2 = target and
  v0 = previous current animation (the current is only stored at 8003943C).
* 8003A860 spawns a class: a0 parent entity, a1 1 = map-local sprite bank,
  a2 sprite index (map-local index, without +100h), a3 X, stack+10 Y,
  stack+14 Z, stack+18 direction (16.16 positions). Located from its 49 call
  sites passing a1 = 1 and literal indexes that match the source review's
  SpawnWarpEntity calls (e.g. D8h in FunctionTypeA). It returns 0 when the
  map has no such sprite or no free slot, so a missing sprite never spawns.
* Entity fields (pinned source Entity.cs, offsets cross-checked with the
  updater): +68 class (sprite table index, map-local +100h), +8C target
  direction, +114/+118/+11C X/Y/Z.

Hook: the two instructions at 80039408 (sll v0,a2,3 / subu v0,v0,a2) become
jal wrapper / nop. The wrapper saves what the updater still needs, and when
the animation really changed (a2 != v0) walks the rule table: every rule whose
class and animation match spawns its class at the entity (+ offset in pixels)
facing the entity's direction. A guard word stops a spawned class's own rules
from spawning recursively. The wrapper then recomputes v0 = a2*7 and returns.

Rule table: 24-byte rows (u16 class 0-511, u16 animation, u16 spawned class
0-511, s16 dx, s16 dy, s16 dz pixels, u16 flags, u16 cooldown frames, u16 source
class (0 = the rule's class), u16 max at once (0 = no limit), u32 last spawn time,
u32 address of the list of actors this rule spawned, 0 without Max at once), ended by
FFFFh; after it, one list of `max at once` words per rule that has it. Static only; the timing and look of new attacks
needs testing in game.

Options (user 2026-10-26, Melzas's doubles):
* source class (Spawn from): the spawn comes from a live actor (status 2) of that class
  (such as Melzas's doubles) instead of the one whose animation started: the first one, or
  with flags bit 0 (Random) a random one; Random alone picks among the rule's own class.
  None alive -> from the one whose animation started.
* flags bit 1, use the map's template: the spawned class has custom behaviour (custom AI,
  lifetime). The export puts a dormant template of it on the map (enabled, not created at
  map load, C program = its custom AI); the rule spawns the last such record of the current
  map (records *0x801F2EC8, count *0x801F2ED4, 20 bytes: +4 enabled, +5 flags 0x80 local
  0x40 at load, +6 sprite, +12 C program) with 0x8003AAE8(parent, index, 1), as op 8B
  (0x80040E38) does, then sets its position and direction. No such record: the plain spawn.
* max at once (1-16): no spawn while that many of the actors this rule spawned are still
  alive (status 1-3, still the spawned class and still the parent (+0C) it was spawned
  from: a freed slot reused by something else, such as a projectile's own afterimages of
  the same class, does not count). The list holds (actor, parent) pairs. 0x8003A860 returns the new actor (v0 = s0, 0x8003A92C) or 0. The pick uses the game's
  random formula (seed 0x8009AF70 * 0x7D2B89DD + 0xE06A02E7, as inlined at 0x8003DAD4)
  without storing it, so the game's own random sequence is unchanged.
* cooldown: after a spawn, the rule does nothing for that many frames of play time
  (0x801D7CB4), so several actors starting the animation together give one spawn.
"""
import struct

HOOK = 0x80039408
HOOK_EXPECTED = (0x000610C0, 0x00461023)
SPAWN = 0x8003A860
SPAWN_PROLOGUE = (0x27BDFF98, 0xAFB40050, 0x0080A021, 0xAFB20048, 0x00A09021)
MINE = 16   # spawns a rule remembers for Max at once
ENTRY = struct.Struct('<HHHhhhHHHHHHHHII')   # ... despawn, slots, hp (0 = its own), chance, time, list
# Chance (user 2026-10-27): u16 at +26, 1-99 = percent of the animation starts that spawn (0 = always).
# Two steps of the game's random formula from its seed (not stored, so the game's own sequence is
# unchanged; two steps so it does not repeat the Random source pick's draw), r = hi(x * 100) in 0..99,
# no spawn when r >= chance. Checked before the cooldown, so a skipped start does not use it up.
# Despawn after (user 2026-10-26): a once-per-frame check in the entity update (0x8003BD14..: it
# runs on the scratchpad stack; its call of the animation-updater loop 0x80039724 at 0x8003BD1C)
# removes, with the game's own 0x8003B0C8 (op 2E), every actor a rule spawned whose play-time
# deadline passed. (0x800434BC and 0x8002C678 were tried first: neither runs every frame in a
# room, BizHawk 2026-10-26.)
TICK_SITE, TICK_CALL, TICK_TARGET, REMOVE = 0x8003BD1C, 0x0C00E5C9, 0x80039724, 0x8003B0C8
ACTORS, STRIDE, SLOTS = 0x801AC6F8, 0x294, 64
PLAY_TIME = 0x801D7CB4
SEED, MUL, ADD = 0x8009AF70, 0x7D2B89DD, 0xE06A02E7
TEMPLATES, TEMPLATE_COUNT, SPAWN_TEMPLATE = 0x801F2EC8, 0x801F2ED4, 0x8003AAE8
RECORD = 20
FRAME = 0x48


def _offset(exe, address):
    load = struct.unpack_from('<I', exe, 0x18)[0]
    return address - load + 0x800


def validate(exe):
    """Refuse to patch an executable whose hook or spawn routine differs from stock."""
    a = _offset(exe, HOOK)
    if struct.unpack_from('<2I', exe, a) != HOOK_EXPECTED:
        raise ValueError('Animation updater at 80039408 differs from the known native code')
    b = _offset(exe, SPAWN)
    if struct.unpack_from('<5I', exe, b) != SPAWN_PROLOGUE:
        raise ValueError('Spawn routine at 8003A860 differs from the known native code')


def check_rules(rules):
    rows = []
    for rule in rules:
        values = (rule['class'], rule['animation'], rule['spawn'], rule.get('dx', 0), rule.get('dy', 0), rule.get('dz', 0),
                  (1 if rule.get('from_random') else 0) | (2 if rule.get('template') else 0), rule.get('cooldown', 0) or 0, rule.get('from_class') or 0,
                  rule.get('max_alive', 0) or 0, rule.get('despawn', 0) or 0, rule.get('hp', 0) or 0,
                  rule.get('chance', 100) if rule.get('chance') is not None else 100)
        if any(type(v) is not int for v in values):
            raise ValueError('Spawn rule values must be whole numbers')
        owner, animation, spawn, dx, dy, dz, flags, cooldown, source, max_alive, despawn, hp, chance = values
        if not 1 <= chance <= 100:
            raise ValueError('Chance must be 1-100%')
        values = values[:12] + (0 if chance == 100 else chance,)
        if not 0 <= hp <= 9999:
            raise ValueError('Spawn HP must be 0-9999')
        if not 0 <= despawn <= 36000:
            raise ValueError('Despawn after must be 0-36000 frames')
        if not 0 <= max_alive <= MINE:
            raise ValueError('Max at once must be 0-%d' % MINE)
        if not 0 <= source < 512:
            raise ValueError('Source class must be 0-511')
        if not 0 <= owner < 512 or not 0 <= spawn < 512:
            raise ValueError('Spawn rule classes must be 0-511')
        if not 0 <= animation < 256:
            raise ValueError('Animation must be 0-255')
        if owner == spawn:
            raise ValueError('A class cannot spawn itself when its animation plays')
        if any(not -512 <= v <= 512 for v in (dx, dy, dz)):
            raise ValueError('Spawn offset must be within 512 pixels')
        if not 0 <= cooldown <= 3600:
            raise ValueError('Cooldown must be 0-3600 frames')
        rows.append(values)
    return rows


class _Asm:
    def __init__(self, base):
        self.base = base; self.words = []; self.labels = {}; self.fix = []

    def here(self):
        return self.base + 4 * len(self.words)

    def label(self, name):
        self.labels[name] = len(self.words)

    def r(self, funct, rs=0, rt=0, rd=0, shamt=0):
        self.words.append((rs << 21) | (rt << 16) | (rd << 11) | (shamt << 6) | funct)

    def i(self, op, rs, rt, imm):
        self.words.append((op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF))

    def branch(self, op, rs, rt, target):
        self.fix.append((len(self.words), target)); self.i(op, rs, rt, 0)

    def j(self, op, address):
        self.words.append((op << 26) | ((address >> 2) & 0x3FFFFFF))

    def li(self, reg, value):
        self.i(15, 0, reg, (value >> 16) & 0xFFFF); self.i(13, reg, reg, value & 0xFFFF)

    def nop(self):
        self.words.append(0)

    def finish(self):
        for index, target in self.fix:
            delta = self.labels[target] - index - 1
            self.words[index] |= delta & 0xFFFF
        return struct.pack(f'<{len(self.words)}I', *self.words)


# MIPS registers
ZERO, AT, V0, V1, A0, A1, A2, A3, T0, T1, T2, T3, T4, T5, T6, T7 = range(16)
S0, T8, T9, SP, RA = 16, 24, 25, 29, 31
SLL, SRL, SUBU, ADDU, JR, SLTU, MFHI, MFLO, MULTU = 0, 2, 0x23, 0x21, 8, 0x2B, 0x10, 0x12, 0x19
BEQ, BNE, ADDIU, ANDI, LUI, LW, LH, LHU, SW = 4, 5, 9, 12, 15, 35, 33, 37, 43


def _features(rows):
    """Only the options some rule uses."""
    features = {'max'} if any(r[9] or r[10] for r in rows) else set()
    features |= {'despawn'} if any(r[10] for r in rows) else set()
    features |= {'hp'} if any(r[11] for r in rows) else set()
    features |= {'cooldown'} if any(r[7] for r in rows) else set()
    features |= {'source'} if any(r[6] & 1 or r[8] for r in rows) else set()
    features |= {'template'} if any(r[6] & 2 for r in rows) else set()
    features |= {'chance'} if any(r[12] for r in rows) else set()
    return features


def emit(address, rules):
    """Wrapper + guard word + rule table placed at `address`."""
    rows = check_rules(rules)
    features = _features(rows)
    tick_words = len(_emit_tick(0)) // 4 if 'despawn' in features else 0
    code_words = len(_emit_code(address, 0, 0, features)) // 4 + tick_words
    guard = address + 4 * code_words
    code = _emit_code(address, guard, guard + 4, features)
    if tick_words:
        code += _emit_tick(guard + 4)
    lists = guard + 4 + ENTRY.size * len(rows) + 4   # after the FFFFh end (padded to a word)
    packed = []
    slots = [r[9] or (MINE if r[10] else 0) for r in rows]
    for row, n in zip(rows, slots):
        packed.append(ENTRY.pack(*row[:11], n, row[11], row[12], 0, lists if n else 0)); lists += 12 * n
    body = code + bytes(4) + b''.join(packed) + struct.pack('<HH', 0xFFFF, 0) + bytes(12 * sum(slots))
    return body + bytes((-len(body)) % 4)


def _emit_code(address, guard, table, features=('max', 'cooldown', 'source', 'template', 'chance')):
    a = _Asm(address)
    a.i(ADDIU, SP, SP, -FRAME)
    for reg, slot in ((RA, 0x40), (A0, 0x20), (A1, 0x24), (A2, 0x28), (A3, 0x2C), (V1, 0x30)):
        a.i(SW, SP, reg, slot)
    a.branch(BEQ, A2, V0, 'done'); a.nop()                     # same animation: direction change only
    a.li(T0, guard); a.i(LW, T0, T1, 0); a.nop()
    a.branch(BNE, T1, ZERO, 'done'); a.nop()                   # inside one of our own spawns
    a.li(T3, table)
    a.label('loop')
    a.i(LHU, T3, T4, 0); a.i(ADDIU, ZERO, T5, -1); a.i(ANDI, T5, T5, 0xFFFF)
    a.branch(BEQ, T4, T5, 'done'); a.nop()
    a.i(LW, S0, T2, 0x68); a.nop()
    a.branch(BNE, T4, T2, 'next'); a.nop()
    a.i(LHU, T3, T4, 2); a.i(LW, SP, A2, 0x28); a.nop()
    a.branch(BNE, T4, A2, 'next'); a.nop()
    if 'max' in features:
        # match. Max at once: skip while that many of the spawned class are alive
        a.i(LHU, T3, T4, 18); a.i(LHU, T3, T6, 4)
        a.branch(BEQ, T4, ZERO, 'chance'); a.nop()
        a.i(LW, T3, T0, 32); a.r(ADDU, rd=T1); a.i(LHU, T3, T9, 22)
        a.label('alive')
        a.i(LW, T0, T7, 0); a.nop()
        a.branch(BEQ, T7, ZERO, 'alive_next'); a.nop()
        a.i(LW, T7, T5, 0x10); a.nop(); a.i(ADDIU, T5, T5, -1)
        a.i(11, T5, T5, 3)                                          # sltiu t5, t5, 3: status 1..3
        a.branch(BEQ, T5, ZERO, 'alive_next'); a.nop()
        a.i(LW, T7, T5, 0x68); a.nop()
        a.branch(BNE, T5, T6, 'alive_next'); a.nop()
        a.i(LW, T7, T5, 0x0C); a.i(LW, T0, T8, 4); a.nop()
        a.branch(BNE, T5, T8, 'alive_next'); a.nop()
        a.i(ADDIU, T1, T1, 1)
        a.label('alive_next')
        a.i(ADDIU, T9, T9, -1)
        a.branch(BNE, T9, ZERO, 'alive'); a.i(ADDIU, T0, T0, 12)
        a.r(SLTU, rs=T1, rt=T4, rd=T5)
        a.branch(BEQ, T5, ZERO, 'next'); a.nop()                   # count >= max
    a.label('chance')
    if 'chance' in features:
        # Chance: no spawn on (100 - chance)% of the starts (two steps of the game's random formula)
        a.i(LHU, T3, T4, 26); a.nop()
        a.branch(BEQ, T4, ZERO, 'cooldown'); a.nop()
        a.li(T0, SEED); a.i(LW, T0, T5, 0); a.li(T6, MUL); a.li(T7, ADD)
        a.r(MULTU, rs=T5, rt=T6); a.r(MFLO, rd=T5); a.nop(); a.nop(); a.r(ADDU, rs=T5, rt=T7, rd=T5)
        a.r(MULTU, rs=T5, rt=T6); a.r(MFLO, rd=T5); a.nop(); a.nop(); a.r(ADDU, rs=T5, rt=T7, rd=T5)
        a.i(ADDIU, ZERO, T6, 100)
        a.r(MULTU, rs=T5, rt=T6); a.r(MFHI, rd=T5); a.nop(); a.nop()   # r = 0..99
        a.r(SLTU, rs=T5, rt=T4, rd=T5)
        a.branch(BEQ, T5, ZERO, 'next'); a.nop()                   # r >= chance: not this time
    a.label('cooldown')
    if 'cooldown' in features:
        # Cooldown: skip while fewer than `cooldown` frames passed since this rule's last spawn
        a.i(LHU, T3, T4, 14); a.nop()
        a.branch(BEQ, T4, ZERO, 'source'); a.nop()
        a.li(T0, PLAY_TIME); a.i(LW, T0, T5, 0); a.i(LW, T3, T6, 28); a.nop()
        a.r(SUBU, rs=T5, rt=T6, rd=T6); a.r(SLTU, rs=T6, rt=T4, rd=T6)
        a.branch(BNE, T6, ZERO, 'next'); a.nop()
        a.i(SW, T3, T5, 28)
    a.label('source')
    a.r(ADDU, rs=S0, rt=ZERO, rd=T7)                           # spawn from this entity...
    if 'source' in features:
        a.i(LHU, T3, T4, 12); a.i(LHU, T3, T8, 16); a.i(ANDI, T4, T4, 1)
        a.branch(BNE, T4, ZERO, 'pick'); a.nop()
        a.branch(BEQ, T8, ZERO, 'spawn'); a.nop()                  # not random, no source class: this entity
        a.label('pick')
        # ...or from a live actor of the source class (t8; 0 = this class, t2): random, or the first
        a.branch(BNE, T8, ZERO, 'have_source'); a.nop()
        a.r(ADDU, rs=T2, rt=ZERO, rd=T8)
        a.label('have_source')
        a.li(T0, ACTORS); a.r(ADDU, rd=T1); a.i(ADDIU, ZERO, T9, SLOTS)
        a.label('count')
        a.i(LW, T0, T5, 0x10); a.nop(); a.i(ADDIU, T5, T5, -2)
        a.branch(BNE, T5, ZERO, 'count_next'); a.nop()
        a.i(LW, T0, T5, 0x68); a.nop()
        a.branch(BNE, T5, T8, 'count_next'); a.nop()
        a.i(ADDIU, T1, T1, 1)
        a.label('count_next')
        a.i(ADDIU, T9, T9, -1)
        a.branch(BNE, T9, ZERO, 'count'); a.i(ADDIU, T0, T0, STRIDE)
        a.branch(BEQ, T1, ZERO, 'spawn'); a.nop()
        a.li(T0, SEED); a.i(LW, T0, T5, 0); a.li(T6, MUL)
        a.r(MULTU, rs=T5, rt=T6); a.r(MFLO, rd=T5); a.li(T6, ADD); a.r(ADDU, rs=T5, rt=T6, rd=T5)
        a.r(MULTU, rs=T5, rt=T1); a.r(MFHI, rd=T1); a.nop(); a.nop()   # index 0..count-1
        a.branch(BNE, T4, ZERO, 'chosen'); a.nop()
        a.r(ADDU, rd=T1)                                            # not random: the first one
        a.label('chosen')
        a.li(T0, ACTORS)
        a.label('find')
        a.i(LW, T0, T5, 0x10); a.nop(); a.i(ADDIU, T5, T5, -2)
        a.branch(BNE, T5, ZERO, 'find_next'); a.nop()
        a.i(LW, T0, T5, 0x68); a.nop()
        a.branch(BNE, T5, T8, 'find_next'); a.nop()
        a.branch(BEQ, T1, ZERO, 'found'); a.nop()
        a.i(ADDIU, T1, T1, -1)
        a.label('find_next')
        a.branch(BEQ, ZERO, ZERO, 'find'); a.i(ADDIU, T0, T0, STRIDE)
        a.label('found')
        a.r(ADDU, rs=T0, rt=ZERO, rd=T7)
    a.label('spawn')
    # spawn the rule's class at the chosen entity
    a.i(ADDIU, ZERO, T1, 1); a.li(T0, guard); a.i(SW, T0, T1, 0)
    a.i(SW, SP, T3, 0x34)
    if 'template' in features:
        # the map's template of the spawned class (custom behaviour), searched from the last record
        a.i(LHU, T3, T4, 12); a.nop(); a.i(ANDI, T4, T4, 2)
        a.branch(BEQ, T4, ZERO, 'plain'); a.nop()
        a.i(LHU, T3, T4, 4); a.nop(); a.i(ANDI, T5, T4, 0xFF); a.r(SRL, rt=T4, rd=T6, shamt=8)
        a.li(T0, TEMPLATES); a.i(LW, T0, T0, 0); a.li(T1, TEMPLATE_COUNT); a.i(LW, T1, T9, 0); a.nop()
        a.label('tsearch')
        a.branch(BEQ, T9, ZERO, 'plain'); a.i(ADDIU, T9, T9, -1)
        a.r(SLL, rt=T9, rd=T8, shamt=2); a.r(ADDU, rs=T8, rt=T9, rd=T8); a.r(SLL, rt=T8, rd=T8, shamt=2)
        a.r(ADDU, rs=T0, rt=T8, rd=T8)                               # record = base + index*20
        a.i(36, T8, T2, 4); a.nop(); a.branch(BEQ, T2, ZERO, 'tsearch'); a.nop()
        a.i(36, T8, T2, 6); a.nop(); a.branch(BNE, T2, T5, 'tsearch'); a.nop()
        a.i(36, T8, T2, 12); a.nop(); a.branch(BEQ, T2, ZERO, 'tsearch'); a.nop()
        a.i(36, T8, T2, 5); a.nop(); a.i(ANDI, T1, T2, 0x40)
        a.branch(BNE, T1, ZERO, 'tsearch'); a.nop()
        a.i(ANDI, T1, T2, 0x80); a.r(SRL, rt=T1, rd=T1, shamt=7)
        a.branch(BNE, T1, T6, 'tsearch'); a.nop()
        a.i(SW, SP, T7, 0x38)
        a.r(ADDU, rs=T7, rt=ZERO, rd=A0); a.r(ADDU, rs=T9, rt=ZERO, rd=A1)
        a.j(3, SPAWN_TEMPLATE); a.i(ADDIU, ZERO, A2, 1)
        a.i(LW, SP, T3, 0x34); a.i(LW, SP, T7, 0x38)
        a.branch(BEQ, V0, ZERO, 'spawned'); a.nop()
        for field, position in ((6, 0x114), (8, 0x118), (10, 0x11C)):
            a.i(LH, T3, T5, field); a.i(LW, T7, T6, position); a.r(SLL, rt=T5, rd=T5, shamt=16)
            a.r(ADDU, rs=T6, rt=T5, rd=T6); a.i(SW, V0, T6, position)
        a.i(LW, T7, T6, 0x8C); a.nop(); a.i(SW, V0, T6, 0x8C)
        a.branch(BEQ, ZERO, ZERO, 'spawned'); a.nop()
    a.label('plain')
    a.i(LHU, T3, T4, 4); a.nop(); a.r(SRL, rt=T4, rd=A1, shamt=8); a.i(ANDI, T4, A2, 0xFF)
    for field, position, slot in ((6, 0x114, None), (8, 0x118, 0x10), (10, 0x11C, 0x14)):
        a.i(LH, T3, T5, field); a.nop(); a.r(SLL, rt=T5, rd=T5, shamt=16)
        a.i(LW, T7, T6, position); a.nop(); a.r(ADDU, rs=T6, rt=T5, rd=A3 if slot is None else T6)
        if slot is not None:
            a.i(SW, SP, T6, slot)
    a.i(LW, T7, T6, 0x8C); a.nop(); a.i(SW, SP, T6, 0x18)
    a.j(3, SPAWN); a.r(ADDU, rs=T7, rt=ZERO, rd=A0)            # jal spawn ; move a0,t7
    a.i(LW, SP, T3, 0x34)
    a.label('spawned')
    a.li(T0, guard); a.i(SW, T0, ZERO, 0)
    if 'hp' in features:
        # Spawn HP: the new actor's hit points (+0x14), else the class's own
        a.i(LHU, T3, T4, 24); a.nop()
        a.branch(BEQ, T4, ZERO, 'hp_done'); a.nop()
        a.branch(BEQ, V0, ZERO, 'hp_done'); a.nop()
        a.i(SW, V0, T4, 0x14)
        a.label('hp_done')
    if 'max' in features:
        # Max at once: remember the new actor in a free (empty, dead or reused) place
        a.i(LHU, T3, T4, 22); a.i(LHU, T3, T6, 4)
        a.branch(BEQ, T4, ZERO, 'next'); a.nop()
        a.branch(BEQ, V0, ZERO, 'next'); a.nop()
        a.i(LW, T3, T0, 32); a.r(ADDU, rs=T4, rt=ZERO, rd=T9)
        a.label('keep')
        a.i(LW, T0, T7, 0); a.nop()
        a.branch(BEQ, T7, ZERO, 'store'); a.nop()
        a.i(LW, T7, T5, 0x10); a.nop(); a.i(ADDIU, T5, T5, -1)
        a.i(11, T5, T5, 3)
        a.branch(BEQ, T5, ZERO, 'store'); a.nop()
        a.i(LW, T7, T5, 0x68); a.nop()
        a.branch(BNE, T5, T6, 'store'); a.nop()
        a.i(LW, T7, T5, 0x0C); a.i(LW, T0, T8, 4); a.nop()
        a.branch(BNE, T5, T8, 'store'); a.nop()
        a.i(ADDIU, T9, T9, -1)
        a.branch(BNE, T9, ZERO, 'keep'); a.i(ADDIU, T0, T0, 12)
        a.branch(BEQ, ZERO, ZERO, 'next'); a.nop()                 # all alive (cannot happen: checked before)
        a.label('store')
        a.i(LW, V0, T5, 0x0C); a.i(SW, T0, V0, 0); a.i(SW, T0, T5, 4)   # the new actor and its parent
        a.i(LHU, T3, T4, 20); a.i(SW, T0, ZERO, 8)                       # its despawn deadline (0 = never)
        a.branch(BEQ, T4, ZERO, 'next'); a.nop()
        a.li(T5, PLAY_TIME); a.i(LW, T5, T5, 0); a.nop(); a.r(ADDU, rs=T5, rt=T4, rd=T5); a.i(SW, T0, T5, 8)
    a.label('next')
    a.branch(BEQ, ZERO, ZERO, 'loop'); a.i(ADDIU, T3, T3, ENTRY.size)
    a.label('done')
    for reg, slot in ((A0, 0x20), (A1, 0x24), (A2, 0x28), (A3, 0x2C), (V1, 0x30), (RA, 0x40)):
        a.i(LW, SP, reg, slot)
    a.nop()
    a.r(SLL, rt=A2, rd=V0, shamt=3); a.r(SUBU, rs=V0, rt=A2, rd=V0)   # the two replaced instructions
    a.r(JR, rs=RA); a.i(ADDIU, SP, SP, FRAME)
    return a.finish()


def _emit_tick(table):
    """Once per frame (called instead of 0x80039724 at 0x8003BD1C): run it, then remove
    every spawned actor whose despawn deadline passed (still alive, same class, same parent)."""
    a = _Asm(0)
    S1, S2, S3 = 17, 18, 19
    a.i(ADDIU, SP, SP, -0x28)
    for reg, slot in ((RA, 0x24), (S0, 0x10), (S1, 0x14), (S2, 0x18), (S3, 0x1C)):
        a.i(SW, SP, reg, slot)
    a.j(3, TICK_TARGET); a.nop()
    a.li(S1, table)
    a.label('rule')
    a.i(LHU, S1, T4, 0); a.i(ADDIU, ZERO, T5, -1); a.i(ANDI, T5, T5, 0xFFFF)
    a.branch(BEQ, T4, T5, 'end'); a.nop()
    a.i(LHU, S1, T4, 20); a.i(LW, S1, S2, 32)
    a.branch(BEQ, T4, ZERO, 'nextrule'); a.nop()
    a.branch(BEQ, S2, ZERO, 'nextrule'); a.nop()
    a.i(LHU, S1, S3, 22); a.nop()
    a.label('entry')
    a.branch(BEQ, S3, ZERO, 'nextrule'); a.i(ADDIU, S3, S3, -1)
    a.i(LW, S2, S0, 0); a.nop()
    a.branch(BEQ, S0, ZERO, 'nextentry'); a.nop()
    a.i(LW, S2, T5, 8); a.nop()
    a.branch(BEQ, T5, ZERO, 'nextentry'); a.nop()
    a.li(T6, PLAY_TIME); a.i(LW, T6, T6, 0); a.nop()
    a.r(SLTU, rs=T6, rt=T5, rd=T7)
    a.branch(BNE, T7, ZERO, 'nextentry'); a.nop()               # not yet
    a.i(SW, S2, ZERO, 0); a.i(SW, S2, ZERO, 8)                  # forget it either way
    a.i(LW, S0, T5, 0x10); a.nop(); a.i(ADDIU, T5, T5, -1)
    a.i(11, T5, T5, 3)                                          # status 1..3
    a.branch(BEQ, T5, ZERO, 'nextentry'); a.nop()
    a.i(LHU, S1, T6, 4); a.i(LW, S0, T5, 0x68); a.nop()
    a.branch(BNE, T5, T6, 'nextentry'); a.nop()                 # slot reused by another class
    a.i(LW, S0, T5, 0x0C); a.i(LW, S2, T6, 4); a.nop()
    a.branch(BNE, T5, T6, 'nextentry'); a.nop()
    a.j(3, REMOVE); a.r(ADDU, rs=S0, rt=ZERO, rd=A0)
    a.label('nextentry')
    a.branch(BEQ, ZERO, ZERO, 'entry'); a.i(ADDIU, S2, S2, 12)
    a.label('nextrule')
    a.branch(BEQ, ZERO, ZERO, 'rule'); a.i(ADDIU, S1, S1, ENTRY.size)
    a.label('end')
    for reg, slot in ((RA, 0x24), (S0, 0x10), (S1, 0x14), (S2, 0x18), (S3, 0x1C)):
        a.i(LW, SP, reg, slot)
    a.nop(); a.r(JR, rs=RA); a.i(ADDIU, SP, SP, 0x28)
    return a.finish()


def tick_address(address, rules):
    """Address of the once-per-frame despawn check inside the block at `address` (None: unused)."""
    rows = check_rules(rules)
    if not any(r[10] for r in rows):
        return None
    features = _features(rows)
    return address + len(_emit_code(address, 0, 0, features))


def patch_tick(exe, tick, offset_of):
    at = offset_of(exe, TICK_SITE)
    if struct.unpack_from('<I', exe, at)[0] != TICK_CALL:
        raise ValueError('Entity update call at 0x8003BD1C differs from the known native code')
    struct.pack_into('<I', exe, at, 0x0C000000 | ((tick >> 2) & 0x3FFFFFF))


class Block:
    """Position-dependent block for editor_qol's prepend allocator."""
    def __init__(self, rules):
        self.rules = check_rules(rules)
        self.length = len(emit(0x80010000, rules))
        self.source_rules = rules

    def __call__(self, address):
        return emit(address, self.source_rules)


def patch_hook(exe, wrapper_address, offset_of):
    at = offset_of(exe, HOOK)
    struct.pack_into('<2I', exe, at, 0x0C000000 | ((wrapper_address >> 2) & 0x3FFFFFF), 0)
    return dict(feature='animation_spawns', hook=hex(HOOK), wrapper=hex(wrapper_address))


def rules_from_database(document):
    """Rules from every class's 'spawn_attacks' list (classes resolved to catalogue ids)."""
    definitions = {d.get('id'): d for d in (document or {}).get('definitions', []) if isinstance(d, dict)}
    rules = []
    for d in definitions.values():
        for row in d.get('data', {}).get('spawn_attacks', []) or []:
            owner = d.get('source', {}).get('catalogue_index')
            target = definitions.get(row.get('class_id'), {}).get('source', {}).get('catalogue_index')
            if type(owner) is not int or type(target) is not int:
                continue
            source = definitions.get(row.get('from_class_id'), {}).get('source', {}).get('catalogue_index') or 0
            if row.get('source_animation') and source:
                # Spawn from a part with its own animation (user 2026-10-27): the part's animation and
                # frame start it and it spawns at that part (Random: at a random one of that class)
                owner, source = source, 0
            rules.append(dict(**{'class': owner}, animation=row.get('animation', 0), frame=row.get('frame', 0), spawn=target,
                              dx=row.get('dx', 0), dy=row.get('dy', 0), dz=row.get('dz', 0),
                              from_random=bool(row.get('from_random')), cooldown=row.get('cooldown', 0) or 0,
                              from_class=source,
                              max_alive=row.get('max_alive', 0) or 0, despawn=row.get('despawn', 0) or 0, hp=row.get('hp', 0) or 0, chance=row.get('chance', 100) or 100,
                              template=((definitions.get(row.get('class_id'), {}).get('data') or {}).get('custom_ai') or {}).get('mode') == 'custom'))
    return rules
