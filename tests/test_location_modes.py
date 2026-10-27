import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from location_picker import location_ids,OPEN_WORLD_INOA,initial_map

class LocationModeTests(unittest.TestCase):
 def test_initial_maps_match_randomizer_and_post_ship_arrival(self):
  from intro_skip import ARRIVAL
  from editor_open_world import KEPT_INOA_MAPS
  self.assertEqual(initial_map(True),241)
  self.assertEqual(initial_map(False),ARRIVAL['map_id'])
  self.assertEqual(OPEN_WORLD_INOA,frozenset(KEPT_INOA_MAPS))
 def test_mode_initial_selection_loads_correct_map(self):
  from editor_ui import Editor
  from types import SimpleNamespace
  class Value:
   def set(self,value):self.value=value
  editor=Editor.__new__(Editor);editor.map_id=Value();editor.session=object();editor.dirty=True
  editor.database=SimpleNamespace(document={'mod_options':{'open_world':True}})
  loaded=[];editor.load_map=lambda:loaded.append(editor.map_id.value)
  editor.select_initial_map();editor.database.document['mod_options']['open_world']=False
  editor.select_initial_map();self.assertEqual(loaded,['241','163']);self.assertTrue(editor.dirty)

 def test_story_mode_keeps_every_source_map(self):
  self.assertEqual(location_ids(False),list(range(483)))
 def test_open_world_retains_connected_rooms_and_hides_story_variants(self):
  maps=set(location_ids(True))
  self.assertTrue(OPEN_WORLD_INOA<=maps)
  self.assertTrue({332,475,427,10,12}<=maps)
  self.assertTrue({129,162,163,169,242,259,478}.isdisjoint(maps))
