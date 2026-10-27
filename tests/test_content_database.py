import json,sys,tempfile,unittest
import struct
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from content_database import ContentDatabase
from editor_session import EditSession
from mod_export import save_mod,load_mod
from event_graph import new_event_graph

class ContentDatabaseTests(unittest.TestCase):
 def test_duplicate_keeps_editable_data_and_gets_new_id(self):
  db=ContentDatabase();npc=db.new("npc","Mira");npc["data"]["dialogue_sprite"]=23
  clone=db.duplicate(npc["id"])
  self.assertNotEqual(npc["id"],clone["id"]);self.assertEqual(clone["clone_of"],npc["id"])
  self.assertEqual(clone["data"]["dialogue_sprite"],23)
  clone["data"]["dialogue_sprite"]=24
  self.assertEqual(db.get(npc["id"])["data"]["dialogue_sprite"],23)
  self.assertNotEqual(npc["class_key"],clone["class_key"])

 def test_rejects_duplicate_ids_and_bad_shapes(self):
  db=ContentDatabase();row=db.new("weapon")
  with self.assertRaises(ValueError):db.replace(row["id"],dict(row,data=[]))
  doc=db.to_json();doc["definitions"].append(dict(row))
  with self.assertRaises(ValueError):ContentDatabase(doc)

 def test_imports_balance_tiers_as_raw_source_data(self):
  data=struct.pack("<hh",4,4)+bytes([255,17,20]+[16]*11+[1,129,7])
  db=ContentDatabase();rows=db.import_balance_table(data)
  self.assertEqual(len(rows),2)
  self.assertEqual(rows[0]["data"]["balance_tiers"][0]["max_hp"],20)
  self.assertEqual(rows[0]["data"]["balance_tiers"][0]["attacks_raw"],[{"attribute":129,"power":7}])

 def test_object_reactions_are_single_trigger_rows_and_animations_duplicate(self):
  db=ContentDatabase();obj=db.new("object","Gate plate")
  obj["data"]["reactions"]["player_standing"]={"activate":True,"destroy":False}
  obj["data"]["animations"]=[{"name":"activate","ticks_per_frame":3,"frames":[1,4,8]}]
  clone=db.duplicate(obj["id"])
  self.assertEqual(clone["data"]["reactions"]["player_standing"],{"activate":True,"destroy":False})
  self.assertEqual(clone["data"]["animations"][0]["ticks_per_frame"],3)
  self.assertEqual(clone["data"]["animations"][0]["frames"],[1,4,8])

 def test_animation_frames_and_speed_are_available_to_all_definition_types(self):
  db=ContentDatabase()
  for kind in ("npc","enemy","boss","object","item","weapon","player"):
   row=db.new(kind)
   animation=row["data"]["animations"][0]
   animation.update(ticks_per_frame=3,frames=[7,2,9])
   db.replace(row["id"],row)
  loaded=ContentDatabase(db.to_json())
  for row in loaded.definitions:
   self.assertEqual(row["data"]["animations"][0],{"name":"idle","ticks_per_frame":3,"frames":[7,2,9]})

 def test_animation_validation_applies_to_npcs_and_enemies_too(self):
  for kind in ("npc","enemy","boss"):
   row=ContentDatabase().new(kind)
   row["data"]["animations"][0]["ticks_per_frame"]=0
   with self.subTest(kind=kind),self.assertRaises(ValueError):ContentDatabase({"format":"alundra-content-database-v1","definitions":[row]})

 def test_database_round_trips_with_named_mod(self):
  session=EditSession(bytes(64),verify=False);session.replace(10,b"edit","test")
  database=ContentDatabase();row=database.new("weapon","Saber")
  row["data"].update(slot=2,damage=17,charge_frames=40,attack_animation_frames=24)
  row["data"]["animations"][0].update(ticks_per_frame=2,frames=[11,3,7])
  npc=database.new("npc","Mira");npc["data"]["animations"][0].update(ticks_per_frame=5,frames=[4,6])
  database.document["instances"]=[{"id":"fixture:map:4:entity:0","map_id":4,"entity_index":0,"class_id":npc["id"],"source":{"build_sha256":"fixture","sprite_id":7,"offset":"0x100"}}]
  session.content_database=database.to_json()
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/"example.alundramod";save_mod(session,path,"Example",1)
   with patch("editor_session.verify_datas"):
    loaded,_=load_mod(session.original,path)
   self.assertEqual(loaded.data,session.data)
   self.assertEqual(loaded.content_database,session.content_database)
   self.assertEqual(loaded.content_database["definitions"][0]["data"]["animations"][0]["frames"],[11,3,7])
   self.assertEqual(loaded.content_database["definitions"][0]["data"]["animations"][0]["ticks_per_frame"],2)
   self.assertEqual(loaded.content_database["definitions"][1]["data"]["animations"][0]["frames"],[4,6])
   self.assertEqual(loaded.content_database["instances"][0]["class_id"],npc["id"])

 def test_map_instances_link_to_shared_sprite_class_and_survive_reload(self):
  db=ContentDatabase();klass=db.new("npc","Mira")
  klass["source"]={"build_sha256":None,"sprite_id":7}
  data=bytearray(16);data[6]=7;data[14]=7
  maps={3:{"entities":[{"index":0,"offset":"0x0"}]},
        4:{"entities":[{"index":2,"offset":"0x8"}]}}
  with patch("map_inspector.inspect_map",side_effect=lambda _data,m:maps.get(m,{"entities":[]})):
   instances=db.scan_instances(bytes(data))
  self.assertEqual(len(instances),2)
  self.assertEqual({row["class_id"] for row in instances},{klass["id"]})
  self.assertEqual(instances[0]["source"]["sprite_id"],7)
  loaded=ContentDatabase(db.to_json())
  self.assertEqual(len(loaded.document["instances"]),2)
  loaded.delete(klass["id"])
  self.assertTrue(all(row["class_id"] is None for row in loaded.document["instances"]))

 def test_scanning_edited_placements_keeps_base_build_identity(self):
  db=ContentDatabase();klass=db.new("npc","Septimus")
  base=bytes(16);edited=bytearray(base);edited[6]=9
  klass["source"]={"build_sha256":__import__("hashlib").sha256(base).hexdigest(),"sprite_id":9}
  with patch("map_inspector.inspect_map",return_value={"entities":[{"index":0,"offset":"0x0"}]}):
   instances=db.scan_instances(bytes(edited),source_datas=base)
  self.assertEqual(instances[0]["class_id"],klass["id"])
  self.assertEqual(instances[0]["source"]["build_sha256"],__import__("hashlib").sha256(base).hexdigest())

 def test_object_class_can_reference_an_item_for_chest_or_drop_content(self):
  db=ContentDatabase();chest=db.new("object","Small chest");item=db.new("item","Strength Tonic")
  chest["data"]["contained_item_class_id"]=item["id"]
  db.replace(chest["id"],chest)
  loaded=ContentDatabase(db.to_json())
  self.assertEqual(loaded.get(chest["id"])["data"]["contained_item_class_id"],item["id"])
  loaded.delete(item["id"])
  self.assertIsNone(loaded.get(chest["id"])["data"]["contained_item_class_id"])

 def test_object_class_cannot_link_non_item_as_contents(self):
  db=ContentDatabase();chest=db.new("object","Vase");npc=db.new("npc","Septimus")
  chest["data"]["contained_item_class_id"]=npc["id"]
  with self.assertRaisesRegex(ValueError,"item class"):db.replace(chest["id"],chest)

 def test_placed_chest_page_can_select_its_own_database_item(self):
  db=ContentDatabase();chest=db.new('object','Chest');chest['source']={'catalogue_index':30};db.replace(chest['id'],chest)
  item=db.new('item','Strength Tonic')
  event=new_event_graph('event:chest',427,'Chest',8,9,chest['id'])
  event['pages'][0]['contained_item_class_id']=item['id']
  document=db.to_json();document['event_graphs']=[event]
  loaded=ContentDatabase(document)
  self.assertEqual(loaded.document['event_graphs'][0]['pages'][0]['contained_item_class_id'],item['id'])

 def test_page_chest_contents_rejects_missing_or_non_item_classes(self):
  db=ContentDatabase();chest=db.new('object','Chest');chest['source']={'catalogue_index':30};db.replace(chest['id'],chest)
  npc=db.new('npc','Septimus');event=new_event_graph('event:chest',427,'Chest',8,9,chest['id'])
  event['pages'][0]['contained_item_class_id']=npc['id']
  document=db.to_json();document['event_graphs']=[event]
  with self.assertRaisesRegex(ValueError,'Chest contents'):
   ContentDatabase(document)

class BossPartLinkTests(unittest.TestCase):
    def test_boss_parts_are_linked_and_a_donorless_part_cannot_be_placed_alone(self):
        db=ContentDatabase()
        boss=db.new('boss','Melzas');boss['source']['catalogue_index']=418
        part=db.new('boss','Melzas Double');part['source']['catalogue_index']=424
        self.assertEqual(db.ensure_boss_parts(),[424])
        self.assertEqual(boss['source']['boss_parts'],[419,420,423,424]);self.assertEqual(part['source']['boss_part_of'],418)
        event=lambda cid:{'id':'e','pages':[{'id':'p','commands':[]}],'class_id':cid}
        with self.assertRaisesRegex(ValueError,'part of Melzas'):db._validate_event_classes(event(part['id']))
        db._validate_event_classes(event(boss['id']))

if __name__=="__main__":unittest.main()
