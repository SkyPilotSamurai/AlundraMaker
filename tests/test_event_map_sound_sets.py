"""Map-only sounds added to the map's own sound set (tools/map_sound_sets.py, 2026-10-23)."""
import struct
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import map_sound_sets as M

EXE = ROOT / 'game/disc/ALUN_CD.EXE'
SOUND = ROOT / 'game/disc/DATA/SOUND.BIN'


@unittest.skipUnless(EXE.exists() and SOUND.exists(), 'no local game files')
class MapSoundSetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exe = EXE.read_bytes(); cls.sound = SOUND.read_bytes()

    def test_nothing_needed_keeps_files_identical(self):
        self.assertIsNone(M.banks_of(self.exe, 60))
        self.assertEqual(M.needed(self.exe, {321: {181}}), [])   # Zoldia's map has set 27
        exe, sound, report, warnings = M.apply(self.exe, self.sound, {321: {181}, 348: {60}})
        self.assertEqual((exe, sound, report, warnings), (self.exe, self.sound, [], []))

    def test_default_cap_leaves_blade_sound_out_with_warning(self):
        self.assertEqual(M.map_sets(self.exe, 348), {55})
        exe, sound, report, warnings = M.apply(self.exe, self.sound, {348: {181}})
        self.assertEqual((exe, sound, report), (self.exe, self.sound, []))
        self.assertEqual(len(warnings), 1)
        self.assertRegex(warnings[0], r'sound 181 .*map 348.*87[0-9]{3} bytes .*limit 80256')

    def test_extended_adds_blade_sound_to_set_55(self):
        exe, sound, report, warnings = M.apply(self.exe, self.sound, {348: {181}}, extended=True)
        rec = dict(M.MAP_TABLES[348])[181]   # in map 348's own data (native_map_sound_table, 2026-10-26)
        self.assertEqual((rec[0], rec[2], rec[6]), (55, 0, 0))
        self.assertEqual(M.banks_of(exe, 181), {27})   # the stock chain is not touched
        h, b, e = M._set_range(exe, 55)
        vab = M._Vab(sound[h:b], sound[b:e])
        self.assertEqual(vab.nprog, rec[1] + 1)
        r = M._set_range(self.exe, 27)
        src = M._Vab(self.sound[r[0]:r[1]], self.sound[r[1]:r[2]])
        tone = src.vh[src.tone_at(0, 1):src.tone_at(0, 1) + 32]
        self.assertEqual(vab.vag(vab.nvag), src.vag(struct.unpack_from('<h', tone, 0x16)[0]))
        o = M._set_range(self.exe, 55)
        old = M._Vab(self.sound[o[0]:o[1]], self.sound[o[1]:o[2]])
        self.assertEqual(vab.vh[0x20:0x20 + 16 * old.nprog], old.vh[0x20:0x20 + 16 * old.nprog])   # stock programs
        self.assertEqual(vab.vh[old.tone_at(0, 0):old.sizes_at()], old.vh[old.tone_at(0, 0):old.sizes_at()])   # stock tones
        self.assertEqual(bytes(vab.vb[:old.used()[1]]), bytes(old.vb[:old.used()[1]]))   # stock samples
        self.assertTrue(all(M.record(exe, i) == M.record(self.exe, i) for i in range(963)))
        M.verify(self.exe, self.sound, exe, sound, {55})   # every other set / music piece intact
        self.assertTrue(report)
        self.assertTrue(any('more than any stock set (80256)' in w and 'Map 348' in w for w in warnings))

    def test_priority_and_shared_program(self):
        # 130 and 95 come from programs with other attributes or the same; authored (0) goes first
        exe, sound, report, warnings = M.apply(self.exe, self.sound, {348: {130: 2, 181: 0, 95: 2}}, extended=True)
        self.assertIn(181, dict(M.MAP_TABLES[348]))
        h, b, e = M._set_range(exe, 55)
        vab = M._Vab(sound[h:b], sound[b:e])
        o = M._set_range(self.exe, 55); old = M._Vab(self.sound[o[0]:o[1]], self.sound[o[1]:o[2]])
        self.assertLessEqual(vab.nprog - old.nprog, 3)
        for n, r in M.MAP_TABLES[348]:
            self.assertLess(r[2], vab.vh[0x20 + 16 * r[1]])   # tone index inside its program
        M.verify(self.exe, self.sound, exe, sound, {55})

    def test_records_beyond_spares_go_below_the_table(self):
        old = M.FREE_RECORDS
        try:
            M.FREE_RECORDS = ()
            exe, sound, report, warnings = M.apply(self.exe, self.sound, {348: {181}}, extended=True)
        finally:
            M.FREE_RECORDS = old
        # records no longer need spare ids or room below the code: map 348 keeps its own
        self.assertEqual(dict(M.MAP_TABLES[348])[181][0], 55)
        self.assertEqual(M.record(exe, 181), M.record(self.exe, 181))
        M.verify_records(self.exe, exe, set(), set())   # every stock id keeps its record
        self.assertTrue(any("record in the map's data" in line for line in report))


class OwnSetTests(unittest.TestCase):
    @unittest.skipUnless(EXE.exists() and SOUND.exists(), 'no local game files')
    def test_own_table_keeps_stock_sets_and_chains(self):
        exe, snd = EXE.read_bytes(), SOUND.read_bytes()
        own = {(1, 5, 9): None}
        t = M._own_table(exe, {483: (78, len(snd), len(snd) + 0x1000)}, len(snd), len(snd) + 0x3000)
        words = struct.unpack(f'<{len(t) // 4}I', t)
        _, stock = M._offsets(exe)
        k = (M.SET_TABLE - M.OFFSETS) // 4
        self.assertEqual(list(words[:155]), list(stock[k:k + 155]))   # sets 0..76 and the end of 76
        self.assertEqual(words[155:], (len(snd), len(snd), len(snd) + 0x1000, len(snd) + 0x3000))

    def test_empty_vab_takes_tones(self):
        if not (EXE.exists() and SOUND.exists()):
            self.skipTest('no local game files')
        exe, snd = EXE.read_bytes(), SOUND.read_bytes()
        h, b, e = M._set_range(exe, 27)
        src = M._Vab(snd[h:b], snd[b:e]); v = M._Vab.empty(snd[h:b])
        p1 = v.add_tone(src, 0, 1, 0); p2 = v.add_tone(src, 0, 2, 0)
        self.assertEqual((p1, p2, v.nprog, v.ntone, v.nvag), ((0, 0), (0, 1), 1, 2, 2))


class HomeRoomTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / 'game/disc/DATA/DATAS.BIN').exists(), 'no local game files')
    def test_home_room_is_an_active_placement(self):
        import object_sound_banks as osb
        osb._HOMES.clear()
        self.assertEqual(osb._first_home(456), 351)   # Roper: 337/338 copies wait on castle scripts (C hooks)
        self.assertEqual(osb._first_home(455), 12)    # Wasp: its first room's copies have no hooks


class CollectorTests(unittest.TestCase):
    @unittest.skipUnless(EXE.exists() and (ROOT / 'assets/engine/maps/321/data.json').exists(), 'no local game files')
    def test_native_program_sounds(self):
        exe = EXE.read_bytes()
        self.assertTrue({183, 185} <= M.native_class_sounds(exe, 509, 321))   # Zorgia's built-in programs

    @unittest.skipUnless(EXE.exists() and SOUND.exists(), 'no local game files')
    def test_copy_comes_from_the_source_set(self):
        exe, snd = EXE.read_bytes(), SOUND.read_bytes()
        def ok(k):
            b = M.banks_of(exe, k) or set()
            return len(b) >= 3 and 55 not in b and all(M.record(exe, i)[10] == 1 and M.record(exe, i)[5] == -1 for i in M.chain(exe, k))
        n = next(k for k in range(1, 500) if ok(k))
        src = sorted(M.banks_of(exe, n))[-1]
        out, _, report, _ = M.apply(exe, snd, {348: {n: (2, src)}}, extended=True)
        if report:
            want = next(M.record(exe, i) for i in M.chain(exe, n) if M.record(exe, i)[0] == src)
            got = dict(M.MAP_TABLES[348])[n]
            self.assertEqual((got[0], got[3]), (55, want[3]))   # same note as the source set's copy


if __name__ == '__main__':
    unittest.main()
