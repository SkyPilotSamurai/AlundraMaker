import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from starting_equipment_ui import StartingEquipmentPanel,source_equipment
from test_starting_equipment import fixture

class PanelTests(unittest.TestCase):
 def test_source_reader_uses_native_flags_and_checks_compatibility(self):
  exe=fixture()
  self.assertEqual(source_equipment(exe),list(range(1,90)))
  exe[0x800+0x80031E40-0x80020000]=0
  with self.assertRaises(ValueError):source_equipment(exe)
 def panel(self):
  p=StartingEquipmentPanel.__new__(StartingEquipmentPanel)
  p.database=SimpleNamespace(document={'mod_options':{'instant_text':True}})
  p.editor=SimpleNamespace(database=p.database)
  p.selected=[2,5,2];p.custom=True
  return p
 def test_list_commit_deduplicates_and_preserves_other_options(self):
  p=self.panel();p.apply()
  self.assertEqual(p.database.document['mod_options'],{'instant_text':True,'starting_equipment':[2,5]})
  p.custom=False;p.apply()
  self.assertEqual(p.database.document['mod_options'],{'instant_text':True})
 def test_changed_mod_cannot_receive_stale_inventory(self):
  p=self.panel();p.editor.database=SimpleNamespace(document={})
  with self.assertRaises(ValueError):p.apply()
  self.assertNotIn('starting_equipment',p.database.document['mod_options'])
