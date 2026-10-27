import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from editor_session import EditSession
from portal_records import Portal
from warp_editor import warps,set_warp,move_warp,area_bounds,area_dimensions,DestinationPicker,projected_warp_boxes,warp_at_visual_point
class WarpTests(unittest.TestCase):
 def test_actual_warp_form_left_right_native_flags_preserve_lower_bits(self):
  import tkinter as tk
  from types import SimpleNamespace
  from content_database import ContentDatabase
  from warp_editor import WarpWindow
  try:root=tk.Tk()
  except tk.TclError as exc:self.skipTest('Tk unavailable: '+str(exc))
  session=self.fixture();editor=SimpleNamespace(root=root,session=session,current_map=0,database=ContentDatabase(),dirty=False,status=tk.StringVar(master=root),area=SimpleNamespace(draw_records=lambda:None),guard=lambda work:work())
  windows=[]
  def find(widget):
   for child in widget.winfo_children():
    try:
     if child.cget('text')=='Apply warp':return child
    except tk.TclError:pass
    value=find(child)
    if value:return value
  try:
   for direction,bits in [('Left',0x8000),('Right',0xC000)]:
    window=WarpWindow(editor,0);windows.append(window);root.update()
    for lower in (1,0x2345):
     window.fields[8].set(hex(lower));window.entry_direction.set(direction);find(window.window).invoke();root.update()
     self.assertEqual(warps(session,0)[0][2].flags,bits|lower)
    window.window.destroy()
  finally:root.destroy()

 def test_warp_visual_boxes_match_each_raised_floor_and_hit_test(self):
  p=Portal(1,1,2,1,0,0,0,0,0)
  boxes=projected_warp_boxes(p,[(0,80,0,0),(24,64,1,1),(48,48,2,1),(72,80,3,1)])
  self.assertEqual(boxes,[(24,64,48,80),(48,48,72,64)])
  self.assertEqual(warp_at_visual_point([(2,4,boxes)],50,50),4)
  self.assertIsNone(warp_at_visual_point([(2,4,boxes)],50,70))
  self.assertEqual(warp_at_visual_point([(2,4,boxes),(1,6,[boxes[0]])],25,65),6)

 def test_tile_counts_and_pixel_roundtrip(self):
  p=Portal(2,3,4,5,44,6,7,8,65)
  self.assertEqual(area_dimensions(p),(2,3,3,3))
  self.assertEqual(area_dimensions(p,True),(48,48,72,48))
  self.assertEqual(area_bounds(*area_dimensions(p)),(2,3,4,5))
  self.assertEqual(area_bounds(*area_dimensions(p,True),pixels=True),(2,3,4,5))
  self.assertEqual(area_bounds(2,3,1,1),(2,3,2,3))
 def test_unrepresentable_dimensions_rejected(self):
  for values in ((0,0,0,1),(255,0,2,1),(-1,0,1,1)):
   with self.assertRaises(ValueError):area_bounds(*values)
  with self.assertRaises(ValueError):area_bounds(1,0,24,16,pixels=True)
 def test_destination_click_uses_rendered_surface_and_tile_height(self):
  from types import SimpleNamespace
  picker=DestinationPicker.__new__(DestinationPicker)
  picker.width=2;picker.height=2;picker.margin=80
  picker.cells=[{'values':(0,0,0,z)} for z in (0,1,2,3)]
  picker.point=[0,0,99];marked=[];picker.mark=lambda:marked.append(True)
  picker.canvas=SimpleNamespace(canvasx=lambda x:x,canvasy=lambda y:y)
  picker.renderer=SimpleNamespace(surface_at=lambda x,y:(24,48,1,1,'Floor',0))
  picker.pick(SimpleNamespace(x=25,y=49))
  self.assertEqual(picker.point,[1,1,3]);self.assertEqual(marked,[True])
  self.assertEqual(picker.tile_position(1,1),(24,48))
  picker.renderer.surface_at=lambda x,y:None
  picker.pick(SimpleNamespace(x=25,y=49));self.assertEqual(marked,[True])
 def test_destination_choice_only_updates_draft(self):
  from types import SimpleNamespace
  class Value:
   def __init__(self):self.value=None
   def set(self,value):self.value=value
  session=object();fields=[Value() for _ in range(9)];updates=[]
  owner=SimpleNamespace(session=session,editor=SimpleNamespace(session=session),fields=fields,update_destination=lambda:updates.append(True))
  closed=[];picker=DestinationPicker.__new__(DestinationPicker);picker.owner=owner;picker.point=[4,5,6];picker.window=SimpleNamespace(destroy=lambda:closed.append(True))
  picker.confirm();self.assertEqual([fields[i].value for i in (5,6,7)],['4','5','6']);self.assertEqual(updates,[True]);self.assertEqual(closed,[True])
  owner.editor.session=object()
  with self.assertRaises(ValueError):picker.confirm()

 def fixture(self):
  data=bytearray(7000);start=0x42c
  empty=Portal(0,0,255,255,0,0,0,0,0).encode()
  for i in range(64):data[start+i*12:start+(i+1)*12]=empty
  data[start:start+12]=Portal(2,3,4,5,44,6,7,8,65).encode()
  data[3000:3002]=bytes((12,12))
  s=EditSession(data,verify=False);s.layout=lambda m:(0,(0,3000,6000,0,0,0,0));return s
 def test_delete_warp_moves_later_warps_up_and_undoes(self):
  from warp_editor import delete_warp
  s=self.fixture();start=0x42c
  s.data[start+12:start+24]=Portal(9,9,9,9,55,1,1,0,2).encode()
  s.data[start+24:start+36]=Portal(7,7,7,7,66,1,1,0,2).encode()
  before=bytes(s.data)
  delete_warp(s,0,0)
  self.assertEqual([(i,p.destination_map) for i,_,p in warps(s,0)],[(0,55),(1,66)])
  delete_warp(s,0,1);self.assertEqual([p.destination_map for _,_,p in warps(s,0)],[55])
  with self.assertRaises(ValueError):delete_warp(s,0,5)
  s.undo();s.undo();self.assertEqual(s.data,before)
 def test_destination_and_move_undo(self):
  s=self.fixture();before=bytes(s.data);p=warps(s,0)[0][2];v=list(p.__dict__.values());v[4]=241
  set_warp(s,0,0,v);self.assertEqual(warps(s,0)[0][2].destination_map,241)
  move_warp(s,0,0,1,2);p=warps(s,0)[0][2];self.assertEqual((p.x1,p.y1,p.x2,p.y2),(3,5,5,7))
  s.undo();s.undo();self.assertEqual(s.data,before)
 def test_invalid_destination_preserves_bytes(self):
  s=self.fixture();before=bytes(s.data);v=list(warps(s,0)[0][2].__dict__.values());v[4]=483
  with self.assertRaises(ValueError):set_warp(s,0,0,v)
  self.assertEqual(s.data,before)
 def test_moved_warp_marks_new_floor_with_one_exact_undo(self):
  from area_map import grid
  s=self.fixture();width,height,cells=grid(s,0)
  old=cells[3*width+2]['offset']+1;s.data[old]=0x81
  new=cells[8*width+7]['offset']+1;s.data[new]=0x12
  before=bytes(s.data);p=warps(s,0)[0][2]
  values=list(p.__dict__.values());values[:4]=[7,8,8,9];values[8]=0x4001
  set_warp(s,0,0,values)
  self.assertEqual(s.data[new],0x92)
  self.assertEqual(s.data[old],0x81)
  for y in (8,9):
   for x in (7,8):self.assertTrue(s.data[cells[y*width+x]['offset']+1]&0x80)
  changed=bytes(s.data);self.assertEqual(len(s.undo_stack),1)
  s.undo();self.assertEqual(bytes(s.data),before)
  s.redo();self.assertEqual(bytes(s.data),changed)
