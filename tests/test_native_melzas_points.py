import struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
EXE=ROOT/'game/disc/ALUN_CD.EXE'

@unittest.skipUnless(EXE.exists(),'private stock executable missing')
class MelzasPointsTests(unittest.TestCase):
 def test_injection_moves_points_centre_and_heights_on_listed_maps_only(self):
  from project_state_runtime import inject_private_state
  from native_melzas_points import SITES,CENTRE_SITES
  exe=EXE.read_bytes()
  out,manifest=inject_private_state(exe,{},melzas_places={483:(276,-72,-304)})
  load,=struct.unpack_from('<I',out,0x18);word=lambda a:struct.unpack_from('<I',out,a-load+0x800)[0]
  for at,_ in SITES:self.assertEqual(word(at)>>26,3);self.assertEqual(word(at+4),0x3C158003)
  for at,reg,axis in CENTRE_SITES:self.assertEqual(word(at)>>26,3)
  rows=manifest['melzas_points'];self.assertEqual(rows['maps'],{'483':[276,-72,-304]})
  lst=rows['list_address'];self.assertEqual(struct.unpack_from('<iiiii',out,lst-load+0x800),(483,276<<16,-72<<16,-304<<16,-1))
 def test_without_placements_the_executable_keeps_stock_code(self):
  from project_state_runtime import inject_private_state
  out,manifest=inject_private_state(EXE.read_bytes(),{})
  load,=struct.unpack_from('<I',out,0x18)
  self.assertEqual(struct.unpack_from('<I',out,0x8007C4B8-load+0x800)[0],0x3C158003);self.assertNotIn('melzas_points',manifest)

if __name__=='__main__':unittest.main()
