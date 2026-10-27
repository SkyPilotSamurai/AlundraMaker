"""New attacks on a chosen frame: spawn a class when an enemy/boss shows
frame N (N >= 1) of one of its animations. Frame 0 rules stay with
native_animation_spawns (animation start).

Native facts (stock USA Rev1 ALUN_CD.EXE, 800393A4 per-entity animation updater,
disassembled 2026-10-18):
* entity+A0 = start of the current animation's frame records, entity+A4 = the
  record about to be shown, entity+90 = current animation, entity+68 = class.
* Frame records are 5 bytes each, contiguous (first byte has bit 80h; byte 0/1
  end or loop the animation, which resets +A4 to +A0). So the record at s1 is
  frame (s1 - [entity+A0]) / 5.
* 800394F4 (lw v0,A4(s0)) / 800394F8 (andi v1,v1,7Fh) run exactly once per
  new frame shown, for every frame including frame 0, with s0 = entity and
  s1 = that frame's record; neither is a branch delay slot.

Hook: those two instructions become jal wrapper / nop. The wrapper walks the
rule table and, for each rule whose class, current animation and frame match,
spawns its class at the entity (+ offset in pixels) facing the entity's
direction (8003A860, as native_animation_spawns). A looping animation spawns
again each time the frame comes round. Then it redoes the two instructions.

Rule table: 14-byte rows (u16 class, u16 animation, u16 frame, u16 spawned
class, s16 dx, dy, dz pixels), ended by FFFFh. Static only; timing needs
testing in game.
"""
import struct
from native_animation_spawns import _Asm, _offset, SPAWN, SPAWN_PROLOGUE
from native_animation_spawns import (ZERO, V0, V1, A0, A1, A2, A3, T0, T1, T2, T3, T4, T5, T6, T7,
                                     S0, SP, RA, SLL, SRL, SUBU, ADDU, JR, BEQ, BNE, ADDIU, ANDI, LW, LH, LHU, SW)
S1, T8 = 17, 24
HOOK = 0x800394F4
HOOK_EXPECTED = (0x8E0200A4, 0x3063007F)
ENTRY = struct.Struct('<HHHHhhh')
FRAME = 0x48
CODE_WORDS = 87


def validate(exe):
    a = _offset(exe, HOOK)
    if struct.unpack_from('<2I', exe, a) != HOOK_EXPECTED:
        raise ValueError('Animation frame step at 800394F4 differs from the known native code')
    b = _offset(exe, SPAWN)
    if struct.unpack_from('<5I', exe, b) != SPAWN_PROLOGUE:
        raise ValueError('Spawn routine at 8003A860 differs from the known native code')


def check_rules(rules):
    rows = []
    for rule in rules:
        values = (rule['class'], rule['animation'], rule.get('frame', 0), rule['spawn'],
                  rule.get('dx', 0), rule.get('dy', 0), rule.get('dz', 0))
        if any(type(v) is not int for v in values):
            raise ValueError('Spawn rule values must be whole numbers')
        owner, animation, frame, spawn, dx, dy, dz = values
        if not 0 <= owner < 512 or not 0 <= spawn < 512:
            raise ValueError('Spawn rule classes must be 0-511')
        if not 0 <= animation < 256:
            raise ValueError('Animation must be 0-255')
        if not 1 <= frame < 256:
            raise ValueError('Frame must be 1-255 (frame 0 is the animation start)')
        if owner == spawn:
            raise ValueError('A class cannot spawn itself when its animation plays')
        if any(not -512 <= v <= 512 for v in (dx, dy, dz)):
            raise ValueError('Spawn offset must be within 512 pixels')
        rows.append(values)
    return rows


def emit(address, rules):
    rows = check_rules(rules)
    guard = address + 4 * CODE_WORDS
    table = guard + 4
    a = _Asm(address)
    a.i(ADDIU, SP, SP, -FRAME)
    for reg, slot in ((RA, 0x40), (A0, 0x20), (A1, 0x24), (A2, 0x28), (A3, 0x2C), (V1, 0x30)):
        a.i(SW, SP, reg, slot)
    a.li(T0, guard); a.i(LW, T0, T1, 0); a.nop()
    a.branch(BNE, T1, ZERO, 'done'); a.nop()                   # inside one of our own spawns
    a.i(LW, S0, T7, 0xA0); a.nop(); a.r(SUBU, rs=S1, rt=T7, rd=T7)   # byte offset of this frame
    a.i(LW, S0, T8, 0x90)                                      # current animation
    a.i(SW, SP, T7, 0x38); a.i(SW, SP, T8, 0x3C)
    a.li(T3, table)
    a.label('loop')
    a.i(LHU, T3, T4, 0); a.i(ADDIU, ZERO, T5, -1); a.i(ANDI, T5, T5, 0xFFFF)
    a.branch(BEQ, T4, T5, 'done'); a.nop()
    a.i(LW, S0, T2, 0x68); a.nop()
    a.branch(BNE, T4, T2, 'next'); a.nop()
    a.i(LHU, T3, T4, 2); a.i(LW, SP, T8, 0x3C); a.nop()
    a.branch(BNE, T4, T8, 'next'); a.nop()
    a.i(LHU, T3, T4, 4); a.i(LW, SP, T7, 0x38)
    a.r(SLL, rt=T4, rd=T5, shamt=2); a.r(ADDU, rs=T5, rt=T4, rd=T5)   # frame * 5
    a.branch(BNE, T5, T7, 'next'); a.nop()
    a.i(ADDIU, ZERO, T1, 1); a.li(T0, guard); a.i(SW, T0, T1, 0)
    a.i(SW, SP, T3, 0x34)
    a.i(LHU, T3, T4, 6); a.r(SRL, rt=T4, rd=A1, shamt=8); a.i(ANDI, T4, A2, 0xFF)
    for field, position, slot in ((8, 0x114, None), (10, 0x118, 0x10), (12, 0x11C, 0x14)):
        a.i(LH, T3, T5, field); a.r(SLL, rt=T5, rd=T5, shamt=16)
        a.i(LW, S0, T6, position); a.nop(); a.r(ADDU, rs=T6, rt=T5, rd=A3 if slot is None else T6)
        if slot is not None:
            a.i(SW, SP, T6, slot)
    a.i(LW, S0, T6, 0x8C); a.nop(); a.i(SW, SP, T6, 0x18)
    a.j(3, SPAWN); a.r(ADDU, rs=S0, rt=ZERO, rd=A0)
    a.i(LW, SP, T3, 0x34); a.li(T0, guard); a.i(SW, T0, ZERO, 0)
    a.label('next')
    a.branch(BEQ, ZERO, ZERO, 'loop'); a.i(ADDIU, T3, T3, ENTRY.size)
    a.label('done')
    for reg, slot in ((A0, 0x20), (A1, 0x24), (A2, 0x28), (A3, 0x2C), (V1, 0x30), (RA, 0x40)):
        a.i(LW, SP, reg, slot)
    a.i(LW, S0, V0, 0xA4)                                     # the two replaced instructions
    a.i(ANDI, V1, V1, 0x7F)
    a.r(JR, rs=RA); a.i(ADDIU, SP, SP, FRAME)
    code = a.finish()
    if len(code) != 4 * CODE_WORDS:
        raise AssertionError(f'wrapper is {len(code) // 4} words, expected {CODE_WORDS}')
    body = code + bytes(4) + b''.join(ENTRY.pack(*row) for row in rows) + struct.pack('<H', 0xFFFF)
    return body + bytes((-len(body)) % 4)


class Block:
    def __init__(self, rules):
        self.rules = check_rules(rules)
        self.source_rules = rules
        self.length = len(emit(0x80010000, rules))

    def __call__(self, address):
        return emit(address, self.source_rules)


def patch_hook(exe, wrapper_address, offset_of):
    at = offset_of(exe, HOOK)
    struct.pack_into('<2I', exe, at, 0x0C000000 | ((wrapper_address >> 2) & 0x3FFFFFF), 0)
    return dict(feature='frame_spawns', hook=hex(HOOK), wrapper=hex(wrapper_address))
