"""Start as Meia: non-attack frames become Meia, attack frames and other sprites stay."""
import struct,sys,unittest
from copy import copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
DATAS=ROOT/'game'/'disc'/'DATA'/'DATAS.BIN'

@unittest.skipUnless(DATAS.is_file(),'private retail DATAS.BIN not present')
class CostumeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from editor_session import EditSession
        import player_costume as pc
        cls.pc=pc;cls.data=DATAS.read_bytes()
        s=EditSession(cls.data,None,verify=False);t=copy(s);t.data=bytearray(s.data)
        cls.report=pc.apply_costume(t);cls.out=bytes(t.data)
    def test_size_and_everything_fits(self):
        self.assertEqual(len(self.out),len(self.data))
        self.assertEqual(self.report['kept_alundra'],[])
        self.assertLessEqual(self.report['texture_bytes'],self.report['room'])
    def test_only_global_bank_changes(self):
        start,sheet,end,header=self.pc._global_bank(self.data)
        self.assertEqual(self.out[end:],self.data[end:])
    def test_attack_frames_keep_alundra(self):
        uses,quads,base=self.pc._player_image_sets(self.data)
        keep=[i for i,u in uses.items() if {a for a,_,_ in u}&self.pc.KEEP_ALUNDRA]
        for i in keep[:200]:
            pos=base+i*2;n=self.data[pos+1]*14+2
            self.assertEqual(self.out[pos:pos+n],self.data[pos:pos+n])
        from editor_session import EditSession
        from animation_preview import load_animation
        a=load_animation(EditSession(self.data,None,verify=False),163,0,0x10,0)
        b=load_animation(EditSession(self.out,None,verify=False),163,0,0x10,0)
        # Same Alundra drawing (shape), only his blue tones recoloured to Meia's lavender.
        self.assertEqual([f.image.split()[3].tobytes() for f in a.frames if f.image],[f.image.split()[3].tobytes() for f in b.frames if f.image])
    def test_menu_portrait_and_palettes(self):
        self.assertEqual(self.report.get('menu_portrait'),'Meia')
        self.assertEqual(self.pc.meia_tones(0x7C00)&0x8000,0)
        self.assertNotEqual(self.pc.meia_tones(0x7C00),0x7C00)   # pure blue changes
        self.assertEqual(self.pc.meia_tones(0x001F),0x001F)      # red stays
    def test_walk_frames_change(self):
        from editor_session import EditSession
        from animation_preview import load_animation
        a=load_animation(EditSession(self.data,None,verify=False),163,0,0x01,0)
        b=load_animation(EditSession(self.out,None,verify=False),163,0,0x01,0)
        self.assertNotEqual(a.frames[0].image.tobytes(),b.frames[0].image.tobytes())

if __name__=='__main__':unittest.main()
