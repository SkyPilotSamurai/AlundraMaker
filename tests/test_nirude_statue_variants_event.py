"""Shooting Nirude Face Statue entries (Fire / Homing Fire / Laser), 2026-10-24."""
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
DATAS = ROOT / 'game/disc/DATA/DATAS.BIN'
TESTS = (bytes.fromhex('a101'), bytes.fromhex('a102'), bytes.fromhex('a202'))   # stand-in condition / command bytes


class EmitterTests(unittest.TestCase):
    def test_fire_keeps_stock_35_b3_body(self):
        from native_nirude_statue_variants import emitter_program
        code = emitter_program('fire', 0x8701, (14,))
        # 35 B 3 per statue: 30 <broken> skip, 2C t, 04 skip, 2D t, 00 00
        self.assertEqual(code[:3], bytes.fromhex('377800'))
        self.assertEqual(code[3:6], bytes.fromhex('300187'))
        self.assertIn(bytes.fromhex('2c0e'), code); self.assertIn(bytes.fromhex('2d0e'), code)
        self.assertEqual(code[-1], 0xFF)

    def test_laser_spawns_column_five_frames_apart(self):
        from native_nirude_statue_variants import emitter_program
        code = emitter_program('laser', 0x8701, tuple(range(13, 22)))
        self.assertIn(b''.join(bytes((0x2D, t, 0x37, 0x05)) for t in range(13, 22)), code)

    def test_emitter_waits_for_active(self):
        from native_nirude_statue_variants import emitter_program, emitter_refs
        code = emitter_program('laser', 0x8701, (13,), 0x8702)
        self.assertTrue(code.startswith(bytes.fromhex('360287')))
        self.assertEqual([r[0] for r in emitter_refs(code)], ['spawn'])

    def test_refs_name_every_spawn_and_test(self):
        from native_nirude_statue_variants import emitter_program, emitter_refs
        refs = emitter_refs(emitter_program('homing', 0x8701, (16,)))
        self.assertEqual(sorted(r[0] for r in refs), ['select', 'spawn'])
        self.assertTrue(all(r[2] == 16 for r in refs))

    def test_flags_per_placement(self):
        from native_nirude_statue_variants import next_flags
        counts = {}
        self.assertEqual(next_flags(5, counts), (0x8700, 0x8701, 0x8702))
        self.assertEqual(next_flags(5, counts), (0x8703, 0x8704, 0x8705))

    def test_variant_of_needs_variant_key(self):
        from native_nirude_statue_variants import variant_of
        from native_nirude_face import is_face
        row = {'source': {'catalogue_index': 346, 'variant': 'nirude_statue', 'statue_variant': 'laser'}}
        self.assertEqual(variant_of(row), 'laser')
        self.assertFalse(is_face(row))                     # never takes the plain statue's path
        self.assertIsNone(variant_of({'source': {'catalogue_index': 346}}))


class ExpandTests(unittest.TestCase):
    def test_activation_controllers_and_state(self):
        from new_event_compile import _nirude_statue_variants
        from project_state_registry import ProjectStateRegistry
        reg = ProjectStateRegistry({})
        defs = {'object:0900': {'kind': 'object', 'source': {'catalogue_index': 346, 'variant': 'nirude_statue', 'statue_variant': 'fire'}}}
        g = {'id': 'event:s', 'name': 'S', 'map_id': 483, 'region': [27, 36, 1, 1], 'native_placement': {'active_by_default': True},
             'pages': [{'class_id': 'object:0900', 'trigger': 'activate', 'commands': [],
                        'trigger_actions': [{'trigger': 'activate', 'commands': [{'type': 'wait', 'frames': 1}]},
                                            {'trigger': 'deactivate', 'commands': [{'type': 'wait', 'frames': 2}]}]}]}
        states = {}
        out = _nirude_statue_variants([g], defs, reg, states)
        self.assertEqual([o['id'] for o in out], ['event:s/activated', 'event:s/broken'])
        self.assertIn('event:s', states)
        self.assertEqual(g['pages'][0]['trigger'], 'interact')
        self.assertEqual(set(g['_statue']), {'state', 'broken'})

    def test_missing_active_by_default_is_on_explicit_off_stays_off(self):
        from new_event_compile import _nirude_statue_variants
        from project_state_registry import ProjectStateRegistry
        defs = {'o': {'kind': 'object', 'source': {'catalogue_index': 346, 'variant': 'nirude_statue', 'statue_variant': 'fire'}}}
        for placement, want in (({}, True), ({'active_by_default': False}, False)):
            reg = ProjectStateRegistry({})
            g = {'id': 'e', 'name': 'S', 'map_id': 483, 'native_placement': placement, 'pages': [{'class_id': 'o', 'trigger': 'activate'}]}
            _nirude_statue_variants([g], defs, reg, {})
            row = next(s for s in reg.state['switches'] if s['id'] == g['_statue']['state'])
            self.assertEqual(bool(row.get('initial_value')), want)


class DatabaseTests(unittest.TestCase):
    def test_entries(self):
        from content_database import ContentDatabase
        db = ContentDatabase()
        base = db.new('object', 'Nirude Face Statue'); base['source'] = {'catalogue_index': 346, 'observed_maps': [17]}
        rows = db.ensure_nirude_statue_variants()
        self.assertEqual([r['name'] for r in rows], ['Nirude Face Statue (Fire)', 'Nirude Face Statue (Homing Fire)',
                                                    'Nirude Face Statue (Laser)'])
        self.assertEqual([r['source']['fixed_donor'] for r in rows], [[35, 9], [38, 13], [36, 10]])
        self.assertEqual(len(db.ensure_nirude_statue_variants()), 3)
        self.assertEqual(sum(1 for r in db.definitions if r['source'].get('variant') == 'nirude_statue'), 3)


@unittest.skipUnless(DATAS.is_file(), 'needs the original DATAS.BIN')
class InstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = DATAS.read_bytes()

    def test_each_variant_installs_with_templates_copied(self):
        from native_nirude_statue_variants import install, VARIANTS
        for key, v in VARIANTS.items():
            with self.subTest(key):
                data, (c, d), b, report = install(self.data, 163, key, {}, (0, 0, 0), {}, *TESTS)
                self.assertTrue(c & 0x80 and d & 0x80 and b & 0x80)
                copied = [r for r in report['templates'] if 'copied_to' in r]
                self.assertEqual(len({r['template'] for r in copied}), len(v['templates']), report['templates'])
                self.assertEqual((report['hit_flag'], report['broken_flag'], report['active_flag']), ('0x8700', '0x8701', '0x8702'))

    def test_fire_statue_story_wait_passed(self):
        from native_nirude_statue_variants import install
        _, _, _, report = install(self.data, 163, 'fire', {}, (0, 0, 0), {}, *TESTS)
        self.assertIn('wait 0x81ab passed', report['statue_flags_moved'])

    def test_tick_program_wraps_stock_c(self):
        from native_nirude_statue_variants import _own_program, tick_program
        from editor_session import EditSession
        s = EditSession.readonly(self.data)
        stock, rows, _ = _own_program(self.data, s, 36, 'C', 10, {0x8064: 0x8700, 0x83E8: 0x8701})
        code = tick_program(stock, rows, 0x8701, 0x8702, *TESTS)
        self.assertTrue(code.startswith(bytes.fromhex('a10203')))        # broken switch on -> broken
        self.assertIn(bytes.fromhex('1a0d'), code[:8])                    # dormant face
        self.assertIn(bytes.fromhex('050287') + stock[:4], code)          # active: room flag, then stock C
        self.assertIn(bytes.fromhex('050187a202'), code)                  # broken flag + broken switch
        self.assertTrue(code.endswith(bytes.fromhex('0501872b1a03ff')))


if __name__ == '__main__':
    unittest.main()
