import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from entity_records import read_entities

class EntityTests(unittest.TestCase):
    def test_layout_and_nonzero_terminator_prefix(self):
        raw = bytes(range(20))
        records, end = read_entities(raw + b"XY\0\0next", 0, 28)
        self.assertEqual(end, 24)
        self.assertEqual(records[0].encode(), raw)
        self.assertEqual(records[0].position_raw, (7,8,9))
        self.assertEqual(records[0].programs["C"], 12)
        self.assertEqual(records[0].contents, 0x1312)

    def test_bounds(self):
        for raw, end in [(b"\1"*19,19), (b"\1"*20,20), (bytes(4),5)]:
            with self.assertRaises(ValueError):
                read_entities(raw, 0, end)

    def test_full_table(self):
        records, end = read_entities(b"\1"*2560, 0, 2560)
        self.assertEqual(len(records),128)
        self.assertEqual(end,2560)
