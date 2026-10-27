"""Launch only a completed editor build in an isolated visible BizHawk session."""
import json
import re
import subprocess
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SETTINGS=ROOT/'game/editor-settings.json'
DEFAULT=Path(r'E:\_Emulator\BizHawk-2.9.1-win-x64\EmuHawk.exe')

def isolated_runtime_directory(base,cue,entries,name='bizhawk'):
    """Leave room for BizHawk's ROM-named autosave suffix on legacy Win32."""
    def fits(run):
        directories=[run/'paths'/re.sub(r'[^a-zA-Z0-9_-]','_',str(e.get('System','Global')))/
                     re.sub(r'[^a-zA-Z0-9_-]','_',str(e.get('Type','Other')))
                     for e in entries if e.get('Type')!='Firmware']
        directories=directories or [run/'paths'/'Global'/'Other']
        return max(len(str(p.resolve())) for p in directories)+len(Path(cue).stem)+70<248
    run=Path(base)/name
    if fits(run):return run
    run=ROOT/'game'/'emulator-runs'/name
    if not fits(run):raise ValueError('The exported game filename is too long for isolated BizHawk saves. Choose a shorter output filename before testing.')
    return run

def chosen_emulator(settings=SETTINGS):
    try:
        value=json.loads(Path(settings).read_text(encoding='utf-8')).get('emulator_path')
        if value and Path(value).is_file():return Path(value)
    except (OSError,ValueError,TypeError):pass
    return DEFAULT if DEFAULT.is_file() else None

def save_emulator(path,settings=SETTINGS):
    path=Path(path).resolve()
    if not path.is_file() or path.name.lower()!='emuhawk.exe':
        raise ValueError('Choose BizHawk EmuHawk.exe')
    target=Path(settings);target.parent.mkdir(parents=True,exist_ok=True)
    try:preferences=json.loads(target.read_text(encoding='utf-8'))
    except (OSError,ValueError,TypeError):preferences={}
    if not isinstance(preferences,dict):preferences={}
    preferences['emulator_path']=str(path)
    target.write_text(json.dumps(preferences,indent=2)+'\n',encoding='utf-8')
    return path

PS1_BIOS_SIZE=524288

def ps1_firmware_folder(original,target):
    """A folder holding only the PS1 BIOS files from BizHawk's Firmware folder.
    BizHawk hashes every file in its firmware folder when a game starts, so a
    folder with just these files starts PS1 games faster. None if no PS1 BIOS
    was found (BizHawk then keeps using its own folder)."""
    import shutil
    target=Path(target)
    if target.is_dir() and any(target.iterdir()):return target
    found=[]
    try:
        for path in Path(original).rglob('*'):
            try:
                if not path.is_file() or path.stat().st_size!=PS1_BIOS_SIZE:continue
                with path.open('rb') as stream:head=stream.read(0x10000)
            except OSError:continue
            if b'Sony Computer Entertainment' in head:found.append(path)
    except OSError:return None
    if not found:return None
    target.mkdir(parents=True,exist_ok=True)
    for path in found:
        name=path.name
        if (target/name).exists():name=f'{path.parent.name}-{name}'
        shutil.copy2(path,target/name)
    return target

def prepare_launch(emulator,cue,*,run_root=None,source_config=None):
    """One editor-owned BizHawk settings file, kept between launches so BizHawk
    remembers what it learns (and your changes in it). Saves go to its own
    folder, never to your normal BizHawk saves; your own config is not changed."""
    emulator=Path(emulator).resolve();cue=Path(cue).resolve()
    if not emulator.is_file() or emulator.name.lower()!='emuhawk.exe':raise ValueError('Choose BizHawk EmuHawk.exe')
    _checked_bins(cue)
    source_config=Path(source_config) if source_config else emulator.parent/'config.ini'
    if not source_config.is_file():
        source_config=ROOT/'game/bizhawk-stock-save/stock-config.ini'
    base=Path(run_root or ROOT/'game/editor-emulator-tests')
    configuration=None
    # A test run (run_root given) only ever uses its own folder: it never falls back to,
    # or rewrites, the editor's shared BizHawk settings (that muted them, 2026-10-24).
    shared=() if run_root else (ROOT/'game'/'emulator-runs'/'bizhawk',)
    for run in (base/'bizhawk',)+shared:
        config=run/'config.ini'
        if config.is_file():
            try:configuration=json.loads(config.read_text(encoding='utf-8-sig'));break
            except (OSError,ValueError):configuration=None
    fresh=configuration is None
    if fresh:
        if not source_config.is_file():raise ValueError('BizHawk configuration is missing; open BizHawk once to configure PS1 firmware')
        configuration=json.loads(source_config.read_text(encoding='utf-8-sig'))
        run=isolated_runtime_directory(base,cue,configuration.get('PathEntries',{}).get('Paths',[]))
        config=run/'config.ini'
    run.mkdir(parents=True,exist_ok=True)
    for entry in configuration.get('PathEntries',{}).get('Paths',[]):
        if entry.get('Type')=='Firmware':
            if fresh:
                firmware=Path(entry.get('Path','Firmware'))
                if not firmware.is_absolute():firmware=emulator.parent/firmware
                slim=ps1_firmware_folder(firmware,run/'Firmware')
                entry['Path']=str((slim or firmware).resolve())
            continue
        system=re.sub(r'[^a-zA-Z0-9_-]','_',str(entry.get('System','Global')))
        kind=re.sub(r'[^a-zA-Z0-9_-]','_',str(entry.get('Type','Other')))
        directory=run/'paths'/system/kind;directory.mkdir(parents=True,exist_ok=True)
        entry['Path']=str(directory.resolve())
    configuration.update(SingleInstanceMode=False,AutoLoadLastSaveSlot=False,StartPaused=False,
        StartFullscreen=False,Unthrottled=False,SpeedPercent=100,UpdateAutoCheckEnabled=False)
    if fresh:configuration.update(SaveWindowPosition=False)
    if fresh and run_root:configuration.update(SoundVolume=0)   # only test runs start muted
    for key in ('RecentLua','RecentLuaSession','RecentRoms'):
        if isinstance(configuration.get(key),dict):
            configuration[key]['AutoLoad']=False;configuration[key]['recentlist']=[]
    config.write_text(json.dumps(configuration,indent=2),encoding='utf-8')
    return {'command':[str(emulator),'--gdi','--config='+str(config.resolve()),str(cue)],
            'cwd':str(emulator.parent),'run_directory':str(run.resolve()),'config':str(config.resolve())}

def close_running_bizhawk(run=subprocess.run):
    """Build & test: end every running BizHawk (EmuHawk.exe) first, so the new
    build is the one that boots and the old BIN is no longer held open.
    Returns True when something was closed."""
    import os
    if os.name!='nt':return False
    result=run(['taskkill','/F','/T','/IM','EmuHawk.exe'],capture_output=True,text=True,
               creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return result.returncode==0

# --- Reusing an open BizHawk -------------------------------------------------
# Every launch runs a small Lua "server" in BizHawk. It boots the build, then
# keeps watching live/command.txt: a later Build & test writes the new disc
# there and the same BizHawk opens it (client.openrom keeps the script alive),
# so BizHawk is started once instead of after every build. BizHawk plays a
# copy of the build (live/<name> test <n>.cue), never the project BIN, so the
# next build can be written while the old one is still running.
HEARTBEAT_SECONDS=6     # the server touches live/heartbeat.txt every second
ACK_SECONDS=10

SERVER_LUA=r'''-- Editor Build & test server (tools/editor_emulator.py): boots this build,
-- then opens each later build in this same BizHawk.
local live='__LIVE__'
local first_boot='__BOOT__'
local function read_lines(p) local f=io.open(p,'r') if not f then return nil end local t={} for l in f:lines() do t[#t+1]=l end f:close() return t end
local function write(p,text) local f=io.open(p,'w') if f then f:write(text) f:close() end end
local function boot(path)
 if not path or path=='' then return end
 local chunk=loadfile(path)
 if chunk then chunk() else gui.addmessage('Boot script could not be read') end
 client.speedmode(100)
end
local function command_id() local c=read_lines(live..'/command.txt') return c and c[1] or nil end
local handled=command_id()
local clock=os and os.time or function() return 0 end
boot(first_boot)
local last_beat,frame=-1,0
while true do
 local now=clock()
 if now~=last_beat then write(live..'/heartbeat.txt',tostring(now)..'\n'); last_beat=now end
 frame=frame+1
 if frame%20==0 then
  local c=read_lines(live..'/command.txt')
  if c and c[1] and c[1]~=handled and c[2] then
   handled=c[1]
   local ok=client.openrom(c[2])
   write(live..'/ack.txt',handled..(ok and ' ok' or ' failed')..'\n')
   if ok then gui.addmessage('New build opened'); boot(c[3]) end
  end
 end
 emu.frameadvance()
end
'''

def live_directory(run_root=None):
    return Path(run_root or ROOT/'game/editor-emulator-tests')/'live'

def _lua_path(path):
    return str(Path(path).resolve()).replace('\\','/')

def _checked_bins(cue):
    cue=Path(cue).resolve()
    if not cue.is_file() or cue.suffix.lower()!='.cue':raise ValueError('Build a verified BIN/CUE before testing')
    text=cue.read_text(encoding='utf-8-sig')
    references=re.findall(r'^\s*FILE\s+"([^"]+)"',text,flags=re.M|re.I)
    if not references or any(not (cue.parent/name).is_file() for name in references):raise ValueError('Built CUE is missing its game BIN')
    return cue,text,references

def live_copy(cue,live,stable=True):
    """Copy the build for BizHawk to play; old copies that are no longer open
    are removed. The copy keeps the same name every test ("<build> test"), so
    BizHawk's save states and memory card (named after the disc) carry over
    between builds (user 2026-10-27). If the old copy is still open, a new name
    is used for this one test."""
    import shutil,time
    cue,text,references=_checked_bins(cue)
    live=Path(live);live.mkdir(parents=True,exist_ok=True)
    locked=False
    for old in list(live.glob('*.bin'))+list(live.glob('*.cue')):
        for _ in range(20):   # BizHawk may take a moment to let go after closing
            try:old.unlink();break
            except FileNotFoundError:break
            except OSError:time.sleep(0.1)
        else:locked=True   # the disc BizHawk is playing right now
    stem=f'{cue.stem[:40]} test' if stable and not locked else f'{cue.stem[:40]} test {uuid.uuid4().hex[:6]}'
    for index,name in enumerate(references):
        target=f'{stem}.bin' if len(references)==1 else f'{stem} {index+1}.bin'
        shutil.copyfile(cue.parent/name,live/target)
        text=re.sub(r'(^\s*FILE\s+")'+re.escape(name)+'"',lambda m:m.group(1)+target+'"',text,count=1,flags=re.M|re.I)
    copy=live/f'{stem}.cue';copy.write_text(text,encoding='utf-8')
    return copy

def fresh_cue(cue):
    """A new cue for the same disc, next to it: BizHawk names the memory card
    after the cue, so each test starts with a fresh card without copying the
    disc. Older test cues of this disc are removed."""
    cue,text,references=_checked_bins(cue)
    for old in cue.parent.glob(f'{cue.stem[:40]} test *.cue'):
        try:old.unlink()
        except OSError:pass
    copy=cue.parent/f'{cue.stem[:40]} test {uuid.uuid4().hex[:6]}.cue'
    copy.write_text(text,encoding='utf-8')
    return copy

def bizhawk_server_alive(live,now=None):
    import time
    beat=Path(live)/'heartbeat.txt'
    try:age=(time.time() if now is None else now)-beat.stat().st_mtime
    except OSError:return False
    return age<=HEARTBEAT_SECONDS

def send_to_running_bizhawk(live,cue,boot_script,timeout=ACK_SECONDS,sleep=None):
    """Ask the open BizHawk to play cue; True once it confirms."""
    import os,time
    sleep=sleep or time.sleep
    live=Path(live);ident=uuid.uuid4().hex[:12]
    temp=live/'command.tmp'
    temp.write_text(f'{ident}\n{Path(cue).resolve()}\n{Path(boot_script).resolve() if boot_script else ""}\n',encoding='utf-8')
    for _ in range(20):
        try:os.replace(temp,live/'command.txt');break
        except OSError:sleep(0.05)   # BizHawk is reading the old command
    else:return False
    end=time.time()+timeout
    while time.time()<end:
        try:answer=(live/'ack.txt').read_text(encoding='utf-8').split()
        except OSError:answer=[]
        if answer[:1]==[ident]:return answer[1:2]==['ok']
        sleep(0.1)
    return False

def _boot_script(directory,cue,main_menu,instant_boot):
    if instant_boot:
        # Instant boot build: cold boot at high speed until the game map runs
        # (the main-menu save state would still show the old title).
        from instant_boot import write_script as instant_script
        try:
            from mod_export import read_datas
            exe=read_datas(Path(cue).with_suffix('.bin'),'ALUN_CD.EXE')
        except Exception:
            exe=None
        return instant_script(directory,exe=exe)
    if main_menu:
        # Open at the main menu: the one saved main-menu state, else a
        # fast replay of the recorded route (tools/bizhawk_main_menu.py).
        try:
            from bizhawk_main_menu import write_script
            return write_script(directory,cue)
        except Exception as exc:  # a missing route/state never blocks the test
            return None,{'mode':'normal boot','reason':str(exc)}
    return None,{'mode':'normal boot'}

def launch_built_game(emulator,cue,main_menu=True,instant_boot=False,reuse=True,**options):
    """Build & test (user 2026-10-16): open the build in a fresh BizHawk with a
    plain power-on boot. No save state is loaded and no Lua script runs (the
    old main-menu state / instant-boot / server scripts are no longer used);
    main_menu, instant_boot and reuse are kept only for old callers."""
    live=live_directory(options.get('run_root'))
    _checked_bins(cue)
    close_running_bizhawk()   # first, so the old copy is let go and the same name can be reused
    copy=live_copy(cue,live)
    plan=prepare_launch(emulator,copy,**{k:v for k,v in options.items() if k in ('run_root','source_config')})
    plan['main_menu']={'mode':'normal boot'}
    kwargs={'cwd':plan['cwd']}
    if hasattr(subprocess,'STARTUPINFO'):
        info=subprocess.STARTUPINFO();info.dwFlags|=subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow=1  # SW_SHOWNORMAL: editor's interactive desktop.
        kwargs['startupinfo']=info
    process=subprocess.Popen(plan['command'],**kwargs)
    return dict(plan,pid=process.pid,reused=False)
