import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_default_route_profile import compile_default_route


class DefaultRouteTests(unittest.TestCase):
    @patch('native_default_route_profile.compile_movement_command',return_value=bytes.fromhex('09181a011e18001a0000'))
    def test_repeat_back_edge_targets_initial_move(self, movement):
        programs,report=compile_default_route(b'',260,{'repeat':True,'idle_animation':0},map_id=163)
        code=programs['C'];offset=7
        self.assertEqual(code[offset],2)
        self.assertEqual(offset+struct.unpack_from('<h',code,offset+1)[0],0)
        self.assertEqual(code[-1],255)
        self.assertEqual(programs['F'],b'\xff')
        self.assertFalse(report['runtime_verified'])

    @patch('native_default_route_profile.compile_movement_command',return_value=bytes.fromhex('09181a011e18001a0000'))
    def test_one_time_finishes_at_idle_then_end(self, movement):
        programs,_=compile_default_route(b'',260,{'repeat':False},map_id=163)
        self.assertEqual(programs['C'],bytes.fromhex('09181a011e18001a0000ff'))

    def test_skip_blocking_or_non_boolean_repeat_rejected(self):
        for command in ({'repeat':1},{'blocked_behavior':'skip'}):
            with self.subTest(command=command),self.assertRaises(ValueError):
                compile_default_route(b'',260,command,map_id=163)


if __name__=='__main__':unittest.main()
