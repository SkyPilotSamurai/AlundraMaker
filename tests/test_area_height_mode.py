import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from area_ui import AreaPanel,DEFAULT_HEIGHT_EDIT
from area_map import entity_preview_anchor,entity_tile_selection_anchor,tile_stroke_steps
from entity_preview import EntityPreview

class Value:
 def __init__(self,value):self.value=value
 def get(self):return self.value
 def set(self,value):self.value=value

class AreaHeightModeTests(unittest.TestCase):
 def test_sprite_collision_footprint_comes_from_native_header_offsets(self):
  decoder=EntityPreview.__new__(EntityPreview);decoder.start=0;decoder.end=64;decoder.data=bytearray(64)
  decoder.header=(0,0,0,0,4,0,0,0,0,0,0,0)
  decoder.data[0:4]=(32).to_bytes(4,'little',signed=True)
  decoder.data[56:62]=bytes((254,253,4,5,6,7))
  self.assertEqual(decoder.ground_footprint(0),(-2,-3,4,5,6,7))
 def test_height_edit_is_off_by_default(self):
  self.assertFalse(DEFAULT_HEIGHT_EDIT)
 def test_entity_sprite_and_selection_marker_share_raised_tile_anchor(self):
  area=AreaPanel.__new__(AreaPanel);calls=[]
  class Decoder:
   def representative_frame(self,*args):return Image.new('RGBA',(24,32),(255,255,255,255)),-5,-10
  class Canvas:
   def delete(self,*args):pass
   def create_image(self,*args,**kwargs):calls.append((args,kwargs))
   def create_text(self,*args,**kwargs):pass
   def tag_raise(self,*args):pass
  data=bytearray(32);data[5]=0;data[6]=7
  area.editor=SimpleNamespace(root=None,session=SimpleNamespace(data=data),current_map=2,
   database=SimpleNamespace(document={'event_graphs':[]}))
  area.canvas=Canvas();area.default_visible=lambda kind:True
  area.grid_cells=[{'values':(0,0,0,2)}];area.grid_width=area.grid_height=1;area.margin=32
  area.elevation_enabled=lambda:True;area.sprites=Decoder();area.hits=[]
  area.update_whole_event_menu=lambda entries:None;area.highlight_record=lambda:None;area.populate_record_list=lambda:None
  with patch('area_ui.inspect_map',return_value={'entities':[{'position_raw':(0,0,0),'offset':'0x0'}],'events':[]}),patch('area_ui.warps',return_value=[]),patch('area_ui.cached_preview',return_value=Decoder()),patch('area_ui.ImageTk.PhotoImage',side_effect=lambda image,master=None:image):
   area.draw_records()
  self.assertEqual(calls[0][0][:2],(7,-2))
  self.assertEqual(area.markers,[(12,16,0)])
 def test_entity_feet_follow_ground_tile_height_in_preview(self):
  cells=[{'values':(0,0,0,0)},{'values':(0,0,0,3)},
         {'values':(0,0,0,1)},{'values':(0,0,0,2)}]
  flat=entity_preview_anchor(2,2,0,cells,2,2,48,True)
  raised=entity_preview_anchor(2,2,0,cells,2,2,48,True)
  other_tile=entity_preview_anchor(0,2,0,cells,2,2,48,True)
  self.assertEqual(flat,(36,40,2))
  self.assertEqual(raised[1],flat[1])
  self.assertEqual(other_tile,(12,56,1))
 def test_entity_preview_preserves_existing_z_projection_and_flat_edit_view(self):
  cells=[{'values':(0,0,0,3)}]
  self.assertEqual(entity_preview_anchor(0,0,1,cells,1,1,48,True),(12,8,3))
  self.assertEqual(entity_preview_anchor(0,0,1,cells,1,1,48,False),(12,56,3))
 def test_entity_anchor_uses_native_half_tile_precision_without_snapping(self):
  cells=[{'values':(0,0,0,0)} for _ in range(4)]
  self.assertEqual(entity_preview_anchor(1,1,0,cells,2,2,0),(24,16,0))
 def test_entity_height_clamps_to_ground_instead_of_adding_both_heights(self):
  cells=[{'values':(0,0,0,3)}]
  self.assertEqual(entity_preview_anchor(0,0,1,cells,1,1,48),(12,8,3))
 def test_actor_footprint_samples_all_four_native_ground_corners(self):
  cells=[{'values':(0,0,0,0)} for _ in range(9)]
  cells[8]['values']=(0,0,0,4)
  # Raw XY=2,2 places the actor at 36,24. The collision box crosses into
  # tile (2,2), whose four-corner terrain scan finds height four.
  footprint=(-13,-9,0,26,18,1)
  self.assertEqual(entity_preview_anchor(2,2,0,cells,3,3,48,True,footprint),(36,8,4))
 def test_entity_selection_marker_stays_on_the_visible_ground_tile(self):
  cells=[{'values':(0,0,0,0)},{'values':(0,0,0,2)}]
  self.assertEqual(entity_tile_selection_anchor(2,0,cells,2,1,32),(36,16,2))
  self.assertEqual(entity_tile_selection_anchor(2,0,cells,2,1,32,False),(36,48,2))
 def test_tile_draw_drag_uses_tile_sized_steps_not_mouse_pixels(self):
  self.assertEqual(tile_stroke_steps(2400,1600),100)
  self.assertEqual(tile_stroke_steps(1,1),1)
 def test_height_mode_disallows_event_edits_and_double_click_creation(self):
  area=AreaPanel.__new__(AreaPanel);area.height_edit=Value(True)
  self.assertFalse(area.events_allowed())
  self.assertIsNone(area.double_click(None))
 def test_normal_mode_keeps_event_actions_enabled(self):
  area=AreaPanel.__new__(AreaPanel);area.height_edit=Value(False)
  self.assertTrue(area.events_allowed())
 def test_height_mode_shows_the_map_as_it_looks(self):
  # 2026-10-08: height editing shows the raised map (frozen picture, numbers on every tile).
  area=AreaPanel.__new__(AreaPanel);area.height_edit=Value(True);area.height=Value(True)
  self.assertTrue(area.elevation_enabled())
  self.assertFalse(area.events_allowed())

if __name__=='__main__':unittest.main()
