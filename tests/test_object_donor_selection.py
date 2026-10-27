import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import object_donor_selection as selection


def record(hooks=b'\x00'*6):
    raw=bytearray(20);raw[5]=0xC0;raw[6]=48;raw[10:16]=hooks
    return bytes(raw)


class DonorSelectionTests(unittest.TestCase):
    def select(self,rows,callbacks=None):
        def cluster(data,map_id): return {'entities':rows.get(map_id,[])}
        def native(data,map_id,index): return (callbacks or {}).get(map_id,[('A',0),('C',23)])
        with patch.object(selection,'record_cluster',side_effect=cluster), \
             patch.object(selection,'sprite_callbacks',side_effect=native):
            return selection.preferred_hook_free_donor(b'',304)

    def test_hook_free_alternative_preserves_native_callback_profile(self):
        hooked=record(b'\x81'+b'\x00'*5)
        result=self.select({1:[hooked],4:[record()]})
        self.assertEqual((result['map_id'],result['entity_index']),(4,0))
        self.assertEqual(result['first_donor']['map_id'],1)
        self.assertTrue(result['hook_free']);self.assertFalse(result['gameplay_verified'])

    def test_callback_mismatch_is_never_selected(self):
        result=self.select({1:[record(b'\x81'+b'\x00'*5)],4:[record()]},
                           {4:[('A',0),('C',70)]})
        self.assertEqual(result['map_id'],1)
        self.assertEqual(result['selection'],'first_donor_fallback')
        self.assertEqual(result['hook_free_callback_mismatches'],1)

    def test_first_hook_free_donor_stays_deterministic(self):
        result=self.select({1:[record(),record()],4:[record()]})
        self.assertEqual((result['map_id'],result['entity_index']),(1,0))
        self.assertEqual(result['donor_count'],3)

    def test_no_hook_free_keeps_guarded_fallback(self):
        result=self.select({2:[record(b'\x81'+b'\x00'*5)]})
        self.assertEqual(result['selection'],'first_donor_fallback')
        self.assertFalse(result['hook_free'])

    def test_nonobject_or_absent_class_rejected(self):
        with self.assertRaisesRegex(ValueError,'only for object'):
            selection.preferred_hook_free_donor(b'',260)
        with self.assertRaisesRegex(ValueError,'no concrete'):
            self.select({})
    def test_known_map_controller_dependency_keeps_guarded_donor(self):
        with patch.object(selection,'MAP_CONTROLLER_REQUIRED',frozenset({304})):
            result=self.select({1:[record(b'\x81'+b'\x00'*5)],4:[record()]})
        self.assertEqual(result['map_id'],1)
        self.assertTrue(result['known_map_controller_dependency'])

    def test_platform_door_grating_controller_is_not_replaced_by_scenery(self):
        for catalogue in (312,313,324,325,326,345):
            with self.subTest(catalogue=catalogue):
                hooked=bytearray(20);hooked[5]=0xC0;hooked[6]=catalogue-256;hooked[12]=0x81
                passive=bytearray(hooked);passive[12]=0
                def cluster(data,map_id):return {'entities':[bytes(hooked)] if map_id==1 else [bytes(passive)] if map_id==4 else []}
                with patch.object(selection,'record_cluster',side_effect=cluster), patch.object(selection,'sprite_callbacks',return_value=[('A',0),('C',0)]):
                    result=selection.preferred_hook_free_donor(b'',catalogue)
                self.assertEqual(result['map_id'],1)
                self.assertTrue(result['known_map_controller_dependency'])
                self.assertFalse(result['hook_free'])

    def test_rolling_rock_returns_actual_guarded_controller_not_first_static(self):
        static=bytearray(20);static[5]=0xC0;static[6]=59
        native=bytearray(static);native[10]=0x81;native[12]=0x81
        def cluster(data,map_id):return {'entities':[bytes(static)] if map_id==1 else [bytes(native)] if map_id==4 else []}
        with patch.object(selection,'record_cluster',side_effect=cluster),patch.object(selection,'sprite_callbacks',return_value=[('E',19)]),patch.object(selection,'CONTROLLER_GUARDED_DONORS',{315:(4,0,bytes(native).hex())}):
            result=selection.preferred_hook_free_donor(b'',315)
        self.assertEqual(result['map_id'],4);self.assertEqual(result['first_donor']['map_id'],1)
        self.assertEqual(result['selection'],'guarded_native_controller_donor');self.assertFalse(result['hook_free'])
        self.assertFalse(result['instance_callbacks_transplanted'])

    def test_rolling_controller_mismatch_does_not_fall_back_to_scenery(self):
        raw=bytearray(20);raw[5]=0xC0;raw[6]=59
        with patch.object(selection,'record_cluster',return_value={'entities':[bytes(raw)]}),patch.object(selection,'sprite_callbacks',return_value=[('E',19)]),patch.object(selection,'CONTROLLER_GUARDED_DONORS',{315:(4,0,'ff'*20)}):
            with self.assertRaisesRegex(ValueError,'source record differs'):selection.preferred_hook_free_donor(b'',315)
