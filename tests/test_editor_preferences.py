import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_preferences import load_preferences,save_preferences,safe_build_name,selected_game_bin,project_build_name,project_output_paths

class EditorPreferencesTests(unittest.TestCase):
 def test_preferences_are_persistent_merged_and_name_is_safe(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'game'/'editor-settings.json'
   save_preferences({'game_bin_path':'C:/Games/Alundra.bin'},path)
   save_preferences({'project_build_name':'Dream Tower'},path)
   self.assertEqual(load_preferences(path),{'game_bin_path':'C:/Games/Alundra.bin','project_build_name':'Dream Tower'})
   self.assertEqual(project_build_name(path),'Dream Tower')
   self.assertEqual(safe_build_name(' Dream Tower.alundramod '),'Dream Tower')
   self.assertEqual(safe_build_name('../Tower: One.bin'),'.._Tower_ One')
 def test_valid_game_bin_is_restored_across_loads(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);game=root/'game.bin';game.write_bytes(b'disc')
   settings=root/'preferences.json';save_preferences({'game_bin_path':str(game)},settings)
   self.assertEqual(selected_game_bin(settings),game)
   game.unlink();self.assertIsNone(selected_game_bin(settings))
 def test_bad_project_name_fails_clearly(self):
  for name in ('','  ','...'):
   with self.assertRaises(ValueError):safe_build_name(name)
 def test_project_name_owns_automatic_mod_and_build_folder(self):
  paths=project_output_paths(' Dream Tower.bin ','C:/Editor')
  self.assertEqual(paths['folder'],Path('C:/Editor/mods/Dream Tower'))
  self.assertEqual(paths['mod'],paths['folder']/'Dream Tower.alundramod')
  self.assertEqual(paths['bin'],Path('C:/Editor/build/Dream Tower.bin'))
  self.assertEqual(paths['cue'],Path('C:/Editor/build/Dream Tower.cue'))

if __name__=='__main__':unittest.main()
