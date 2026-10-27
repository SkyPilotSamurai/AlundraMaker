import sys,struct,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_session import EditSession
from native_event_commands import apply_form,encode_insert,replace_in_place,delete_command


class NativeCommandTests(unittest.TestCase):
 def session(self,raw):return EditSession(raw,verify=False)
 def roots(self,session):
  stack=ExitStack();roots={'F 0':(0,len(session.data),0)}
  stack.enter_context(patch('event_editor.script_roots',return_value=roots))
  stack.enter_context(patch('native_event_commands.script_roots',return_value=roots))
  return stack
 def test_typed_wait_money_switch_edits_undo_exactly(self):
  original=b'\x37\x03\x98\x01\x00\x05\x07\x00\xff';s=self.session(original)
  with self.roots(s):
   apply_form(s,0,'F 0',0,dict(type='wait',frames=9))
   apply_form(s,0,'F 0',2,dict(type='change_money',amount=50))
   apply_form(s,0,'F 0',5,dict(type='set_switch',switch_id=7,native_flag_operand=7,value=False))
  self.assertEqual(bytes(s.data),b'\x37\x09\x98\x32\x00\x06\x07\x00\xff')
  for _ in range(3):s.undo()
  self.assertEqual(bytes(s.data),original)
 def test_warp_edit_preserves_original_effect_and_sound(self):
  raw=struct.pack('<BH5B',0x53,12,1,2,3,4,5)+b'\xff';s=self.session(raw)
  with self.roots(s):apply_form(s,0,'F 0',0,dict(type='warp_player',map_id=51,x=6,y=7,z=8))
  self.assertEqual(bytes(s.data[6:8]),b'\x04\x05')
 def test_deletion_and_insertion_preserve_external_branch_addresses_and_unknown_data(self):
  original=b'\x98\x01\x00\x02\x03\x00\xff';s=self.session(original)
  with self.roots(s):
   delete_command(s,0,'F 0',0)
   self.assertEqual(bytes(s.data[3:]),original[3:])
   replace_in_place(s,0,'F 0',0,encode_insert(dict(type='set_switch',switch_id=9,value=True)))
  self.assertEqual(bytes(s.data),b'\x05\x09\x00'+original[3:])
 def test_unknown_and_terminator_cannot_be_deleted_or_overwritten(self):
  s=self.session(b'\xfe\x12\xff')
  with patch('native_event_commands.instructions',return_value=[(0,0xFE,2),(2,255,1)]):
   for p in (0,2):
    with self.assertRaises(ValueError):delete_command(s,0,'F 0',p)
   with self.assertRaises(ValueError):replace_in_place(s,0,'F 0',0,b'\x37\x01')
  self.assertEqual(bytes(s.data),b'\xfe\x12\xff')

 def test_insert_rejects_branch_entering_middle_of_freed_slot(self):
  s=self.session(b'\x01\x01\x01\x02\xfe\xff\xff')
  roots={'F 0':(0,7,0)}
  with patch('event_editor.script_roots',return_value=roots),patch('native_event_commands.script_roots',return_value=roots):
   with self.assertRaisesRegex(ValueError,'middle'):
    replace_in_place(s,0,'F 0',0,encode_insert(dict(type='change_money',amount=2)))
  self.assertEqual(bytes(s.data[:3]),b'\x01\x01\x01')

if __name__=='__main__':unittest.main()
