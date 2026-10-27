import sys,unittest,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from sprite_palette import recolor,palettes,apply_palette
from editor_session import EditSession
class SpritePaletteTests(unittest.TestCase):
 def fixture(self):
  data=bytearray(512);struct.pack_into('<12I',data,64,0,0,0,0,0,48,80,0,0,0,0,0)
  struct.pack_into('<16H',data,112,*([0,0xFC43,0x4210,0x03FF]+[0]*12))
  s=EditSession(data,verify=False);s.layout=lambda m:(0,[0,0,0,64,256,512,0]);return s
 def test_swap_preserves_shading_transparency_and_high_bit(self):
  words=(0,0x8000,0xFC43,0x4210,0x03FF)
  result=recolor(words,'Blue','Red')
  self.assertEqual(result,(0,0x8000,0x8C5F,0x4210,0x03FF))
  self.assertEqual(sorted([result[2]&31,(result[2]>>5)&31,(result[2]>>10)&31]),sorted([3,2,31]))
 def test_apply_mod_roundtrip_and_undo(self):
  s=self.fixture();before=bytes(s.data);words=palettes(s,0)[0][2]
  apply_palette(s,0,0,recolor(words,'Blue','Red'));edited=bytes(s.data)
  fresh=self.fixture();fresh.apply_patch(s.patch());self.assertEqual(bytes(fresh.data),edited)
  s.undo();self.assertEqual(bytes(s.data),before)
 def test_invalid_palette_rejects_without_mutation(self):
  s=self.fixture();before=bytes(s.data)
  for index,words in ((-1,[0]*16),(1,[0]*16),(0,[0]*15),(0,[65536]*16)):
   with self.assertRaises(ValueError):apply_palette(s,0,index,words)
  self.assertEqual(bytes(s.data),before)
 def test_bounds_rejected(self):
  s=self.fixture();struct.pack_into('<I',s.data,64+6*4,500)
  with self.assertRaises(ValueError):palettes(s,0)
