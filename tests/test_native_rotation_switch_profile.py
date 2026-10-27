import unittest
from native_rotation_switch_profile import compile_rotation_switch
from project_state_registry import ProjectStateRegistry
class RotationProfileTests(unittest.TestCase):
 def test_native_animation_cycle_and_replaced_foreign_target(self):
  r=ProjectStateRegistry({});identity=r.create('switches','Request')['id'];p,report=compile_rotation_switch(r,identity,[{'type':'change_money','amount':7}],leaf_emitter=lambda row:bytes.fromhex('980700'))
  for direction in (24,0,8,16):self.assertIn(bytes.fromhex('1a011c011a00')+bytes((9,direction))+bytes.fromhex('9807002a'),p['C'])
  self.assertEqual(p['D'][-2:],bytes.fromhex('2bff'));self.assertNotIn(bytes.fromhex('5b0301'),p['C']);self.assertEqual(report['native_self_directions'],[24,0,8,16])
 def test_request_binding_is_exact_project_id(self):
  r=ProjectStateRegistry({});r.create_auto('switches')
  for value in (True,9):
   with self.assertRaises(ValueError):compile_rotation_switch(r,value,[])
 def test_initial_direction_is_explicit_up(self):
  r=ProjectStateRegistry({});identity=r.create_auto('switches')['id'];p,_=compile_rotation_switch(r,identity)
  self.assertEqual(p['A'],bytes.fromhex('0910ff'))
