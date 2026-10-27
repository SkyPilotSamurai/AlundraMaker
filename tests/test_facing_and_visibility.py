import sys, unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from area_ui import AreaPanel
from event_movement_compile import compile_facing_command
from event_graph import new_event_graph,validate_event_graph
from event_graph_ui import command_template
from new_event_compile import _generated_opcodes
from native_event_commands import encode_insert

class FacingVisibilityTests(unittest.TestCase):
 def test_facing_encodings_and_schema(self):
  for direction,raw in [('player','27'),('away_from_player','270a'),('up','0910'),('down','0900'),('left','0908'),('right','0918')]:
   command=dict(command_template('face_actor'),direction=direction)
   graph=new_event_graph('event:1',12,x=1,y=1);graph['pages'][0]['commands']=[command]
   validate_event_graph(graph)
   self.assertEqual(compile_facing_command(command,has_actor=True),bytes.fromhex(raw))
   self.assertEqual(encode_insert(command),bytes.fromhex(raw))
   self.assertTrue(_generated_opcodes(bytes.fromhex(raw)+'\xff'.encode('latin1')))
 def test_unsafe_facing_rejected(self):
  for update in [{'target':'another_actor'},{'direction':'invalid'}]:
   with self.assertRaises(ValueError):compile_facing_command(dict(command_template('face_actor'),**update),has_actor=True)
  with self.assertRaises(ValueError):compile_facing_command(command_template('face_actor'),has_actor=False)
 def test_visibility_separate_and_hiding_clears_selection(self):
  panel=AreaPanel.__new__(AreaPanel)
  panel.show_default_events=SimpleNamespace(get=lambda:False)
  panel.show_default_objects=SimpleNamespace(get=lambda:True)
  self.assertFalse(panel.default_visible('events'));self.assertTrue(panel.default_visible('entities'))
  panel.selected_record=('events',1);panel.record_drag=('events',1)
  panel.editor=SimpleNamespace(session=object(),current_map=12)
  drawn=[];panel.draw_records=lambda:drawn.append(True)
  panel.change_default_visibility()
  self.assertIsNone(panel.selected_record);self.assertIsNone(panel.record_drag);self.assertEqual(drawn,[True])
  panel.selected_record=('graphs',1);panel.change_default_visibility();self.assertEqual(panel.selected_record,('graphs',1))
 def test_hidden_regions_cannot_be_picked(self):
  panel=AreaPanel.__new__(AreaPanel);panel.mode=SimpleNamespace(get=lambda:'Events')
  panel.canvas=SimpleNamespace(canvasx=lambda x:x,canvasy=lambda y:y)
  panel.show_default_events=SimpleNamespace(get=lambda:False)
  panel.markers=[];panel.info={'events':[{'rectangle':[0,0,2,2]}]};panel.margin=0
  panel.project_graphs=[(3,{'region':[0,0,1,1]})];panel.whole_map_graphs=set()
  self.assertEqual(panel.record_at(SimpleNamespace(x=5,y=5)),('graphs',3))
