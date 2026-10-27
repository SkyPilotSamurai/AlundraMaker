import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_session import EditSession
from mod_export import build_snapshot
from event_graph import new_event_graph
from event_export import prepare_native_event_export
from test_native_script_allocation import fixture
from map_inspector import inspect_map

class BuildSnapshotTests(unittest.TestCase):
 def test_gui_snapshot_compiles_events_and_freezes_source(self):
  session=EditSession(fixture(),verify=False)
  graph=new_event_graph('event:gui',2,'GUI authored event',3,4)
  graph['pages'][0].update(trigger='touch',commands=[{'type':'show_dialogue','speaker':None,'text':'GUI export'}])
  document={'definitions':[],'event_graphs':[graph]}
  frozen=build_snapshot(session,document)
  document['event_graphs'][0]['pages'][0]['commands'][0]['text']='later edit'
  self.assertEqual(frozen.content_database['event_graphs'][0]['pages'][0]['commands'][0]['text'],'GUI export')
  with patch('area_map.grid',return_value=(8,8,[{'values':[0,0,0,1]}]*64)):
   exported=prepare_native_event_export(frozen)
  self.assertEqual(len(inspect_map(exported.data,2)['events']),2)
  self.assertEqual(bytes(session.data),bytes(frozen.data))
  self.assertTrue(callable(frozen.layout))
 def test_compiled_source_and_extra_file_bytes_survive(self):
  from types import SimpleNamespace
  session=EditSession(fixture(),verify=False);session.export_original=b'original disc datas'
  session.extra_files={'ALUN_CD.EXE':SimpleNamespace(original=b'old',data=bytearray(b'new'))}
  frozen=build_snapshot(session);session.extra_files['ALUN_CD.EXE'].data[0]=0
  self.assertEqual(frozen.export_original,b'original disc datas')
  self.assertEqual(frozen.extra_files['ALUN_CD.EXE'].data,b'new')

if __name__=='__main__':unittest.main()
