import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from texture_codec import pack_ez,pack_ez_compact,pack_ez_fit,unpack_ez
DATAS=ROOT/'game/disc/DATA/DATAS.BIN'


class CompactPackTests(unittest.TestCase):
    def test_round_trip_and_page_rules(self):
        import random
        rng=random.Random(5);raw=bytes(rng.choice((0,0,0,0x11,0xAD,0x3C,rng.randrange(256))) for _ in range(65536))
        packed=pack_ez_compact(raw)
        self.assertEqual(unpack_ez(packed,len(raw))[0],raw)
        self.assertLessEqual(len(packed),len(pack_ez(raw)))
        self.assertEqual(pack_ez_fit(raw,b'EZ\0\0\0\0',10**6),pack_ez(raw))


@unittest.skipUnless(DATAS.is_file(),'needs DATAS.BIN')
class RoomTests(unittest.TestCase):
    def setUp(self):
        from editor_session import EditSession
        self.s=EditSession(DATAS.read_bytes(),None,verify=False)

    def test_compact_pack_saves_room_on_real_maps(self):
        raw,start,end=self.s.texture(163);header=bytes(self.s.data[start:start+6])
        self.assertGreater(len(pack_ez(raw,header))-len(pack_ez_compact(raw,header)),500)

    def test_new_map_has_blank_texture_and_full_sheet_can_make_room(self):
        from content_database import ContentDatabase
        from map_create import create_map
        from map_tile_import import import_tiles
        from area_map import grid
        db=ContentDatabase();m,_=create_map(self.s,db.document)
        self.assertFalse(any(self.s.texture(m)[0]))
        w,h,c=grid(self.s,17);codes=sorted({x['values'][4] for x in c if x['values'][4]!=65535})[:40]
        with self.assertRaises(ValueError):import_tiles(self.s,db,163,17,codes)
        self.assertEqual(len(import_tiles(self.s,db,163,17,codes,erase_unused=True)),40)


if __name__=='__main__':unittest.main()
