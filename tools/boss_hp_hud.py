"""Boss HP on the HUD (user 2026-10-27): the current boss's hit points, as many digits as needed
(at least 3: 000), halfway between the max-life number ("/15") and the Gilder number, shown while
a boss is in the room.

Stock US 1.1 ALUN_CD.EXE, static (2026-10-27):
* 0x8004D67C `jal 0x8004DB10` (HUD update): 0x8004DB10 writes the max-life digits into the HUD's
  20-byte SPRT primitives 0x8011952C + buffer * 100 (5 sprites, 8x16, x = *0x800AA0C0 + 0x90 + 8i,
  y = *0x800AA0C2; buffer = *0x801E5F38) and links them into the ordering table entry
  0x801F53A0 + buffer * 40. Digit d's texture u, v = bytes 0, 1 of 0x8009EE40 + d * 20.
* The Gilder digits (0x8011993C) start at x + 0x100; "/15" ends at x + 0xB8: middle x + 0xDC.
* Actors 0x801AC6F8 + slot * 0x294 (64): +0x10 status (1-3 alive), +0x68 class (catalogue index),
  +0x14 hit points.

Hook: that jal becomes jal wrapper. The wrapper calls 0x8004DB10, then finds the first live actor
whose class is a boss class of the project (the Database's Boss list), and draws its hit points
(0-99999) with copies of the "/15" digit sprite, linked into the same ordering-table entry, so it
shows and hides with the HUD. No boss: nothing drawn. Static only; needs an in-game check."""
import struct
from native_animation_spawns import (_Asm, ZERO, V0, V1, A0, A1, A2, A3, T0, T1, T2, T3, T4, T5, T6, T7,
                                     S0, T8, T9, SP, RA, SLL, ADDU, SUBU, JR, BEQ, BNE, ADDIU, LW, LHU, SW)

HOOK, HOOK_WORD = 0x8004D67C, 0x0C000000 | ((0x8004DB10 >> 2) & 0x3FFFFFF)
LIFE_DRAW = 0x8004DB10
PRIMS, BUFFER, OT, HUD_X, HUD_Y, DIGITS = 0x8011952C, 0x801E5F38, 0x801F53A0, 0x800AA0C0, 0x800AA0C2, 0x8009EE40
ACTORS, STRIDE, SLOTS = 0x801AC6F8, 0x294, 64
MIDDLE = 0xDC
MAX_DIGITS = 5
S1, S2 = 17, 18
LBU, SB, SH, ANDI, ORI, LUI, SLTIU, XORI = 36, 40, 41, 12, 13, 15, 11, 14
AND, OR, DIVU, MFHI, MFLO, SLT = 0x24, 0x25, 0x1B, 0x10, 0x12, 0x2A
FRAME = 0x30


def boss_classes(document):
    out = []
    for d in (document or {}).get('definitions', []):
        c = (d.get('source') or {}).get('catalogue_index')
        if d.get('kind') == 'boss' and not d.get('clone_of') and type(c) is int and 0 <= c < 0xFFFF and c not in out:
            out.append(c)
    return out


def _code(address, prims, table):
    a = _Asm(address)
    a.i(ADDIU, SP, SP, -FRAME)
    for reg, slot in ((RA, 0x20), (S0, 0x14), (S1, 0x18), (S2, 0x1C)):
        a.i(SW, SP, reg, slot)
    a.j(3, LIFE_DRAW); a.nop()                                  # the game's own max-life digits
    # the first live boss
    a.li(T0, ACTORS + STRIDE); a.i(ADDIU, ZERO, T9, SLOTS - 1)
    a.i(ADDIU, ZERO, T3, -1); a.i(ANDI, T3, T3, 0xFFFF)
    a.label('actor')
    a.i(LW, T0, T5, 0x10); a.nop(); a.i(ADDIU, T5, T5, -1); a.i(SLTIU, T5, T5, 3)
    a.branch(BEQ, T5, ZERO, 'actor_next'); a.nop()
    a.i(LW, T0, T6, 0x68); a.li(T1, table)
    a.label('boss')
    a.i(LHU, T1, T2, 0); a.nop()
    a.branch(BEQ, T2, T3, 'actor_next'); a.nop()
    a.branch(BEQ, T2, T6, 'found'); a.i(ADDIU, T1, T1, 2)
    a.branch(BEQ, ZERO, ZERO, 'boss'); a.nop()
    a.label('actor_next')
    a.i(ADDIU, T9, T9, -1)
    a.branch(BNE, T9, ZERO, 'actor'); a.i(ADDIU, T0, T0, STRIDE)
    a.branch(BEQ, ZERO, ZERO, 'done'); a.nop()                 # no boss: nothing drawn
    a.label('found')
    a.i(LW, T0, S0, 0x14); a.nop()
    a.r(SLT, rs=S0, rt=ZERO, rd=T1)
    a.branch(BEQ, T1, ZERO, 'positive'); a.nop()
    a.r(ADDU, rd=S0)                                            # below 0 -> 0
    a.label('positive')
    a.li(T1, 100000); a.r(0x2B, rs=S0, rt=T1, rd=T2)            # sltu
    a.branch(BNE, T2, ZERO, 'small'); a.nop()
    a.li(S0, 99999)
    a.label('small')
    # digits, units last, at sp+0..4
    a.r(ADDU, rs=S0, rt=ZERO, rd=V0); a.i(ADDIU, ZERO, T1, 10)
    for i in range(MAX_DIGITS - 1, -1, -1):
        a.r(DIVU, rs=V0, rt=T1); a.r(MFLO, rd=V0); a.r(MFHI, rd=T2); a.nop(); a.nop()
        a.i(SB, SP, T2, i)
    # how many: at least 3, more when needed
    a.i(ADDIU, ZERO, S1, 3)
    for limit in (1000, 10000):
        a.i(SLTIU, S0, T1, limit); a.i(XORI, T1, T1, 1); a.r(ADDU, rs=S1, rt=T1, rd=S1)
    a.i(ADDIU, SP, S2, MAX_DIGITS); a.r(SUBU, rs=S2, rt=S1, rd=S2)   # first digit shown
    # this frame's buffer: template sprite, our sprites, ordering-table entry
    a.li(T7, BUFFER); a.i(LW, T7, T7, 0); a.nop()
    a.r(SLL, rt=T7, rd=T1, shamt=6); a.r(SLL, rt=T7, rd=T2, shamt=5); a.r(ADDU, rs=T1, rt=T2, rd=T1)
    a.r(SLL, rt=T7, rd=T2, shamt=2); a.r(ADDU, rs=T1, rt=T2, rd=T1)      # buffer * 100
    a.li(T8, PRIMS + 3 * 20); a.r(ADDU, rs=T8, rt=T1, rd=T8)
    a.li(T4, prims); a.r(ADDU, rs=T4, rt=T1, rd=T4)
    a.r(SLL, rt=T7, rd=T1, shamt=5); a.r(SLL, rt=T7, rd=T2, shamt=3); a.r(ADDU, rs=T1, rt=T2, rd=T1)   # * 40
    a.li(A3, OT); a.r(ADDU, rs=A3, rt=T1, rd=A3)
    a.li(T1, HUD_X); a.i(LHU, T1, T5, 0); a.i(LHU, T1, A2, 2); a.nop()
    a.i(ADDIU, T5, T5, MIDDLE); a.r(SLL, rt=S1, rd=T1, shamt=2); a.r(SUBU, rs=T5, rt=T1, rd=T5)   # centred
    a.label('digit')
    for w in range(5):
        a.i(LW, T8, A0, 4 * w); a.nop(); a.i(SW, T4, A0, 4 * w)
    a.i(SH, T4, T5, 8); a.i(SH, T4, A2, 10)
    a.i(LBU, S2, A0, 0); a.nop()
    a.r(SLL, rt=A0, rd=A1, shamt=4); a.r(SLL, rt=A0, rd=A0, shamt=2); a.r(ADDU, rs=A0, rt=A1, rd=A0)
    a.li(A1, DIGITS); a.r(ADDU, rs=A0, rt=A1, rd=A0)
    a.i(LBU, A0, A1, 0); a.i(LBU, A0, V1, 1); a.nop()
    a.i(SB, T4, A1, 12); a.i(SB, T4, V1, 13)
    # link into the ordering table, as 0x8004DB10 does
    a.i(LW, T4, V1, 0); a.i(LW, A3, V0, 0); a.i(LUI, 0, T2, 0xFF00); a.i(LUI, 0, T1, 0x00FF); a.i(ORI, T1, T1, 0xFFFF)
    a.r(AND, rs=V1, rt=T2, rd=V1); a.r(AND, rs=V0, rt=T1, rd=A0); a.r(OR, rs=V1, rt=A0, rd=V1); a.i(SW, T4, V1, 0)
    a.r(AND, rs=V0, rt=T2, rd=V0); a.r(AND, rs=T4, rt=T1, rd=A0); a.r(OR, rs=V0, rt=A0, rd=V0); a.i(SW, A3, V0, 0)
    a.i(ADDIU, T4, T4, 20); a.i(ADDIU, T5, T5, 8); a.i(ADDIU, S2, S2, 1); a.i(ADDIU, S1, S1, -1)
    a.branch(BNE, S1, ZERO, 'digit'); a.nop()
    a.label('done')
    for reg, slot in ((RA, 0x20), (S0, 0x14), (S1, 0x18), (S2, 0x1C)):
        a.i(LW, SP, reg, slot)
    a.nop(); a.r(JR, rs=RA); a.i(ADDIU, SP, SP, FRAME)
    return a.finish()


class Block:
    def __init__(self, bosses):
        if not bosses:
            raise ValueError('Boss HP on the HUD: the Database has no Boss classes')
        self.bosses = list(bosses)
        self.code_size = len(_code(0x80010000, 0, 0))
        self.length = self.code_size + 2 * MAX_DIGITS * 20 + 2 * (len(self.bosses) + 1)
        self.length += (-self.length) % 4

    def __call__(self, address):
        prims = address + self.code_size; table = prims + 2 * MAX_DIGITS * 20
        raw = bytearray(_code(address, prims, table)) + bytes(2 * MAX_DIGITS * 20)
        raw += struct.pack(f'<{len(self.bosses) + 1}H', *self.bosses, 0xFFFF)
        return bytes(raw + bytes(self.length - len(raw)))


def validate(exe):
    load = struct.unpack_from('<I', exe, 0x18)[0]
    if struct.unpack_from('<I', exe, HOOK - load + 0x800)[0] != HOOK_WORD:
        raise ValueError('Boss HP on the HUD: the HUD update call at 0x8004D67C differs from the stock game')


def patch_hook(exe, address, offset_of):
    at = offset_of(exe, HOOK)
    if struct.unpack_from('<I', exe, at)[0] != HOOK_WORD:
        raise ValueError('Boss HP on the HUD: the HUD update call at 0x8004D67C differs from the stock game')
    struct.pack_into('<I', exe, at, 0x0C000000 | ((address >> 2) & 0x3FFFFFF))
    return dict(feature='boss_hp_hud', hook=hex(HOOK), wrapper=hex(address))
