"""Class colour / animation speed / movement speed installed per map (tools/class_looks.py)."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
DATAS=ROOT/'game'/'disc'/'DATA'/'DATAS.BIN'

@unittest.skipUnless(DATAS.is_file(),'private retail DATAS.BIN not present')
class ClassLooksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=DATAS.read_bytes()
    def sets(self,data):
        from class_looks import _sprite_bounds
        from entity_animation import parse_sprite_animation_record
        start,end,sh=_sprite_bounds(data,327)
        return parse_sprite_animation_record(data,start,end,418&255,sh[3],sh[4])
    def test_animation_speed_halves_frame_delays_and_keeps_size(self):
        from class_looks import scale_animation_speed
        out,n=scale_animation_speed(self.data,327,418,200)
        self.assertEqual(len(out),len(self.data));self.assertGreater(n,0)
        for a,b in zip(self.sets(self.data),self.sets(out)):
            for sa,sb in zip(a.streams,b.streams):
                if sa is None:continue
                for fa,fb in zip(sa.frames,sb.frames):
                    self.assertEqual(fb.delay_raw&0x80,0x80)
                    t=fa.delay_raw&0x7F
                    if t:self.assertEqual(fb.delay_raw&0x7F,max(1,round(t/2)))
    def test_movement_speed_scales_set_speed_only(self):
        from class_looks import scale_movement_speed
        out,n=scale_movement_speed(self.data,327,418,150)
        for a,b in zip(self.sets(self.data),self.sets(out)):
            self.assertEqual(b.speed_raw,max(1,round(a.speed_raw*1.5)) if a.speed_raw else 0)
            self.assertEqual(a.streams,b.streams)
    def test_settings_default_and_global_classes_refused(self):
        from class_looks import class_settings,scale_movement_speed
        self.assertEqual(class_settings({'data':{}}),(0,100,100,100))
        with self.assertRaises(ValueError):scale_movement_speed(self.data,327,30,150)

    def test_static_frame_points_every_frame_at_the_chosen_picture(self):
        from class_looks import apply_static_frames
        class X: pass
        x=X();x.data=bytearray(self.data)
        doc={'definitions':[{'id':'npc:m','kind':'npc','source':{'catalogue_index':418}}],
             'event_graphs':[{'id':'e','map_id':327,'pages':[{'class_id':'npc:m'}],
                              'native_placement':{'animation':3,'animation_static':True,'static_frame':1}}]}
        report=apply_static_frames(x,doc)
        self.assertEqual(report[0].get('animation'),3,report);self.assertEqual(len(x.data),len(self.data))
        before,after=self.sets(self.data)[3],self.sets(bytes(x.data))[3]
        for sa,sb in zip(before.streams,after.streams):
            if sa is None:continue
            want=sa.frames[min(1,len(sa.frames)-1)].image_set_index
            self.assertEqual({f.image_set_index for f in sb.frames},{want})
        self.assertEqual(self.sets(bytes(x.data))[2].streams[0].frames[0].image_set_index,
                         self.sets(self.data)[2].streams[0].frames[0].image_set_index)

if __name__=='__main__':unittest.main()
