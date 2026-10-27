import unittest
from native_breakable_platform_profile import compile_platform,CONTROLLER
from project_state_registry import ProjectStateRegistry
class BreakableProfileTests(unittest.TestCase):
 def test_empty_contents_retains_exact_source_controller(self):
  p,r=compile_platform(ProjectStateRegistry({}))
  self.assertEqual(p,{'C':CONTROLLER});self.assertEqual(r['private_flags_required'],0)
 def test_activation_actions_follow_animation_wait_before_lifecycle3(self):
  p,_=compile_platform(ProjectStateRegistry({}),[{'type':'change_money','amount':7}],leaf_emitter=lambda r:bytes.fromhex('980700'))
  self.assertEqual(p['C'],bytes.fromhex('003e04feff370f1a051c0198070019ff'))
 def test_unsupported_leaf_is_not_silently_dropped(self):
  with self.assertRaises(ValueError):compile_platform(ProjectStateRegistry({}),[{'type':'not_a_verified_command'}])
