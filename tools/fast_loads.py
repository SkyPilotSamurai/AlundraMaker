"""Mod option "Fast loads" (user 2026-10-16): the game loads faster when it
starts up and when it changes rooms. Nothing else changes.

Changing rooms (ALUN_CD.EXE, main loop 8002C598, see WARPS.md):
* 8004B0F0: when the new room has other music and the door makes no sound, the
  old music fades over 120 frames (fade timer 801EFBFC = 0x78) and 8004B1D8
  waits for the whole fade before the room is read; a door with a sound stops
  the music at once instead (8004AD18(0)). Fast loads takes that same path for
  every room change (8004B184 bnez s0 -> b): up to 2 s less black screen.
* 8004B1D8 then waits until every sound effect has finished (8004AFE8) before
  reading the room; Fast loads reads it at once (8004B22C beqz -> nop). The door
  sound keeps playing while the room loads.
Starting up (SLUS_005.53, title 80021F2C, BOOT_AND_ENDING.md):
* after START / CONTINUE the chosen word brightens +4 a frame (24 frames) and the
  screen fades out -2 a frame (128 frames) before the game loads; Fast loads
  uses +16 and -16 (6 and 16 frames, same end values).
The CD reads themselves stay at the console's double speed."""
import struct

# Music fade and screen fades stay as in the game (user 2026-10-17); only the
# wait for sound effects before reading the room goes.
# The music fade (0x8004C964, timer 0x801EFBFC from 120) is heard from 120 to 61;
# at 60 the music is stopped and the last 57 frames are silence. A room change
# (0x8004B1D8) waits for all of them before reading the room; Fast loading
# reads it once the music has stopped (timer <= 60). What you hear is the same.
# The rest of the timer is cleared when the new room's music starts (0x8004AC90
# handles a running fade), else it runs out normally. User 2026-10-17, to test.
EXE_SITES = ((0x8004B208, 0x00000000, 0x2842003D),   # slti v0, v0, 61 (load delay slot was nop)
             (0x8004B20C, 0x1440FFF8, 0x1040FFF8),   # loop while timer > 60 (was: until 0)
             (0x8004B22C, 0x1040FFF9, 0x00000000))   # do not wait for sound effects to end
SLUS_NAME = 'SLUS_005.53'
SLUS_SITES = ()   # title fades stay as in the game (user 2026-10-17)


def _patch(data, sites, name):
    data = bytearray(data)
    load = struct.unpack_from('<I', data, 0x18)[0]
    for address, old, new in sites:
        at = address - load + 0x800
        word = struct.unpack_from('<I', data, at)[0]
        if word == new:
            continue
        if word != old:
            raise ValueError(f'Fast loads: unexpected code at {address:08X} in {name}')
        struct.pack_into('<I', data, at, new)
    return bytes(data)


def patch_exe(exe):
    return _patch(exe, EXE_SITES, 'ALUN_CD.EXE')


def patch_slus(slus):
    return _patch(slus, SLUS_SITES, SLUS_NAME)
