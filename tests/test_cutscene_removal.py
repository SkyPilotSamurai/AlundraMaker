import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
DISC=ROOT/'game/disc'


@unittest.skipUnless((DISC/'DATA/DATAS.BIN').is_file() and (DISC/'ALUN_CD.EXE').is_file(),'needs the US game files')
class CutsceneRemovalTests(unittest.TestCase):
    def session(self,options):
        from editor_session import EditSession
        s=EditSession((DISC/'DATA/DATAS.BIN').read_bytes(),None,verify=False)
        s.content_database={'mod_options':options};return s

    def test_option_patches_story_cutscenes_fanfares_and_skips_intro(self):
        from editor_qol import apply_qol
        s=self.session({'remove_cutscenes':True});exe=(DISC/'ALUN_CD.EXE').read_bytes()
        out,report=apply_qol(s,exe)
        self.assertTrue(report['options']['skip_intro'])
        cut=next(p for p in report['patches'] if p.get('format')=='alundra-editor-remove-cutscenes-v1')
        self.assertEqual(len(cut['changes']),12)
        self.assertNotIn(325,{c['map_id'] for c in cut['changes']})  # post-Wilda night kept
        self.assertGreater(len(cut['item_fanfares']['items']),40)
        self.assertNotEqual(bytes(s.data),s.original)

    def test_works_with_open_world_and_is_idempotent(self):
        from editor_qol import apply_qol
        from cutscene_removal import apply_cutscene_removal
        s=self.session({'remove_cutscenes':True,'open_world':True})
        apply_qol(s,(DISC/'ALUN_CD.EXE').read_bytes())
        before=bytes(s.data);apply_cutscene_removal(s);self.assertEqual(bytes(s.data),before)


if __name__=='__main__':unittest.main()
