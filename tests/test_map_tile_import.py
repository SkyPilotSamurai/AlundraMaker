import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_session import EditSession
from content_database import ContentDatabase
from map_tile_import import import_tiles,tile_bytes,write_tile,convert_pixels
from texture_codec import pack_ez

class TileImportTests(unittest.TestCase):
 def fixture(self,capacity=10000):
  source=bytearray(196608);write_tile(source,1,bytes([17])*192)
  target=bytearray(196608);write_tile(target,0,bytes([34])*192)
  packed=pack_ez(bytes(target));capacity=max(len(packed),capacity)
  session=EditSession(bytes(4096)+packed+bytes(capacity-len(packed)),verify=False)
  session.texture=lambda m:(source if m==1 else target,4096,4096+capacity)
  session.palette=lambda m,p:([0,31]+[0]*14,0) if m==1 else (([0,0,992]+[0]*13) if p==0 else [0]*16,256+p*32)
  return session,ContentDatabase(),source,target

 def test_deferred_import_shows_at_once_and_is_written_later(self):
  from map_tile_import import flush_texture
  from texture_codec import unpack_ez
  s,db,source,target=self.fixture();before=bytes(s.data)
  cells=[{'values':(0,0,0,0,0),'walls':[]}]
  with patch('map_tile_import.grid',return_value=(1,1,cells)):
   result=import_tiles(s,db,0,1,[1],defer=True)
  self.assertEqual(result,{1:0x1001})
  self.assertEqual(bytes(s.data[4096:]),before[4096:])   # texture not compressed yet
  self.assertEqual(tile_bytes(s._pending_textures[0],1),tile_bytes(source,1))
  self.assertEqual(int.from_bytes(s.data[290:292],'little'),0)   # the palette waits with the texture
  self.assertIn(288,s._pending_palettes)
  s.layout=lambda m:(0,[0]*7)
  self.assertTrue(flush_texture(s,db,0));self.assertFalse(s._pending_textures);self.assertFalse(s._pending_palettes)
  self.assertEqual(int.from_bytes(s.data[290:292],'little'),31)
  self.assertEqual(tile_bytes(unpack_ez(s.data[4096:])[0],1),tile_bytes(source,1))
 def test_exact_colour_import_is_atomic_and_undoable(self):
  s,db,source,target=self.fixture();before=bytes(s.data)
  cells=[{'values':(0,0,0,0,0),'walls':[]}]
  with patch('map_tile_import.grid',return_value=(1,1,cells)):
   result=import_tiles(s,db,0,1,[1])
  self.assertEqual(result,{1:0x1001});self.assertEqual(len(s.undo_stack),1)
  from texture_codec import unpack_ez
  self.assertEqual(tile_bytes(unpack_ez(s.data[4096:])[0],1),tile_bytes(source,1))
  self.assertEqual(int.from_bytes(s.data[290:292],'little'),31)
  s.undo();self.assertEqual(bytes(s.data),before)

 def test_palette_exhaustion_uses_closest_colours(self):
  # 2026-10-08: with all 16 palettes in use the tile is recoloured into the
  # best-matching palette instead of failing (user request: no import errors).
  s,db,_,_=self.fixture();before=bytes(s.data)
  old=s.palette;s.palette=lambda m,p:old(m,p) if m==1 else ([0]+[992]*15,256+p*32)
  with patch('map_tile_import.grid',return_value=(16,1,[{'values':(0,0,0,0,p<<12),'walls':[]} for p in range(16)])):
   result=import_tiles(s,db,0,1,[1])
  self.assertEqual(len(s.undo_stack),1);self.assertTrue(0<=result[1]>>12<16)
  s.undo();self.assertEqual(bytes(s.data),before)

 def test_colour_index_remap_and_same_map_no_import(self):
  self.assertEqual(convert_pixels(bytes([0x11]),[0,31]+[0]*14,[0,0,31]+[0]*13),bytes([0x22]))
  self.assertEqual(import_tiles(None,None,7,7,[1,65535]),{1:1,65535:65535})
