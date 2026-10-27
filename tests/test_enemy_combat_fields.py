import unittest,sys,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from enemy_combat_fields import *
from enemy_definition import BalanceSession
from native_attack_balance import damage_preview


class CombatFieldsTests(unittest.TestCase):
    def test_editor_uses_flail_label_preserving_source_spelling(self):
        self.assertEqual(ATTACK_LABELS[1],"Flail")
        self.assertNotIn("Hammer",ATTACK_LABELS)
        self.assertEqual(SOURCE_ATTACK_TYPES[1],"Hammer")
    def raw(self):return struct.pack('<h',2)+bytes([255,19,40]+[16]*11+[2,1,8,1,20])
    def test_all_response_bytes_roundtrip_and_modes_distinct(self):
        for raw in range(256):
            decoded=decode_response(raw)
            self.assertEqual(encode_response(decoded['mode'],decoded['factor_numerator']),raw)
        self.assertNotEqual(decode_response(128)['mode'],decode_response(192)['mode'])
        for raw in (-1,256,True):
            with self.assertRaises(ValueError):decode_response(raw)
    def test_zero_scalar_is_not_immunity(self):
        record=BalanceTable(self.raw()).record(0)
        self.assertEqual(damage_preview(record,0,0,40)['damage'],1)
        self.assertEqual(damage_preview(record,0,32,40)['damage'],40)
        self.assertEqual(damage_preview(record,0,0x40,40)['hp_after'],0)
        for raw in (0x80,0xc0):self.assertEqual(damage_preview(record,0,raw,40)['hp_after'],40)
    def test_response_edit_only_changes_selected_byte_and_undo(self):
        raw=self.raw();session=BalanceSession(raw,verify=False)
        report=edit_response(session,0,0,6,mode='scalar',factor_numerator=24)
        differences=[i for i,(a,b) in enumerate(zip(raw,session.data)) if a!=b]
        self.assertEqual(differences,[10]);self.assertEqual(report['offset'],10)
        session.undo();self.assertEqual(bytes(session.data),raw)
        with self.assertRaises(ValueError):edit_response(session,0,0,0,mode='scalar',factor_numerator=16)
    def test_contact_is_not_fabricated_field(self):
        fields=combat_fields(self.raw(),0)
        self.assertIsNone(fields['defense_field']);self.assertIsNone(fields['contact_damage_field'])
        self.assertEqual(len(fields['incoming_responses']),11)
        route=contact_attack_for_animation(self.raw(),0,0,0)
        self.assertEqual(route['selection']['index'],1)
        self.assertFalse(route['contact_identity_proven'])

if __name__=='__main__':unittest.main()
