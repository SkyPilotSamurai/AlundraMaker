import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from content_database import ContentDatabase
from event_edit_draft import EventEditDraft
from project_state_registry import ProjectStateRegistry
from editor_session import EditSession


class EventDraftTests(unittest.TestCase):
    def test_cancel_changes_neither_global_event_nor_switch(self):
        db=ContentDatabase();before=db.to_json();draft=EventEditDraft(db)
        registry=ProjectStateRegistry(draft.database.document)
        self.assertEqual(registry.create_auto('switches')['id'],1)
        self.assertEqual(registry.create_auto('switches')['id'],2)
        draft.database.new_event_graph(1)
        self.assertEqual(db.to_json(),before)

    def test_apply_publishes_only_referenced_new_state_and_event_atomically(self):
        db=ContentDatabase();before=db.to_json();draft=EventEditDraft(db)
        state=ProjectStateRegistry(draft.database.document)
        state.create_auto('switches');state.create_auto('switches')
        graph=draft.database.new_event_graph(1)
        graph['pages'][0]['commands']=[{'type':'set_switch','switch_scope':'project','switch_id':1,'value':True}]
        session=EditSession(b'',verify=False);draft.commit(session)
        self.assertEqual([r['id'] for r in ProjectStateRegistry(db.document).options('switches')],[1])
        self.assertEqual(len(db.document['event_graphs']),1)
        session.undo();self.assertEqual(db.to_json(),before)
        session.redo();self.assertEqual(len(db.document['event_graphs']),1)

    def test_gate_binding_keeps_only_confirmed_project_switch(self):
        db=ContentDatabase();draft=EventEditDraft(db)
        registry=ProjectStateRegistry(draft.database.document)
        registry.create_auto('switches');registry.create_auto('switches')
        graph=draft.database.new_event_graph(1)
        graph['native_placement']={'open_switch_id':2}
        draft.commit()
        self.assertEqual([r['id'] for r in ProjectStateRegistry(db.document).options('switches')],[2])
        with self.assertRaisesRegex(ValueError,'referenced'):ProjectStateRegistry(db.document).delete('switches',2)

    def test_gate_binding_rejects_bool_or_missing_switch_atomically(self):
        for identity in (True,99):
            db=ContentDatabase();before=db.to_json();draft=EventEditDraft(db)
            ProjectStateRegistry(draft.database.document).create_auto('switches')
            graph=draft.database.new_event_graph(1);graph['native_placement']={'open_switch_id':identity}
            with self.assertRaises(ValueError):draft.commit()
            self.assertEqual(db.to_json(),before)

    def test_existing_game_switch_discards_provisional_new_switch(self):
        db=ContentDatabase();draft=EventEditDraft(db)
        ProjectStateRegistry(draft.database.document).create_auto('switches')
        graph=draft.database.new_event_graph(1)
        graph['pages'][0]['commands']=[{'type':'set_switch','switch_id':32,'native_flag_operand':32,'value':True}]
        draft.commit()
        self.assertEqual(ProjectStateRegistry(db.document).options('switches'),[])
        self.assertNotIn('switch_scope',db.document['event_graphs'][0]['pages'][0]['commands'][0])

    def test_validation_failure_does_not_publish_switch_or_graph(self):
        db=ContentDatabase();before=db.to_json();draft=EventEditDraft(db)
        state=ProjectStateRegistry(draft.database.document);state.create_auto('switches')
        graph=draft.database.new_event_graph(1)
        graph['pages'][0]['commands']=[{'type':'set_switch','switch_scope':'project','switch_id':99,'value':True}]
        with self.assertRaises(ValueError):draft.commit()
        self.assertEqual(db.to_json(),before)

    def test_concurrent_registry_changes_kept_without_overwrite(self):
        # 2026-10-23: changes made elsewhere are merged, never overwritten or refused
        db=ContentDatabase();draft=EventEditDraft(db)
        ProjectStateRegistry(db.document).create_auto('switches')
        draft.commit()
        self.assertEqual(ProjectStateRegistry(db.document).get('switches',1)['name'],'Switch1')

    def test_existing_switch_rename_is_provisional_and_confirmable(self):
        db=ContentDatabase();ProjectStateRegistry(db.document).create_auto('switches')
        draft=EventEditDraft(db);ProjectStateRegistry(draft.database.document).update('switches',1,name='Door open')
        self.assertEqual(ProjectStateRegistry(db.document).get('switches',1)['name'],'Switch1')
        draft.commit();self.assertEqual(ProjectStateRegistry(db.document).get('switches',1)['name'],'Door open')

    def test_delete_is_provisional_then_undoable_and_ids_stay_reserved(self):
        db=ContentDatabase();graph=db.new_event_graph(1);draft=EventEditDraft(db)
        draft.delete_event(graph['id'])
        self.assertEqual(len(db.document['event_graphs']),1)
        session=EditSession(b'',verify=False);draft.commit(session)
        self.assertEqual(db.document['event_graphs'],[])
        self.assertIn(graph['id'],db.document['deleted_event_ids'])
        session.undo();self.assertEqual(len(db.document['event_graphs']),1)

if __name__=='__main__':unittest.main()
