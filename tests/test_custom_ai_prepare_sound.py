import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from native_custom_ai import compile_custom_ai
from sound_database import encode_sound, encode_stop_sound

ATTACK = {'name': 'B', 'type': 'spawned', 'min_distance': 3, 'max_distance': 8, 'chance': 50, 'interval': 120,
          'animation': 4, 'frames': 40, 'prepare_animation': 2, 'stall_before': 20, 'move_before': 'none',
          'move_during': 'none', 'spawn_class': 'object:0143', 'spawn_frame': 12, 'spawn_x': 0, 'spawn_y': 0, 'spawn_z': 16}
SOUNDS = {2: 97, 4: 0}


def build(**extra):
    ai = {'mode': 'custom', 'chase': True, 'attacks': [dict(ATTACK, **extra)]}
    return compile_custom_ai(ai, walk_animation=1, idle_animation=0, class_bits=0, vital=False,
                             spawn_templates={'object:0143': 5}, anim_sounds=SOUNDS)


class PrepareSoundTests(unittest.TestCase):
    def test_default_is_unchanged(self):
        self.assertEqual(build(), build(prepare_sound=None))
        self.assertNotIn(encode_stop_sound(97), build())
        self.assertIn(bytes((0x1A, 2, 0x37, 20)), build())

    def test_none_stops_the_animation_sound_after_its_tick(self):
        self.assertIn(bytes((0x1A, 2, 0x37, 0)) + encode_stop_sound(97) + bytes((0x37, 19)), build(prepare_sound=-1))

    def test_chosen_sound_replaces_it(self):
        self.assertIn(bytes((0x1A, 2, 0x37, 0)) + encode_stop_sound(97) + encode_sound(181) + bytes((0x37, 19)),
                      build(prepare_sound=181))

    def test_silent_animation_just_plays_the_chosen_sound(self):
        code = build(prepare_animation=4, prepare_sound=181)
        self.assertIn(bytes((0x1A, 4)) + encode_sound(181) + bytes((0x37, 20)), code)

    def test_sound_without_prepare_animation(self):
        code = build(prepare_animation=None, stall_before=20, prepare_sound=181)
        self.assertIn(bytes((0x1A, 0)) + encode_sound(181), code)   # stall: idle animation (sound 0 here)
        code = build(prepare_animation=None, stall_before=0, prepare_sound=181)
        self.assertIn(bytes((0x27,)) , code); self.assertIn(encode_sound(181), code)
        self.assertNotIn(encode_stop_sound(97), build(prepare_animation=None, prepare_sound=-1))


if __name__ == '__main__':
    unittest.main()
