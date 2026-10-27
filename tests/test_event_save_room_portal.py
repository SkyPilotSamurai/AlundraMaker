"""Save Room Portal (tools/save_portal.py; docs/2026-10-23-save-room-portal.txt)."""
import struct
import sys
import unittest
from pathlib import Path
from unittest import mock
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
for _m in ['tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog', 'PIL.ImageTk', 'zoom_canvas']:
    sys.modules.setdefault(_m, mock.MagicMock())
import save_portal as S

DATAS = ROOT / 'game/disc/DATA/DATAS.BIN'


def _run(code, start=0, player=(0, 0, 0), limit=40):
    """Follow the B program's jumps (00 02 03 04 37 3B 53 FF) for one player tile; returns the 53 operands."""
    pc, cond = start, 0
    for _ in range(limit):
        op = code[pc]
        if op == 0x00: pc += 1
        elif op == 0x37: pc += 2
        elif op == 0x3B:
            x1, x2, y1, y2, z1, z2 = code[pc + 1:pc + 7]
            cond = int(x1 <= player[0] <= x2 and y1 <= player[1] <= y2 and z1 <= player[2] <= z2); pc += 7
        elif op in (2, 3, 4):
            rel = struct.unpack_from('<h', code, pc + 1)[0]
            pc = pc + rel if op == 2 or (op == 3 and cond) or (op == 4 and not cond) else pc + 3
        elif op == 0x53: return struct.unpack_from('<H5B', code, pc + 1)
        else: raise AssertionError(hex(op))
    return None


class PortalBytes(unittest.TestCase):
    def test_swirl_entry_matches_save_room_452(self):
        self.assertEqual(S.swirl_entry(52, 60, 14, 17, 1).hex(), '0000333b40181d2202000000')

    def test_warp_flags_match_stock_rooms(self):
        self.assertEqual((0 << 12) | S.WARP_LOW, 85)      # 452-460
        self.assertEqual((1 << 12) | S.WARP_LOW, 4181)    # 470
        self.assertEqual(((S.WARP_LOW & 0x70) >> 4, S.WARP_LOW & 15), (5, 5))

    def test_rect_is_two_by_two_above_the_event_tile(self):
        self.assertEqual(S.rect(14, 17), (14, 16, 15, 17))

    def test_mode_defaults_to_previous(self):
        self.assertEqual(S.mode_of({}), 'previous')
        self.assertEqual(S.mode_of(None), 'previous')
        self.assertEqual(S.mode_of({'warp_mode': 'destination'}), 'destination')

    def test_program_picks_route_by_arrival_and_sends_back(self):
        routes = [([26, 42, 26, 42], (483, 26, 43, 10)), ([27, 41, 27, 42], (484, 2, 19, 2))]
        code = S.back_program((26, 43, 27, 44), 10, routes)
        self.assertEqual(code[-1], 0xFF)
        self.assertIsNone(_run(code, 0, (26, 42, 10), 12))   # no warp while he is off the panel
        # the arrival tile picks the loop; then he steps on the panel
        for arrival, want in (((26, 42, 10), (483, 26, 43, 10, 5, 74)), ((27, 41, 10), (484, 2, 19, 2, 5, 74))):
            pc = 0
            for _ in range(10):                          # find the route loop for this arrival
                op = code[pc]
                if op == 0x3B:
                    x1, x2, y1, y2, z1, z2 = code[pc + 1:pc + 7]
                    cond = x1 <= arrival[0] <= x2 and y1 <= arrival[1] <= y2 and z1 <= arrival[2] <= z2; pc += 7
                elif op == 3:
                    if cond: pc += struct.unpack_from('<h', code, pc + 1)[0]; break
                    pc += 3
                else: pc += 1
            self.assertEqual(_run(code, pc, (26, 44, 10)), want)
        self.assertEqual(_run(code, 0, (27, 43, 10)), routes[0][1] + (5, 74))   # first seen on the panel


@unittest.skipUnless(DATAS.exists(), 'no game files')
class StockRooms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = DATAS.read_bytes()

    def test_previous_location_matches_the_stock_way_back(self):
        # each stock save room's own record: (map, x, y); four of them are exactly what the rule gives
        for room, back in ((452, (62, 18, 16)), (453, (22, 26, 31)), (454, (74, 4, 13)), (455, (26, 25, 27))):
            [e] = S.entrances(self.data, room)
            self.assertEqual((e['map'],) + S.return_point(self.data, e['map'], e['box'], e['facing'])[:2], back)

    def test_install_writes_panel_swirl_and_records(self):
        from native_class_placement import record_cluster
        g = {'id': 'e', 'name': 'P', 'map_id': 452, 'region': [14, 17, 1, 1], 'native_placement': {}}
        data, [report] = S.install(self.data, [g])
        self.assertEqual(report['mode'], 'previous')
        self.assertEqual(report['returns'], [[62, 18, 16, 6]])
        effects = record_cluster(data, 452)['effects']
        self.assertEqual(effects[-16:-4].hex(), '0000333b40181d2202000000')
        rows = S._portals(data, 452)[1]
        new = [p for i, _, p in rows if i in report['warp_indices']]
        self.assertEqual({(p.x1, p.y1) for p in new}, {(14, 16), (15, 16), (14, 17), (15, 17)})
        self.assertTrue(all((p.destination_map, p.destination_x, p.destination_y, p.flags) == (62, 18, 16, 85) for p in new))

    def test_warp_panel_tiles_are_warp_squares_like_stock(self):
        from heal_tile import add_warp_data, _View
        from area_map import grid
        data = bytearray(self.data)
        add_warp_data(data, 453, (20, 10, 21, 11), {'map': 22, 'x': 26, 'y': 31, 'z': 2})
        w, h, cells = grid(_View(data), 453)
        for x, y in ((20, 10), (21, 10), (20, 11), (21, 11)):
            o = cells[y * w + x]['offset']
            self.assertEqual((data[o] & 0x04, data[o + 1] & 0x80), (0x04, 0x80))
        sw, sh, stock = grid(_View(self.data), 452)
        o = stock[16 * sw + 14]['offset']
        self.assertEqual((self.data[o] & 0x04, self.data[o + 1] & 0x80), (0x04, 0x80))   # stock panel

    def test_destination_mode_needs_a_destination(self):
        g = {'id': 'e', 'name': 'P', 'map_id': 452, 'region': [14, 17, 1, 1], 'native_placement': {'warp_mode': 'destination'}}
        with self.assertRaises(ValueError):
            S.install(self.data, [g])
        g['native_placement']['warp_to'] = {'map': 22, 'x': 26, 'y': 31, 'z': 2}
        data, [report] = S.install(self.data, [g])
        self.assertEqual(report['warp_to'], [22, 26, 31, 2])


class DatabaseRow(unittest.TestCase):
    def test_ensure_save_portal_is_an_object(self):
        from content_database import ContentDatabase
        from types import SimpleNamespace
        db = SimpleNamespace(definitions=[])
        db.new = lambda kind, name: db.definitions.append({'id': 'object:1', 'kind': kind, 'name': name}) or db.definitions[-1]
        row = ContentDatabase.ensure_save_portal(db)
        self.assertEqual((row['kind'], row['name'], row['source']['variant']), ('object', 'Save Room Portal', 'save_portal'))
        self.assertIs(ContentDatabase.ensure_save_portal(db), row)
        self.assertTrue(S.portal_of(row))


if __name__ == '__main__':
    unittest.main()
