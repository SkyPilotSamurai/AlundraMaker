import struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import starting_equipment as se
EXE=ROOT/'game/disc/ALUN_CD.EXE'

class StartingKeys(unittest.TestCase):
    def test_validate(self):
        base=dict(max_hp=10,hp=10,max_mp=0,mp=0,gilder=0)
        self.assertEqual(se.validate_starting_stats(base)['keys'],0)
        self.assertEqual(se.validate_starting_stats(dict(base,keys=99))['keys'],99)
        for bad in (-1,100,'3'):
            with self.assertRaises(ValueError):se.validate_starting_stats(dict(base,keys=bad))
        self.assertEqual(se.STAT_ORDER.index('keys')+1,se.STAT_ORDER.index('gilder'))

    def test_stub(self):
        w=struct.unpack('<13I',se.emit_key_stub(3))
        self.assertEqual(w[3],0x24100003);self.assertEqual(w[4],0x0C013EF9);self.assertEqual(w[5],0x2404003D)
        self.assertEqual(w[11],0x08020F8D)
        with self.assertRaises(ValueError):se.emit_key_stub(0)

    @unittest.skipUnless(EXE.exists(),'private stock EXE absent')
    def test_stock_hook(self):
        exe=EXE.read_bytes();se.verify_key_hook(exe)
        self.assertEqual(se.read_starting_stats(exe)['keys'],0)
        out=se.patch_key_hook(exe,0x8001F800)
        self.assertEqual(struct.unpack_from('<I',out,0x80031E7C-0x80020000+0x800)[0],0x0C007E00)

if __name__=='__main__':unittest.main()
