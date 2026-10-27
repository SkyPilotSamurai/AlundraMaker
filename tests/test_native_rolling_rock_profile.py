import unittest
from native_rolling_rock_profile import compile_platform,CONTROLLER,INITIAL
from project_state_registry import ProjectStateRegistry
class RollingProfileTests(unittest.TestCase):
 def test_empty_actions_preserve_both_exact_native_programs(self):
  p,r=compile_platform(ProjectStateRegistry({}))
  self.assertEqual(p,{'A':INITIAL,'C':CONTROLLER});self.assertEqual(r['private_flags_required'],0)
 def test_actions_run_only_after_second_native_leg(self):
  p,r=compile_platform(ProjectStateRegistry({}),[{'type':'change_money','amount':7}],leaf_emitter=lambda r:bytes.fromhex('980700'))
  self.assertEqual(p['A'],INITIAL);self.assertEqual(p['C'],CONTROLLER[:-2]+bytes.fromhex('1a0098070019ff'))
  self.assertTrue(r['continuation_after_native_second_leg'])
 def test_unknown_authored_action_refused(self):
  with self.assertRaises(ValueError):compile_platform(ProjectStateRegistry({}),[{'type':'not_a_verified_command'}])
