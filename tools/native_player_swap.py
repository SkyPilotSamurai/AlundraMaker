"""Change Player Character (Alundra / Meia) at runtime: private opcode EB nn (nn 0 Alundra, 1 Meia).

Original injected MIPS (not a recovered vanilla routine). Evidence (docs/2026-10-22-player-
character-swap.txt, BizHawk US v1.1 RAM/VRAM dumps): the global sprite bank (DATAS.BIN 0x800 up to
its texture sheet) stays resident in RAM at 0x800CBF58 + (offset - 0x800); its 8 4bpp texture pages
sit in VRAM at x = 320 + 64 * page, y = 256..511 and global palette slot k at VRAM (192, 480 + k)
(DATAS 0xCAC + 32 * k); a room warp did not re-upload them.
The build computes the XOR of the project's game data with the same data after the Start as Meia
costume (player_costume.apply_costume, with the command's two options); it is appended to DATAS.BIN
and read in 4 KB chunks by the game's own file read during the swap (see below). The handler applies that XOR when the requested character
differs from the current one: RAM words in place; VRAM spans read back (GP0 C0), XORed and written
again (GP0 A0), with interrupts masked and after GPU DMA (channel 2) finishes. XOR is its own
inverse, so the same data swaps back. The current character lives in the injected state word: an
EXE reload (reset, loading a save) starts as Alundra again, matching the reloaded graphics.
"""
import struct

OPCODE = 0xEB
BANK_RAM = 0x800CBF58          # RAM address of DATAS.BIN offset 0x800 (observed, US v1.1)
SHEET_X, SHEET_Y = 320, 256
CLUT_DATAS, CLUT_X, CLUT_Y = 0xCAC, 192, 480


def _runs(words, gap):
    out = []; s = p = None
    for x in words:
        if s is None or x > p + 4 * gap:
            if s is not None: out.append((s, p))
            s = x
        p = x
    if s is not None: out.append((s, p))
    return out


NO_DASH = 0x8003257C   # stock ALUN_CD.EXE: andi v0,v0,0x10 (Triangle dash check), 0x30420010
LIMIT = 16 * 1024      # swap data that fits beside the other editor code (32 KB prepend in all)


def patch_data(stock, meia, no_dash=False):
    """(ram list bytes, vram list bytes) from two game data images (bank + sheet only)."""
    from texture_codec import unpack_ez
    start, sheet = struct.unpack_from('<2I', stock); end = struct.unpack_from('<I', stock, 0x14)[0]
    if start != 0x800 or struct.unpack_from('<2I', meia) != (start, sheet):
        raise ValueError('Player swap needs the same global sprite bank layout in both pictures')
    ram = bytearray()
    words = [i for i in range(start, sheet & ~3, 4) if stock[i:i + 4] != meia[i:i + 4]]
    for s, e in _runs(words, 2):
        n = (e - s) // 4 + 1
        ram += struct.pack('<2I', BANK_RAM + s - start, n)
        ram += bytes(a ^ b for a, b in zip(stock[s:s + 4 * n], meia[s:s + 4 * n]))
    if no_dash:   # Meia without Alundra for other actions: Triangle never starts a dash (as editor_qol)
        ram += struct.pack('<3I', NO_DASH, 1, 0x10)
    ram += bytes(8)
    ra, _ = unpack_ez(bytes(stock[sheet:end]), limit=262144)
    rm, _ = unpack_ez(bytes(meia[sheet:struct.unpack_from('<I', meia, 0x14)[0]]), limit=262144)
    vram = bytearray()

    def span(x, y, a, b):
        n = len(a) // 4
        vram.extend(struct.pack('<I', x | y << 10 | n << 19) + bytes(p ^ q for p, q in zip(a, b)))
    for row in range(2048):
        page, y = divmod(row, 256); base = row * 128
        ws = [i for i in range(base, base + 128, 4) if ra[i:i + 4] != rm[i:i + 4]]
        for s, e in _runs(ws, 1):
            span(SHEET_X + 64 * page + (s - base) // 2, SHEET_Y + y, ra[s:e + 4], rm[s:e + 4])
    for k in range(32):
        o = CLUT_DATAS + 32 * k
        if stock[o:o + 32] != meia[o:o + 32]:
            span(CLUT_X, CLUT_Y + k, stock[o:o + 32], meia[o:o + 32])
    vram += bytes(4)
    return bytes(ram), bytes(vram)


def emit(state, ram_list, vram_list, scratch):
    """Handler code. state: state word address; lists/scratch: RAM addresses."""
    from project_state_runtime import _Mips
    m = _Mips()
    T0, T1, T2, T3, T4, T5, T6, T7, T8, T9, V1 = 8, 9, 10, 11, 12, 13, 14, 15, 24, 25, 3

    def wait(bit, label):          # until GPUSTAT (t5+4) has the bit set
        m.label(label); m.load(T7, T5, 4); m.i(15, 0, T8, 1 << (bit - 16)); m.r(T7, T8, T7, 0x24); m.branch(4, T7, 0, label)
    m.load(T0, 6, 0); m.load(T1, T0, 1, 36)                       # t1 = operand
    m.li(T2, state); m.load(T3, T2, 0); m.branch(4, T1, T3, 'ret')
    m.i(43, T2, T1, 0)
    m.words.append(0x40000000 | T9 << 16 | 12 << 11)              # mfc0 t9, SR
    m.i(9, 0, T3, -2); m.r(T9, T3, T4, 0x24); m.words.append(0x40800000 | T4 << 16 | 12 << 11)   # IEc off
    m.li(T0, ram_list)
    m.label('ram'); m.load(T1, T0, 0); m.load(T2, T0, 4); m.i(9, T0, T0, 8); m.branch(4, T1, 0, 'vram')
    m.label('rw'); m.load(T3, T0, 0); m.load(T4, T1, 0); m.r(T4, T3, T4, 0x26); m.i(43, T1, T4, 0)
    m.i(9, T0, T0, 4); m.i(9, T1, T1, 4); m.i(9, T2, T2, -1); m.branch(5, T2, 0, 'rw')
    m.branch(4, 0, 0, 'ram')
    m.label('vram'); m.li(T5, 0x1F801810); m.li(T6, 0x1F8010A8)
    m.label('dma'); m.load(T7, T6, 0); m.i(15, 0, T8, 0x0100); m.r(T7, T8, T7, 0x24); m.branch(5, T7, 0, 'dma')
    m.li(T0, vram_list)
    m.label('span'); m.load(T1, T0, 0); m.i(9, T0, T0, 4); m.branch(4, T1, 0, 'done')
    # header word: x | y << 10 | words << 19 (span = 2 * words halfwords, one row)
    m.i(12, T1, T3, 0x3FF); m.r(0, T1, T4, 2, 10); m.i(12, T4, T4, 0x1FF); m.r(0, T4, T4, 0, 16); m.r(T3, T4, T2, 0x25)   # t2 = x | y << 16
    m.r(0, T1, T6, 2, 19); m.r(0, T6, T4, 0, 1); m.i(15, 0, T3, 1); m.r(T4, T3, T4, 0x25)          # t6 = words; t4 = 2n | 1 << 16
    m.r(T6, 0, V1, 0x21)  # v1 = t6
    wait(26, 'c1'); m.i(15, 0, T3, 0xC000); m.i(43, T5, T3, 0); m.i(43, T5, T2, 0); m.i(43, T5, T4, 0)
    wait(27, 'rd0'); m.li(T3, scratch)
    m.label('rd'); m.load(T7, T5, 0); m.load(T8, T0, 0); m.r(T7, T8, T7, 0x26); m.i(43, T3, T7, 0)
    m.i(9, T3, T3, 4); m.i(9, T0, T0, 4); m.i(9, V1, V1, -1); m.branch(5, V1, 0, 'rd')
    wait(26, 'c2'); m.i(15, 0, T3, 0xA000); m.i(43, T5, T3, 0); m.i(43, T5, T2, 0); m.i(43, T5, T4, 0)
    m.r(T6, 0, V1, 0x21); m.li(T3, scratch)
    m.label('wr'); m.load(T7, T3, 0); m.i(43, T5, T7, 0); m.i(9, T3, T3, 4); m.i(9, V1, V1, -1); m.branch(5, V1, 0, 'wr')
    m.branch(4, 0, 0, 'span')
    m.label('done'); wait(26, 'c3'); m.i(15, 0, T3, 0x0100); m.i(43, T5, T3, 0)   # clear texture cache
    m.words.append(0x40800000 | T9 << 16 | 12 << 11)                              # restore SR
    m.li(T2, state); m.i(43, T2, 31, 4)                                           # keep ra; BIOS A(44h) FlushCache (code word may change)
    m.i(9, 0, T2, 0xA0); m.i(9, 0, T1, 0x44); m.words.extend([T2 << 21 | 31 << 11 | 9, 0])
    m.li(T2, state); m.load(31, T2, 4)
    m.label('ret'); m.i(9, 0, 2, 2); m.words.extend([0x03E00008, 0])
    return m.finish()


def max_span_words(vram_list):
    o = 0; most = 0
    while True:
        h = struct.unpack_from('<I', vram_list, o)[0]
        if not h: return most
        most = max(most, h >> 19); o += 4 + 4 * (h >> 19)


# Disc file (user 2026-10-22): the XOR data is appended to DATA\DATAS.BIN (2048-aligned, after the
# map table's end sentinel, so no map read reaches it) and read during the swap through the game's
# own synchronous file read, stock ALUN_CD.EXE 0x80083F04 ReadFile(name, dest, offset, size)
# (wraps 0x80050220: CdSearchFile, CdRead, CdReadSync; offset must be 2048-aligned, 0x8005028C),
# the same call the game uses with the name string at 0x800C7DD4 ("DATA\DATAS.BIN", 0x8002C298).
# Records never cross a CHUNK: header < 0 -> RAM run (address, count, words); header > 0 -> VRAM
# span (x | y << 10 | words << 19, words); 0 -> end of chunk.
READ_FILE, DATAS_NAME = 0x80083F04, 0x800C7DD4
CHUNK = 4096


def disc_blob(ram_list, vram_list):
    """Chunked record stream (bytes, chunk count)."""
    recs = []; o = 0
    while True:
        addr, n = struct.unpack_from('<2I', ram_list, o)
        if not addr: break
        data = ram_list[o + 8:o + 8 + 4 * n]; o += 8 + 4 * n
        for k in range(0, n, 256):   # short runs: every record fits a chunk
            part = data[4 * k:4 * min(n, k + 256)]
            recs.append(struct.pack('<2I', addr + 4 * k, len(part) // 4) + part)
    o = 0
    while True:
        h = struct.unpack_from('<I', vram_list, o)[0]
        if not h: break
        recs.append(vram_list[o:o + 4 + 4 * (h >> 19)]); o += 4 + 4 * (h >> 19)
    chunks = [bytearray()]
    for r in recs:
        if len(chunks[-1]) + len(r) + 4 > CHUNK: chunks.append(bytearray())
        chunks[-1] += r
    return b''.join(bytes(c) + bytes(CHUNK - len(c)) for c in chunks), len(chunks)


def emit_disc(state, buf, scratch, base, count):
    """Handler: per chunk ReadFile into buf (retried), then apply its records with interrupts masked."""
    from project_state_runtime import _Mips
    m = _Mips()
    T0, T1, T2, T3, T4, T5, T6, T7, T8, T9, V0, V1 = 8, 9, 10, 11, 12, 13, 14, 15, 24, 25, 2, 3
    S0, S1, S2, S3, SP, RA = 16, 17, 18, 19, 29, 31
    jal = lambda a: m.words.extend([0x0C000000 | ((a >> 2) & 0x3FFFFFF), 0])

    def wait(bit, label):
        m.label(label); m.load(T7, T5, 4); m.i(15, 0, T8, 1 << (bit - 16)); m.r(T7, T8, T7, 0x24); m.branch(4, T7, 0, label)
    m.i(9, SP, SP, -40); m.i(43, SP, RA, 32); m.i(43, SP, S0, 16); m.i(43, SP, S1, 20); m.i(43, SP, S2, 24); m.i(43, SP, S3, 28)
    m.load(T0, 6, 0); m.load(T1, T0, 1, 36)
    m.li(T2, state); m.load(T3, T2, 0); m.branch(4, T1, T3, 'exit')
    m.i(43, T2, T1, 0); m.r(0, 0, S0, 0x21)
    m.label('chunk'); m.i(9, 0, S1, count); m.branch(4, S0, S1, 'finish')
    # (ReadFile retries by itself on a read error: 80050408 waits, then starts again at 800502A0)
    m.li(4, DATAS_NAME); m.li(5, buf); m.li(6, base); m.r(0, S0, T0, 0, 12); m.r(6, T0, 6, 0x21)
    m.li(7, CHUNK); jal(READ_FILE)
    m.words.append(0x40000000 | T9 << 16 | 12 << 11)
    m.i(9, 0, T3, -2); m.r(T9, T3, T4, 0x24); m.words.append(0x40800000 | T4 << 16 | 12 << 11)
    m.li(T5, 0x1F801810); m.li(T6, 0x1F8010A8)
    m.label('dma'); m.load(T7, T6, 0); m.i(15, 0, T8, 0x0100); m.r(T7, T8, T7, 0x24); m.branch(5, T7, 0, 'dma')
    m.li(S3, buf)
    m.label('rec'); m.load(T1, S3, 0); m.i(9, S3, S3, 4); m.branch(4, T1, 0, 'endchunk')
    m.words.extend([0x04000000 | T1 << 21, 0]); neg_at = len(m.words) - 2   # bltz t1, ram (patched below)
    m.i(12, T1, T3, 0x3FF); m.r(0, T1, T4, 2, 10); m.i(12, T4, T4, 0x1FF); m.r(0, T4, T4, 0, 16); m.r(T3, T4, T2, 0x25)
    m.r(0, T1, T6, 2, 19); m.r(0, T6, T4, 0, 1); m.i(15, 0, T3, 1); m.r(T4, T3, T4, 0x25); m.r(T6, 0, V1, 0x21)
    wait(26, 'c1'); m.i(15, 0, T3, 0xC000); m.i(43, T5, T3, 0); m.i(43, T5, T2, 0); m.i(43, T5, T4, 0)
    wait(27, 'rd0'); m.li(T3, scratch)
    m.label('rd'); m.load(T7, T5, 0); m.load(T8, S3, 0); m.r(T7, T8, T7, 0x26); m.i(43, T3, T7, 0)
    m.i(9, T3, T3, 4); m.i(9, S3, S3, 4); m.i(9, V1, V1, -1); m.branch(5, V1, 0, 'rd')
    wait(26, 'c2'); m.i(15, 0, T3, 0xA000); m.i(43, T5, T3, 0); m.i(43, T5, T2, 0); m.i(43, T5, T4, 0)
    m.r(T6, 0, V1, 0x21); m.li(T3, scratch)
    m.label('wr'); m.load(T7, T3, 0); m.i(43, T5, T7, 0); m.i(9, T3, T3, 4); m.i(9, V1, V1, -1); m.branch(5, V1, 0, 'wr')
    m.branch(4, 0, 0, 'rec')
    m.label('ram'); m.words[neg_at] |= (m.labels['ram'] - neg_at - 1) & 0xFFFF
    m.load(T2, S3, 0); m.i(9, S3, S3, 4)
    m.label('rw'); m.load(T3, S3, 0); m.load(T4, T1, 0); m.r(T4, T3, T4, 0x26); m.i(43, T1, T4, 0)
    m.i(9, S3, S3, 4); m.i(9, T1, T1, 4); m.i(9, T2, T2, -1); m.branch(5, T2, 0, 'rw')
    m.branch(4, 0, 0, 'rec')
    m.label('endchunk'); wait(26, 'c3'); m.i(15, 0, T3, 0x0100); m.i(43, T5, T3, 0)
    m.words.append(0x40800000 | T9 << 16 | 12 << 11)
    m.i(9, S0, S0, 1); m.branch(4, 0, 0, 'chunk')
    m.label('finish'); m.i(9, 0, T2, 0xA0); m.i(9, 0, T1, 0x44); m.words.extend([T2 << 21 | RA << 11 | 9, 0])   # BIOS FlushCache
    m.label('exit'); m.load(RA, SP, 32); m.load(S0, SP, 16); m.load(S1, SP, 20); m.load(S2, SP, 24); m.load(S3, SP, 28)
    m.i(9, 0, V0, 2); m.words.extend([0x03E00008, 0x27BD0028])   # jr ra; addiu sp, 40
    return m.finish()


def verify_exe(exe):
    """The read call and its name string as in stock US v1.1."""
    load = struct.unpack_from('<I', exe, 0x18)[0]
    at = lambda a, n: exe[a - load + 0x800:a - load + 0x800 + n]
    if at(DATAS_NAME, 15) != b'DATA\\DATAS.BIN\x00' or struct.unpack('<3I', at(READ_FILE, 12)) != (0x27BDFFE8, 0xAFBF0010, 0x0C014088):
        raise ValueError('Change Player Character: the game file read (80083F04) differs from the stock executable')


def blocks(stock, meia, place, no_dash=False, data_end=None):
    """Prepend buffer, scratch, state and handler with place(bytes) -> address.
    Returns (handler address, report with 'file' = bytes to append to DATAS.BIN at 'file_offset')."""
    import hashlib
    ram, vram = patch_data(stock, meia, no_dash)
    blob, count = disc_blob(ram, vram)
    end = len(stock) if data_end is None else data_end
    base = end + (-end) % 2048
    buf = place(bytes(CHUNK)); scratch = place(bytes(4 * max(1, max_span_words(vram)))); state = place(bytes(8))
    code = emit_disc(state, buf, scratch, base, count)
    return place(code), {'code_size': len(code), 'code_sha256': hashlib.sha256(code).hexdigest(), 'ram_patch_bytes': len(ram),
                         'vram_patch_bytes': len(vram), 'file_offset': base, 'file_size': len(blob), 'chunks': count,
                         'file': blob, 'state_address': state, 'bank_ram': BANK_RAM, 'runtime_verified': False}
