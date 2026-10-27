"""Launcher / Generator placements keep what they spawn; Generator "Spawns" option (2026-10-22)."""
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
DATAS = ROOT / 'game/disc/DATA/DATAS.BIN'


class ExpandTests(unittest.TestCase):
    def test_spawned_class_adds_dormant_template_graph(self):
        from new_event_compile import _expand_spawn_templates
        g = {'id': 'event:gen', 'name': 'Gen', 'map_id': 600, 'region': [4, 5, 1, 1],
             'native_placement': {'spawned_class': 'enemy:0001'}, 'pages': [{'class_id': 'object:0127'}]}
        out = _expand_spawn_templates([g], {'enemy:0001': {}, 'object:0127': {}})
        self.assertEqual(len(out), 2)
        sp = out[1]['native_placement']
        self.assertEqual((sp['spawn_of'], sp['spawn_class'], sp['generator_spawn']), ('event:gen', 'enemy:0001', True))
        self.assertEqual(out[1]['region'][:2], [4, 5])

    def test_missing_spawned_class_is_an_error(self):
        from new_event_compile import _expand_spawn_templates
        g = {'id': 'e', 'map_id': 1, 'native_placement': {'spawned_class': 'enemy:9999'}, 'pages': []}
        with self.assertRaises(ValueError):
            _expand_spawn_templates([g], {})

    def test_generator_is_a_spawn_choice_class(self):
        from behavior_transplant import SPAWN_CHOICE_CATALOGUES
        self.assertIn(394, SPAWN_CHOICE_CATALOGUES)


class FreezableFlameTests(unittest.TestCase):
    def test_touched_program_matches_stock_443(self):
        from native_freezable_flame import touched_program
        self.assertEqual(touched_program(0x800A).hex(), '878007040700' + '2b050a80ff')

    def test_flight_program_jumps_land_on_instructions(self):
        from native_freezable_flame import flight_program
        code = flight_program(0x87F0)
        self.assertEqual(code[:3], bytes((0x2A, 0x1A, 0x03)))
        self.assertEqual(code[-3], 0x02)
        self.assertEqual(code[4 + int.from_bytes(code[7:9], 'little', signed=True)], 0x06)   # flag set -> freeze (clear flag)
        self.assertEqual(len(code) - 3 + int.from_bytes(code[-2:], 'little', signed=True), 0)   # thawed -> fly again

    def test_launcher_and_turret_offer_the_option(self):
        from native_freezable_flame import FREEZABLE_CATALOGUES
        self.assertEqual(set(FREEZABLE_CATALOGUES), {317, 342})

@unittest.skipUnless(DATAS.is_file(), 'needs the original DATAS.BIN')
class TransplantSpawnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = DATAS.read_bytes()

    def hooks(self, m, i):
        from native_class_placement import record_cluster
        return record_cluster(self.data, m)['entities'][i][10:16]

    def test_launcher_flames_are_copied_not_removed(self):
        from behavior_transplant import transplant_hooks
        _, _, report = transplant_hooks(self.data, 163, 26, self.hooks(26, 0), spawns=(0,) * 6)
        refs = report['copied_programs'][0]['map_refs']
        self.assertEqual(len(refs), 4)
        self.assertTrue(all('copied_to' in r for r in refs), refs)

    def test_object_without_spawns_option_still_removes(self):
        from behavior_transplant import transplant_hooks
        _, _, report = transplant_hooks(self.data, 163, 26, self.hooks(26, 0))
        self.assertTrue(all(r.get('removed') for r in report['copied_programs'][0]['map_refs']))

    def test_generator_spawns_chosen_template(self):
        from behavior_transplant import transplant_hooks
        _, _, report = transplant_hooks(self.data, 163, 87, self.hooks(87, 21), spawns=(0,) * 6, spawn_target=0x55)
        refs = report['copied_programs'][0]['map_refs']
        self.assertEqual([r.get('chosen') for r in refs], [0x55] * 4)


    def test_launcher_always_fire_removes_player_box(self):
        from behavior_transplant import program_span
        code, _ = program_span(self.data, 26, 'C', 34, player_box='always')
        self.assertNotIn(bytes.fromhex('3b1d310a14003b'), code)
        self.assertEqual(code.count(bytes((0x2D,))) >= 4, True)

    def test_launcher_trigger_range_box(self):
        from behavior_transplant import program_span
        code, _ = program_span(self.data, 26, 'C', 34, player_box=(30, 40, 3))
        self.assertIn(bytes((0x3B, 27, 33, 37, 43)), code)

if __name__ == '__main__':
    unittest.main()
