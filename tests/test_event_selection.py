import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from event_selection import covers_map,point_in_box
from area_ui import AreaPanel

class SelectionTests(unittest.TestCase):
 def test_group_stamp_preview_matches_raised_cells_and_flags_edges(self):
  panel=AreaPanel.__new__(AreaPanel);drawn=[]
  panel.canvas=SimpleNamespace(canvasx=lambda x:x,canvasy=lambda y:y,delete=lambda tag:drawn.clear(),create_rectangle=lambda *bounds,**style:drawn.append((bounds,style)))
  panel.mode=SimpleNamespace(get=lambda:'Paint tiles');panel.group_brush={(0,0):1,(1,0):2}
  panel.renderer=SimpleNamespace(surface_at=lambda x,y:(0,0,0,0,'Floor',0))
  panel.grid_width=2;panel.grid_height=1;panel.grid_cells=[{'values':(0,0,0,z)} for z in (1,2)];panel.margin=32;panel.elevation_enabled=lambda:True
  panel.preview_group(SimpleNamespace(x=0,y=0));self.assertEqual([r[0] for r in drawn],[(0,0,24,16),(24,0,48,16)])   # flat group stamp (2026-10-07)
  self.assertTrue(all(style['outline']=='white' for _,style in drawn))
  panel.clear_group_preview();self.assertEqual(drawn,[])

 def test_every_selected_library_tile_gets_white_outline(self):
  panel=AreaPanel.__new__(AreaPanel);drawn=[];deleted=[]
  panel.library=SimpleNamespace(delete=lambda tag:deleted.append(tag),create_rectangle=lambda *bounds,**style:drawn.append((bounds,style)))
  panel.mark_library_tiles([(0,0,1),(24,0,2),(0,16,3)])
  self.assertEqual(len(drawn),3)
  self.assertTrue(all(style['outline']=='white' for bounds,style in drawn))
  self.assertEqual(drawn[-1][0],(0,16,24,32))
  self.assertIn('group_selection',deleted)

 def test_entire_grid_and_oversize_native_bounds(self):
  self.assertTrue(covers_map((0,0,255,255),40,30))
  self.assertTrue(covers_map((0,0,39,29),40,30))
  self.assertFalse(covers_map((1,0,39,29),40,30))
  self.assertFalse(covers_map((0,0,38,29),40,30))
 def test_full_area_does_not_hit_canvas(self):
  panel=AreaPanel.__new__(AreaPanel)
  panel.canvas=SimpleNamespace(canvasx=lambda x:x,canvasy=lambda y:y,bbox=lambda tag:(10,10,170,30),find_overlapping=lambda *b:())
  panel.mode=SimpleNamespace(get=lambda:'Events');panel.label_only_records=[]
  panel.whole_map_events={0};panel.whole_map_graphs=set();panel.markers=[];panel.project_graphs=[];panel.warp_hit_boxes=[]
  panel.info={'events':[{'rectangle':[0,0,255,255]}]};panel.margin=0
  panel.editor=SimpleNamespace(database=SimpleNamespace(document={}),current_map=0)
  self.assertIsNone(panel.record_at(SimpleNamespace(x=20,y=20)))
  self.assertIsNone(panel.record_at(SimpleNamespace(x=300,y=300)))
 def test_hit_box_is_half_open(self):
  self.assertTrue(point_in_box((10,10,20,20),10,10))
  self.assertFalse(point_in_box((10,10,20,20),20,20))
  self.assertFalse(point_in_box(None,10,10))

 def test_dropdown_rebuild_and_open_correct_record(self):
  panel=AreaPanel.__new__(AreaPanel);commands=[];configs=[];opened=[]
  panel.whole_event_menu=SimpleNamespace(delete=lambda *args:commands.clear(),add_command=lambda **kw:commands.append(kw))
  panel.whole_event_button=SimpleNamespace(configure=lambda **kw:configs.append(kw))
  panel.editor=SimpleNamespace(guard=lambda action:action())
  panel.record_list=SimpleNamespace(exists=lambda key:False)
  panel.highlight_record=lambda:None
  panel.edit_selected_process=lambda:opened.append(panel.selected_record)
  panel.update_whole_event_menu([('events',3,'Event 3'),('graphs',7,'Room logic')])
  commands[0]['command']();commands[1]['command']()
  self.assertEqual(opened,[('events',3),('graphs',7)])
  self.assertEqual(configs[-1]['text'],'Whole-map events (2)')
  panel.update_whole_event_menu([])
  self.assertEqual(commands,[]);self.assertEqual(configs[-1]['state'],'disabled')

class RedrawSelectionTests(unittest.TestCase):
 def test_selection_box_drawn_after_crop_move(self):
  # 2026-10-23: closing the event editor redraws records on a cropped map; the white
  # box (not tagged "record") was drawn before the crop move and sat crop px below.
  import inspect
  source=inspect.getsource(AreaPanel._draw_records)
  self.assertLess(source.index('self.canvas.move("record",0,-crop)'),source.index('self.highlight_record()'))
