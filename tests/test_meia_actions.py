"""Meia basic attack: every attack/carry/hurt frame is redrawn in Meia's outfit and fits."""
import struct, sys, unittest
from copy import copy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
DATAS = ROOT / 'game' / 'disc' / 'DATA' / 'DATAS.BIN'


@unittest.skipUnless(DATAS.is_file(), 'private retail DATAS.BIN not present')
class MeiaOutfitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from editor_session import EditSession
        import player_costume as pc
        cls.data = DATAS.read_bytes()
        s = EditSession(cls.data, None, verify=False); t = copy(s); t.data = bytearray(s.data)
        cls.report = pc.apply_costume(t, basic_attack=True)['meia_actions']
        cls.out = bytes(t.data)

    def test_every_action_frame_redrawn(self):
        self.assertEqual(self.report['head_not_found'], [])
        self.assertEqual(self.report['replaced'], self.report['image_sets'])
        self.assertNotIn('left_as_alundra', self.report)

    def test_her_palette_in_slot_10(self):
        import meia_actions as ma
        from player_costume import _global_bank
        start, _, _, header = _global_bank(self.out)
        words = list(struct.unpack_from('<16H', self.out, start + header[5] + ma.OUTFIT_PALETTE_SLOT * 32))
        self.assertEqual(words, ma.meia_words())

    def test_normal_frames_use_her_palette(self):
        import meia_actions as ma
        from player_costume import _player_image_sets
        uses, _, _ = _player_image_sets(self.data)
        base = ma._frame_base(self.out)
        for iset in ma.action_image_sets(self.data, set(), ma.ACTION_ANIMATIONS):
            pos = base + iset * 2
            pals = {self.out[pos + 3 + q * 14] for q in range(self.out[pos + 1]) if self.out[pos + 6 + q * 14]}
            self.assertNotIn(17, pals, f'image set {iset} still draws his body palette')


if __name__ == '__main__':
    unittest.main()
