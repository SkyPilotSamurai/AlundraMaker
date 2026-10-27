import sys,struct,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import event_editor as native
from native_event_presentation import present,parse_operand,operand_choices,help_for

class Session:
 def __init__(self,raw):self.data=bytearray(raw);self.changes=[]
 def replace(self,offset,raw,name):self.changes.append((offset,raw,name));self.data[offset:offset+len(raw)]=raw

class NativePresentationTests(unittest.TestCase):
 def roots(self,session):return patch.object(native,'script_roots',return_value={'F 0':(0,len(session.data),0)})
 def test_named_map_item_switch_and_numeric_fallback(self):
  for op,value in ((0x53,241),(0x83,36),(5,7)):
   choices=operand_choices(op,0);label=next(k for k,v in choices.items() if v==value)
   self.assertEqual(parse_operand(label,choices),value)
  self.assertEqual(parse_operand('0x8007'),0x8007)
 def test_known_operand_roundtrips(self):
  for op,values in ((2,[3]),(0x31,[7,5]),(0x37,[25]),(0x1A,[2]),(0x73,[4]),(0x74,[3]),(0x78,[3]),(0x6B,[256]),(0x6C,[4]),(0x6D,[9])):
   fmt=native.EDITABLE[op][1];raw=bytes([op])+struct.pack('<'+fmt,*values)+b'\xff';session=Session(raw)
   with self.roots(session):native.edit_instruction(session,0,'F 0',0,values)
   self.assertEqual(bytes(session.data),raw)
 def test_branch_to_middle_rejected_unchanged_external_retained(self):
  session=Session(b'\x02\x04\x00\x37\x01\xff')
  with self.roots(session):
   native.edit_instruction(session,0,'F 0',0,[4]) # preserve old unusual destination
   with self.assertRaises(ValueError):native.edit_instruction(session,0,'F 0',0,[1])
   native.edit_instruction(session,0,'F 0',0,[5])
 def test_unknown_tail_retained_bounded_by_next_root(self):
  session=Session(b'\x37\x01\xfe\x12\xff')
  with patch.object(native,'script_roots',return_value={'F 0':(0,5,0),'F 1':(4,5,0)}):
   self.assertEqual(native.instructions(session,0,'F 0'),[(0,0x37,2),(2,0xFE,2)])
  shown=present(session,0,2,0xFE,2,{0:1,2:2})
  self.assertEqual(shown['group'],'Misc / Unknown');self.assertFalse(shown['editable'])
 def test_semantic_branch_and_wait(self):
  session=Session(b'\x31\x07\x00\x05\x00\x37\x19\xff')
  with patch('native_flag_index.flag_uses',return_value={}):shown=present(session,0,0,0x31,5,{0:1,5:2,7:3})   # 8-byte data has no map table
  self.assertIn('Jess',shown['settings']);self.assertIn('Line 2',shown['settings'])
  self.assertEqual(present(session,0,5,0x37,2,{})['group'],'Flow control')
 def test_dialogue_keeps_order_and_text(self):
  session=Session(b'\x0d\x80\x00')
  with patch('native_event_presentation.dialogue_entry',return_value=(0,99,b'Hello {token}')):
   shown=present(session,0,0,0x0D,native.SIZES[0x0D],{0:1})
  self.assertEqual(shown['action'],'Show text');self.assertIn('Hello {token}',shown['settings'])
 def test_spawn_requires_actual_template(self):
  session=Session(b'\x8a\x00'+bytes(6)+b'\xff')
  with self.roots(session),patch('map_inspector.inspect_map',return_value={'entities':[{}]}):
   native.edit_instruction(session,0,'F 0',0,[0,128,64,16])
   with self.assertRaises(ValueError):native.edit_instruction(session,0,'F 0',0,[1,128,64,16])
 def test_movement_event_help_distinguishes_progress_check_from_move_command(self):
  self.assertIn('does not move',help_for(0x6A))
  self.assertIn('does not issue movement',help_for(0x6B))
  self.assertIn('next branch',help_for(0x6C))
  self.assertIn('Source-reported',help_for(0x8B))

if __name__=='__main__':unittest.main()

