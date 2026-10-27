import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from entity_preview import EntityPreview
from test_local_sprite_import import fixture
from editor_session import EditSession


def quad(sx, x=0):
    return struct.pack('<6B8b',0,0,sx,0,2,1,x,0,x+2,0,x,1,x+2,1)


def preview(first=quad(0), second=quad(2)):
    view=EntityPreview.__new__(EntityPreview)
    view.data=bytearray(512);view.start=0;view.end=512
    view.header=[0]*12;view.header[5]=0;view.header[6]=32
    struct.pack_into('<16H',view.data,0,0,31,31<<5,*([0]*13))
    view.data[64:94]=b'\x00\x02'+first+second
    view.raw=bytearray(32768);view.raw[:2]=b'\x11\x22'
    return view


class CompositeTests(unittest.TestCase):
    def test_foreground_first_quad_preserved_over_background(self):
        view=preview();before=bytes(view.data)
        image,x,y=view.images(64,2)
        self.assertEqual((x,y,image.size),(0,0,(2,1)))
        self.assertEqual(list(image.get_flattened_data()),[(255,0,0,255)]*2)
        self.assertEqual(bytes(view.data),before)

    def test_transparent_foreground_exposes_background(self):
        view=preview();view.raw[0]=0x10
        image,_,_=view.images(64,2)
        self.assertEqual(list(image.get_flattened_data()),[(0,255,0,255),(255,0,0,255)])

    def test_shared_artwork_retains_independent_frame_positions(self):
        view=preview();view.data[100:116]=b'\x00\x01'+quad(0,7)
        first,x,y=view.images(64,2);second,sx,sy=view.images(100,1)
        self.assertEqual((x,y,sx,sy),(0,0,7,0))
        self.assertEqual(first.tobytes(),second.tobytes())
        self.assertEqual(len(view.piece_cache),2)
        self.assertEqual(len(view.palette_cache),1)

    def test_direction_offsets_select_distinct_native_frames(self):
        data=fixture();start=2048+2*2048+40
        # Native first-set direction entries address streams by byte offset.
        struct.pack_into('<4H',data,start+204,0,6,0xffff,0xffff)
        data[start+224:start+230]=b'\x81\xff\xff\x08\x00\x01'
        data[start+246:start+262]=bytes((0,1,0,0,0,0,2,2,-1&255,0,1,0,-1&255,2,1,2))
        view=EntityPreview(EditSession(data,verify=False),2)
        self.assertEqual(view.frame(7,0)[1],0)
        self.assertEqual(view.frame(7,1)[1],-1)
        self.assertEqual(view.frame(7,2)[1],0) # unavailable direction fallback


if __name__=='__main__':unittest.main()
