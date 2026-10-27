import unittest
from unittest.mock import patch
import native_magicpot_donor as source

class MagicpotDonorTests(unittest.TestCase):
    def verify(self,record=None,callbacks=None):
        rows=[bytes(20)]*source.ENTITY+[bytes.fromhex(source.RECORD) if record is None else record]
        with patch.object(source,'record_cluster',return_value={'entities':rows}),patch.object(source,'sprite_callbacks',return_value=source.CALLBACKS if callbacks is None else callbacks):
            return source.donor(b'')
    def test_initializer_runs_in_C_and_returns_to_native_bounce_without_overriding_load(self):
        result=self.verify()
        self.assertEqual(source.INITIALIZER,b'\x1a\x01\x40\x02\x00\xff')
        self.assertEqual(result['initializer_bank'],'C')
        self.assertEqual(result['native_callbacks'],[('A',20),('C',74),('D',0),('E',0),('F',0)])
        self.assertTrue(result['preserves_native_A20'])
        self.assertFalse(result['existing_stock_actors_changed'])
    def test_source_story_hook_or_saved_height_drift_is_rejected(self):
        for offset in (9,10,12,16,18):
            row=bytearray.fromhex(source.RECORD);row[offset]^=1
            with self.assertRaisesRegex(ValueError,'record differs'):self.verify(record=bytes(row))
    def test_load_and_bounce_callback_drift_is_rejected(self):
        for bank,index in (('A',0),('C',0),('D',1)):
            callbacks=[(b,index if b==bank else i) for b,i in source.CALLBACKS]
            with self.assertRaisesRegex(ValueError,'callback'):self.verify(callbacks=callbacks)

if __name__=='__main__':unittest.main()
