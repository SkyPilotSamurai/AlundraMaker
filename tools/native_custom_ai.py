"""Custom enemy AI (Edit AI > Custom): compiled to the game's own event script
language as the enemy's C (tick) program, plus two small injected opcodes.

Native facts used (ALUN_CD.EXE, stock US):
* Event opcode handlers get a0 = logic entity, a2 -> current script pointer,
  a3 -> process state (result word at +0x2C) and return the opcode length.
* Entity PosX/PosY at +0x114/+0x118 (16.16 pixels); TargetDirection at +0x8C;
  player PosX/PosY at 0x801AC80C/0x801AC810 (opcode 0x27 Face the player).
* 0x09 n: TargetDirection = n (0 down, 8 left, 16 up, 24 right); 0x0A: turn around;
* 0x0B: set TargetAnimationId, wait until moved N pixels (native walking with
  collision); 0x0C: random cardinal TargetDirection; 0x27: face the player;
  0x1A: animation; 0x37: wait N frames; 0x8C: random byte < N -> result 0;
  0x62/0x63: set/clear entity flag bits on a selected entity (0x80 = self);
  0x10/0x11 lock/unlock player; 0x16/0x17 gravity on/off;
  0x8B: spawn a map template relative to a selected entity (0x80 = self).
* Branches: 02 jump, 03 jump if result != 0, 04 jump if result == 0.
Injected (private-state module, like E0-E8):
* E9 min max : result = 1 when Alundra is min..max tiles away (24x16 px tiles,
  larger of the two axes), else 0.
* EC n(u16) : velocity n*2 in the entity's TargetDirection (see emit_speed); EC 0 stops.
Nothing here is gameplay-verified yet."""
import struct
from event_logic_compile import _Assembler

OP_RANGE = 0xE9
OP_SPEED = 0xEC          # injected: EC n -> velocity n*2 (walk units) in the facing (emit_speed)
OP_TURN = 0x0A           # native: TargetDirection + 16 (turn around)
OP_HIT = 0xEE           # injected: apply this hit's damage (no stun), count it per slot
OP_HITS = 0xED          # injected: ED k n: k 0 hits (chance), 1 hits (after N), 2 damage >= n -> result 1 and clear; 3 clear all
HIT_TABLE_BYTES = 256   # 64 actor slots x (hits A, hits B, damage u16)
SIZES = {OP_RANGE: 3, OP_SPEED: 3, OP_HIT: 1, OP_HITS: 3}
CLASS_BITS = 0x0809          # EntityFlags ClassA | ClassB | ClassC: can be hit
SPEED_UNITS = 65536 / 1536   # EC units per pixel per 1/60 s: n*2*768/65536 px (observed 0x40 -> 1.5)
TILE_PIXELS = 20             # walking distance per tile (between 16 and 24)
MAX_SPEED = 0xFFFF           # EC speed is a u16 (2026-10-24)
MAX_LUNGE_TILES = 12
CHASE_STOP_TILES = 1          # chase stops when Alundra is within this many tiles (E9 0 n)
CHUNK_PIXELS = 8              # walk/chase pieces between death checks (~5 frames at walking speed)
CHECK_FRAMES = 8              # custom AI tests death / hurt at least every 8 frames
HURT_RESUME = 0x0B            # stock Red Reaper resumes when +0x1D0 falls to 0x0B (14 frames after a hit)
MAX_LUNGE_PX_PER_FRAME = 24   # BizHawk 2026-10-24: 24 px/frame still stops at a 1-tile pillar (487)
BUILD_WARNINGS = []           # read and cleared by mod_export.build_game


def emit_range():
    from project_state_runtime import _Mips
    m = _Mips()
    m.load(8, 6, 0)                      # t0 = script
    m.load(9, 8, 1, 36); m.load(10, 8, 2, 36)   # t1 = min, t2 = max
    def axis(own, player_lo, divisor, out):
        m.load(11, 4, own)               # t3 = entity pos
        m.i(15, 0, 12, 0x801B); m.load(12, 12, player_lo)   # t4 = player pos
        m.r(12, 11, 11, 0x23)            # t3 = t4 - t3
        m.r(0, 11, 11, 0, 16); m.words[-1] = (11 << 16) | (11 << 11) | (16 << 6) | 3   # sra t3,t3,16
        m.branch(1, 11, 1, 'pos' + str(out))  # bgez t3 (REGIMM rt=1)
        m.r(0, 11, 11, 0x23)             # t3 = 0 - t3
        m.label('pos' + str(out))
        m.i(9, 0, 13, divisor)           # t5 = divisor
        m.r(11, 13, 0, 0x1B)             # divu t3, t5
        m.words.append((out << 11) | 0x12)   # mflo out
        m.words.extend([0, 0])
    axis(0x114, -0x37F4 & 0xFFFF, 24, 14)    # t6 = |dx| tiles
    axis(0x118, -0x37F0 & 0xFFFF, 16, 15)    # t7 = |dy| tiles
    m.r(14, 15, 11, 0x2B)                # t3 = t6 < t7
    m.branch(4, 11, 0, 'max')            # beq t3,0 -> keep t6
    m.r(15, 0, 14, 0x21)                 # t6 = t7
    m.label('max')
    m.r(14, 9, 11, 0x2B)                 # t3 = dist < min
    m.branch(5, 11, 0, 'out')
    m.r(10, 14, 11, 0x2B)                # t3 = max < dist
    m.branch(5, 11, 0, 'out')
    m.i(9, 0, 11, 1); m.i(43, 7, 11, 0x2C); m.branch(4, 0, 0, 'ret')
    m.label('out'); m.i(43, 7, 0, 0x2C)
    m.label('ret'); m.i(9, 0, 2, 3); m.words.extend([0x03E00008, 0])
    return m.finish()


# Move route "Remove": native 2E with selector 0x80 (this character) calls the
# game's remove-entity routine 0x8003B0C8 (status 4, slot freed next frame).
# 19 only deactivates (status 3), which leaves the character on screen. 2E 80
# freeing a spawned blade was seen in BizHawk 2026-10-20
# (docs/2026-10-20-zorgia-projectile-lifecycle.txt, docs/2026-10-19-reaper-spawned-blade.txt).
REMOVE_SELF = bytes((0x2E, 0x80))


def emit_speed():
    # EC n: target velocity of this entity in its TargetDirection at speed n*2 (walk units).
    # Stock 0x80036E80 (ALUN_CD.EXE US) runs every frame: speed = halfword +8 of the animation
    # frame (+0x9C); only when it differs from +0xF4 or +0x8C differs from +0x94 does it rewrite
    # +0xBC/+0xC0 = table[dir] (0x80023654 / 0x80023694) * speed. The physics then moves the entity
    # toward that velocity with collision. EC writes that velocity to +0xBC/+0xC0, current +0xC4/+0xC8,
    # +0xDC/+0xE0 and the moved-this-frame +0xE4/+0xE8 (the collision loop 0x80038xxx), +0x94 = dir. Walk: 0x90 -> +0xBC -0x1B000 (BizHawk dump).
    # EC lo hi (2026-10-24): 16-bit speed, so a 12-tile lunge fits a ~10-frame swing window.
    return struct.pack('<33I', 0x8CC80000, 0, 0x91090001, 0x910B0002, 0x8C8A008C, 0x000B5A00, 0x012B4825, 0x00094840, 0x000A5040,
                       0x3C0B8002, 0x016A5821, 0x856C3654, 0x856D3694, 0x01890018, 0x00006012, 0, 0,
                       0x01A90018, 0x00006812, 0xAC8C00BC, 0xAC8D00C0, 0xAC8C00C4, 0xAC8D00C8, 0xAC8C00DC,
                       0xAC8D00E0, 0xAC8C00E4, 0xAC8D00E8, 0x8C8E008C, 0, 0xAC8E0094, 0x03E00008, 0x24020003, 0)


def _wait(asm, frames):
    frames = int(frames)
    check = getattr(asm, 'vital_check', None)   # death / hurt test between short waits (2026-10-24)
    if check and frames > 0:
        # 37 n lasts n+1 frames (one tick to resume; BizHawk 2026-10-25: 117 frames split in 8s started the
        # swing lunge 15 frames late). Keep the one-37 total of frames+1: chunks of CHECK_FRAMES frames each
        # (37 CHECK_FRAMES-1), never a 1-frame chunk (37 0).
        total = frames + 1
        while total > 0:
            c = min(CHECK_FRAMES, total)
            if total - c == 1: c -= 1
            asm.data.extend((0x37, c - 1)); total -= c
            if total > 0: check()
        return
    while frames > 0:
        n = min(255, frames); asm.data.extend((0x37, n)); frames -= n


def _walk(asm, animation, tiles):
    pixels = max(1, int(tiles) * TILE_PIXELS)
    check = getattr(asm, 'vital_check', None)
    while pixels > 0:   # with death checks: CHUNK_PIXELS at a time, so a death mid-walk is seen at once
        n = min(CHUNK_PIXELS if check else 0xFFFF, pixels); pixels -= n
        asm.data.extend((0x0B, animation)); asm.data.extend(struct.pack('<H', n))
        if check: check()


def _lunge(asm, animation, tiles, start, end, name, retarget=False, label=None):
    # Attack movement for animations without speed of their own (Red Reaper animation 3: 0B/1F
    # never ended, 65 went through walls; BizHawk 2026-10-22). 1A anim, wait to the swing, then
    # every script tick EC speed (velocity in the facing, moved by the native physics, so walls
    # stop it) and 37 01, then EC 0. start/end are animation frames (60 per second); 37 n waits n
    # of them, one loop pass (EC, 37 01, 74) takes 2 (BizHawk 2026-10-22). 'toward' re-faces Alundra every tick.
    pixels = max(1, int(tiles) * TILE_PIXELS)
    start = max(0, int(start)); end = max(start + 2, int(end))
    ticks = max(1, (end - start) // 2)
    per_frame = pixels / (ticks * 2)
    if per_frame > MAX_LUNGE_PX_PER_FRAME:
        BUILD_WARNINGS.append(f'{label or name}: lunge needs {per_frame:.1f} px/frame; capped at {MAX_LUNGE_PX_PER_FRAME} (collision limit), it covers {MAX_LUNGE_PX_PER_FRAME * ticks * 2 / TILE_PIXELS:.1f} tiles')
        per_frame = MAX_LUNGE_PX_PER_FRAME
    speed = min(MAX_SPEED, max(1, round(per_frame * SPEED_UNITS)))
    asm.data.extend((0x1A, animation)); _wait(asm, start)
    asm.data.extend((0x73, min(255, ticks))); asm.label(name)
    if retarget: asm.data.append(0x27)
    if getattr(asm, 'vital_check', None): asm.vital_check()
    asm.data.append(OP_SPEED); asm.data.extend(struct.pack('<H', speed)); asm.data.extend((0x37, 1)); asm.branch(0x74, name); asm.data.extend((OP_SPEED, 0, 0))
    return start + ticks * 2


def swing_frames(frames):
    """(first, last) animation frame (60/s) of the frames with an attack box, from the clip's
    frame list (collision_raw != 0). Stock Reaper animation 3: frames 11-13, 116..126; its hit
    landed ~117 frames in (BizHawk 2026-10-22). None when no frame has a box."""
    t = 0; hit = []
    for f in frames:
        if getattr(f, 'collision_raw', 0): hit.append((t, t + f.ticks))
        t += f.ticks
    return (hit[0][0], hit[-1][1]) if hit else None




def emit_hit(table):
    """EE: run from the enemy's own D (hit) program. Stock class D 8 (0x80080640) is damage
    0x8003ACAC + death flag +0x277 + hurt animation 4 + face away (the knockback is animation 4's
    speed). EE keeps only the damage and death flag, then adds the HP lost and one hit to this
    slot's (+0x000) counters at table."""
    from project_state_runtime import _Mips
    m = _Mips()
    m.i(9, 29, 29, -24); m.i(43, 29, 31, 20); m.i(43, 29, 16, 16); m.i(43, 29, 17, 12)
    m.r(4, 0, 16, 0x21)                       # s0 = a0
    m.load(17, 4, 0x14)                       # s1 = HP before
    m.words.extend([0x0C000000 | (0x8003ACAC >> 2) & 0x3FFFFFF, 0])   # jal damage(a0)
    m.branch(4, 2, 0, 'alive')                # v0 == 0: still alive
    m.i(9, 0, 8, 1); m.i(40, 16, 8, 0x277)   # sb 1, 0x277(s0)
    m.label('alive')
    m.load(9, 16, 0x14); m.r(17, 9, 9, 0x23)  # t1 = before - after
    m.branch(1, 9, 1, 'pos'); m.r(0, 0, 9, 0x21)  # bgez; else t1 = 0
    m.label('pos')
    m.load(10, 16, 0); m.r(0, 10, 10, 0, 2)  # t2 = slot * 4
    m.li(11, table); m.r(11, 10, 11, 0x21)
    for k in (0, 1):
        m.load(12, 11, k, 36); m.i(9, 12, 12, 1); m.i(11, 12, 13, 0x100)   # lbu, +1, sltiu
        m.branch(5, 13, 0, 'ok%d' % k); m.i(9, 0, 12, 0xFF)
        m.label('ok%d' % k); m.i(40, 11, 12, k)
    m.load(12, 11, 2, 37); m.r(12, 9, 12, 0x21); m.i(41, 11, 12, 2)       # damage += t1 (u16)
    m.load(31, 29, 20); m.load(16, 29, 16); m.load(17, 29, 12)
    m.i(9, 29, 29, 24); m.words.extend([0x03E00008, (9 << 26) | (2 << 16) | 1])   # jr ra; v0 = 1 (length)
    return m.finish()


def emit_hits(table):
    """ED k n (3 bytes): result = counter k of this slot >= n (k 0/1 hit counts, 2 damage), and
    that counter is cleared when it is; k 3 clears all three, result 0."""
    from project_state_runtime import _Mips
    m = _Mips()
    m.load(8, 6, 0); m.load(9, 8, 1, 36); m.load(10, 8, 2, 36)   # t1 = k, t2 = n
    m.load(11, 4, 0); m.r(0, 11, 11, 0, 2); m.li(12, table); m.r(12, 11, 12, 0x21)   # t4 = entry
    # k 4 (2026-10-24): result = death flag +0x277 set (native damage 0x8003ACAC on HP 0)
    m.i(9, 0, 13, 4); m.branch(5, 9, 13, 'not4')
    m.load(14, 4, 0x277, 36); m.r(0, 14, 15, 0x2B); m.i(43, 7, 15, 0x2C); m.branch(4, 0, 0, 'ret')
    m.label('not4')
    # k 5: result = hit-invulnerability counter +0x1D0 (0x19 on a hit, -1 per frame) > n
    m.i(9, 0, 13, 5); m.branch(5, 9, 13, 'not5')
    m.load(14, 4, 0x1D0, 37); m.r(10, 14, 15, 0x2B); m.i(43, 7, 15, 0x2C); m.branch(4, 0, 0, 'ret')
    m.label('not5')
    m.i(9, 0, 13, 3); m.branch(5, 9, 13, 'test')
    m.i(43, 12, 0, 0); m.i(43, 7, 0, 0x2C); m.branch(4, 0, 0, 'ret')
    m.label('test'); m.i(9, 0, 13, 2); m.branch(5, 9, 13, 'byte')
    m.load(14, 12, 2, 37); m.r(14, 10, 15, 0x2B); m.i(14, 15, 15, 1)   # t7 = !(t6 < n)
    m.i(43, 7, 15, 0x2C); m.branch(4, 15, 0, 'ret'); m.i(41, 12, 0, 2); m.branch(4, 0, 0, 'ret')
    m.label('byte'); m.r(12, 9, 12, 0x21); m.load(14, 12, 0, 36); m.r(14, 10, 15, 0x2B); m.i(14, 15, 15, 1)
    m.i(43, 7, 15, 0x2C); m.branch(4, 15, 0, 'ret'); m.i(40, 12, 0, 0)
    m.label('ret'); m.words.extend([0x03E00008, (9 << 26) | (2 << 16) | 3])
    return m.finish()


# Hurt animation each native class D program sets (+0x88) after the damage, then it faces away
# from Alundra (+0x8C): read from ALUN_CD.EXE's D table 0x800C719C (2026-10-25).
STUN_ANIMATIONS = {1: 5, 3: 9, 6: 6, 7: 7, 8: 4, 9: 2, 10: 6, 11: 4, 13: 3, 14: 5, 16: 8, 17: 8, 18: 2,
                   19: 8, 22: 6, 23: 5, 24: 7, 26: 8, 27: 6, 28: 7, 35: 6, 37: 1, 38: 2, 39: 3, 40: 2,
                   41: 3, 42: 1, 43: 6, 46: 3}


def hit_program(ai, stun_animation=None):
    """D (hit reaction) program: EE (damage, count), or None when neither 'No hit stun' nor a
    dart trigger is set (the class keeps its native D). With a dart trigger and 'No hit stun'
    unticked, the class's stun is kept after EE (user 2026-10-25: the Red Reaper lost its hit
    stun): its hurt animation (stun_animation) and facing away from Alundra (27, 0A)."""
    dart = ai.get('dart') or {}
    if not (ai.get('no_hit_stun') or dart.get('chance') or dart.get('after_hits') or dart.get('after_damage')):
        return None
    if not ai.get('no_hit_stun') and stun_animation is not None:
        return bytes((OP_HIT, 0x1A, int(stun_animation), 0x27, OP_TURN))
    return bytes((OP_HIT,))


# Stock death animation per class: the last animation between the death flag (+0x277) and removal,
# measured in BizHawk 2026-10-24 (stock AI, docs/2026-10-24-reaper-map-tests.txt). Classes not listed:
# unknown (no death animation by default). Not decoded statically from the class code.
STOCK_DEATH_ANIMATIONS = {
    'enemy:0072': 2,   # Red Reaper: 4 5 (hurt) 2
    'enemy:0045': 2,   # Zombie: 4 5 2
    'enemy:0004': 2,   # Gragg (Axe): 4 5 2
    'enemy:0074': 8,   # Green Shadow: 6 7 8
    'enemy:0038': 8,   # Shadow: 6 7 8
    'enemy:0012': 8,   # Lizardman (Sword): 7 8
    'enemy:0033': 7,   # Mummy: 5 6 7
}


def stock_death_animation(definition):
    """The class's stock death animation: measured ones by class id, else None (no death animation)."""
    return STOCK_DEATH_ANIMATIONS.get((definition or {}).get('id'))


def compile_custom_ai(ai, *, walk_animation, idle_animation, class_bits, spawn_templates=None, swings=None, owner=None, death_animation=None, vital=True, lengths=None, anim_sounds=None, stun_animation=None):
    # anim_sounds: {animation: its own start sound (anim set tail, 0 = none)} for an attack's Prepare sound
    # lengths: {animation: frames (60/s)} so whole-animation waits can be checked for death
    # vital=False: no death/hurt checks (unit tests of the movement byte layout only)
    """Return the C program bytes (no terminator: it loops forever).
    swings: {animation: (first, last)} attack-box frames (swing_frames), the default lunge window."""
    swings = swings or {}; lengths = lengths or {}; anim_sounds = anim_sounds or {}
    spawn_templates = spawn_templates or {}
    asm = _Assembler(); asm.label('start')
    route_first = bool(ai.get('route_before_attack'))
    route_list = list(ai.get('routes') or [])
    main_trig = (route_list[0].get('triggers') or {}).get('before_attack') if route_list else None
    if main_trig and main_trig.get('on') and main_trig.get('target') == '(any)' and int(main_trig.get('chance', 100)) >= 100:
        route_first = True   # Main route, before any attack, 100%: the original 'Always do before attack'

    routes = {r.get('name'): r.get('steps', []) for r in ai.get('routes') or []}
    hit_steps = routes.get(ai.get('on_hit_route')) if ai.get('on_hit_route') else None

    dart = ai.get('dart') or {}
    darting = bool(dart.get('chance') or dart.get('after_hits') or dart.get('after_damage'))

    native_stun = hit_program(ai) is None or (not ai.get('no_hit_stun') and stun_animation is not None)   # hurt animation + knockback (class D, or kept after EE)

    def vital_check():
        # The custom C replaces the class's C, which handled death and the end of the hurt stun:
        # without this the enemy stayed at HP 0 forever and its hurt pose stalled (2026-10-24).
        asm.data.extend((OP_HITS, 4, 0)); asm.branch(3, 'dead')
        if native_stun: asm.data.extend((OP_HITS, 5, HURT_RESUME)); asm.branch(3, 'hurt')
    if vital: asm.vital_check = vital_check

    def hit_check():
        if vital: vital_check()
        # native 71: Result = this enemy's hit counter (non-zero just after a hit)
        if hit_steps is not None:
            asm.data.append(0x71); asm.branch(3, 'on_hit')
        if darting:      # counters kept by EE in this enemy's D program (hit_program)
            k = asm.name()
            if dart.get('chance'):
                asm.data.extend((OP_HITS, 0, 1)); asm.branch(4, f'nd{k}')
                asm.data.extend((0x8C, min(255, round(int(dart['chance']) * 256 / 100)))); asm.branch(3, f'nd{k}')
                asm.branch(2, 'dart')
            asm.label(f'nd{k}')
            if dart.get('after_hits'): asm.data.extend((OP_HITS, 1, min(255, int(dart['after_hits'])))); asm.branch(3, 'dart')
            if dart.get('after_damage'): asm.data.extend((OP_HITS, 2, min(255, int(dart['after_damage'])))); asm.branch(3, 'dart')

    def route():
        steps = list((ai.get('routes') or [{}])[0].get('steps', ai.get('route') or []) if ai.get('routes') else (ai.get('route') or []))
        if ai.get('chase'):
            steps = [{'kind': 'chase', 'value': 1}] + steps
        if not steps:                                             # wander like the game's enemies
            steps = [{'kind': 'random', 'value': 1}, {'kind': 'wait', 'value': 30}]
        for st in steps:
            emit_step(st); hit_check()

    def emit_step(st):
        k = st['kind']; v = st.get('value', 1)
        if k in ('up', 'down', 'left', 'right'):
            asm.data.extend((0x09, {'down': 0, 'up': 16, 'left': 8, 'right': 24}[k])); _walk(asm, walk_animation, v)
        elif k == 'toward': asm.data.append(0x27); _walk(asm, walk_animation, v)
        elif k == 'chase':   # 27, 1A walk, 1F: ends when blocked (0B walking into a wall never ended, 2026-10-22)
            asm.data.extend((0x27, 0x1A, walk_animation)); px = max(1, int(v)) * TILE_PIXELS; ck = asm.name()
            while px > 0:   # 1F n: moved n px or blocked; in CHUNK_PIXELS pieces with death checks
                n = min(CHUNK_PIXELS if vital else 0xFFFF, px); px -= n
                # stop next to Alundra: the chase walked onto him (no body collision for e.g. the Red Reaper),
                # where the sword in front of him can't reach it (BizHawk 2026-10-24)
                if ai.get('stop_near_player'):   # option, off by default (user 2026-10-25)
                    asm.data.extend((OP_RANGE, 0, CHASE_STOP_TILES)); asm.branch(3, f'near{ck}')
                asm.data.append(0x1F); asm.data.extend(struct.pack('<H', n))
                if vital: vital_check()
                if px > 0: asm.data.append(0x27)
            asm.branch(2, f'chased{ck}'); asm.label(f'near{ck}'); asm.data.extend((0x1A, idle_animation)); asm.label(f'chased{ck}')
        elif k == 'away': asm.data.extend((0x27, OP_TURN)); _walk(asm, walk_animation, v)
        elif k == 'random': asm.data.append(0x0C); _walk(asm, walk_animation, v)
        elif k == 'face_player': asm.data.append(0x27)
        elif k == 'face': asm.data.extend((0x09, {'down': 0, 'up': 16, 'left': 8, 'right': 24}[v]))
        elif k == 'wait': _wait(asm, v)
        elif k == 'remove': asm.data.extend(REMOVE_SELF); asm.data.append(0xFF)
        elif k == 'animation': asm.data.extend((0x1A, int(v)))
        elif k == 'lock_player': asm.data.append(0x10)
        elif k == 'unlock_player': asm.data.append(0x11)
        elif k == 'gravity_on': asm.data.append(0x16)
        elif k == 'gravity_off': asm.data.append(0x17)
        elif k == 'hitbox_off': asm.data.extend((0x63, 0x80)); asm.data.extend(struct.pack('<H', class_bits or CLASS_BITS))
        elif k == 'hitbox_on': asm.data.extend((0x62, 0x80)); asm.data.extend(struct.pack('<H', class_bits or CLASS_BITS))
        elif k in ('invisible', 'visible'):
            raise ValueError('Go invisible / become visible: use a Change animation step to a vanish animation for now')
        else: raise ValueError(f'Unknown move route step {k}')

    def triggers(kind, match):
        # Routes set to run before/after an attack or animation (user 2026-10-27), each with a % roll
        for i, r in enumerate(route_list):
            t = (r.get('triggers') or {}).get(kind)
            if not (t and t.get('on')): continue
            if kind.endswith('_attack') and t.get('target') not in ('(any)', match): continue
            if kind.endswith('_anim') and (match is None or t.get('target') != match): continue
            if i == 0 and kind == 'before_attack' and route_first: continue   # already run before the checks
            k = asm.name(); chance = int(t.get('chance', 100))
            if chance < 100:
                asm.data.extend((0x8C, min(255, round(chance * 256 / 100)))); asm.branch(3, f'trig{k}')
            for st in r.get('steps', []): emit_step(st); hit_check()
            asm.label(f'trig{k}')

    hit_check()
    if route_first:
        route()          # 'Always do before attack': the whole route runs before every attack check
    attacks = list(ai.get('attacks') or [])
    for n, a in enumerate(attacks):
        skip = f'skip{n}'
        asm.data.extend((OP_RANGE, int(a['min_distance']), int(a['max_distance'])))
        asm.branch(4, skip)                                   # not in range
        asm.data.extend((0x8C, min(255, round(int(a['chance']) * 256 / 100))))
        asm.branch(3, skip)                                   # roll failed
        triggers('before_attack', a.get('name'))
        prep = a['prepare_animation'] if a.get('prepare_animation') is not None else (idle_animation if a.get('stall_before') else None)
        stall = int(a.get('stall_before', 0))
        if a.get('prepare_animation') is not None: triggers('before_anim', prep)
        if prep is not None: asm.data.extend((0x1A, prep))
        ps = a.get('prepare_sound')
        if ps is not None:   # independent of the Prepare animation (user 2026-10-25)
            # The animation's own sound is played by the animation update (0x800393A4 -> PlaySound
            # 0x8004A128) on the tick after 1A; no silent variant exists, so wait that tick and
            # Stop Sound (75) its id, then play the chosen sound (BD).
            from sound_database import encode_sound, encode_stop_sound
            own = anim_sounds.get(prep) if prep is not None else None
            if own:
                asm.data.extend((0x37, 0)); stall = max(0, stall - 1)
                asm.data.extend(encode_stop_sound(int(own)))
            if int(ps) >= 0: asm.data.extend(encode_sound(int(ps)))
        _wait(asm, stall)
        if a.get('prepare_animation') is not None: triggers('after_anim', prep)
        main_anim = a['animation'] if a.get('animation') is not None else (
            walk_animation if a.get('move_during', 'none') in ('toward', 'away', 'lock') and a.get('move_during_tiles') else None)
        triggers('before_anim', main_anim)
        mb = a.get('move_before', 'none')
        if mb in ('toward', 'away') and a.get('move_before_tiles'):
            asm.data.append(0x27)
            if mb == 'away': asm.data.append(OP_TURN)
            _walk(asm, walk_animation, a['move_before_tiles'])
        asm.data.append(0x27)                                 # face Alundra as the attack starts
        md = a.get('move_during', 'none'); frames = int(a.get('frames', 30))
        if a['type'] == 'spawned' and a.get('spawn_class') in spawn_templates:
            asm.data.extend((0x1A, a['animation']))
            at = min(frames, int(a.get('spawn_frame', 0))); _wait(asm, at)
            x, y, z = (int(a.get(k, 0)) for k in ('spawn_x', 'spawn_y', 'spawn_z'))
            asm.data.extend((0x8B, 0x80, spawn_templates[a['spawn_class']]))
            asm.data.extend(struct.pack('<hhh', x, y, z))
            if a.get('spawn_sound') is not None:   # the same sound command as the Play Sound event
                from sound_database import encode_sound
                asm.data.extend(encode_sound(int(a['spawn_sound'])))
            _wait(asm, frames - at)
        elif md in ('toward', 'away', 'lock') and a.get('move_during_tiles'):
            if md == 'away': asm.data.append(OP_TURN)
            tiles = min(MAX_LUNGE_TILES, int(a['move_during_tiles']))
            anim = a['animation'] if a.get('animation') is not None else walk_animation
            window = swings.get(anim) or (0, frames * 2)
            start = window[0] if a.get('move_from') is None else int(a['move_from'])
            end = window[1] if a.get('move_to') is None else int(a['move_to'])
            used = _lunge(asm, anim, tiles, start, end, f'lunge{n}', md == 'toward', label=f"{owner or 'Enemy'} attack '{a.get('name')}'")
            if a.get('whole_animation'):   # finish the animation (checked waits when its length is known)
                if vital and lengths.get(anim): _wait(asm, max(0, lengths[anim] - used))
                else: asm.data.extend((0x1C, 1))
                frames = 0
            else: _wait(asm, frames - used)
        elif a.get('whole_animation') and a.get('animation') is not None:
            # 1A anim, 1C 01: wait until the animation has played once, as the stock Reaper's slash
            # (176 frames, its hit ~117 frames in; cutting it at 'frames' skipped the hit, 2026-10-22)
            asm.data.extend((0x1A, a['animation']))
            if vital and lengths.get(a['animation']): _wait(asm, lengths[a['animation']])
            else: asm.data.extend((0x1C, 1))
            frames = 0
        else:
            if a.get('animation') is not None: asm.data.extend((0x1A, a['animation']))
            _wait(asm, frames)
        triggers('after_anim', main_anim)
        asm.data.extend((0x1A, idle_animation))
        triggers('after_attack', a.get('name'))
        cool = max(0, int(a.get('interval', 120)) - frames)   # cool down before the next choice
        if darting:          # a dart may cut the cool-down short: check every 10 frames
            while cool > 0: _wait(asm, min(10, cool)); cool -= 10; hit_check()
        else: _wait(asm, cool)
        if not (cool or frames or a.get('stall_before') or a.get('whole_animation')):
            _wait(asm, 1)    # never loop back without yielding a frame (see the end of the loop)
        asm.branch(2, 'start')
        asm.label(skip)
    if not route_first:
        route()
    # Every pass of the C loop must wait at least one frame: a chase/walk step that is blocked at
    # once (wall/hole toward Alundra) ends in the same tick, and with no attack in range the loop
    # spun forever inside one frame and froze the game (Red Reaper on map 489, 2026-10-24).
    _wait(asm, 1)
    asm.branch(2, 'start')
    if darting:
        # Dart away: clear the counters, face away from Alundra, then the same collision-respecting
        # velocity as the attack lunge (EC every 2 frames) for tiles at speed px/frame, EC 0.
        asm.label('dart'); asm.data.extend((OP_HITS, 3, 0, 0x27, OP_TURN, 0x1A, int(dart.get('animation', walk_animation))))
        pixels = max(1, int(dart.get('tiles', 3)) * TILE_PIXELS); pace = max(0.1, float(dart.get('speed', 4)))
        speed = min(MAX_SPEED, max(1, round(pace * SPEED_UNITS))); ticks = min(255, max(1, round(pixels / pace / 2)))
        asm.data.extend((0x73, ticks)); asm.label('dartloop')
        asm.data.append(OP_SPEED); asm.data.extend(struct.pack('<H', speed)); asm.data.extend((0x37, 1)); asm.branch(0x74, 'dartloop')
        asm.data.extend((OP_SPEED, 0, 0, 0x1A, idle_animation)); asm.branch(2, 'start')
    if hit_steps is not None:
        asm.label('on_hit')            # On hit: run that route once, then back to normal
        for st in hit_steps: emit_step(st)
        asm.branch(2, 'start')
    # Hurt (class D set the hurt animation and +0x1D0 = 0x19): stand still until +0x1D0 <= 0x0B, then
    # idle and restart the AI, as the stock Red Reaper does (BizHawk 2026-10-24: anim 4, 5, then 0
    # 14 frames after the hit). The 25-frame +0x1D0 invulnerability itself is the game's own.
    if vital and native_stun:
        asm.label('hurt'); asm.data.extend((OP_SPEED, 0, 0)); asm.label('hurtwait')
        asm.data.extend((0x37, 1, OP_HITS, 4, 0)); asm.branch(3, 'dead')
        asm.data.extend((OP_HITS, 5, HURT_RESUME)); asm.branch(3, 'hurtwait')
        asm.data.extend((0x1A, idle_animation)); asm.branch(2, 'start')
    # Dead (+0x277 set by the native damage at HP 0): stop, let the hurt pose finish, play the death
    # animation if the class has one, then remove this character (2E 80), as the stock C did (status 4).
    if not vital: return asm.finish()
    asm.label('dead'); asm.data.extend((OP_SPEED, 0, 0)); asm.label('deadwait')
    asm.data.append(0x37); asm.data.append(1)
    if native_stun: asm.data.extend((OP_HITS, 5, HURT_RESUME)); asm.branch(3, 'deadwait')
    if death_animation is not None: asm.data.extend((0x1A, int(death_animation), 0x1C, 1))
    asm.data.extend(REMOVE_SELF); asm.data.append(0xFF)
    return asm.finish()
