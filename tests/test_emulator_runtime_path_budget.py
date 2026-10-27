import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_emulator import isolated_runtime_directory

class EmulatorRuntimePathTests(unittest.TestCase):
 entries=[{'System':'PSX','Type':'Save RAM'}]
 def test_deep_fixture_path_gets_compact_owned_save_directory(self):
  with patch('editor_emulator.ROOT',Path('C:/short')):
   run=isolated_runtime_directory(Path('C:/fixtures')/('long-fixture-'*16),'game.cue',self.entries)
  self.assertEqual(run,Path('C:/short/game/emulator-runs/bizhawk'))
 def test_short_custom_runtime_root_is_retained(self):
  run=isolated_runtime_directory(Path('C:/qa'),'game.cue',self.entries)
  self.assertEqual(run,Path('C:/qa/bizhawk'))
 def test_extreme_game_name_rejected_before_any_directory_creation(self):
  with patch('editor_emulator.ROOT',Path('C:/short')):
   with self.assertRaisesRegex(ValueError,'shorter output filename'):
    isolated_runtime_directory(Path('C:/qa'),('g'*220)+'.cue',self.entries)
