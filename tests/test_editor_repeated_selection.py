import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))

class RepeatedSelectionTests(unittest.TestCase):
 def test_native_double_click_does_not_rebuild_selected_form(self):
  from event_process_ui import EventProcess
  form=MagicMock()
  obj=SimpleNamespace(tree=SimpleNamespace(selection=lambda:('123',)),form=form,_selected_command='123')
  EventProcess.load_command(obj)
  form.winfo_children.assert_not_called()

 def test_authored_queued_selection_does_not_reset_working_edits(self):
  from event_graph_ui import EventGraphWindow
  draft={'id':'event:1','name':'Unsaved edit'}
  obj=SimpleNamespace(events=SimpleNamespace(selection=lambda:('event:1',)),working=draft)
  EventGraphWindow.load_selected(obj)
  self.assertEqual(obj.working['name'],'Unsaved edit')

 def test_relation_cache_tracks_new_and_reassigned_definitions(self):
  from content_database import ContentDatabase
  from placement_catalogue import placement_info
  db=ContentDatabase();parent=db.new('enemy','Slime');parent['source']={'catalogue_index':329}
  part=db.new('enemy','Part');part['source']={'catalogue_index':330}
  self.assertEqual(placement_info(part,db)['primary_class_id'],parent['id'])
  parent['source']['catalogue_index']=410
  self.assertIsNone(placement_info(part,db)['primary_class_id'])
  replacement=db.new('enemy','New Slime');replacement['source']={'catalogue_index':329}
  self.assertEqual(placement_info(part,db)['primary_class_id'],replacement['id'])
