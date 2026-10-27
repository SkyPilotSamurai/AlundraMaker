import sys,unittest,struct
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from event_graph import new_event_graph,validate_event_graph
from new_event_compile import compile_new_events
from editor_session import EditSession
from content_database import ContentDatabase
from native_class_placement import record_cluster
from native_enemy_death import TESTED_DEATH_CALLBACKS
from mod_export import prepare_project_state_executable
from event_vm_compatibility import verify_event_vm_abi

class ProductionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  p=ROOT/'game/disc/DATA/DATAS.BIN';e=ROOT/'game/disc/ALUN_CD.EXE'
  if not p.exists()or not e.exists():raise unittest.SkipTest('Private stock input unavailable')
  cls.stock=p.read_bytes();cls.exe=e.read_bytes();db=ContentDatabase();db.populate_catalogue(cls.stock);cls.definitions=db.definitions
 def event(self,catalogue=335,commands=None):
  d=next(d for d in self.definitions if d['kind']=='enemy' and d.get('source',{}).get('catalogue_index')==catalogue)
  g=new_event_graph('test:death',163,'Puku Death',8,15,d['id']);g['pages'][0].update(trigger='death',commands=commands if commands is not None else[{'type':'change_money','amount':7}]);validate_event_graph(g)
  s=EditSession(self.stock);s.content_database={'definitions':self.definitions,'event_graphs':[g]};return s,g
 def test_native_AI_and_default_drop_record_retained(self):
  s,g=self.event();c=compile_new_events(s,[g]);r=record_cluster(c.data,163)['entities'][-1]
  self.assertEqual(r[10:14],bytes(4));self.assertTrue(r[14]&128);self.assertEqual(r[15],0);self.assertEqual(r[18:20],bytes(2))
  self.assertEqual(c.native_event_export_report[0]['bank'],'E')
  self.assertIn(0xe5,c.native_event_export_report[0]['opcodes'])
 def test_production_export_installs_optional_exact_handler(self):
  s,g=self.event();c=compile_new_events(s,[g]);ops=c.native_event_export_report[0]['opcodes'];m=prepare_project_state_executable(c,self.exe,ops)
  self.assertEqual(m['optional_features'],['enemy_hp_zero'])
  self.assertTrue(verify_event_vm_abi(bytes(c.extra_files['ALUN_CD.EXE'].data),self.exe,ops,private_state_manifest=m)['relevant_handler_signatures_compatible'])
 def test_each_tested_profile_retains_its_distinct_native_callbacks(self):
  for catalogue,callbacks in TESTED_DEATH_CALLBACKS.items():
   with self.subTest(catalogue=catalogue):
    s,g=self.event(catalogue);c=compile_new_events(s,[g]);r=c.native_event_export_report[0]
    self.assertEqual(r['sprite_callbacks'],callbacks)
    self.assertEqual(r['native_enemy_death']['catalogue_index'],catalogue)
    self.assertTrue(r['native_enemy_death']['native_AI_retained'])
    self.assertEqual(record_cluster(c.data,163)['entities'][-1][10:14],bytes(4))
 def test_changed_native_profile_is_guarded(self):
  s,g=self.event(329)
  altered=[('A',1),('C',1),('D',1),('E',2),('F',0)]   # not the standard death routine
  with patch('event_vm_compatibility.sprite_callbacks',return_value=altered):
   with self.assertRaisesRegex(ValueError,"standard death routine"):
    compile_new_events(s,[g])
 def test_production_clear_is_before_runtime_root_handoff(self):
  from project_state_registry import ProjectStateRegistry
  from project_state_runtime import compile_project_command
  s,g=self.event();c=compile_new_events(s,[g]);r=c.native_event_export_report[0];profile=r['native_enemy_death']
  self.assertTrue(profile['clear_latch_before_native_handoff']);self.assertEqual(profile['continuation_lifetime'],'native actor lifetime')
  base,h=c.layout(163);section=base+h[3];header=struct.unpack_from('<12I',c.data,section)
  root=struct.unpack_from('<h',c.data,section+header[10]+r['root_index']*2)[0]
  code=bytes(c.data[section+header[6]+root:section+header[6]+root+r['code_bytes']])
  reg=ProjectStateRegistry(c.content_database)
  clear=compile_project_command({'type':'set_switch','switch_scope':'project','switch_id':profile['private_latch_id'],'value':False},reg)
  self.assertTrue(code.endswith(clear+bytes((0x40,4,0,0xff))))
 def test_passive_enemy_remains_native_without_optional_injection(self):
  s,g=self.event(commands=[]);c=compile_new_events(s,[g]);self.assertNotIn(0xe5,c.native_event_export_report[0]['opcodes'])
  self.assertIsNone(prepare_project_state_executable(c,self.exe,c.native_event_export_report[0]['opcodes']))
  self.assertEqual(record_cluster(c.data,163)['entities'][-1][10:16],bytes(6))
 def test_other_enemies_and_unverified_continuations_guarded(self):
  # death actions: anything the event system can do except actor movement / map changes
  s,g=self.event();g['pages'][0]['commands']=[{'type':'warp_player','map_id':1,'x':1,'y':1,'z':0}]
  with self.assertRaisesRegex(ValueError,'cannot include warp_player'):compile_new_events(s,[g])
  s,g=self.event();g['pages'].append(dict(g['pages'][0],id='page:2'))
  with self.assertRaisesRegex(ValueError,'one event page'):compile_new_events(s,[g])

if __name__=='__main__':unittest.main()
