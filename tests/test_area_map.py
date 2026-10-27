import unittest,sys,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from area_map import grid,edit_cell,edit_wall,edit_height,tile_at_canvas,first_visible_row,map_y_to_view,view_y_to_map
from editor_session import EditSession
class AreaTests(unittest.TestCase):
 def fixture(self):
  data=bytearray(4096);data[64:68]=bytes([2,2,2,2])
  first=64+4+1536
  for i in range(4):struct.pack_into("<4BHh",data,first+i*8,1,2,3,4,5,-1)
  struct.pack_into("<h",data,first+6,0)
  struct.pack_into("<bBH",data,first+32,1,1,7)
  s=EditSession(data,verify=False);s.layout=lambda m:(0,(0,64,4000,0,0,0,0))
  return s
 def test_tile_change_preserves_wall_pointer_and_neighbours(self):
  s=self.fixture();before=bytes(s.data);w,h,c=grid(s,0);o=c[0]["offset"]
  edit_cell(s,0,0,0,[9,8,7,6,0x5123])
  self.assertEqual(s.data[o+6:],before[o+6:])
  self.assertEqual(s.data[:o],before[:o])
  s.undo();self.assertEqual(s.data,before)
 def test_wall_change_and_undo(self):
  s=self.fixture();before=bytes(s.data)
  edit_wall(s,0,0,0,0,999)
  self.assertEqual(grid(s,0)[2][0]["walls"][0][1],999)
  s.undo();self.assertEqual(s.data,before)
 def test_invalid_cell_and_height(self):
  s=self.fixture()
  with self.assertRaises(ValueError):edit_cell(s,0,2,0,[1,2,3,4,5])
  with self.assertRaises(ValueError):edit_cell(s,0,0,0,[1,2,3,256,5])

 def test_invalid_wall_index_does_not_modify_data(self):
  s=self.fixture();before=bytes(s.data)
  for index in (-1,1):
   with self.assertRaises(ValueError):edit_wall(s,0,0,0,index,999)
  self.assertEqual(s.data,before)
  self.assertFalse(s.undo_stack)

 def test_height_click_changes_one_step_and_undo_restores_tile(self):
  s=self.fixture();before=bytes(s.data);self.assertEqual(edit_height(s,0,0,0,1),5)
  self.assertEqual(grid(s,0)[2][0]["values"][3],5)
  self.assertEqual(len(s.undo_stack),1);s.undo();self.assertEqual(s.data,before)
  self.assertEqual(edit_height(s,0,0,0,-1),3)

 def test_height_click_with_the_views_grid_needs_no_map_reread(self):
  s=self.fixture();w,_,cells=grid(s,0)
  from unittest.mock import patch
  with patch('area_map.grid',side_effect=AssertionError('re-read')):
   self.assertEqual(edit_height(s,0,0,0,1,cells=cells,width=w),5)
   self.assertEqual(edit_height(s,0,0,0,1,cells=cells,width=w),6)   # reads the byte, not the stale grid
  self.assertEqual(grid(s,0)[2][0]["values"][3],6);self.assertEqual(len(s.undo_stack),2)

 def test_height_bounds_and_direction_validation_do_not_edit(self):
  s=self.fixture();before=bytes(s.data)
  for delta in (0,2,-1):
   if delta==-1:
    s.data[64+4+256*6+3]=0
   with self.assertRaises(ValueError):edit_height(s,0,0,0,delta)
  self.assertFalse(s.undo_stack)

 def test_height_target_follows_visible_wall_to_its_tile(self):
  class Renderer:
   def surface_at(self,x,y):return (24,32,7,9,"Wall 0",123)
  self.assertEqual(tile_at_canvas(Renderer(),30,38,{}),(7,9))

 def test_height_target_uses_rendered_cell_fallback_and_rejects_outside(self):
  class Renderer:
   def surface_at(self,x,y):return None
  hits={(2,3):(48,48,5,6)}
  self.assertEqual(tile_at_canvas(Renderer(),50,50,hits),(5,6))
  self.assertIsNone(tile_at_canvas(Renderer(),500,500,hits))

 def test_surface_pick_sees_wall_through_transparent_floor(self):
  from area_map import MapRenderer
  from PIL import Image
  r=MapRenderer.__new__(MapRenderer)
  r.surface_hits={(0,0):[(0,0,0,0,"Wall 0",7),(0,0,0,1,"Floor",8)]}
  wall=Image.new("RGBA",(24,16),(255,0,0,255));floor=Image.new("RGBA",(24,16),(0,0,0,0));floor.putpixel((3,4),(0,255,0,255))
  r.tile=lambda code:wall if code==7 else floor
  self.assertEqual(r.surface_at(1,1)[4],"Wall 0")
  self.assertEqual(r.surface_at(3,4)[4],"Floor")
  self.assertIsNone(r.surface_at(30,1))
 def test_map_view_can_crop_blank_elevation_headroom(self):
  from PIL import Image
  image=Image.new('RGBA',(32,48),(31,34,40,255))
  for y in range(13,48):image.putpixel((15,y),(180,120,60,255))
  self.assertEqual(first_visible_row(image),13)
  self.assertEqual(first_visible_row(Image.new('RGBA',(8,8),(31,34,40,255))),0)
 def test_tile_selection_maps_correctly_after_top_crop(self):
  for crop in (0,16,160,480):
   source_y=736
   visible_y=map_y_to_view(source_y,crop)
   self.assertEqual(view_y_to_map(visible_y,crop),source_y)
