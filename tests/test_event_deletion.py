import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from content_database import ContentDatabase
from editor_session import EditSession,DocumentEdit
from event_deletion import delete_graph,delete_record,record_deleted


class EventDeletionTests(unittest.TestCase):
 def test_authored_delete_mixed_byte_undo_redo_and_binary_patch(self):
  session=EditSession(bytes(8),verify=False);db=ContentDatabase();row=db.new_event_graph(163,'My event',1,1)
  event_id=row['id'];before=copy.deepcopy(db.document)
  session.replace(0,b'\x01','Tile edit');delete_graph(session,db,event_id)
  self.assertEqual(db.document['event_graphs'],[]);self.assertIsInstance(session.undo_stack[-1],DocumentEdit)
  session.replace(1,b'\x02','Later tile edit');session.undo();self.assertEqual(db.document['event_graphs'],[])
  session.undo();self.assertEqual(db.document,before);self.assertEqual(session.data[:2],b'\x01\0')
  session.undo();self.assertEqual(bytes(session.data),bytes(8))
  session.redo();session.redo();session.redo();self.assertEqual(db.document['event_graphs'],[])
  self.assertEqual(session.patch()['changes'],[{'offset':0,'before':'0000','after':'0102'}])
 def test_delete_referenced_graph_rejected_and_bound_override_preserved_stock(self):
  session=EditSession(bytes(8),verify=False);db=ContentDatabase();first=db.new_event_graph(163,'Speaker')
  second=db.new_event_graph(163,'Caller');second['pages'][0]['commands']=[{'type':'show_dialogue','speaker_event_id':first['id'],'text':'Hi'}]
  with self.assertRaisesRegex(ValueError,'referenced'):delete_graph(session,db,first['id'])
  second['pages'][0]['commands']=[];first['native_binding']={'script_key':'F 1'}
  self.assertIn('original game process remains',delete_graph(session,db,first['id']))
  self.assertEqual(bytes(session.data),bytes(8))
 def test_native_delete_preserves_slots_program_bytes_and_originals(self):
  path=ROOT/'game/disc/DATA/DATAS.BIN'
  if not path.exists():self.skipTest('Private original unavailable')
  from map_inspector import inspect_map
  from mod_export import save_mod,load_mod,build_snapshot
  source=path.read_bytes();session=EditSession(source);db=ContentDatabase();rows=inspect_map(source,163)
  for kind in ('entities','events'):
   original=bytes(session.data);document=copy.deepcopy(db.document);offset=int(rows[kind][0]['offset'],16)
   delete_record(session,db,163,kind,0)
   expected=bytearray(original);expected[offset+4]=0
   self.assertEqual(session.data,expected);self.assertTrue(record_deleted(db.document,163,kind,0))
   self.assertEqual(inspect_map(session.data,163)[kind],inspect_map(expected,163)[kind])
   self.assertEqual(len(inspect_map(session.data,163)[kind]),len(rows[kind]))
   self.assertEqual(session.original,source)
   frozen=build_snapshot(session,db.to_json());self.assertTrue(record_deleted(frozen.content_database,163,kind,0))
   with tempfile.TemporaryDirectory() as folder:
    target=Path(folder)/'delete.json';save_mod(session,target,'Deletion',163)
    restored,_=load_mod(source,target)
    self.assertEqual(restored.data,expected);self.assertTrue(record_deleted(restored.content_database,163,kind,0))
   session.undo();self.assertEqual(bytes(session.data),original);self.assertEqual(db.document,document)
   session.redo();self.assertEqual(session.data,expected);session.undo()
 def test_document_undo_does_not_discard_pending_texture_pixels(self):
  from editor_ui import Editor
  editor=Editor.__new__(Editor);editor.session=EditSession(bytes(8),verify=False);db=ContentDatabase()
  row=db.new_event_graph(163);delete_graph(editor.session,db,row['id'])
  editor.current_map=163;editor.dirty=True;editor.texture_raw=bytearray(b'pending');editor.need=lambda:None
  refresh=[];editor.refresh_deleted_events=lambda:refresh.append(True);editor.status=SimpleNamespace(set=lambda s:None)
  editor.undo();self.assertTrue(editor.dirty);self.assertEqual(editor.texture_raw,b'pending');self.assertEqual(len(db.document['event_graphs']),1)
  editor.redo();self.assertTrue(editor.dirty);self.assertEqual(editor.texture_raw,b'pending');self.assertEqual(len(db.document['event_graphs']),0)
  self.assertEqual(len(refresh),2)
 def test_delete_undo_preserves_later_database_edits_and_never_reuses_id(self):
  session=EditSession(bytes(8),verify=False);db=ContentDatabase();first=db.new_event_graph(163,'Deleted')
  delete_graph(session,db,first['id']);new=db.new_event_graph(163,'Keep new')
  self.assertNotEqual(new['id'],first['id']);db.document['mod_options']={'lr_swaps':True}
  session.undo();self.assertEqual([r['name'] for r in db.document['event_graphs']],['Deleted','Keep new'])
  self.assertEqual(db.document['mod_options'],{'lr_swaps':True})
 def test_bound_process_export_does_not_reenable_deleted_actor(self):
  from unittest.mock import patch
  from event_native_compile import native_binding
  from event_export import prepare_native_event_export
  session=EditSession(bytes(80),verify=False);session.data[10:22]=bytes.fromhex('0d80000502000603000000ff');session.data[64]=1
  db=ContentDatabase();graph=db.new_event_graph(244);graph['pages'][0]['commands']=[]
  roots={'F 0':(10,22,10)};rows=[(10,13,3),(13,5,3),(16,6,3),(19,0,1),(20,0,1),(21,255,1)]
  with patch('event_native_compile.script_roots',return_value=roots),patch('event_native_compile.instructions',return_value=rows):
   graph['native_binding']=native_binding(session,244,'F 0')
   with patch('event_deletion.inspect_map',return_value={'entities':[{'offset':'0x3c'}]}):delete_record(session,db,244,'entities',0)
   exported=prepare_native_event_export(session)
   self.assertEqual(exported.data[64],0);self.assertEqual(exported.data[10],255)


if __name__=='__main__':unittest.main()
