import unittest
from pathlib import Path
from copy import deepcopy
from content_database import ContentDatabase

class ReservedItemZeroTests(unittest.TestCase):
    def fixture(self):
        db=ContentDatabase();db.populate_catalogue()
        chest=next(r for r in db.definitions if r.get('source',{}).get('catalogue_index')==30)
        row=db.new('item','Unnamed item 00');row['source']={'balance_entry':30,'balance_sha256':'test','native_data_baseline':deepcopy(row['data'])}
        return db,chest,row
    def test_only_unedited_reserved_duplicate_merges_into_real_chest(self):
        db,chest,row=self.fixture();count=len(db.definitions)
        db._merge_balance_catalogue_duplicates()
        self.assertEqual(len(db.definitions),count-1);self.assertNotIn(row,db.definitions)
        self.assertEqual(chest['source']['balance_entry'],30)
    def test_custom_rename_edit_and_reference_remain(self):
        for change in ('name','data','reference','user_named'):
            db,chest,row=self.fixture()
            if change=='name':row['name']='My box'
            elif change=='data':row['data']['notes']='Customized'
            elif change=='reference':db.document['instances'].append({'class_id':row['id']})
            else:row['source']['user_named']=True
            db._merge_balance_catalogue_duplicates();self.assertIn(row,db.definitions)
    def test_real_balance_import_matches_default_object_catalogue_count(self):
        path=Path(__file__).resolve().parents[1]/'game/disc/DATA/BALANCE.BIN'
        if not path.exists():self.skipTest('Local retail input unavailable')
        db=ContentDatabase();db.populate_catalogue()
        count=sum(r['kind']=='object' for r in db.definitions)
        db.import_balance_table(path.read_bytes(),preserve_existing=True);db.populate_catalogue()
        self.assertEqual(sum(r['kind']=='object' for r in db.definitions),count)
        self.assertEqual(len([r for r in db.definitions if r.get('source',{}).get('catalogue_index')==30]),1)

if __name__=='__main__':unittest.main()
