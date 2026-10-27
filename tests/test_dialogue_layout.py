import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from dialogue_layout import format_dialogue
from native_text_allocation import append_local_text
from test_native_script_allocation import fixture
from editor_session import EditSession
from map_text import entries

class DialogueLayoutTests(unittest.TestCase):
 def test_long_word_lines_and_page_wait(self):
  self.assertEqual(format_dialogue('w'*61),'w'*20+'\\N'+'w'*20+'\\N'+'w'*20+'\\Aw')
 def test_controls_and_explicit_lines(self):
  self.assertEqual(format_dialogue('Hello world'),'Hello world')
  self.assertEqual(format_dialogue('One\\W2Two\\0100\\Y'),'One\\W2Two\\0100\\Y')
  self.assertEqual(format_dialogue('a\r\nb\nc\nd'),'a\\Nb\\Nc\\Ad')
  self.assertEqual(format_dialogue('a\\Ab'),'a\\Ab')
 def test_malformed_control_or_unencodable_input(self):
  for text in ('x\\','x\\W','x\\Wx','\\0100','a\0b','雪'):
   with self.assertRaises(ValueError):format_dialogue(text)
 def test_native_allocation_emits_wrapped_control_bytes(self):
  data,report=append_local_text(fixture(),2,'w'*21,auto_wrap=True)
  self.assertTrue(report['auto_wrap'])
  self.assertIn(('w'*20+'\\Nw').encode(),[r[2] for r in entries(EditSession(data,verify=False),2)])
  self.assertEqual(format_dialogue('\x80'*40),'\x80'*35+'\\N'+'\x80'*5)
