import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from event_movement_compile import animation_profile, compile_verified_self_route,compile_movement_command


def fixture():
    data = bytearray(0x1800)
    struct.pack_into('<2I', data, 0, 0x800, 0x1800)
    struct.pack_into('<12I', data, 0x800, 0, 0, 0, 48, 1072, 1076, 1080, 1082, 1084, 1086, 1088, 1090)
    struct.pack_into('<i', data, 0x800 + 48 + 4 * 130, 1100)
    struct.pack_into('<4I', data, 0x800 + 1100, 1132, 1160, 1192, 1200)
    for n, speed in enumerate((0, 128)):
        struct.pack_into('<4HH4B', data, 0x800 + 1132 + n * 14, 0, 8, 16, 24, speed, 0, 0, 0, 1)
    return data


class NativeMovementCompileTests(unittest.TestCase):
    def test_authoring_route_adapter_and_unsafe_targets(self):
        command=dict(type='move_actor',target='this_event',mode='walk_tiles',tiles=2,direction='right',moving_animation=1,idle_animation=0)
        self.assertEqual(compile_movement_command(fixture(),130,command),
            compile_verified_self_route(fixture(),130,['right','right'],moving_animation=1,idle_animation=0,skip_impossible=False))
        command.update(mode='route',route=['down','left'])
        self.assertEqual(compile_movement_command(fixture(),130,command),
            compile_verified_self_route(fixture(),130,['down','left'],moving_animation=1,idle_animation=0,skip_impossible=False))
        for update in ({'target':'npc:other'},{'mode':'toward_player'},{'moving_animation':None}):
            with self.assertRaises(ValueError):compile_movement_command(fixture(),130,dict(command,**update))
        with self.assertRaises(ValueError):compile_movement_command(fixture(),None,command)
    def test_native_walk_distance_and_direction_encoding(self):
        raw = compile_verified_self_route(fixture(), 130, ['down', 'left', 'up', 'right'], moving_animation=1, idle_animation=0)
        self.assertEqual(raw, bytes.fromhex('09001a011e1000 09081a011e1800 09101a011e1000 09181a011e1800 1a0000'))

    def test_animation_requires_moving_speed_and_real_directions(self):
        data = fixture()
        with self.assertRaises(ValueError): compile_verified_self_route(data, 130, ['up'], moving_animation=0, idle_animation=1)
        struct.pack_into('<H', data, 0x800 + 1150, 65535)
        with self.assertRaises(ValueError): compile_verified_self_route(data, 130, ['up'], moving_animation=1, idle_animation=0)

    def test_profile_bounds_unknown_class_and_invalid_routes(self):
        self.assertEqual([r['speed'] for r in animation_profile(fixture(), 130)], [0, 128])
        for route in ([], ['north'], ['up'] * 256, [[]], [1]):
            with self.assertRaises(ValueError): compile_verified_self_route(fixture(), 130, route, moving_animation=1, idle_animation=0)
        with self.assertRaises(ValueError): animation_profile(fixture(), 131)
        with self.assertRaises(ValueError): animation_profile(fixture(), 256)
        for data in (b'', b'\0' * 8, None):
            with self.assertRaises((ValueError, struct.error)): animation_profile(data, 256, 10)
        data = bytearray(0x800)
        struct.pack_into('<I', data, 0x28, len(data) - 4)
        with self.assertRaises(ValueError): animation_profile(data, 256, 0)


if __name__ == '__main__': unittest.main()
