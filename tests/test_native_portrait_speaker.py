import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import native_portrait_speaker as nps


class PortraitSpeakerTests(unittest.TestCase):
    def test_handler_shape(self):
        code = nps.emit()
        self.assertEqual(len(code) % 4, 0)
        self.assertIn((0x0C000000 | nps.PORTRAIT >> 2 & 0x3FFFFFF).to_bytes(4, 'little'), code)
        self.assertIn((0x0C000000 | nps.NAME >> 2 & 0x3FFFFFF).to_bytes(4, 'little'), code)
        self.assertEqual(nps.compile_portrait(b'', 494, 0), (b'', None))   # not a local NPC identity

    def test_stock_contract_and_melzas_portrait(self):
        exe = ROOT / 'game/disc/ALUN_CD.EXE'
        datas = ROOT / 'game/disc/DATA/DATAS.BIN'
        if not exe.exists() or not datas.exists(): self.skipTest('Private stock input unavailable')
        nps.verify(exe.read_bytes())
        data = datas.read_bytes()
        self.assertEqual(nps.portrait_quad(data, 327, 162), (3, 6, 200, 176, 48, 72))
        out, code = nps.compile_portrait(data, 1, 418)   # Melzas is not on map 1
        self.assertEqual(len(code), nps.SIZE); self.assertEqual(code[0], nps.OPCODE)
        self.assertEqual(code[7:], (418).to_bytes(2, 'little'))
        from map_inspector import inspect_map
        inspect_map(out, 1)


if __name__ == '__main__':
    unittest.main()
