import os, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from cd_sector import mode2_form1, mode2_form1_many


def sector(seed):
    s = bytearray(2352)
    s[0:12] = b'\x00' + b'\xff' * 10 + b'\x00'
    s[12:15] = bytes((seed & 0xFF, (seed >> 8) & 0xFF, 2)); s[15] = 2
    s[16:20] = s[20:24] = b'\x00\x00\x08\x00'
    s[24:2072] = os.urandom(2048)
    return s


class ManySectors(unittest.TestCase):
    def test_same_as_one_by_one(self):
        rows = [sector(i) for i in range(64)]
        want = [bytes(mode2_form1(bytearray(r))) for r in rows]
        got = [bytes(r) for r in mode2_form1_many([bytearray(r) for r in rows])]
        self.assertEqual(want, got)


if __name__ == "__main__":
    unittest.main()
