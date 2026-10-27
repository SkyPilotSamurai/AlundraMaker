import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
from native_flags import locate_flag


class NativeFlagTests(unittest.TestCase):
    def test_sluice_and_second_bank(self):
        a = locate_flag(0x058D)
        self.assertEqual((a['word_address'], a['word_mask']), (0x801DD3E4, 0x2000))
        self.assertEqual((a['byte_address'], a['byte_mask']), (0x801DD3E5, 0x20))
        self.assertEqual(locate_flag(0x8000)['byte_address'], 0x801E6378)

    def test_all_unsigned_operands(self):
        for code in range(65536):
            x = locate_flag(code)
            base = 0x801E6378 if code >= 32768 else 0x801DD334
            self.assertEqual(x['byte_address'], base + (code & 32767) // 8)
            self.assertEqual(x['byte_mask'], 1 << (code % 8))

    def test_bounds(self):
        for code in (-1,65536):
            with self.assertRaises(ValueError):
                locate_flag(code)
