import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import bush_catalogue as bc
INPUT=ROOT/'game/disc/DATA/DATAS.BIN'

class SplitStackTests(unittest.TestCase):
 def test_bush_is_the_part_on_and_above_the_floor(self):
  self.assertEqual(bc.split_stack((2,[10,11,12])),([10,11],[12]))
  self.assertEqual(bc.split_stack((0,[12])),([],[12]))
  self.assertEqual(bc.split_stack(None),([],[]))

@unittest.skipUnless(INPUT.exists(),'Local lawful native input required')
class BushPlacementTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from editor_session import EditSession
  cls.data=INPUT.read_bytes()
 def session(self):
  from editor_session import EditSession
  return EditSession(self.data,verify=False)
 def test_styles_are_isolated_bushes(self):
  styles=bc.bush_styles(self.session(),maps=range(0,12))
  self.assertTrue(styles);self.assertTrue(all(s['shift']==len(s['codes']) for s in styles))
 def test_plant_keeps_floor_height_and_cliff_then_remove(self):
  from area_map import grid
  s=self.session();style=bc.bush_styles(s,maps=[1])[0]
  w,h,cells=grid(s,3)
  raised=next(c for c in cells if c['walls'] and c['walls'][0][2]==0 and not c['values'][0]&2)
  x,y=raised['x'],raised['y'];before=raised['values']
  self.assertEqual(bc.place_bush(s,SimpleNamespace(document={}),3,[(x,y)],style),1)
  after=grid(s,3)[2][y*w+x]
  self.assertEqual(after['values'][0],before[0]|2);self.assertEqual(after['values'][3:5],before[3:5])
  self.assertEqual(len(after['walls']),len(style['codes'])+len(raised['walls']))
  self.assertEqual(after['walls'][-1][1],raised['walls'][-1][1])   # the tile's own cliff face stays
  self.assertEqual(bc.remove_bush(s,3,[(x,y)]),1)
  gone=grid(s,3)[2][y*w+x]
  self.assertEqual(gone['values'][0],before[0]&~2);self.assertEqual([k for _,k,_,_ in gone['walls']],[k for _,k,_,_ in raised['walls']])

class WallsTests(BushPlacementTests):
 def test_wall_stack_brush_keeps_floor_and_removes_cleanly(self):
  from area_map import grid
  s=self.session();stacks=bc.wall_stacks(s,3);self.assertTrue(stacks)
  self.assertIn(stacks[0]['codes'][0],bc.floor_codes(s,3)+[c for st in stacks for c in st['codes']])
  w,h,cells=grid(s,20);plain=next(c for c in cells if not c['walls'] and c['values'][4]!=0xFFFF)
  x,y=plain['x'],plain['y']
  self.assertEqual(bc.place_walls(s,SimpleNamespace(document={}),20,[(x,y)],stacks[0]),1)
  after=grid(s,20)[2][y*w+x];self.assertEqual(after['values'],plain['values'][:5]+(after['values'][5],))
  self.assertEqual(len(after['walls']),len(stacks[0]['codes']))
  self.assertEqual(bc.remove_walls(s,20,[(x,y)]),1);self.assertEqual(grid(s,20)[2][y*w+x]['walls'],[])

class FloorLayerTests(unittest.TestCase):
 def test_layer_goes_on_the_floor_and_keeps_other_layers(self):
  from types import SimpleNamespace
  from unittest.mock import patch
  cells=[dict(values=(0,0,4,2,100,-1),walls=None),dict(values=(0,0,4,2,100,-1),walls=(0,[7,8])),dict(values=(0,0,4,2,100,-1),walls=(2,[5,6,9]))]
  out={}
  with patch('map_area_copy.cells_of',return_value=(3,1,cells)),patch('map_area_copy.rebuild_grid',lambda s,m,c,l:out.update(c=c)):
   self.assertEqual(bc.place_layer(None,0,[(0,0),(1,0),(2,0)],42),3)
  self.assertEqual([c['walls'] for c in out['c']],[(1,[42]),(1,[42,7,8]),(2,[5,42,9])])
  self.assertTrue(all(c['values'][4]==100 for c in out['c']))   # floors stay
  with patch('map_area_copy.cells_of',return_value=(3,1,out['c'])),patch('map_area_copy.rebuild_grid',lambda s,m,c,l:out.update(c=c)):
   self.assertEqual(bc.remove_layer(None,0,[(0,0),(1,0),(2,0)]),3)
  self.assertEqual([c['walls'] for c in out['c']],[None,(0,[7,8]),(2,[5,0xFFFF,9])])

class WallTileTests(unittest.TestCase):
 def test_wall_tile_goes_under_the_lowest_layer(self):
  from unittest.mock import patch
  cells=[dict(values=(0,0,4,2,100,-1),walls=None),dict(values=(0,0,4,2,100,-1),walls=(2,[5,6])),dict(values=(0,0,4,2,100,-1),walls=(0,[7]))]
  out={}
  with patch('map_area_copy.cells_of',return_value=(3,1,cells)),patch('map_area_copy.rebuild_grid',lambda s,m,c,l:out.update(c=c)):
   self.assertEqual(bc.place_face(None,0,[(0,0),(1,0),(2,0)],42),3)
  self.assertEqual([c['walls'] for c in out['c']],[(0,[42]),(2,[5,6,42]),(0,[7,42])])
  with patch('map_area_copy.cells_of',return_value=(3,1,out['c'])),patch('map_area_copy.rebuild_grid',lambda s,m,c,l:out.update(c=c)):
   self.assertEqual(bc.remove_face(None,0,[(0,0),(1,0),(2,0)]),3)
  self.assertEqual([c['walls'] for c in out['c']],[None,(2,[5,6]),(0,[7])])
 def test_bush_above_the_floor_is_not_removed_as_a_wall_tile(self):
  from unittest.mock import patch
  cells=[dict(values=(2,0,4,2,100,-1),walls=(2,[5,6]))]
  with patch('map_area_copy.cells_of',return_value=(1,1,cells)),patch('map_area_copy.rebuild_grid',lambda *a:None):
   self.assertEqual(bc.remove_face(None,0,[(0,0)]),0)

if __name__=='__main__':unittest.main()
