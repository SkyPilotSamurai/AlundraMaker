import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from content_database import ContentDatabase
from editor_session import EditSession
from event_graph import new_event_graph
from event_export import prepare_native_event_export,generated_event_opcodes
from native_class_placement import record_cluster
from mod_export import prepare_project_state_executable
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless((ROOT/'game/disc/DATA/DATAS.BIN').exists(),'Lawful retail inputs required')
class BookInteractionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.stock=(ROOT/'game/disc/DATA/DATAS.BIN').read_bytes();cls.exe=(ROOT/'game/disc/ALUN_CD.EXE').read_bytes()
  db=ContentDatabase();db.populate_catalogue(cls.stock)
  cls.definition=next(d for d in db.definitions if d['kind']=='object' and d.get('source',{}).get('catalogue_index')==303)
 def fixture(self,commands=None):
  g=new_event_graph('book-test',163,'Book',8,15,self.definition['id'])
  g['pages'][0].update(trigger='interact',commands=[{'type':'show_dialogue','text':'Read this book.'},{'type':'change_money','amount':7}] if commands is None else commands)
  s=EditSession(self.stock);s.content_database={'definitions':[copy.deepcopy(self.definition)],'event_graphs':[g]}
  return s,g
 def test_retained_native_wait_and_no_optional_executable_extension(self):
  s,g=self.fixture();before=copy.deepcopy(s.content_database);c=prepare_native_event_export(s)
  row=record_cluster(c.data,163)['entities'][-1]
  self.assertTrue(row[10]);self.assertTrue(row[12]);self.assertTrue(row[15]);self.assertEqual(row[11],0);self.assertEqual(row[13:15],bytes(2))
  opcodes=generated_event_opcodes(s,c);self.assertTrue({0x62,0x66,0x39,0x98}.issubset(opcodes))
  self.assertIsNone(prepare_project_state_executable(c,self.exe,opcodes))
  self.assertEqual(s.content_database,before)
 def test_passive_book_hooks_and_original_source_remain_unchanged(self):
  s,g=self.fixture([]);c=prepare_native_event_export(s)
  self.assertEqual(record_cluster(c.data,163)['entities'][-1][10:16],bytes(6))
  self.assertEqual(record_cluster(c.data,136)['entities'][8],record_cluster(self.stock,136)['entities'][8])
 def test_unsupported_behavior_conditions_donor_and_speakers_stay_guarded(self):
  mutations=[lambda g:g['pages'][0].update(trigger='activate'),lambda g:g['pages'][0].update(conditions=[{'type':'switch','flag':1}]),
   lambda g:g['pages'][0]['commands'].append({'type':'wait','frames':60}),lambda g:g['pages'][0]['commands'][0].update(speaker='player'),
   lambda g:g.setdefault('native_placement',{}).update(donor_map_id=117,donor_entity_index=20)]
  for i,change in enumerate(mutations):
   with self.subTest(i=i):
    s,g=self.fixture();change(g)
    with self.assertRaises(ValueError):prepare_native_event_export(s)
 def test_changed_native_source_guard_rejects_inherited_controller(self):
  from native_book_interaction import verify_source
  from native_class_placement import append_record_cluster
  cluster=record_cluster(self.stock,136);row=bytearray(cluster['entities'][8]);row[15]=0x82;cluster['entities'][8]=bytes(row)
  changed,_=append_record_cluster(self.stock,136,entities=cluster['entities'])
  with self.assertRaises(ValueError):verify_source(changed)
