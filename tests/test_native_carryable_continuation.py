import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_carryable_continuation import emit,inject,verify_source,E2
from test_project_state_runtime import execute_handler
INPUT=Path(__file__).resolve().parents[1]/'game/disc/ALUN_CD.EXE'
class CarryContinuationTests(unittest.TestCase):
 def test_completed_animation_and_impact_only_advance_without_mutating_actor(self):
  owner=0x801AF050
  for animation,finished,impact in ((2,1,0),(0,0,4)):
   state={owner+0x10:3,owner+0x88:animation,owner+0xAC:finished,owner+0x184:impact,owner+0x6C:0x3310}
   result,_,after=execute_handler(emit(),bytes((0xE8,)),state,owner=owner)
   self.assertEqual(result,1);self.assertEqual(after,state)
 def test_living_or_invalid_owner_does_not_start_native_destruction(self):
  for owner,status in ((0x801AF050,2),(0x80010000,3),(0x801B6BF8,3)):
   state={owner+0x10:status,owner+0x88:2,owner+0xAC:1,owner+0x184:4}
   result,_,after=execute_handler(emit(),bytes((0xE8,)),state,owner=owner)
   self.assertEqual(result,0);self.assertEqual(after,state)
 def test_real_native_callback_is_called_instead_of_substituting_hp_or_f(self):
  words=struct.unpack('<'+str(len(emit())//4)+'I',emit())
  self.assertEqual(sum(w==0x0C000000|(E2>>2&0x3ffffff) for w in words),1)
  self.assertNotIn(0x8CA80014,words)
  self.assertIn(0x00A02021,words) # logic owner A1 passed as native callback A0
 @unittest.skipUnless(INPUT.exists(),'Lawful native input required')
 def test_exact_controller_source_and_protected_optional_dispatch(self):
  stock=INPUT.read_bytes();contract=verify_source(stock);patched,report=inject(stock)
  self.assertEqual(contract['native_fields']['animation']['width'],32)
  self.assertLess(report['native_stack']['stack_top'],report['handler_address'])
  load=struct.unpack_from('<I',patched,0x18)[0]
  self.assertEqual(struct.unpack_from('<I',patched,0x8009B814+0xE8*4-load+0x800)[0],report['handler_address'])
  self.assertFalse(report['runtime_verified'])
  bad=bytearray(stock);bad[E2-0x80020000+0x800]^=1
  with self.assertRaises(ValueError):verify_source(bad)
 @unittest.skipUnless(INPUT.exists(),'Lawful native input required')
 def test_optional_feature_is_explicit_and_native_controller_stays_verified(self):
  from project_state_runtime import inject_private_state,verify_private_state_injection
  from event_vm_compatibility import verify_event_vm_abi
  import hashlib
  stock=INPUT.read_bytes();plain,manifest=inject_private_state(stock,{})
  self.assertNotIn('232',manifest['handlers'])
  patched,manifest=inject_private_state(stock,{},optional_features=('carryable_e2',))
  self.assertIn('232',manifest['handlers']);verify_event_vm_abi(patched,stock,{0xE8},manifest)
  with self.assertRaises(ValueError):verify_event_vm_abi(patched,stock,{0xE8})
  bad=bytearray(patched);bad[E2-manifest['new_load']+0x800]^=1
  manifest['result_sha256']=hashlib.sha256(bad).hexdigest()
  with self.assertRaises(ValueError):verify_private_state_injection(bad,manifest)
