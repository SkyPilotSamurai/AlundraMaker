"""2026-10-21: RPG-style page priority (a later page in force hides an earlier one whatever its
conditions), conditional-enemy latch slots, boss-part recolouring and enemy donor choice."""
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
from new_event_compile import _split_pages, _presence_condition
from native_actor_lifecycle import compile_condition_presence_watcher


def sw(i, v=True):
    return {'type': 'switch', 'switch_scope': 'project', 'switch_id': i, 'value': v, 'operator': '=='}


def graph(*pages):
    return {'id': 'event:1', 'name': 'Block', 'map_id': 483, 'class_id': 'npc:1',
            'pages': [dict({'conditions': [], 'commands': [], 'class_id': 'npc:1'}, **p) for p in pages]}


class PagePriority(unittest.TestCase):
    def test_block_without_condition_vanishes_when_a_two_condition_page_is_in_force(self):
        out = _split_pages([graph({}, {'conditions': [sw(1), sw(2)], 'class_id': None})])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]['_blockers'], [[sw(1), sw(2)]])
        presence = _presence_condition(out[0])
        self.assertEqual(list(presence), [[]])
        self.assertEqual(len(presence.blockers), 1)

    def test_single_switch_later_page_still_flips(self):
        out = _split_pages([graph({}, {'conditions': [sw(3)], 'class_id': None})])
        self.assertNotIn('_blockers', out[0])
        self.assertEqual(out[0]['pages'][0]['conditions'], [dict(sw(3), value=False)])

    def test_later_page_without_conditions_hides_earlier(self):
        out = _split_pages([graph({}, {'class_id': 'npc:2'})])
        self.assertEqual([g['id'] for g in out], ['event:1#page2'])

    def test_watcher_checks_blockers_first(self):
        test = ('test', b'\xe1\x01\x00')   # any byte test: only the layout matters here
        with_blocker = compile_condition_presence_watcher([[]], 3, blockers=[[test, test]])
        plain = compile_condition_presence_watcher([[test]], 3)
        self.assertGreater(len(with_blocker), len(plain))
        with self.assertRaises(ValueError):
            compile_condition_presence_watcher([[]], 3)   # no conditions and no later page: always shown
        with self.assertRaises(ValueError):
            compile_condition_presence_watcher([[]], 3, blockers=[[]])


class Recolour(unittest.TestCase):
    def test_group_recolour_keeps_palette_count_for_melzas(self):
        path = ROOT / 'game/disc/DATA/DATAS.BIN'
        if not path.exists():
            self.skipTest('Private original unavailable')
        from local_sprite_recolor import recolor_local_classes
        from local_sprite_import import layout, sprite_assets
        data = path.read_bytes()
        _, _, s, _, sh = layout(data, 327); before = (sh[6] - sh[5]) // 32
        result, info = recolor_local_classes(data, 327, [418, 419, 420, 423, 424], 150, 140)
        _, _, s2, _, sh2 = layout(result, 327)
        self.assertLessEqual((sh2[6] - sh2[5]) // 32, max(before, 41))
        self.assertEqual(info['catalogues'], [418, 419, 420, 423, 424])
        for c in (418, 424):   # the boss and his look-alike copy both changed
            a = sprite_assets(data, 327, c - 256); b = sprite_assets(result, 327, c - 256)
            pal = lambda d, sh_, s_, i: d[s_ + sh_[5] + 32 * i:s_ + sh_[5] + 32 * (i + 1)]
            self.assertTrue(any(pal(data, sh, s, i) != pal(result, sh2, s2, j)
                                for i, j in zip(sorted(a['palettes']), sorted(b['palettes']))))


class CommandTransforms(unittest.TestCase):
    def test_show_hide_graphic_and_create_become_switches_and_pages(self):
        from new_event_compile import _visibility_and_graphics
        made = []
        class Reg:
            def create(self, kind, name, initial_value=False):
                made.append((name, initial_value)); return {'id': len(made)}
        target = graph({}); target['id'] = 'event:t'
        caller = graph({'commands': [{'type': 'set_event_active', 'event_id': 'event:t', 'active': False},
                                     {'type': 'change_graphic', 'target': 'this_event', 'graphic': 'npc:2'},
                                     {'type': 'spawn_class', 'class_id': 'object:1', 'position': [3, 4]}]})
        caller['id'] = 'event:c'
        graphs = [target, caller]
        _visibility_and_graphics(graphs, Reg())
        self.assertEqual([r['type'] for r in caller['pages'][0]['commands']], ['set_switch'] * 3)
        self.assertTrue(made[0][1])                                          # "shown" starts ON
        self.assertEqual(target['pages'][0]['conditions'][-1]['switch_id'], 1)
        self.assertEqual(caller['pages'][-1]['class_id'], 'npc:2')          # the new graphic is a later page
        spawned = graphs[-1]
        self.assertEqual((spawned['region'][:2], spawned['class_id']), ([3, 4], 'object:1'))


if __name__ == '__main__':
    unittest.main()
