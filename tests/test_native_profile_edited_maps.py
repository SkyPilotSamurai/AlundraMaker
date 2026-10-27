"""Legitimate map edits must not invalidate exact native donor verification."""
import importlib
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from area_map import grid,edit_height
from editor_session import EditSession
from event_editor import instructions

PROFILES=(('floor_switch',1,'C 17'),('ignition_switch',58,'C 1'),
 ('key_door',42,'F 16'),('gate',39,'C 2'),('large_gate',55,'C 11'),
 ('lever',22,'C 1'),('platform_lift',29,'C 29'),
 ('platform_shuttle',52,'C 7'),('statue',2,'C 10'),
 ('wall_switch',40,'C 7'),('rotation_switch',126,'C 1'),
 ('breakable_platform',306,'C 16'),('large_breakable_platform',69,'C 29'),
 ('rolling_rock',67,'C 30'))
INPUT=ROOT/'game/disc/DATA/DATAS.BIN'

@unittest.skipUnless(INPUT.exists(),'Local lawful native input required')
class EditedMapProfileTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.original=INPUT.read_bytes()
 def test_undoable_target_height_edit_keeps_exact_donor_contracts(self):
  session=EditSession(self.original)
  cell=next(c for c in grid(session,163)[2] if c['values'][3]<255)
  edit_height(session,163,cell['x'],cell['y'],1)
  self.assertNotEqual(bytes(session.data),self.original)
  for name,_,_ in PROFILES:
   with self.subTest(profile=name):
    importlib.import_module('native_'+name+'_profile').verify_source(session.data)
  session.undo();self.assertEqual(bytes(session.data),self.original)
 def test_modified_native_donor_program_still_rejected_after_map_edit(self):
  session=EditSession(self.original)
  edit_height(session,163,0,0,1)
  for name,map_id,root in PROFILES:
   with self.subTest(profile=name):
    donor=bytearray(session.data)
    position=next(iter(instructions(session,map_id,root)))[0]
    donor[position]^=1
    with self.assertRaises(ValueError):
     importlib.import_module('native_'+name+'_profile').verify_source(donor)
