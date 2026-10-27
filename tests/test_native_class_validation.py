import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from native_class_validation import require_native_class_definition


class ClassValidationTests(unittest.TestCase):
    def test_renames_and_original_imported_stats_allowed(self):
        require_native_class_definition(SimpleNamespace(), {'id': 'enemy:new', 'name': 'Renamed', 'kind': 'enemy',
            'data': {'max_hp': 20, 'attacks': [7], 'balance_tiers': [{'max_hp': 20, 'attacks_raw': [7]}]}})

    def test_project_only_palette_animation_and_reactions_reject(self):
        for kind, values in [('npc', {'palette_shift': {'hue_degrees': 50}}),
                             ('npc', {'animations': [{'frames': [1], 'ticks_per_frame': 4}]}),
                             ('object', {'throwable': True}), ('enemy', {'contact_damage': 99}),
                             ('enemy', {'hitboxes': [{'x': 1, 'y': 2, 'z': 3}]})]:
            with self.assertRaises(ValueError):
                require_native_class_definition(SimpleNamespace(), {'id': 'test', 'kind': kind, 'data': values})

    def test_immutable_baseline_detects_emptied_attacks_and_boolean_changes(self):
        for key, old, new in [('attacks', [1], []), ('throwable', True, False)]:
            with self.assertRaises(ValueError):
                require_native_class_definition(SimpleNamespace(), {'id': 'test', 'kind': 'object',
                    'source': {'native_data_baseline': {key: old}}, 'data': {key: new}})

    def test_native_chest_contents_are_supported(self):
        require_native_class_definition(SimpleNamespace(), {'id': 'chest', 'kind': 'object',
            'data': {'contained_item_class_id': 'item:herb'}})
