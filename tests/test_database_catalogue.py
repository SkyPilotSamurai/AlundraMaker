import sys,unittest,struct,hashlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from database_catalogue import classify,entity_names,icon_path,preview_hue
from content_database import ContentDatabase
from database_balance import apply_definition_balance
from enemy_definition import BalanceSession,BalanceTable
from event_command_dialog import summary

class CatalogueTests(unittest.TestCase):
 def test_source_catalogue_and_non_item_ice_projectile(self):
  names=entity_names();self.assertEqual(len(names),512)
  self.assertEqual(names[268]['text_fr'].split(' (')[0],'Septimus')
  self.assertEqual(classify(14,'Ice ball'),'object')
  self.assertEqual(classify(31,'I01_Basic sword'),'item')
  self.assertEqual(classify(291,'Generic jar'),'object')
 def test_reference_icons_are_not_swap_or_force_variants(self):
  self.assertEqual(icon_path('Herb').name,'Herbs.png')
  self.assertEqual(icon_path('Cloth Armor').name,'Cloth_Armour.png')
  self.assertEqual(icon_path('Strength Tonic').name,'Strength_Tonic.png')
  self.assertIsNone(icon_path('Invented item'))
 def test_hue_preview_preserves_transparency_and_input(self):
  from PIL import Image
  image=Image.new('RGBA',(2,1));image.putdata([(255,0,0,255),(0,0,0,0)])
  row={'data':{'palette_shift':{'hue_degrees':120}}}
  shown=preview_hue(image,row)
  self.assertEqual([shown.getpixel((x,0)) for x in range(2)],[(0,255,0,255),(0,0,0,0)])
  self.assertEqual(image.getpixel((0,0)),(255,0,0,255))
 def test_native_bank_names_link_distinct_classes(self):
  data=bytearray(40);data[6]=12;data[25]=128;data[26]=12
  db=ContentDatabase()
  maps={1:{'entities':[{'index':0,'offset':'0x0'},{'index':1,'offset':'0x14'}]}}
  with patch('map_inspector.inspect_map',side_effect=lambda _,m:maps.get(m,{'entities':[]})):
   db.scan_instances(data);db.populate_catalogue(data)
  ids=[r['class_id'] for r in db.document['instances']]
  self.assertNotEqual(*ids);self.assertEqual(db.get(ids[1])['name'],'Septimus')
  self.assertEqual(db.get(ids[1])['source']['sprite_bank'],1)
  db.get(ids[1])['name']='Custom scholar'
  with patch('map_inspector.inspect_map',side_effect=lambda _,m:maps.get(m,{'entities':[]})):db.populate_catalogue(data)
  self.assertEqual(db.get(ids[1])['name'],'Custom scholar')
 def test_balance_edits_change_source_and_clones_do_not(self):
  raw=struct.pack('<h',2)+bytes([255,17,20]+[16]*11+[1,129,7]);session=BalanceSession(raw,verify=False)
  db=ContentDatabase();row=db.import_balance_table(raw)[0]
  row['kind']='enemy';row['data']['max_hp']=35;row['data']['attacks'][0]['power']=11
  self.assertTrue(apply_definition_balance(session,row))
  record=BalanceTable(session.data).record(0);self.assertEqual(record['max_hp'],35);self.assertEqual(record['attacks'][0]['power'],11)
  clone=db.duplicate(row['id']);clone['data']['max_hp']=99
  self.assertEqual(clone['source']['native_data_baseline']['max_hp'],20)
  self.assertFalse(apply_definition_balance(session,clone));self.assertEqual(BalanceTable(session.data).record(0)['max_hp'],35)
  other=BalanceSession(struct.pack('<h',2)+bytes([255,17,21]+[16]*11+[1,129,7]),verify=False)
  with self.assertRaisesRegex(ValueError,'differs'):apply_definition_balance(other,row)
  self.assertEqual(db.import_balance_table(bytes(session.data),preserve_existing=True),[])
  self.assertEqual(len(db.definitions),2)
 def test_contents_names_item_and_switch_without_raw_json(self):
  db=ContentDatabase();item=db.new('item','Herb')
  self.assertEqual(summary({'type':'give_item','item_class_id':item['id'],'quantity':1},db),'Herb + 1')
  self.assertEqual(summary({'type':'set_switch','switch_id':20,'value':True},db),'Game #0020 = ON')


 def test_catalogue_available_without_game_or_maps(self):
  db=ContentDatabase();db.populate_catalogue()
  self.assertTrue(all(any(r['kind']==kind for r in db.definitions) for kind in ('npc','enemy','boss','object','item','weapon','player')))
  septimus=next(r for r in db.definitions if r['name']=='Septimus');septimus['name']='My scholar'
  ids=[r['id'] for r in db.definitions];db.populate_catalogue()
  self.assertEqual(ids,[r['id'] for r in db.definitions]);self.assertEqual(septimus['name'],'My scholar')
 def test_missing_maps_do_not_empty_catalogue_and_scan_is_cached(self):
  db=ContentDatabase();data=bytes(40)
  with patch('map_inspector.inspect_map',side_effect=ValueError('Missing map')) as inspect:
   db.scan_all_map_sprites(data);db.scan_instances(data);db.populate_catalogue(data)
   self.assertEqual(inspect.call_count,483)
  self.assertEqual(len(db.document['map_index_errors']),483)
  self.assertTrue(any(r['name']=='Septimus' for r in db.definitions))
  self.assertEqual(db.document['instances'],[])


 def test_missing_map_previews_fall_back_without_blocking_database(self):
  from database_catalogue import reference_image,portrait_image
  row={'kind':'npc','name':'Septimus','source':{'catalogue_index':268,'observed_maps':[1]},'data':{}}
  with patch('native_class_placement.class_preview',side_effect=ValueError('Missing map')):
   self.assertIsNone(reference_image(object(),row))
  with patch('entity_preview.cached_preview',side_effect=ValueError('Missing map')):
   self.assertIsNone(portrait_image(object(),row))

if __name__=='__main__':unittest.main()
