import copy
import hashlib
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from database_balance import apply_definition_balance, sync_balance_aliases
from enemy_definition import BalanceSession, BalanceTable
from native_class_validation import require_native_class_definition


class DatabaseCombatBalanceTests(unittest.TestCase):
    def fixture(self):
        raw = struct.pack('<hh', 4, 4) + bytes([255, 20, 30] + [16]*11 + [2, 1, 7, 6, 12, 222])
        balance = BalanceSession(raw, verify=False)
        row = {'id': 'enemy:0001', 'name': 'Test enemy', 'kind': 'enemy',
               'source': {'balance_entry': 0, 'balance_sha256': hashlib.sha256(raw).hexdigest()},
               'data': {'max_hp': 30, 'attacks': [{'attribute': 1, 'power': 7},
                                               {'attribute': 6, 'power': 12}],
                        'damage_responses_raw': [16]*11}}
        return balance, row

    def test_per_attack_and_weakness_write_only_native_fields_and_undo(self):
        balance, row = self.fixture()
        original = bytes(balance.data)
        row['data']['attacks'][1]['power'] = 19
        row['data']['damage_responses_raw'][5] = 32
        self.assertTrue(apply_definition_balance(balance, row))
        record = BalanceTable(balance.data).record(0)
        self.assertEqual(record['attacks'], row['data']['attacks'])
        self.assertEqual(record['damage_responses'], row['data']['damage_responses_raw'])
        self.assertEqual(record['alias_entries'], [0, 1])
        self.assertEqual(balance.data[-1], 222)
        session = SimpleNamespace(extra_files={'DATA/BALANCE.BIN': balance})
        require_native_class_definition(session, row)
        balance.undo()
        self.assertEqual(bytes(balance.data), original)

    def test_invalid_response_is_transactional_and_clones_do_not_patch_source(self):
        balance, row = self.fixture()
        original = bytes(balance.data)
        row['data']['damage_responses_raw'][3] = 256
        with self.assertRaises(ValueError):
            apply_definition_balance(balance, row)
        self.assertEqual(bytes(balance.data), original)
        row['clone_of'] = 'enemy:0000'
        self.assertFalse(apply_definition_balance(balance, row))
        self.assertEqual(bytes(balance.data), original)

    def test_unsupported_independent_defense_is_not_silently_exported(self):
        balance, row = self.fixture()
        row['data']['defense'] = 4
        with self.assertRaisesRegex(ValueError, 'defense'):
            require_native_class_definition(SimpleNamespace(extra_files={'DATA/BALANCE.BIN': balance}), row)

    def test_shared_record_refresh_preserves_names_and_independent_clones(self):
        balance, row = self.fixture()
        alias = copy.deepcopy(row)
        alias.update(id='enemy:0002', name='Custom alias name')
        alias['source']['balance_entry'] = 1
        clone = copy.deepcopy(alias)
        clone.update(id='enemy:0003', clone_of=alias['id'])
        db = SimpleNamespace(definitions=[row, alias, clone])
        row['data']['damage_responses_raw'][0] = 8
        row['data']['attacks'][0]['power'] = 23
        apply_definition_balance(balance, row)
        self.assertEqual(sync_balance_aliases(db, balance, 0), [row['id'], alias['id']])
        self.assertEqual(alias['name'], 'Custom alias name')
        self.assertEqual(alias['data']['damage_responses_raw'][0], 8)
        self.assertEqual(alias['data']['attacks'][0]['power'], 23)
        self.assertEqual(clone['data']['attacks'][0]['power'], 7)


    def test_later_tier_alias_does_not_replace_first_tier_database_stats(self):
        raw = struct.pack('<hh', 4, 19) + bytes([2,15,10]+[16]*11+[0]) + bytes([255,15,20]+[32]*11+[0])
        balance = BalanceSession(raw, verify=False)
        rows = [{'id': 'enemy:0001', 'kind': 'enemy', 'name': 'First tier',
                 'source': {'balance_entry': 0}, 'data': {'max_hp': 10}},
                {'id': 'enemy:0002', 'kind': 'enemy', 'name': 'Shared later tier',
                 'source': {'balance_entry': 1}, 'data': {'max_hp': 20}}]
        self.assertEqual(BalanceTable(raw).record(1)['alias_entries'], [0, 1])
        balance.edit_stats(1, max_hp=44)
        self.assertEqual(sync_balance_aliases(SimpleNamespace(definitions=rows), balance, 1), ['enemy:0002'])
        self.assertEqual(rows[0]['data'], {'max_hp': 10})
        self.assertEqual(rows[1]['data']['max_hp'], 44)


if __name__ == '__main__':
    unittest.main()
