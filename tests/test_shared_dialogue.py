import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_session import EditSession
from map_text import entries,dialogue_entry,edit_dialogue

class SharedDialogueTests(unittest.TestCase):
 def fixture(self):
  data=bytearray(4096)
  struct.pack_into('<I',data,12,2048)
  struct.pack_into('<I',data,16,2500)
  struct.pack_into('<I',data,40,2600)
  for start,text in ((2048,b'Shared line'),(2700,b'Local line!')):
   data[start:start+256]=b'\xff'*256
   struct.pack_into('<h',data,start,256)
   data[start+256:start+257+len(text)]=text+b'\0'
  data[2000:2005]=bytes([13,0,92,7,128])
  s=EditSession(data,verify=False);s.layout=lambda m:(2600,[0,0,0,0,0,0,100])
  return s
 def test_storage_selection_and_exact_undo(self):
  s=self.fixture();before=bytes(s.data)
  self.assertEqual(dialogue_entry(s,0,2000)[2],b'Shared line')
  self.assertEqual(dialogue_entry(s,0,2002)[2],b'Local line!')
  edit_dialogue(s,0,2000,'Changed')
  self.assertEqual(dialogue_entry(s,0,2000)[2],b'Changed    ')
  self.assertEqual(dialogue_entry(s,0,2002)[2],b'Local line!')
  s.undo();self.assertEqual(bytes(s.data),before)
 def test_invalid_text_does_not_mutate(self):
  s=self.fixture();before=bytes(s.data)
  for text in ('X'*12,'zero\0byte','snowman \u2603'):
   with self.assertRaises(ValueError):edit_dialogue(s,0,2000,text)
   self.assertEqual(bytes(s.data),before)
 def test_shared_pointer_cannot_cross_next_section(self):
  s=self.fixture();struct.pack_into('<h',s.data,2048,460)
  self.assertIsNone(dialogue_entry(s,0,2000))
 def test_truncated_table_is_not_read(self):
  s=self.fixture();struct.pack_into('<I',s.data,12,4000)
  self.assertEqual(entries(s,None),[])
