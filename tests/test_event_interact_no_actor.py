"""2026-10-23 Maker Demo QA: Interact on a page with no character is a whole-map controller that
tests the tile area (3B) and the talk button (2F 0020 01); the placed lever305 no longer gets an
editor-added BD 02 sound when pulled."""
import inspect, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
import new_event_compile
from new_event_compile import _run_controller, validate_new_event, _split_pages


def green_shadow():
    sw = lambda i: {'type': 'switch', 'native_flag_operand': 0x7F0 + i, 'switch_id': i, 'value': True}
    return {'id': 'event:0152', 'name': 'Green Shadow', 'map_id': 483, 'region': [29, 51, 1, 1], 'class_id': 'enemy:0074',
            'pages': [{'trigger': 'death', 'class_id': 'enemy:0074', 'conditions': [sw(5)], 'commands': [{'type': 'set_switch'}]},
                      {'trigger': 'interact', 'class_id': None, 'conditions': [sw(8)], 'commands': [{'type': 'give_item'}]},
                      {'trigger': 'interact', 'class_id': None, 'conditions': [{'type': 'self_switch', 'letter': 'A', 'value': True}], 'commands': []}]}


class InteractWithoutActor(unittest.TestCase):
    def test_page_two_is_kept_and_validates(self):
        subs = _split_pages([green_shadow()])
        self.assertEqual([s['id'] for s in subs], ['event:0152#page1', 'event:0152#page2'])
        validate_new_event(subs[1])   # raised "Events without an actor currently use Player touch" before

    def test_controller_tests_area_then_button(self):
        g = {'pages': [{'conditions': []}]}
        code = _run_controller(g, bytes((0x9B, 1, 0)), False, None, None, interact_area=[29, 51, 1, 1])
        self.assertEqual(code[0], 0)
        self.assertEqual(code[1:9], bytes((0x3B, 29, 29, 51, 51, 0, 127, 0x04)))
        self.assertEqual(code[11:16], bytes((0x2F, 0x80, 0x00, 0x01, 0x04)))   # Square
        self.assertIn(bytes((0x9B, 1, 0, 0x02)), code)
        self.assertEqual(code[-1], 0xFF)

    def test_other_controllers_unchanged(self):
        g = {'pages': [{'conditions': []}]}
        self.assertNotIn(0x3B, _run_controller(g, b'', False, None, None))


class LeverSound(unittest.TestCase):
    def test_no_editor_sound_on_pull(self):
        src = inspect.getsource(new_event_compile)
        self.assertNotIn("34:bytes.fromhex('bd0200')", src)
        self.assertIn("insert_before={22:_release, 34:code[:-1]}", src)


if __name__ == '__main__':
    unittest.main()
