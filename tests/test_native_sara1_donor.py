import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import native_sara1_donor as source

class Sara1DonorTests(unittest.TestCase):
    def test_exact_native_donor_keeps_ai_and_no_instance_hooks(self):
        records=[bytes(20)]*source.ENTITY+[bytes.fromhex(source.RECORD)]
        with patch.object(source,'record_cluster',return_value={'entities':records}),patch.object(source,'sprite_callbacks',return_value=source.CALLBACKS):
            result=source.donor(b'')
        self.assertEqual(result['map_id'],54);self.assertFalse(result['gameplay_verified'])
        self.assertEqual(bytes.fromhex(result['record_hex'])[10:16],bytes(6))

    def test_record_or_callback_drift_rejected(self):
        records=[bytes(20)]*source.ENTITY+[bytes.fromhex(source.RECORD)]
        with patch.object(source,'record_cluster',return_value={'entities':records}),patch.object(source,'sprite_callbacks',return_value=[('C',0)]):
            with self.assertRaisesRegex(ValueError,'callback'):source.donor(b'')
        records[-1]=bytes(20)
        with patch.object(source,'record_cluster',return_value={'entities':records}):
            with self.assertRaisesRegex(ValueError,'donor differs'):source.donor(b'')

if __name__=='__main__':unittest.main()
