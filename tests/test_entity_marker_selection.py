import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from area_ui import AreaPanel

class Value:
 def __init__(self,v):self.v=v
 def get(self):return self.v

class Canvas:
 def __init__(self):self.rects=[]
 def delete(self,*a):pass
 def bbox(self,*a):return None
 def create_rectangle(self,*a,**k):self.rects.append(a)
 def canvasx(self,x):return x
 def canvasy(self,y):return y

class EntityMarkerSelection(unittest.TestCase):
 def panel(self,crop=0):
  area=AreaPanel.__new__(AreaPanel)
  area.canvas=Canvas();area.map_crop_top=crop;area.record_drag=None;area.drag_delta=(0,0)
  # Marker for entity 0 on tile (0,2): stored as tile centre X and tile BOTTOM edge Y.
  area.markers=[(12,48,0)]
  return area
 def test_selection_box_covers_the_entity_tile_not_the_one_below(self):
  area=self.panel();area.selected_record=('entities',0);area.highlight_record()
  self.assertEqual(area.canvas.rects[-1],(0,32,24,48))
 def test_selection_box_respects_cropped_view(self):
  area=self.panel(crop=10);area.selected_record=('entities',0);area.highlight_record()
  self.assertEqual(area.canvas.rects[-1],(0,22,24,38))
 def test_clicking_the_entity_tile_selects_it_and_tile_below_does_not(self):
  area=self.panel();area.height_edit=Value(False);area.mode=Value('Select tile')
  area.warp_hit_boxes=[];area.info={'events':[]};area.project_graphs=[]
  area.whole_map_events=set();area.whole_map_graphs=set();area.default_visible=lambda k:True
  area.editor=SimpleNamespace(database=SimpleNamespace(document={}),current_map=0)
  self.assertEqual(area.record_at(SimpleNamespace(x=12,y=40)),('entities',0))
  self.assertIsNone(area.record_at(SimpleNamespace(x=12,y=52)))
if __name__=='__main__':unittest.main()
