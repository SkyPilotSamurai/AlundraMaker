"""Mod option "Instant boot": power on straight into the game.

What New Game does in the stock boot loader SLUS_005.53 (US 1.1):
  title menu (80021F2C) returns 0 -> *(80010000) = 0 (no save handed over),
  shut the title down, LoadExec("cdrom:\\ALUN_CD.EXE;1", sp 801FFF00).
ALUN_CD.EXE reads that word through the pointer at 80029B68 (= 80010000) in
its game-start routine 80031CE0: 1 = continue the save copied after it,
0 = new game (anything else starts a debug map).

Instant boot does the same without the loader:
* SYSTEM.CNF boots ALUN_CD.EXE directly (BOOT = cdrom:\\ALUN_CD.EXE;1; same
  length; TCB/EVENT/STACK unchanged), so the BIOS loads the game at once: no
  1.2 MB loader, opening movie, title graphics or title menu.
* A small entry stub (header PC) clears 80010000/80010004 when the game was
  started by the BIOS (sp is the SYSTEM.CNF stack 801FFFF0; the loader's
  LoadExec gives 801FFF00), then jumps to the original entry 8008DDA0. So a
  disc boot is always a clean New Game, while Game Over -> title -> Continue
  (the loader is unchanged) still hands over its save.
Skip intro is no longer turned on with it (user 2026-10-16); tick it yourself. The
PlayStation BIOS logo still shows. Not verified in BizHawk.

Build & test with Instant boot: a cold boot at turbo speed until the game's
map is running, then normal speed (no main-menu save state).
"""
import struct

SLUS_NAME = 'SLUS_005.53'
# Instant boot (user 2026-10-16): the boot program's main loop (800255B0) plays
# USA_OP, the title, ARAN_OP, the title, forever. The two movie calls
# (jal 80027F5C) are removed, so power-on goes straight to the title menu and
# its timeout shows the title again. Same calls the randomizer removes.
SLUS_MOVIE_CALLS = ((0x800255DC, 0x0C009FD7), (0x80025600, 0x0C009FD7))


def patch_slus_movies(slus):
    """SLUS_005.53 without the opening movies (title menu at power-on)."""
    data = bytearray(slus)
    load = struct.unpack_from('<I', data, 0x18)[0]
    for address, call in SLUS_MOVIE_CALLS:
        at = address - load + 0x800
        word = struct.unpack_from('<I', data, at)[0]
        if word == 0:
            continue
        if word != call:
            raise ValueError(f'Instant boot: unexpected code at {address:08X} in {SLUS_NAME}')
        struct.pack_into('<I', data, at, 0)
    return bytes(data)

CNF_NAME = 'SYSTEM.CNF'
BIOS_STACK = 0x801FFFF0
FLAG = 0x80010000


def patch_system_cnf(text):
    """SYSTEM.CNF booting ALUN_CD.EXE instead of the loader (same length)."""
    old, new = b'cdrom:\\SLUS_005.53;1', b'cdrom:\\ALUN_CD.EXE;1'
    if new in text:
        return bytes(text)
    if text.count(old) != 1:
        raise ValueError('Instant boot: SYSTEM.CNF does not boot SLUS_005.53; this disc is not supported')
    return bytes(text).replace(old, new)


def entry_stub(address, original_entry):
    """Code placed at `address`: clear the save hand-over word on a BIOS boot, then the stock entry."""
    words = [
        0x3C080000 | (BIOS_STACK >> 16),           # lui  t0, 801F
        0x35080000 | (BIOS_STACK & 0xFFFF),        # ori  t0, t0, FFF0
        0x17A80004,                                # bne  sp, t0, +4 (go)
        0x00000000,                                # nop
        0x3C080000 | (FLAG >> 16),                 # lui  t0, 8001
        0xAD000000,                                # sw   zero, 0(t0)
        0xAD000004,                                # sw   zero, 4(t0)
        0x08000000 | ((original_entry >> 2) & 0x3FFFFFF),   # go: j original entry
        0x00000000,
    ]
    return struct.pack('<9I', *words)


ENTRY_STUB_SIZE = 36

LUA = r'''-- Editor Build & test with Instant boot (tools/instant_boot.py).
-- Starts past the PlayStation logo: a save state taken the moment the game
-- program is running. One state is shared by every project and build (map
-- data is still read from the new disc). No speed-up.
local state_path='__STATE__'
local function exists(p) local f=io.open(p,'rb') if f then f:close() return true end return false end
if exists(state_path) then
 savestate.load(state_path); client.speedmode(100); gui.addmessage('Started past the PlayStation logo'); return
end
local domain=nil
for _,n in pairs(memory.getmemorydomainlist()) do
 local size=memory.getmemorydomainsize(n)
 if size==2097152 and (n=='MainRAM' or n=='Main RAM' or n=='RAM' or n=='Main Memory') then domain=n end
end
local function game_running()
 if not domain then return false end
 local word=memory.read_u32_le(0x2BE00,domain)
 return word==0x30420803 or word==0x30420800
end
client.speedmode(100); gui.addmessage('First run: preparing the start past the logo')
for frame=1,__LIMIT__ do
 emu.frameadvance()
 if game_running() then
  savestate.save(state_path); gui.addmessage('Saved: later runs start past the logo'); break
 end
end
'''

TURBO_PERCENT = 1600
FRAME_LIMIT = 6000      # 100 s of game time at most
SETTLE_FRAMES = 30
# Fallback only (no video memory to watch): the state is taken this many
# frames before the game file was first seen in memory (4 s).
MARGIN_FRAMES = 240
# New names: states saved by the older version (during the PlayStation logo)
# are not used any more.
STATE_NAME = 'instant-boot-after-logos.State'
FRAME_NAME = 'instant-boot-after-logos.txt'


def write_script(run_directory, store=None, exe=None):
    """Lua for this launch: load the past-the-logo state of this game program,
    or (first run with this program) boot normally and save it."""
    from pathlib import Path
    import hashlib
    if store is None:
        from bizhawk_main_menu import STORE as store
    store = Path(store); store.mkdir(parents=True, exist_ok=True)
    # One state for every project and build (user choice): made once, then
    # always reused. Delete it to make a fresh one.
    state = store / 'instant-boot-past-logo-2.State'   # renamed 2026-10-11: a fresh state is made once
    lua = lambda p: str(Path(p).resolve()).replace('\\', '/')
    script = Path(run_directory) / 'instant-boot.lua'
    script.write_text(LUA.replace('__LIMIT__', str(FRAME_LIMIT)).replace('__STATE__', lua(state)), encoding='utf-8')
    mode = 'instant boot from the past-the-logo state' if state.is_file() else 'instant boot; saving the past-the-logo state this run'
    return script, {'mode': mode, 'state': str(state)}
