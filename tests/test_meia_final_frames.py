"""Meia basic attack: the user's meia-final-1x.png frames all fit the global sheet."""
import sys, unittest
from copy import copy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
DATAS = ROOT / 'game' / 'disc' / 'DATA' / 'DATAS.BIN'


@unittest.skipUnless(DATAS.is_file(), 'private retail DATAS.BIN not present')
class MeiaFinalFramesTests(unittest.TestCase):
    def test_all_frames_fit(self):
        import meia_final_frames as m
        if not m.ART.exists():
            self.skipTest('meia-final-1x.png not present')
        from editor_session import EditSession
        import player_costume as pc
        s = EditSession(DATAS.read_bytes(), None, verify=False); t = copy(s); t.data = bytearray(s.data)
        report = pc.apply_costume(t, basic_attack=True)['meia_final_frames']
        self.assertEqual(report['did_not_fit'], [])
        self.assertEqual(report['replaced'], report['normal'])
        self.assertEqual(report['flash_replaced'], report['flash'])


if __name__ == '__main__':
    unittest.main()
