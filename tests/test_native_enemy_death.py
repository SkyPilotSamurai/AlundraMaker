import struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from native_enemy_death import emit_hp_zero_query,verify_native_contract,compile_death_E
from project_state_runtime import inject_private_state,verify_private_state_injection
from project_state_registry import ProjectStateRegistry

class DeathTests(unittest.TestCase):
 def test_query_uses_full_native_word_and_logic_actor(self):
  words=struct.unpack('<7I',emit_hp_zero_query())
  self.assertEqual(words,(0x8ca80014,0,0x2d080001,0xace8002c,0x24020001,0x03e00008,0))
  # An HP halfword of zero is insufficient: a live 65536 value remains false.
  for hp,expected in ((0,1),(1,0),(65536,0),(0xffffffff,0)):
   self.assertEqual(int((hp&0xffffffff)<1),expected)
 def test_native_signatures_reject_changed_hp_width(self):
  p=ROOT/'game/disc/ALUN_CD.EXE'
  if not p.exists():self.skipTest('private stock input unavailable')
  raw=p.read_bytes();self.assertEqual(verify_native_contract(raw)['logic_actor_register'],'a1')
  altered=bytearray(raw);altered[0x800+0x8003ae00-0x80020000+3]^=4
  with self.assertRaises(ValueError):verify_native_contract(altered)
 def test_optional_feature_preserves_default_and_verifies_own_handler(self):
  p=ROOT/'game/disc/ALUN_CD.EXE'
  if not p.exists():self.skipTest('private stock input unavailable')
  raw=p.read_bytes();doc={};reg=ProjectStateRegistry(doc);reg.create('switches','Dead')
  base,b=inject_private_state(raw,doc);same,_=inject_private_state(raw,doc,optional_features=())
  self.assertEqual(base,same);self.assertNotIn('229',b['handlers'])
  new,m=inject_private_state(raw,doc,optional_features=('enemy_hp_zero',))
  self.assertIn(229,verify_private_state_injection(new,m)['opcodes'])
  self.assertEqual(m['optional_features'],['enemy_hp_zero'])
 def test_experimental_per_lifetime_clear_is_opt_in_and_before_handoff(self):
  from project_state_runtime import compile_project_command
  doc={};r=ProjectStateRegistry(doc);l=r.create('switches','Dead')['id'];commands=[{'type':'change_money','amount':7}]
  base=compile_death_E(r,l,commands)
  self.assertEqual(base,compile_death_E(r,l,commands,clear_latch_before_handoff=False))
  clear=compile_project_command({'type':'set_switch','switch_scope':'project','switch_id':l,'value':False},r)
  new=compile_death_E(r,l,commands,clear_latch_before_handoff=True)
  self.assertNotEqual(base,new)
  self.assertTrue(new.endswith(clear+bytes((0x40,4,0,0xff))))
 def test_handoff_after_continuation_and_no_native_AI_replacement(self):
  doc={};r=ProjectStateRegistry(doc);l=r.create('switches','Dead')['id']
  code=compile_death_E(r,l,[{'type':'change_money','amount':7}])
  self.assertIn(bytes((0xe5,4)),code);self.assertTrue(code.endswith(bytes((0x98,7,0,0x40,4,0,0xff))))

if __name__=='__main__':unittest.main()
