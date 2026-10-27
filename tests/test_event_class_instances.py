import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import class_instance as ci
import content_database as cdb


def cls(cid, facing=None, kind='object', cat=1, **source):
    src = dict(catalogue_index=cat, **source)
    if facing:src['default_facing'] = facing
    return {'id': cid, 'kind': kind, 'name': cid, 'source': src, 'data': {}}


def graph(cid, **placement):
    return {'id': 'e1', 'pages': [{'class_id': cid}], 'native_placement': placement}


class EventClassInstanceTests(unittest.TestCase):
    def test_unset_facing_follows_class_changes(self):
        d = cls('rock', 'left');g = graph('rock')
        self.assertEqual(ci.effective_placement(g, d)['facing'], 'left')
        d['source']['default_facing'] = 'right'
        self.assertEqual(ci.effective_placement(g, d)['facing'], 'right')
        self.assertEqual(ci.resolve_graphs([g], [d])[0]['native_placement']['facing'], 'right')
        self.assertEqual(g['native_placement'], {})   # build never writes into the project

    def test_override_wins(self):
        d = cls('rock', 'left');g = graph('rock', facing='up')
        self.assertEqual(ci.resolve_graphs([g], [d])[0]['native_placement']['facing'], 'up')

    def test_set_override_drops_class_value(self):
        d = cls('rock', 'left');p = {}
        ci.set_override(p, 'facing', 'left', d);self.assertEqual(p, {})
        ci.set_override(p, 'facing', 'up', d);self.assertEqual(p, {'facing': 'up'})
        sara = cls('sara', kind='boss', cat=452);q = {}
        ci.set_override(q, 'track_player', True, sara, fallback=False);self.assertEqual(q, {})
        ci.set_override(q, 'track_player', False, sara, fallback=False);self.assertEqual(q, {'track_player': False})
        foe = cls('foe', kind='enemy');r = {}
        ci.set_override(r, 'track_player', False, foe, fallback=False);self.assertEqual(r, {})

    def test_pillar_default(self):
        self.assertEqual(ci.class_placement_defaults(cls('p', cat=298)), {'facing': 'right'})

    def test_migration_keeps_differing_values(self):
        doc = {'definitions': [cls('rock', 'left')],
               'event_graphs': [graph('rock', facing='left', height=3), dict(graph('rock', facing='down'), id='e2')]}
        removed = ci.strip_class_defaults(doc)
        self.assertEqual(removed, [('e1', 'facing', 'left')])
        self.assertEqual(doc['event_graphs'][0]['native_placement'], {'height': 3})
        self.assertEqual(doc['event_graphs'][1]['native_placement'], {'facing': 'down'})

    def test_replace_notifies_listeners(self):
        db = cdb.ContentDatabase();db.populate_catalogue()
        row = dict(db.definitions[0]);row['data'] = dict(row['data'], palette_shift={'hue_degrees': 40})
        seen = [];listener = lambda d, i: seen.append(i)
        cdb.DEFINITION_LISTENERS.append(listener)
        try:
            db.replace(row['id'], row);db.replace(row['id'], row)   # unchanged second time
        finally:cdb.DEFINITION_LISTENERS.remove(listener)
        self.assertEqual(seen, [row['id']])


if __name__ == '__main__':
    unittest.main()
