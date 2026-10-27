import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from entity_preview import cached_preview

class PreviewCacheTests(unittest.TestCase):
 def test_reuse_and_invalidate_only_asset_changes(self):
  session=SimpleNamespace(data=bytearray(200),layout=lambda m:(0,(0,0,0,20,60,100,0)))
  with patch('entity_preview.EntityPreview',side_effect=lambda *args:object()) as make:
   first=cached_preview(session,0);self.assertIs(first,cached_preview(session,0));self.assertEqual(make.call_count,1)
   session.data[5]=1;self.assertIs(first,cached_preview(session,0))
   session.data[65]=1;self.assertIsNot(first,cached_preview(session,0));self.assertEqual(make.call_count,2)
 def test_cache_is_bounded(self):
  session=SimpleNamespace(data=bytearray(200),layout=lambda m:(0,(0,0,0,20,60,100,0)))
  with patch('entity_preview.EntityPreview',side_effect=lambda *args:object()):
   for i in range(12):session.data[65]=i;cached_preview(session,0)
  self.assertEqual(len(session._entity_preview_cache),1)

 def test_thumbnail_reuse_and_asset_edit_invalidation(self):
  from database_catalogue import reference_image
  session=SimpleNamespace(data=bytearray(200),layout=lambda m:(0,(0,0,0,20,60,100,0)))
  row={'kind':'npc','name':'NPC','source':{'catalogue_index':268,'observed_maps':[0]},'data':{}}
  with patch('database_catalogue._reference_image_uncached',side_effect=lambda *args:object()) as decode:
   first=reference_image(session,row);self.assertIs(first,reference_image(session,row));self.assertEqual(decode.call_count,1)
   session.data[65]=1;self.assertIsNot(first,reference_image(session,row));self.assertEqual(decode.call_count,2)
 def test_eager_loading_finishes_all_maps_and_classes(self):
  from editor_asset_preload import preload_editor_assets
  session=SimpleNamespace(texture=lambda m:None);database=SimpleNamespace(definitions=[{'name':'A'},{'name':'B'}]);progress=[]
  with patch('editor_asset_preload.cached_preview',side_effect=ValueError('Missing sprite')),patch('editor_asset_preload.script_roots',return_value={}),patch('editor_asset_preload.entries',return_value=[]),patch('editor_asset_preload.reference_image',return_value=None) as image,patch('editor_asset_preload.portrait_image',return_value=None),patch('bush_catalogue.cached_bush_styles',return_value=[]),patch('bush_catalogue.column_catalogue',return_value=None),patch('bush_catalogue.floor_catalogue',return_value=None):
   result=preload_editor_assets(session,database,lambda d,t,l:progress.append((d,t)))
  self.assertEqual(image.call_count,2);self.assertEqual(result['processed'],3+483*4+2*2)
  self.assertEqual(progress[-1],(1939,1939));self.assertTrue(session._full_asset_preload)
  self.assertEqual(len(result['errors']),484)
 def test_preload_runs_in_the_background_without_a_window(self):
  from editor_ui import Editor
  editor=Editor.__new__(Editor);editor.root=object();editor.session=object();editor.database=object()
  editor.poll_background_preload=lambda:None
  started=[]
  class Job:
   def __init__(self,ed,session,database):self.session=session;self.stopped=False;self.finished=True
   def start(self):started.append(self);return self
  with patch('editor_background_preload.BackgroundPreload',Job),patch('editor_memory_loading.run_memory_load') as window:
   editor.root=SimpleNamespace(bind_all=lambda *a,**k:None)
   editor.schedule_asset_preload();editor.schedule_asset_preload()
  window.assert_not_called();self.assertEqual(len(started),1)   # background, no window, started once
