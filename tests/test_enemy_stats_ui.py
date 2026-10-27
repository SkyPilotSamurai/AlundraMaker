import unittest,sys
from pathlib import Path
from copy import deepcopy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from enemy_stats_ui import apply_combat_form,response_values,multiplier_factor,MODE_LABELS
from enemy_combat_fields import decode_response

class EnemyStatsFormTests(unittest.TestCase):
 def row(self):
  return {'id':'enemy:1','kind':'enemy','name':'Example','source':{'balance_entry':1},'data':{'max_hp':50,'contact_damage':None,'attacks':[{'attribute':7,'power':4},{'attribute':2,'power':9}], 'damage_responses_raw':[16]*11}}
 def test_incoming_all_raw_bytes_roundtrip_without_flag_loss(self):
  for raw in range(256):
   row=self.row();row['data']['damage_responses_raw']=[raw]*11
   value=decode_response(raw);mode=next(k for k,v in MODE_LABELS.items() if v==value['mode'])
   result=apply_combat_form(row,50,[4,9],incoming=[(mode,f"{value['factor_numerator']*6.25:g}%")]*11)
   self.assertEqual(result,row)
 def test_contact_assignment_does_not_assume_slot_or_modify_attribute(self):
  row=self.row();saved=deepcopy(row)
  result=apply_combat_form(row,63,[4,19],contact_index=1)
  self.assertEqual(row,saved);self.assertEqual(result['source']['contact_attack_index'],1)
  self.assertEqual(result['data']['attacks'],[{'attribute':7,'power':4},{'attribute':2,'power':19}])
  self.assertIsNone(result['data']['contact_damage'])
  result=apply_combat_form(result,63,[4,19]);self.assertNotIn('contact_attack_index',result['source'])
 def test_percent_presets_exact_and_invalid_ranges_rejected(self):
  for text,value in [('Normal (100%)',16),('Resistant (50%)',8),('Weak (200%)',32),('0%',0),('393.75%',63)]:self.assertEqual(multiplier_factor(text),value)
  for text in ('NaN','Infinity','-6.25%','400%','1%','hello'):
   with self.assertRaises(ValueError):multiplier_factor(text)
 def test_ranges_unknown_hp_and_fallback(self):
  row=self.row();row['data']['max_hp']=None
  self.assertIsNone(apply_combat_form(row,'',[4,9])['data']['max_hp'])
  row['data']['balance_tiers']=[{'damage_responses_raw':[8]*11}];del row['data']['damage_responses_raw']
  self.assertEqual(response_values(row),[8]*11)
  for kwargs in ({'hp':256},{'attack_powers':[4,256]},{'contact_index':2},{'incoming':[('unknown','100%')]*11}):
   args=dict(hp=50,attack_powers=[4,9]);args.update(kwargs)
   with self.assertRaises(ValueError):apply_combat_form(row,**args)
 def test_form_uses_real_balance_backend(self):
  import struct,hashlib
  from enemy_definition import BalanceSession
  from database_balance import apply_definition_balance
  raw=struct.pack('<h',2)+bytes([255,19,50]+[16]*11+[2,7,4,2,9])
  session=BalanceSession(raw,verify=False);row=self.row();row['source']={'balance_entry':0,'balance_sha256':hashlib.sha256(raw).hexdigest()}
  result=apply_combat_form(row,60,[10,19],incoming=[('Damage multiplier','50%')]*11)
  self.assertTrue(apply_definition_balance(session,result))
  self.assertEqual(session.data[4],60);self.assertEqual(session.data[5:16],bytes([8]*11))
  self.assertEqual(session.data[17:21],bytes([7,10,2,19]));session.undo();self.assertEqual(bytes(session.data),raw)

if __name__=='__main__':unittest.main()
