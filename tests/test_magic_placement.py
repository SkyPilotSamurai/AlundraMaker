import struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import magic_placement as mp


class MagicPlacement(unittest.TestCase):
    def test_settings_validate(self):
        row=dict(kind='item',source=dict(item_id=50),data=dict(magic_placement={str(0x80036AE4):dict(mode=3,tiles=10,random=True)}))
        self.assertEqual(mp.settings([row]),{0x80036AE4:(3,10,True,0,0,0,100,0x18,None)})
        row['data']['magic_placement'][str(0x80036AE4)]['tiles']=11
        with self.assertRaises(ValueError):mp.settings([row])
        self.assertIsNone(mp.settings([dict(kind='item',source={},data={})]))
        row['data']['magic_placement'][str(0x80036AE4)].update(tiles=0,mode=0,tracking=11)
        with self.assertRaises(ValueError):mp.settings([row])

    def test_block_config_and_stubs(self):
        raw=mp.Block({0x80036AE4:(3,10,True,7,300,0,100,0x18,5)})(0x80018000)
        self.assertEqual(len(raw),mp.SIZE)
        _,labels,config,_=mp._words(0x80018000)
        self.assertEqual(raw[config-0x80018000+64:config-0x80018000+72],bytes([3,0x8A,7,0])+struct.pack('<HH',300,6))
        self.assertEqual(struct.unpack_from('<I',raw,labels['s8']-0x80018000+4)[0],0x24190008)


DATAS=ROOT/'game/disc/DATA/DATAS.BIN'


@unittest.skipUnless(DATAS.is_file(),'needs private DATAS.BIN')
class ColourVariants(unittest.TestCase):
    def test_variants_use_spare_slots_only(self):
        d=DATAS.read_bytes()
        ch={0x800362A0:(0,0,False,0,0,120,150,0x14,None),0x800363A4:(0,0,False,0,0,120,150,0x17,None)}
        v=mp.variants(ch,d)
        slots=[s for _,c in v.values() for s,_ in c]
        self.assertEqual(len(v),2);self.assertTrue(all(s in mp.SPARE_SLOTS for s in slots));self.assertEqual(len(slots),len(set(slots)))


class WaterScrollStub(unittest.TestCase):
    def test_stub_and_need(self):
        import magic_spawns as ms
        raw=ms.WaterScrollStub()(0x80018000)
        self.assertEqual(struct.unpack('<5I',raw),(0x2404002D,0x0C00D7C7,0,0x0800DB38,0x00401821))
        row=dict(kind='item',source=dict(item_id=43),data=dict(magic_behaves_like=45))
        self.assertTrue(ms.needs_water_stub([row]));row['data']['magic_behaves_like']=46
        self.assertFalse(ms.needs_water_stub([row]))
