import inspect,sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from area_ui import AreaPanel


class HeightStepColumnTests(unittest.TestCase):
 """2026-10-25 user bug: a few +1 clicks filled map 495 with wall columns.
 adjust_height ran fix_masks on the clicked tile's whole column, which moved
 pictures of every walled tile in that column into other floors (one +1 on
 495 (24,15) changed 20 more cells down column 24)."""
 def panel(self):
  p=AreaPanel.__new__(AreaPanel)
  p.elevation_enabled=lambda:True;p.original_pieces=lambda:None
  p.editor=SimpleNamespace(session=SimpleNamespace(data=bytearray(64)),current_map=1,database=SimpleNamespace(document={}))
  p.grid_width=1;p.grid_height=4
  p.grid_cells=[dict(x=0,y=y,offset=y*8,values=(0,0,0,0,5,-1),walls=[(None,7,0,0)] if y==3 else []) for y in range(4)]
  p.seen=[];p.record_pieces=lambda c:(p.seen.append(c['y']),[])[1]
  return p
 def test_only_limits_fix_masks_to_the_edited_tile(self):
  p=self.panel();p.fix_masks([0],redraw=False,only={(0,1)})
  self.assertNotIn(3,p.seen)   # the walled tile elsewhere in the column is left alone
  p=self.panel();p.fix_masks([0],redraw=False)
  self.assertIn(3,p.seen)      # the Fix masks button still checks the whole column
 def test_height_edits_pass_only_the_edited_tile(self):
  src=inspect.getsource(AreaPanel.adjust_height)
  self.assertIn('fix_masks([tx],redraw=False,only={(tx,ty)})',src)


if __name__=='__main__':unittest.main()
