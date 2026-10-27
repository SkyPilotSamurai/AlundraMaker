"""2026-10-25 user bug (map 489): painting a height on one square changed another
('One edits the other'). Each paint must change only the clicked square, in normal
and Wall mode, and leave the picture identical; an edit that can't do that is undone."""
import copy,sys,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
DATAS=ROOT/'game/disc/DATA/DATAS.BIN';MOD=ROOT/'game/Maker Demo/Maker Demo.alundramod'


class _Var:
 def __init__(s,v):s.v=v
 def get(s):return s.v
 def set(s,v):s.v=v


class _Canvas:
 def create_text(s,*a,**k):return 0
 def create_image(s,*a,**k):return 0
 def canvasx(s,v):return v
 def canvasy(s,v):return v
 def find_withtag(s,t):return []
 def __getattr__(s,n):return lambda *a,**k:None


@unittest.skipUnless(DATAS.exists() and MOD.exists(),'private Maker Demo inputs not present')
class HeightSquareAlone(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import mod_export
  cls.session,_=mod_export.load_mod(DATAS.read_bytes(),MOD)
 def panel(self):
  from area_ui import AreaPanel
  from area_map import MapRenderer,grid
  s=self.session;p=AreaPanel.__new__(AreaPanel)
  p.editor=SimpleNamespace(session=s,current_map=489,database=SimpleNamespace(document=copy.deepcopy(s.content_database)),dirty=False,
                           root=SimpleNamespace(after=lambda d,f:None,after_cancel=lambda j:None))
  p.canvas=_Canvas();p.map_crop_top=0;p.renderer=MapRenderer(s,489);_,p.hits,p.margin=p.renderer.render(True)
  p.grid_width,p.grid_height,p.grid_cells=grid(s,489)
  p.pending_heights={};p.pending_tiles={};p.pending_stack_grid=None;p.pending_stack_tiles=set()
  p.mark_walls=_Var(False);p.height_edit=_Var(True);p.height_show=_Var('Lowest');p.show_wall_pit_heights=_Var(False)
  p.height_wall_mode=_Var(False);p.height_brush=_Var(3);p.walk_blocks=_Var('Blocks everyone');p.caption=_Var('');p.last_height_edit=None
  p.elevation_enabled=lambda:True;p.raise_height_numbers=lambda:None;p.schedule_height_redraw=lambda delay=40:None
  p.redraw_columns=lambda *a,**k:None;p.brush=None;p.paint_photos=[]
  return p
 def test_each_square_alone_both_modes(self):
  base=bytes(self.session.data);done=0
  for wall in (False,True):
   for x in range(9,15):
    for r in range(3,8):
     for brush in (2,5):
      p=self.panel();sq=(x*24,r*16+p.margin)
      v0=p.height_view_values();pics=[p.column_picture(c) for c in range(p.grid_width)]
      p.height_wall_mode.set(wall);p.height_brush.set(brush);p.paint_height(None,square=sq)
      v1=p.height_view_values()
      changed=[k for k in set(v0)|set(v1) if k!=sq and v0.get(k)!=v1.get(k)]
      self.assertEqual(changed,[],(wall,x,r,brush))
      self.assertEqual([p.column_picture(c) for c in range(p.grid_width)],pics,(wall,x,r,brush))
      self.assertIn(v1.get(sq),(v0.get(sq),p.wanted_square_value(brush,wall)))
      done+=v1.get(sq)!=v0.get(sq)
  self.assertEqual(bytes(self.session.data),base)
  self.assertGreater(done,0)
 def test_grey_square_gets_its_own_record(self):
  # (9,3) is a grey square whose wall picture belongs to record (9,8), which also shows
  # the 1 on (9,0): painting 2 used to edit (9,8) and change (9,0).
  p=self.panel();sq=(9*24,3*16+p.margin);v0=p.height_view_values()
  p.height_brush.set(2);p.paint_height(None,square=sq);v1=p.height_view_values()
  self.assertEqual(v1[sq],frozenset({'2'}))
  self.assertEqual(v1.get((9*24,p.margin)),v0.get((9*24,p.margin)))


if __name__=='__main__':unittest.main()
