"""Custom AI attack movement and whole-animation options (2026-10-22, Blood Reaper)."""
import sys, unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import native_custom_ai as n

SLASH = {'type': 'strike', 'min_distance': 0, 'max_distance': 2, 'chance': 60, 'interval': 90,
         'animation': 3, 'frames': 40, 'stall_before': 10, 'move_during': 'lock', 'move_during_tiles': 3}


def code(attack, **kw):
    return n.compile_custom_ai({'chase': True, 'attacks': [attack]}, walk_animation=1, idle_animation=0, class_bits=0, vital=False, **kw)


class AttackMovementTests(unittest.TestCase):
    def test_lunge_uses_speed_opcode_not_walk_until_moved(self):
        c = code(SLASH)
        self.assertIn(bytes((0x1A, 3)), c)
        self.assertIn(bytes((n.OP_SPEED, 0, 0)), c)           # stops after the window
        self.assertNotIn(bytes((0x0B, 3)), c)                 # 0B never ended with a speedless animation
        self.assertIn(bytes((0x74,)), c)

    def test_swing_window_waits_until_the_attack_box(self):
        c = code(dict(SLASH, whole_animation=True), swings={3: (116, 126)})
        i = c.index(bytes((0x1A, 3)))
        self.assertEqual(c[i + 2:i + 4], bytes((0x37, 116)))
        self.assertEqual(c[i + 4:i + 6], bytes((0x73, 5)))     # 10 frames = 5 loop passes
        self.assertEqual(c[i + 6], n.OP_SPEED)
        self.assertEqual(int.from_bytes(c[i + 7:i + 9], 'little'), round(60 * n.SPEED_UNITS / 10))   # u16: no 255 cap (2026-10-24)
        self.assertIn(bytes((n.OP_SPEED, 0, 0, 0x1C, 1)), c)      # then the whole animation plays out

    def test_explicit_window_overrides_detected_one(self):
        c = code(dict(SLASH, move_from=20, move_to=40), swings={3: (116, 126)})
        i = c.index(bytes((0x1A, 3)))
        self.assertEqual(c[i + 2:i + 6], bytes((0x37, 20, 0x73, 10)))

    def test_toward_refaces_every_tick(self):
        c = code(dict(SLASH, move_during='toward'), swings={3: (0, 20)})
        self.assertIn(bytes((0x27, n.OP_SPEED)), c)

    def test_whole_animation_without_movement(self):
        c = code(dict(SLASH, move_during='none', whole_animation=True))
        self.assertIn(bytes((0x1A, 3, 0x1C, 1)), c)

    def test_swing_frames_from_attack_boxes(self):
        F = lambda t, c=0: SimpleNamespace(ticks=t, collision_raw=c)
        self.assertEqual(n.swing_frames([F(8), F(8), F(4, 6), F(2, 12), F(5)]), (16, 22))
        self.assertIsNone(n.swing_frames([F(8)]))

    def test_speed_handler_shape(self):
        h = n.emit_speed()
        self.assertEqual(len(h) % 4, 0)
        self.assertEqual(h[4:8], bytes(4))                     # load delay slot after lw t0
        self.assertIn(bytes.fromhex('bc008cac'), h)            # sw t4, 0xBC(a0)


if __name__ == '__main__':
    unittest.main()


class HitReactionTests(unittest.TestCase):
    def test_hit_program_only_when_needed(self):
        self.assertIsNone(n.hit_program({}))
        self.assertIsNone(n.hit_program({'dart': {'chance': 0, 'after_hits': 0, 'after_damage': 0}}))
        self.assertEqual(n.hit_program({'no_hit_stun': True}), bytes((n.OP_HIT,)))
        self.assertEqual(n.hit_program({'dart': {'after_hits': 3}}), bytes((n.OP_HIT,)))

    def dart_code(self, **dart):
        return n.compile_custom_ai({'chase': True, 'attacks': [dict(SLASH)], 'dart': dict(tiles=3, speed=4, **dart)},
                                   walk_animation=1, idle_animation=0, class_bits=0, vital=False)

    def test_dart_triggers(self):
        self.assertIn(bytes((n.OP_HITS, 0, 1, 0x04)), self.dart_code(chance=50))
        self.assertIn(bytes((0x8C, 128)), self.dart_code(chance=50))
        self.assertIn(bytes((n.OP_HITS, 1, 3, 0x03)), self.dart_code(after_hits=3))
        self.assertIn(bytes((n.OP_HITS, 2, 8, 0x03)), self.dart_code(after_damage=8))
        self.assertNotIn(bytes((n.OP_HITS,)), n.compile_custom_ai({'attacks': [dict(SLASH)]}, walk_animation=1, idle_animation=0, class_bits=0, vital=False))

    def test_dart_moves_away_with_speed_and_resets(self):
        c = self.dart_code(after_hits=2)
        i = c.index(bytes((n.OP_HITS, 3, 0)))
        self.assertEqual(c[i + 3:i + 7], bytes((0x27, n.OP_TURN, 0x1A, 1)))
        self.assertEqual(c[i + 7:i + 9], bytes((0x73, round(60 / 4 / 2))))
        self.assertEqual(c[i + 9:i + 12], bytes((n.OP_SPEED,)) + round(4 * n.SPEED_UNITS).to_bytes(2, 'little'))
        self.assertIn(bytes((n.OP_SPEED, 0, 0, 0x1A, 0)), c[i:])

    def test_hit_handlers_assemble(self):
        for f in (n.emit_hit, n.emit_hits):
            h = f(0x8001E000)
            self.assertEqual(len(h) % 4, 0)
            self.assertEqual(h[-8:-4], bytes.fromhex('0800e003'))      # jr ra
        self.assertIn(struct.pack('<I', 0x0C000000 | ((0x8003ACAC >> 2) & 0x3FFFFFF)), n.emit_hit(0x8001E000))   # native damage


import struct
