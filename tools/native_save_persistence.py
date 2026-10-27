"""Project state (switches, variables, Self Switches) in the memory-card save (2026-10-22).

Stock ALUN_CD.EXE (sha256 12f12eaf..., load 0x80020000; PS1 virtual addresses below):
- The game's card file "BASLUS-00553ALUNDRA " is one 0x2000 block: 0x200 header, four 0x76C slot
  records at 0x80122898 + slot*0x76C (each a copy of the 0x758-byte live state 0x801DD2D8),
  0x24 filler + 0x28 bytes, CRC at +0x1FFC (observed on a BizHawk card, 2026-10-22). No proven
  free room for 1 KiB of project state per slot, so that block is left exactly as the game writes it.
- Save: builder 0x8006343C (slot in s2, from 0x800C67F8) calls the write wrapper 0x800600A8
  (a0 port 0/1, a1 file name, a2 block) at 0x80063810.
- Load: the title / load room runs in the boot EXE (SLUS_005.53; ALUN_CD.EXE code is not in RAM
  there, observed 2026-10-22). It leaves the chosen record at the temporary state 0x80010000
  (pointer 0x80029B68; word +4 = slot written by the save builder) and starts ALUN_CD.EXE, whose
  start-up 0x80031CC0 copies it to the live state with jal 0x80083DE0 at 0x80031D0C when
  temp word 0 == 1 (a loaded game). A new game takes the other branch; ALUN_CD.EXE is loaded
  fresh for every game start, so the project state then has the build's initial values.

Injected (original MIPS, not recovered vanilla code):
- SAVE hook at 0x80063810: runs the native write; when it succeeded, reads the companion file
  "BASLUS-00553ALUNDRAP" (or starts empty), puts the block header and, for the saved slot,
  magic + a hash of that slot's native record + the 1 KiB project state, and writes it back
  (creating the 1-block file the first time).
- LOAD hook at 0x80031D0C: runs the native copy, then reads the companion file (card port 1,
  then port 2); when the loaded slot's entry has the magic and the hash of the loaded record
  (bytes 8..0x757), the project state is restored from it. Otherwise (no file, a save made by
  the stock game or overwritten since) the state keeps the build's initial values.
"""
import struct

SAVE_SITE = 0x80063810      # jal 0x800600A8 (native card write wrapper)
LOAD_SITE = 0x80031D0C      # jal 0x80083DE0: a loaded game's state goes from the temporary copy to the live state
STOCK = {SAVE_SITE: (0x0C01802A,), LOAD_SITE: (0x0C020F78, 0x00000000)}
RESTORE = 0x80083DE0; TEMP_POINTER = 0x80029B68
WRITE = 0x800600A8; OPEN = 0x8008428C; READ = 0x8008429C; BWRITE = 0x800842AC; CLOSE = 0x800842BC
RECORDS = 0x80122898; STRIDE = 0x76C; RECORD_BYTES = 0x758; BLOCK = 0x80122698
SELECTED = 0x80122304; PORT = 0x800C67B4
NAME = b'BASLUS-00553ALUNDRAP'
MAGIC = 0x31535041          # 'APS1'
ENTRY = 8 + 1024
SIZE = (0x200 + 4 * ENTRY + 127) & ~127   # bytes read / written (128-byte card sectors)


def verify(exe, load):
    for address, words in STOCK.items():
        off = address - load + 0x800
        if struct.unpack_from('<' + 'I' * len(words), exe, off) != words:
            raise ValueError(f'Save persistence: unexpected stock code at 0x{address:08X}')


def data_block():
    """Companion buffer, then the two card paths (port 0 / port 1)."""
    paths = b''.join((p + NAME + b'\0').ljust(32, b'\0') for p in (b'bu00:', b'bu10:'))
    return bytes(SIZE) + paths


def _jal(m, target):
    m.words.append(0x0C000000 | ((target >> 2) & 0x3FFFFFF)); m.words.append(0)


def emit(state, initial, buffer, paths):
    """(save hook, load hook) code; both start at their own address (relative branches only)."""
    from project_state_runtime import _Mips
    SP, RA, V0, A0, A1, A2, ZERO = 29, 31, 2, 4, 5, 6, 0
    S0, S1, S2, S3, S4, S5 = 16, 17, 18, 19, 20, 21
    T0, T1, T2, T3 = 8, 9, 10, 11

    def copy(m, dst, src, count, tag):     # word copy dst <- src (registers), count bytes
        m.i(9, src, T3, count); m.label(tag)
        m.load(T0, src, 0); m.i(43, dst, T0, 0); m.i(9, src, src, 4); m.i(9, dst, dst, 4)
        m.branch(5, src, T3, tag)

    def hash_record(m, base_reg, tag):     # v0 = djb2 over record bytes 8..0x757 (word 0 differs once loaded); t0-t3
        m.i(9, base_reg, T3, RECORD_BYTES); m.i(9, base_reg, T1, 8); m.i(9, ZERO, V0, 5381)
        m.label(tag); m.load(T0, T1, 0, 36)
        m.r(0, V0, T2, 0, 5); m.r(T2, V0, V0, 0x21); m.r(V0, T0, V0, 0x21)   # v0 = v0*33 + byte
        m.i(9, T1, T1, 1); m.branch(5, T1, T3, tag)

    def read_companion(m, port_reg, tag):   # fills buffer from the companion file, or zeroes it
        m.li(A0, paths); m.branch(4, port_reg, ZERO, tag + 'p'); m.i(9, A0, A0, 32); m.label(tag + 'p')
        m.i(9, ZERO, A1, 1); _jal(m, OPEN); m.r(V0, ZERO, S4, 0x21)
        m.words.append((1 << 26) | (S4 << 21) | (0 << 16)); m.branches.append((len(m.words) - 1, tag + 'none')); m.words.append(0)   # bltz s4
        m.r(S4, ZERO, A0, 0x21); m.li(A1, buffer); m.i(9, ZERO, A2, SIZE); _jal(m, READ)
        m.r(S4, ZERO, A0, 0x21); _jal(m, CLOSE); m.branch(4, ZERO, ZERO, tag + 'end')
        m.label(tag + 'none'); m.li(T1, buffer); m.i(9, T1, T3, SIZE); m.label(tag + 'z')
        m.i(43, T1, ZERO, 0); m.i(9, T1, T1, 4); m.branch(5, T1, T3, tag + 'z')
        m.label(tag + 'end')

    save = _Mips()
    save.i(9, SP, SP, -0x40)
    for n, r in enumerate((RA, S0, S1, S2, S3, S4, S5)): save.i(43, SP, r, 0x10 + 4 * n)
    save.r(A0, ZERO, S0, 0x21); save.r(A1, ZERO, S1, 0x21); save.r(A2, ZERO, S3, 0x21)
    save.r(S2, ZERO, S5, 0x21)                       # slot (builder's s2)
    _jal(save, WRITE); save.i(43, SP, V0, 0x30)
    save.i(9, ZERO, T0, -1); save.branch(4, V0, T0, 'out')
    read_companion(save, S0, 'r')
    save.li(T1, buffer); save.r(S3, ZERO, T2, 0x21); copy(save, T1, T2, 0x200, 'hdr')
    save.li(T1, RECORDS); save.i(9, ZERO, T2, STRIDE)
    save.words.append((S5 << 21) | (T2 << 16) | 0x18); save.words.append((T2 << 11) | 0x12)   # mult; mflo
    save.r(T1, T2, S2, 0x21)
    hash_record(save, S2, 'h')
    save.li(T1, buffer + 0x200); save.i(9, ZERO, T2, ENTRY)
    save.words.append((S5 << 21) | (T2 << 16) | 0x18); save.words.append((T2 << 11) | 0x12)
    save.r(T1, T2, T1, 0x21)
    save.li(T0, MAGIC); save.i(43, T1, T0, 0); save.i(43, T1, V0, 4); save.i(9, T1, T1, 8)
    save.li(T2, state); copy(save, T1, T2, 1024, 'st')
    # write: open (read/write); first time: create one block, then open again
    save.li(A0, paths); save.branch(4, S0, ZERO, 'wp'); save.i(9, A0, A0, 32); save.label('wp')
    save.r(A0, ZERO, S1, 0x21); save.i(9, ZERO, A1, 2); _jal(save, OPEN); save.r(V0, ZERO, S4, 0x21)
    save.words.append((1 << 26) | (S4 << 21)); save.branches.append((len(save.words) - 1, 'make')); save.words.append(0)
    save.branch(4, ZERO, ZERO, 'have')
    save.label('make'); save.r(S1, ZERO, A0, 0x21); save.li(A1, 0x10200); _jal(save, OPEN)
    save.words.append((1 << 26) | (V0 << 21)); save.branches.append((len(save.words) - 1, 'out')); save.words.append(0)
    save.r(V0, ZERO, A0, 0x21); _jal(save, CLOSE)
    save.r(S1, ZERO, A0, 0x21); save.i(9, ZERO, A1, 2); _jal(save, OPEN); save.r(V0, ZERO, S4, 0x21)
    save.words.append((1 << 26) | (S4 << 21)); save.branches.append((len(save.words) - 1, 'out')); save.words.append(0)
    save.label('have'); save.r(S4, ZERO, A0, 0x21); save.li(A1, buffer); save.i(9, ZERO, A2, SIZE); _jal(save, BWRITE)
    save.r(S4, ZERO, A0, 0x21); _jal(save, CLOSE)
    save.label('out'); save.load(V0, SP, 0x30)
    for n, r in enumerate((RA, S0, S1, S2, S3, S4, S5)): save.load(r, SP, 0x10 + 4 * n)
    save.r(RA, 0, 0, 8); save.i(9, SP, SP, 0x40)

    load = _Mips()
    load.i(9, SP, SP, -0x28)
    for n, r in enumerate((RA, S0, S2, S4, S5)): load.i(43, SP, r, 0x10 + 4 * n)
    _jal(load, RESTORE)                                  # the native copy first
    load.li(T0, TEMP_POINTER); load.load(S2, T0, 0)      # temporary copy of the loaded slot record
    load.load(S5, S2, 4); load.i(11, S5, T0, 4); load.branch(4, T0, ZERO, 'done')   # record+4: slot (0..3)
    load.i(9, ZERO, S0, 0); read_companion(load, S0, 'a')
    load.li(T1, buffer + 0x200); load.load(T0, T1, 0); load.li(T3, MAGIC); load.branch(4, T0, T3, 'got')
    load.i(9, ZERO, S0, 1); read_companion(load, S0, 'b')   # not on the card in port 1: try port 2
    load.label('got')
    hash_record(load, S2, 'h')
    load.li(T1, buffer + 0x200); load.i(9, ZERO, T2, ENTRY)
    load.words.append((S5 << 21) | (T2 << 16) | 0x18); load.words.append((T2 << 11) | 0x12)
    load.r(T1, T2, T1, 0x21)
    load.load(T0, T1, 0); load.li(T3, MAGIC); load.branch(5, T0, T3, 'done')
    load.load(T0, T1, 4); load.branch(5, T0, V0, 'done')
    load.i(9, T1, T2, 8); load.li(T1, state); copy(load, T1, T2, 1024, 'st')
    load.label('done')
    for n, r in enumerate((RA, S0, S2, S4, S5)): load.load(r, SP, 0x10 + 4 * n)
    load.r(RA, 0, 0, 8); load.i(9, SP, SP, 0x28)
    return save.finish(), load.finish()


def patch(output, load, save_address, load_address):
    """Point the two native sites at the hooks (stock words checked by verify)."""
    struct.pack_into('<I', output, SAVE_SITE - load + 0x800, 0x0C000000 | ((save_address >> 2) & 0x3FFFFFF))
    struct.pack_into('<I', output, LOAD_SITE - load + 0x800, 0x0C000000 | ((load_address >> 2) & 0x3FFFFFF))
