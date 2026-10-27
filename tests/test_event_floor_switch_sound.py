"""Floor switch press sound (2026-10-23, docs/2026-10-22-maker-demo-qa.txt).

The compiled Step On controller plays BD 3C 00 between the latch set and the
press animation; sound 60 is a global record (bank -1), so it does not depend on
the map's sound set. BizHawk run snd2 (map 483): sounds 60 and 218 keyed on
and both present in the dumped audio at the press frame."""
import struct
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from native_floor_switch_profile import compile_floor_switch
from project_state_registry import ProjectStateRegistry

CLICK = bytes((0xBD, 0x3C, 0x00, 0x1A, 0x04))


class FloorSwitchPressSoundTests(unittest.TestCase):
    def setUp(self):
        self.registry = ProjectStateRegistry({})
        self.latch = self.registry.create('switches', 'Floor pressed')['id']

    def test_click_follows_latch_set_before_press_animation(self):
        for kw in ({}, {'while_pressured': True}, {'ignore_spring_bean': True}):
            code = compile_floor_switch(self.registry, self.latch, [], **kw)[0]['C']
            at = code.find(CLICK)
            self.assertGreater(at, 0, kw)
            self.assertEqual(code[at - 4], 0xE0, kw)   # the latch set_switch right before it

    def test_floor_tile_switch_click_is_bd_play_not_75_stop(self):
        # Step On Switch (Floor) touch event: opcode 75 calls StopSound 0x8004A7B4 (silent);
        # BD calls PlaySound 0x8004A128 (handler 0x8004278C).
        from event_logic_compile import compile_logic
        self.assertEqual(compile_logic([{'type': 'native_play_sound', 'sound_id': 0x3C}]), bytes((0xBD, 0x3C, 0)))
        src = (ROOT / 'tools/new_event_compile.py').read_text(encoding='utf-8')
        self.assertNotIn("{'type': 'play_sound', 'sound_id': 0x3C}", src)
        self.assertEqual(src.count("{'type': 'native_play_sound', 'sound_id': 0x3C}"), 1)   # one Activate handler (tile controller, 2026-10-25)

    def test_play_sound_is_bd_and_stop_sound_is_75(self):
        from event_logic_compile import compile_logic
        from native_event_authoring import compile_command, summary, validate_command
        from native_event_commands import encode_insert
        from sound_database import encode_sound, encode_stop_sound
        self.assertEqual(encode_sound(181), bytes((0xBD, 181, 0)))
        self.assertEqual(encode_stop_sound(3), bytes((0x75, 3)))
        rows = [{'type': 'play_sound', 'sound_id': 3}, {'type': 'stop_sound', 'sound_id': 3}]
        self.assertEqual(compile_logic(rows), bytes((0xBD, 3, 0, 0x75, 3)))
        self.assertEqual(compile_command(rows[1]), bytes((0x75, 3)))
        self.assertEqual(encode_insert(rows[1]), bytes((0x75, 3)))
        self.assertEqual(summary(rows[1]), 'Stop sound 3')
        validate_command(rows[1])
        with self.assertRaises(ValueError):
            validate_command({'type': 'stop_sound', 'sound_id': 256})

    def test_imported_stock_75_round_trips_as_stop(self):
        from native_event_commands import command_form
        session = type('S', (), {'data': bytes((0x75, 9))})()
        self.assertEqual(command_form(session, 0, 0, 0x75), {'type': 'stop_sound', 'sound_id': 9})

    def test_custom_ai_spawn_sound_uses_play(self):
        src = (ROOT / 'tools/native_custom_ai.py').read_text(encoding='utf-8')
        self.assertIn("asm.data.extend(encode_sound(int(a['spawn_sound'])))", src)

    @unittest.skipUnless((ROOT / 'game/disc/ALUN_CD.EXE').exists(), 'no local ALUN_CD.EXE')
    def test_sound_60_is_global_not_map_bank(self):
        d = (ROOT / 'game/disc/ALUN_CD.EXE').read_bytes()
        t = struct.unpack_from('<I', d, 0x18)[0]
        rec = struct.unpack_from('<11h', d, 0x800AA150 - t + 0x800 + 0x16 * 60)
        self.assertEqual(rec[0], -1)   # PlaySound 0x8004A1D0: bank -1 keys on the global VAB


if __name__ == '__main__':
    unittest.main()
