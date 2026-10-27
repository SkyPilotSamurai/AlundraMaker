import unittest,sys,struct
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from editor_session import EditSession
from event_records_edit import move_record
class MoveTests(unittest.TestCase):
 def test_entity_move_preserves_programs_height_and_undo(self):
  s=EditSession(bytes(100),verify=False)
  s.data[20:40]=struct.pack("<16B2H",0,0,9,9,1,0,2,6,8,4,129,0,130,0,0,131,0,0)
  before=bytes(s.data)
  rows={"entities":[{"offset":"0x14"}]}
  with patch("event_records_edit.inspect_map",return_value=rows),patch("event_records_edit.grid",return_value=(10,10,[])),patch("editor_session.inspect_map",return_value=rows):
   move_record(s,0,"entities",0,2,-1)
   self.assertEqual(tuple(s.data[27:30]),(10,6,4));self.assertEqual(s.data[30:40],before[30:40])
   s.undo();self.assertEqual(s.data,before)
   with self.assertRaises(ValueError):move_record(s,0,"entities",0,100,0)
   self.assertEqual(s.data,before)
 def test_event_move_preserves_dimensions_and_program(self):
  s=EditSession(bytes(100),verify=False);s.data[20:28]=bytes([1,2,4,5,129,0,0,0]);before=bytes(s.data)
  rows={"events":[{"offset":"0x14"}]}
  with patch("event_records_edit.inspect_map",return_value=rows),patch("event_records_edit.grid",return_value=(10,10,[])),patch("editor_session.inspect_map",return_value=rows):
   move_record(s,0,"events",0,2,1);self.assertEqual(s.data[20:28],bytes([3,3,6,6,129,0,0,0]))
   s.undo();self.assertEqual(s.data,before)
