import unittest
from unittest.mock import patch
import test_new_event_compile as existing
from event_export import prepare_native_event_export, EventExportError
from native_class_placement import append_record_cluster, record_cluster

class PassivePlacementTests(unittest.TestCase):
    def setUp(self):
        existing.NewEventCompileTests.setUp(self)
    def test_empty_classless_event_has_no_native_region(self):
        self.graph['pages'][0].update(trigger='interact',commands=[])
        old=bytes(self.session.data)
        exported=prepare_native_event_export(self.session)
        self.assertEqual(bytes(exported.data),old)
        self.assertEqual(exported.native_event_export_report[0]['bank'],None)

    def test_blank_enemy_preserves_native_ai_and_donor_record(self):
        raw=bytes([0,0,7,7,1,64,4,2,2,2,1,2,3,4,5,6,0,0,0,0])
        self.session.data,_=append_record_cluster(self.session.data,2,entities=[raw])
        self.graph['pages'][0].update(trigger='interact',commands=[],class_id='enemy:test')
        self.graph['native_placement']={'donor_entity_index':0}
        self.session.content_database['definitions']=[{'id':'enemy:test','kind':'enemy','source':{'catalogue_index':4}}]
        exported=prepare_native_event_export(self.session)
        rows=record_cluster(exported.data,2)['entities']
        self.assertEqual(rows[0],raw)
        self.assertEqual(rows[1][10:16],raw[10:16])
        self.assertIsNone(exported.native_event_export_report[0]['bank'])

    def test_item_is_initially_spawned_native_pickup_without_authored_hook(self):
        self.graph['pages'][0].update(trigger='interact',commands=[],class_id='item:herb')
        self.session.content_database['definitions']=[{'id':'item:herb','kind':'item','source':{'item_id':36,'catalogue_index':66}}]
        template=bytes([0,0,7,7,1,0,66]+[0]*13)
        with patch('new_event_compile.verified_item_pickup_template',return_value=template):
            exported=prepare_native_event_export(self.session)
        row=record_cluster(exported.data,2)['entities'][-1]
        self.assertEqual(row[5],64)
        self.assertEqual(row[6],66)
        self.assertEqual(row[7:10],bytes([6,8,2]))
        self.assertEqual(row[10:],bytes(10))
        self.assertTrue(exported.native_event_export_report[0]['native_pickup'])

    def test_death_never_overwrites_deactivation_callback(self):
        self.graph['pages'][0].update(trigger='death',class_id='enemy:test')
        with self.assertRaisesRegex(EventExportError,'Death continuation'):
            prepare_native_event_export(self.session)

    def test_project_switch_variable_commands_and_branch_compile(self):
        from project_state_registry import ProjectStateRegistry
        reg=ProjectStateRegistry(self.session.content_database)
        switch=reg.create('switches','Door unlocked')
        variable=reg.create('variables','Talk count')
        self.graph['pages'][0]['commands']=[
            {'type':'set_switch','switch_scope':'project','switch_id':switch['id'],'value':True},
            {'type':'set_variable','variable_scope':'project','variable_id':variable['id'],'operation':'add','value':1},
            {'type':'if','condition':{'type':'variable','variable_scope':'project','variable_id':variable['id'],'operator':'>=','value':1},'then':[{'type':'change_money','amount':1}],'else':[]}]
        exported=prepare_native_event_export(self.session)
        ops=exported.native_event_export_report[0]['opcodes']
        self.assertTrue({0xE0,0xE3,0xE4,0x98}.issubset(ops))
        self.assertEqual(reg.get('switches',switch['id'])['initial_value'],False)

    def test_npc_selected_pose_has_native_A_process_and_preserves_stock(self):
        raw=bytes([0,0,7,7,1,64,4,2,2,2]+[0]*10)
        self.session.data,_=append_record_cluster(self.session.data,2,entities=[raw])
        self.graph['pages'][0].update(trigger='interact',commands=[],class_id='npc:test')
        self.graph['native_placement']={'donor_entity_index':0,'direction':3,'initial_animation':2}
        self.session.content_database['definitions']=[{'id':'npc:test','kind':'npc','source':{'catalogue_index':4}}]
        with patch('event_movement_compile.animation_profile',return_value=[{'directions_valid':[True]*4}]*3):
            exported=prepare_native_event_export(self.session)
        row=record_cluster(exported.data,2)['entities'][-1]
        self.assertEqual(row[5]&3,3)
        self.assertTrue(row[10]&128)
        self.assertEqual(record_cluster(exported.data,2)['entities'][0],raw)
        self.assertEqual(exported.native_event_export_report[0]['opcodes'],[0x1A,0xFF])

    def test_npc_up_facing_validates_native_animation_direction2(self):
        raw=bytes([0,0,7,7,1,64,4,2,2,2]+[0]*10)
        self.session.data,_=append_record_cluster(self.session.data,2,entities=[raw])
        self.graph['pages'][0].update(trigger='interact',commands=[],class_id='npc:test')
        self.graph['native_placement']={'donor_entity_index':0,'direction':1,'initial_animation':0}
        self.session.content_database['definitions']=[{'id':'npc:test','kind':'npc','source':{'catalogue_index':4}}]
        with patch('event_movement_compile.animation_profile',return_value=[{'directions_valid':[False,False,True,False]}]):
            exported=prepare_native_event_export(self.session)
        self.assertEqual(record_cluster(exported.data,2)['entities'][-1][5]&3,1)
