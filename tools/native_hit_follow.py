"""Hit spot that follows its object (2026-10-24): a lifted, carried, thrown, pushed or rolled object
keeps its Hit trigger. The stock hit spot (map 10 entity 1) gets a C program that copies the
object's position onto itself every frame with an injected opcode, and leaves when the object is
gone.

Injected (private-state module, like E0-EE; stock dispatch slot 0x8009B814 + 0xEF*4 is the
fallback 0x8003DBD0):
* EF sel: n = 0x8003D374(logic, sel) (the stock selection, list 0x8013D488; a record number
  selects that placed object while it is live, research/us_decomp/vm_ops/audit_00_2F.md);
  n > 0: logic PosX/PosY/PosZ (+0x114/+0x118/+0x11C) = the first selected's, Result 1;
  n == 0: Result 0. Length 2. A hit stored by the object itself (spot +0x224 == object) is
  cleared; the spot is an attack target (+6C bit0, the attack scan's target bit) only while the
  object stands on the ground (+0x144), has no holder (+0x28) and is not breaking (status 3), so
  a carried or flying object does not hit its own spot (BizHawk p2/p3: a thrown barrel broke on it).
Spot C: 17 (gravity off), loop { EF owner; 04 -> gone; 00 (next frame) }, gone: 2E 80 (the spot
marks itself inactive), FF."""
import struct

OPCODE = 0xEF
SELECT = 0x8003D374
SELECTED = 0x8013D488


def emit():
    from project_state_runtime import _Mips
    m = _Mips()
    m.i(9, 29, 29, -24); m.i(43, 29, 31, 20); m.i(43, 29, 16, 16); m.i(43, 29, 17, 12)
    m.r(4, 0, 16, 0x21)                       # s0 = logic
    m.r(7, 0, 17, 0x21)                       # s1 = process state
    m.load(8, 6, 0)                           # t0 = script pointer
    m.load(5, 8, 1, 36)                       # a1 = selector
    m.words.extend([0x0C000000 | (SELECT >> 2) & 0x3FFFFFF, 0])   # jal select(a0 = logic, a1)
    m.branch(4, 2, 0, 'none')                 # nothing selected: the object is gone
    m.li(9, SELECTED); m.load(9, 9, 0)        # t1 = first selected entity
    for off in (0x114, 0x118, 0x11C):
        m.load(10, 9, off); m.i(43, 16, 10, off)
    # The object's own throw / break is no hit on it (BizHawk p2, 2026-10-24: a barrel thrown into a
    # pillar broke and ran "Barrel hit."): a hit by the object itself (spot +0x224 = the object) is
    # dropped, and while the object is held (+0x28 holder) or breaking (status 3) the spot is no
    # attack target (+6C bit0 off).
    m.load(10, 16, 0x224); m.branch(5, 10, 9, 'own')     # attacker != the object
    m.i(43, 16, 0, 0x224)                       # sw zero, 0x224(s0)
    m.label('own')
    m.load(10, 9, 0x10); m.load(12, 16, 0x6C)    # t2 = object status, t4 = spot +6C
    m.i(13, 12, 12, 1)                          # ori t4, t4, 1
    m.i(9, 0, 13, 3); m.branch(4, 10, 13, 'off')     # status 3: not a target
    m.load(13, 9, 0x28); m.branch(5, 13, 0, 'off')    # held: not a target
    m.load(13, 9, 0x144); m.branch(5, 13, 0, 'flags')  # on the ground (+0x144): a target
    m.label('off'); m.i(9, 0, 14, -2); m.r(12, 14, 12, 0x24)   # and t4, t4, ~1
    m.label('flags'); m.i(43, 16, 12, 0x6C)
    m.i(9, 0, 11, 1); m.branch(4, 0, 0, 'store')
    m.label('none'); m.r(0, 0, 11, 0x21)      # t3 = 0
    m.label('store'); m.i(43, 17, 11, 0x2C)   # Result
    m.load(31, 29, 20); m.load(16, 29, 16); m.load(17, 29, 12)
    m.words.extend([0x24020002, 0x03E00008, 0x27BD0018])   # v0 = 2 (length); jr ra; addiu sp, sp, 24
    return m.finish()


def follow_program(owner_record):
    """The spot's C program; owner_record: the object's record number on this map (< 0x80)."""
    if type(owner_record) is not int or not 0 <= owner_record < 0x80:
        raise ValueError('A following hit spot needs its object as one of the first 128 placements of the map')
    from event_logic_compile import _Assembler
    a = _Assembler()
    a.data.append(0x17)                       # gravity off: it stays where the object is
    a.label('loop')
    a.data.extend((OPCODE, owner_record)); a.branch(4, 'gone')
    a.data.append(0x00); a.branch(2, 'loop')
    a.label('gone'); a.data.extend((0x2E, 0x80, 0xFF))
    return a.finish()
