import sys,unittest,hashlib
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_ui import Editor

class DatabaseRefreshTests(unittest.TestCase):
 def test_current_input_refreshes_names_and_preview_links_without_rescanning_unchanged_source(self):
  editor=Editor.__new__(Editor);calls=[]
  editor.database=SimpleNamespace(document={},scan_all_map_sprites=lambda d:calls.append(('source',d)),scan_instances=lambda d,**kw:calls.append(('instances',d)),populate_catalogue=lambda d=None:calls.append(('names',d)))
  editor.session=SimpleNamespace(original=b'base',data=bytearray(b'base'),source_verified=False,path=None)
  editor.populate_database_from_game();self.assertEqual(len(calls),3)
  editor.populate_database_from_game();self.assertEqual(len(calls),3)
  editor.session.data[0]=ord('B');editor.populate_database_from_game()
  self.assertEqual([kind for kind,data in calls],['source','instances','names','instances','names'])
  self.assertEqual(calls[-1][1],b'Base')
  self.assertEqual(editor.database.document['named_catalogue_build'],hashlib.sha256(b'Base').hexdigest())
 def test_stat_changes_in_balance_do_not_reindex_maps(self):
  editor=Editor.__new__(Editor);calls=[]
  editor.database=SimpleNamespace(document={},scan_all_map_sprites=lambda d:calls.append('source'),scan_instances=lambda d,**kw:calls.append('instances'),populate_catalogue=lambda d=None:calls.append('names'),import_balance_table=lambda *a,**k:None)
  editor.session=SimpleNamespace(original=b'base',data=bytearray(b'base'),source_verified=False,path=None,extra_files={})
  editor.populate_database_from_game();n=len(calls)
  editor.session.extra_files['DATA/BALANCE.BIN']=SimpleNamespace(data=bytearray(b'stats'))   # written by the database
  editor.populate_database_from_game();self.assertEqual(len(calls),n)
 def test_no_session_still_seeds_catalogue(self):
  editor=Editor.__new__(Editor);calls=[];editor.session=None
  editor.database=SimpleNamespace(populate_catalogue=lambda:calls.append(True))
  editor.populate_database_from_game();self.assertEqual(calls,[True])
