import unittest
from native_small_rolling_rock_profile import compile_controller,INITIAL,CONTROLLER
from project_state_registry import ProjectStateRegistry
class SmallRollingTests(unittest.TestCase):
 def test_explicit_target_replaces_only_area_and_room_completion(self):
  p,r=compile_controller(ProjectStateRegistry({}),{'x':8,'y':9,'height':1},[{'type':'change_money','amount':7}],leaf_emitter=lambda r:bytes.fromhex('980700'))
  self.assertEqual(p['A'],INITIAL)
  self.assertEqual(p['C'],bytes.fromhex('006e04feff1a00078008080909010104f1ff58eeff0a00eeffeeff0098070019ff'))
  self.assertFalse(r['source_room_flag032F_reused'])
 def test_unconfigured_or_outside_target_rejected(self):
  for target in [None,{}, {'x':8,'y':9}, {'x':128,'y':9,'height':1}, {'x':8,'y':9,'height':True}]:
   with self.assertRaises(ValueError):compile_controller(ProjectStateRegistry({}),target)
 def test_unobserved_direction_rejected(self):
  with self.assertRaisesRegex(ValueError,'Up'):compile_controller(ProjectStateRegistry({}),{'x':8,'y':9,'height':1},facing='right')
 def test_unknown_action_rejected(self):
  with self.assertRaises(ValueError):compile_controller(ProjectStateRegistry({}),{'x':8,'y':9,'height':1},[{'type':'unknown'}])
