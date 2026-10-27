import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from content_database import ContentDatabase
from placement_catalogue import placement_info,placement_rows,annotate_placement_sources,database_rows


def source(db,kind,name,index):
    row=db.new(kind,name);row['source']={'catalogue_index':index};return row


class PlacementCatalogueTests(unittest.TestCase):
    def test_user_confirmed_werewolf_and_soul_leech_boss_tabs(self):
        from database_catalogue import classify
        db=ContentDatabase();leech=source(db,'enemy','Soul Leech',476)
        wolf=source(db,'enemy','Werewolf',482)
        self.assertEqual(database_rows(db,'boss'),[leech,wolf])
        self.assertEqual(database_rows(db,'enemy'),[])
        self.assertEqual(classify(476,'Suction unit'),'boss')
        self.assertEqual(classify(482,'Werewolf Lv.1'),'boss')

    def test_twin_demons_is_one_boss(self):
        # 501 is made by 500 in the fight and never placed: only Twin Demons (500) is a boss.
        db=ContentDatabase();boss=source(db,'boss','Twin Demons',500);half=source(db,'boss','Twin younger',501)
        self.assertEqual(placement_rows(db,'Bosses'),[boss])
        self.assertEqual(placement_info(boss,db)['role'],'primary')
        from database_catalogue import HIDDEN_CATALOGUE
        self.assertIn(501,HIDDEN_CATALOGUE)

    def test_parts_leave_primary_boss_tab_without_deletion(self):
        db=ContentDatabase();boss=source(db,'boss','Melzas',418)
        part=source(db,'boss','Custom laser label',419)
        before=db.to_json();self.assertEqual(placement_rows(db,'Bosses'),[boss])
        self.assertEqual(placement_rows(db,'Misc'),[part])
        self.assertEqual(placement_rows(db,'boss',True),[boss,part])
        self.assertEqual(placement_info(part,db)['primary_class_id'],boss['id'])
        self.assertFalse(placement_info(part,db)['standalone_supported'])
        self.assertEqual(db.to_json(),before)

    def test_items_and_effects_distinct_native_identity_preserved(self):
        db=ContentDatabase();herb=source(db,'item','Herb',48)
        sword=source(db,'weapon','Sword',31);fire=source(db,'object','Fireball',11)
        pot=source(db,'object','Vase',291);npc=source(db,'npc','Jess',260)
        self.assertEqual(placement_rows(db,'Items'),[sword,herb])
        self.assertEqual(placement_rows(db,'Misc'),[fire])
        self.assertEqual(placement_rows(db,'Objects'),[pot])
        self.assertEqual(placement_rows(db,'NPCs'),[npc])
        self.assertEqual(placement_info(herb)['placement_default'],'map_pickup')

    def test_clones_user_names_and_ambiguous_parts_preserved(self):
        db=ContentDatabase();enemy=source(db,'enemy','Slime Gel',329)
        projectile=source(db,'enemy','Projectile',330);clone=db.duplicate(projectile['id'])
        clone['name']='My purple projectile';unknown=source(db,'enemy','King fragments',483)
        self.assertIsNone(placement_info(unknown,db)['primary_class_id'])
        annotate_placement_sources(db)
        restored=ContentDatabase(db.to_json())
        self.assertEqual(len(restored.definitions),4)
        self.assertEqual(restored.get(clone['id'])['name'],'My purple projectile')
        self.assertEqual(placement_rows(restored,'Enemies'),[restored.get(enemy['id'])])
        self.assertEqual(len(placement_rows(restored,'Misc')),3)

    def test_named_head_can_be_primary_and_invalid_tab_rejected(self):
        db=ContentDatabase();head=source(db,'enemy','Wilda head',412)
        body=source(db,'enemy','Wilda body',413)
        self.assertEqual(placement_rows(db,'boss'),[head])
        self.assertEqual(placement_info(body,db)['primary_catalogue_index'],412)
        with self.assertRaises(ValueError):placement_rows(db,'Invented')

    def test_database_enemy_list_excludes_attacks_preserves_references(self):
        db=ContentDatabase();enemy=source(db,'enemy','Worm',410)
        attack=source(db,'enemy','Projectile',411)
        creature=source(db,'enemy','Lizardman (projectiles)',371)
        before=db.to_json()
        self.assertEqual(database_rows(db,'enemy'),[creature,enemy])
        self.assertEqual(database_rows(db,'misc'),[attack])
        self.assertEqual(database_rows(db,'unclassified'),[attack])
        self.assertEqual(db.to_json(),before)


if __name__=='__main__':unittest.main()
