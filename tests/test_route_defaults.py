import sys,unittest,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from event_graph import new_event_graph,validate_event_graph
from event_movement_compile import compile_movement_command,compile_verified_self_route
from new_event_compile import validate_new_event
from test_event_movement_compile import fixture
class RouteDefaultsTests(unittest.TestCase):
 def test_default_route_is_saved_validated_and_not_silently_ignored(self):
  graph=new_event_graph('event:route',2);route=dict(type='move_actor',target='this_event',mode='route',route=['right','down'],movement_speed=150,blocked_behavior="wait",repeat=True)
  graph['pages'][0]['default_move_route']=route
  self.assertEqual(validate_event_graph(graph)['pages'][0]['default_move_route'],route)
  with self.assertRaisesRegex(ValueError,'controller'):validate_new_event(graph)
  for field,value in [('movement_speed',0),('movement_speed',401),('blocked_behavior','unknown'),('repeat','yes')]:
   bad=dict(route,**{field:value});graph['pages'][0]['default_move_route']=bad
   with self.assertRaises(ValueError):validate_event_graph(graph)
 def test_default_route_waits_until_obstruction_clears(self):
  row=dict(type='move_actor',target='this_event',mode='route',route=['left','up'],moving_animation=1,idle_animation=0,movement_speed=100,blocked_behavior="wait")
  self.assertEqual(compile_movement_command(fixture(),130,row),bytes.fromhex('09081a011e1800 09101a011e1000 1a0000'))
  with self.assertRaisesRegex(ValueError,'per-actor'):compile_movement_command(fixture(),130,dict(row,movement_speed=150))
 def test_only_route_directions_need_animation_frames(self):
  data=fixture();struct.pack_into('<H',data,0x800+1146,65535)
  compile_verified_self_route(data,130,['right'],moving_animation=1,idle_animation=0,skip_impossible=False)
  with self.assertRaises(ValueError):compile_verified_self_route(data,130,['down'],moving_animation=1,idle_animation=0,skip_impossible=False)
if __name__=='__main__':unittest.main()
