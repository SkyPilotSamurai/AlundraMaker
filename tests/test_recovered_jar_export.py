import copy,hashlib,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_session import EditSession
from content_database import ContentDatabase
from event_graph import new_event_graph
from event_export import prepare_native_event_export,generated_event_opcodes
from mod_export import prepare_project_state_executable
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless((ROOT/'game/disc/DATA/DATAS.BIN').exists(),'Lawful inputs required')
class JarExportTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.stock=(ROOT/'game/disc/DATA/DATAS.BIN').read_bytes();cls.exe=(ROOT/'game/disc/ALUN_CD.EXE').read_bytes()
  db=ContentDatabase();db.populate_catalogue(cls.stock)
  cls.defs=[r for r in db.definitions if r['kind']=='object' and r.get('source',{}).get('catalogue_index') in (290,291)]
 def session(self,catalogue=291,commands=None):
  definition=next(r for r in self.defs if r['source']['catalogue_index']==catalogue)
  graph=new_event_graph('jar-export',163,'Jar regression',8,15,definition['id'])
  graph['pages'][0].update(trigger='activate',commands=[{'type':'change_money','amount':7}] if commands is None else commands)
  session=EditSession(self.stock);session.content_database={'definitions':copy.deepcopy(self.defs),'event_graphs':[graph]}
  return session,graph
 def test_only_E_added_native_C_F_retained_and_optional_source_verified_feature(self):
  from native_class_placement import record_cluster
  from event_vm_compatibility import verify_event_vm_abi
  s,g=self.session();before=copy.deepcopy(s.content_database);c=prepare_native_event_export(s)
  row=record_cluster(c.data,163)['entities'][-1]
  self.assertTrue(row[14]);self.assertEqual(row[10:14],bytes(4));self.assertEqual(row[15],0)
  ops=generated_event_opcodes(s,c);self.assertIn(0xE8,ops)
  manifest=prepare_project_state_executable(c,self.exe,ops)
  self.assertEqual(manifest['optional_features'],['carryable_e2'])
  verify_event_vm_abi(bytes(c.extra_files['ALUN_CD.EXE'].data),self.exe,ops,manifest)
  self.assertEqual(s.content_database,before)
 def test_passive_native_hooks_stay_empty_and_no_E8(self):
  s,g=self.session(commands=[]);g['id']='event:QA-027'
  c=prepare_native_event_export(s)
  from native_class_placement import record_cluster
  self.assertEqual(record_cluster(c.data,163)['entities'][-1][10:16],bytes(6))
  self.assertNotIn(0xE8,generated_event_opcodes(s,c))
  self.assertIsNone(prepare_project_state_executable(c,self.exe,generated_event_opcodes(s,c)))
 def test_other_class_commands_conditions_donor_and_unknown_feature_stay_guarded(self):
  s,_=self.session(290)
  with self.assertRaises(ValueError):prepare_native_event_export(s)
  for index,mutate in enumerate((lambda g:g['pages'][0].update(trigger='interact'),lambda g:g['pages'][0].update(conditions=[{'type':'switch','flag':1}]),lambda g:g.setdefault('native_placement',{}).update(donor_map_id=163,donor_entity_index=10),lambda g:g['pages'][0].update(commands=[{'type':'wait','frames':30}]))):
   with self.subTest(mutation=index):
    s,g=self.session();mutate(g)
    with self.assertRaises(ValueError):prepare_native_event_export(s)
