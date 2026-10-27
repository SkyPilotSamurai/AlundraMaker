import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from content_database import ContentDatabase
from event_graph import validate_event_graph


class ProjectEventGraphTests(unittest.TestCase):
    def test_empty_tile_event_can_link_a_reusable_map_class(self):
        db=ContentDatabase()
        npc=db.new("npc","Septimus")
        event=db.new_event_graph(427,"New NPC event",x=18,y=7,class_id=npc["id"])
        self.assertEqual(event["region"],[18,7,1,1])
        self.assertEqual(event["pages"][0]["class_id"],npc["id"])
        loaded=ContentDatabase(db.to_json())
        self.assertEqual(loaded.document["event_graphs"][0]["pages"][0]["class_id"],npc["id"])

    def test_event_class_actions_use_existing_placeable_classes_and_item_classes(self):
        db=ContentDatabase();obj=db.new("object","Stone chest");item=db.new("item","Herb")
        event=db.new_event_graph(12,x=3,y=4)
        event["pages"][0]["commands"]=[
            {"type":"spawn_class","class_id":obj["id"],"position":[3,4]},
            {"type":"give_item","item_class_id":item["id"],"quantity":1,"obtained_message":"Got Herb."},
        ]
        db.replace_event_graph(event["id"],event)
        self.assertEqual(ContentDatabase(db.to_json()).document["event_graphs"][0]["pages"][0]["commands"][0]["class_id"],obj["id"])
        event["class_id"]=item["id"]
        with self.assertRaisesRegex(ValueError,"native item identity"):
            db.replace_event_graph(event["id"],event)

    def test_referenced_classes_cannot_be_deleted_out_from_under_events(self):
        db=ContentDatabase();obj=db.new("object","Torch");event=db.new_event_graph(9,x=2,y=3,class_id=obj["id"])
        with self.assertRaisesRegex(ValueError,"used by a map event"):
            db.delete(obj["id"])

    def test_nested_class_actions_are_checked_and_keep_their_database_links(self):
        db=ContentDatabase();obj=db.new("object","Gate");event=db.new_event_graph(9)
        event["pages"][0]["commands"]=[{"type":"if","condition":{"type":"switch","switch_id":1,"value":True},
            "then":[{"type":"spawn_class","class_id":obj["id"],"position":[1,1]}],"else":[]}]
        db.replace_event_graph(event["id"],event)
        with self.assertRaisesRegex(ValueError,"used by a map event"):
            db.delete(obj["id"])

    def test_event_is_standalone_and_has_rpg_style_pages_and_ordered_commands(self):
        db=ContentDatabase()
        event=db.new_event_graph(427,"Torch and hidden chest")
        event["region"]=[8,12,2,1]
        event["trigger"]="touch"
        event["pages"][0]["commands"]=[
            {"type":"set_switch","switch_id":14,"value":True},
            {"type":"if","condition":{"type":"switch","switch_id":14,"value":True},
             "then":[{"type":"spawn_class","class_id":"object:chest:0001","position":[10,12]}],
             "else":[{"type":"show_dialogue","speaker":"Septimus","text":"The torch is still dark."}]},
            {"type":"give_item","item_class_id":"item:0001","quantity":1,
             "obtained_message":"Obtained Strength Tonic."},
            {"type":"warp_player","map_id":244,"x":9,"y":7},
        ]
        checked=validate_event_graph(event)
        self.assertEqual(checked["region"],[8,12,2,1])
        self.assertEqual(checked["pages"][0]["commands"][1]["then"][0]["type"],"spawn_class")
        self.assertNotIn("npc_instance",checked)
        self.assertNotIn("object_instance",checked)

    def test_graphs_save_as_separate_project_events(self):
        db=ContentDatabase();event=db.new_event_graph(4,"Standalone trigger")
        loaded=ContentDatabase(db.to_json())
        self.assertEqual(loaded.document["event_graphs"],[event])
        loaded.replace_event_graph(event["id"],dict(event,name="Edited region"))
        self.assertEqual(loaded.document["event_graphs"][0]["name"],"Edited region")
        loaded.delete_event_graph(event["id"])
        self.assertEqual(loaded.document["event_graphs"],[])

    def test_invalid_regions_triggers_commands_and_conditions_are_rejected(self):
        event=ContentDatabase().new_event_graph(12)
        for path,value in [
            (("region",),[1,2,0,1]),
            (("trigger",),"telepathy"),
            (("pages",0,"commands"),[{"type":"give_item","item_class_id":""}]),
            (("pages",0,"commands"),[{"type":"set_variable","variable_id":1,"operation":"divide","value":0}]),
            (("pages",0,"conditions"),[{"type":"variable","variable_id":1,"operator":"??","value":0}]),
        ]:
            trial={**event,"pages":[dict(event["pages"][0],commands=[],conditions=[])]}
            if len(path)==1:trial[path[0]]=value
            elif path[0]=="pages":trial["pages"][path[1]][path[2]]=value
            with self.subTest(path=path),self.assertRaises(ValueError):validate_event_graph(trial)


if __name__=="__main__":unittest.main()
