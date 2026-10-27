"""2026-10-22 pages QA: item, money and other game conditions on event pages are compiled into
the presence watcher instead of making the build drop the event; Autorun / Parallel pages are
whole-map controllers."""
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
from new_event_compile import _split_pages, _presence_condition, _native_page_test, _run_controller, validate_new_event
from native_actor_lifecycle import compile_condition_presence_watcher

ITEM = {'type': 'item', 'item_class_id': 'item:herb', 'operator': '>=', 'quantity': 1}
MONEY = {'type': 'money', 'amount': 40, 'value': True}


def graph(*pages):
    return {'id': 'event:1', 'name': 'NPC', 'map_id': 483, 'class_id': 'npc:1',
            'pages': [dict({'conditions': [], 'commands': [], 'class_id': 'npc:1'}, **p) for p in pages]}


class PageConditions(unittest.TestCase):
    def test_item_and_money_pages_are_accepted(self):
        out = _split_pages([graph({}, {'conditions': [ITEM], 'class_id': 'npc:2'}, {'conditions': [MONEY], 'class_id': 'npc:3'})])
        first = _presence_condition(out[0])
        self.assertEqual([b[0][0] for b in first.blockers], ['code', 'code'])
        self.assertEqual(list(_presence_condition(out[1])), [[('code', ITEM)]])

    def test_native_tests(self):
        self.assertEqual(_native_page_test(ITEM, lambda r: 36), [(bytes((0x83, 36, 1)), 4)])
        self.assertEqual(_native_page_test(dict(ITEM, operator='<'), lambda r: 36), [(bytes((0x83, 36, 1)), 3)])
        self.assertEqual(len(_native_page_test(dict(ITEM, operator='=='), lambda r: 36)), 2)
        self.assertEqual(_native_page_test(MONEY, None), [(bytes((0x9A, 0x28, 0x00)), 4)])
        self.assertEqual(_native_page_test(dict(MONEY, value=False), None)[0][1], 3)
        with self.assertRaises(ValueError):
            _native_page_test(dict(ITEM, operator='!='), lambda r: 36)

    def test_watcher_emits_code_tests(self):
        code = compile_condition_presence_watcher([[('code', [(bytes((0x9A, 0x28, 0x00)), 4)])]], 5)
        self.assertIn(bytes((0x9A, 0x28, 0x00, 0x04)), code)

    def test_yes_no_still_refused(self):
        with self.assertRaises(ValueError):
            _presence_condition(graph({'conditions': [{'type': 'yes_no', 'value': True}]}))


class AutorunParallel(unittest.TestCase):
    BODY = bytes((0x9B, 0x01, 0x00))
    LOCK = bytes((0x10, 0x59, 0x81, 0x00))

    def g(self, trigger):
        return {'id': 'e', 'name': 'Auto', 'map_id': 483, 'region': [3, 3, 1, 1], 'class_id': None, 'trigger': trigger,
                'pages': [{'trigger': trigger, 'class_id': None, 'commands': [{'type': 'change_money', 'amount': 1}],
                           'conditions': [{'type': 'switch', 'native_flag_operand': 0x7F0, 'switch_id': 0x7F0, 'value': True}]}]}

    def test_validate_accepts_class_free_autorun_and_parallel(self):
        for t in ('autorun', 'parallel'):
            validate_new_event(self.g(t))

    def test_autorun_locks_runs_once_and_waits_for_the_page_to_end(self):
        code = _run_controller(self.g('autorun'), self.BODY, True, None, None)
        self.assertEqual(code[0], 0)                          # poll: one frame
        self.assertEqual(code[1], 0x31)                       # flag clear -> back to poll
        self.assertIn(self.LOCK + self.BODY + bytes((0x11, 0x00)), code)
        self.assertEqual(code[-1], 0xFF)

    def test_parallel_loops_without_lock(self):
        code = _run_controller(self.g('parallel'), self.BODY, False, None, None)
        self.assertNotIn(self.LOCK, code)
        self.assertEqual(code[-4], 0x02)                      # jump back to poll

    def test_later_page_is_tested_first(self):
        g = self.g('parallel'); g['_blockers'] = [[{'type': 'switch', 'native_flag_operand': 0x7F1, 'switch_id': 0x7F1, 'value': True}]]
        code = _run_controller(g, b'', False, None, None)
        self.assertEqual((code[1], code[6]), (0x31, 0x02))    # later page in force -> back to poll


if __name__ == '__main__':
    unittest.main()
