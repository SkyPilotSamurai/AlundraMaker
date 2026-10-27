import unittest
from native_large_gate_profile import compile_gate
from project_state_registry import ProjectStateRegistry
class LargeGateProfileTests(unittest.TestCase):
 def test_explicit_switch_binding_keeps_native_motion_and_groundwait(self):
  reg=ProjectStateRegistry({});sid=reg.create('switches','Gate open')['id'];p,r=compile_gate(reg,sid,[])
  self.assertIn(bytes.fromhex('1b00012030001b0000'),p['C']);self.assertIn(bytes.fromhex('16251700'),p['C']);self.assertEqual(r['native_flag_replaced'],'8006');self.assertEqual(r['open_switch_id'],sid)
 def test_user_continuation_after_full_open_before_hold(self):
  reg=ProjectStateRegistry({});sid=reg.create('switches','Gate open')['id'];p,_=compile_gate(reg,sid,[{'type':'change_money','amount':7}],leaf_emitter=lambda r:bytes.fromhex('980700'))
  self.assertIn(bytes.fromhex('2030001b0000be1900bde000980700'),p['C'])
 def test_entry_with_switch_on_is_open_without_replay(self):
  reg=ProjectStateRegistry({});sid=reg.create('switches','Gate open')['id'];p,_=compile_gate(reg,sid,[{'type':'change_money','amount':7}],leaf_emitter=lambda r:bytes.fromhex('980700'))
  c=p['C'];snap=c.index(bytes.fromhex('1b00302030001b0000'))
  self.assertLess(snap,c.index(bytes.fromhex('bd1900')))   # entry check first, silent 48px step
  self.assertEqual(c.count(bytes.fromhex('980700')),1)      # Activate contents only on the real opening
  self.assertEqual(c.count(bytes.fromhex('16251700')),1)    # switch OFF: native fall back to closed
 def test_missing_explicit_control_rejected(self):
  with self.assertRaises((KeyError,ValueError)):compile_gate(ProjectStateRegistry({}),9,[])
if __name__=='__main__':unittest.main()
