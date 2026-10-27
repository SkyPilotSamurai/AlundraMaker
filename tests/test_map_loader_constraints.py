import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from map_loader_constraints import validate_layout,STOCK_MAX_MAP_BYTES

class LoaderConstraintTests(unittest.TestCase):
    def fixture(self):
        data=bytearray(484*2048)
        struct.pack_into('<484I',data,0x28,*[(i+1)*2048 for i in range(484)])
        return data
    def test_complete_table(self):
        self.assertEqual(validate_layout(self.fixture())['map_count'],483)
    def test_unaligned_start_rejected(self):
        data=self.fixture();struct.pack_into('<I',data,0x28+427*4,428*2048+20)
        with self.assertRaisesRegex(ValueError,'aligned'):validate_layout(data)
    def test_end_sentinel_mandatory(self):
        data=self.fixture();data.extend(bytes(2048))
        with self.assertRaisesRegex(ValueError,'sentinel'):validate_layout(data)
    def test_stock_envelope_and_monotonicity(self):
        data=self.fixture();struct.pack_into('<I',data,0x28+427*4,427*2048)
        with self.assertRaisesRegex(ValueError,'increase'):validate_layout(data)
        data=self.fixture();delta=STOCK_MAX_MAP_BYTES
        data.extend(bytes(delta))
        for i in range(428,484):struct.pack_into('<I',data,0x28+i*4,(i+1)*2048+delta)
        with self.assertRaisesRegex(ValueError,'largest-stock'):validate_layout(data)
