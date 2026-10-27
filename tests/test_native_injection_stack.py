import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_injection_stack import protect,STACK_SITE
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'game/disc/ALUN_CD.EXE'

@unittest.skipUnless(INPUT.exists(),'Requires lawful local executable')
class NativeInjectionStackTests(unittest.TestCase):
 def module(self,load=0x8001F000):
  stock=INPUT.read_bytes();old,size=struct.unpack_from('<II',stock,0x18)
  out=bytearray(stock[:0x800]+bytes(old-load)+stock[0x800:])
  struct.pack_into('<II',out,0x18,load,size+old-load)
  return out
 def test_existing_code_and_addresses_remain_exact_except_stack_setup(self):
  source=self.module();out,report=protect(source)
  changed=[i for i,(a,b) in enumerate(zip(source,out)) if a!=b]
  self.assertTrue(changed);self.assertTrue(all(STACK_SITE-0x8001F000+0x800<=i<STACK_SITE-0x8001F000+0x804 for i in changed))
  self.assertEqual(report['stack_top'],0x8001EFF0)
  self.assertLess(report['stack_top'],report['lowest_injected_address'])
 def test_composition_lowers_stack_below_every_new_prefix(self):
  first,_=protect(self.module());second=bytearray(first[:0x800]+bytes(4096)+first[0x800:])
  load,size=struct.unpack_from('<II',second,0x18);struct.pack_into('<II',second,0x18,load-4096,size+4096)
  out,report=protect(second)
  self.assertEqual(report['previous_stack_top'],0x8001EFF0);self.assertEqual(report['stack_top'],0x8001DFF0)
 def test_unknown_native_switch_helper_is_rejected(self):
  source=self.module();source[0x8008427C-0x8001F000+0x800]^=1
  with self.assertRaisesRegex(ValueError,'contract differs'):protect(source)
 def test_excessive_injection_is_rejected_before_touching_output(self):
  source=self.module(0x80017800);before=bytes(source)
  with self.assertRaisesRegex(ValueError,'32KiB'):protect(source)
  self.assertEqual(bytes(source),before)
