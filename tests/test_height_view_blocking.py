import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
DATAS=ROOT/'game/disc/DATA/DATAS.BIN'

@unittest.skipUnless(DATAS.exists(),'private DATAS.BIN not present')
class HeightViewBlocking(unittest.TestCase):
 def test_stock_maps_untouched(self):
  from editor_session import EditSession
  from height_view_blocking import apply_height_view_blocking,project_maps
  s=EditSession.open_data(DATAS.read_bytes(),DATAS)
  self.assertEqual(list(project_maps(s)),[])
  out,changes=apply_height_view_blocking(s)
  self.assertEqual(changes,{});self.assertIs(out,s)
 def test_covered_cells_take_shown_height_on_edited_map(self):
  from editor_session import EditSession
  from area_map import grid
  from height_view_blocking import apply_height_view_blocking,view_rules
  s=EditSession.open_data(DATAS.read_bytes(),DATAS)
  w,h,c=grid(s,345)
  # stock 345: (4,12) is a walkable height-0 cell with no picture, under the raised floor's number
  self.assertEqual(c[12*w+4]['values'][:4],(4,144,4,0))
  # raise its neighbour row like the Maker Demo copy did, so the map counts as edited
  o=c[11*w+4]['offset'];s.data[o+3]=3
  # under a shown number: exported at that height, flags kept, not blocked (user 2026-10-25)
  grey,heights=view_rules(s,345)
  self.assertNotIn((4,12),grey);self.assertIn((4,12),heights);self.assertGreater(heights[(4,12)],0)
  out,changes=apply_height_view_blocking(s)
  self.assertIn(345,changes)
  self.assertIsNot(out,s)
  oc=grid(out,345)[2]
  self.assertEqual(oc[12*w+4]['values'][:3],(4,144,4));self.assertEqual(oc[12*w+4]['values'][3],heights[(4,12)])
  for x,y in changes[345]:
   self.assertEqual(oc[y*w+x]['values'][0]&0x41,0x41)
  self.assertEqual(s.data[c[12*w+4]['offset']+3],0)   # input session unchanged
