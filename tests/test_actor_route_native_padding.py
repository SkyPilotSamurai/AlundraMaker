import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from event_movement_compile import animation_profile,compile_movement_command
from entity_animation import parse_map_sprite_animations
INPUT=Path(__file__).resolve().parents[1]/'game/disc/DATA/DATAS.BIN'

@unittest.skipUnless(INPUT.exists(),'Requires local lawful stock input')
class NativePaddingTests(unittest.TestCase):
    def test_real_beaumont_and_lyman_padding_agrees_with_asset_decoder(self):
        data=INPUT.read_bytes()
        for catalogue,map_id in [(256,10),(265,6),(268,10),(289,12)]:
            expected=parse_map_sprite_animations(data,map_id,catalogue-256)
            actual=animation_profile(data,catalogue,map_id)
            self.assertEqual(len(actual),len(expected))
            self.assertEqual([row['speed'] for row in actual],[row.speed_raw for row in expected])
            route=compile_movement_command(data,catalogue,dict(mode='route',target='this_event',route=['up','down'],moving_animation=1,idle_animation=0),map_id=map_id)
            self.assertEqual(route,bytes.fromhex('09101a011e100009001a011e10001a0000'))
