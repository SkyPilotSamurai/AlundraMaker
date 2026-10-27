import unittest,sys,random,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from texture_codec import unpack_ez,pack_ez
from editor_session import EditSession
class TextureCodecTests(unittest.TestCase):
 def test_roundtrip_patterns(self):
  rng=random.Random(33)
  for data in [bytes([173])*600,bytes(700),b"ABCD"*200,bytes(rng.randrange(256) for _ in range(1000)),bytes(range(256))*3]:
   self.assertEqual(unpack_ez(pack_ez(data),len(data)+1)[0],data)
 def test_bad_matches(self):
  for payload in [b"EZ",b"EZ"+bytes(4)+bytes([173]),b"EZ"+bytes(4)+bytes([173,5,3]),b"EZ"+bytes(4)+bytes([1,173,1,255])]:
   with self.assertRaises(ValueError):unpack_ez(payload,10)
class EditSessionTests(unittest.TestCase):
 def test_overlap_undo_redo_patch_roundtrip(self):
  original=bytes(range(100));s=EditSession(original,verify=False)
  s.replace(5,b"ABCDEF","one");s.replace(7,b"xyz","two")
  expected=bytes(s.data);patch=s.patch()
  fresh=EditSession(original,verify=False);fresh.apply_patch(patch)
  self.assertEqual(bytes(fresh.data),expected)
  s.undo();s.undo();self.assertEqual(bytes(s.data),original)
  s.redo();s.redo();self.assertEqual(bytes(s.data),expected)
 def test_patch_failure_is_atomic(self):
  s=EditSession(bytes(10),verify=False);s.replace(2,b"abc","edit");p=s.patch()
  p["result_sha256"]="wrong";fresh=EditSession(bytes(10),verify=False)
  with self.assertRaises(ValueError):fresh.apply_patch(p)
  self.assertEqual(bytes(fresh.data),bytes(10))
  self.assertFalse(fresh.undo_stack)
 def test_new_edit_clears_redo(self):
  s=EditSession(bytes(5),verify=False);s.replace(0,b"a","a");s.undo();s.replace(1,b"b","b")
  self.assertFalse(s.redo_stack)
 def test_invalid_bounds(self):
  s=EditSession(bytes(4),verify=False)
  with self.assertRaises(ValueError):s.replace(3,b"xx","bad")
class EventOperandTests(unittest.TestCase):
 def fixture(self):
  import struct
  from event_editor import script_roots
  data=bytearray(256)
  struct.pack_into("<12I",data,64,128,0,0,0,0,0,48,52,56,60,64,68)
  struct.pack_into("<h",data,114,32)
  data[144:148]=bytes([0x83,1,2,255])
  s=EditSession(data,verify=False);s.layout=lambda m:(0,(0,0,0,64,0,0,0))
  return s
 def test_same_size_operand_edit_and_undo(self):
  from event_editor import edit_instruction,instructions
  s=self.fixture();before=bytes(s.data)
  edit_instruction(s,0,"A 1",144,[5,3])
  self.assertEqual(bytes(s.data[144:148]),bytes([0x83,5,3,255]))
  s.undo();self.assertEqual(bytes(s.data),before)
 def test_reject_invalid_operand_and_unaligned_offset(self):
  from event_editor import edit_instruction
  s=self.fixture()
  with self.assertRaises(ValueError):edit_instruction(s,0,"A 1",144,[256,3])
  with self.assertRaises(ValueError):edit_instruction(s,0,"A 1",145,[5,3])
 def test_edit_native_sound_effect_command(self):
  from event_editor import edit_instruction
  s=self.fixture();s.data[144:146]=bytes([0x75,0x54])
  edit_instruction(s,0,"A 1",144,[0x31])
  self.assertEqual(bytes(s.data[144:146]),bytes([0x75,0x31]))
  s.undo();self.assertEqual(bytes(s.data[144:146]),bytes([0x75,0x54]))
