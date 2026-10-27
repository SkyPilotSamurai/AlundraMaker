import sys,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
DISC=ROOT/'game/disc'


@unittest.skipUnless((DISC/'DATA/DATAS.BIN').is_file() and (DISC/'ALUN_CD.EXE').is_file(),'needs the US game files')
class NewMapSlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from editor_session import EditSession
        cls.datas=(DISC/'DATA/DATAS.BIN').read_bytes()
        cls.Session=EditSession

    def session(self):
        return self.Session(self.datas,None,verify=False)

    def test_seventeen_slots_then_full_and_undo(self):
        import map_create
        from map_slots import extra_count,map_count
        from area_map import grid
        from map_inspector import inspect_map
        s=self.session();doc={}
        for expected in range(483,500):
            m,label=map_create.create_map(s,doc);self.assertEqual(m,expected)
        self.assertEqual((extra_count(s.data),map_count(s.data)),(17,500))
        with self.assertRaises(map_create.SlotsFull):map_create.create_map(s,doc)
        w,h,cells=grid(s,499);self.assertEqual({c['values'] for c in cells},{(0,0,4,1,0xFFFF,-1)})
        info=inspect_map(bytes(s.data),499);self.assertEqual((info['entities'],info['events']),([],[]))
        for _ in range(17):s.undo()
        self.assertEqual(bytes(s.data),s.original)

    def test_patch_round_trip_and_loader_bounds(self):
        import map_create
        from map_block_repack import pointers
        from map_loader_constraints import validate_layout
        s=self.session();map_create.create_map(s,{});map_create.create_map(s,{})
        p=s.patch();self.assertIn('tail',p)
        t=self.session();t.apply_patch(p);self.assertEqual(bytes(t.data),bytes(s.data))
        self.assertEqual(len(pointers(s.data)),486);self.assertEqual(validate_layout(bytes(s.data))['map_count'],485)
        self.assertLessEqual(max(validate_layout(bytes(s.data))['maximum_map_bytes'],0),0x58800)

    def test_overwrite_choices_have_both_tabs(self):
        from map_create import overwrite_choices,blank_existing_map
        s=self.session();unused,game,free=overwrite_choices(s,{})
        self.assertEqual(len(unused)+len(game),482);self.assertIn(118,unused);self.assertIn(163,game)
        blank_existing_map(s,{},118)

    def test_build_hooks_loader_music_and_sound_tables(self):
        import map_create,extra_maps_runtime as emr
        from editor_qol import apply_qol
        from native_lr_swaps import offset
        s=self.session();doc={'map_music':{'483':16,'163':7}}
        map_create.create_map(s,doc);s.content_database=doc
        exe=(DISC/'ALUN_CD.EXE').read_bytes()
        out,report=apply_qol(s,exe);out=bytearray(out)
        hooks=next(p for p in report['patches'] if p.get('feature')=='new_map_slots_hooks')
        music=struct.unpack_from('<500i',out,offset(out,int(hooks['music_table'],16),2000))
        sfx=struct.unpack_from('<500i',out,offset(out,int(hooks['sound_bank_table'],16),2000))
        stock_music,stock_sfx=emr.stock_tables(exe,offset)
        self.assertEqual((music[163],music[483]),(7,16));self.assertEqual(list(sfx[:483]),stock_sfx)
        self.assertEqual(sfx[483],stock_sfx[doc['new_map_slots']['483']['template_map']])
        word=lambda va:struct.unpack_from('<I',out,offset(out,va))[0]
        self.assertEqual(word(0x8002C2B0),0x0C000000|((int(hooks['block'],16)>>2)&0x3FFFFFF))
        self.assertEqual(word(0x8002C484),0x00541021);self.assertEqual(word(0x8002C48C),0x8C470004)
        table=int(hooks['header_buffer'],16)+0x28
        self.assertEqual(((word(0x8002C344)&0xFFFF)<<16)+struct.unpack('<h',struct.pack('<H',word(0x8002C360)&0xFFFF))[0],table)

    def test_expand_maps_beyond_500(self):
        import map_create
        from map_slots import map_count,ext_info,offsets
        from map_block_repack import pointers,replace_block
        from editor_qol import apply_qol
        from native_lr_swaps import offset
        s=self.session();doc={'map_music':{'501':16}}
        for _ in range(17):map_create.create_map(s,doc)
        with self.assertRaises(map_create.SlotsFull):map_create.create_map(s,doc)
        self.assertEqual(map_create.create_expanded_map(s,doc)[0],500)
        self.assertEqual(map_create.create_map(s,doc)[0],501)   # expanded: New Map keeps going
        self.assertEqual((map_count(s.data),ext_info(s.data)[1]),(502,2))
        self.assertEqual(len(pointers(s.data)),503)
        o=offsets(s.data);grown=replace_block(bytes(s.data),163,bytes(s.data[o[163]:o[164]])+bytes(2048))
        self.assertEqual((map_count(grown),offsets(grown)[501]-o[501]),(502,2048))
        t=self.session();t.apply_patch(s.patch());self.assertEqual(bytes(t.data),bytes(s.data))
        s.content_database=doc
        out,report=apply_qol(s,(DISC/'ALUN_CD.EXE').read_bytes());out=bytearray(out)
        hooks=next(p for p in report['patches'] if p.get('feature')=='new_map_slots_hooks')
        self.assertEqual((hooks['maps'],hooks['expanded_maps']),(502,2))
        word=lambda va:struct.unpack_from('<I',out,offset(out,va))[0]
        self.assertEqual(word(0x800318F4),0x0C000000|((int(hooks['door_helper'],16)>>2)&0x3FFFFFF))
        self.assertEqual(struct.unpack_from('<i',out,offset(out,int(hooks['music_table'],16)+4*501))[0],16)
        for _ in range(19):s.undo()
        self.assertEqual(bytes(s.data),s.original)

    def test_no_new_maps_means_no_hooks(self):
        from editor_qol import apply_qol
        s=self.session();s.content_database={}
        exe=(DISC/'ALUN_CD.EXE').read_bytes();out,report=apply_qol(s,exe)
        self.assertEqual(out,exe)


if __name__=='__main__':unittest.main()


@unittest.skipUnless((DISC/'DATA/DATAS.BIN').is_file(),'needs the US game files')
class DeleteMapWarpTests(unittest.TestCase):
    def test_delete_removes_warp_commands_and_compacts_doors(self):
        from editor_session import EditSession
        import map_create
        from map_delete import delete_map
        from warp_editor import add_warp,warps
        from content_database import ContentDatabase
        from event_graph import validate_event_graph
        s=EditSession((DISC/'DATA/DATAS.BIN').read_bytes(),None,verify=False)
        db=ContentDatabase();doc=db.document
        a,_=map_create.create_map(s,doc);b,_=map_create.create_map(s,doc);c,_=map_create.create_map(s,doc)
        add_warp(s,b,5,5,a,5,5,0);add_warp(s,b,7,7,c,5,5,0)
        g=db.new_event_graph(b,'Warp out',3,4);w={'type':'warp_player','map_id':a,'x':1,'y':1}
        g['pages'][0]['commands']=[w,{'type':'show_dialogue','text':'hi'}]
        g['pages'][0]['trigger_actions']=[{'trigger':'interact','commands':[dict(w)],'hit_sources':[],'destroy_after':False}]
        db.replace_event_graph(g['id'],g)
        before=bytes(s.data)
        delete_map(s,doc,a)
        self.assertEqual([(i,p.destination_map) for i,_,p in warps(s,b-1)],[(0,c-1)])
        for row in db.document['event_graphs']:validate_event_graph(row)
        s.undo();self.assertEqual(bytes(s.data),before)
