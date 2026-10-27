import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from content_database import ContentDatabase
from editor_session import EditSession
from event_graph import new_event_graph
from event_export import prepare_native_event_export, EventExportError
from native_class_placement import record_cluster
from event_editor import instructions
from object_activation import default_event_trigger

INPUT = Path(__file__).resolve().parents[1] / 'game/disc/DATA/DATAS.BIN'


@unittest.skipUnless(INPUT.exists(), 'Requires local lawful stock input')
class KeyDoorExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stock = INPUT.read_bytes()
        db = ContentDatabase(); db.populate_catalogue(cls.stock)
        cls.definition = next(r for r in db.definitions if r['kind'] == 'object'
                              and r.get('source', {}).get('catalogue_index') == 324)

    def session(self, count=1):
        graphs = []
        for i in range(count):
            graph = new_event_graph('door:'+str(i),163,'Key door',8+i*2,15,self.definition['id'])
            graph['pages'][0].update(trigger='activate',commands=[{'type':'change_money','amount':7}])
            graphs.append(graph)
        session = EditSession(self.stock)
        session.content_database = {'definitions':[copy.deepcopy(self.definition)],'event_graphs':graphs}
        return session

    def test_two_doors_keep_stock_and_separate_private_opened_state(self):
        session = self.session(2); before = copy.deepcopy(session.content_database)
        exported = prepare_native_event_export(session)
        original = record_cluster(self.stock,163)['entities']
        rows = record_cluster(exported.data,163)['entities']
        self.assertEqual(rows[:-2],original)
        reports = [r['recovered_object'] for r in exported.native_event_export_report]
        self.assertNotEqual(reports[0]['state_id'], reports[1]['state_id'])
        self.assertEqual(session.content_database,before)
        self.assertEqual(default_event_trigger(self.definition),'activate')
        for row, report in zip(rows[-2:], reports):
            self.assertEqual(row[9],2)
            self.assertEqual(row[11:15],bytes(4))
            self.assertEqual(report['controller']['key_item_id'],61)
            code = b''.join(bytes(exported.data[p:p+n]) for p,_,n in
                            instructions(exported,163,'F '+str(row[15]&127)))
            offset = code.index(bytes.fromhex('833d01598100')) + 6
            target = offset + int.from_bytes(code[offset+1:offset+3],'little',signed=True)
            self.assertEqual(code[target],0x0D)
            self.assertIn(bytes.fromhex('843d'),code[:target])
            self.assertIn(bytes.fromhex('980700'),code[:target])

    def test_wrong_trigger_rejected(self):
        session = self.session();session.content_database['event_graphs'][0]['pages'][0]['trigger']='interact'
        with self.assertRaisesRegex(EventExportError,'Activate'):
            prepare_native_event_export(session)


if __name__ == '__main__':
    unittest.main()
