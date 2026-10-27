import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from weapon_damage_fields import *
from enemy_definition import BalanceSession
ROOT=Path(__file__).resolve().parents[1]
class WeaponDamageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.raw=(ROOT/'game/disc/DATA/BALANCE.BIN').read_bytes();cls.exe=(ROOT/'game/disc/ALUN_CD.EXE').read_bytes()
 def test_tables_code_and_stock_distinct_targets(self):
  self.assertTrue(verify_weapon_routing(self.exe))
  for item,powers in [(2,(4,10)),(3,(8,12)),(4,(16,16)),(6,(2,5)),(10,(6,12)),(14,(4,12)),(16,(4,12))]:
   row=weapon_damage_profile(self.raw,item,self.exe);self.assertEqual((row['normal']['power'],row['charge']['power']),powers)
  self.assertEqual(weapon_damage_profile(self.raw,2)['charge']['targets'][0]['pair_index'],25)
  for item in (1,5,8,9):self.assertFalse(weapon_damage_profile(self.raw,item)['charge']['available'])
 def test_sword_new_normal_translates_base_and_charge_shared_only(self):
  session=BalanceSession(self.raw);before=bytes(session.data)
  result=edit_weapon_damage(session,2,normal=7,charge=17,exe=self.exe)
  self.assertEqual((result['profile']['normal']['power'],result['profile']['charge']['power']),(7,17))
  self.assertEqual(result['changed_entries'],[0,32])
  self.assertEqual(len([i for i,(a,b) in enumerate(zip(before,session.data)) if a!=b]),2)
  self.assertEqual(weapon_damage_profile(session.data,3)['charge']['power'],16)
  session.undo();self.assertEqual(bytes(session.data),before)
 def test_fire_effect_only_existing_damage_pairs_not_terminal(self):
  session=BalanceSession(self.raw);table=BalanceTable(self.raw);terminal=table.record(11)['attacks'][4].copy()
  result=edit_weapon_damage(session,16,normal=19,charge=27)
  self.assertEqual(result['changed_entries'],[11,12]);self.assertEqual(len(result['changed_offsets']),8)
  self.assertEqual(BalanceTable(session.data).record(11)['attacks'][4],terminal)
  for entry,power in ((11,19),(12,27)):
   self.assertEqual([p['power'] for p in BalanceTable(session.data).record(entry)['attacks'][:4]],[power]*4)
  session.undo();self.assertEqual(bytes(session.data),self.raw)
 def test_missing_charge_and_ranges_reject_atomically(self):
  session=BalanceSession(self.raw)
  for item,kw in [(1,{'charge':5}),(7,{'normal':10}),(2,{'normal':1}),(2,{'normal':300}),(2,{'normal':9,'charge':3}),(16,{'normal':256})]:
   with self.assertRaises(ValueError):edit_weapon_damage(session,item,**kw)
   self.assertEqual(bytes(session.data),self.raw)
 def test_missing_modified_animation_target_is_unavailable_atomically(self):
  modified=bytearray(self.raw);player=BalanceTable(modified).record(0)
  modified[player['offset']+14]=0
  profile=weapon_damage_profile(modified,2)
  self.assertFalse(profile['normal']['available']);self.assertFalse(profile['charge']['available'])
  session=BalanceSession(modified,verify=False)
  with self.assertRaises(ValueError):edit_weapon_damage(session,2,normal=8,charge=10)
  self.assertEqual(bytes(session.data),bytes(modified))
 def test_modified_routing_rejected_and_unrelated_mod_preserved(self):
  modified=bytearray(self.exe);modified[0x93b8+2]^=1
  with self.assertRaises(ValueError):verify_weapon_routing(modified)
  modified=bytearray(self.exe);modified[0x800455dc-0x80020000+0x800]^=1
  with self.assertRaises(ValueError):verify_weapon_routing(modified)
  modified=bytearray(self.exe);modified[0x800]^=1
  self.assertTrue(verify_weapon_routing(modified))

if __name__=='__main__':unittest.main()
