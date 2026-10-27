import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_session import EditSession
from entity_preview import cached_preview

class EagerCacheTests(unittest.TestCase):
 def test_texture_reuse_then_edit_invalidation(self):
  session=EditSession.__new__(EditSession);session.data=bytearray(100);session.layout=lambda m:(0,(0,0,20,40,60,80,90))
  with patch('editor_session.unpack_ez',return_value=(bytes(32768),None)) as unpack:
   first=session.texture(0)[0];self.assertIs(first,session.texture(0)[0]);self.assertEqual(unpack.call_count,1)
   session.data[25]=1;session.texture(0);self.assertEqual(unpack.call_count,2);self.assertEqual(len(session._texture_cache),1)
 def test_full_preload_retains_different_map_banks(self):
  session=SimpleNamespace(data=bytearray(600),_full_asset_preload=True,layout=lambda m:(0,(0,0,0,m*40,m*40+10,m*40+30,0)))
  with patch('entity_preview.EntityPreview',side_effect=lambda *args:object()):
   for m in range(12):cached_preview(session,m)
  self.assertEqual(len(session._entity_preview_cache),12)

 def test_completed_load_is_not_repeated_when_editing(self):
  from editor_ui import Editor
  editor=Editor.__new__(Editor);editor.root=object();editor.session=SimpleNamespace(asset_preload_result={'processed':484})
  with patch('editor_ui.tk.Toplevel') as window:
   editor.schedule_asset_preload()
  window.assert_not_called()
