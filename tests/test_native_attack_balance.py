import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_attack_balance import selected_attack,attack_edit,damage_preview,analyse_native,target_response
from enemy_definition import BalanceSession,BalanceTable


def fixture():
    return struct.pack('<hh',4,4)+bytes([255,21,50]+[16]*11+[3,1,2,0x81,7,1,20])


class AttackBalanceTests(unittest.TestCase):
    def test_animation_pairs_and_shared_fallback(self):
        r=BalanceTable(fixture()).record(0)
        self.assertEqual(selected_attack(r,0)['power'],7)
        self.assertEqual(selected_attack(r,1)['power'],20)
        self.assertEqual(selected_attack(r,2)['power'],2)
        self.assertTrue(selected_attack(r,2)['fallback'])
        self.assertIsNone(selected_attack(dict(offset=0,attacks=[]),0))
        for bad in (-1,True,0x7fffffff):
            with self.assertRaises(ValueError):selected_attack(r,bad)

    def test_exact_pair_edit_alias_scope_and_undo(self):
        raw=fixture();s=BalanceSession(raw,verify=False)
        report=attack_edit(s,0,0,0,power=99)
        self.assertEqual(report['alias_entries'],[0,1])
        changed=[i for i,(a,b) in enumerate(zip(raw,s.data)) if a!=b]
        self.assertEqual(changed,[22])
        self.assertEqual(BalanceTable(s.data).record(1)['attacks'][1]['power'],99)
        s.undo();self.assertEqual(bytes(s.data),raw)
        with self.assertRaisesRegex(ValueError,'shared fallback'):attack_edit(s,0,0,8,power=9)
        attack_edit(s,0,0,8,power=9,allow_shared_fallback=True)
        self.assertEqual(BalanceTable(s.data).record(0)['attacks'][0]['power'],9)
        before=bytes(s.data)
        with self.assertRaises(ValueError):attack_edit(s,0,0,0,power=256)
        self.assertEqual(bytes(s.data),before)

    def test_native_scalar_path_modes_and_equipment(self):
        r=BalanceTable(fixture()).record(0)
        self.assertEqual(damage_preview(r,0,16,50,[r,r],equipment_animation=0)['damage'],21)
        self.assertEqual(damage_preview(r,0,16,50,[r,r],equipment_animation=1)['damage'],47)
        with self.assertRaisesRegex(ValueError,'separate native player animation'):
            damage_preview(r,0,16,50,[r])
        self.assertEqual(damage_preview(r,1,16,50,[r,r])['damage'],20)
        self.assertEqual(damage_preview(r,0,0,50)['damage'],1)
        self.assertEqual(damage_preview(r,0,64,50)['hp_after'],0)
        for response in (128,192):self.assertEqual(damage_preview(r,0,response,50)['hp_after'],50)
        with self.assertRaises(ValueError):damage_preview(r,0,16,50,[r]*4)

    def test_unknown_native_build_rejected(self):
        with self.assertRaisesRegex(ValueError,'fingerprinted'):analyse_native(b'unknown')

    def test_response_zero_nibble_native_max_hp_alias(self):
        r=BalanceTable(fixture()).record(0)
        self.assertEqual(target_response(r,0x80),50)
        self.assertEqual(target_response(r,0x81),16)
        self.assertEqual(target_response(r,11),16)
        for attr in (12,15,256,True):
            with self.assertRaises(ValueError):target_response(r,attr)


if __name__=='__main__':unittest.main()
