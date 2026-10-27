import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from starting_equipment_ui import equipment_rows

class StartingEquipmentPickerTests(unittest.TestCase):
 def test_native_items_only_and_duplicates_are_not_new_engine_items(self):
  def row(i,kind='weapon',**extra):return dict(id=str(i),name=str(i),kind=kind,source={'item_id':i},**extra)
  first=row(1)
  database=SimpleNamespace(definitions=[row(0),row(90),row(2,clone_of='1'),row(4,'npc'),first,row(1),row(20,'armor'),row(36,'item')])
  result=equipment_rows(database)
  self.assertEqual([i for i,_ in result],[1,20,36]);self.assertIs(result[0][1],first)
