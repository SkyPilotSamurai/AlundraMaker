"""Self-contained database classes (tools/class_capture.py, stock_donors, map_sound_sets; 2026-10-23)."""
import struct
import sys
import unittest
from pathlib import Path
from unittest import mock
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import class_capture
import map_sound_sets as M
import stock_donors

EXE = ROOT / 'game/disc/ALUN_CD.EXE'
SOUND = ROOT / 'game/disc/DATA/SOUND.BIN'
HAVE_CAPTURE = class_capture.load() is not None


class DonorMapTests(unittest.TestCase):
    def test_placed_class_maps_are_donor_maps(self):
        definitions = {'enemy:x': {'id': 'enemy:x', 'kind': 'enemy', 'source': {'catalogue_index': 456, 'observed_maps': [9]}},
                       'enemy:y': {'id': 'enemy:y', 'kind': 'enemy', 'source': {'catalogue_index': 455}}}
        graphs = [{'map_id': 483, 'pages': [{'class_id': 'enemy:x'}]}]
        with mock.patch.object(class_capture, 'maps_of', side_effect=lambda c: {456: [337, 351], 455: [14]}[c]):
            maps = stock_donors.donor_maps(graphs, definitions)
        self.assertTrue({337, 351, 9} <= maps)
        self.assertNotIn(14, maps)   # not placed
        self.assertTrue(stock_donors.DONOR_MAPS <= maps)
        self.assertTrue({2, 12, 22, 54, 110, 111, 136, 151, 226} <= stock_donors.DONOR_MAPS)

    def test_original_prefers_compiled_projects_export_original(self):
        class S: pass
        s = S(); s.original = b'compiled'; s.export_original = b'stock'
        self.assertEqual(stock_donors.original_of(s), b'stock')
        s.export_original = None
        self.assertEqual(stock_donors.original_of(s), b'compiled')


@unittest.skipUnless(HAVE_CAPTURE and EXE.exists(), 'no class capture / game files')
class CaptureTests(unittest.TestCase):
    def test_capture_matches_reading_the_original_maps(self):
        import object_sound_banks as osb
        exe = EXE.read_bytes()
        for c in (456, 428, 455, 335, 509, 418, 297):
            e = class_capture.entry(c)
            self.assertTrue(e['maps'])
            for m, h in e['homes'].items():
                m = int(m)
                self.assertEqual(h['list'], osb._class_sounds(c, m))
                self.assertEqual(set(h['native']), M._native_class_sounds(exe, c, m))
                self.assertEqual(h['set'], struct.unpack_from('<i', exe, M._f(exe, 0x800C8B90) + 4 * m)[0])

    def test_script_sounds_only_from_the_class_own_placement(self):
        import object_sound_banks as osb
        # Flame (319) in room 140: the hook-free home placement (17) runs no program; 476 / 477
        # belong to the hooked flame 140/2 (C/D 130), not to the class placed without hooks
        self.assertEqual(class_capture.home(319, 140)['entity'], 17)
        self.assertNotIn(477, class_capture.sounds(319, 140))
        self.assertTrue({476, 477} <= set(osb._class_sounds(319, 140, 2)))

    def test_active_homes(self):
        self.assertEqual(class_capture.active_home(456), 351)   # Roper: 337/338 wait on castle scripts
        self.assertEqual(class_capture.active_home(428), 351)   # Red Reaper
        self.assertEqual(class_capture.active_home(455), 12)    # Wasp

    def test_home_set_comes_from_the_original_table(self):
        # a built executable whose table entry for the home room changed (a boss placed there)
        exe = bytearray(EXE.read_bytes())
        struct.pack_into('<i', exe, M._f(exe, 0x800C8B90) + 4 * 351, 27)
        self.assertEqual(M.home_sound_set(bytes(exe), 456, 351), class_capture.home_set(456, 351))
        self.assertNotEqual(M.home_sound_set(bytes(exe), 456, 351), 27)

    def test_captured_samples_match_sound_bin(self):
        import hashlib
        sound = SOUND.read_bytes(); exe = EXE.read_bytes()
        for s in class_capture.home(456, 351)['sounds']:
            r = s['record']; h, b, e = M._set_range(exe, r[0])
            vab = M._Vab(sound[h:b], sound[b:e])
            tone = vab.vh[vab.tone_at(r[1], r[2]):vab.tone_at(r[1], r[2]) + 32]
            self.assertEqual(bytes(tone).hex(), s['tone_hex'])
            self.assertEqual(hashlib.sha1(vab.vag(struct.unpack_from('<h', tone, 0x16)[0])).hexdigest(), s['sample_sha1'])
            self.assertTrue((class_capture.SOUNDS / f"{s['sample_sha1']}.vag").exists())


@unittest.skipUnless(EXE.exists() and SOUND.exists(), 'no local game files')
class SoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exe = EXE.read_bytes(); cls.sound = SOUND.read_bytes()

    def test_identical_sample_is_shared(self):
        # set 27's tone for 181 added twice to set 55: the second tone reuses the sample
        r = M._set_range(self.exe, 27); src = M._Vab(self.sound[r[0]:r[1]], self.sound[r[1]:r[2]])
        o = M._set_range(self.exe, 55); vab = M._Vab(self.sound[o[0]:o[1]], self.sound[o[1]:o[2]])
        rec = M.record(self.exe, 181)
        vab.add_tone(src, rec[1], rec[2])
        after_one = (vab.nvag, len(vab.vb))
        p, t = vab.add_tone(src, rec[1], rec[2])
        self.assertEqual((vab.nvag, len(vab.vb)), after_one)
        tone = vab.vh[vab.tone_at(p, t):vab.tone_at(p, t) + 32]
        self.assertEqual(struct.unpack_from('<h', tone, 0x16)[0], after_one[0])

    def test_multi_tone_sound_keeps_its_tones_together(self):
        # 293 (Melzas) plays two consecutive tones (record +0x14 = 2)
        rec = M.record(self.exe, 293); self.assertEqual(rec[10], 2)
        r = M._set_range(self.exe, rec[0]); src = M._Vab(self.sound[r[0]:r[1]], self.sound[r[1]:r[2]])
        o = M._set_range(self.exe, 55); vab = M._Vab(self.sound[o[0]:o[1]], self.sound[o[1]:o[2]])
        p, t = vab.add_tone(src, rec[1], rec[2], None, rec[10])
        for k in range(2):
            a = vab.vh[vab.tone_at(p, t + k):vab.tone_at(p, t + k) + 32]
            b = src.vh[src.tone_at(rec[1], rec[2] + k):src.tone_at(rec[1], rec[2] + k) + 32]
            self.assertEqual(bytes(a[:0x14]), bytes(b[:0x14]))
            self.assertEqual(vab.vag(struct.unpack_from('<h', a, 0x16)[0]), src.vag(struct.unpack_from('<h', b, 0x16)[0]))

    def test_uncopyable_reasons(self):
        self.assertIn('plays nothing', M._not_copyable(M.record(self.exe, 256)))
        self.assertIn('2 tones', M._not_copyable(M.record(self.exe, 293), multi_tone=False))
        self.assertIsNone(M._not_copyable(M.record(self.exe, 293)))

    def test_record_gap_option(self):
        exe = bytes(self.exe)
        load = struct.unpack_from('<I', exe, 0x18)[0]
        e0, _, _ = M._prepend_records(exe, 10, None, 0)
        e8, _, _ = M._prepend_records(exe, 10, None, 0x800)
        self.assertEqual(load - struct.unpack_from('<I', e0, 0x18)[0], 0x800)
        self.assertEqual(load - struct.unpack_from('<I', e8, 0x18)[0], 0x1000)

    def test_warning_names_the_class_and_map(self):
        M.OWNERS.clear(); M._owner(348, 181, 'Red Reaper')
        _, _, _, warnings = M.apply(self.exe, self.sound, {348: {181}})
        self.assertRegex(warnings[0], r'sound 181 .* of Red Reaper on map 348 not added')
        M.OWNERS.clear()


if __name__ == '__main__':
    unittest.main()
