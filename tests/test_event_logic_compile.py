import copy
import struct
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from event_logic_compile import compile_logic, compile_spawn_template, compile_spawn_at_player, item_pickup_template, compile_give_pickup, find_item_template, verified_item_pickup_template, compile_wait_template_absent, verified_chest_template, compile_page_dispatch, compile_speaker_dialogue


def execute(code, flags=None, quantity=0):
    """Small semantic oracle for ONLY tested native flag/threshold control flow."""
    flags = dict(flags or {})
    p = 0; result = 0
    for _ in range(100):
        if p == len(code):
            return flags
        op = code[p]
        if op in (5, 6):
            flags[struct.unpack_from('<H', code, p + 1)[0]] = op == 5
            p += 3
        elif op in (0x30, 0x31):
            flag, displacement = struct.unpack_from('<Hh', code, p + 1)
            state = flags.get(flag, False)
            p += displacement if state == (op == 0x30) else 5
        elif op == 0x83:
            result = int(quantity >= code[p + 2]); p += 3
        elif op in (2, 3, 4):
            displacement = struct.unpack_from('<h', code, p + 1)[0]
            take = op == 2 or result == (op == 3)
            p += displacement if take else 3
        else:
            raise AssertionError(f'Unsupported oracle opcode {op}')
    raise AssertionError('Compiler generated a loop')


def set_flag(flag, value=True):
    return {'type': 'set_switch', 'native_flag_operand': flag, 'value': value}


class EventLogicCompileTests(unittest.TestCase):
    def test_explicit_speaker_uses_native_actor_reference_and_byte_text(self):
        self.assertEqual(compile_speaker_dialogue(12, 0x83), bytes.fromhex('5c0c8300'))
        self.assertEqual(compile_speaker_dialogue(0x81, 0x80), bytes.fromhex('5c818000'))
        for args in ((0x82, 0), (0, 256), (0, 0, 2), (True, 0)):   # mode 1 is valid (stock questions)
            with self.assertRaises(ValueError): compile_speaker_dialogue(*args)

    def test_pages_choose_highest_matching_and_combine_conditions(self):
        pages = [{'commands': [set_flag(10)], 'conditions': []},
                 {'commands': [set_flag(11)], 'conditions': [{'type': 'switch', 'value': True, 'native_flag_operand': 1}]},
                 {'commands': [set_flag(12)], 'conditions': [
                     {'type': 'switch', 'value': True, 'native_flag_operand': 1},
                     {'type': 'item', 'native_item_id': 2, 'quantity': 2, 'operator': '>='}]}]
        raw = compile_page_dispatch(pages)
        for flags, quantity, expected in (({}, 0, 10), ({1: True}, 0, 11), ({1: True}, 2, 12), ({1: False}, 2, 10)):
            out = execute(raw, flags, quantity)
            self.assertEqual([n for n in (10, 11, 12) if out.get(n)], [expected])

    def test_no_eligible_page_and_empty_high_page(self):
        condition = {'type': 'switch', 'value': True, 'native_flag_operand': 1}
        raw = compile_page_dispatch([{'commands': [set_flag(12)], 'conditions': [condition]}])
        self.assertEqual(execute(raw), {})
        raw = compile_page_dispatch([{'commands': [set_flag(12)]}, {'commands': [], 'conditions': [condition]}])
        self.assertEqual(execute(raw, {1: True}), {1: True})

    def test_page_leaves_compile_once_and_input_remains_unchanged(self):
        pages = [{'commands': [{'type': 'show_dialogue', 'text': 'low'}]},
                 {'commands': [{'type': 'show_dialogue', 'text': 'high'}], 'conditions': [
                     {'type': 'switch', 'value': True, 'native_flag_operand': 1}]}]
        old = copy.deepcopy(pages); calls = []
        compile_page_dispatch(pages, lambda row: (calls.append(row['text']) or b'\x0d\x80\x00'))
        self.assertEqual(calls, ['high', 'low'])
        self.assertEqual(pages, old)

    def test_template_absence_loop_yields_and_uses_opcode_relative_target(self):
        raw = compile_wait_template_absent(12)
        self.assertEqual(raw, bytes.fromhex('002c0c04fdff'))
        self.assertEqual(3 + struct.unpack_from('<h', raw, 4)[0], 0)
        with self.assertRaises(ValueError): compile_wait_template_absent(128)

    def test_global_pickup_fallback_requires_assets_and_stock_callbacks(self):
        data = bytearray(0x1000)
        struct.pack_into('<2I', data, 0, 0x800, 0x1000)
        struct.pack_into('<12I', data, 0x800, 0, 0, 0, 48, 448, 450, 452, 454, 456, 458, 460, 462)
        for index, pointer in ((31, 500), (66, 600)):
            struct.pack_into('<i', data, 0x800 + 48 + 4 * index, pointer)
            struct.pack_into('<4I', data, 0x800 + pointer, pointer + 32, pointer + 48, pointer + 60, pointer + 64)
            data[0x800 + pointer + 16:0x800 + pointer + 24] = bytes.fromhex('800123ffff000000')
        self.assertEqual(verified_item_pickup_template(data, 1), item_pickup_template(1))
        struct.pack_into('<i', data, 0x800 + 48 + 4 * 30, 700)
        data[0x800 + 700 + 19:0x800 + 700 + 24] = bytes.fromhex('ff000000ff')
        chest = verified_chest_template(data, 1)
        self.assertEqual(chest[4:7], bytes((1, 0x40, 0x1E)))
        self.assertEqual(chest[16:], bytes((0, 0, 1, 0)))
        data[0x800 + 700 + 23] = 0
        self.assertIsNone(verified_chest_template(data, 1))
        self.assertIsNone(verified_item_pickup_template(data, 2))
        data[0x800 + 500 + 20] = 1
        self.assertIsNone(verified_item_pickup_template(data, 1))
        struct.pack_into('<i', data, 0x800 + 48 + 4 * 31, 0x900)
        with self.assertRaises(ValueError): verified_item_pickup_template(data, 1)

    def test_item_donor_rejects_hooks_flags_and_local_sprite(self):
        good = item_pickup_template(0x24)
        local = bytearray(good); local[5] = 0x80
        hooked = bytearray(good); hooked[10] = 0x81
        flagged = bytearray(good); flagged[16] = 1
        data = bytes(local + hooked + flagged + good)
        def inspect(data, map_id):
            return {'entities': [{'offset': hex(offset), 'index': n}
                    for n, offset in enumerate((0, 20, 40, 60))]} if map_id == 7 else {'entities': []}
        with patch('map_inspector.inspect_map', inspect):
            donor = find_item_template(data, 0x24)
        self.assertEqual((donor['map_id'], donor['entity_index'], donor['offset'], donor['raw']),
                         (7, 3, 60, good))
        self.assertEqual(compile_give_pickup(4), compile_spawn_at_player(4))

    def test_delayed_pickup_template_and_player_relative_spawn(self):
        row = item_pickup_template(0x24)
        self.assertEqual(len(row), 20)
        self.assertEqual(row[:7], bytes.fromhex('0000333b010042'))
        self.assertEqual(row[10:], bytes(10))
        self.assertEqual(compile_spawn_at_player(12), bytes.fromhex('8b810c000000000000'))
        for value in (0, 90, True, -1):
            with self.assertRaises(ValueError): item_pickup_template(value)
        with self.assertRaises(ValueError): compile_spawn_at_player(128)

    def test_spawn_is_explicit_map_template_and_world_coordinates(self):
        self.assertEqual(compile_spawn_template(2, 24, 40, 16),
                         bytes.fromhex('8a 02 18 00 28 00 10 00'))
        for values in ((256, 0, 0, 0), (2, -1, 0, 0), (2, 0, 0, 65536), (True, 1, 2, 3)):
            with self.assertRaises(ValueError):
                compile_spawn_template(*values)

    def test_switch_both_branches_preserve_input_and_opcode_relative_base(self):
        rows = [{'type': 'if', 'condition': {'type': 'switch', 'value': True,
                 'native_flag_operand': 0x0634}, 'then': [set_flag(2)], 'else': [set_flag(3)]}]
        old = copy.deepcopy(rows)
        raw = compile_logic(rows)
        self.assertEqual(raw, bytes.fromhex('31 34 06 0b 00 05 02 00 02 06 00 05 03 00'))
        self.assertTrue(execute(raw, {0x0634: True})[2])
        self.assertNotIn(3, execute(raw, {0x0634: True}))
        self.assertTrue(execute(raw, {0x0634: False})[3])
        self.assertEqual(old, rows)

    def test_all_switch_comparisons(self):
        for value in (False, True):
            for operator in ('==', '!='):
                for state in (False, True):
                    row = {'type': 'if', 'condition': {'type': 'switch', 'value': value,
                           'operator': operator, 'native_flag_operand': 1},
                           'then': [set_flag(2)], 'else': [set_flag(3)]}
                    out = execute(compile_logic([row]), {1: state})
                    expected = state == value if operator == '==' else state != value
                    self.assertTrue(out[2 if expected else 3])
                    self.assertNotIn(3 if expected else 2, out)

    def test_inventory_comparisons_threshold_edges(self):
        for op in ('>=', '<', '==', '!='):
            for n in (1, 2, 254):
                row = {'type': 'if', 'condition': {'type': 'item', 'native_item_id': 2,
                       'operator': op, 'quantity': n}, 'then': [set_flag(2)], 'else': [set_flag(3)]}
                raw = compile_logic([row])
                for quantity in (0, n - 1, n, n + 1, 1000):
                    expected = {'>=': quantity >= n, '<': quantity < n,
                                '==': quantity == n, '!=': quantity != n}[op]
                    self.assertTrue(execute(raw, quantity=quantity)[2 if expected else 3])

    def test_nested_if_and_empty_branches(self):
        inner = {'type': 'if', 'condition': {'type': 'switch', 'value': False,
                 'native_flag_operand': 1}, 'then': [], 'else': [set_flag(8)]}
        raw = compile_logic([{'type': 'if', 'condition': {'type': 'switch', 'value': True,
              'native_flag_operand': 2}, 'then': [inner], 'else': []}, set_flag(9)])
        self.assertEqual(execute(raw, {1: True, 2: True}), {1: True, 2: True, 8: True, 9: True})
        self.assertNotIn(8, execute(raw, {1: True, 2: False}))

    def test_resolvers_do_not_assume_editor_ids_are_native(self):
        self.assertEqual(compile_logic([{'type': 'set_switch', 'switch_id': 12, 'value': True}],
                         switch_resolver=lambda row: 0x8001), b'\x05\x01\x80')
        with self.assertRaises(ValueError):
            compile_logic([{'type': 'set_switch', 'switch_id': 12, 'value': True}])
        raw = compile_logic([{'type': 'if', 'condition': {'type': 'item', 'item_class_id': 'item:1',
               'operator': '>=', 'quantity': 1}, 'then': [set_flag(2)]}], item_resolver=lambda row: 2)
        self.assertTrue(execute(raw, quantity=1)[2])

    def test_wait_money_and_leaf_bytes(self):
        rows = [{'type': 'wait', 'frames': 255}, {'type': 'change_money', 'amount': 9999},
                {'type': 'show_dialogue', 'text': 'Hi'}]
        self.assertEqual(compile_logic(rows, lambda row: b'\x0d\x80\x00'),
                         bytes.fromhex('37 ff 98 0f 27 0d 80 00'))

    def test_range_boolean_and_unknown_rejected(self):
        invalid = [set_flag(True), set_flag(65536), set_flag(0x800), set_flag(0x7FFB), set_flag(0x8800), {'type': 'wait', 'frames': 256},
                   {'type': 'wait', 'frames': 0}, {'type': 'change_money', 'amount': -1},
                   {'type': 'set_variable', 'value': 1}, {'type': 'give_item', 'item_class_id': 'x'}]
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(ValueError):
                compile_logic([row])
        with self.assertRaises(ValueError):
            compile_logic([{'type': 'if', 'condition': {'type': 'item', 'native_item_id': 2,
                'quantity': 255, 'operator': '=='}, 'then': []}])

    def test_branch_overflow_rejected(self):
        row = {'type': 'if', 'condition': {'type': 'switch', 'native_flag_operand': 1, 'value': True},
               'then': [{'type': 'leaf'}]}
        with self.assertRaisesRegex(ValueError, '16-bit'):
            compile_logic([row], lambda row: b'\x01' * 32768)


if __name__ == '__main__':
    unittest.main()
