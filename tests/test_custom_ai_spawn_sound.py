import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from native_custom_ai import compile_custom_ai
from sound_database import encode_sound

ATTACK = {'name': 'B', 'type': 'spawned', 'min_distance': 3, 'max_distance': 8, 'chance': 50, 'interval': 120,
          'animation': 4, 'frames': 40, 'prepare_animation': None, 'stall_before': 0, 'move_before': 'none',
          'move_during': 'none', 'spawn_class': 'object:0143', 'spawn_frame': 12, 'spawn_x': 0, 'spawn_y': 0, 'spawn_z': 16}


def build(**extra):
    ai = {'mode': 'custom', 'chase': True, 'attacks': [dict(ATTACK, **extra)]}
    return compile_custom_ai(ai, walk_animation=1, idle_animation=0, class_bits=0, vital=False, spawn_templates={'object:0143': 5})


class SpawnSoundTests(unittest.TestCase):
    def test_sound_follows_the_spawn(self):
        code = build(spawn_sound=181)
        spawn = bytes((0x8B, 0x80, 5, 0, 0, 0, 0, 16, 0))   # template 5 at x 0, y 0, height 16
        self.assertIn(spawn + encode_sound(181), code)

    def test_no_sound_by_default(self):
        self.assertNotIn(encode_sound(181), build())
        self.assertEqual(build(), build(spawn_sound=None))


if __name__ == '__main__':
    unittest.main()
