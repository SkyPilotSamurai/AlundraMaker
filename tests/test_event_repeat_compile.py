import copy
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
from event_logic_compile import compile_logic
from editor_session import EditSession
from event_graph import new_event_graph
from event_export import prepare_native_event_export, generated_event_opcodes, EventExportError
from event_editor import instructions
from native_class_placement import append_record_cluster, record_cluster
from test_native_script_allocation import fixture


class RepeatLogicTests(unittest.TestCase):
    def test_yielding_repeat_requires_explicit_retained_context(self):
        with self.assertRaisesRegex(ValueError, 'retained native continuation'):
            compile_logic([{'type': 'repeat', 'count': 2, 'commands': [{'type': 'wait', 'frames': 1}]}])
    def test_counter_relative_branch_and_wait_use_distinct_scratch(self):
        row = {'type': 'repeat', 'count': 2, 'commands': [{'type': 'change_money', 'amount': 1}, {'type': 'wait', 'frames': 3}]}
        old = copy.deepcopy(row)
        raw = compile_logic([row], continuation_proven=True)
        self.assertEqual(raw, bytes.fromhex('10598100 7302 980100 3703 74fbff 11'))   # player held still while a timed Repeat runs
        self.assertEqual(row, old)
        pc = 0; count = 0; money = 0
        while pc < len(raw):
            op = raw[pc]
            if op == 0x10: pc += 4
            elif op == 0x11: pc += 1
            elif op == 0x73: count = raw[pc + 1]; pc += 2
            elif op == 0x98: money += struct.unpack_from('<H', raw, pc + 1)[0]; pc += 3
            elif op == 0x37: pc += 2
            elif op == 0x74:
                count -= 1; pc += struct.unpack_from('<h', raw, pc + 1)[0] if count > 0 else 3
            else: self.fail('Unexpected native operation')
        self.assertEqual(money, 2)

    def test_unsupported_control_nested_counters_empty_and_bad_counts_rejected(self):
        for body in ([], [{'type': 'repeat', 'count': 2, 'commands': [{'type': 'wait', 'frames': 1}]}],
                     [{'type': 'if', 'condition': {'type': 'switch', 'native_flag_operand': 1, 'value': True}, 'then': []}],
                     [{'type': 'unsafe_leaf'}]):
            with self.assertRaises(ValueError):
                compile_logic([{'type': 'repeat', 'count': 2, 'commands': body}], lambda row: b'\x78\x03\0')
        for count in (0, 256, True, -1, None):
            with self.assertRaises(ValueError): compile_logic([{'type': 'repeat', 'count': count, 'commands': [{'type': 'wait', 'frames': 1}]}])


class RepeatNewEventTests(unittest.TestCase):
    def setUp(self):
        self.session = EditSession(fixture(), verify=False)
        self.graph = new_event_graph('event:repeat', 2, 'Repeat text', 3, 4)
        self.graph['pages'][0].update(trigger='touch', commands=[{'type': 'repeat', 'count': 2,
            'commands': [{'type': 'show_dialogue', 'text': 'Again'}, {'type': 'wait', 'frames': 2}]}])
        self.session.content_database = {'definitions': [], 'event_graphs': [self.graph]}
        grid = patch('area_map.grid', return_value=(8, 8, [{'values': [0, 0, 0, 1]}] * 64))
        grid.start(); self.addCleanup(grid.stop)
        callbacks = patch('event_vm_compatibility.sprite_callbacks', return_value=[])
        callbacks.start(); self.addCleanup(callbacks.stop)

    def test_repeated_text_allocated_once_and_native_counter_in_abi(self):
        from map_text import entries
        source = bytes(self.session.data)
        exported = prepare_native_event_export(self.session)
        report = exported.native_event_export_report[0]
        rows = instructions(exported, 2, f"B {report['root_index']}")
        self.assertEqual([row[1] for row in rows], [0x10, 0x59, 0x73, 0x0D, 0x39, 0x37, 0x74, 0x11, 255])
        self.assertEqual(sum(text == b'Again' for _, _, text in entries(exported, 2)), 1)
        self.assertTrue({0x73, 0x74}.issubset(set(generated_event_opcodes(self.session, exported))))
        self.assertEqual(bytes(self.session.data), source)

    def test_repeated_speaker_dependencies_are_placed_and_select_actual_new_actor(self):
        raw = bytes([0, 0, 7, 7, 1, 64, 4, 2, 2, 2] + [0] * 10)
        self.session.data, _ = append_record_cluster(self.session.data, 2, entities=[raw])
        npc = new_event_graph('event:speaker', 2, 'Speaker', 5, 5)
        npc['pages'][0].update(trigger='interact', class_id='npc:test', commands=[])
        npc['native_placement'] = {'donor_entity_index': 0}
        self.session.content_database['definitions'] = [{'id': 'npc:test', 'kind': 'npc', 'source': {'catalogue_index': 4}}]
        self.session.content_database['event_graphs'].append(npc)
        self.graph['pages'][0]['commands'][0]['commands'][0]['speaker'] = npc['id']
        exported = prepare_native_event_export(self.session)
        self.assertEqual(len(record_cluster(exported.data, 2)['entities']), 2)
        report = exported.native_event_export_report[0]
        rows = instructions(exported, 2, f"B {report['root_index']}")
        selected = next(row for row in rows if row[1] == 0x5C)
        self.assertEqual(exported.data[selected[0] + 1], 1)

    def test_nested_repeat_rejected_without_changing_input(self):
        self.graph['pages'][0]['commands'][0]['commands'] = [{'type': 'repeat', 'count': 2, 'commands': [{'type': 'wait', 'frames': 1}]}]
        before = bytes(self.session.data)
        with self.assertRaisesRegex(EventExportError, 'without nested Repeat'): prepare_native_event_export(self.session)
        self.assertEqual(bytes(self.session.data), before)

    def test_actor_repeat_rejected_before_native_allocation(self):
        self.graph['pages'][0].update(trigger='interact', class_id='npc:test')
        before = bytes(self.session.data)
        with self.assertRaisesRegex(EventExportError, 'graphic-free Player Touch'):
            prepare_native_event_export(self.session)
        self.assertEqual(bytes(self.session.data), before)

    def test_actor_text_followed_by_actions_rejected_until_continuation_proof(self):
        self.graph['pages'][0].update(trigger='interact', class_id='npc:test', commands=[
            {'type': 'show_dialogue', 'text': 'Before'}, {'type': 'change_money', 'amount': 1}])
        before = bytes(self.session.data)
        with self.assertRaisesRegex(EventExportError, 'placeable database class'):
            prepare_native_event_export(self.session)
        self.assertEqual(bytes(self.session.data), before)


if __name__ == '__main__': unittest.main()
