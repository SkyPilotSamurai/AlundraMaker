"""2026-10-22: database thumbnails of semi-transparent sprite pieces (Giant Slime body,
sheet 0x1B = additive) were drawn opaque and too dark."""
import struct, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from entity_preview import EntityPreview


class Fake:
    palette_bytes = EntityPreview.palette_bytes

    def __init__(self, words):
        self.start = 0; self.header = [0, 0, 0, 0, 0, 0, 32]
        self.data = struct.pack('<16H', *words)

    def read(self, fmt, pos):
        return struct.unpack_from('<' + fmt, self.data, pos)


WORDS = [0, 0x9864, 0x1463] + [0] * 13   # STP grey-blue, non-STP colour


class SemiPalette(unittest.TestCase):
    def test_opaque_sheet_unchanged(self):
        p = Fake(WORDS).palette_bytes(0, 0x03)
        self.assertEqual(p[7], 255); self.assertEqual(p[3], 0)

    def test_additive_is_brightness_alpha(self):
        f = Fake(WORDS); base = f.palette_bytes(0); p = f.palette_bytes(0, 0x1B)
        r, g, b, a = p[4:8]; m = max(base[4:7])
        self.assertEqual(a, m); self.assertEqual(max(r, g, b), 255)
        for over_black, added in zip((r * a // 255, g * a // 255, b * a // 255), base[4:7]):
            self.assertLessEqual(abs(over_black - added), 2)
        self.assertEqual(p[8:12], base[8:12])   # no STP bit: opaque as before

    def test_half_blend_alpha_128(self):
        self.assertEqual(Fake(WORDS).palette_bytes(0, 0x0B)[7], 128)


if __name__ == '__main__':
    unittest.main()
