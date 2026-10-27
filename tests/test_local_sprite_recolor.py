import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from test_local_sprite_import import fixture
from local_sprite_recolor import shift_hue,recolor_local_class
from local_sprite_import import layout
from editor_session import EditSession
from entity_preview import EntityPreview
from map_block_repack import pointers


class PaletteForkTests(unittest.TestCase):
    def test_hue_rgb555_transparency_stp_and_neutral(self):
        words=[0,31,0x801f,0x4210]+[0]*12
        result=shift_hue(words,120)
        self.assertEqual(result[:4],(0,31<<5,0x8000|(31<<5),0x4210))
        self.assertEqual(shift_hue(words,360),tuple(words))

    def test_same_id_aliases_other_assets_remain_original(self):
        d=fixture();b,h,s,e,sh=layout(d,2)
        struct.pack_into('<I',d,s+sh[3]+6*4,172) # two native classes share an asset
        old=EntityPreview(EditSession(d,verify=False),2).frame(6)[0]
        new,report=recolor_local_class(d,2,263,120)
        session=EditSession(new,verify=False);changed=EntityPreview(session,2).frame(7)[0]
        unaffected=EntityPreview(session,2).frame(6)[0]
        self.assertEqual(unaffected.tobytes(),old.tobytes())
        self.assertEqual(changed.size,old.size)
        self.assertEqual(changed.getpixel((0,0)),(0,255,0,255))
        self.assertEqual(old.getpixel((0,0)),(255,0,0,255))
        self.assertTrue(report['native_identity_preserved'])
        self.assertFalse(report['independent_instance_clone'])
        ob,oh,os,oe,osh=layout(new,2)
        self.assertEqual(d[b+h[4]:b+h[5]],new[ob+oh[4]:ob+oh[5]])
        self.assertEqual(d[s+sh[0]:s+sh[1]],new[os+osh[0]:os+osh[1]])
        pp,qq=pointers(d),pointers(new)
        for m in (0,1,3,242,482):self.assertEqual(d[pp[m]:pp[m+1]],new[qq[m]:qq[m+1]])

    def test_invalid_hue_and_global_class_are_rejected(self):
        d=fixture()
        with self.assertRaises(ValueError):recolor_local_class(d,2,7,120)
        for value in (361,-361,float('nan'),True,'red'):
            with self.assertRaises(ValueError):shift_hue([0]*16,value)


if __name__=='__main__':unittest.main()
