import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from catalogue_names import default_name, apply_default_name, USER_NAMES, USER_NAMES_2026_10_06, refresh_database_names, user_name_basis, capitalize_words
from database_catalogue import entity_names, classify
from content_database import ContentDatabase


class NameTests(unittest.TestCase):
    def test_french_source_defaults_migrate_to_english_without_renaming_custom_npcs(self):
        names=entity_names()
        for index in (358,359,360,402):
            entry=names[index]
            row={'name':entry['text_fr'].split(' (')[0],'source':{}}
            apply_default_name(row,index,entry,'npc')
            expected={358:'Worshiper',360:'Meia (Bound)'}.get(index) or capitalize_words(entry['text_en'].lstrip('◆'))
            self.assertEqual(row['name'],expected)
            row['name']='My NPC'
            apply_default_name(row,index,entry,'npc')
            self.assertEqual(row['name'],'My NPC')

    def test_confirmed_user_names_have_distinct_mud_classes(self):
        names=entity_names()
        for index, expected in USER_NAMES.items():
            value, source=default_name(index,names[index],classify(index,names[index]['text_en']))
            self.assertEqual(value,capitalize_words(expected))
            self.assertEqual(source['name_basis'],user_name_basis(index))
        self.assertIn('Insect man Lv.1',default_name(401,names[401],'enemy')[1]['name_aliases'])
        self.assertIn('Mud man Lv.1',default_name(431,names[431],'enemy')[1]['name_aliases'])

    def test_user_renames_2026_10_07_and_word_capitalisation(self):
        names=entity_names()
        for index,expected in ((1,'Spring Bean'),(358,'Worshiper'),(507,"Zazan's Rock"),(508,"Zazan's Underling"),(230,'Flail Wall (2×2×1) Permanent')):
            self.assertEqual(default_name(index,names[index],classify(index,names[index]['text_en']))[0],expected)
        self.assertEqual(capitalize_words("rock (breakable by iron ball) 1"),"Rock (Breakable By Iron Ball) 1")
        self.assertEqual(capitalize_words("Zazan's rock"),"Zazan's Rock")
        self.assertEqual(capitalize_words("Meia (YM08 variant)"),"Meia (YM08 Variant)")

    def test_native_name_defaults_and_component_names_not_assumed(self):
        names=entity_names()
        self.assertEqual(default_name(399,names[399],'npc')[0],'Keysmith')
        self.assertEqual(default_name(495,names[495],'boss')[0],'Nirude (With Body)')
        value,source=default_name(366,names[366],'enemy')
        self.assertNotEqual(value,'Jeal')
        self.assertFalse(source['name_verified'])
        self.assertEqual(default_name(399,names[399],'npc')[1]['name_pointer_file_offset'],798)

    def test_old_defaults_refresh_custom_names_and_clones_preserved(self):
        entry=entity_names()[329]
        row={'name':'Slime Gel','source':{}}
        apply_default_name(row,329,entry,'enemy')
        self.assertEqual(row['name'],'Puku')
        row['name']='My jelly'
        apply_default_name(row,329,entry,'enemy')
        self.assertEqual(row['name'],'My jelly')
        for flags in ({'user_named':True},{}):
            row={'name':'Slime Gel','source':flags}
            if not flags:row['clone_of']='enemy:0001'
            apply_default_name(row,329,entry,'enemy')
            self.assertEqual(row['name'],'Slime Gel')

    def test_population_migrates_defaults_and_keeps_custom_names(self):
        db=ContentDatabase()
        old=db.new('enemy','Mud man Lv.1');old['source']['catalogue_index']=431
        custom=db.new('enemy','My insect');custom['source']['catalogue_index']=401
        with patch('map_inspector.inspect_map',return_value={'entities':[]}):
            db.populate_catalogue(b'')
        self.assertEqual(old['name'],'Sludge')
        self.assertEqual(custom['name'],'My insect')
        self.assertTrue(custom['source']['name_verified'])

    def test_enemy_level_suffix_is_alias_only_and_custom_names_retained(self):
        names=entity_names();entry=names[338]
        value,meta=default_name(338,entry,'enemy')
        self.assertEqual(value,'Gragg (Axe)')
        self.assertIn('Orc (axe) Lv.1',meta['name_aliases'])
        row={'name':'Orc (axe) Lv.1','source':{}}
        apply_default_name(row,338,entry,'enemy')
        self.assertEqual(row['name'],'Gragg (Axe)')
        row={'name':'My Orc Lv.1','source':{}}
        apply_default_name(row,338,entry,'enemy')
        self.assertEqual(row['name'],'My Orc Lv.1')

    def test_user_npc_names_and_unanswered_identity(self):
        names=entity_names()
        for index,expected in {289:'Dog',355:"Meia's Mother",434:'Kline Nightmare'}.items():
            value,meta=default_name(index,names[index],'npc')
            self.assertEqual(value,expected)
            self.assertEqual(meta['name_basis'],'user confirmed 2026-10-05')
            self.assertNotIn('name_module',meta)
        value,meta=default_name(353,names[353],'npc')
        self.assertEqual(value,'Alicia')
        self.assertFalse(meta['name_verified'])

    def test_cached_us_species_refresh_without_map_scan(self):
        db=ContentDatabase()
        row=db.new('enemy','Muruta (claws)')
        row['source']={'catalogue_index':347,'default_name':'Muruta (claws)',
                       'name_aliases':['Ancient source label']}
        custom=db.new('enemy','My Muruta');custom['source']={'catalogue_index':350,'default_name':'Muruta (bow)'}
        explicit=db.new('enemy','Mimming (spinning)');explicit['source']={'catalogue_index':386,'user_named':True}
        clone=db.duplicate(row['id'])
        with patch('map_inspector.inspect_map',side_effect=AssertionError('Must not scan maps')):
            changes=refresh_database_names(db)
        self.assertEqual(row['name'],'Murgg (Claws)')
        self.assertEqual(custom['name'],'My Muruta')
        self.assertEqual(explicit['name'],'Mimming (spinning)')
        self.assertEqual(clone['name'],'Muruta (claws) Copy')
        self.assertEqual(len(changes),1)
        self.assertIn('Ancient source label',row['source']['name_aliases'])
        self.assertIn('Muruta (claws)',row['source']['name_aliases'])
        self.assertEqual(refresh_database_names(db),[])

    def test_component_spelling_retains_descriptor(self):
        names=entity_names()
        self.assertEqual(default_name(496,names[496],'enemy')[0],'Nirude Rockfall (222)')
        self.assertEqual(default_name(377,names[377],'enemy')[0],'Miming (Scythe)')

if __name__=='__main__':unittest.main()

