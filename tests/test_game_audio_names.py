import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from game_audio_names import music_default_name,sound_default_name,music_name,sound_name
import map_music_ui


class Var:
    def __init__(self,v=''):self.v=v
    def get(self):return self.v
    def set(self,v):self.v=v


class AudioNameTests(unittest.TestCase):
    def test_music_uses_us_names_and_row_offset(self):
        self.assertEqual(music_default_name(0),'No Music')
        self.assertEqual(music_default_name(1),'Alundra, Opening Theme')
        self.assertEqual(music_default_name(2),"Jess's Theme");self.assertEqual(music_default_name(3),'Stormy Seas');self.assertEqual(music_default_name(12),'Sanctuary')
        self.assertEqual(music_default_name(19),'All Hail King Zazan')
        self.assertEqual(music_default_name(4),'Boss Battle I')

    def test_official_soundtrack_titles(self):
        self.assertEqual(music_default_name(16),'The Village Of Inoa')
        self.assertEqual(music_default_name(7),'The Wind That Spans The Earth')
        self.assertEqual(music_default_name(11),'Torla, The Mountain Of Flame')
        self.assertEqual(music_default_name(15),'The Mad Priest Ronan')
        self.assertEqual(music_default_name(6),"Lars's Crypt (Requiem)");self.assertEqual(music_default_name(9),'Reptile Lair')
        self.assertEqual(music_default_name(24),"Septimus's Theme (Unused)");self.assertEqual(music_default_name(21),'The Coal Mine Where Devils Lurk')
        self.assertEqual(music_default_name(30),'Nightmare');self.assertEqual(music_default_name(35),"Meia's Dream")
        self.assertEqual(music_default_name(33),'Melzas')
        self.assertEqual(music_default_name(46),'Sage II')

    def test_evidence_sound_names(self):
        import json
        from pathlib import Path
        rows=json.loads((Path(__file__).resolve().parents[1]/'data/sound-names.json').read_text(encoding='utf-8'))
        self.assertEqual(len(rows),502)
        self.assertFalse(any(r['name'].startswith('Unused Sound') for r in rows.values()))
        self.assertTrue(all(r['name'].endswith('(unverified)') for r in rows.values() if not r['verified']))
        self.assertTrue(all(r['evidence'].get('record') for r in rows.values()))
        self.assertEqual(sound_default_name(300),'Klark Ship: Bird')

    def test_play_sound_search_filters_choices(self):
        import tkinter as tk
        from event_command_dialog import Fields
        root=tk.Tk();root.withdraw()
        try:
            f=Fields(root,None);f.add('sound_id','Sound effect',1,mapped_choices={'001 - Cursor movement':1,'029 - Sword: Swing':29})
            f.add_search('sound_id','Find sound');f.widgets['sound_id_search'].insert(0,'sword')
            self.assertEqual(list(f.widgets['sound_id'].cget('values')),['029 - Sword: Swing']);self.assertEqual(f.readers['sound_id'](),29)
        finally:root.destroy()

    def test_sound_names_are_english_with_us_fixes(self):
        self.assertEqual(sound_default_name(0),'Silence')
        self.assertEqual(sound_default_name(1),'Cursor movement')
        self.assertEqual(sound_default_name(49),'HP recovery item (large)')
        self.assertEqual(sound_default_name(35),'Flail: Swing')
        self.assertEqual(sound_default_name(205),"Village: Murgg's voice")
        self.assertEqual(sound_default_name(87),'Monster Alundra')
        self.assertTrue(all(sound_default_name(i) for i in range(256)))

    def test_user_names_win(self):
        doc={'music_names':{'7':'My field'},'sound_names':{'1':'Blip'}}
        self.assertEqual(music_name(doc,7),'My field');self.assertEqual(sound_name(doc,1),'Blip')
        self.assertEqual(music_name(doc,8),'Flaming Assault')


class MapMusicTests(unittest.TestCase):
    def editor(self):
        return SimpleNamespace(database=SimpleNamespace(document={}),dirty=False)

    def test_override_saved_and_default_clears_it(self):
        e=self.editor()
        self.assertTrue(map_music_ui.set_map_track(e,12,5,default=7))
        self.assertEqual(e.database.document['map_music'],{'12':5});self.assertTrue(e.dirty)
        self.assertTrue(map_music_ui.set_map_track(e,12,7,default=7))
        self.assertNotIn('map_music',e.database.document)

    def test_other_maps_untouched(self):
        e=self.editor();e.database.document['map_music']={'3':9}
        map_music_ui.set_map_track(e,12,5,default=7)
        self.assertEqual(e.database.document['map_music'],{'3':9,'12':5})

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError):map_music_ui.set_map_track(self.editor(),1,47)


if __name__=='__main__':unittest.main()
