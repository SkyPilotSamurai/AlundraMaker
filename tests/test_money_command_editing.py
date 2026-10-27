import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_session import EditSession
from event_editor import edit_instruction,instructions
class MoneyCommandEditing(unittest.TestCase):
 def fixture(self,op):
  data=bytearray(256)
  struct.pack_into('<12I',data,64,128,0,0,0,0,0,48,52,56,60,64,68)
  struct.pack_into('<h',data,114,32)
  payload=bytes([op,0x34,0x12,255]) if op<0x9B else bytes([op,255])
  data[144:144+len(payload)]=payload
  s=EditSession(data,verify=False);s.layout=lambda m:(0,(0,0,0,64,0,0,0));return s
 def test_unsigned_money_edit_preserves_following_command_and_undo(self):
  for op in (0x98,0x99,0x9A):
   s=self.fixture(op);before=bytes(s.data)
   edit_instruction(s,0,'A 1',144,[65535])
   self.assertEqual(bytes(s.data[144:148]),bytes([op,255,255,255]))
   self.assertEqual(instructions(s,0,'A 1')[-1],(147,255,1))
   s.undo();self.assertEqual(bytes(s.data),before)
 def test_money_range_rejected_without_mutation(self):
  s=self.fixture(0x98);before=bytes(s.data)
  for amount in (-1,65536):
   with self.assertRaises(ValueError):edit_instruction(s,0,'A 1',144,[amount])
   self.assertEqual(bytes(s.data),before)
 def test_warp_toggle_is_single_undo_step(self):
  s=self.fixture(0x9B);before=bytes(s.data)
  edit_instruction(s,0,'A 1',144,[],0x9C)
  self.assertEqual(bytes(s.data[144:146]),bytes([0x9C,255]))
  self.assertEqual(len(s.undo_stack),1)
  s.undo();self.assertEqual(bytes(s.data),before)
 def test_arbitrary_opcode_replacement_rejected(self):
  s=self.fixture(0x98);before=bytes(s.data)
  with self.assertRaises(ValueError):edit_instruction(s,0,'A 1',144,[2],0x99)
  self.assertEqual(bytes(s.data),before)
