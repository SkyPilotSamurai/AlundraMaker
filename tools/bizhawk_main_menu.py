"""Build & test: start BizHawk at the game's main menu.

The title menu (New Game / Continue) belongs to the boot loader SLUS_005.53,
which no build changes; the edited ALUN_CD.EXE and DATAS are read from the
disc only after New Game / Continue. A save state taken at the main menu is
reusable. Since 2026-10-08 (user choice) ONE main-menu state is used for every
build and run, whatever the disc layout: main-menu.State. (Caution kept for
the record: when DATAS.BIN changes size the later files move on the disc; if a
build ever misbehaves right after New Game, delete main-menu.State and press
F9 at the main menu once to record a fresh one.) An older per-layout state
(menu-<signature>.State) is adopted as main-menu.State when that file is missing.

* main-menu.State exists            -> load it: BizHawk opens at the main menu.
* No state, but the route is known  -> boot at high speed replaying the button
  presses recorded once, then save main-menu.State (used every time after).
* Nothing recorded yet              -> boot normally; press F9 in BizHawk at
  the main menu once. That records the route and the state.

Files: private-inputs/bizhawk-main-menu/route.txt, main-menu.State.
Not verified in BizHawk from here.
"""
import hashlib
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / 'private-inputs' / 'bizhawk-main-menu'
STATE_NAME = 'main-menu.State'
MARK_KEY = 'F9'
TURBO_PERCENT = 1600


def _bin_for(cue):
    import re
    cue = Path(cue)
    names = re.findall(r'^\s*FILE\s+"([^"]+)"', cue.read_text(encoding='utf-8-sig'), flags=re.M | re.I)
    return cue.parent / names[0]


def disc_signature(cue):
    """Hash of every file's (sector, size, name) on the built disc."""
    rows = []
    with open(_bin_for(cue), 'rb') as stream:
        def sector(n):
            stream.seek(n * 2352 + 24)
            return stream.read(2048)

        def walk(lba, size, path, depth=0):
            if depth > 8:
                return
            data = b''.join(sector(lba + i) for i in range((size + 2047) // 2048))
            i = 0
            while i < len(data):
                length = data[i]
                if length == 0:
                    i = (i // 2048 + 1) * 2048
                    continue
                extent = struct.unpack_from('<I', data, i + 2)[0]
                bytes_ = struct.unpack_from('<I', data, i + 10)[0]
                flags = data[i + 25]
                name = data[i + 33:i + 33 + data[i + 32]]
                if name not in (b'\x00', b'\x01'):
                    if flags & 2:
                        walk(extent, bytes_, path + name.decode('latin-1') + '/', depth + 1)
                    else:
                        rows.append((extent, bytes_, path + name.decode('latin-1')))
                i += length

        root = sector(16)[156:156 + 34]
        walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '/')
    return hashlib.sha1(repr(sorted(rows)).encode()).hexdigest()[:16]


def _lua_path(path):
    return str(Path(path).resolve()).replace('\\', '/')


LUA = r'''-- Editor Build & test: open at the main menu (see tools/bizhawk_main_menu.py).
local state_path='__STATE__'
local route_path='__ROUTE__'
local mark_key='__MARK__'
local turbo=__TURBO__
local function exists(p) local f=io.open(p,'rb') if f then f:close() return true end return false end
local function save_route(rows,last)
 local f=io.open(route_path,'w'); if not f then return end
 f:write('end '..last..'\n')
 for frame,keys in pairs(rows) do f:write(frame..' '..keys..'\n') end
 f:close()
end
local function load_route()
 local f=io.open(route_path,'r'); if not f then return nil end
 local rows,last={},nil
 for line in f:lines() do
  local a,b=line:match('^(%S+)%s+(%S+)$')
  if a=='end' then last=tonumber(b) elseif a then rows[tonumber(a)]=b end
 end
 f:close(); return rows,last
end
local function pressed()
 local keys={}
 for name,on in pairs(joypad.get()) do if on==true and name:sub(1,3)=='P1 ' then keys[#keys+1]=name end end
 return table.concat(keys,'|'):gsub(' ','_')
end
if exists(state_path) then
 savestate.load(state_path); gui.addmessage('Main menu (saved state)')
 return
end
local rows,last=load_route()
if rows and last then
 client.speedmode(turbo); gui.addmessage('Going to the main menu…')
 for frame=0,last do
  local keys={}
  if rows[frame] then for name in rows[frame]:gmatch('[^|]+') do keys[name:gsub('_',' ')]=true end end
  joypad.set(keys); emu.frameadvance()
 end
 joypad.set({}); client.speedmode(100)
 savestate.save(state_path); gui.addmessage('Main menu. State saved; every build will start here.')
 return
end
gui.addmessage('Go to the main menu, then press '..mark_key..' to remember it for next time.')
local log={};local frame=0
while true do
 local keys=pressed(); if keys~='' then log[frame]=keys end
 if input.get()[mark_key] then
  save_route(log,frame); savestate.save(state_path)
  gui.addmessage('Main menu remembered. Build & test will start here from now on.')
  return
 end
 frame=frame+1; emu.frameadvance()
end
'''


def write_script(run_directory, cue, store=STORE):
    """Write the Lua for this launch; returns (script path, report)."""
    store = Path(store); store.mkdir(parents=True, exist_ok=True)
    try:
        signature = disc_signature(cue)
    except Exception:
        signature = None    # informational only now
    state = store / STATE_NAME
    if not state.is_file():
        older = sorted(store.glob('menu-*.State'), key=lambda p: p.stat().st_mtime)
        if older:
            import shutil
            shutil.copy2(older[-1], state)
    route = store / 'route.txt'
    mode = 'load state' if state.is_file() else 'replay route, then save state' if route.is_file() else f'record: press {MARK_KEY} at the main menu'
    script = Path(run_directory) / 'main-menu.lua'
    text = (LUA.replace('__STATE__', _lua_path(state)).replace('__ROUTE__', _lua_path(route))
            .replace('__MARK__', MARK_KEY).replace('__TURBO__', str(TURBO_PERCENT)))
    script.write_text(text, encoding='utf-8')
    return script, {'signature': signature, 'state': str(state), 'route': str(route), 'mode': mode}
