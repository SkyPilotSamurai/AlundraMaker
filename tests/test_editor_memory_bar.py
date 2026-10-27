"""Status bar loading bar for 'Loading game into memory' (2026-10-17)."""
import sys, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))


class MemoryBarTest(unittest.TestCase):
    def setUp(self):
        import editor_ui
        self.ui = editor_ui
        self.bar = MagicMock(); self.bar.__getitem__.side_effect = lambda k: self.mode
        self.mode = 'determinate'
        self.bar.configure.side_effect = lambda **kw: setattr(self, 'mode', kw.get('mode', self.mode))
        self.text = MagicMock()
        cls = next(c for c in vars(editor_ui).values() if isinstance(c, type) and hasattr(c, 'set_memory_bar'))
        self.ed = SimpleNamespace(memory_bar=self.bar, memory_bar_shown=False, preload_status=self.text)
        self.set = lambda *a: cls.set_memory_bar(self.ed, *a)

    def test_shows_percent_then_hides(self):
        self.set(0, 0, 'Loading game into memory')
        self.bar.pack.assert_called_once()
        self.text.set.assert_called_with('Loading game into memory 0%')
        self.set(50, 200, 'Loading game into memory')
        self.bar.configure.assert_called_with(value=25.0)
        self.text.set.assert_called_with('Loading game into memory 25%')
        self.set(None)
        self.bar.pack_forget.assert_called_once(); self.assertFalse(self.ed.memory_bar_shown)


if __name__ == '__main__':
    unittest.main()
