import unittest
from pathlib import Path
from native_flame_pillar_profile import CONTROLLER,compile_pillar
class FlamePillarTests(unittest.TestCase):
 def test_passive_retains_exact_native_cycle(self):
  programs,report=compile_pillar();self.assertEqual(programs['C'],CONTROLLER);self.assertFalse(report['production_enabled'])
 def test_continuation_before_restart_keeps_animation_and_waits(self):
  programs,report=compile_pillar(bytes.fromhex('980100'));self.assertEqual(programs['C'],CONTROLLER[:-2]+bytes.fromhex('98010049ff'))

 @unittest.skipUnless((Path(__file__).resolve().parents[1]/'game/disc/ALUN_CD.EXE').exists(),'Local lawful native input required')
 def test_native_cycle_handlers_reject_changed_dispatch_or_body(self):
  import struct
  from alundra_memory import parse_exe
  from event_vm_compatibility import verify_event_vm_abi
  original=(Path(__file__).resolve().parents[1]/'game/disc/ALUN_CD.EXE').read_bytes();load=parse_exe(original)['load_address'];table=0x8009B814-load+0x800
  verify_event_vm_abi(original,original,{0x49,0xBD,0xBE})
  for opcode in (0x49,0xBD,0xBE):
   address=struct.unpack_from('<I',original,table+opcode*4)[0]
   for offset in (table+opcode*4,address-load+0x800):
    modified=bytearray(original);modified[offset]^=4
    with self.subTest(opcode=opcode,offset=offset),self.assertRaises(ValueError):verify_event_vm_abi(modified,original,{0x49,0xBD,0xBE})
