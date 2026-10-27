import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from test_local_sprite_import import fixture
from editor_session import EditSession
from animation_preview import load_animation,available_animations,terminal_meaning,preview_delay_ms
from entity_preview import EntityPreview


class PreviewTests(unittest.TestCase):
    def test_native_frames_pixels_delays_and_fixed_canvas(self):
        session=EditSession(fixture(),verify=False)
        clip=load_animation(session,2,263)
        self.assertEqual(len(clip.frames),1);self.assertEqual(clip.frames[0].delay_raw,0x81)
        self.assertEqual(clip.duration_ticks,1);self.assertEqual(clip.native_speed_raw,1)
        self.assertEqual(clip.terminal_kind,'loop')
        im=EntityPreview(session,2).frame(7)[0]
        self.assertEqual(clip.frames[0].image.tobytes(),im.tobytes())
        self.assertEqual(clip.canvas_image(clip.frames[0]).size,im.size)
        self.assertEqual(clip.frame_at_tick(100).index,0)
        self.assertEqual(available_animations(session,2,263)[0]['direction_frames'],(1,0,0,0))

    def test_direction_fallback_and_range_validation(self):
        session=EditSession(fixture(),verify=False)
        self.assertEqual(load_animation(session,2,263,direction=2).selected_direction,0)
        with self.assertRaisesRegex(ValueError,'no drawable'):load_animation(session,2,263,direction=2,fallback_direction=False)
        with self.assertRaises(ValueError):load_animation(session,2,263,animation_index=1)

    def test_lossless_transition_types_and_no_forced_loop(self):
        self.assertEqual(terminal_meaning(b'\x01'),('loop',None))
        self.assertEqual(terminal_meaning(b'\x00\x04'),('change',4))
        self.assertEqual(terminal_meaning(b'\x00\x80'),('hold',None))
        self.assertEqual(terminal_meaning(b'\x7f'),('change',0))
        self.assertEqual(terminal_meaning(b'\xff'),('unknown',None))
        d=fixture();sp=2048+2*2048+40;d[sp+223:sp+225]=b'\x00\x80'
        clip=load_animation(EditSession(d,verify=False),2,263)
        self.assertEqual(clip.terminal_kind,'hold');self.assertEqual(clip.terminator,b'\x00\x80')
        self.assertEqual(clip.frame_at_tick(100).index,0)

    def test_rotated_quad_is_drawn_and_keeps_raw_metadata(self):
        # 2026-10-08: rotated/scaled quads are drawn (perspective map of the
        # texture rectangle onto the four corners) instead of left empty.
        d=fixture();sp=2048+2*2048+40;d[sp+230+2+10]=1
        clip=load_animation(EditSession(d,verify=False),2,263)
        self.assertIsNotNone(clip.frames[0].image)
        self.assertIsNone(clip.frames[0].unsupported_reason)
        self.assertEqual(clip.frames[0].image_set_index,0)

    def test_global_bank_and_display_speed_do_not_change_data(self):
        d=fixture();sp=2048+2*2048+40;struct.pack_into('<2I',d,0,sp,sp+320)
        struct.pack_into('<I',d,0x14,sp+2048)
        session=EditSession(d,verify=False);original=bytes(session.data)
        clip=load_animation(session,427,7)
        self.assertEqual(len(clip.frames),1)
        self.assertEqual(preview_delay_ms(6,60,1),100)
        self.assertEqual(preview_delay_ms(6,60,2),50)
        self.assertEqual(bytes(session.data),original)


if __name__=='__main__':unittest.main()
