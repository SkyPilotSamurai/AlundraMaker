import unittest
import test_new_event_compile as existing
from event_export import prepare_native_event_export
from native_class_placement import append_record_cluster, record_cluster


class EventFloatTests(unittest.TestCase):
    def setUp(self):
        existing.NewEventCompileTests.setUp(self)

    def _npc(self, **page):
        raw = bytes([0, 0, 7, 7, 1, 64, 4, 2, 2, 2] + [0] * 10)
        self.session.data, _ = append_record_cluster(self.session.data, 2, entities=[raw])
        self.graph['pages'][0].update(trigger='interact', commands=[], class_id='npc:test', **page)
        self.graph['native_placement'] = {'donor_entity_index': 0}
        self.session.content_database['definitions'] = [{'id': 'npc:test', 'kind': 'npc', 'source': {'catalogue_index': 4}}]
        return raw

    def test_float_adds_gravity_off_load_process_and_raises_z(self):
        raw = self._npc(float=True, float_height=24)
        exported = prepare_native_event_export(self.session)
        row = record_cluster(exported.data, 2)['entities'][-1]
        self.assertTrue(row[10] & 128)
        self.assertEqual(row[9], raw[9] + 3)
        self.assertEqual(record_cluster(exported.data, 2)['entities'][0], raw)
        self.assertTrue({0x17, 0x5E, 0xFF}.issubset(exported.native_event_export_report[0]['opcodes']))

    def test_no_float_keeps_record(self):
        raw = self._npc()
        row = record_cluster(prepare_native_event_export(self.session).data, 2)['entities'][-1]
        self.assertEqual(row[10], 0)
        self.assertEqual(row[9], raw[9])

    def test_bad_float_height_rejected(self):
        self._npc(float=True, float_height=-8)
        with self.assertRaisesRegex(Exception, 'Float height'):
            prepare_native_event_export(self.session)


if __name__ == '__main__':
    unittest.main()
