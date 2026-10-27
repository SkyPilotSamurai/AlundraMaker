import copy,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from content_database import ContentDatabase
from editor_session import EditSession
from event_graph import new_event_graph
from event_export import prepare_native_event_export,EventExportError
from native_class_placement import record_cluster
from event_editor import script_roots
INPUT=Path(__file__).resolve().parents[1]/'game/disc/DATA/DATAS.BIN'

@unittest.skipUnless(INPUT.exists(),'Requires local lawful stock input')
class RouteExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock=INPUT.read_bytes();db=ContentDatabase();db.populate_catalogue(cls.stock)
        cls.jess=next(x for x in db.definitions if x['kind']=='npc' and x.get('source',{}).get('catalogue_index')==260)
        cls.npcs={x['source']['catalogue_index']:x for x in db.definitions if x['kind']=='npc' and x.get('source',{}).get('catalogue_index') in (256,265,268,289)}
        cls.chest=next(x for x in db.definitions if x['kind']=='object' and x.get('source',{}).get('catalogue_index')==30)
        cls.herb=next(x for x in db.definitions if x['kind']=='item' and x.get('source',{}).get('item_id')==36)

    def session(self):
        s=EditSession(self.stock);g=new_event_graph('route:1',163,'Route',8,15,self.jess['id'])
        g['pages'][0]['commands']=[dict(type='move_actor',target='this_event',mode='route',route=['up','down'],moving_animation=1,idle_animation=0,movement_speed=100,blocked_behavior='wait')]
        s.content_database={'definitions':[copy.deepcopy(self.jess)],'event_graphs':[g]};return s,g

    def test_retained_actor_bytes_match_cold_boot_profile(self):
        s,g=self.session();before=copy.deepcopy(s.content_database);e=prepare_native_event_export(s)
        roots=script_roots(e,163);row=record_cluster(e.data,163)['entities'][-1]
        key='F '+str(row[15]&127)
        off=roots[key][0]
        self.assertEqual(bytes(e.data[off:off+22]),bytes.fromhex('6604000009101a011e100009001a011e10001a0000ff'))
        self.assertEqual(row[10:12],bytes(2));self.assertTrue(row[12]&128)
        self.assertEqual(row[13:15],bytes(2));self.assertEqual(s.content_database,before)
        self.assertEqual(bytes(s.data),self.stock)

    def test_custom_speed_and_skipping_fall_back_without_blocking_export(self):
        for field,value in [('movement_speed',200),('blocked_behavior','skip')]:
            s,g=self.session();g['pages'][0]['commands'][0][field]=value
            e=prepare_native_event_export(s,best_effort=True)
            self.assertTrue(e.native_event_export_skipped)
            self.assertTrue(e.native_event_export_report)

    def test_conditional_dialogue_and_other_actor_controllers_fall_back(self):
        for change in ('condition','dialogue','class'):
            s,g=self.session()
            if change=='condition':g['pages'][0]['conditions']=[{'type':'switch','switch_id':1,'native_flag_operand':1,'value':True}]
            elif change=='dialogue':
                other=copy.deepcopy(self.npcs[265]);g['pages'][0]['class_id']=other['id'];s.content_database['definitions']=[other]
                g['pages'][0]['commands'].append({'type':'show_dialogue','text':'Requires further ordered walking verification'})
            else:s.content_database['definitions'][0]['source']['catalogue_index']=378
            e=prepare_native_event_export(s,best_effort=True)
            self.assertTrue(e.native_event_export_skipped)
            self.assertTrue(e.native_event_export_report)

    def test_unsupported_default_route_falls_back_and_is_reported(self):
        s,g=self.session();g['pages'][0]['default_move_route']={'route':['up']}
        e=prepare_native_event_export(s,best_effort=True)
        self.assertEqual(e.native_event_export_skipped[0]['omitted_settings'],['default movement route'])
        self.assertTrue(e.native_event_export_report)

    def test_default_route_matches_proven_continuous_controller(self):
        for catalogue in (260, 256):
            s,g=self.session()
            definition=self.jess if catalogue==260 else self.npcs[256]
            s.content_database['definitions']=[copy.deepcopy(definition)]
            g['pages'][0]['class_id']=definition['id']
            route=g['pages'][0]['commands'][0].copy()
            route.update(route=['right','left'],repeat=True)
            g['pages'][0].update(commands=[],default_move_route=route)
            before=record_cluster(s.data,163)['entities']
            e=prepare_native_event_export(s);rows=record_cluster(e.data,163)['entities']
            self.assertEqual(rows[:-1],before)
            row=rows[-1];roots=script_roots(e,163)
            off=roots['C '+str(row[12]&127)][0]
            self.assertEqual(bytes(e.data[off:off+18]),bytes.fromhex('09181a011e180009081a011e180002f2ffff'))
            self.assertEqual(e.data[roots['F '+str(row[15]&127)][0]],255)
            self.assertFalse(e.native_event_export_report[0]['gameplay_verified'])
            self.assertEqual(bytes(s.data),self.stock)

    def test_unproven_default_route_variations_are_attempted_with_fallback(self):
        for field,value in [('repeat',False),('route',['up','down']),('movement_speed',200),('blocked_behavior','skip')]:
            s,g=self.session();route=g['pages'][0]['commands'].pop()
            route.update(route=['right','left'],repeat=True);route[field]=value
            g['pages'][0]['default_move_route']=route
            e=prepare_native_event_export(s,best_effort=True)
            self.assertTrue(e.native_event_export_skipped)
            self.assertTrue(e.native_event_export_report)

    def test_default_dialogue_routes_get_independent_snapshot_slots_and_optional_executable(self):
        from mod_export import prepare_project_state_executable
        from project_state_runtime import verify_private_state_injection
        s,g=self.session();route=g['pages'][0]['commands'][0].copy();route.update(route=['right','left'],repeat=True)
        g['pages'][0].update(default_move_route=route,commands=[{'type':'show_dialogue','text':'One coin after text.','auto_wrap':False},{'type':'change_money','amount':1}])
        other=copy.deepcopy(g);other['id']='route:2';other['region']=[11,15,1,1];other['pages'][0]['class_id']=self.npcs[256]['id']
        s.content_database['definitions'].append(copy.deepcopy(self.npcs[256]));s.content_database['event_graphs'].append(other)
        e=prepare_native_event_export(s)
        self.assertEqual(e.actor_route_resume_slots,2)
        self.assertEqual([r['native_default_route']['snapshot_slot'] for r in e.native_event_export_report],[0,1])
        ops=sorted({op for r in e.native_event_export_report for op in r['opcodes']})
        self.assertIn(0xE6,ops);self.assertIn(0xE7,ops)
        stockexe=(INPUT.parents[1]/'ALUN_CD.EXE').read_bytes()
        manifest=prepare_project_state_executable(e,stockexe,ops)
        self.assertEqual(manifest['optional_features'],['actor_route_resume'])
        self.assertEqual(manifest['route_resume']['storage_size'],160)
        verify_private_state_injection(e.extra_files['ALUN_CD.EXE'].data,manifest)
        self.assertNotIn('project_state',s.content_database)

    def test_other_default_route_contents_and_speakers_are_attempted(self):
        for commands in ([{'type':'change_money','amount':1}],
                         [{'type':'show_dialogue','text':'X','speaker':'player'},{'type':'change_money','amount':1}]):
            s,g=self.session();route=g['pages'][0]['commands'][0].copy();route.update(route=['right','left'],repeat=True)
            g['pages'][0].update(default_move_route=route,commands=commands)
            e=prepare_native_event_export(s,best_effort=True)
            self.assertTrue(e.native_event_export_report)

    def test_only_new_dog_route_adds_self_collision_load(self):
        s,g=self.session();dog=copy.deepcopy(self.npcs[289])
        g['pages'][0]['class_id']=dog['id'];s.content_database['definitions']=[dog]
        before=record_cluster(s.data,163)['entities'];e=prepare_native_event_export(s)
        after=record_cluster(e.data,163)['entities'];self.assertEqual(after[:-1],before)
        row=after[-1];roots=script_roots(e,163);off=roots['A '+str(row[10]&127)][0]
        self.assertEqual(bytes(e.data[off:off+5]),bytes.fromhex('62808000ff'))
        self.assertIn(0x62,e.native_event_export_report[0]['opcodes'])
        self.assertEqual(bytes(s.data),self.stock)

    def test_jess_dialogues_bracket_route_and_each_waits(self):
        s,g=self.session();route=g['pages'][0]['commands'][0]
        g['pages'][0]['commands']=[{'type':'show_dialogue','text':'Route first. Wait for my walk.','auto_wrap':False},route,{'type':'show_dialogue','text':'Route second. My walk is done.','auto_wrap':False},{'type':'change_money','amount':1}]
        e=prepare_native_event_export(s);row=record_cluster(e.data,163)['entities'][-1];off=script_roots(e,163)['F '+str(row[15]&127)][0]
        raw=bytes(e.data[off:off+33])
        self.assertEqual(raw[:5],bytes.fromhex('660400000d'))
        self.assertEqual(raw[6:8],bytes.fromhex('0039'))
        self.assertEqual(raw[8:26],bytes.fromhex('09101a011e100009001a011e10001a00000d'))
        self.assertEqual(raw[-6:],bytes.fromhex('0039980100ff'))

    def test_jess_private_state_commands_share_retained_route_context(self):
        from project_state_registry import ProjectStateRegistry
        s,g=self.session();registry=ProjectStateRegistry(s.content_database)
        switch=registry.create('switches','Running')['id'];variable=registry.create('variables','Counter')['id']
        g['pages'][0]['commands']=[{'type':'set_switch','switch_scope':'project','switch_id':switch,'value':True},g['pages'][0]['commands'][0],{'type':'set_variable','variable_scope':'project','variable_id':variable,'operation':'add','value':6}]
        e=prepare_native_event_export(s,best_effort=True)
        self.assertIn(0xE0,e.native_event_export_report[0]['opcodes']);self.assertIn(0xE3,e.native_event_export_report[0]['opcodes'])
        self.assertEqual(s.content_database['project_state']['variables'][0]['initial_value'],0)

    def test_route_native_switch_commands_do_not_block_other_export(self):
        s,g=self.session();g['pages'][0]['commands'].append({'type':'set_switch','switch_scope':'native','switch_id':1,'value':True})
        e=prepare_native_event_export(s,best_effort=True)
        self.assertTrue(e.native_event_export_report)
        self.assertTrue(e.native_event_export_skipped)

    def test_chest_route_moves_instance_and_keeps_its_chest_item_and_animation(self):
        s,g=self.session();g['pages'][0].update(class_id=self.chest['id'],commands=[],conditions=[],
            contained_item_class_id=self.herb['id'],trigger_actions=[{'trigger':'interact','commands':[],
            'hit_sources':[],'destroy_after':False}],default_move_route={'type':'move_actor','target':'this_event',
            'mode':'route','route':['left','right'],'repeat':True,'movement_speed':100,'blocked_behavior':'wait'})
        g['class_id']=self.chest['id'];s.content_database={'definitions':[copy.deepcopy(self.chest),copy.deepcopy(self.herb)],'event_graphs':[g]}
        exported=prepare_native_event_export(s,best_effort=True)
        self.assertEqual(len(exported.native_event_export_report),1)
        self.assertTrue(exported.native_event_export_report[0]['native_chest'])
        self.assertFalse(exported.native_event_export_skipped)
        row=record_cluster(exported.data,163)['entities'][-1]
        self.assertEqual(struct.unpack_from('<H',row,18)[0],36)
        roots=script_roots(exported,163);off=roots['C '+str(row[12]&127)][0]
        # Opcode65 applies one-pixel offsets to this chest instance, followed
        # by a one-tick wait. No 1A animation command is generated.
        self.assertEqual(bytes(exported.data[off:off+10]),bytes.fromhex('6580ffff000000003700'))
        route_bytes=bytes(exported.data[off:off+485])
        self.assertEqual(route_bytes.count(bytes.fromhex('6580')),48)
        self.assertNotIn(0x1A,route_bytes)
        self.assertTrue(exported.native_event_export_report[0]['native_default_route']['appearance_animation_preserved'])
        self.assertEqual(g['pages'][0]['default_move_route']['route'],['left','right'])
        self.assertEqual(bytes(s.data),self.stock)
