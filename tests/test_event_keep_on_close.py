import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from content_database import ContentDatabase
from event_edit_draft import EventEditDraft
from editor_session import EditSession
from event_graph_ui import EventGraphWindow

def fake_root():
 jobs=[]
 root=SimpleNamespace(after=lambda delay,fn:(jobs.append(fn),len(jobs))[1],after_cancel=lambda job:None,
                      bind_all=lambda *a,**k:None)
 return root,jobs

class KeepOnCloseTests(unittest.TestCase):
 def window(self,db,session):
  root,jobs=fake_root()
  obj=EventGraphWindow.__new__(EventGraphWindow)
  obj.editor=SimpleNamespace(database=db,session=session,area=None,dirty=False,root=root,
                             status=MagicMock(),guard=lambda fn:fn(),_input_clock_bound=True,last_input=-100)
  obj.window=MagicMock();obj.window.state.return_value='withdrawn';obj._commit_selected=MagicMock()
  return obj,jobs

 def test_close_hides_then_keeps_event_in_project_and_undo(self):
  db=ContentDatabase();draft=EventEditDraft(db);event=draft.database.new_event_graph(1)
  event['name']='My new NPC';session=EditSession(b'',verify=False)
  obj,jobs=self.window(db,session);obj.draft=draft
  obj.close()
  obj.window.withdraw.assert_called_once();obj.window.destroy.assert_not_called()
  self.assertEqual(db.document['event_graphs'],[])      # saved passively, not yet
  self.assertTrue(obj.closing())
  jobs[-1]()                                              # the timer fires
  self.assertFalse(obj.closing())
  self.assertEqual(db.document['event_graphs'][0]['name'],'My new NPC')
  self.assertTrue(obj.editor.dirty);obj.window.destroy.assert_called_once()
  self.assertEqual(session.content_database['event_graphs'][0]['name'],'My new NPC')
  self.assertEqual(len(session.undo_stack),1)
  session.undo();self.assertEqual(db.document['event_graphs'],[])

 def test_finish_close_locks_in_immediately(self):
  db=ContentDatabase();draft=EventEditDraft(db);draft.database.new_event_graph(1)
  obj,jobs=self.window(db,EditSession(b'',verify=False));obj.draft=draft
  obj.close();obj.finish_close()
  self.assertEqual(len(db.document['event_graphs']),1);obj.window.destroy.assert_called_once()

 def test_invalid_edit_keeps_window_open(self):
  obj=EventGraphWindow.__new__(EventGraphWindow);obj.window=MagicMock()
  obj._commit_selected=MagicMock(side_effect=ValueError('Invalid edit'))
  with self.assertRaises(ValueError):obj.close()
  obj.window.withdraw.assert_not_called();obj.window.destroy.assert_not_called()

 def test_failed_lock_in_shows_window_again(self):
  obj,jobs=self.window(ContentDatabase(),None)
  obj.close_job=1;obj.keep_changes=MagicMock(side_effect=ValueError('conflict'))
  with self.assertRaises(ValueError):obj.finish_close()
  obj.window.deiconify.assert_called_once();obj.window.destroy.assert_not_called()

 def test_main_save_flushes_existing_event_window(self):
  from editor_ui import Editor
  graph=SimpleNamespace(window=SimpleNamespace(winfo_exists=lambda:True),keep_changes=MagicMock(),closing=lambda:False)
  Editor.keep_open_event_edits(SimpleNamespace(event_graph_window=graph))
  graph.keep_changes.assert_called_once()

 def test_main_save_finishes_closing_window(self):
  from editor_ui import Editor
  graph=SimpleNamespace(window=SimpleNamespace(winfo_exists=lambda:True),finish_close=MagicMock(),closing=lambda:True)
  Editor.keep_open_event_edits(SimpleNamespace(event_graph_window=graph))
  graph.finish_close.assert_called_once()

if __name__=='__main__':unittest.main()
