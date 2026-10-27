"""Project state follows the game's own death retry (user 2026-10-26).

Stock ALUN_CD.EXE US 1.1: dying and choosing to continue runs 0x80031B50, which counts the retry
(+0x756) and at 0x80031B80 calls 0x80083DE0: the live state 0x801DD2D8 is copied back from the
temporary record 0x80010000 (pointer 0x80029B68). That record is only written when the game starts:
a new game (0x80083E34 from 0x80031E7C) or a loaded save (boot EXE, then 0x80031D0C copies it to
the live state). So every native switch goes back to how it was when the game was started / loaded.

The editor's project state (1 KiB of switches and variables, project_state_runtime) was never part of
that record, so it kept the values from before the death. This keeps a snapshot next to it:
- the snapshot starts as the build's initial values (a new game);
- after a save is loaded (the LOAD_SITE hook of native_save_persistence) it takes the loaded state;
- the retry call at 0x80031B80 runs the native copy, then copies the snapshot back.
Original MIPS, not recovered vanilla code. Not verified in game."""
import struct

RETRY_SITE = 0x80031B80
RETRY_WORDS = (0x0C020F78, 0x00000000)   # jal 0x80083DE0; nop
RESTORE = 0x80083DE0


def verify(exe, load):
    off = RETRY_SITE - load + 0x800
    if struct.unpack_from('<II', exe, off) != RETRY_WORDS:
        raise ValueError('Retry state: unexpected stock code at 0x%08X' % RETRY_SITE)


def emit_call_then_copy(target, src, dst, size=1024):
    """Code: call target, then copy size bytes src -> dst (words), return."""
    from project_state_runtime import _Mips
    m = _Mips(); SP, RA, T0, T1, T2, T3 = 29, 31, 8, 9, 10, 11
    m.i(9, SP, SP, -24); m.i(43, SP, RA, 16)
    m.words.append(0x0C000000 | ((target >> 2) & 0x3FFFFFF)); m.words.append(0)
    m.li(T1, src); m.li(T2, dst); m.i(9, T1, T3, size)
    m.label('copy'); m.load(T0, T1, 0); m.i(43, T2, T0, 0); m.i(9, T1, T1, 4); m.i(9, T2, T2, 4)
    m.branch(5, T1, T3, 'copy')
    m.load(RA, SP, 16); m.i(9, SP, SP, 24); m.words.extend([0x03E00008, 0])
    return m.finish()


def jal(address):
    return 0x0C000000 | ((address >> 2) & 0x3FFFFFF)
