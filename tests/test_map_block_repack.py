import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from map_block_repack import pointers,replace_block,replace_section,sections
class RepackTests(unittest.TestCase):
 def fixture(self):
  d=bytearray(2048*484)
  struct.pack_into("<484I",d,0x28,*[2048*(n+1) for n in range(484)])
  for n in range(483):
   base=2048*(n+1);struct.pack_into("<7I",d,base,28,100,200,300,400,500,600)
   d[base+700:base+704]=struct.pack("<I",n)
  return d
 def test_growth_preserves_other_maps_and_reverse(self):
  d=self.fixture();old=pointers(d);original=bytes(d[old[427]:old[428]])
  block=original+bytes(2048);new=replace_block(d,427,block);ptr=pointers(new)
  for n in range(483):
   if n!=427:self.assertEqual(new[ptr[n]:ptr[n+1]],d[old[n]:old[n+1]])
  self.assertEqual(replace_block(new,427,original),d)
 def test_identity(self):
  d=self.fixture();p=pointers(d)
  self.assertEqual(replace_block(d,427,d[p[427]:p[428]]),d)
 def test_reject_bad_table_and_section(self):
  d=self.fixture();p=pointers(d)
  with self.assertRaises(ValueError):replace_block(d,427,b'bad')
  struct.pack_into('<I',d,0x28+428*4,p[427])
  with self.assertRaises(ValueError):pointers(d)

 def test_unaligned_replacement_and_existing_offsets_rejected(self):
  d=self.fixture();before=bytes(d)
  with self.assertRaisesRegex(ValueError,'four-byte'):replace_section(d,427,2,b'abc')
  self.assertEqual(d,before)
  p=pointers(d);block=bytearray(d[p[427]:p[428]])
  struct.pack_into('<I',block,12,301)
  with self.assertRaises(ValueError):sections(block)
 def test_grown_padded_texture_keeps_following_sections_aligned(self):
  from texture_codec import pack_ez,unpack_ez
  raw=bytes(range(100));packed=pack_ez(raw)
  self.assertNotEqual(len(packed)%4,0)
  packed+=bytes((-len(packed))%4)
  d=self.fixture();p=pointers(d);old=bytes(d[p[427]:p[428]]);h=sections(old)
  result=replace_section(d,427,2,packed);p=pointers(result);block=result[p[427]:p[428]];new=sections(block)
  self.assertTrue(all(v%4==0 for v in new))
  self.assertEqual(unpack_ez(block[new[2]:new[3]])[0],raw)
  self.assertEqual(block[new[3]:new[6]],old[h[3]:h[6]])
