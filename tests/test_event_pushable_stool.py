"""Stool (Pushable) (tools/native_pushable_stool.py; docs/2026-10-23-pushable-stool.txt)."""
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
for _m in ['tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.filedialog', 'PIL.ImageTk', 'zoom_canvas']:
    sys.modules.setdefault(_m, mock.MagicMock())
import native_pushable_stool as S

DATAS = ROOT / 'game/disc/DATA/DATAS.BIN'
SIZE = {0x00: 1, 0x02: 3, 0x03: 3, 0x06: 3, 0x09: 2, 0x1A: 2, 0x1F: 3, 0x36: 3, 0x37: 2, 0x57: 9, 0x6E: 1, 0xBD: 3, 0xFF: 1}


def run(code, facing, blocked=False):
    """Follow the C program for one push (flag already set): the ops it runs until it clears the flag."""
    order = ('down', 'up', 'left', 'right')
    pc, cond, ran = 0, 0, []
    for _ in range(80):
        op = code[pc]; ran.append(code[pc:pc + SIZE[op]])
        if op == 0x06: return ran
        if op == 0x57: pc += struct.unpack_from('<h', code, pc + 1 + 2 * order.index(facing))[0]; continue
        if op == 0x6E: cond = int(blocked)
        if op in (0x02, 0x03) and (op == 0x02 or cond):
            pc += struct.unpack_from('<h', code, pc + 1)[0]; continue
        pc += SIZE[op]
    raise AssertionError('no end')


def end_pc(code, facing, blocked=False):
    """Where one push ends (the offset of the flag clear it reaches)."""
    order = ('down', 'up', 'left', 'right')
    pc, cond = 0, 0
    for _ in range(80):
        op = code[pc]
        if op == 0x06: return pc
        if op == 0x57: pc += struct.unpack_from('<h', code, pc + 1 + 2 * order.index(facing))[0]; continue
        if op == 0x6E: cond = int(blocked)
        if op in (0x02, 0x03) and (op == 0x02 or cond):
            pc += struct.unpack_from('<h', code, pc + 1)[0]; continue
        pc += SIZE[op]
    raise AssertionError('no end')


def moves(ran):
    return [(r[1], struct.unpack_from('<H', r, 1)[0]) for r in ran if r[0] in (0x09, 0x1F)]


class Programs(unittest.TestCase):
    def test_talk_sets_the_flag_like_stock(self):
        self.assertEqual(S.talk_program(0x800B).hex(), '050b80ff')   # stock map 137 entity 2 F

    def test_each_facing_moves_one_tile_that_way(self):
        code = S.tick_program(0x8780)
        for facing, (direction, pixels) in {'down': (0, 16), 'up': (0x10, 16), 'left': (8, 24), 'right': (0x18, 24)}.items():
            ran = run(code, facing)
            self.assertEqual([r[0] for r in ran if r[0] in (0x09, 0xBD, 0x1A, 0x1F)], [0x09, 0xBD, 0x1A, 0x1F, 0x1A])
            self.assertEqual(ran[[r[0] for r in ran].index(0x09)][1], direction)
            self.assertEqual(ran[[r[0] for r in ran].index(0x1F)][1:].hex(), struct.pack('<H', pixels).hex())
            self.assertEqual(ran[-1], b'\x06\x80\x87')

    def test_program_loops_back_and_ends(self):
        code = S.tick_program(0x8781)
        self.assertEqual(code[-1], 0xFF)
        self.assertEqual(code[-4], 0x02)
        self.assertEqual(len(code) - 4 + struct.unpack_from('<h', code, len(code) - 3)[0], 2)   # back to the wait

    def test_directions_not_ticked_do_nothing(self):
        code = S.tick_program(0x8780, ['up', 'down'])
        for facing in ('left', 'right'):
            self.assertEqual([r[0] for r in run(code, facing)[3:]], [0x57, 0x06])

    def test_options_default(self):
        self.assertEqual(S.allowed({}), ['down', 'up', 'left', 'right'])
        self.assertEqual(S.allowed({'push_directions': ['right', 'up']}), ['up', 'right'])
        self.assertEqual(S.allowed({'push_directions': []}), [])
        self.assertIsNone(S.target_of({}))
        self.assertEqual(S.target_of({'target_tile': {'x': 43, 'y': 46}}), (43, 46))
        with self.assertRaises(ValueError):
            S.target_of({'target_tile': {'x': 200, 'y': 1}})

    def test_move_once_rests_after_a_real_move(self):
        code = S.tick_program(0x8780, once=True)
        clear = bytes((0x06, 0x80, 0x87))
        rest = code.rindex(clear)
        self.assertEqual(code[rest + 3:rest + 7].hex(), '0002ffff')   # yield; jump back to the yield
        self.assertEqual(end_pc(code, 'right'), rest)                  # moved: rests
        self.assertEqual(end_pc(code, 'right', blocked=True), code.index(clear))   # blocked: waits again
        self.assertEqual(end_pc(code, 'left'), rest)

    def test_target_tile_on_and_off(self):
        on, off = bytes.fromhex('bd0100'), bytes.fromhex('bd0200')
        state = (bytes.fromhex('e10000'), bytes.fromhex('e20100'), bytes.fromhex('e20000'))
        code = S.tick_program(0x8780, target=(43, 46), on=on, off=off, state=state)
        box = bytes.fromhex('07802b2b2e2e00ff')                       # this stool inside tile 43,46 (any height)
        self.assertEqual(code[:2].hex(), '3701')
        self.assertEqual(code[2:10], box)                              # on entering the map
        self.assertEqual(code.count(box), 2)                           # and after a move
        self.assertEqual(code.count(on), 2); self.assertEqual(code.count(off), 2)
        self.assertEqual(code.count(bytes((0x6E,))), 4)
        self.assertEqual(code[-1], 0xFF)

    def test_step_on_switches(self):
        plain = S.tick_program(0x8780)
        self.assertNotIn(bytes.fromhex('638000'), plain)
        code = S.tick_program(0x8780, switches=[5, 200])
        self.assertIn(bytes.fromhex('63800040'), code)                 # may ride (clear 0x4000)
        self.assertEqual(code.count(bytes.fromhex('a905')), 4)         # blocked by switch template 5: hop
        self.assertNotIn(bytes((0xA9, 200)), code)                     # not a template selector
        self.assertEqual(code.count(bytes((0x1B,)) + (S.HOP_FORCE).to_bytes(2, 'little') + bytes((0x37, S.HOP_RISE))), 4)
        self.assertIn(bytes.fromhex('4385'), code); self.assertIn(bytes.fromhex('aa81'), code)
        self.assertEqual(code.count(bytes.fromhex('4386')), 2)
        self.assertEqual(code[-1], 0xFF)

    def test_flags_per_map(self):
        counts = {}
        self.assertEqual([S.next_flag(494, counts), S.next_flag(494, counts), S.next_flag(495, counts)], [0x8780, 0x8781, 0x8780])
        counts[1] = S.MAX_PER_MAP
        with self.assertRaises(ValueError):
            S.next_flag(1, counts)


class DatabaseRow(unittest.TestCase):
    def test_row_is_a_sanctuary_stool_object(self):
        from content_database import ContentDatabase
        base = {'id': 'object:0001', 'kind': 'object', 'name': 'Tri-Color Switch (Red)',
                'source': {'catalogue_index': 383, 'variant': 'tricolor', 'default_facing': 'down', 'lit_color': 'red', 'observed_maps': [75, 137]}}
        db = SimpleNamespace(definitions=[base])
        db.new = lambda kind, name, template_id=None: db.definitions.append({'id': 'object:0002', 'kind': kind, 'name': name, 'clone_of': template_id, 'source': {}}) or db.definitions[-1]
        row = ContentDatabase.ensure_pushable_stool(db)
        self.assertEqual((row['kind'], row['name']), ('object', 'Stool (Pushable)'))
        self.assertEqual(row['source']['variant'], 'push_stool')
        self.assertEqual(row['source']['fixed_donor'], [137, 2])
        self.assertEqual(row['source']['observed_maps'][0], 137)
        self.assertNotIn('default_facing', row['source'])
        self.assertIs(ContentDatabase.ensure_pushable_stool(db), row)
        self.assertTrue(S.is_stool(row))
        self.assertEqual(base['source']['variant'], 'tricolor')


@unittest.skipUnless(DATAS.exists(), 'no game files')
class StockStool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from editor_session import EditSession
        cls.session = EditSession.readonly(DATAS.read_bytes())

    def test_donor_record_and_programs(self):
        from native_class_placement import record_cluster
        from event_editor import script_roots
        raw = record_cluster(self.session.data, 137)['entities'][2]
        self.assertEqual(raw[6] + (256 if raw[5] & 128 else 0), 383)
        self.assertEqual(raw[10:16].hex(), '820083000082')
        roots = script_roots(self.session, 137)
        f = roots['F 2'][0]; c = roots['C 3'][0]
        self.assertEqual(self.session.data[f:f + 4].hex(), '050b80ff')
        stock = bytes(self.session.data[c:c + 170])
        # the stock right push: face right, sound 311, animation 4, wait moved 24 or blocked
        self.assertIn(bytes.fromhex('0918bd37011a041f1800'), stock)
        self.assertIn(bytes.fromhex('0908bd37011a041f1800'), stock)
        self.assertIn(bytes.fromhex('574b004b0023000a00'), stock)   # 57: down, up -> no move; left, right

    def test_push_animation_moves_in_every_direction(self):
        from event_movement_compile import animation_profile
        rows = animation_profile(self.session.data, 383, 137)
        self.assertEqual(rows[4]['speed'], 160)
        self.assertEqual(rows[4]['directions_valid'], [True] * 4)
        self.assertEqual(rows[3]['speed'], 0)


if __name__ == '__main__':
    unittest.main()
