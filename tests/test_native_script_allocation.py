import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from native_script_allocation import append_native_process, script_tables
from map_block_repack import pointers, sections
from map_inspector import inspect_map


def fixture():
    # One tiny structurally valid map repeated 483 times, aligned like DATAS.
    section = bytearray(108)
    header = [76, 80, 80, 48, 52, 56, 60, 62, 66, 68, 70, 72]
    struct.pack_into("<12I", section, 0, *header)
    # A zero, B zero + root14, C/D/E/F each zero; then native End+padding.
    struct.pack_into("<7h", section, 60, 0, 0, 14, 0, 0, 0, 0)
    section[74:76] = b"\xff\xff"
    # One existing map trigger at (1,1), keeping terminator and asset tail.
    section[80:88] = bytes([1, 1, 1, 1, 129, 0, 0, 0])
    section[92:] = bytes(range(16))
    block = bytearray(2048)
    struct.pack_into("<7I", block, 0, 28, 28, 28, 28, 136, 136, 136)
    block[28:136] = section
    data = bytearray(2048) + block * 483
    struct.pack_into("<484I", data, 0x28, *range(2048, 2048 * 485, 2048))
    return data


class ScriptAllocationTests(unittest.TestCase):
    def test_earlier_f_code_is_preserved_after_adding_b_root(self):
        section=bytearray(100)
        # B points later, while F points to the beginning of the code payload.
        struct.pack_into('<12I',section,0,100,100,100,48,48,48,60,62,66,68,70,72)
        struct.pack_into('<9h',section,60,0,0,32,0,0,0,0,18,26)
        section[78:]=b'\xff'*22
        _,tables,code,start=script_tables(section)
        self.assertEqual(start,78);self.assertEqual(tables[-1],[0,18,26])
        self.assertEqual(code,b'\xff'*22)

    def test_appended_b_process_preserves_stock_payload_and_other_maps(self):
        original = fixture()
        result, report = append_native_process(original, 2, "B", b"\x05\xfc\x7f\xff")
        before = pointers(original); after = pointers(result)
        oldblock = original[before[2]:before[3]]
        newblock = result[after[2]:after[3]]
        oldsec = oldblock[28:136]
        newsec = newblock[28:sections(newblock)[4]]
        self.assertEqual(newsec[48:108], oldsec[48:])
        header, tables, code, code_start = script_tables(newsec)
        self.assertEqual(report["root_index"], 2)
        self.assertEqual(tables[1][:2], [0, 16])
        self.assertEqual(newsec[header[6] + tables[1][2]:][:4], b"\x05\xfc\x7f\xff")
        self.assertEqual(code[:2], b"\xff\xff")
        self.assertEqual(len(inspect_map(result, 2)["events"]), 1)
        for m in range(483):
            if m != 2:
                self.assertEqual(original[before[m]:before[m+1]], result[after[m]:after[m+1]])

    def test_empty_f_table_reserves_index_zero(self):
        section = bytearray(108)
        struct.pack_into("<12I", section, 0, 76, 80, 80, 48, 52, 56, 60, 62, 66, 68, 70, 74)
        struct.pack_into("<7h", section, 60, 0, 0, 14, 0, 0, 0, 0)
        section[74:76] = b"\xff\xff"
        header, tables, _, _ = script_tables(section)
        self.assertEqual(tables[-1], [])

    def test_missing_code_boundary_and_unterminated_new_process_fail_closed(self):
        with self.assertRaises(ValueError):
            script_tables(bytes(108))
        with self.assertRaisesRegex(ValueError, "End process"):
            append_native_process(fixture(), 0, "B", b"\x05\x01\x00")


if __name__ == "__main__":
    unittest.main()
