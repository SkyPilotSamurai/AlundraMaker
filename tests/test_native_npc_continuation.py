import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'))
from editor_session import EditSession
from event_graph import new_event_graph
from event_export import prepare_native_event_export, generated_event_opcodes, EventExportError
from native_class_placement import append_record_cluster,record_cluster
from native_npc_continuation import compile_fixed_npc_handoff
from event_editor import instructions
from test_native_script_allocation import fixture


class NpcContinuationTests(unittest.TestCase):
    def test_exact_relative_target_and_global_yield(self):
        raw=compile_fixed_npc_handoff(bytes.fromhex('980100ff'))
        self.assertEqual(raw,bytes.fromhex('66040000980100ff'))
        self.assertEqual(raw[4],0x98)
        with self.assertRaises(ValueError):compile_fixed_npc_handoff(b'\x98\x01\0')

    def test_fixed_new_npc_has_owned_tick_and_ordered_contents(self):
        session=EditSession(fixture(),verify=False)
        donor=bytes([0,0,7,7,1,0,4,2,2,2]+[0]*10)
        session.data,_=append_record_cluster(session.data,2,entities=[donor])
        graph=new_event_graph('npc:new',2,'New NPC',3,4)
        graph['pages'][0].update(trigger='interact',class_id='npc:test',commands=[
            {'type':'show_dialogue','text':'Before','speaker':'self'},
            {'type':'change_money','amount':1}])
        graph['native_placement']={'donor_entity_index':0}
        session.content_database={'definitions':[{'id':'npc:test','kind':'npc','source':{'catalogue_index':4}}], 'event_graphs':[graph]}
        old=bytes(session.data)
        with patch('area_map.grid',return_value=(8,8,[{'values':[0,0,0,1]}]*64)),patch('event_vm_compatibility.sprite_callbacks',return_value=[]):
            exported=prepare_native_event_export(session)
            actors=record_cluster(exported.data,2)['entities']
            self.assertEqual(actors[0],donor)
            tick=actors[1][12];talk=actors[1][15]
            self.assertTrue(tick&128);self.assertTrue(talk&128)
            self.assertEqual([op for _,op,_ in instructions(exported,2,f'C {tick&127}')],[255])
            self.assertEqual([op for _,op,_ in instructions(exported,2,f'F {talk&127}')],[0x66,0,0x0D,0x39,0x98,255])
            self.assertTrue({0x66,0x39}.issubset(set(generated_event_opcodes(session,exported))))
            self.assertEqual(bytes(session.data),old)
            self.assertFalse(exported.native_event_export_report[0]['npc_continuation']['gameplay_verified'])
            graph['pages'][0]['commands'].insert(0,{'type':'move_actor','target':'self','mode':'toward_player'})
            with self.assertRaisesRegex(EventExportError,'newly placed fixed NPC'):prepare_native_event_export(session)


if __name__=='__main__':unittest.main()
