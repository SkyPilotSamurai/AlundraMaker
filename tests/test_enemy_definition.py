import sys
import struct
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from enemy_definition import BalanceTable, BalanceSession


class BalanceTests(unittest.TestCase):
    def fixture(self):
        # Two table slots alias a two-tier chain, with opaque padding.
        return struct.pack('<hh', 4, 4) + bytes([2,18,10]+[16]*11+[1,129,7,222]) + bytes([255,15,20]+[32]*11+[0])

    def test_edit_preserves_headers_padding_and_aliases(self):
        data = self.fixture(); table = BalanceTable(data)
        record = table.record(0)
        self.assertEqual(record['alias_entries'], [0,1])
        offset, replacement = table.replacement(0, max_hp=30, attacks=[dict(attribute=129,power=90)])
        expected = bytearray(data[offset:offset+18]); expected[2]=30; expected[16]=90
        self.assertEqual(replacement, expected)
        self.assertEqual(table.data, data)
        self.assertEqual(table.selected_tier(0,3), 1)

    def test_reject_invalid_edits(self):
        table=BalanceTable(self.fixture())
        for args in [dict(max_hp=256),dict(attacks=[]),dict(damage_responses=[0])]:
            with self.assertRaises(ValueError): table.replacement(0,**args)
        with self.assertRaises(ValueError): table.record(0,-1)
        with self.assertRaises(ValueError): BalanceTable(self.fixture()[:-1])

    def test_item_and_sprite_reserved_mapping(self):
        table=BalanceTable(struct.pack('<'+'h'*512,*([1024]*512))+bytes([255,15,1]+[0]*12))
        self.assertEqual(table.entry_for_sprite(31),30)
        self.assertEqual(table.entry_for_sprite(127),30)
        self.assertEqual(table.entry_for_sprite(128),128)
        self.assertEqual(table.entry_for_item(1),31)
        with self.assertRaises(ValueError): table.entry_for_sprite(-1)

    def test_session_patch_and_undo(self):
        original=self.fixture()
        session=BalanceSession(original,verify=False)
        session.edit_stats(0,max_hp=44)
        patch=session.patch()
        other=BalanceSession(original,verify=False)
        other.apply_patch(patch)
        self.assertEqual(session.data,other.data)
        other.undo()
        self.assertEqual(other.data,original)
        with self.assertRaises(ValueError): other.apply_patch(dict(patch,format='alundra-datas-patch-v1'))
