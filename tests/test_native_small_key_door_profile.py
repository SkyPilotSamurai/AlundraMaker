import unittest
from native_small_key_door_profile import compile_small_key_door
from project_state_registry import ProjectStateRegistry
from pathlib import Path
class SmallKeyDoorTests(unittest.TestCase):
 def test_retained_c_owns_wait_and_cleanup_not_transient_f(self):
  r=ProjectStateRegistry({});flag=r.create('switches','Opened')['id'];p,meta=compile_small_key_door(r,flag,128,bytes.fromhex('373c980700'),retained_c=True)
  self.assertIn(bytes.fromhex('843d'),p['F']);self.assertNotIn(bytes.fromhex('373c'),p['F']);self.assertNotIn(bytes.fromhex('2e80'),p['F'])
  self.assertTrue(p['C'].startswith(bytes.fromhex('00e1000001')))
  self.assertTrue(p['C'].endswith(bytes.fromhex('373c9807002e80ff')))
  self.assertTrue(meta['experimental_retained_c']);self.assertFalse(meta['production_enabled'])
 def test_wait_occurs_after_consumption_before_self_removal(self):
  r=ProjectStateRegistry({});flag=r.create('switches','Opened')['id'];p,meta=compile_small_key_door(r,flag,128,bytes.fromhex('373c980700'))
  code=p['F'];self.assertLess(code.index(bytes.fromhex('843d')),code.index(bytes.fromhex('373c')))
  self.assertLess(code.index(bytes.fromhex('373c')),code.index(bytes.fromhex('9807002e80')))
  self.assertNotIn(bytes.fromhex('05ac02'),code);self.assertEqual(meta['removed_room_flag'],'02AC')
 def test_map_local_owned_failure_text_required(self):
  r=ProjectStateRegistry({});flag=r.create('switches','Opened')['id']
  for ref in [0,127,256,None]:
   with self.assertRaises(ValueError):compile_small_key_door(r,flag,ref)

 @unittest.skipUnless((Path(__file__).resolve().parents[1]/'game/disc/DATA/DATAS.BIN').exists(),'Local lawful input required')
 def test_real_map_edit_accepted_but_donor_corruption_rejected(self):
  from editor_session import EditSession
  from area_map import edit_height
  from event_editor import instructions
  from native_small_key_door_profile import verify_source
  s=EditSession((Path(__file__).resolve().parents[1]/'game/disc/DATA/DATAS.BIN').read_bytes())
  edit_height(s,163,0,0,1);self.assertTrue(verify_source(s.data))
  position=instructions(s,41,'F 24')[0][0];s.data[position]^=1
  with self.assertRaisesRegex(ValueError,'F 24 differs'):verify_source(s.data)
