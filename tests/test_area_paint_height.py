import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from area_ui import AreaPanel


class Session:
 def __init__(self):
  self.data=bytearray(16)
  self.labels=[]
 def replace(self,offset,payload,label):
  self.data[offset:offset+len(payload)]=payload
  self.labels.append(label)


def cell(x,offset,height,art):
 return dict(x=x,y=0,offset=offset,values=(0,0,0,height,art,-1),walls=[])


class AreaPaintHeightTests(unittest.TestCase):
 def test_group_brush_stamps_art_flat_at_the_clicked_tile_height_atomically(self):
  # Since 2026-10-07 a group stamp lands flat at the clicked tile's height (no gaps).
  session=Session();panel=AreaPanel.__new__(AreaPanel)
  panel.selected=(0,0);panel.brush=10;panel.group_brush={(0,0):0x1234,(1,0):0x2345}
  panel.group_brush_heights={(0,0):2,(1,0):5};panel.commit_pending=lambda:None;panel.wall=SimpleNamespace(get=lambda:'Floor')
  panel.editor=SimpleNamespace(session=session,current_map=7)
  panel.grid_width=2;panel.grid_height=1;panel.grid_cells=[cell(0,0,3,1),cell(1,8,0,2)]
  panel.refresh=lambda **kwargs:None;panel.atlas=lambda:None
  panel.paint_selected()
  self.assertEqual(session.data[3:6],struct.pack('<BH',3,0x1234))
  self.assertEqual(session.data[11:14],struct.pack('<BH',3,0x2345))
  self.assertEqual(panel.grid_cells[0]['values'][3:5],(3,0x1234))
  self.assertEqual(panel.grid_cells[1]['values'][3:5],(3,0x2345))
  self.assertEqual(session.labels,['Tile group stamp'])

 def test_brush_without_source_height_leaves_target_height_unchanged(self):
  session=Session();panel=AreaPanel.__new__(AreaPanel)
  panel.selected=(0,0);panel.brush=0x1234;panel.brush_height=None;panel.group_brush=None
  panel.wall=SimpleNamespace(get=lambda:'Floor');panel.editor=SimpleNamespace(session=session,current_map=7,root=SimpleNamespace(after=lambda *a:'id',after_cancel=lambda *a:None))
  target=cell(0,0,4,0x0001);panel.grid_width=panel.grid_height=1;panel.grid_cells=[target]
  panel.elevation_enabled=lambda:True;panel.margin=64;panel.renderer=SimpleNamespace(tile=lambda code:None)
  panel.refresh=lambda **kwargs:None;panel.atlas=lambda:None;panel.pending_tiles={}
  panel.paint_photos=[];panel.paint_job=None;panel.canvas=SimpleNamespace(create_image=lambda *a,**k:None)
  from unittest.mock import patch
  with patch('area_ui.ImageTk',SimpleNamespace(PhotoImage=lambda *a,**k:object())):
   panel.paint_selected(repaint=False)
  # Painting waits in pending_tiles and is locked in later as one undo step.
  self.assertEqual(panel.pending_tiles[3],struct.pack('<BH',4,0x1234))
  self.assertEqual(target['values'][3:5],(4,0x1234))

 def _single(self,brush_height,target,cells=None,width=1):
  session=Session();panel=AreaPanel.__new__(AreaPanel)
  panel.selected=(0,0);panel.brush=0x1234;panel.brush_height=brush_height;panel.group_brush=None
  panel.wall=SimpleNamespace(get=lambda:'Floor');panel.editor=SimpleNamespace(session=session,current_map=7,root=SimpleNamespace(after=lambda *a:'id',after_cancel=lambda *a:None))
  panel.grid_cells=cells or [target];panel.grid_width=width;panel.grid_height=1
  panel.elevation_enabled=lambda:True;panel.margin=64;panel.renderer=SimpleNamespace(tile=lambda code:None)
  panel.refresh=lambda **kwargs:None;panel.atlas=lambda:None;panel.pending_tiles={}
  panel.paint_photos=[];panel.paint_job=None;panel.canvas=SimpleNamespace(create_image=lambda *a,**k:None)
  from unittest.mock import patch
  with patch('area_ui.ImageTk',SimpleNamespace(PhotoImage=lambda *a,**k:object())):
   panel.paint_selected(repaint=False)
  return panel

 def test_brush_picked_at_another_height_keeps_target_height(self):
  # A tile picked in the tile picker (source height 1) painted on height-4 floor
  # used to drop the floor to 1 and leave a gap.
  target=cell(0,0,4,0x0001);panel=self._single(1,target)
  self.assertEqual(panel.pending_tiles[3],struct.pack('<BH',4,0x1234))

 def test_new_tile_on_empty_ground_takes_neighbour_height(self):
  target=cell(0,0,0,0xFFFF);neighbour=cell(1,8,3,0x0002)
  panel=self._single(None,target,[target,neighbour],width=2)
  self.assertEqual(panel.pending_tiles[3],struct.pack('<BH',3,0x1234))


if __name__=='__main__':unittest.main()
