import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from content_database import ContentDatabase
from editor_session import EditSession
from event_graph import new_event_graph
from event_export import prepare_native_event_export,generated_event_opcodes,EventExportError
from native_class_placement import record_cluster
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'game/disc/DATA/DATAS.BIN'

@unittest.skipUnless(INPUT.exists(),'Requires local lawful stock input')
class RecoveredExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock=INPUT.read_bytes();db=ContentDatabase();db.populate_catalogue(cls.stock)
        cls.definition=next(row for row in db.definitions if row['kind']=='object' and row.get('source',{}).get('catalogue_index')==305)
        cls.floor=next(row for row in db.definitions if row['kind']=='object' and row.get('source',{}).get('catalogue_index')==301)
        cls.ice=next(row for row in db.definitions if row['kind']=='object' and row.get('source',{}).get('catalogue_index')==304)
        cls.ignition=next(row for row in db.definitions if row['kind']=='object' and row.get('source',{}).get('catalogue_index')==307)
        cls.herb=next(row for row in db.definitions if row['kind']=='item' and row.get('source',{}).get('item_id')==36)
    def session(self,commands=None,count=1):
        session=EditSession(self.stock);graphs=[]
        for i in range(count):
            graph=new_event_graph('lever:'+str(i),163,'Lever '+str(i),8+i*2,15,self.definition['id'])
            graph['pages'][0].update(trigger='activate',commands=commands or [])
            graphs.append(graph)
        session.content_database={'definitions':[copy.deepcopy(self.definition)],'event_graphs':graphs}
        return session
    def test_two_database_levers_retain_controllers_and_independent_state(self):
        session=self.session([{'type':'change_money','amount':1}],2)
        before=copy.deepcopy(session.content_database)
        exported=prepare_native_event_export(session)
        original=record_cluster(self.stock,163)['entities'];new=record_cluster(exported.data,163)['entities']
        self.assertEqual(new[:-2],original)
        for row in new[-2:]:
            self.assertEqual(row[9],2) # Actual selected tile height1, native half-tile encoding.
            self.assertTrue(row[12]&128);self.assertTrue(row[13]&128)
            self.assertEqual(row[15],0) # No fake replacement F interaction.
        reports=exported.native_event_export_report
        states=[r['recovered_object']['state_id'] for r in reports]
        requests=[r['recovered_object']['request_id'] for r in reports]
        self.assertEqual(len(set(states+requests)),4)
        self.assertIn(0xE0,generated_event_opcodes(session,exported))
        self.assertIn(0xE1,generated_event_opcodes(session,exported))
        self.assertEqual(session.content_database,before);self.assertEqual(bytes(session.data),self.stock)
    def test_passive_database_lever_also_keeps_native_behavior(self):
        session=self.session();exported=prepare_native_event_export(session)
        self.assertTrue(exported.native_event_export_report[0]['native_passive'])
        self.assertIn('recovered_object',exported.native_event_export_report[0])
    def test_unsupported_activation_actions_fail_before_game_is_written(self):
        session=self.session([{'type':'show_dialogue','text':'Not verified in this controller yet'}])
        with self.assertRaisesRegex(EventExportError,'Recovered object currently supports'):
            prepare_native_event_export(session)
    def test_database_floor_keeps_native_standing_controller_and_action(self):
        session=self.session([{'type':'change_money','amount':7}])
        session.content_database['definitions']=[copy.deepcopy(self.floor)]
        session.content_database['event_graphs'][0]['pages'][0]['class_id']=self.floor['id']
        exported=prepare_native_event_export(session)
        row=record_cluster(exported.data,163)['entities'][-1]
        self.assertTrue(row[10]&128);self.assertTrue(row[12]&128)
        self.assertEqual(row[13],0);self.assertEqual(row[15],0)
        self.assertIn(0x3F,generated_event_opcodes(session,exported))   # native 'anything standing on this'
        self.assertEqual(exported.native_event_export_report[0]['recovered_object']['catalogue'],301)
        self.assertFalse(exported.native_event_export_report[0]['recovered_object']['controller']['ignore_spring_bean'])
    def test_floor_ignore_spring_bean_option_compiles_settle_check(self):
        session=self.session([{'type':'change_money','amount':7}])
        session.content_database['definitions']=[copy.deepcopy(self.floor)]
        graph=session.content_database['event_graphs'][0]
        graph['pages'][0]['class_id']=self.floor['id'];graph['native_placement']={'ignore_spring_bean':True}
        exported=prepare_native_event_export(session)
        self.assertTrue(exported.native_event_export_report[0]['recovered_object']['controller']['ignore_spring_bean'])
        opcodes=generated_event_opcodes(session,exported)
        for opcode in (0x3E,0x3F,0x37):self.assertIn(opcode,opcodes)
    def test_ice_event_cannot_silently_replace_native_pickup(self):
        session=self.session([{'type':'change_money','amount':1}])
        session.content_database['definitions']=[copy.deepcopy(self.ice)]
        graph=session.content_database['event_graphs'][0]
        graph['pages'][0].update(class_id=self.ice['id'],trigger='interact')
        with self.assertRaisesRegex(EventExportError,'retained native controller'):
            prepare_native_event_export(session)
    def test_floor_contents_resolve_text_wait_and_native_inventory_grant(self):
        session=self.session([{'type':'show_dialogue','text':'The switch has activated.'},
            {'type':'give_item','item_class_id':self.herb['id'],'quantity':1},{'type':'change_money','amount':7}])
        session.content_database['definitions']=[copy.deepcopy(self.floor),copy.deepcopy(self.herb)]
        session.content_database['event_graphs'][0]['pages'][0]['class_id']=self.floor['id']
        exported=prepare_native_event_export(session)
        opcodes=generated_event_opcodes(session,exported)
        for opcode in (0x3F,0x0D,0x39,0x82,0x98):self.assertIn(opcode,opcodes)
        self.assertEqual(bytes(session.data),self.stock)
        self.assertEqual(record_cluster(exported.data,163)['entities'][:-1],record_cluster(self.stock,163)['entities'])
    def test_two_hit_switches_keep_native_reaction_and_isolated_latches(self):
        session=self.session([{'type':'change_money','amount':7}],2)
        session.content_database['definitions']=[copy.deepcopy(self.ignition)]
        for graph in session.content_database['event_graphs']:
            graph['pages'][0]['class_id']=self.ignition['id']
        exported=prepare_native_event_export(session)
        reports=exported.native_event_export_report
        states=[]
        for report in reports:
            recovered=report['recovered_object'];states.extend([recovered['state_id'],recovered['request_id']])
            self.assertEqual(recovered['controller']['donor_map'],58)
            self.assertEqual(set(recovered['controller']['native_flags_replaced']),{'016D','8064'})
        self.assertEqual(len(set(states)),4)
        original=record_cluster(self.stock,163)['entities'];rows=record_cluster(exported.data,163)['entities']
        self.assertEqual(rows[:-2],original)
        for row in rows[-2:]:
            self.assertTrue(row[12]&128);self.assertTrue(row[13]&128);self.assertEqual(row[15],0)
        self.assertTrue({0xBD,0xE0,0xE1}<=set(generated_event_opcodes(session,exported)))
