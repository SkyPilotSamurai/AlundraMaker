import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_actor_route_profile import compile_route_profile

class ProfileTests(unittest.TestCase):
    def test_handoff_owns_route_and_actions(self):
        command={'moving_animation':1,'idle_animation':0,'blocked_behavior':'wait'}
        with patch('native_actor_route_profile.compile_movement_command',return_value=bytes.fromhex('09101a011e10001a0000')):
            programs,report=compile_route_profile(b'data',260,command,map_id=163,after=bytes.fromhex('980100'))
        self.assertEqual(programs['C'],b'\xff')
        self.assertEqual(programs['F'],bytes.fromhex('6604000009101a011e10001a0000980100ff'))
        self.assertFalse(report['runtime_verified'])
        self.assertEqual(report['speed_percent'],100)

    def test_errors_from_sprite_validation_preserved(self):
        with patch('native_actor_route_profile.compile_movement_command',side_effect=ValueError('Bad native pose')):
            with self.assertRaisesRegex(ValueError,'Bad native pose'):
                compile_route_profile(b'',260,{},map_id=163)
