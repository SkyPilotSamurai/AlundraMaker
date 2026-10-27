import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from content_database import ContentDatabase
from event_graph import ensure_trigger_actions, new_event_graph, validate_event_graph
from new_event_compile import validate_new_event


class TriggerHandlerTests(unittest.TestCase):
    def test_legacy_event_migrates_to_one_handler_without_losing_commands(self):
        graph = new_event_graph('event:copy', 12, 'A', 3, 4)
        graph['pages'][0]['commands'] = [{'type':'show_dialogue','text':'Hello'}]
        handler = ensure_trigger_actions(graph['pages'][0])[0]
        self.assertEqual(handler['trigger'], 'interact')
        self.assertEqual(handler['commands'], graph['pages'][0]['commands'])
        self.assertFalse(handler['destroy_after'])
        validate_event_graph(graph)

    def test_separate_touch_and_interact_tabs_persist_their_own_contents(self):
        db = ContentDatabase(); event = db.new_event_graph(12, 'Two triggers', 3, 4)
        page = event['pages'][0]
        handlers = ensure_trigger_actions(page)
        handlers[0]['commands'] = [{'type':'show_dialogue','text':'Talk'}]
        handlers.append({'trigger':'touch','commands':[{'type':'change_money','amount':2}],
                         'hit_sources':[],'destroy_after':False})
        db.replace_event_graph(event['id'], event)
        restored = ContentDatabase(db.to_json()).document['event_graphs'][0]['pages'][0]
        self.assertEqual([row['trigger'] for row in restored['trigger_actions']], ['interact','touch'])
        self.assertEqual(restored['trigger_actions'][1]['commands'][0]['type'], 'change_money')
        with self.assertRaisesRegex(ValueError, 'multiple trigger tabs'):
            validate_new_event(event)

    def test_hit_tab_requires_a_valid_selected_attack_filter_and_is_export_guarded(self):
        graph = new_event_graph('event:hit', 12, 'Hit', 3, 4)
        page = graph['pages'][0]
        page['trigger_actions'] = [{'trigger':'hit','commands':[], 'hit_sources':['sword'], 'destroy_after':False}]
        validate_event_graph(graph)
        with self.assertRaisesRegex(ValueError, 'native attack-hit callback'):
            validate_new_event(graph)
        page['trigger_actions'][0]['hit_sources'] = ['telepathy']
        with self.assertRaisesRegex(ValueError, 'Hit filters'):
            validate_event_graph(graph)

    def test_erase_event_command_replaces_destroy_after(self):
        from new_event_compile import _take_erase, _destroys
        graph = new_event_graph('event:erase', 12, 'Erase', 3, 4)
        erase = {'type': 'erase_event'}
        graph['pages'][0]['commands'] = [erase]
        graph['pages'][0]['trigger_actions'] = [{'trigger':'interact','commands':[erase],
                                                 'hit_sources':[], 'destroy_after':True}]
        validate_event_graph(graph)
        _take_erase(graph)
        self.assertTrue(_destroys(graph))
        self.assertEqual(graph['pages'][0]['commands'], [])
        old = new_event_graph('event:old', 12, 'Old', 3, 4)
        old['pages'][0]['trigger_actions'] = [{'trigger':'interact','commands':[],'hit_sources':[], 'destroy_after':True}]
        _take_erase(old)
        self.assertFalse(_destroys(old))   # the old checkbox no longer erases

    def test_object_state_checkboxes_default_off_and_roundtrip(self):
        db=ContentDatabase();obj=db.new('object','Switch')
        self.assertFalse(obj['data']['active_by_default'])
        self.assertFalse(obj['data']['activation_one_way'])
        self.assertFalse(obj['data']['remember_state_until_area_exit'])
        obj['data']['remember_state_until_area_exit']=True;db.replace(obj['id'],obj)
        self.assertTrue(ContentDatabase(db.to_json()).get(obj['id'])['data']['remember_state_until_area_exit'])
        obj['data']['active_by_default']='false'
        with self.assertRaisesRegex(ValueError, 'checkbox'):
            db.replace(obj['id'],obj)

    def test_project_event_copy_gets_new_event_and_page_ids_and_can_move_maps(self):
        db=ContentDatabase();npc=db.new('npc','Septimus');source=db.new_event_graph(12,'Guard',4,5,npc['id'])
        source['pages'][0]['commands']=[{'type':'show_dialogue','text':'Stay back.'}]
        db.replace_event_graph(source['id'],source)
        clone=db.duplicate_event_graph(source['id'],427,18,21)
        self.assertNotEqual(clone['id'],source['id'])
        self.assertNotEqual(clone['pages'][0]['id'],source['pages'][0]['id'])
        self.assertEqual((clone['map_id'],clone['region'][:2]),(427,[18,21]))
        self.assertEqual(clone['pages'][0]['class_id'],npc['id'])
        clone['pages'][0]['commands'][0]['text']='Copied text'
        self.assertEqual(source['pages'][0]['commands'][0]['text'],'Stay back.')

    def test_bound_native_process_cannot_be_copied_as_a_fresh_map_event(self):
        db=ContentDatabase();event=db.new_event_graph(12,'Retail process')
        event['native_binding']={'map_id':12,'bank':'F','offset':100}
        db.replace_event_graph(event['id'],event)
        with self.assertRaisesRegex(ValueError,'bound retail event cannot be copied'):
            db.duplicate_event_graph(event['id'],12,4,5)


if __name__ == '__main__':
    unittest.main()
