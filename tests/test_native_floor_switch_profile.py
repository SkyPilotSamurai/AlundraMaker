import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from native_floor_switch_profile import compile_floor_switch
from project_state_registry import ProjectStateRegistry


def execute(code, state, standing=False, pc=0):
    """Synthetic scheduler model; never claimed as emulator evidence."""
    # standing: False, True (the player), 'object' (stays), 'bean' (thrown
    # Spring Bean: gone after any 37 wait, as it despawns 3 frames after landing)
    animations = []; money = 0; condition = False; waited = False
    for _ in range(200):
        op = code[pc]; origin = pc
        if op == 0: return pc+1, animations, money
        if op == 0xFF: return None, animations, money
        if op in (0xE0, 0xE1):
            slot, value = struct.unpack_from('<HB', code, pc+1)
            if op == 0xE0: state[slot] = bool(value)
            else: condition = state[slot] == bool(value)
            pc += 4
        elif op in (2, 3, 4):
            selected = op == 2 or (condition if op == 3 else not condition)
            pc = origin + struct.unpack_from('<h', code, pc+1)[0] if selected else pc+3
        elif op == 0x3E: condition = standing is True; pc += 1
        elif op == 0x3F: condition = bool(standing) and not (standing == 'bean' and waited); pc += 1
        elif op == 0x37: waited = True; pc += 2
        elif op == 0xBD: pc += 3
        elif op == 0x1A: animations.append(code[pc+1]); pc += 2
        elif op == 0x1C: pc += 2
        elif op == 0x98: money += struct.unpack_from('<H', code, pc+1)[0]; pc += 3
        else: raise AssertionError(f'Unexpected opcode {op:02X}')
    raise AssertionError('Controller failed to yield/end')


class FloorSwitchProfileTests(unittest.TestCase):
    def setUp(self):
        self.registry = ProjectStateRegistry({})
        self.latch = self.registry.create('switches', 'Floor pressed')['id']

    def test_waits_until_standing_then_animates_and_runs_ordered_reward_once(self):
        programs, report = compile_floor_switch(self.registry, self.latch,
                                                [{'type': 'change_money', 'amount': 7}])
        state = {0: False}
        pc, art, reward = execute(programs['C'], state)
        self.assertEqual((art, reward, state), ([], 0, {0: False}))
        pc, art, reward = execute(programs['C'], state, pc=pc)
        self.assertEqual((art, reward), ([], 0))
        pc, art, reward = execute(programs['C'], state, standing=True, pc=pc)
        # 2026-10-11: it stays pressed and waits (re-armed when a command deactivates it)
        self.assertIsNotNone(pc);self.assertEqual((art, reward, state), ([4], 7, {0: True}))
        pc, art, reward = execute(programs['C'], state, True, pc=pc)
        self.assertEqual((art, reward), ([], 0))   # pressed again: nothing repeats
        self.assertEqual(execute(programs['A'], state), (None, [1], 0))
        self.assertFalse(report['gameplay_verified'])

    def test_separate_switches_do_not_activate_each_other(self):
        second = self.registry.create('switches', 'Other floor')['id']
        first, _ = compile_floor_switch(self.registry, self.latch)
        other, _ = compile_floor_switch(self.registry, second)
        state = {0: False, 1: False}
        pc, _, _ = execute(first['C'], state)
        execute(first['C'], state, True, pc)
        self.assertEqual(state, {0: True, 1: False})
        self.assertEqual(execute(other['A'], state), (None, [], 0))

    def test_missing_state_and_uncompiled_commands_rejected(self):
        with self.assertRaises(ValueError): compile_floor_switch(self.registry, 999)
        with self.assertRaises(ValueError):
            compile_floor_switch(self.registry, self.latch, [{'type': 'opaque-room-action'}])

    def test_unpressed_load_does_not_change_animation(self):
        programs, _ = compile_floor_switch(self.registry, self.latch)
        self.assertEqual(execute(programs['A'], {0: False}), (None, [], 0))

    def test_private_condition_runs_only_selected_activation_branch(self):
        user_switch = self.registry.create('switches', 'Puzzle enabled')['id']
        commands = [{'type':'if', 'condition':{'type':'switch','switch_scope':'project',
                    'switch_id':user_switch,'value':True},
                    'then':[{'type':'change_money','amount':11}],
                    'else':[{'type':'change_money','amount':99}]}]
        programs, _ = compile_floor_switch(self.registry, self.latch, commands)
        state = {0:False, 1:True}
        pc, _, _ = execute(programs['C'], state)
        _, art, money = execute(programs['C'], state, True, pc)
        self.assertEqual((art,money,state), ([4],11,{0:True,1:True}))

    def test_two_instances_complete_independent_user_rewards(self):
        second = self.registry.create('switches','Second floor')['id']
        first, _ = compile_floor_switch(self.registry,self.latch,
                    [{'type':'change_money','amount':7}])
        other, _ = compile_floor_switch(self.registry,second,
                    [{'type':'change_money','amount':11}])
        state = {0:False,1:False}
        p1,_,_ = execute(first['C'],state)
        p2,_,_ = execute(other['C'],state)
        self.assertEqual(execute(first['C'],state,True,p1)[2],7)
        self.assertFalse(state[1])
        self.assertEqual(execute(other['C'],state,True,p2)[2],11)
        self.assertEqual(state,{0:True,1:True})
        self.assertEqual(execute(first['C'],state,True)[2],0)
        self.assertEqual(execute(other['C'],state,True)[2],0)


class IgnoreSpringBeanTests(unittest.TestCase):
    def setUp(self):
        self.registry = ProjectStateRegistry({})
        self.latch = self.registry.create('switches', 'Floor pressed')['id']

    def press(self, who, **options):
        programs, report = compile_floor_switch(self.registry, self.latch,
                                                [{'type': 'change_money', 'amount': 7}], **options)
        state = {0: False}
        pc, _, _ = execute(programs['C'], state)
        _, art, money = execute(programs['C'], state, who, pc)
        return money, state[0], programs, report

    def test_default_press_test_is_native_anything_standing(self):
        for who in (True, 'object', 'bean'):
            self.assertEqual(self.press(who)[:2], (7, True), who)
        programs = self.press(True)[2]
        self.assertIn(0x3F, programs['C']); self.assertNotIn(0x37, programs['C'])

    def test_ignore_spring_bean_excludes_only_the_thrown_bean(self):
        self.assertEqual(self.press('bean', ignore_spring_bean=True)[:2], (0, False))
        self.assertEqual(self.press(True, ignore_spring_bean=True)[:2], (7, True))
        self.assertEqual(self.press('object', ignore_spring_bean=True)[:2], (7, True))
        self.assertTrue(self.press(True, ignore_spring_bean=True)[3]['ignore_spring_bean'])

    def test_ignore_spring_bean_with_while_pressed(self):
        for who, expected in ((True, 7), ('object', 7), ('bean', 0)):
            money, latch, _, report = self.press(who, ignore_spring_bean=True, while_pressured=True)
            self.assertEqual((money, latch), (expected, bool(expected)), who)
        self.assertTrue(report['while_pressured'] and report['ignore_spring_bean'])
        self.assertEqual(self.press('bean', while_pressured=True)[:2], (7, True))
