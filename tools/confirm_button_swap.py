"""Mod option "Confirm button: Square (JP)" (2026-10-22, docs/2026-10-22-confirm-button-swap.txt).

The US game confirms menus with Cross (pad bit 0x40); the JP game and the remake's
Controls > Confirm Button = JP use Square (0x80). Text advance is already Square in
the US game, and menu cancel is Start/Triangle/L2/R2 (pad & 0x813, remake menu.py),
never Cross, so only the confirm tests change: `andi rt,rs,0x40` -> `andi rt,rs,0x80`.
Gameplay (jump 0x8003253C) is untouched.

Each site is (PS1 virtual address, stock andi word, word of the pad load that feeds
it, offset of that load in words, what it is). Both words are checked before patching,
through the module's own EXE header (no fixed offsets/deltas)."""
import struct

PAD_PRESSED, PAD_REPEAT = 0x801DDA4A, 0x801DDA4E   # held 0x801DDA48 (pad block 0x801DDA38+0x10..)

# ALUN_CD.EXE (US 1.1, load 0x80020000)
ALUN_SITES = (
    (0x8004BCA4, 0x30620040, 0x9463DA4E, -2, 'menu confirm, pad repeat; window task 0x8004BC2C (called by pointer; shop/buy window? unverified)'),
    (0x80051748, 0x30420040, 0x9442DA4A, -2, 'Yes/No window (Ask A Question) 0x80051710, pad pressed'),
    (0x8005869C, 0x30420040, 0x9442DA4E, -2, 'inventory/equipment menu input 0x80058308, pad repeat'),
    (0x8005B554, 0x30620040, 0x9463DA4E, -2, 'save book file list 0x8005AF04, pad repeat'),
)
# SLUS_005.53 (boot EXE: title menu and the History Book load window); s0/a0 = 0x800351D8 pad
SLUS_SITES = (
    (0x80022058, 0x32020040, 0x32020800, -2, 'title menu (NEW GAME/CONTINUE): Start or Cross; Start kept'),
    (0x80024B0C, 0x32020040, 0x1440FFF2, -1, 'History Book 0x80024A90 (book_card) message wait'),
    (0x80024C88, 0x32020040, 0x1440FFEE, -1, 'History Book 0x80024BF8 (book_words) message wait'),
    (0x8002509C, 0x30820040, 0x30822000, -2, 'History Book 0x80024E78 (book_ask) YES/NO load question'),
)


def _offset(exe, address):
    load, size = struct.unpack_from('<II', exe, 0x18)
    if not load <= address < load + size: raise ValueError(f'Confirm button: {address:08X} outside the executable')
    return 0x800 + address - load


def patch(exe, sites, name):
    exe = bytearray(exe); report = []
    for address, stock, context, rel, what in sites:
        at = _offset(exe, address); word = struct.unpack_from('<I', exe, at)[0]
        ctx = struct.unpack_from('<I', exe, at + 4 * rel)[0]
        new = (stock & ~0xFFFF) | 0x80
        if word == new and ctx == context: pass
        elif word != stock or ctx != context:
            raise ValueError(f'Confirm button: unexpected code at {address:08X} in {name}')
        struct.pack_into('<I', exe, at, new)
        report.append(dict(module=name, address=hex(address), stock=hex(stock), new=hex(new), site=what))
    return bytes(exe), report


def patch_alun(exe): return patch(exe, ALUN_SITES, 'ALUN_CD.EXE')
def patch_slus(exe): return patch(exe, SLUS_SITES, 'SLUS_005.53')[0]
