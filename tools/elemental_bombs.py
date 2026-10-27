"""Mod option "Elemental bomb effects" (2026-10-22, docs/2026-10-22-fire-detonates-bombs.txt).

The Bomb is global sprite 2 (DATAS global sprite header: flags 0x13234E, built-in programs C62/D30/E12).
ALUN_CD.EXE (US 1.1, load 0x80020000), built-in tables C 0x800C6D9C, D 0x800C719C:
  C62 0x8007D1AC  fuse (Entity+0x274, 240 frames); at 0 it sets status 3 (Entity+0x10) = goes off.
  D30 0x80081054  hit handler: attack kind 4 Bomb, 6 Fire (Fire Wand), 0xA Fire Magic -> status 3,
                  the same as the fuse running out (E12 0x80081B3C then plays the explosion).
  Hit scan 0x80039C00: attacker mask from its flags (bit2->1, bit1->8, 0x1000->0x800); a target is
  only tested when target flags & mask. Wand shots and magic target class 1; the bomb is class 8 only
  (bomb blasts), so stock fire never reaches D30 (observed: stock fuse 199 frames after the throw
  whatever hits it).
Hooks (prepend allocation, all sites signature-checked):
  0 0x80039D54 `lw v0,0x6C(s0)` (target flags) -> jal target_flags: a sprite-2 target and attack kind
    6/0xA (fire) or 7/9 (Ice Wand, Water Magic) also gets the attacker's mask, so the hit registers.
  1 0x80039F6C `sw v0,0x1D0(s0)` (hit registered) -> jal hit_mark: stores 0x19 as stock; for a sprite-2
    target hit by kind 7/9, Entity+0x284 = 1 once (a second ice hit does not stack). (The bomb's D30
    cannot be used for ice: its response for ice skips the attacker store at 0x80039F64.)
  2 0x8007D1E0 C62 `lw v1,0x274(s0)` -> jal ice_slow: while marked, every second frame the fuse gets +1
    before C62's own -1: half speed from the ice hit on. The explosion is unchanged.
Fire detonation is stock D30 once hook 0 lets the hit through."""
import struct

C_TABLE, D_TABLE, C62, D30 = 0x800C6D9C, 0x800C719C, 0x8007D1AC, 0x80081054
D30_WORDS = (0x8C820224, 0, 0x8C4201C8, 0, 0x90420000, 0, 0x3043000F, 0x24020004, 0x10620005,
             0x24020006, 0x10620003, 0x2402000A, 0x14620003, 0, 0x24020003, 0xAC820010, 0x03E00008, 0)
SCAN_HOOK, MARK_HOOK, C_HOOK = 0x80039D54, 0x80039F6C, 0x8007D1E0
SCAN_CONTEXT = (0x8E02006C, 0, 0x00571024, 0x104000B8)   # lw v0,0x6C(s0); nop; and v0,v0,s7; beqz v0,skip
MARK_CONTEXT = (0xAE110224, 0x24020019, 0xAE0201D0, 0x8E220220)   # sw s1,0x224(s0); li v0,0x19; sw v0,0x1D0(s0); lw v0,0x220(s1)
C62_CONTEXT = (0x8E030274, 0, 0x2462FFFF, 0x10600000 | ((0x8007D2E0 - 0x8007D1F0) >> 2), 0xAE020274)
MARK = 0x284   # Entity+0x284: not used by C62/D30/E12 (static); 0 on every stock bomb frame (BizHawk);
# +0x280 was 16 on every bomb frame, so it is not free


def _bne(rs, rt, off): return 0x14000000 | rs << 21 | rt << 16 | (off & 0xFFFF)
def _beq(rs, rt, off): return 0x10000000 | rs << 21 | rt << 16 | (off & 0xFFFF)


T0, T1, S0, S3 = 8, 9, 16, 19
TARGET_FLAGS = (0x8E02006C, 0x8E080068, 0x24090002, _bne(T0, T1, 10), 0x24090006,
                _beq(S3, T1, 7), 0x2409000A, _beq(S3, T1, 5), 0x24090007, _beq(S3, T1, 3), 0x24090009,
                _bne(S3, T1, 2), 0, 0x00571025, 0x03E00008, 0)   # yes: or v0,v0,s7
HIT_MARK = (0x24080019, 0xAE0801D0, 0x8E080068, 0x24090002, _bne(T0, T1, 10), 0x24090007,
            _beq(S3, T1, 3), 0x24090009, _bne(S3, T1, 6), 0,
            0x8E080000 | MARK, 0, _bne(T0, 0, 2), 0x24090001, 0xAE090000 | MARK, 0x03E00008, 0)
ICE_SLOW = (0x8E030274, 0x8E090068, 0x24080002, _bne(T1, T0, 10), 0, 0x8E090000 | MARK, 0,
            _beq(T1, 0, 6), 0x39290003, 0xAE090000 | MARK, 0x24080002, _bne(T1, T0, 2), 0,
            0x24630001, 0x03E00008, 0)   # lw v1,fuse; toggle mark 1<->2; +1 when 2
PARTS = (TARGET_FLAGS, HIT_MARK, ICE_SLOW)
SIZE = 4 * sum(map(len, PARTS))


def _off(exe, address, size=4):
    load, length = struct.unpack_from('<II', exe, 0x18)
    if not load <= address <= load + length - size: raise ValueError(f'Elemental bombs: {address:08X} outside the executable')
    return 0x800 + address - load


def _words(exe, address, n): return struct.unpack_from(f'<{n}I', exe, _off(exe, address, 4 * n))


def validate(exe):
    if exe[:8] != b'PS-X EXE': raise ValueError('Elemental bombs needs a PS-X executable')
    if _words(exe, D_TABLE + 4 * 30, 1)[0] != D30 or _words(exe, C_TABLE + 4 * 62, 1)[0] != C62:
        raise ValueError('Elemental bombs: built-in program table C62/D30 differs')
    if _words(exe, D30, len(D30_WORDS)) != D30_WORDS: raise ValueError('Elemental bombs: D30 hit handler differs')
    if _words(exe, C_HOOK, 5) != C62_CONTEXT: raise ValueError('Elemental bombs: C62 bomb fuse code differs')
    if _words(exe, SCAN_HOOK, 4) != SCAN_CONTEXT: raise ValueError('Elemental bombs: hit scan target test differs')
    if _words(exe, MARK_HOOK - 8, 4) != MARK_CONTEXT: raise ValueError('Elemental bombs: hit scan hit store differs')


class Block:
    length = SIZE
    def __call__(self, address): return struct.pack(f'<{SIZE // 4}I', *TARGET_FLAGS, *HIT_MARK, *ICE_SLOW)


def addresses(address):
    out = []
    for part in PARTS: out.append(address); address += 4 * len(part)
    return out


def patch_hooks(exe, address):
    """exe: bytearray already validated; address: where Block was placed (before the prefix is inserted)."""
    flags, mark, slow = addresses(address)
    for site, target in ((SCAN_HOOK, flags), (MARK_HOOK, mark), (C_HOOK, slow)):
        struct.pack_into('<I', exe, _off(exe, site), 0x0C000000 | (target >> 2 & 0x3FFFFFF))
    return {'feature': 'elemental_bombs', 'module': 'ALUN_CD.EXE',
            'target_flags': hex(flags), 'hit_mark': hex(mark), 'ice_slow': hex(slow),
            'sites': [dict(address=hex(SCAN_HOOK), stock='0x8e02006c lw v0,0x6C(s0) (hit scan)', new='jal target_flags'),
                      dict(address=hex(MARK_HOOK), stock='0xae0201d0 sw v0,0x1D0(s0) (hit scan)', new='jal hit_mark'),
                      dict(address=hex(C_HOOK), stock='0x8e030274 lw v1,0x274(s0) (C62 fuse)', new='jal ice_slow')],
            'fire': 'stock D30 (kinds 4/6/0xA -> status 3), reached through hook 0'}
