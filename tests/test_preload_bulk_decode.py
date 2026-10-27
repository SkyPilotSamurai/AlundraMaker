import random
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from entity_preview import indexed_sprite_page
from texture_codec import unpack_ez
from PIL import Image

class BulkDecodeTests(unittest.TestCase):
 def test_every_pixel_matches_native_nibble_order(self):
  raw=random.Random(71).randbytes(65536)
  for page in range(2):
   expected=bytes((raw[page*32768+i//2]>>(4*(i&1)))&15 for i in range(65536))
   self.assertEqual(indexed_sprite_page(raw,page).tobytes(),expected)
 def test_missing_page_is_rejected(self):
  with self.assertRaises(IndexError):indexed_sprite_page(bytes(32767),0)
 def test_rgba_crop_preserves_transparency_and_all_palette_words(self):
  raw=random.Random(17).randbytes(32768)
  words=[0,0x8000,31,31<<5,31<<10]+list(range(11))
  colors=[((v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31,0 if v==0 else 255) for v in words]
  page=indexed_sprite_page(raw,0)
  for sx,sy,w,h in [(0,0,256,256),(1,7,31,43),(253,254,3,2)]:
   fast=page.crop((sx,sy,sx+w,sy+h))
   fast.putpalette(bytes(c for rgba in colors for c in rgba),rawmode='RGBA')
   expected=Image.new('RGBA',(w,h))
   expected.putdata([colors[(raw[((sy+y)*256+sx+x)//2]>>(4*((sx+x)&1)))&15] for y in range(h) for x in range(w)])
   self.assertEqual(fast.convert('RGBA').tobytes(),expected.tobytes())
 def test_overlapping_and_nonoverlapping_matches(self):
  for distance in range(1,256):
   seed=bytes(range(distance))
   escaped=seed.replace(b'\xad',b'\xad\x00')
   for length in (1,2,7,254,255):
    block=b'EZ\0\0\0\0'+escaped+bytes((173,distance,length,173,255,0))
    expected=seed+(seed*((length+distance-1)//distance))[:length]
    self.assertEqual(unpack_ez(block,1000),(expected,len(block)))
