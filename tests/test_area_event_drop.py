"""A quick drag can release the button before the last pointer move is handled:
the event must land on the tile under the release point (area_ui.release)."""
import sys,types,unittest
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
try:
    from area_ui import AreaPanel
except ImportError:
    AreaPanel=None

@unittest.skipIf(AreaPanel is None,'tkinter not available')
class EventDropTests(unittest.TestCase):
    def test_release_uses_the_release_point(self):
        a=AreaPanel.__new__(AreaPanel)
        row={'id':'e1','region':[10,12,1,1]}
        document={'event_graphs':[row]}
        a.editor=NS(current_map=7,dirty=False,database=NS(document=document),session=NS(replace_document=lambda old,new,label:old.update(new)))
        a.height_edit=NS(get=lambda:False);a.clear_in_front_of_switches=lambda:None
        a.pending_tiles={};a.record_drag=('graphs',0,7,0,0);a.drag_point=None;a.stroke_cells=set()
        a.drag_delta=(0,0);a.drag_shift=(0,0);a.redraw_after_drag=False
        a.canvas=NS(delete=lambda *x:None,canvasx=lambda v:v)
        a.canvas_y=lambda ev:ev.y
        a.highlight_record=lambda:None;a.draw_records=lambda:None;a.caption=NS(set=lambda t:None)
        seen=[]
        def drag_graph(index,px,py):seen.append((px,py));a.drag_delta=(10,6)   # tile under (px,py) is 20,18
        a.drag_graph=drag_graph
        a.release(NS(x=480,y=300))
        self.assertEqual(seen,[(480,300)])
        self.assertEqual(document['event_graphs'][0]['region'][:2],[20,18])

if __name__=='__main__':unittest.main()
