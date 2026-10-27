import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from editor_session import EditSession
from event_graph import new_event_graph
from event_export import prepare_native_event_export, EventExportError
from event_editor import instructions
from map_inspector import inspect_map
from map_text import entries
from native_class_placement import append_record_cluster, record_cluster
from test_native_script_allocation import fixture


class NewEventCompileTests(unittest.TestCase):
    def setUp(self):
        self.session = EditSession(fixture(), verify=False)
        self.grid = patch("area_map.grid", return_value=(8, 8, [{"values": [0, 0, 0, 1]}] * 64))
        self.grid.start(); self.addCleanup(self.grid.stop)
        callbacks = patch("event_vm_compatibility.sprite_callbacks", return_value=[("A", 0), ("C", 0), ("D", 0), ("E", 0), ("F", 0)])
        callbacks.start(); self.addCleanup(callbacks.stop)
        self.graph = new_event_graph("event:0001", 2, "New trigger", 3, 4)
        self.graph["pages"][0]["trigger"] = "touch"
        self.graph["pages"][0]["commands"] = [{"type": "show_dialogue", "text": "Hi"},
            {"type": "set_switch", "native_flag_operand": 0x8001, "value": True}]
        self.session.content_database = {"definitions": [], "event_graphs": [self.graph]}

    def test_new_touch_region_has_native_code_and_new_dialogue(self):
        original = bytes(self.session.data)
        exported = prepare_native_event_export(self.session)
        events = inspect_map(exported.data, 2)["events"]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[-1]["rectangle"], (3, 4, 3, 4))
        key = f"B {events[-1]['bank_b_index']}"
        self.assertEqual([(op, size) for _, op, size in instructions(exported, 2, key)], [(13, 3), (0x39, 1), (5, 3), (255, 1)])
        self.assertIn(b"Hi", [row[2] for row in entries(exported, 2)])
        self.assertEqual(bytes(self.session.data), original)

    def test_key_door_yield_guard_precedes_donor_import(self):
        self.graph['pages'][0].update(trigger='activate',class_id='object:door',commands=[
            {'type':'if','condition':{'type':'switch','native_flag_operand':1,'value':True},
             'then':[],'else':[{'type':'wait','frames':60}]}])
        self.session.content_database['definitions']=[{'id':'object:door','kind':'object','source':{'catalogue_index':324}}]
        original=bytes(self.session.data)
        with self.assertRaisesRegex(EventExportError,'retained native continuation'):
            prepare_native_event_export(self.session)
        self.assertEqual(bytes(self.session.data),original)

    def test_flame_pillar_contents_guard_precedes_donor_import(self):
        self.graph['pages'][0].update(trigger='activate',class_id='object:pillar',commands=[{'type':'change_money','amount':1}])
        self.session.content_database['definitions']=[{'id':'object:pillar','kind':'object','source':{'catalogue_index':316}}]
        with self.assertRaisesRegex(EventExportError,'native passive cycle only'):
            prepare_native_event_export(self.session)

    def test_class_donor_native_interaction_has_new_script_hook(self):
        raw = bytes([0, 0, 7, 7, 1, 0, 4, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        self.session.data, _ = append_record_cluster(self.session.data, 2, entities=[raw])
        self.graph["pages"][0].update(trigger="interact", class_id="npc:test")
        self.graph["pages"][0]["commands"] = [{"type": "show_dialogue", "text": "Hi"}]
        self.graph["native_placement"] = {"donor_entity_index": 0}
        self.session.content_database["definitions"] = [{"id": "npc:test", "kind": "npc", "source": {"catalogue_index": 4}}]
        exported = prepare_native_event_export(self.session)
        entities = record_cluster(exported.data, 2)["entities"]
        self.assertEqual(entities[0], raw)
        self.assertEqual(len(entities), 2)
        self.assertEqual(entities[-1][7:10], bytes([6, 8, 2]))
        self.assertTrue(entities[-1][15] & 128)
        key = f"F {entities[-1][15] & 127}"
        self.assertEqual([row[1] for row in instructions(exported, 2, key)[:2]], [0x27, 13])

    def _npc_interact(self, placement, commands=None):
        raw = bytes([0, 0, 7, 7, 1, 0, 4, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        self.session.data, _ = append_record_cluster(self.session.data, 2, entities=[raw])
        self.graph["pages"][0].update(trigger="interact", class_id="npc:test")
        self.graph["pages"][0]["commands"] = commands or [{"type": "show_dialogue", "text": "Hi"}]
        self.graph["native_placement"] = dict(donor_entity_index=0, **placement)
        self.session.content_database["definitions"] = [{"id": "npc:test", "kind": "npc", "source": {"catalogue_index": 4}}]
        exported = prepare_native_event_export(self.session)
        return exported, record_cluster(exported.data, 2)["entities"][-1]

    def test_direction_fix_npc_does_not_turn_to_player(self):
        exported, row = self._npc_interact({"direction_fix": True})
        self.assertEqual(instructions(exported, 2, f"F {row[15] & 127}")[0][1], 13)

    def test_lock_and_unlock_movement_compile_to_native_control_opcodes(self):
        exported, row = self._npc_interact({}, [{"type": "lock_movement"}, {"type": "show_dialogue", "text": "Hi"},
                                                {"type": "unlock_movement"}])
        ops = [r[1] for r in instructions(exported, 2, f"F {row[15] & 127}")]
        self.assertIn(0x27, ops); self.assertLess(ops.index(0x27), ops.index(0x10)); self.assertLess(ops.index(0x10), ops.index(13))
        self.assertLess(ops.index(13), ops.index(0x11))

    def test_chosen_npc_animation_installs_load_program(self):
        with patch("event_movement_compile.animation_profile", return_value=[0, 1, 2]):
            exported, row = self._npc_interact({"animation": 2})
        self.assertTrue(row[12] & 128)
        self.assertEqual([r[1] for r in instructions(exported, 2, f"C {row[12] & 127}")], [0x1A, 0xFF])

    def test_mismatched_class_and_unimplemented_commands_fail_before_output(self):
        self.graph["pages"][0]["commands"] = [{"type": "move_actor", "target": "self", "mode": "toward_player"}]
        with self.assertRaisesRegex(EventExportError, "no verified native compiler"):
            prepare_native_event_export(self.session)

    def test_self_route_is_in_order_and_reaches_native_process(self):
        raw=bytes([0,0,7,7,1,0,4,2,2,2]+[0]*10)
        self.session.data,_=append_record_cluster(self.session.data,2,entities=[raw])
        self.graph['pages'][0].update(trigger='interact',class_id='npc:test',commands=[
            {'type':'move_actor','target':'this_event','mode':'walk_tiles','tiles':1,'direction':'down','moving_animation':0,'idle_animation':1},
            {'type':'show_dialogue','text':'Arrived'}])
        self.graph['native_placement']={'donor_entity_index':0}
        self.session.content_database['definitions']=[{'id':'npc:test','kind':'npc','source':{'catalogue_index':4}}]
        route=bytes.fromhex('09001a001e10001a0100')
        old=bytes(self.session.data)
        with patch('event_movement_compile.compile_movement_command',return_value=route) as compiler:
            with self.assertRaisesRegex(EventExportError,'retained movement continuation'):
                prepare_native_event_export(self.session)
        compiler.assert_not_called()
        self.assertEqual(bytes(self.session.data),old)

    def test_multiple_new_events_preserve_both_native_hooks(self):
        other = new_event_graph("event:0002", 2, "Other", 5, 5)
        other["pages"][0].update(trigger="touch", commands=[{"type": "show_dialogue", "text": "Other"}])
        self.session.content_database["event_graphs"].append(other)
        exported = prepare_native_event_export(self.session)
        events = inspect_map(exported.data, 2)["events"]
        self.assertEqual(len(events), 3)
        self.assertNotEqual(events[1]["program"], events[2]["program"])
        for event in events[1:]:
            self.assertEqual(instructions(exported, 2, f"B {event['bank_b_index']}")[-1][1], 255)
        self.assertTrue({b"Hi", b"Other"}.issubset({row[2] for row in entries(exported, 2)}))

    def test_chest_uses_builtin_callbacks_and_independent_no_flag_contents(self):
        raw = bytes([0, 0, 7, 7, 1, 64, 30, 2, 2, 2, 1, 2, 3, 4, 5, 6, 17, 0, 1, 0])
        self.session.data, _ = append_record_cluster(self.session.data, 2, entities=[raw])
        self.graph["pages"][0].update(trigger="interact", class_id="object:chest", commands=[])
        self.graph["native_placement"] = {"donor_entity_index": 0}
        self.session.content_database["definitions"] = [
            {"id": "object:chest", "kind": "object", "source": {"catalogue_index": 30}, "data": {"contained_item_class_id": "item:herb"}},
            {"id": "item:herb", "kind": "item", "source": {"catalogue_index": 66, "item_id": 36}}]
        with patch("new_event_compile.verified_chest_template", return_value=raw):
            exported = prepare_native_event_export(self.session)
        records = record_cluster(exported.data, 2)["entities"]
        self.assertEqual(records[0], raw)
        self.assertEqual(records[1][10:16], bytes(6))
        self.assertEqual(records[1][16:18], bytes([0xFE, 0x07]))   # saved chest flag 2046 (FREE_CHEST_FLAGS)
        self.assertEqual(records[1][18:20], bytes([36, 0]))
        self.assertTrue(exported.native_event_export_report[0]["native_chest"])

    def test_each_placed_chest_can_override_its_shared_class_item(self):
        raw = bytes([0, 0, 7, 7, 1, 64, 30, 2, 2, 2, 1, 2, 3, 4, 5, 6, 17, 0, 1, 0])
        self.session.data, _ = append_record_cluster(self.session.data, 2, entities=[raw])
        self.graph["pages"][0].update(trigger="interact", class_id="object:chest", commands=[],
                                      contained_item_class_id="item:tonic")
        self.graph["native_placement"] = {"donor_entity_index": 0}
        self.session.content_database["definitions"] = [
            {"id": "object:chest", "kind": "object", "source": {"catalogue_index": 30},
             "data": {"contained_item_class_id": "item:herb"}},
            {"id": "item:herb", "kind": "item", "source": {"catalogue_index": 66, "item_id": 36}},
            {"id": "item:tonic", "kind": "item", "source": {"catalogue_index": 67, "item_id": 37}}]
        with patch("new_event_compile.verified_chest_template", return_value=raw) as verify:
            exported = prepare_native_event_export(self.session)
        records = record_cluster(exported.data, 2)["entities"]
        self.assertEqual(records[1][18:20], bytes([37, 0]))
        self.assertEqual(verify.call_args_list[-1].args[1], 37)

    def test_unassigned_placed_chest_is_rejected_with_actionable_message(self):
        raw = bytes([0, 0, 7, 7, 1, 64, 30, 2, 2, 2, 1, 2, 3, 4, 5, 6, 17, 0, 1, 0])
        self.session.data, _ = append_record_cluster(self.session.data, 2, entities=[raw])
        self.graph["pages"][0].update(trigger="interact", class_id="object:chest", commands=[])
        self.graph["native_placement"] = {"donor_entity_index": 0}
        self.session.content_database["definitions"] = [
            {"id": "object:chest", "kind": "object", "source": {"catalogue_index": 30}, "data": {}}]
        with self.assertRaisesRegex(ValueError, "Choose an item for the placed Chest"):
            prepare_native_event_export(self.session)

    def test_conditional_pages_install_one_dispatch_process(self):
        self.graph["pages"].append({"id": "page:second", "name": "Second", "trigger": "touch",
            "conditions": [{"type": "switch", "switch_id": 7, "native_flag_operand": 7, "value": True}],
            "commands": [{"type": "show_dialogue", "text": "Second"}]})
        exported = prepare_native_event_export(self.session)
        events = inspect_map(exported.data, 2)["events"]
        self.assertEqual(len(events), 2)
        ops = [row[1] for row in instructions(exported, 2, f"B {events[-1]['bank_b_index']}")]
        self.assertIn(0x31, ops)
        self.assertEqual(ops.count(0x0D), 2)
        self.assertTrue({b"Hi", b"Second"}.issubset({row[2] for row in entries(exported, 2)}))

    def test_page_graphic_change_rejects_instead_of_silently_keeping_sprite(self):
        self.graph["pages"].append({"id": "page:second", "name": "Second", "trigger": "touch",
            "class_id": "npc:new", "conditions": [], "commands": []})
        # later pages with another character are split into their own actor (2026-10-21); an unknown one still rejects
        with self.assertRaisesRegex(EventExportError, "existing placeable database class"):
            prepare_native_event_export(self.session)

    def test_other_existing_speaker_uses_native_selector_dialogue(self):
        raw = bytes([0, 0, 7, 7, 1, 64, 4, 2, 2, 2] + [0] * 10)
        self.session.data, _ = append_record_cluster(self.session.data, 2, entities=[raw])
        self.graph["pages"][0]["commands"] = [{"type": "show_dialogue", "text": "Other speaker", "native_speaker_entity_index": 0}]
        exported = prepare_native_event_export(self.session)
        report = exported.native_event_export_report[0]
        rows = instructions(exported, 2, f"B {report['root_index']}")
        self.assertEqual(rows[0][1:], (0x5C, 4))
        self.assertEqual(exported.data[rows[0][0]+1], 0)

    def test_missing_speaker_is_not_silently_ignored(self):
        self.graph["pages"][0]["commands"] = [{"type": "show_dialogue", "text": "Who", "speaker": "npc:missing"}]
        with self.assertRaisesRegex(EventExportError, "speaker instance"):
            prepare_native_event_export(self.session)

    def test_global_hue_rejects_without_silent_metadata_export(self):
        self.graph["pages"][0]["class_id"] = "npc:hue"
        self.session.content_database["definitions"] = [{"id": "npc:hue", "kind": "npc",
            "source": {"catalogue_index": 4}, "data": {"palette_shift": {"hue_degrees": 90}}}]
        with self.assertRaisesRegex(EventExportError, "global class recolors"):
            prepare_native_event_export(self.session)

    def test_herb_gift_uses_direct82_without_pickup_allocation(self):
        raw = bytes([0, 0, 7, 7, 1, 64, 66, 2, 2, 2] + [0] * 10)
        self.graph["pages"][0]["commands"] = [{"type": "give_item", "item_class_id": "item:herb", "quantity": 1}]
        self.session.content_database["definitions"] = [{"id": "item:herb", "kind": "item", "source": {"catalogue_index": 66, "item_id": 36}}]
        old = bytes(self.session.data)
        with patch("new_event_compile.find_item_template", return_value={"raw": raw}):
            exported=prepare_native_event_export(self.session)
        cluster=record_cluster(exported.data,2)
        self.assertFalse(cluster['entities'])
        self.assertEqual([op for _,op,_ in instructions(exported,2,f"B {cluster['events'][-1][4]&127}")],[0x82,0x0D,0x39,255])   # default "obtained" text + wait
        self.assertEqual(bytes(self.session.data), old)

    def test_gift_missing_donor_and_custom_message_are_explicit_errors(self):
        self.session.content_database["definitions"] = [{"id": "item:herb", "kind": "item", "source": {"catalogue_index": 66, "item_id": 36}}]
        command = {"type": "give_item", "item_class_id": "item:herb", "quantity": 1}
        self.graph["pages"][0]["commands"] = [command]
        with patch("new_event_compile.find_item_template", return_value=None), patch("new_event_compile.verified_item_pickup_template", return_value=None):
            prepare_native_event_export(self.session)
        command["obtained_message"] = "Custom message"
        with self.assertRaisesRegex(EventExportError, "no automatic obtained-item message"):
            prepare_native_event_export(self.session)


if __name__ == "__main__":
    unittest.main()
