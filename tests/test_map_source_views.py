import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from area_map import MapRenderer
from map_tile_library import map_source_views
class MapSourceViewsTests(unittest.TestCase):
 def renderer(self):
  renderer=MapRenderer.__new__(MapRenderer);renderer.session=object();renderer.m=1
  renderer.tile=lambda code:Image.new('RGBA',(24,16),(0,0,0,0) if code==65535 else (0,0,0,255) if code==0 else (code*30,40,50,255))
  cells=[dict(x=x,y=0,values=(0,0,0,0,1 if x==0 else 2 if x==4 else 0),walls=[]) for x in range(5)]
  return renderer,cells
 def test_whole_map_matches_native_layout_and_separate_rooms(self):
  renderer,cells=self.renderer()
  with patch('area_map.grid',return_value=(5,1,cells)),patch('map_tile_library.grid',return_value=(5,1,cells)):
   native,_,_=renderer.render(True);views=map_source_views(renderer)
  self.assertEqual(views[0]['image'].tobytes(),native.tobytes())
  self.assertEqual(len(views),3)
  self.assertEqual(views[1]['bounds'],(0,0,24,16));self.assertEqual(views[2]['bounds'],(96,0,120,16))
  self.assertEqual(views[2]['hits'],[(0,0,2)])
  self.assertEqual(views[2]['height_hits'],[(0,0,2,0)])
 def test_height_and_walls_stay_in_place_with_tile_aligned_crop(self):
  renderer,cells=self.renderer();cells=cells[:1];cells[0]['values']=(0,0,0,2,1);cells[0]['walls']=[(10,2,0,0)]
  with patch('area_map.grid',return_value=(1,2,cells)),patch('map_tile_library.grid',return_value=(1,2,cells)):
   native,_,_=renderer.render(True);view=map_source_views(renderer)[0]
  self.assertEqual(view['image'].tobytes(),native.crop(view['bounds']).tobytes())
  self.assertEqual(view['hits'],[(0,0,1),(0,16,2)])
  self.assertEqual(view['height_hits'],[(0,0,1,2),(0,16,2,2)])
 def test_large_connected_map_is_navigable_without_rearranging_tiles(self):
  renderer,_=self.renderer()
  cells=[dict(x=x,y=0,values=(0,0,0,0,1),walls=[]) for x in range(49)]
  with patch('area_map.grid',return_value=(49,1,cells)),patch('map_tile_library.grid',return_value=(49,1,cells)):
   views=map_source_views(renderer)
  self.assertEqual(len(views),4)
  self.assertEqual([v['image'].width for v in views[1:]],[576,576,24])
  self.assertEqual(sum(len(v['hits']) for v in views[1:]),49)
  for view in views[1:]:self.assertEqual(view['image'].tobytes(),views[0]['image'].crop(view['bounds']).tobytes())
 def test_empty_map_still_has_whole_map_without_fake_sections(self):
  renderer,cells=self.renderer();cells=cells[:1];cells[0]['values']=(0,0,0,0,65535)
  with patch('area_map.grid',return_value=(1,1,cells)),patch('map_tile_library.grid',return_value=(1,1,cells)):
   views=map_source_views(renderer)
  self.assertEqual(len(views),1);self.assertEqual(views[0]['label'],'Whole map');self.assertEqual(views[0]['hits'],[])
if __name__=='__main__':unittest.main()
