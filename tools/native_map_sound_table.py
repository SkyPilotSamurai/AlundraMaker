"""A project map's own sound records live in its own map data (user 2026-10-26).

Stock ALUN_CD.EXE US 1.1 (static trace 2026-10-26): PlaySound 0x8004A128 keeps the requested id in
s6 (0x8004A164) and the record id in s3. A record whose bank (+0) is not -1 reaches 0x8004A3D4,
which walks the +0x0C chain until the record's bank equals the loaded set (0x801D7DC4); the
found path 0x8004A440 reads the record at 0x800AA150 + s3 * 0x16. PlaySound uses no t registers.

Here, the records a project map's own sound set needs are not chain records below the game code:
they are stored at the end of the map's sprite-info section 3 (header word 4 = section 4 start
= its end; the block stays in the buffer 0x801536C0 while the map runs). The later sections
shift down inside the map's own 2048-aligned block; no other map moves:
    count * [u16 sound id, 0x16-byte record], u16 count, u16 map id, 'SNDT'
A fixed hook at 0x8004A3D4 looks the requested id (s6) up in the current map's table (checked by
magic and map id 0x801F5358); on a match it copies that record into the unused record 510
(bank -2, no chain reaches it, map_sound_sets.FREE_RECORDS) and continues at 0x8004A440 with
s3 = 510. Otherwise it runs the two replaced instructions and the game's own chain walk.
The shared code is fixed-size (EMIT_SIZE), whatever the number of maps or sounds.
Original MIPS, not vanilla code."""
import struct

HOOK_SITE = 0x8004A3D4
STOCK_WORDS = (0x3C02801D, 0x8C427DC4)   # lui v0,0x801D ; lw v0,0x7DC4(v0)
RESUME = 0x8004A3DC
FOUND = 0x8004A440
REC, REC_SIZE = 0x800AA150, 0x16
SCRATCH = 510
MAP_BUFFER = 0x801536C0
CURRENT_MAP = 0x801F5358
MAGIC = b'SNDT'
ENTRY = 2 + REC_SIZE


def table(map_id, records):
    """Bytes appended to the map's section 3: records = [(sound id, 11 halfwords)]."""
    out = bytearray()
    for n, rec in records:
        out += struct.pack('<H11h', n, *rec)
    return bytes(out + struct.pack('<HH', len(records), map_id) + MAGIC)


def verify(exe, load):
    off = HOOK_SITE - load + 0x800
    if struct.unpack_from('<2I', exe, off) != STOCK_WORDS:
        raise ValueError('Map sound table: unexpected stock code at 0x%08X' % HOOK_SITE)


def emit():
    """Position-independent hook (absolute j targets only)."""
    w = []
    def I(op, rs, rt, im): w.append(op << 26 | rs << 21 | rt << 16 | (im & 0xFFFF))
    def R(rs, rt, rd, sh, f): w.append(rs << 21 | rt << 16 | rd << 11 | sh << 6 | f)
    def li(rt, v): I(15, 0, rt, (v + 0x8000) >> 16); I(9, rt, rt, v)
    def j(a): w.append(0x08000000 | (a >> 2 & 0x3FFFFFF))
    br = []
    def b(op, rs, rt, label): br.append((len(w), label)); I(op, rs, rt, 0); w.append(0)
    lab = {}
    V0, S3, S6, T0, T1, T2, T3, T4, T5, T6, T7 = 2, 19, 22, 8, 9, 10, 11, 12, 13, 14, 15
    li(T0, MAP_BUFFER); I(35, T0, T1, 16); w.append(0)        # t1 = section 4 start
    R(T0, T1, T0, 0, 0x21)                                     # t0 = end of section 3
    I(35, T0, T1, -4); li(T2, struct.unpack('<I', MAGIC)[0])
    b(5, T1, T2, 'stock')
    I(37, T0, T1, -6); li(T2, CURRENT_MAP); I(35, T2, T2, 0); w.append(0)
    b(5, T1, T2, 'stock')
    I(37, T0, T4, -8); w.append(0)                             # t4 = count
    R(0, T4, T6, 3, 0); R(0, T4, T7, 4, 0); R(T6, T7, T6, 0, 0x21)   # t6 = count * 24
    R(T0, T6, T5, 0, 0x23); I(9, T5, T5, -8)                   # t5 = first entry
    lab['loop'] = len(w)
    b(4, T4, 0, 'stock')
    I(37, T5, T7, 0); w.append(0)
    b(4, T7, S6, 'found')
    I(9, T5, T5, ENTRY); I(9, T4, T4, -1)
    br.append((len(w), 'loop')); I(4, 0, 0, 0); w.append(0)
    lab['found'] = len(w)
    li(T3, REC + SCRATCH * REC_SIZE)
    for k in range(11):
        I(33, T5, T1, 2 + 2 * k); w.append(0); I(41, T3, T1, 2 * k)
    I(9, 0, S3, SCRATCH)
    j(FOUND); w.append(0)
    lab['stock'] = len(w)
    w.extend(STOCK_WORDS); w.append(0)
    j(RESUME); w.append(0)
    for at, label in br:
        w[at] |= (lab[label] - at - 1) & 0xFFFF
    return struct.pack('<%dI' % len(w), *w)


EMIT_SIZE = len(emit())


def patch(exe, load, code_address):
    verify(exe, load)
    exe = bytearray(exe)
    struct.pack_into('<2I', exe, HOOK_SITE - load + 0x800, 0x08000000 | (code_address >> 2 & 0x3FFFFFF), 0)
    return exe
