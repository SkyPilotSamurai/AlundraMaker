import sys,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_event_view import event_hooks,graphic_entities,event_graphic
from native_event_presentation import present


class NativeEventViewTests(unittest.TestCase):
 def setup_records(self):
  session=Mock();session.data=bytearray(80)
  info={'entities':[{'offset':'0x0'},{'offset':'0x14'}],
        'events':[{'offset':'0x28'}]}
  session.data[44]=128;session.data[6]=7;session.data[5]=2
  return session,info

 def test_map_region_only_links_explicit_valid_spawn_templates(self):
  session,info=self.setup_records();session.data[60:68]=bytes([0x8A,1])+bytes(6)
  session.data[68:76]=bytes([0x8A,99])+bytes(6)
  with patch('native_event_view.script_roots',return_value={'B 0':(60,80,60)}),patch('native_event_view.instructions',return_value=[(60,0x8A,8),(68,0x8A,8)]):
   self.assertEqual(graphic_entities(session,0,'events',0,info),([1],'Spawned object preview'))
   self.assertEqual(graphic_entities(session,0,'entities',0,info),([0],'Event graphic'))

 def test_absent_hook_and_invisible_event_have_no_guessed_graphic(self):
  session,info=self.setup_records()
  with patch('native_event_view.script_roots',return_value={}):
   self.assertIsNone(event_hooks(session,0,'events',0,info)[0]['key'])
   self.assertEqual(graphic_entities(session,0,'events',0,info)[0],[])

 def test_representative_frame_used_and_cropped_with_original_direction(self):
  session,info=self.setup_records();image=Image.new('RGBA',(24,24))
  image.putpixel((8,10),(255,0,0,255));decoder=Mock()
  decoder.representative_frame.return_value=(image,0,0)
  with patch('native_event_view.cached_preview',return_value=decoder) as cache:
   result,basis,entity=event_graphic(session,0,'entities',0,info)
  cache.assert_called_once_with(session,0,True)
  decoder.representative_frame.assert_called_once_with(7,2)
  self.assertEqual(result.size,(1,1));self.assertEqual(entity,0)

 def test_local_bank_bit_is_respected(self):
  session,info=self.setup_records();session.data[5]=130;decoder=Mock()
  decoder.representative_frame.return_value=None
  with patch('native_event_view.cached_preview',return_value=decoder) as cache:
   self.assertIsNone(event_graphic(session,12,'entities',0,info)[0])
  cache.assert_called_once_with(session,12,False)

 def test_source_reported_camera_and_flags_preserve_unknown_operands(self):
  session=Mock();session.data=bytearray(b'\x62\x80\x08\x00\x69\x01\x00\x02\x00\x03\x00')
  shown=present(session,0,0,0x62,4,{})
  self.assertEqual(shown['action'],'Set character flags')
  self.assertIn('Flags: class B',shown['settings'])   # mask 0x0008 decoded via native_event_knowledge.EFLAGS;self.assertFalse(shown['editable'])
  self.assertIn('Height (pixels): 3',present(session,0,4,0x69,7,{})['settings'])

if __name__=='__main__':unittest.main()
