import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from native_dialogue_wait import analyse, dialogue_wait_step, compile_dialogue_wait


class DialogueWaitTests(unittest.TestCase):
    def test_flags_wait_and_continue_are_not_inverted(self):
        self.assertEqual(compile_dialogue_wait(), b'\x39')
        for flags in (4, 5, 7, 0xFFFFFFFF): self.assertEqual(dialogue_wait_step(flags), 0)
        for flags in (0, 1, 2, 8): self.assertEqual(dialogue_wait_step(flags), 1)
        for flags in (True, -1, 0x100000000):
            with self.assertRaises(ValueError): dialogue_wait_step(flags)

    def test_exact_native_evidence(self):
        path = ROOT / 'game/disc/ALUN_CD.EXE'
        if not path.exists(): self.skipTest('Private stock input unavailable')
        report = analyse(path.read_bytes())
        self.assertEqual(report['handler'], '8003EEF0')
        self.assertFalse(report['runtime_verified'])


if __name__ == '__main__': unittest.main()
