import sys
import unittest
from copy import deepcopy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from content_database import ContentDatabase

class DuplicateImportTests(unittest.TestCase):
 def fixture(self):
  db=ContentDatabase();target=db.new('object','Jar')
  target['source']={'catalogue_index':291,'native_data_baseline':deepcopy(target['data'])}
  duplicate=db.new('object','Jar');duplicate['data']['max_hp']=4
  duplicate['source']={'balance_entry':291,'balance_sha256':'test','tier_offsets':[20],
                       'native_data_baseline':deepcopy(duplicate['data'])}
  return db,target,duplicate
 def test_merge_links_graphics_stats_and_references(self):
  db,target,duplicate=self.fixture()
  db.document['instances'].append({'class_id':duplicate['id']})
  db._merge_balance_catalogue_duplicates()
  self.assertEqual(len(db.definitions),1)
  self.assertEqual(target['data']['max_hp'],4)
  self.assertEqual(target['source']['balance_entry'],291)
  self.assertEqual(db.document['instances'][0]['class_id'],target['id'])
  db._merge_balance_catalogue_duplicates();self.assertEqual(len(db.definitions),1)
 def test_authored_changes_and_clones_preserved(self):
  db,target,duplicate=self.fixture();duplicate['data']['max_hp']=99
  db._merge_balance_catalogue_duplicates()
  self.assertEqual(len(db.definitions),2)
  self.assertEqual(duplicate['source']['catalogue_index'],291)
  db,target,duplicate=self.fixture();duplicate['clone_of']=target['id']
  db._merge_balance_catalogue_duplicates();self.assertEqual(len(db.definitions),2)
 def test_canonical_edits_are_not_overwritten(self):
  db,target,duplicate=self.fixture()
  target['data']['max_hp']=88;target['source']['native_data_baseline']['max_hp']=None
  db._merge_balance_catalogue_duplicates()
  self.assertEqual(target['data']['max_hp'],88)
  self.assertEqual(target['source']['native_data_baseline']['max_hp'],4)
