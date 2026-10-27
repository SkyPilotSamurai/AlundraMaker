import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from map_tile_library import map_library
from area_ui import AreaPanel
class TileSelectorLayoutTests(unittest.TestCase):
 def test_percentage_width_and_manual_resize_survive_window_resize(self):
  p=AreaPanel.__new__(AreaPanel);width=[1920];position=[0]
  def sash(index,value=None):
   if value is not None:position[0]=value
   return position[0]
  p.workspace_panes=SimpleNamespace(winfo_width=lambda:width[0],panes=lambda:(1,2),sashpos=sash,identify=lambda x,y:0)
  p.picker_width_fraction=.26;p.picker_sash_dragging=False;p.pane_layout_job=None
  p.apply_pane_layout();self.assertEqual(position[0],499)
  width[0]=1280;p.apply_pane_layout();self.assertEqual(position[0],333)
  p.begin_pane_resize(SimpleNamespace(x=333,y=100));position[0]=448;p.end_pane_resize(None)
  width[0]=1920;p.apply_pane_layout();self.assertEqual(position[0],672)
 def test_all_map_layers_not_only_selected_cell(self):
  p=AreaPanel.__new__(AreaPanel);chosen=['Wall 3'];values=[]
  p.grid_cells=[{'walls':[]},{'walls':[1,2,3,4]}]
  p.wall=SimpleNamespace(get=lambda:chosen[0],set=lambda v:chosen.__setitem__(0,v))
  p.wall_combo=SimpleNamespace(configure=lambda **kw:values.append(kw['values']))
  p.update_layer_choices();self.assertEqual(values[-1],['Floor','Wall 0','Wall 1','Wall 2','Wall 3']);self.assertEqual(chosen[0],'Wall 3')
  p.grid_cells=[{'walls':[]}];p.update_layer_choices();self.assertEqual(chosen[0],'Floor')
 def test_two_columns_preserve_every_tile_and_group_positions(self):
  cells=[dict(x=x,y=0,values=(0,0,0,0,x),walls=[]) for x in (0,8,16)]
  renderer=SimpleNamespace(session=object(),m=0,tile=lambda c:Image.new('RGBA',(24,16),(c+1,2,3,255)))
  with patch('map_tile_library.grid',return_value=(24,1,cells)):
   single,a=map_library(renderer);wide,b=map_library(renderer,columns=2)
  self.assertEqual(wide.width,480);self.assertLess(wide.height,single.height)
  self.assertEqual(sorted(c for x,y,c in a),sorted(c for x,y,c in b))
  self.assertEqual(b[1][0],248);self.assertEqual(b[0][1],b[1][1]);self.assertGreater(b[2][1],b[1][1])
