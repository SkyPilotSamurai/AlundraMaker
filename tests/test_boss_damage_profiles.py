import unittest,sys,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from boss_damage_profiles import boss_profile


class BossDamageTests(unittest.TestCase):
    def table(self,index):
        start=(index+1)*2
        record=bytes([255,17,75]+[1]*8+[128,1,128]+[1,1,20])
        return struct.pack('<'+'h'*(index+1),*([start]*(index+1)))+record
    def test_resistance_explains_small_hits_without_unique_code(self):
        profile=boss_profile(self.table(479),479)
        samples=profile['incoming_responses'][0]['samples']
        self.assertEqual([s['damage'] for s in samples],[1,1,2,4])
        self.assertTrue(profile['stock_power_pair_shared'])
        self.assertFalse(profile['code_patch_required_for_response_edit'])
    def test_special_response_not_scalar_multiplier(self):
        profile=boss_profile(self.table(479),479)
        water=profile['incoming_responses'][8]
        self.assertEqual(water['mode'],'skip_80')
        self.assertTrue(all(s['hp_after']==75 for s in water['samples']))
        with self.assertRaises(ValueError):boss_profile(self.table(479),1)

if __name__=='__main__':unittest.main()
