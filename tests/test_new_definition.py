import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from content_database import ContentDatabase
class NewDefinitionTests(unittest.TestCase):
 def test_blank_item_and_enemy_require_no_existing_definition(self):
  db=ContentDatabase()
  for kind in ('item','enemy'):
   row=db.new(kind,'Custom '+kind)
   self.assertNotIn('clone_of',row)
   self.assertIsNone(row['source']['sprite_id'])
 def test_optional_template_is_independent_and_keeps_export_clone_marker(self):
  db=ContentDatabase();old=db.new('enemy','Original');old['data']['max_hp']=20
  new=db.new('enemy','New',template_id=old['id'])
  self.assertEqual(new['data']['max_hp'],20);self.assertEqual(new['clone_of'],old['id'])
  new['data']['max_hp']=50;self.assertEqual(old['data']['max_hp'],20)
 def test_wrong_template_kind_does_not_create_entry(self):
  db=ContentDatabase();row=db.new('item');before=len(db.definitions)
  with self.assertRaises(ValueError):db.new('enemy',template_id=row['id'])
  self.assertEqual(len(db.definitions),before)
