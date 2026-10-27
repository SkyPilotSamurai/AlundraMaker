import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from area_ui import AreaPanel


def panel(wall):
 p=AreaPanel.__new__(AreaPanel)
 p.editor=SimpleNamespace(session=SimpleNamespace(data=bytearray(32)),dirty=False)
 p.grid_width=1;p.grid_height=4;p.pending_heights={};p.pending_tiles={}
 p.grid_cells=[dict(x=0,y=y,offset=8*y,values=(0,0,0,y,0x10+y,-1),walls=[]) for y in range(4)]
 p.height_wall_mode=SimpleNamespace(get=lambda:wall);p.height_brush=SimpleNamespace(get=lambda:3)
 p.height_stack={(0,0):(0,1)};p.height_grey={};p.drawn_x={};p.height_shown={}
 p.caption=SimpleNamespace(set=lambda t:None)
 def swap(tx,ty,ny,target):   # stands in for the normal-mode record move
  v=list(p.grid_cells[ny]['values']);v[3]=target;p.grid_cells[ny]['values']=tuple(v)
 p.swap_for_height=MagicMock(side_effect=swap)
 for name in ('undo_made_wall','fix_masks','schedule_height_redraw','clear_x_at'):setattr(p,name,MagicMock())
 return p


class HeightWallModeTests(unittest.TestCase):
 def test_wall_mode_moves_the_record_like_normal_mode_then_makes_it_a_wall(self):
  # user 2026-10-25: Wall + N keeps the tile on the clicked square (record moves
  # to row + N - height) and makes only that tile a wall (byte 0 |= 0x41).
  p=panel(True);p._paint_height_body(None,square=(0,0))
  p.swap_for_height.assert_called_once_with(0,1,3,3)
  self.assertEqual(p.pending_heights,{24:0x41})
  self.assertEqual(p.grid_cells[3]['values'][0],0x41)
  self.assertEqual([c['values'][0] for c in p.grid_cells[:3]],[0,0,0])
  p.undo_made_wall.assert_not_called()

 def test_normal_mode_does_not_wall(self):
  p=panel(False);p._paint_height_body(None,square=(0,0))
  p.swap_for_height.assert_called_once_with(0,1,3,3);self.assertEqual(p.pending_heights,{})


if __name__=='__main__':unittest.main()
