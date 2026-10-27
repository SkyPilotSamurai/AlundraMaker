import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import editor_emulator

class EditorEmulatorTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.base=Path(self.temp.name);self.exe=self.base/'EmuHawk.exe';self.exe.write_bytes(b'fixture')
  self.bin=self.base/'built.bin';self.bin.write_bytes(b'fixture');self.cue=self.base/'built.cue'
  self.cue.write_text('FILE "built.bin" BINARY\n TRACK 01 MODE2/2352\n')
  self.config=self.base/'source-config.ini'
  self.config.write_text(json.dumps({'SoundVolume':87,'PathEntries':{'Paths':[{'System':'PSX','Type':'Save RAM','Path':'user-saves'},{'System':'Global','Type':'Firmware','Path':'Firmware'}]},'RecentLua':{'AutoLoad':True,'recentlist':['old.lua']},'AutoLoadLastSaveSlot':True}))
 def test_config_and_save_paths_are_isolated_source_unchanged(self):
  before=self.config.read_bytes()
  plan=editor_emulator.prepare_launch(self.exe,self.cue,run_root=self.base/'runs',source_config=self.config)
  config=json.loads(Path(plan['config']).read_text())
  self.assertEqual(self.config.read_bytes(),before)
  self.assertEqual(config['SoundVolume'],0)
  self.assertFalse(config['AutoLoadLastSaveSlot']);self.assertFalse(config['RecentLua']['AutoLoad'])
  self.assertTrue(Path(config['PathEntries']['Paths'][0]['Path']).is_relative_to(Path(plan['run_directory'])))
  self.assertEqual(Path(config['PathEntries']['Paths'][1]['Path']),self.base/'Firmware')
  self.assertIn('--gdi',plan['command']);self.assertEqual(plan['command'][-1],str(self.cue))
 def test_missing_output_never_launches(self):
  self.bin.unlink()
  with patch('editor_emulator.subprocess.Popen') as process:
   with self.assertRaisesRegex(ValueError,'missing its game BIN'):
    editor_emulator.launch_built_game(self.exe,self.cue,run_root=self.base/'runs',source_config=self.config)
  process.assert_not_called()
 def test_visible_launch_and_path_preference(self):
  settings=self.base/'preferences.json'
  editor_emulator.save_emulator(self.exe,settings)
  self.assertEqual(editor_emulator.chosen_emulator(settings),self.exe)
  with patch('editor_emulator.subprocess.Popen',return_value=SimpleNamespace(pid=123)) as process:
   plan=editor_emulator.launch_built_game(self.exe,self.cue,run_root=self.base/'runs',source_config=self.config)
  self.assertEqual(plan['pid'],123)
  info=process.call_args.kwargs.get('startupinfo')
  if info is not None:self.assertEqual(info.wShowWindow,1)
 def test_emulator_setting_merges_with_other_persisted_preferences(self):
  settings=self.base/'preferences.json';settings.write_text(json.dumps({'game_bin_path':'game.bin','project_build_name':'Tower'}))
  editor_emulator.save_emulator(self.exe,settings)
  data=json.loads(settings.read_text())
  self.assertEqual(data['game_bin_path'],'game.bin');self.assertEqual(data['project_build_name'],'Tower')

class KeptBizHawkSettingsTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.base=Path(self.temp.name);self.exe=self.base/'EmuHawk.exe';self.exe.write_bytes(b'fixture')
  (self.base/'g.bin').write_bytes(b'disc');self.cue=self.base/'g.cue';self.cue.write_text('FILE "g.bin" BINARY\n')
  firmware=self.base/'Firmware'/'psx';firmware.mkdir(parents=True)
  (firmware/'scph1001.bin').write_bytes((b'\0'*0x108+b'Sony Computer Entertainment Inc.').ljust(524288,b'\0'))
  (firmware/'other.bin').write_bytes(b'\0'*524288);(self.base/'Firmware'/'big.rom').write_bytes(b'x'*1000)
  self.config=self.base/'source-config.ini'
  self.config.write_text(json.dumps({'SoundVolume':87,'PathEntries':{'Paths':[{'System':'PSX','Type':'Save RAM','Path':'s'},{'System':'Global','Type':'Firmware','Path':'Firmware'}]}}))
 def launch(self):
  return editor_emulator.prepare_launch(self.exe,self.cue,run_root=self.base/'runs',source_config=self.config)
 def test_one_settings_file_is_kept_between_launches(self):
  first=self.launch()
  data=json.loads(Path(first['config']).read_text());data['SoundVolume']=40;data['WindowSize']=3;data['AutoLoadLastSaveSlot']=True
  Path(first['config']).write_text(json.dumps(data))   # what BizHawk writes when it closes
  second=self.launch()
  self.assertEqual(first['config'],second['config'])
  kept=json.loads(Path(second['config']).read_text())
  self.assertEqual((kept['SoundVolume'],kept['WindowSize']),(40,3));self.assertFalse(kept['AutoLoadLastSaveSlot'])
 def test_firmware_folder_has_only_the_ps1_bios(self):
  plan=self.launch()
  firmware=Path(json.loads(Path(plan['config']).read_text())['PathEntries']['Paths'][1]['Path'])
  self.assertEqual(firmware,Path(plan['run_directory'])/'Firmware')
  self.assertEqual(sorted(p.name for p in firmware.iterdir()),['scph1001.bin'])
 def test_without_a_ps1_bios_bizhawks_folder_stays(self):
  (self.base/'Firmware'/'psx'/'scph1001.bin').unlink()
  plan=self.launch()
  firmware=Path(json.loads(Path(plan['config']).read_text())['PathEntries']['Paths'][1]['Path'])
  self.assertEqual(firmware,self.base/'Firmware')

class ReuseOpenBizHawkTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.base=Path(self.temp.name);self.exe=self.base/'EmuHawk.exe';self.exe.write_bytes(b'fixture')
  (self.base/'Tower.bin').write_bytes(b'disc');self.cue=self.base/'Tower.cue'
  self.cue.write_text('FILE "Tower.bin" BINARY\n TRACK 01 MODE2/2352\n')
  self.config=self.base/'source-config.ini'
  self.config.write_text(json.dumps({'PathEntries':{'Paths':[{'System':'PSX','Type':'Save RAM','Path':'s'}]}}))
  self.live=editor_emulator.live_directory(self.base/'runs')
 def test_bizhawk_plays_a_renamed_copy_and_old_copies_go(self):
  first=editor_emulator.live_copy(self.cue,self.live)
  second=editor_emulator.live_copy(self.cue,self.live)
  self.assertFalse(first.exists());self.assertNotEqual(first.name,second.name)
  bins=list(self.live.glob('*.bin'));self.assertEqual(len(bins),1)
  self.assertIn(f'FILE "{bins[0].name}" BINARY',second.read_text());self.assertEqual(bins[0].read_bytes(),b'disc')
 def test_heartbeat_age_decides_if_bizhawk_answers(self):
  self.live.mkdir(parents=True)
  self.assertFalse(editor_emulator.bizhawk_server_alive(self.live))
  (self.live/'heartbeat.txt').write_text('1')
  stamp=(self.live/'heartbeat.txt').stat().st_mtime
  self.assertTrue(editor_emulator.bizhawk_server_alive(self.live,now=stamp+2))
  self.assertFalse(editor_emulator.bizhawk_server_alive(self.live,now=stamp+60))
 def answer(self,result='ok'):
  def sleep(_):
   lines=(self.live/'command.txt').read_text().split('\n')
   (self.live/'ack.txt').write_text(f'{lines[0]} {result}\n')
  return sleep
 def test_build_and_test_is_a_plain_boot(self):
  # User 2026-10-16: no save state and no Lua script; any open BizHawk is closed first.
  self.live.mkdir(parents=True);(self.live/'heartbeat.txt').write_text('1')
  with patch('editor_emulator.send_to_running_bizhawk') as send,\
       patch('editor_emulator.subprocess.Popen',return_value=SimpleNamespace(pid=7)) as process,patch('editor_emulator.close_running_bizhawk') as close:
   plan=editor_emulator.launch_built_game(self.exe,self.cue,run_root=self.base/'runs',source_config=self.config)
  send.assert_not_called();close.assert_called_once();self.assertFalse(plan['reused']);self.assertEqual(plan['pid'],7)
  command=process.call_args.args[0]
  self.assertFalse([c for c in command if c.startswith('--lua')])
  self.assertEqual(Path(command[-1]).parent,self.live)
  self.assertEqual(plan['main_menu'],{'mode':'normal boot'})
 def test_failed_open_is_reported(self):
  self.live.mkdir(parents=True)
  self.assertFalse(editor_emulator.send_to_running_bizhawk(self.live,self.cue,None,timeout=2,sleep=self.answer('failed')))
 @unittest.skipUnless(__import__('shutil').which('lua5.4'),'needs lua5.4')
 def test_server_script_boots_then_opens_the_next_build(self):
  import subprocess
  self.live.mkdir(parents=True)
  boot=self.base/'boot.lua';boot.write_text("gui.addmessage('boot') for i=1,3 do emu.frameadvance() end return\n")
  server=self.base/'server.lua'
  server.write_text(editor_emulator.SERVER_LUA.replace('__LIVE__',editor_emulator._lua_path(self.live)).replace('__BOOT__',editor_emulator._lua_path(boot)))
  harness=self.base/'harness.lua'
  harness.write_text(f"""gui={{addmessage=function(m) print('MSG '..m) end}}
client={{speedmode=function() end,openrom=function(p) print('OPEN '..p) return true end}}
emu={{frameadvance=function() coroutine.yield() end}}
local co=coroutine.create(function() dofile('{editor_emulator._lua_path(server)}') end)
for i=1,120 do
 assert(coroutine.resume(co))
 if i==40 then local f=io.open('{editor_emulator._lua_path(self.live)}/command.txt','w') f:write('n1\\nnew.cue\\n\\n') f:close() end
end
""")
  out=subprocess.run(['lua5.4',str(harness)],capture_output=True,text=True,check=True).stdout
  self.assertEqual(out.splitlines()[:3],['MSG boot','OPEN new.cue','MSG New build opened'])
  self.assertEqual((self.live/'ack.txt').read_text(),'n1 ok\n');self.assertTrue((self.live/'heartbeat.txt').exists())

class EditorBuildTestFlow(unittest.TestCase):
 def editor(self):
  from editor_ui import Editor
  editor=Editor.__new__(Editor)
  editor.session=SimpleNamespace();editor.database=SimpleNamespace(to_json=lambda:{},document={})
  editor.build_running=False;editor.root=SimpleNamespace(after=lambda *args:None)
  self.status=[];editor.status=SimpleNamespace(set=self.status.append)
  editor.need=lambda:None;editor.apply_pixels=lambda:None
  editor.keep_open_event_edits=lambda:None;editor.save_on_build=SimpleNamespace(get=lambda:False)
  return editor
 def run_build(self,builder):
  import editor_ui
  class Thread:
   def __init__(self,target,daemon):self.target=target
   def start(self):self.target()
  editor=self.editor()
  with patch('editor_preferences.selected_game_bin',return_value=None),patch('editor_preferences.save_preferences'),patch('editor_ui.filedialog.askopenfilename',return_value='source.bin'),patch('editor_ui.filedialog.asksaveasfilename',return_value='result.bin'),patch('mod_export.build_snapshot',return_value=object()),patch('editor_ui.build_game',builder),patch('editor_ui.threading.Thread',Thread),patch('editor_ui.messagebox.showerror'),patch('editor_emulator.chosen_emulator',return_value=Path('EmuHawk.exe')),patch('editor_emulator.launch_built_game',return_value={'run_directory':'isolated'}) as launch:
   editor.build_modded_game(test=True)
  return launch
 def test_failed_build_never_launches_emulator(self):
  def fail(*args,**kwargs):raise ValueError('Unsupported event')
  launch=self.run_build(fail)
  launch.assert_not_called();self.assertIn('Unsupported event',self.status)
 def test_only_completed_output_cue_is_launched(self):
  launch=self.run_build(lambda *args,**kwargs:('result.bin','validated.cue'))
  launch.assert_called_once_with(Path('EmuHawk.exe'),'validated.cue')
  self.assertTrue(any('built and opened' in text for text in self.status))
 def test_build_uses_saved_disc_and_allows_replacing_named_output(self):
  import editor_ui,editor_preferences
  class Thread:
   def __init__(self,target,daemon):self.target=target
   def start(self):self.target()
  editor=self.editor();editor.project_build_name=SimpleNamespace(get=lambda:'Tower');editor.game_bin_path=SimpleNamespace(set=lambda value:None)
  def build(*args,**kwargs):self.assertIs(kwargs.get('overwrite'),True);return ('tower.bin','tower.cue')
  with patch('editor_preferences.selected_game_bin',return_value=Path('source.bin')),patch('editor_preferences.save_preferences'),patch('editor_ui.filedialog.asksaveasfilename',return_value='tower.bin'),patch('mod_export.build_snapshot',return_value=object()),patch('editor_ui.build_game',side_effect=build),patch('editor_ui.threading.Thread',Thread),patch('editor_ui.messagebox.showerror'):
   editor.build_modded_game(test=False)
  self.assertTrue(any('Game exported' in text for text in self.status))
