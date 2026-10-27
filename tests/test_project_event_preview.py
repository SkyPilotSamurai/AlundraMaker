import unittest,sys
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from project_event_preview import event_world_image,anchor_world_image

class ProjectEventPreviewTests(unittest.TestCase):
    def test_foreign_npc_uses_native_donor_and_keeps_native_size(self):
        image=Image.new('RGBA',(20,30));image.paste((255,0,0,255),(2,3,18,29))
        row={'kind':'npc','source':{'catalogue_index':268,'observed_maps':[242]},'data':{}}
        def preview(session,map_id,index):return (image,0,0) if map_id==242 else None
        with patch('native_class_placement.class_preview',side_effect=preview) as reader:
            actual=event_world_image(SimpleNamespace(),row,163)
        self.assertEqual(actual.size,(16,26));self.assertEqual(reader.call_count,2)
        self.assertEqual(anchor_world_image(actual,4,5,10),(100,80))
    def test_requested_direction_reaches_native_preview(self):
        image=Image.new('RGBA',(8,8),(1,2,3,255))
        row={'kind':'npc','source':{'catalogue_index':268},'data':{}}
        for facing,index in [('down',0),('up',1),('left',2),('right',3)]:
            with patch('native_class_placement.class_preview',return_value=(image,0,0)) as reader:
                event_world_image(object(),row,12,facing)
                self.assertEqual(reader.call_args.args[3],index)
    def test_no_graphic_and_undecoded_graphic_return_marker_request(self):
        self.assertIsNone(event_world_image(object(),None,1))
        with patch('native_class_placement.class_preview',return_value=None):
            self.assertIsNone(event_world_image(object(),{'source':{'catalogue_index':268},'data':{}},1))
if __name__=='__main__':unittest.main()
