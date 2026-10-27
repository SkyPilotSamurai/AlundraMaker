"""Hit triggers on placed objects (2026-10-24, docs/2026-10-24-hit-triggers-objects.txt)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from new_event_compile import _expand_hit_pages, _hit_switch_requests, HIT_SETTLE_FRAMES

SWITCH = lambda i, v=True: {'type': 'switch', 'switch_scope': 'project', 'switch_id': i, 'value': v, 'operator': '=='}
TEXT = {'type': 'show_dialogue', 'text': 'Crate hit.', 'auto_wrap': True}


class _Registry:
    def __init__(self):self.n = 100
    def create(self, kind, name, **_):
        self.n += 1;return {'id': self.n}


def graph(class_id, commands, sources=('sword', 'flail'), trigger='hit', conditions=()):
    page = {'id': 'p', 'class_id': class_id, 'trigger': trigger, 'conditions': list(conditions), 'commands': list(commands),
            'trigger_actions': [{'trigger': trigger, 'hit_sources': list(sources), 'commands': list(commands), 'destroy_after': False}]}
    return {'id': 'event:9', 'name': 'Crate', 'map_id': 483, 'region': [23, 56, 1, 1], 'class_id': None,
            'trigger': trigger, 'pages': [page], 'native_placement': {}}


class HitObjectPageTests(unittest.TestCase):
    def test_object_stays_stock_and_gets_hit_spot_on_its_tile(self):
        g = graph('object:crate', [TEXT], conditions=[SWITCH(4)])
        obj, spot, hit = _expand_hit_pages([g], _Registry(), lambda g, p: True)
        self.assertEqual(obj['pages'][0]['class_id'], 'object:crate')
        self.assertEqual((obj['trigger'], obj['pages'][0]['trigger']), ('interact', 'interact'))
        self.assertEqual((obj['pages'][0]['commands'], obj['pages'][0]['trigger_actions']), ([], []))   # stock reaction kept
        self.assertEqual(spot['region'], [23, 56, 1, 1])
        self.assertEqual(spot['_hit_marker']['elements'], [0, 1])
        self.assertEqual(spot['pages'][0]['conditions'], [SWITCH(4)])   # there while the page is in force
        request = spot['_hit_marker']['request']
        self.assertEqual(hit['pages'][0]['conditions'], [SWITCH(request)])
        self.assertEqual(hit['pages'][0]['commands'][1], TEXT)

    def test_hit_controller_waits_out_the_swing(self):
        _, spot, hit = _expand_hit_pages([graph('object:crate', [TEXT])], _Registry(), lambda g, p: True)
        request = spot['_hit_marker']['request']
        self.assertEqual(hit['pages'][0]['commands'][-2:], [
            {'type': 'wait', 'frames': HIT_SETTLE_FRAMES},
            {'type': 'set_switch', 'switch_scope': 'project', 'switch_id': request, 'value': False}])

    def test_object_hit_page_without_actions_is_just_the_object(self):
        out = _expand_hit_pages([graph('object:crate', [])], _Registry(), lambda g, p: True)
        self.assertEqual(len(out), 1);self.assertEqual(out[0]['pages'][0]['trigger'], 'interact')

    def test_other_classes_are_left_alone(self):
        g = graph('object:lever', [TEXT])
        self.assertEqual(_expand_hit_pages([g], _Registry(), lambda g, p: False), [g])

    def test_hit_object_weapons_are_still_required(self):
        with self.assertRaisesRegex(ValueError, 'at least one weapon'):
            _expand_hit_pages([graph('object:crate', [TEXT], sources=())], _Registry(), lambda g, p: True)


class HitSwitchRequestTests(unittest.TestCase):
    DEFS = {'object:lever': {'kind': 'object', 'source': {'catalogue_index': 305}}}

    def test_text_on_a_lever_runs_from_a_controller(self):
        g = graph('object:lever', [TEXT], trigger='activate')
        out = _hit_switch_requests([g], self.DEFS, {305}, _Registry())
        self.assertEqual(len(out), 1)
        ask = g['pages'][0]['commands']
        self.assertEqual(ask, [{'type': 'set_switch', 'switch_scope': 'project', 'switch_id': 101, 'value': True}])
        self.assertEqual(g['pages'][0]['trigger_actions'][0]['commands'], ask)
        self.assertEqual(out[0]['class_id'], None);self.assertEqual(out[0]['trigger'], 'parallel')
        self.assertEqual(out[0]['pages'][0]['conditions'], [SWITCH(101)])
        self.assertEqual(out[0]['pages'][0]['commands'][1:], [TEXT])

    def test_switch_only_actions_stay_on_the_lever(self):
        commands = [{'type': 'set_switch', 'switch_scope': 'project', 'switch_id': 5, 'value': True}]
        g = graph('object:lever', commands, trigger='activate')
        self.assertEqual(_hit_switch_requests([g], self.DEFS, {305}, _Registry()), [])
        self.assertEqual(g['pages'][0]['commands'], commands)


class FollowTests(unittest.TestCase):
    def test_moving_object_spot_follows_it(self):
        g = graph('object:barrel', [TEXT])
        obj, spot, hit = _expand_hit_pages([g], _Registry(), lambda g, p: True, lambda g, p: True)
        self.assertEqual(spot['_hit_marker']['follow'], 'event:9')
        _, still, _ = _expand_hit_pages([graph('object:statue', [TEXT])], _Registry(), lambda g, p: True)
        self.assertNotIn('follow', still['_hit_marker'])

    def test_follow_program_and_opcode(self):
        from native_hit_follow import follow_program, emit, OPCODE
        code = follow_program(12)
        self.assertEqual(code[:3], bytes((0x17, OPCODE, 12)))
        self.assertTrue(code.endswith(bytes((0x2E, 0x80, 0xFF))))
        handler = emit()
        self.assertEqual(len(handler) % 4, 0)
        self.assertIn(bytes.fromhex('0200 0224')[::-1][::-1] if False else (0x24020002).to_bytes(4, 'little'), handler)   # length 2
        with self.assertRaises(ValueError):
            follow_program(200)


class LeverWeaponTests(unittest.TestCase):
    DEFS = {'object:lever': {'kind': 'object', 'source': {'catalogue_index': 305}}}

    def test_non_sword_weapons_get_a_hit_spot(self):
        from new_event_compile import _lever_other_weapons
        g = graph('object:lever', [TEXT], sources=('sword', 'flail', 'bow'))
        spot, hit = _lever_other_weapons([g], self.DEFS, _Registry())
        self.assertEqual(spot['_hit_marker']['elements'], [1, 2])   # the sword flips the lever itself
        self.assertEqual(hit['pages'][0]['commands'][1], TEXT)
        self.assertEqual(_lever_other_weapons([graph('object:lever', [TEXT], sources=('sword',))], self.DEFS, _Registry()), [])


class NirudeFaceTests(unittest.TestCase):
    DEFS = {'object:face': {'kind': 'object', 'source': {'catalogue_index': 346}}}

    def face(self, active=False):
        page = {'id': 'p', 'class_id': 'object:face', 'trigger': 'activate', 'conditions': [], 'commands': [],
                'trigger_actions': [{'trigger': 'activate', 'commands': [], 'hit_sources': [], 'destroy_after': False},
                                    {'trigger': 'deactivate', 'commands': [TEXT], 'hit_sources': [], 'destroy_after': False}]}
        return {'id': 'event:7', 'name': 'Face', 'map_id': 483, 'region': [27, 52, 1, 1], 'class_id': None,
                'trigger': 'activate', 'pages': [page], 'native_placement': {'active_by_default': active}}

    def test_breaking_runs_deactivate_once(self):
        from new_event_compile import _nirude_faces
        states = {}
        g = self.face()
        out = _nirude_faces([g], self.DEFS, _Registry(), states)
        self.assertEqual(states, {'event:7': g['_face']['state']})
        self.assertEqual(g['pages'][0]['trigger_actions'], [])   # its own C / D programs run it
        (broken,) = out
        self.assertEqual(broken['pages'][0]['conditions'][0], SWITCH(g['_face']['broken']))
        self.assertEqual(broken['pages'][0]['commands'][1:], [TEXT])

    def test_active_by_default_starts_the_state_on(self):
        from new_event_compile import _nirude_faces
        created = []
        class Reg(_Registry):
            def create(self, kind, name, initial_value=None, **_):
                created.append((name, initial_value));return super().create(kind, name)
        _nirude_faces([self.face(True)], self.DEFS, Reg(), {})
        self.assertIn(('Face object state', True), created)

    def test_program_keeps_the_stock_ops(self):
        from native_nirude_face import tick_program, touched_program
        code = tick_program(0x8760, b'\xAA', b'\xBB', b'\xCC')
        self.assertEqual(touched_program(0x8760), bytes.fromhex('056087ff'))
        self.assertTrue(code.startswith(b'\xBB\x03'))                  # broken -> broken face
        self.assertIn(bytes.fromhex('bd55001a0b1d01be5500'), code)       # stock wake-up
        self.assertEqual(code.count(bytes.fromhex('7305')), 3)          # three stages of five hits
        self.assertTrue(code.endswith(bytes.fromhex('2b1a03ff')))
        self.assertIn(b'\xCC', code)


if __name__ == '__main__':
    unittest.main()
