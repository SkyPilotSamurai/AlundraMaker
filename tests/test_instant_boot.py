"""Instant boot: SYSTEM.CNF boots ALUN_CD.EXE; the entry stub clears the loader
hand-over word only on a BIOS boot (unicorn MIPS run)."""
import struct,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import instant_boot as ib
try:
    import unicorn
    from unicorn import mips_const as M
except ImportError:
    unicorn=None
EXE=ROOT/'game'/'disc'/'ALUN_CD.EXE'
CNF=b'BOOT = cdrom:\\SLUS_005.53;1\r\nTCB = 4\r\nEVENT = 16\r\nSTACK = 801FFFF0\r\n'


class InstantBootTests(unittest.TestCase):
    def test_system_cnf(self):
        out=ib.patch_system_cnf(CNF)
        self.assertEqual(len(out),len(CNF));self.assertIn(b'BOOT = cdrom:\\ALUN_CD.EXE;1',out)
        self.assertIn(b'STACK = 801FFFF0',out);self.assertEqual(ib.patch_system_cnf(out),out)
        with self.assertRaises(ValueError):ib.patch_system_cnf(b'BOOT = cdrom:\\OTHER.EXE;1\r\n')

    @unittest.skipIf(unicorn is None,'unicorn not installed')
    def test_entry_stub_clears_only_on_bios_boot(self):
        for sp,cleared in ((0x801FFFF0,True),(0x801FFF00,False)):
            mu=unicorn.Uc(unicorn.UC_ARCH_MIPS,unicorn.UC_MODE_MIPS32+unicorn.UC_MODE_LITTLE_ENDIAN)
            mu.mem_map(0,0x200000)
            mu.mem_write(0x10000,struct.pack('<II',1,1))
            mu.mem_write(0x1F000,ib.entry_stub(0x8001F000,0x8008DDA0))
            mu.reg_write(M.UC_MIPS_REG_SP,sp)
            mu.emu_start(0x8001F000,0x8008DDA0,count=20)
            self.assertEqual(mu.reg_read(M.UC_MIPS_REG_PC),0x8008DDA0)
            self.assertEqual(struct.unpack('<II',mu.mem_read(0x10000,8)),(0,0) if cleared else (1,1))

    @unittest.skipUnless(EXE.is_file(),'private executable not present')
    def test_build_sets_entry_to_stub(self):
        from editor_qol import apply_qol
        stock=EXE.read_bytes()
        datas=ROOT/'game'/'disc'/'DATA'/'DATAS.BIN'
        if not datas.is_file():self.skipTest('private game data not present')
        from editor_session import EditSession
        session=EditSession(datas.read_bytes(),None,verify=False)
        session.content_database={'mod_options':{'instant_boot_plus':True}}
        out,report=apply_qol(session,stock)
        pc=struct.unpack_from('<I',out,0x10)[0];load=struct.unpack_from('<I',out,0x18)[0]
        self.assertEqual(report['instant_boot']['original_entry'],hex(struct.unpack_from('<I',stock,0x10)[0]))
        stub=out[pc-load+0x800:pc-load+0x800+ib.ENTRY_STUB_SIZE]
        self.assertEqual(stub,ib.entry_stub(pc,struct.unpack_from('<I',stock,0x10)[0]))

    def test_menu_instant_boot_only_removes_movies(self):
        slus=ROOT/'game'/'disc'/'SLUS_005.53'
        if not slus.is_file():self.skipTest('private boot program not present')
        stock=slus.read_bytes();out=ib.patch_slus_movies(stock)
        diffs=[i for i in range(0,len(stock),4) if stock[i:i+4]!=out[i:i+4]]
        self.assertEqual(len(diffs),2)   # two jal 80027F5C -> nop
        self.assertEqual(ib.patch_slus_movies(out),out)
        from mod_export import _slus_options
        self.assertEqual(_slus_options({'instant_boot':True}),['movies'])
        self.assertEqual(_slus_options({'instant_boot_plus':True,'fast_loading':True}),['movies','fast'])
        self.assertEqual(_slus_options({'fast_loads':True}),['fast'])

    def test_build_and_test_script(self):
        with tempfile.TemporaryDirectory() as folder:
            script,report=ib.write_script(folder,store=folder,exe=b'program A')
            text=script.read_text()
            self.assertIn('saving',report['mode'])
            Path(report['state']).write_bytes(b'x')
            self.assertIn('past-the-logo state',ib.write_script(folder,store=folder,exe=b'program A')[1]['mode'])
            # a changed game program never loads the old state
            self.assertNotIn('saving',ib.write_script(folder,store=folder,exe=b'program B')[1]['mode'])   # one shared state
        self.assertNotIn('speedmode(1600',text);self.assertNotIn('__',text)
        self.assertIn('game_running()',text)   # saved once the game program runs (past the logo)


if __name__=='__main__':unittest.main()
