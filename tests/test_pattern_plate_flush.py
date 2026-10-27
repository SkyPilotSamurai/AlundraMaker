"""Placed pattern plates: Flush With Floor (default) is a hidden, not solid plate drawn in the floor squares; unticked keeps the original, 2026-10-25."""
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
DATAS = ROOT / 'game/disc/DATA/DATAS.BIN'


@unittest.skipUnless(DATAS.is_file(), 'needs the original DATAS.BIN')
class PlateFlushTests(unittest.TestCase):
    def compile(self, flush):
        from content_database import ContentDatabase
        from editor_session import EditSession
        from event_graph import new_event_graph
        from new_event_compile import compile_new_events
        from native_class_placement import record_cluster
        stock = DATAS.read_bytes()
        db = ContentDatabase(); db.populate_catalogue(stock); db.ensure_pattern_plates()
        defn = next(r for r in db.definitions if r.get('source', {}).get('catalogue_index') == 364 and not r.get('clone_of'))
        star = next(r for r in db.definitions if r.get('source', {}).get('catalogue_index') == 363 and not r.get('clone_of'))
        o = new_event_graph('star:test', 1, 'Star', 6, 4, star['id'])
        g = new_event_graph('plate:test', 1, 'Plate', 6, 2, defn['id']); g['pages'][0]['trigger'] = 'activate'
        g['pages'][0]['commands'] = [{'type': 'wait', 'frames': 1}]
        if not flush: g['native_placement'] = {'plate_flush': False}
        s = EditSession(stock); s.content_database = {'definitions': db.definitions, 'event_graphs': [o, g]}
        c = compile_new_events(s, [o, g])
        old = record_cluster(stock, 1)['entities']; rows = record_cluster(c.data, 1)['entities']
        self.assertEqual(rows[:len(old)], old)                 # the game's own plates unchanged
        return c.data, rows[-1]

    def test_flush_plate_is_hidden_and_drawn_in_the_floor(self):
        import struct
        from local_sprite_import import sprite_assets
        from area_map import grid
        from heal_tile import _View
        data, row = self.compile(True)
        self.assertEqual(row[5] & 0x80, 0x80); self.assertNotEqual(row[6], 364 - 256)
        a = sprite_assets(data, 1, row[6])
        self.assertFalse(struct.unpack_from('<H', data, a['record'] + 0x10)[0] & 0x80)   # not solid
        self.assertTrue(all(data[q + 6:q + 14] == bytes(8) for q in a['quads']))          # not drawn
        old = grid(_View(DATAS.read_bytes()), 1); new = grid(_View(data), 1)
        w = old[0]
        for x, y in ((6, 1), (7, 1), (6, 2), (7, 2)):                                     # plate squares redrawn
            self.assertNotEqual(old[2][y * w + x]['values'][4], new[2][y * w + x]['values'][4])

    def test_unticked_plate_is_original(self):
        data, row = self.compile(False)
        self.assertEqual((row[5] & 0x80, row[6]), (0x80, 364 - 256))

if __name__ == '__main__':
    unittest.main()
