import copy
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
from editor_session import EditSession
from event_graph import new_event_graph
from event_export import prepare_native_event_export, generated_event_opcodes, EventExportError
from event_editor import instructions
from native_class_placement import append_record_cluster, record_cluster
from test_native_script_allocation import fixture


class ConditionalNpcPresenceTests(unittest.TestCase):
    def setUp(self):
        self.session = EditSession(fixture(), verify=False)
        self.donor = bytes([0, 0, 7, 7, 1, 3, 4, 2, 2, 2] + [0] * 10)
        self.session.data, _ = append_record_cluster(self.session.data, 2, entities=[self.donor])
        self.graph = new_event_graph('event:presence', 2, 'Conditional NPC', 3, 4)
        self.graph['pages'][0].update(trigger='interact', class_id='npc:test',
            conditions=[{'type': 'switch', 'native_flag_operand': 0x8007, 'value': True}],
            commands=[{'type': 'show_dialogue', 'text': 'Visible'}])
        self.graph['native_placement'] = {'donor_entity_index': 0, 'presence_by_page_condition': True}
        self.session.content_database = {'definitions': [{'id': 'npc:test', 'kind': 'npc',
            'source': {'catalogue_index': 4}}], 'event_graphs': [self.graph]}
        grid = patch('area_map.grid', return_value=(8, 8, [{'values': [0, 0, 0, 1]}] * 64))
        grid.start(); self.addCleanup(grid.stop)
        callbacks = patch('event_vm_compatibility.sprite_callbacks', return_value=[('A', 0), ('C', 0), ('D', 0), ('E', 0), ('F', 0)])
        callbacks.start(); self.addCleanup(callbacks.stop)

    def test_separate_controller_targets_actual_actor_and_preserves_source(self):
        original = bytes(self.session.data); old_graph = copy.deepcopy(self.graph)
        old = record_cluster(self.session.data, 2)
        exported = prepare_native_event_export(self.session)
        cluster = record_cluster(exported.data, 2)
        self.assertEqual(cluster['entities'][0], self.donor)
        self.assertEqual(cluster['events'][:len(old['events'])], old['events'])
        self.assertEqual(len(cluster['entities']), 2)
        actor = cluster['entities'][1]
        self.assertFalse(actor[5] & 0x40)
        report = exported.native_event_export_report[0]
        watcher = report['presence_controller']
        self.assertEqual(watcher['template_index'], 1)
        self.assertEqual(cluster['events'][-1][:4], bytes([0, 0, 7, 7]))
        self.assertEqual(cluster['events'][-1][4], watcher['hook_value'])
        contents = instructions(exported, 2, f"F {actor[15] & 127}")
        self.assertIn(13, [row[1] for row in contents])
        controller = instructions(exported, 2, f"B {watcher['root_index']}")
        for offset, opcode, width in controller:
            if opcode in (0x2C, 0x2D, 0x2E):
                self.assertEqual(exported.data[offset + 1], 1)
        self.assertTrue({0, 2, 3, 4, 0x31, 0x2C, 0x2D, 0x2E, 255}.issubset(set(generated_event_opcodes(self.session, exported))))
        self.assertEqual(bytes(self.session.data), original)
        self.assertEqual(self.graph, old_graph)

    def test_ordinary_dormant_donor_copy_is_spawn_enabled_and_original_unchanged(self):
        self.graph['pages'][0]['conditions'] = []   # no conditions: always present
        exported = prepare_native_event_export(self.session)
        rows = record_cluster(exported.data, 2)['entities']
        self.assertEqual(rows[0], self.donor)
        self.assertEqual(rows[1][5], self.donor[5] | 0x40)
        self.assertNotIn('presence_controller', exported.native_event_export_report[0])
        self.assertEqual(len(record_cluster(exported.data, 2)['events']), 1)

    def test_new_dialogue_passes_explicit_auto_wrap_and_defaults_to_enabled(self):
        from native_text_allocation import append_local_text
        from new_event_compile import compile_new_events
        for setting in (None, False, True):
            command = self.graph['pages'][0]['commands'][0]
            command.pop('auto_wrap', None)
            if setting is not None: command['auto_wrap'] = setting
            with patch('new_event_compile.append_local_text', wraps=append_local_text) as writer:
                compile_new_events(self.session, [self.graph])
            self.assertEqual(writer.call_args.kwargs['auto_wrap'], True if setting is None else setting)

    def test_multiple_actor_hooks_and_controller_indices_remain_stable(self):
        other = copy.deepcopy(self.graph)
        other['id'] = 'event:other'; other['name'] = 'Other NPC'; other['region'] = [5, 5, 1, 1]
        other['pages'][0]['conditions'][0]['value'] = False
        self.session.content_database['event_graphs'].append(other)
        exported = prepare_native_event_export(self.session)
        cluster = record_cluster(exported.data, 2)
        self.assertEqual(len(cluster['entities']), 3)
        for index, report in enumerate(exported.native_event_export_report, 1):
            watcher = report['presence_controller']; actor = cluster['entities'][index]
            self.assertEqual(watcher['template_index'], index)
            self.assertEqual(actor[15], report['hook_value'])
            self.assertEqual(cluster['events'][index][4], watcher['hook_value'])
            self.assertEqual(instructions(exported, 2, f"F {report['root_index']}")[-1][1], 255)
            self.assertEqual(instructions(exported, 2, f"B {watcher['root_index']}")[-1][1], 255)

    def test_pickup_template_prefix_and_touch_contents_do_not_shift_controller_identity(self):
        gift = new_event_graph('event:gift', 2, 'Gift', 2, 2)
        gift['pages'][0].update(trigger='touch', commands=[{'type': 'give_item', 'item_class_id': 'item:herb'}])
        self.session.content_database['definitions'].append({'id': 'item:herb', 'kind': 'item',
            'source': {'catalogue_index': 66, 'item_id': 36}})
        self.session.content_database['event_graphs'].insert(0, gift)
        self.graph['pages'][0]['trigger'] = 'touch'
        from event_logic_compile import item_pickup_template
        original = bytes(self.session.data)
        with patch('new_event_compile.find_item_template', return_value={'raw': item_pickup_template(36)}):
            exported=prepare_native_event_export(self.session)
        cluster=record_cluster(exported.data,2)
        report=next(row for row in exported.native_event_export_report if row['event_id']==self.graph['id'])
        self.assertEqual(report['presence_controller']['template_index'],1)
        self.assertEqual(len(cluster['entities']),2)
        self.assertEqual(bytes(self.session.data), original)

    def test_invalid_conditions_fail_and_every_actor_kind_can_be_conditional(self):
        # 2026-10-07: presence is the default for any placed actor whose pages
        # all have conditions (objects, enemies, bosses too); rewards and
        # inherited hooks are allowed (user request), bad conditions still fail.
        original = bytes(self.session.data)
        for conditions in ([{'type': 'item', 'native_item_id': 36, 'quantity': 1}],
                [{'type': 'switch', 'native_flag_operand': 0x7FFB, 'value': True}]):
            self.graph['pages'][0]['conditions'] = conditions
            with self.assertRaises(EventExportError): prepare_native_event_export(self.session)
        self.graph['pages'][0]['conditions'] = [{'type': 'switch', 'native_flag_operand': 7, 'value': True}]
        self.graph['pages'][0]['commands'] = [{'type': 'show_dialogue', 'text': 'Visible'}]
        exported = prepare_native_event_export(self.session)
        self.assertIn('presence_controller', exported.native_event_export_report[0])
        self.graph['pages'][0]['conditions'] = []
        exported = prepare_native_event_export(self.session)
        self.assertNotIn('presence_controller', exported.native_event_export_report[0])
        self.assertEqual(bytes(self.session.data), original)

    def test_presence_rejected_on_bound_existing_process(self):
        from event_native_compile import compile_bound_event
        bound = copy.deepcopy(self.graph)
        bound['native_binding'] = {'map_id': 2, 'script_key': 'F 1'}
        with self.assertRaisesRegex(ValueError, 'not existing native events'):
            compile_bound_event(self.session, bound)

    def test_generated_controller_native_abi_is_included(self):
        from event_vm_compatibility import verify_event_vm_abi
        path = ROOT / 'game/disc/ALUN_CD.EXE'
        if not path.exists(): self.skipTest('Private native reference unavailable')
        exported = prepare_native_event_export(self.session)
        opcodes = generated_event_opcodes(self.session, exported)
        stock = path.read_bytes()
        self.assertTrue(verify_event_vm_abi(stock, stock, opcodes)['relevant_handler_signatures_compatible'])
        load = struct.unpack_from('<I', stock, 0x18)[0]
        changed = bytearray(stock); changed[0x800 + 0x8003E788 - load] ^= 1
        # Conservative128-byte signatures overlap adjacent2D/2E handlers.
        with self.assertRaisesRegex(ValueError, 'command2[D-E]'):
            verify_event_vm_abi(changed, stock, opcodes)

    def test_map_local_npc_story_hooks_cleared_only_on_authored_copy(self):
        donor = bytearray(self.donor); donor[10:16] = bytes([0x81, 0x82, 0x83, 0x84, 0x85, 0x86])
        self.session.data, _ = append_record_cluster(self.session.data, 2, entities=[bytes(donor)])
        exported = prepare_native_event_export(self.session)
        rows = record_cluster(exported.data, 2)['entities']
        self.assertEqual(rows[0], donor)
        self.assertEqual(rows[1][10:15], bytes(5))
        self.assertTrue(rows[1][15] & 128)
        self.assertEqual(exported.native_event_export_report[0]['npc_donor_map_hooks_cleared'],
            dict(zip('ABCDEF', donor[10:16])))


if __name__ == '__main__': unittest.main()
