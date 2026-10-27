import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from content_database import ContentDatabase
from event_edit_draft import EventEditDraft
from event_graph import new_event_graph


def project():
    db = ContentDatabase()
    a, b = new_event_graph('A', 1), new_event_graph('B', 1)
    a['id'], b['id'] = 'event:a', 'event:b'
    db.document['event_graphs'] = [a, b]
    return db


class DraftMergeTests(unittest.TestCase):
    def test_other_event_changed_elsewhere_merges(self):
        db = project(); draft = EventEditDraft(db)
        draft.database.document['event_graphs'][0]['name'] = 'A edited'
        db.document['event_graphs'][1]['name'] = 'B moved on map'   # changed outside the editor
        draft.commit()
        names = [g['name'] for g in db.document['event_graphs']]
        self.assertEqual(names, ['A edited', 'B moved on map'])

    def test_same_event_changed_in_both_editor_wins(self):
        db = project(); draft = EventEditDraft(db)
        draft.database.document['event_graphs'][0]['name'] = 'A edited'
        db.document['event_graphs'][0]['name'] = 'A elsewhere'
        draft.commit()
        self.assertEqual(db.document['event_graphs'][0]['name'], 'A edited')

    def test_second_commit_after_merge_works(self):
        db = project(); draft = EventEditDraft(db)
        db.document['event_graphs'][1]['name'] = 'B elsewhere'
        draft.database.document['event_graphs'][0]['name'] = 'A1'; draft.commit()
        draft.database.document['event_graphs'][0]['name'] = 'A2'; draft.commit()
        self.assertEqual(db.document['event_graphs'][0]['name'], 'A2')


if __name__ == '__main__':
    unittest.main()
