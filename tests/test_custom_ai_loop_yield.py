"""2026-10-24: a custom AI loop pass must yield a frame (blocked chase froze map 489)."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import native_custom_ai as n


class LoopYields(unittest.TestCase):
    def test_chase_only_loop_waits_before_branch(self):
        code = bytes(n.compile_custom_ai({'chase': True, 'attacks': []}, walk_animation=1, idle_animation=0, class_bits=0, vital=False))
        self.assertEqual(code[0:3], bytes((0x27, 0x1A, 1)))
        self.assertNotIn(bytes((n.OP_RANGE, 0, n.CHASE_STOP_TILES)), code)   # 'Stop near Alundra' off by default
        self.assertIn(bytes((0x37, 1, 0x02)), code)    # wait 1, then the branch to start
        stop = bytes(n.compile_custom_ai({'chase': True, 'attacks': [], 'stop_near_player': True}, walk_animation=1, idle_animation=0, class_bits=0, vital=False))
        self.assertIn(bytes((n.OP_RANGE, 0, n.CHASE_STOP_TILES)), stop)   # on: stops next to Alundra


class LungeSpeed(unittest.TestCase):
    SLASH = dict(name='Slash', type='strike', min_distance=0, max_distance=4, chance=100, interval=60,
                 animation=3, frames=40, move_during='lock', move_during_tiles=12)

    def compile(self, **kw):
        n.BUILD_WARNINGS.clear()
        return bytes(n.compile_custom_ai({'attacks': [dict(self.SLASH, **kw)]}, walk_animation=1, idle_animation=0,
                                         class_bits=0, vital=False, swings={3: (10, 20)}, owner='Reaper'))

    def speed(self, c):
        i = c.index(bytes((n.OP_SPEED,)))
        return int.from_bytes(c[i + 1:i + 3], 'little')

    def test_twelve_tiles_in_ten_frames_is_u16_and_not_capped(self):
        self.assertEqual(self.speed(self.compile()), round(24 * n.SPEED_UNITS))
        self.assertEqual(n.BUILD_WARNINGS, [])

    def test_faster_than_collision_limit_is_capped_with_warning(self):
        self.assertEqual(self.speed(self.compile(move_from=10, move_to=12)), round(24 * n.SPEED_UNITS))
        self.assertIn("Reaper attack 'Slash'", n.BUILD_WARNINGS[0])


class DeathAndHurt(unittest.TestCase):
    def compile(self, **ai):
        return bytes(n.compile_custom_ai(dict(chase=True, attacks=[], **ai), walk_animation=1, idle_animation=0, class_bits=0))

    def test_checks_death_and_removes_itself(self):
        c = self.compile()
        self.assertEqual(c[:3], bytes((n.OP_HITS, 4, 0)))
        self.assertTrue(c.endswith(n.REMOVE_SELF + b'\xff'))
        self.assertIn(bytes((n.OP_HITS, 5, n.HURT_RESUME)), c)   # native stun: wait out the hurt pose

    def test_no_hit_stun_skips_hurt_wait(self):
        self.assertNotIn(bytes((n.OP_HITS, 5)), self.compile(no_hit_stun=True))

    def test_long_waits_are_split(self):
        c = bytes(n.compile_custom_ai({'attacks': [], 'routes': [{'name': 'r', 'steps': [{'kind': 'wait', 'value': 30}]}]},
                                      walk_animation=1, idle_animation=0, class_bits=0))
        self.assertNotIn(bytes((0x37, 30)), c); self.assertIn(bytes((0x37, n.CHECK_FRAMES - 1)), c)

    def test_checked_wait_keeps_the_single_wait_timing(self):
        for frames in (1, 7, 8, 9, 30, 117):
            asm = n._Assembler(); asm.vital_check = lambda: asm.data.extend((n.OP_HITS, 4, 0))
            n._wait(asm, frames); d = bytes(asm.data)
            waits = [d[i + 1] for i in range(len(d) - 1) if d[i] == 0x37 and (i == 0 or d[i - 3] == n.OP_HITS or d[i-1] == 0)]
            self.assertNotIn(0, waits)
            self.assertEqual(sum(w + 1 for w in waits), frames + 1, frames)   # 37 n lasts n+1 frames


class DeathInterruptsLongSteps(unittest.TestCase):
    def test_chase_is_chunked_with_death_checks(self):
        c = bytes(n.compile_custom_ai({'chase': True, 'attacks': []}, walk_animation=1, idle_animation=0, class_bits=0))
        self.assertIn(bytes((0x1F, n.CHUNK_PIXELS, 0, n.OP_HITS, 4, 0)), c)
        self.assertNotIn(bytes((0x1F, 20, 0)), c)

    def test_whole_animation_uses_checked_waits_and_death_animation(self):
        slash = dict(name='Slash', type='strike', min_distance=0, max_distance=4, chance=100, interval=60,
                     animation=3, frames=40, whole_animation=True)
        c = bytes(n.compile_custom_ai({'attacks': [slash]}, walk_animation=1, idle_animation=0, class_bits=0,
                                      lengths={3: 176}, death_animation=2))
        self.assertNotIn(bytes((0x1A, 3, 0x1C, 1)), c)
        self.assertTrue(c.endswith(bytes((0x1A, 2, 0x1C, 1)) + n.REMOVE_SELF + b'\xff'))

    def test_stock_death_animation_of_the_reaper(self):
        self.assertEqual(n.stock_death_animation({'id': 'enemy:0072'}), 2)
        self.assertEqual(n.stock_death_animation({'id': 'enemy:0045'}), 2)
        self.assertIsNone(n.stock_death_animation({'id': 'enemy:9999'}))


if __name__ == '__main__':
    unittest.main()
