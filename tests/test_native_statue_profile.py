import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_statue_profile import verify_source,compile_statue
from project_state_registry import ProjectStateRegistry
ROOT=Path(__file__).resolve().parents[1]

class StatueProfileTests(unittest.TestCase):
    def test_private_request_and_state_replace_both_donor_flags(self):
        doc={};r=ProjectStateRegistry(doc);m=r.create('switches','Moved')['id'];q=r.create('switches','Request')['id']
        programs,report=compile_statue(r,m,q,8,15,8,b'\x98\x01\x00')
        self.assertEqual(programs['F'].hex(),'e1000001030700e0010001ff')
        self.assertIn(bytes.fromhex('09181a01bd19001e1800be19001a0000980100'),programs['C'])
        self.assertNotIn(bytes.fromhex('057903'),programs['C']);self.assertNotIn(bytes.fromhex('366480'),programs['C'])
        self.assertEqual(report['removed_flags'],['0379','8064'])
        self.assertFalse(report['memory_card_persistent'])

    @unittest.skipUnless((ROOT/'game/disc/DATA/DATAS.BIN').exists(),'Local lawful input required')
    def test_exact_native_source_record_and_three_programs(self):
        self.assertTrue(verify_source((ROOT/'game/disc/DATA/DATAS.BIN').read_bytes()))

    def test_shared_request_state_is_rejected(self):
        r=ProjectStateRegistry({});m=r.create('switches','Moved')['id']
        with self.assertRaisesRegex(ValueError,'distinct'):compile_statue(r,m,m,8,15,8)

    @unittest.skipUnless((ROOT/'game/disc/DATA/DATAS.BIN').exists(),'Local lawful input required')
    def test_production_statue_keeps_existing_records_and_uses_owned_three_banks(self):
        from editor_session import EditSession
        from content_database import ContentDatabase
        from event_graph import new_event_graph
        from new_event_compile import compile_new_events
        from native_class_placement import record_cluster
        stock=(ROOT/'game/disc/DATA/DATAS.BIN').read_bytes();db=ContentDatabase();db.populate_catalogue(stock)
        definition=next(r for r in db.definitions if r['kind']=='object' and r.get('source',{}).get('catalogue_index')==298)
        g=new_event_graph('statue:test',163,'Statue',8,15,definition['id']);g['pages'][0]['trigger']='activate';g['pages'][0]['commands']=[{'type':'change_money','amount':1}]
        s=EditSession(stock);s.content_database={'definitions':db.definitions,'event_graphs':[g]}
        c=compile_new_events(s,[g]);old=record_cluster(stock,163)['entities'];rows=record_cluster(c.data,163)['entities']
        self.assertEqual(rows[:-1],old);self.assertEqual(bytes(s.data),stock)
        self.assertTrue(all(rows[-1][i]&128 for i in (10,12,15)));self.assertEqual(rows[-1][11:12],b'\0');self.assertEqual(rows[-1][13:15],b'\0\0')
        self.assertEqual(c.native_event_export_report[0]['recovered_object']['controller']['removed_flags'],['0379','8064'])
        self.assertEqual(len(c.content_database['project_state']['switches']),2)
