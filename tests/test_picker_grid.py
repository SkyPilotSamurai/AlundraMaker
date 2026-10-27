import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from database_picker import grid_geometry,visible_cards,DatabasePicker

class PickerGridTests(unittest.TestCase):
 def test_grid_reflows_and_visible_range_covers_partial_rows(self):
  self.assertEqual(grid_geometry(700,11,164,174),(4,522))
  self.assertEqual(grid_geometry(100,11,164,174),(1,1914))
  self.assertEqual(list(visible_cards(100,4,180,350,174)),list(range(4,20)))
  self.assertEqual(list(visible_cards(11,4,348,350,174)),[8,9,10])

 def test_search_preserves_selected_card_and_filters_all_tabs(self):
  obj=DatabasePicker.__new__(DatabasePicker)
  npc={'id':'npc:0001','name':'Septimus','kind':'npc'}
  other={'id':'npc:0002','name':'Jess','kind':'npc'}
  obj.editor=SimpleNamespace(database={'definitions':[npc,other]})
  obj.canvases={'npc':MagicMock(),'object':MagicMock()};obj.search=SimpleNamespace(get=lambda:'Septimus')
  obj.rows={};obj.selected={'npc':npc['id']};obj.draw=MagicMock()
  obj.refresh()
  self.assertEqual(obj.rows['npc'],[npc]);self.assertEqual(obj.rows['object'],[])
  self.assertEqual(obj.selected['npc'],npc['id']);obj.draw.assert_called_once()

 def test_grid_select_keeps_callback_contract(self):
  obj=DatabasePicker.__new__(DatabasePicker);obj.category=lambda:'npc';obj.selected={'npc':'npc:0001'};obj.finish=MagicMock()
  obj.select();obj.finish.assert_called_once_with('npc:0001')
