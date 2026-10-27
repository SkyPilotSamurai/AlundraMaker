"""Step On Switch (Floor) as a tile-tested whole-map controller (2026-10-25).

Nothing solid stands on the square, so Alundra walks on from squares of the same
height; Alundra (3B) or anything solid resting on the square (3C) presses it, with
the step-on switch's options. Not verified in game."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from native_floor_switch_profile import compile_tile_floor_switch, BEAN_SETTLE_FRAMES
from project_state_registry import ProjectStateRegistry
from project_state_runtime import layout

PRESS = b'\xbd\x3c\x00' + b'\x85' + bytes(10)
LIT = b'\x85' + bytes(10)
RELEASE = b'\x86' + bytes(10)


class FloorTileSwitchTests(unittest.TestCase):
    def build(self, guard=None, **opts):
        r = ProjectStateRegistry({}); sid = r.create('switches', 'Floor state')['id']
        fs = dict(tile=(26, 13), z=1, state_id=sid, **opts)
        return compile_tile_floor_switch(r, layout(r), fs, PRESS, LIT, RELEASE, guard)

    def test_tests_the_square_not_an_actor(self):
        for opts in ({}, {'while_pressed': True}, {'can_deactivate': True}, {'ignore_spring_bean': True}):
            code = self.build(**opts)
            self.assertIn(bytes((0x3B, 26, 26, 13, 13, 1, 1)), code, opts)   # Alundra on it
            self.assertIn(bytes((0x3C, 26, 26, 13, 13, 1, 1)), code, opts)   # something solid on it
            self.assertNotIn(bytes((0x3F,)) + b'\x04', code)
            self.assertEqual(code[-1], 0xFF)
            self.assertIn(PRESS, code); self.assertIn(RELEASE, code)

    def test_ignore_spring_bean_rechecks_after_settle(self):
        self.assertIn(bytes((0x37, BEAN_SETTLE_FRAMES, 0x3C)), self.build(ignore_spring_bean=True))
        self.assertNotIn(bytes((0x37, BEAN_SETTLE_FRAMES, 0x3C)), self.build())

    def test_room_reset_and_keep_state(self):
        self.assertEqual(self.build(guard=0x87A0)[0], 0x30)
        self.assertNotEqual(self.build()[0], 0x30)

    def test_source_builds_floor_switch_as_tile_controller(self):
        src = (ROOT / 'tools/new_event_compile.py').read_text(encoding='utf-8')
        self.assertIn("compile_tile_floor_switch(", src)
        self.assertIn("g['class_id'] = None; g['trigger'] = 'parallel'", src)


if __name__ == '__main__':
    unittest.main()
