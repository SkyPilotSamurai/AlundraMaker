import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from editor_session import EditSession
from map_text import entries
from map_block_repack import pointers, sections, replace_block
from native_text_allocation import append_local_text
from test_native_script_allocation import fixture


class TextAllocationTests(unittest.TestCase):
    def test_padded_large_pool_keeps_all_old_bytes_and_string_offsets(self):
        original = fixture(); roots = pointers(original)
        block = bytearray(original[roots[2]:roots[3]]); start = sections(block)[6]
        block.extend(b"\0" * 60000)
        values = [256] * 128; values[0] = 0
        struct.pack_into("<128h", block, start, *values)
        block[start + 256:start + 264] = b"#Disuse\0"
        block[start + 40000:start + 40006] = b"opaque"
        original = replace_block(original, 2, block)
        roots = pointers(original); old = original[roots[2]:roots[3]]
        result, report = append_local_text(original, 2, "New")
        after = pointers(result); rebuilt = result[after[2]:after[3]]
        self.assertTrue(report["text_pool_repacked"])
        self.assertEqual(struct.unpack_from("<128h", rebuilt, start)[1:], tuple(values[1:]))
        self.assertEqual(rebuilt[:start], old[:start])
        tail = report["original_payload_tail_offset"]
        self.assertEqual(rebuilt[tail:tail + len(old) - start], old[start:])
        self.assertIn(b"New", [r[2] for r in entries(EditSession(result, verify=False), 2)])
        for map_id in range(483):
            if map_id != 2:
                self.assertEqual(original[roots[map_id]:roots[map_id+1]], result[after[map_id]:after[map_id+1]])

    def test_new_string_round_trip_preserves_other_maps_and_original_text_bytes(self):
        original = fixture(); before = pointers(original)
        result, report = append_local_text(original, 2, "Hi\nAlundra")
        after = pointers(result)
        self.assertEqual(report["text_index"], 0)
        session = EditSession(result, verify=False)
        self.assertIn(b"Hi\\NAlundra", [r[2] for r in entries(session, 2)])
        for m in range(483):
            if m != 2:
                self.assertEqual(original[before[m]:before[m+1]], result[after[m]:after[m+1]])

    def test_referenced_zero_slot_is_not_assumed_unused(self):
        original = fixture(); base = pointers(original)[2]
        # Conservative byte-pattern scanner reserves this reference even though
        # the tiny synthetic bytecode fixture has no third mode byte.
        original[base + 28 + 74:base + 28 + 76] = bytes([0x0D, 0x80])
        result, report = append_local_text(original, 2, "New")
        self.assertEqual(report["text_index"], 1)
        self.assertEqual(struct.unpack_from("<h", result, pointers(result)[2] + 136)[0], 0)

    def test_used_strings_are_not_overwritten_and_invalid_characters_fail(self):
        original = fixture(); base = pointers(original)[2]; start = base + 136
        struct.pack_into("<128h", original, start, *([256] * 128))
        original[start + 256:start + 261] = b"Used\0"
        with self.assertRaisesRegex(ValueError, "unused native text slot"):
            append_local_text(original, 2, "New")
        with self.assertRaises(ValueError):
            append_local_text(fixture(), 2, "a\0b")
        with self.assertRaisesRegex(ValueError, "character set"):
            append_local_text(fixture(), 2, "雪")


if __name__ == "__main__":
    unittest.main()
