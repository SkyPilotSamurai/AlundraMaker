import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from content_database import ContentDatabase
from object_activation import default_event_trigger
from new_event_compile import validate_new_event
from event_graph import validate_event_graph


class ActivationTests(unittest.TestCase):
    def test_new_switch_object_defaults_and_existing_events_are_not_rewritten(self):
        for index in (298,301,305,306,307,312,313,324,325,326):
            self.assertEqual(default_event_trigger({'kind':'object','source':{'catalogue_index':index}}),'activate')
        db = ContentDatabase()
        obj = db.new('object', 'Switch')
        obj['source']['catalogue_index'] = 305
        event = db.new_event_graph(51, x=3, y=4, class_id=obj['id'])
        self.assertEqual(event['pages'][0]['trigger'], 'activate')
        event['pages'][0]['trigger'] = 'touch'
        loaded = ContentDatabase(db.to_json())
        self.assertEqual(loaded.document['event_graphs'][0]['pages'][0]['trigger'], 'touch')

    def test_custom_activation_reaction_and_npc_defaults(self):
        obj = {'kind': 'object', 'data': {'reactions': {'sword': {'activate': True}}}}
        self.assertEqual(default_event_trigger(obj), 'activate')
        obj['kind'] = 'npc'
        self.assertEqual(default_event_trigger(obj), 'interact')
        self.assertEqual(default_event_trigger(None), 'interact')

    def test_empty_activation_preserves_native_placement_but_actions_fail_explicitly(self):
        db = ContentDatabase(); obj = db.new('object', 'Torch')
        obj['source']['catalogue_index'] = 337
        event = db.new_event_graph(51, x=3, y=4, class_id=obj['id'])
        self.assertEqual(validate_new_event(event)[1], 'activate')
        event['pages'][0]['commands'] = [{'type': 'wait', 'frames': 1}]
        with self.assertRaisesRegex(ValueError, 'object-specific state-change hook'):
            validate_new_event(event)

    def test_player_character_command_is_stored_and_rejects_unknown_characters(self):
        db = ContentDatabase(); event = db.new_event_graph(51, x=3, y=4)
        event['pages'][0]['commands'] = [{'type': 'change_player_character', 'character': 'Meia'}]
        self.assertEqual(validate_event_graph(event)['pages'][0]['commands'][0]['character'], 'Meia')
        event['pages'][0]['commands'][0]['character'] = 'Septimus'
        with self.assertRaises(ValueError): validate_event_graph(event)


if __name__ == '__main__': unittest.main()
