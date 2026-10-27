import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from new_event_compile import _expand_text_questions


class TextQuestionTests(unittest.TestCase):
    def test_ask_question_becomes_text_then_branch(self):
        yes, no = {'type': 'wait', 'frames': 1}, {'type': 'wait', 'frames': 2}
        graphs = [{'pages': [{'commands': [{'type': 'ask_question', 'text': 'Q?', 'then': [yes], 'else': [no]}]}]}]
        rows = _expand_text_questions(graphs)[0]['pages'][0]['commands']
        self.assertEqual([r['type'] for r in rows], ['show_dialogue', 'if'])
        self.assertNotIn('then', rows[0])
        self.assertEqual(rows[1]['condition'], {'type': 'yes_no', 'value': True})
        self.assertEqual((rows[1]['then'], rows[1]['else']), ([yes], [no]))
        self.assertEqual(graphs[0]['pages'][0]['commands'][0]['type'], 'ask_question')   # project left untouched

    def test_nested_question_and_plain_text(self):
        inner = {'type': 'ask_question', 'text': 'Again?', 'then': [], 'else': []}
        graphs = [{'pages': [{'commands': [{'type': 'show_dialogue', 'text': 'Hi'},
                                           {'type': 'if', 'condition': {'type': 'random', 'percent': 50}, 'then': [inner], 'else': []}]}]}]
        rows = _expand_text_questions(graphs)[0]['pages'][0]['commands']
        self.assertEqual(rows[0], {'type': 'show_dialogue', 'text': 'Hi'})
        self.assertEqual([r['type'] for r in rows[1]['then']], ['show_dialogue', 'if'])

    def test_validation_accepts_ask_question(self):
        from event_graph import new_event_graph, validate_event_graph
        event = new_event_graph('q', 0)
        event['pages'][0]['commands'] = [{'type': 'ask_question', 'text': 'Q?', 'then': [{'type': 'wait', 'frames': 1}], 'else': []}]
        validate_event_graph(event)


if __name__ == '__main__':
    unittest.main()
