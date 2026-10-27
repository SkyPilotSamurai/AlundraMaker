"""Item pages with conditions and actions (2026-10-23): native pickup, once only,
actions run after the pickup; enemy page / item page events swap like NPC pages."""
import unittest
from unittest.mock import patch
import test_new_event_compile as existing
from event_export import prepare_native_event_export
from native_class_placement import record_cluster
from new_event_compile import _expand_item_pages, _split_pages

SWITCH = lambda i, v=True: {'type': 'switch', 'switch_scope': 'project', 'switch_id': i, 'value': v, 'operator': '=='}
ITEM = lambda g, p: p.get('class_id', g.get('class_id')) == 'item:bean'


class _Registry:
    def __init__(self):self.n = 100
    def create(self, kind, name, **_):
        self.n += 1;return {'id': self.n}


class ItemPageExpansionTests(unittest.TestCase):
    def graph(self, pages):
        return {'id': 'event:1', 'name': 'Shadow', 'map_id': 2, 'region': [3, 4, 1, 1], 'class_id': None,
                'trigger': 'interact', 'pages': pages, 'native_placement': {}}

    def test_item_page_is_once_only_and_actions_follow_pickup(self):
        page = {'id': 'p', 'class_id': 'item:bean', 'trigger': 'touch', 'conditions': [SWITCH(8)],
                'commands': [{'type': 'change_money', 'amount': 5}]}
        item, after = _expand_item_pages([self.graph([page])], ITEM, _Registry())
        collected = item['_once']['killed']
        self.assertEqual(item['pages'][0]['commands'], [])
        self.assertIn(SWITCH(collected, False), item['pages'][0]['conditions'])
        self.assertIsNone(after['class_id'])
        self.assertEqual(after['trigger'], 'parallel')
        self.assertIn(SWITCH(collected), after['pages'][0]['conditions'])
        done = after['pages'][0]['conditions'][1]['switch_id']
        self.assertEqual(after['pages'][0]['commands'][0]['switch_id'], done)   # runs once
        self.assertEqual(after['pages'][0]['commands'][1], {'type': 'change_money', 'amount': 5})

    def test_plain_item_stays_plain_native_pickup(self):
        page = {'id': 'p', 'class_id': 'item:bean', 'conditions': [], 'commands': []}
        out = _expand_item_pages([self.graph([page])], ITEM, _Registry())
        self.assertEqual(len(out), 1);self.assertNotIn('_once', out[0])

    def test_enemy_page_then_item_page_split(self):
        pages = [{'id': 'p1', 'class_id': 'enemy:shadow', 'trigger': 'death', 'conditions': [SWITCH(5)], 'commands': []},
                 {'id': 'p2', 'class_id': 'item:bean', 'trigger': 'touch', 'conditions': [SWITCH(8)],
                  'commands': [{'type': 'change_money', 'amount': 1}]}]
        split = _split_pages([self.graph(pages)], lambda g: any(ITEM(g, p) for p in g['pages']))
        self.assertEqual([g['class_id'] for g in split], ['enemy:shadow', 'item:bean'])
        self.assertIn(SWITCH(8, False), split[0]['pages'][0]['conditions'])   # page 2 in force hides the enemy
        out = _expand_item_pages(split, ITEM, _Registry())
        self.assertEqual([g['id'] for g in out], ['event:1#page1', 'event:1#page2', 'event:1#page2/picked_up'])

    def test_same_item_on_two_pages_is_split(self):
        pages = [{'id': 'p1', 'class_id': 'item:bean', 'conditions': [SWITCH(1)], 'commands': []},
                 {'id': 'p2', 'class_id': 'item:bean', 'conditions': [SWITCH(2)], 'commands': []}]
        split = _split_pages([self.graph(pages)], lambda g: any(ITEM(g, p) for p in g['pages']))
        self.assertEqual(len(split), 2)

    def test_item_page_refuses_actions_on_this_event(self):
        page = {'id': 'p', 'class_id': 'item:bean', 'trigger': 'touch', 'conditions': [],
                'commands': [{'type': 'change_animation', 'animation_id': 1}]}
        with self.assertRaisesRegex(ValueError, 'gone once picked up'):
            _expand_item_pages([self.graph([page])], ITEM, _Registry())
        page.update(trigger='event_touch', commands=[{'type': 'change_money', 'amount': 1}])
        with self.assertRaisesRegex(ValueError, 'the event_touch trigger does not apply'):
            _expand_item_pages([self.graph([page])], ITEM, _Registry())

    def test_death_and_activate_item_pages_are_ignored(self):
        for trigger in ('death', 'activate'):
            page = {'id': 'p', 'class_id': 'item:bean', 'trigger': trigger, 'conditions': [],
                    'commands': [{'type': 'change_money', 'amount': 1}]}
            out = _expand_item_pages([self.graph([page])], ITEM, _Registry())
            self.assertEqual(len(out), 1);self.assertEqual(out[0]['pages'][0]['commands'], [])

    def test_hit_item_page_gets_hit_spot_and_controller(self):
        page = {'id': 'p', 'class_id': 'item:bean', 'trigger': 'hit', 'conditions': [],
                'commands': [{'type': 'change_money', 'amount': 1}],
                'trigger_actions': [{'trigger': 'hit', 'hit_sources': ['sword', 'ice_wand'], 'commands': [{'type': 'change_money', 'amount': 1}]}]}
        item, spot, hit = _expand_item_pages([self.graph([page])], ITEM, _Registry())
        self.assertEqual(spot['_hit_marker']['elements'], [0, 7])
        self.assertEqual(spot['pages'][0]['conditions'], item['pages'][0]['conditions'])   # there while the item is
        self.assertIn(SWITCH(spot['_hit_marker']['request']), hit['pages'][0]['conditions'])
        self.assertEqual(hit['pages'][0]['commands'][0]['value'], False)   # one run per hit request
        page['trigger_actions'][0]['hit_sources'] = ['spring_bean']
        with self.assertRaisesRegex(ValueError, 'no known native attack type'):
            _expand_item_pages([self.graph([page])], ITEM, _Registry())

    def test_classless_hit_page_gets_one_spot_per_tile(self):
        from new_event_compile import _expand_hit_pages
        g = self.graph([{'id': 'p', 'class_id': None, 'trigger': 'hit', 'conditions': [], 'commands': [{'type': 'change_money', 'amount': 1}],
                         'trigger_actions': [{'trigger': 'hit', 'hit_sources': ['sword'], 'commands': []}]}])
        g['region'] = [3, 4, 2, 1]
        out = _expand_hit_pages([g], _Registry())
        self.assertEqual([x['region'] for x in out[:2]], [[3, 4, 1, 1], [4, 4, 1, 1]])
        self.assertEqual(out[2]['trigger'], 'parallel')
        g['region'] = [3, 4, 4, 3]
        with self.assertRaisesRegex(ValueError, 'at most 9 tiles'):
            _expand_hit_pages([g], _Registry())

    def test_classless_death_activate_events_are_dropped(self):
        from new_event_compile import _drop_unfired_pages
        g = self.graph([{'id': 'p', 'class_id': None, 'trigger': 'death', 'commands': [{'type': 'change_money', 'amount': 1}]}])
        self.assertEqual(_drop_unfired_pages([g]), [])


class SplitAndWarpTests(unittest.TestCase):
    def test_pages_with_different_triggers_are_split(self):
        g = {'id': 'e', 'class_id': None, 'trigger': 'touch', 'pages': [
            {'id': 'a', 'class_id': None, 'trigger': 'touch', 'conditions': [], 'commands': [{'type': 'change_money', 'amount': 1}]},
            {'id': 'b', 'class_id': None, 'trigger': 'autorun', 'conditions': [SWITCH(3)], 'commands': [{'type': 'change_money', 'amount': 2}]}]}
        split = _split_pages([g])
        self.assertEqual([x['trigger'] for x in split], ['touch', 'autorun'])
        self.assertIn(SWITCH(3, False), split[0]['pages'][0]['conditions'])


class ItemPageExportTests(unittest.TestCase):
    def setUp(self):
        existing.NewEventCompileTests.setUp(self)

    def test_conditional_item_with_actions_exports_pickup_watcher_and_controller(self):
        from project_state_registry import ProjectStateRegistry
        switch = ProjectStateRegistry(self.session.content_database).create('switches', 'Shadow killed')['id']
        self.graph['pages'][0].update(trigger='touch', class_id='item:herb', conditions=[SWITCH(switch)],
                                      commands=[{'type': 'change_money', 'amount': 3}])
        self.session.content_database['definitions'] = [{'id': 'item:herb', 'kind': 'item', 'source': {'item_id': 36, 'catalogue_index': 66}}]
        template = bytes([0, 0, 7, 7, 1, 0, 66] + [0] * 13)
        with patch('new_event_compile.verified_item_pickup_template', return_value=template):
            exported = prepare_native_event_export(self.session)
        report = {row['event_id']: row for row in exported.native_event_export_report}
        item = report['event:0001']
        self.assertTrue(item['native_pickup'])
        self.assertIn('presence_controller', item)
        self.assertTrue(item['collection_persistence'].startswith('once'))
        after = report['event:0001/picked_up']
        self.assertEqual(after['bank'], 'B')
        self.assertIn(0x98, after['opcodes'])   # change money, after the pickup
        row = record_cluster(exported.data, 2)['entities'][-1]
        self.assertEqual(row[6], 66);self.assertEqual(row[10:], bytes(10))   # the item keeps no authored hooks

    def test_hit_item_page_exports_hit_spot(self):
        acts = [{'type': 'change_money', 'amount': 3}]
        self.graph['pages'][0].update(trigger='hit', class_id='item:herb', conditions=[], commands=acts,
            trigger_actions=[{'trigger': 'hit', 'hit_sources': ['sword'], 'commands': acts, 'destroy_after': False}])
        self.session.content_database['definitions'] = [{'id': 'item:herb', 'kind': 'item', 'source': {'item_id': 36, 'catalogue_index': 66}}]
        template = bytes([0, 0, 7, 7, 1, 0, 66] + [0] * 13)
        marker = lambda data, original, m, x, y, z: bytearray(bytes.fromhex('0000333b014019') + bytes((x * 2, y * 2, z * 2)) + bytes(10))
        with patch('new_event_compile.verified_item_pickup_template', return_value=template),                 patch('new_event_compile._hit_marker_record', side_effect=marker):
            exported = prepare_native_event_export(self.session)
        report = [row for row in exported.native_event_export_report if row.get('hit_spot')][0]
        self.assertIn(0x87, report['opcodes']);self.assertIn(0x2A, report['opcodes'])
        self.assertIn('presence_controller', report)   # gone with the item
        hit = [row for row in exported.native_event_export_report if row['event_id'] == 'event:0001/hit'][0]
        self.assertIn(0x98, hit['opcodes'])
        rows = record_cluster(exported.data, 2)['entities']
        spot, item = rows[-1], rows[-2]
        self.assertEqual(spot[6], 25);self.assertEqual(spot[13], report['hit_spot']['D']['hook_value'])
        self.assertEqual(item[10:], bytes(10))   # the item itself keeps no hooks

if __name__ == '__main__':
    unittest.main()
