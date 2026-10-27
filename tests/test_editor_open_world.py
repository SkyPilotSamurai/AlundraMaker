import sys,unittest,json,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_session import EditSession
from event_editor import script_roots
from editor_open_world import world_access_plan,apply_world_access,open_world_starting_state,patch_open_world_spawn,RECIPE,_process_recipe_offset
from native_script_allocation import append_native_process
from intro_skip import patch_intro_spawn

ROOT=Path(__file__).resolve().parents[1]
DATAS=ROOT/'game/disc/DATA/DATAS.BIN'
EXE=ROOT/'game/disc/ALUN_CD.EXE'


class RecipeTests(unittest.TestCase):
    def test_shifted_route_signature_relocates_only_at_decoded_instruction_boundary(self):
        before=bytes.fromhex('38a200ed00');after=bytes.fromhex('0205000000')
        code=b'\x11\x22\x33\x44\x55'+before+b'\xFF'
        offset,moved=_process_recipe_offset(code,0,len(code),2,before,after,411,'B 3','recipe.hpp',30,{5})
        self.assertEqual(offset,5);self.assertTrue(moved)
        with self.assertRaisesRegex(ValueError,'no unique copy'):
            _process_recipe_offset(code,0,len(code),2,before,after,411,'B 3','recipe.hpp',30,{6})
        duplicate=code+before
        with self.assertRaisesRegex(ValueError,'2 possible route commands'):
            _process_recipe_offset(duplicate,0,len(duplicate),2,before,after,411,'B 3','recipe.hpp',30,{5,len(code)})

    def test_recipe_preserves_ids_and_has_no_dream_route_or_shuffle(self):
        recipe=json.loads(RECIPE.read_text())
        self.assertEqual(len(recipe['patches']),119)
        flags,variants=open_world_starting_state()
        self.assertTrue(any(r['operand']==0x67e for r in flags))
        self.assertFalse(any('SYBILL_HOLY_SWORD' in r['name'] or 'RONAN' in r['name'] for r in flags))
        self.assertTrue(all(0<=r['operand']<0x800 for r in flags))
        self.assertEqual(next(r['value'] for r in variants if r['address']=='0x801dd618'),260)
        self.assertEqual({p['anchor']['kind'] for p in recipe['patches']},{'process','entity'})

    @unittest.skipUnless(DATAS.is_file(),'Requires ignored local game data')
    def test_actual_source_preimages_idempotence_undo_and_atomic_rejection(self):
        data=DATAS.read_bytes();s=EditSession(data)
        before=bytes(s.data);plan,_=world_access_plan(s)
        self.assertEqual(len(apply_world_access(s)['changes']),119)
        self.assertEqual(apply_world_access(s)['changes'],[])
        while s.undo_stack:s.undo()
        self.assertEqual(bytes(s.data),before)
        offset,old,new,row=plan[-1];s.data[offset]^=1;broken=bytes(s.data)
        with self.assertRaisesRegex(ValueError,'Open World cannot safely patch map') as caught:
            apply_world_access(s)
        self.assertIn('Expected bytes',str(caught.exception))
        self.assertIn('found',str(caught.exception))
        self.assertIn('Turn off Open World',str(caught.exception))
        self.assertEqual(bytes(s.data),broken);self.assertEqual(s.undo_stack,[])

    @unittest.skipUnless(DATAS.is_file(),'Requires ignored local game data')
    def test_pinned_randomizer_c5_marker_converts_to_native_skip(self):
        s=EditSession(DATAS.read_bytes());recipe=json.loads(RECIPE.read_text())
        row=next(r for r in recipe['patches'] if r['map_id']==411)
        start=script_roots(s,411)[row['anchor']['key']][0]+row['anchor']['relative_offset']
        original=bytes(s.data);s.data[start]=0xC5;with_randomizer_marker=bytes(s.data)
        changes=apply_world_access(s)['changes']
        self.assertEqual(bytes(s.data[start:start+5]),bytes.fromhex('0205000000'))
        converted=next(r for r in changes if r['map_id']==411)
        self.assertEqual(converted['before'],'c5a200ed00')
        while s.undo_stack:s.undo()
        self.assertEqual(bytes(s.data),with_randomizer_marker)
        self.assertEqual(original[start+1:start+5],with_randomizer_marker[start+1:start+5])

    @unittest.skipUnless(DATAS.is_file(),'Requires ignored local game data')
    def test_repacked_native_process_cluster_resolves_active_copied_code(self):
        data=DATAS.read_bytes();s=EditSession(data);original,_=world_access_plan(s)
        m=original[0][3]['map_id']
        new,report=append_native_process(data,m,'F',b'\xff')
        shifted=EditSession(new,verify=False);latest,_=world_access_plan(shifted)
        affected=[(a,b) for a,b in zip(original,latest) if a[3]['map_id']==m and a[3]['anchor']['kind']=='process']
        self.assertTrue(affected)
        self.assertTrue(any(a[0]!=b[0] for a,b in affected))
        for a,b in affected:self.assertEqual(a[1],b[1])
        apply_world_access(shifted)

    @unittest.skipUnless(EXE.is_file(),'Requires ignored local executable')
    def test_open_world_spawn_composes_with_intro_spawn_and_is_idempotent(self):
        old=EXE.read_bytes();intro,_=patch_intro_spawn(old)
        new,report=patch_open_world_spawn(intro)
        self.assertEqual(report['spawn'],dict(map_id=242,x=38,y=12,z=2,house_variant=260))
        from alundra_memory import parse_exe
        info=parse_exe(new)
        def word(address):return struct.unpack_from('<I',new,0x800+address-info['load_address'])[0]
        self.assertEqual(word(0x80031D58)&0xFFFF,242)
        self.assertEqual(word(0x80031D64)&0xFFFF,38)
        self.assertEqual(word(0x80031D70)&0xFFFF,12)
        self.assertEqual(patch_open_world_spawn(new)[0],new)
        self.assertEqual(patch_open_world_spawn(old)[0],patch_open_world_spawn(intro)[0])


if __name__=='__main__':unittest.main()
