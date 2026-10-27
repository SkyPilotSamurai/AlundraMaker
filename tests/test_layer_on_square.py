import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from area_ui import AreaPanel
from bush_catalogue import place_layer


class LayerOnSquareTests(unittest.TestCase):
 def test_layer_on_tile_with_pieces_below_its_floor_lands_on_the_floor(self):
  # 2026-10-25: shift -1 (pieces below the floor) used to append the layer
  # further down the column, on another square.
  grid=(1,1,[dict(values=(0,0,0,6,5,0),walls=(-1,[8607]))])
  place_layer(None,489,[(0,0)],283,grid=grid)
  shift,codes=grid[2][0]['walls']
  self.assertEqual((shift,codes),(1,[283,0xFFFF,8607]))   # 283 at the floor, 8607 still 2 rows below it

 def test_square_covered_by_a_later_tile_uses_a_free_tile_drawn_after_it(self):
  p=AreaPanel.__new__(AreaPanel)
  p.canvas=SimpleNamespace(canvasx=lambda v:v);p.canvas_y=lambda e:e.y
  # square (0,5): tile row 3's floor, covered by a wall piece of tile row 6
  p.renderer=SimpleNamespace(surface_hits={(0,5):[(0,80,0,3,'Floor',100),(0,80,0,6,'Wall 0',200)]})
  p.stack_brush=lambda:(dict(kind='layer',code=283),'')
  p.bush_stroke=[];p.floor_slot_taken=lambda *a:False;p.layer_with_free_tile=MagicMock()
  p.layer_on_square(SimpleNamespace(x=5,y=85))
  self.assertEqual(p.bush_stroke,[])
  p.layer_with_free_tile.assert_called_once_with(5,85,283,7,False)


if __name__=='__main__':unittest.main()
