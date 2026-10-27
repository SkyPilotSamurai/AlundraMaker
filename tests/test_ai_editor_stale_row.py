import sys, unittest
from copy import deepcopy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from ai_editor_ui import AIEditorWindow


class _Var:
    def __init__(self, v): self.v = v
    def get(self): return self.v


class _DB:
    def __init__(self, row): self.rows = {row['id']: row}
    def get(self, i): return self.rows[i]
    def replace(self, i, row): self.rows[i] = row


class _Editor:
    def __init__(self, db):
        self.database = db; self.dirty = False; self.refreshed = None
        self.status = _Var(''); self.status.set = lambda s: None
    def db_refresh(self, i): self.refreshed = i


class AIEditorStaleRowTest(unittest.TestCase):
    def test_close_writes_into_row_replaced_by_autosave(self):
        row = {'id': 'enemy:0072', 'name': 'Red Reaper', 'kind': 'enemy', 'data': {}}
        db = _DB(row); editor = _Editor(db)
        win = AIEditorWindow.__new__(AIEditorWindow)
        win.editor = editor; win.row = row
        win.vars = {'ai_movement': _Var('dart')}
        win.window = type('W', (), {'destroy': lambda self: None})()
        db.replace(row['id'], deepcopy(row))  # Database autosave (db_apply)
        win.close()
        self.assertEqual(db.get('enemy:0072')['data']['ai_movement'], 'dart')
        self.assertTrue(editor.dirty)


if __name__ == '__main__':
    unittest.main()
