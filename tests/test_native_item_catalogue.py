import unittest,struct
from copy import deepcopy
from unittest.mock import patch
from native_item_catalogue import decode_names,apply_default,native_items
from database_catalogue import item_kind

class NativeItemCatalogueTests(unittest.TestCase):
    def test_resource_pointer_bounds_and_termination(self):
        raw=bytearray(0x808);struct.pack_into('<h',raw,0x400,0x800);raw[0x800:]=b'Herb\0xxx'
        self.assertEqual(decode_names(bytes(raw),1),['Herb'])
        struct.pack_into('<h',raw,0x400,-1);self.assertEqual(decode_names(bytes(raw),1),[None])
        struct.pack_into('<h',raw,0x400,0x700)
        with self.assertRaisesRegex(ValueError,'pointer'):decode_names(bytes(raw),1)
        struct.pack_into('<h',raw,0x400,0x800);raw[0x800:]=b'Herbxxxx'
        with self.assertRaisesRegex(ValueError,'terminated'):decode_names(bytes(raw),1)

    def test_retail_names_and_progressive_identity_mismatches(self):
        items=native_items()
        if items is None:self.skipTest('Local retail input unavailable')
        for i,name in ((52,"Oak's Ring"),(56,'Refresher'),(81,'Small Crystal'),(82,'Large Crystal'),(84,'Dew of Life'),(85,'Drop of Life'),(86,'Water of Life')):
            self.assertEqual(items[i]['name'],name)
        for i,group in ((11,3),(13,4),(15,5),(21,8),(22,8),(23,8),(24,8),(29,10)):
            self.assertEqual(items[i]['slot'],group)
            self.assertEqual(items[i]['name'],f'Unnamed item {i:02X}')
        self.assertEqual(item_kind(15,items),'weapon')
        self.assertEqual(item_kind(29,items),'item')

    def test_recognized_old_default_migrates_without_id_or_runtime_change(self):
        info={'name':'Unnamed item 0D','slot':4,'label_basis':'retail','resource_sha256':'hash','native_metadata':{'menu_group':4}}
        row={'id':'class:0020','name':'Bow upgrade','data':{'slot':2},'source':{'catalogue_index':43,'item_id':13,'native_data_baseline':{'slot':2},'item_label_basis':'local randomizer item.json; progressive labels may differ from vanilla'}}
        apply_default(row,info,{'name':'Bow upgrade','slot':2})
        self.assertEqual(row['name'],'Unnamed item 0D');self.assertEqual(row['data']['slot'],4)
        self.assertEqual(row['source']['native_data_baseline']['slot'],4)
        self.assertEqual((row['id'],row['source']['catalogue_index'],row['source']['item_id']),('class:0020',43,13))

    def test_custom_imported_names_metadata_and_clone_remain_unchanged(self):
        info={'name':'Native','slot':4,'label_basis':'retail','resource_sha256':'hash','native_metadata':{'menu_group':4}}
        for extra,name in (({},'My mod wand'),({'user_named':True},'Bow upgrade')):
            row={'name':name,'source':{'item_label_basis':'imported mod resource',**extra},'data':{'slot':7}}
            before=deepcopy(row);apply_default(row,info,{'name':'Bow upgrade','slot':2});self.assertEqual(row,before)
        row={'clone_of':'base','name':'Clone','source':{},'data':{}}
        before=deepcopy(row);apply_default(row,info);self.assertEqual(row,before)

    def test_populate_keeps_custom_imported_item_kind_and_category(self):
        from content_database import ContentDatabase
        db=ContentDatabase();db.populate_catalogue()
        row=next(r for r in db.definitions if r.get('source',{}).get('item_id')==15)
        row['name']='Modded shield';row['kind']='armor';row['source']['item_label_basis']='imported mod resource'
        row['data']['item_category']='Accessory';row['data']['slot']=7
        row['source']['item_metadata_native']={'custom_preimage':True}
        db.populate_catalogue()
        self.assertEqual((row['name'],row['kind'],row['data']['slot'],row['data']['item_category']),('Modded shield','armor',7,'Accessory'))
        self.assertEqual(row['source']['item_metadata_native'],{'custom_preimage':True})

if __name__=='__main__':unittest.main()
