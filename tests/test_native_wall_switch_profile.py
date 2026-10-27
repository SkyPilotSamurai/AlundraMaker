import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_wall_switch_profile import compile_wall_switch,verify_source
from project_state_registry import ProjectStateRegistry


class WallProfileTests(unittest.TestCase):
    def test_source(self):
        data=(Path(__file__).resolve().parents[1]/'game/disc/DATA/DATAS.BIN').read_bytes()
        self.assertTrue(verify_source(data))
    def test_private_and_native(self):
        registry=ProjectStateRegistry({});a=registry.create('switches','State')['id'];b=registry.create('switches','Request')['id']
        programs,report=compile_wall_switch(registry,a,b,[{'type':'change_money','amount':9}])
        self.assertTrue(programs['D'].startswith(bytes.fromhex('bdff0063800008')))
        self.assertIn(bytes.fromhex('6280000800'),programs['C'])
        self.assertEqual(report['native_flags_replaced'],['8001','8002'])
    def test_alias_rejected(self):
        registry=ProjectStateRegistry({});a=registry.create('switches','State')['id']
        with self.assertRaises(ValueError):compile_wall_switch(registry,a,a)


if __name__=='__main__':unittest.main()
