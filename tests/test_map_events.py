import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from map_events import read_map_events

class MapEventTests(unittest.TestCase):
    def test_four_byte_terminator_does_not_consume_next_section(self):
        raw = bytes.fromhex("0306131781123456") + bytes(4) + b"next"
        records, end = read_map_events(raw, 0, len(raw))
        self.assertEqual(end, 12)
        self.assertEqual(records[0].bank_b_index, 1)
        self.assertEqual(records[0].encode(), raw[:8])
        self.assertEqual(records[0].unknown, bytes.fromhex("123456"))

    def test_truncation_and_section_bounds(self):
        for raw, end in [(b"\1"*7, 7), (b"\1"*8, 8),
                         (bytes(4), 5), (bytes(4), -1)]:
            with self.assertRaises(ValueError):
                read_map_events(raw, 0, end)

    def test_full_table_needs_no_terminator(self):
        raw = bytes.fromhex("0102030481000000") * 64 + b"next"
        records, end = read_map_events(raw, 0, len(raw))
        self.assertEqual(len(records), 64)
        self.assertEqual(end, 512)
