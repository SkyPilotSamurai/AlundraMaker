import unittest
from native_platform_lift_profile import compile_platform,SOURCE_CONTROLLER,SOURCE_RECORD
class PlatformProfileTests(unittest.TestCase):
 def test_passive_preserves_exact_native_standing_motion_cycle(self):
  code,report=compile_platform({},[])
  self.assertEqual(code['C'],SOURCE_CONTROLLER)
  self.assertEqual(report['foreign_flags'],[])
  self.assertFalse(report['gameplay_verified'])
 def test_actions_only_follow_native_return_before_restart(self):
  code,_=compile_platform({},[{'type':'change_money','amount':7}],leaf_emitter=lambda row:bytes.fromhex('980700'))
  self.assertEqual(code['C'],SOURCE_CONTROLLER[:-2]+bytes.fromhex('980700')+SOURCE_CONTROLLER[-2:])
  self.assertEqual(code['C'][:5],bytes.fromhex('003e04feff'))
 def test_unverified_command_rejected(self):
  with self.assertRaises(ValueError):compile_platform({},[{'type':'mystery'}])
if __name__=='__main__':unittest.main()
