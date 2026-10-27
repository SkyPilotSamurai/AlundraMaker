import sys,unittest,struct,io,wave
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from sound_database import encode_sound,decode_adpcm,SoundLibrary
from event_logic_compile import compile_logic
from native_event_commands import encode_insert,command_form
from event_graph import new_event_graph,validate_event_graph
from editor_session import EditSession
from event_export import prepare_native_event_export
from event_editor import instructions
from map_inspector import inspect_map
from test_native_script_allocation import fixture
class SoundDatabaseTests(unittest.TestCase):
 def test_ids_and_native_command_encoding(self):
  for value in (0,1,255):self.assertEqual(encode_sound(value),bytes((0xBD,value,0)))   # PlaySound (2026-10-23)
  for value in (-1,256,True,'1'):
   with self.assertRaises(ValueError):encode_sound(value)
 def test_adpcm_signed_nibbles_and_end_flag(self):
  self.assertEqual(decode_adpcm(bytes([12,1])+b'\x87'*14+bytes([12,0])+b'\x11'*14),[7,-8]*14)
  self.assertEqual(decode_adpcm(bytes(16)),[0]*28)
  for bad in (b'\x00',bytes([0x5c,0])+bytes(14),bytes([0x0f,0])+bytes(14)):
   with self.assertRaises(ValueError):decode_adpcm(bad)
 def test_graph_and_compiler_preserve_sound_order(self):
  row=new_event_graph('event:test',2);row['pages'][0]['commands']=[dict(type='play_sound',sound_id=7),dict(type='wait',frames=2),dict(type='play_sound',sound_id=9)]
  validate_event_graph(row);self.assertEqual(compile_logic(row['pages'][0]['commands']),bytes.fromhex('bd07003702bd0900'))
  row['pages'][0]['commands'][0]['sound_id']=256
  with self.assertRaises(ValueError):validate_event_graph(row)
 def test_existing_native_form_and_insert(self):
  self.assertEqual(command_form(type('S',(),{'data':b'\x75\x09'})(),0,0,0x75),dict(type='stop_sound',sound_id=9))   # 75 = StopSound
  self.assertEqual(encode_insert(dict(type='stop_sound',sound_id=9)),bytes((0x75,9)))
  self.assertEqual(encode_insert(dict(type='play_sound',sound_id=9)),bytes((0xBD,9,0)))
 def test_sound_event_reaches_new_native_process(self):
  session=EditSession(fixture(),verify=False);row=new_event_graph('event:sound',2,x=3,y=4)
  row['pages'][0].update(trigger='touch',commands=[dict(type='play_sound',sound_id=7)])
  session.content_database={'definitions':[],'event_graphs':[row]};original=bytes(session.data)
  with patch('area_map.grid',return_value=(8,8,[{'values':[0,0,0,1]}]*64)),patch('event_vm_compatibility.sprite_callbacks',return_value=[('A',0),('C',0),('D',0),('E',0),('F',0)]):
   result=prepare_native_event_export(session)
  event=inspect_map(result.data,2)['events'][-1];ops=instructions(result,2,f"B {event['bank_b_index']}")
  self.assertEqual([(op,size) for off,op,size in ops],[(0xBD,3),(255,1)])
  self.assertEqual(result.data[ops[0][0]+1],7);self.assertEqual(bytes(session.data),original)
 def test_selected_input_table_requires_unique_signature(self):
  with self.assertRaises(ValueError):SoundLibrary(bytes(0x4000),b'PS-X EXE'+bytes(100))
if __name__=='__main__':unittest.main()
