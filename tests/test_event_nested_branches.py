import sys, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
for m in ['tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog', 'PIL.ImageTk', 'zoom_canvas']:
    sys.modules.setdefault(m, MagicMock())
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import event_graph_ui


class Tree:
    def __init__(self):self.rows = [];self.selected = ()
    def delete(self, *a):self.rows = []
    def get_children(self):return ()
    def insert(self, parent, where, iid, values):self.rows.append((iid, values))
    def exists(self, iid):return any(r[0] == iid for r in self.rows)
    def selection(self):return self.selected
    def selection_set(self, iid):self.selected = (iid,)
    def see(self, iid):pass


def window(commands):
    page = {'commands': commands}
    w = SimpleNamespace(commands=Tree(), db=SimpleNamespace(definitions=[]), schedule_apply=lambda: None,
                        current_page=lambda: page, load_command=lambda: None, _commit_command=lambda: None, command_index=None)
    for name in ('refresh_commands', '_locate', 'selected_command_location', 'move_command'):
        setattr(w, name, getattr(event_graph_ui.EventGraphWindow, name).__get__(w))
    return w, page


class NestedBranchTests(unittest.TestCase):
    def test_rows_at_any_depth(self):
        inner = {'type': 'ask_question', 'text': 'Q', 'then': [{'type': 'wait', 'frames': 1}], 'else': []}
        w, page = window([{'type': 'if', 'condition': {'type': 'random', 'percent': 50}, 'then': [inner], 'else': []}])
        w.refresh_commands()
        ids = [r[0] for r in w.commands.rows]
        for iid in ('0', '0:then:0', '0:then:0:then:0', '0:then:0:then:add', '0:then:0:else:add', '0:else:add', 'new'):
            self.assertIn(iid, ids)
        container, index = w._locate('0:then:0:then:0')
        self.assertIs(container, inner['then']);self.assertEqual(index, 0)
        container, index = w._locate('0:then:0:else:add')
        self.assertIs(container, inner['else']);self.assertIsNone(index)

    def test_move_inside_nested_branch(self):
        a, b = {'type': 'wait', 'frames': 1}, {'type': 'wait', 'frames': 2}
        inner = {'type': 'ask_question', 'text': 'Q', 'then': [a, b], 'else': []}
        w, page = window([{'type': 'if', 'condition': {'type': 'random', 'percent': 50}, 'then': [inner], 'else': []}])
        w.refresh_commands();w.commands.selection_set('0:then:0:then:0')
        w.move_command(1)
        self.assertEqual(inner['then'], [b, a]);self.assertEqual(w.commands.selection(), ('0:then:0:then:1',))


if __name__ == '__main__':
    unittest.main()
