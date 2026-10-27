import struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_session import EditSession
from editor_start_point import resolve_start_point,set_start_point,patch_start_point_spawn
from area_map import grid


class StartPointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_path=ROOT/'game/disc/DATA/DATAS.BIN'
        cls.exe_path=ROOT/'game/disc/ALUN_CD.EXE'
        if cls.data_path.exists():cls.data=cls.data_path.read_bytes()

    def test_marker_uses_tile_height_and_enables_new_game_entry(self):
        if not hasattr(self,'data'):self.skipTest('Private original unavailable')
        session=EditSession(self.data);width,height,cells=grid(session,242)
        point=set_start_point({'mod_options':{}},session,242,38,12)
        self.assertEqual(point,{'map_id':242,'x':38,'y':12,'z':cells[12*width+38]['values'][3]})
        options={'mod_options':{}}
        set_start_point(options,session,242,38,12)
        self.assertTrue(options['mod_options']['skip_intro'])
        self.assertEqual(resolve_start_point(session,options['mod_options']['start_point']),point)

    def test_start_point_rejects_outside_map_tiles(self):
        if not hasattr(self,'data'):self.skipTest('Private original unavailable')
        session=EditSession(self.data);width,height,_=grid(session,242)
        for point in ({'map_id':483,'x':0,'y':0},{'map_id':242,'x':width,'y':0},
                      {'map_id':242,'x':0,'y':height}):
            with self.assertRaises(ValueError):resolve_start_point(session,point)

    def test_spawn_patch_writes_map_tile_and_height_only_to_known_fields(self):
        if not self.exe_path.exists():self.skipTest('Private original unavailable')
        from intro_skip import EXE_FIELDS
        from alundra_memory import parse_exe
        source=self.exe_path.read_bytes();point={'map_id':427,'x':7,'y':9,'z':3}
        patched,report=patch_start_point_spawn(source,point)
        info=parse_exe(patched)
        wanted=(7,9,3,427,7,9,None)
        for (address,_,_,_),value in zip(EXE_FIELDS,wanted):
            offset=0x800+address-info['load_address'];word=struct.unpack_from('<I',patched,offset)[0]
            if value is not None:self.assertEqual(word&0xffff,value)
        self.assertEqual(report['spawn'],point)
        self.assertEqual(len(report['sites']),len(EXE_FIELDS))
        self.assertNotEqual(patched,source)

    def test_custom_map_start_is_composed_after_intro_skip(self):
        if not hasattr(self,'data') or not self.exe_path.exists():self.skipTest('Private original unavailable')
        from editor_qol import apply_qol
        session=EditSession(self.data);width,height,cells=grid(session,242)
        z=cells[12*width+38]['values'][3]
        session.content_database={'mod_options':{'open_world':False,'skip_intro':False,
            'start_point':{'map_id':242,'x':38,'y':12}}}
        exe,report=apply_qol(session,self.exe_path.read_bytes())
        self.assertTrue(report['options']['skip_intro'])
        self.assertEqual(report['start_point'],{'map_id':242,'x':38,'y':12,'z':z})
        formats=[p.get('format') for p in report['patches']]
        self.assertLess(formats.index('alundra-editor-start-point-v1'),formats.index('alundra-normal-story-intro-skip-v1'))
        # 2026-10-08: a custom start sets the first-wake flags, above all HUD allowed (0x67E).
        self.assertIn(0x67E,[f['operand'] for f in report['start_point_new_game_flags']])
        self.assertIn('open_world_state',[p.get('feature') for p in report['patches']])
        from alundra_memory import parse_exe
        from intro_skip import EXE_FIELDS
        info=parse_exe(exe)
        for (address,_,_,_),value in zip(EXE_FIELDS,(38,12,z,242,38,12,None)):
            if value is not None:
                off=0x800+address-info['load_address']
                self.assertEqual(struct.unpack_from('<I',exe,off)[0]&0xffff,value)


if __name__=='__main__':unittest.main()
