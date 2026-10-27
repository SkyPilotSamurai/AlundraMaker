"""Experimental door compiler keeps consumption and failure paths distinct."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from native_key_door_profile import compile_door, require_synchronous_continuation
from project_state_registry import ProjectStateRegistry


class DoorProfileTests(unittest.TestCase):
    def setUp(self):
        self.registry = ProjectStateRegistry({})
        self.opened = self.registry.create('switches', 'Opened')['id']

    def test_exact_positive_tested_bytes(self):
        result = compile_door(self.registry, self.opened, 128, bytes.fromhex('980700'))
        self.assertEqual(result['A'].hex(), 'e10000010405002e80ff')
        self.assertEqual(result['F'].hex(),
                         'e1000001032100833d01598100041500bd3c00843d'
                         'e00000019807002e80020700000d8000ff')

    def test_failure_branch_skips_consumption_and_continuation(self):
        code = compile_door(self.registry, self.opened, 128, bytes.fromhex('980700'))['F']
        # The native false branch targets0D directly, skipping00 padding.
        offset = 13
        displacement = int.from_bytes(code[offset+1:offset+3], 'little', signed=True)
        self.assertEqual(code[offset+displacement:], bytes.fromhex('0d8000ff'))
        self.assertNotIn(bytes.fromhex('843d'), code[offset+displacement:])
        self.assertNotIn(bytes.fromhex('980700'), code[offset+displacement:])

    def test_reject_unowned_text(self):
        for value in (0, 127, 256, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                compile_door(self.registry, self.opened, value)

    def test_yielding_continuations_reject_in_either_branch(self):
        for yielding in ({'type':'wait','frames':60}, {'type':'show_dialogue','text':'Opened'}):
            for branch in ('then','else'):
                with self.subTest(yielding=yielding,branch=branch), self.assertRaisesRegex(ValueError,'retained native continuation'):
                    require_synchronous_continuation([{'type':'if',branch:[yielding]}])

    def test_immediate_success_actions_remain_available(self):
        require_synchronous_continuation([{'type':'change_money','amount':7},
            {'type':'if','then':[{'type':'set_switch','switch_scope':'project','switch_id':self.opened,'value':True}]}])


if __name__ == '__main__':
    unittest.main()
