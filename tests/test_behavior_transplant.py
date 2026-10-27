import sys,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
DATAS=ROOT/'game/disc/DATA/DATAS.BIN'

class CloseBizHawkTests(unittest.TestCase):
 def test_build_and_test_ends_running_bizhawk(self):
  import os,editor_emulator
  calls=[]
  def run(args,**kw):calls.append(args);return SimpleNamespace(returncode=0)
  closed=editor_emulator.close_running_bizhawk(run)
  if os.name=='nt':
   self.assertTrue(closed);self.assertEqual(calls[0][:1],['taskkill']);self.assertIn('EmuHawk.exe',calls[0])
  else:self.assertFalse(closed)

@unittest.skipUnless(DATAS.is_file(),'needs the original DATAS.BIN')
class TransplantTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=DATAS.read_bytes()
 def test_lamp_switch_has_several_real_behaviours(self):
  from behavior_transplant import behaviour_variants,variant_label
  variants=behaviour_variants(self.data,398)
  self.assertGreater(len(variants),1)
  self.assertTrue(variant_label(1,variants[0]).startswith('Behaviour 1: as on map'))
 def test_scripts_are_copied_with_new_hooks(self):
  from behavior_transplant import transplant_hooks
  from native_class_placement import record_cluster
  donor=record_cluster(self.data,429)['entities'][0]
  self.assertEqual(donor[6]+(256 if donor[5]&128 else 0),398)
  data,hooks,report=transplant_hooks(self.data,163,429,donor[10:16])
  self.assertEqual(len(report['copied_programs']),sum(1 for v in donor[10:16] if v&0x80))
  for old,new in zip(donor[10:16],hooks):
   self.assertEqual(bool(old),bool(new));self.assertEqual(bool(old&0x80),bool(new&0x80))
  self.assertNotEqual(bytes(data),self.data)
 def test_class_with_no_placed_copy_gets_a_fresh_record(self):
  from behavior_transplant import synthetic_record
  row=synthetic_record(self.data,163,11,5,6,1)
  self.assertEqual((row[6],row[7],row[8],row[9]),(11,10,12,2));self.assertEqual(row[10:20],bytes(10))

 def test_copied_program_uses_room_flags_not_game_flags(self):
  # Map 1 root B2 sets/reads game flags 0127, 00CD, 00CE: the copy uses 8127, 80CD, 80CE.
  import struct
  from editor_session import EditSession
  from event_editor import reachable_instructions
  from behavior_transplant import program_span,FLAG_OPCODES
  s=EditSession(self.data,None,verify=False)
  code,info=program_span(self.data,1,'B',2,s)
  self.assertEqual(info['game_flags_made_room_flags'],['0x127','0xcd','0xce'])
  rows=reachable_instructions(s,1,'B 2');low=min(o for o,_,_ in rows);shift=3 if info['entry_jump'] else 0
  for offset,op,size in rows:
   if op in FLAG_OPCODES:
    operand=struct.unpack_from('<H',code,offset-low+shift+1)[0]
    self.assertTrue(operand==0 or operand&0x8000)
  self.assertEqual(len(code),len(program_span(self.data,1,'B',2,s)[0]))

class RelocationTests(unittest.TestCase):
 def test_placement_shift_units(self):
  from behavior_transplant import placement_shift
  # half-tiles of 12 / 8 / 8 pixels; tiles and 16 px height steps are half of that
  self.assertEqual(placement_shift((27,99,40),(37,95,44)),(120,-32,32,5,-2,2))
 def test_absolute_positions_follow_the_boss(self):
  import struct
  from behavior_transplant import relocate_code
  code=bytearray(bytes((0xA2,0))+struct.pack('<3H',336,800,320)+bytes((0x55,10,20,1,1))+bytes((0x07,0x81,5,6,7,8,1,2))+bytes((0x37,10)))
  rows=[(0,0xA2,8),(8,0x55,5),(13,0x07,8),(21,0x37,2)]
  self.assertEqual(relocate_code(code,rows,0,(120,-32,32,5,-2,2)),3+2+6)
  self.assertEqual(struct.unpack_from('<3H',code,2),(456,768,352))
  self.assertEqual(tuple(code[9:11]),(15,18))
  self.assertEqual(tuple(code[15:21]),(10,11,5,6,3,4))
  self.assertEqual(tuple(code[21:23]),(0x37,10))
 def test_value_leaving_its_field_is_kept(self):
  from behavior_transplant import relocate_code
  code=bytearray((0x55,3,3,1,1))
  relocate_code(code,[(0,0x55,5)],0,(0,0,0,-5,5,0))
  self.assertEqual(tuple(code),(0x55,3,8,1,1))

@unittest.skipUnless(DATAS.is_file(),'needs the original DATAS.BIN')
class BossRelocationTests(unittest.TestCase):
 def test_melzas_effect_moves_with_the_placed_boss(self):
  import struct
  from behavior_transplant import program_span,placement_shift
  from native_class_placement import record_cluster
  data=DATAS.read_bytes()
  raw=record_cluster(data,327)['entities'][0]
  home=program_span(data,327,'C',raw[10:16][2]&0x7F)[0]
  there=program_span(data,327,'C',raw[10:16][2]&0x7F,None,placement_shift(raw[7:10],(raw[7]+10,raw[8]-4,raw[9])))
  self.assertEqual(there[1]['positions_moved_with_placement'],2)
  i=home.index(0xA2)
  self.assertEqual(struct.unpack_from('<2H',there[0],i+2)[0]-struct.unpack_from('<2H',home,i+2)[0],120)

@unittest.skipUnless(DATAS.is_file(),'needs the original DATAS.BIN')
class BossTemplateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=DATAS.read_bytes()
 def test_boss_spawn_templates_come_with_the_boss(self):
  # Giant Slime (Large), map 44 entity 35: its C program spawns templates of class 335 (a map-local sprite)
  from behavior_transplant import transplant_hooks,placement_shift
  from native_class_placement import record_cluster
  from local_sprite_import import import_local_sprite
  donor=record_cluster(self.data,44)['entities'][35]
  shift=placement_shift(donor[7:10],(20,20,4))
  # without the art on the target its sprite is imported into a free slot, or the spawn is skipped
  bare,_,report=transplant_hooks(self.data,163,44,donor[10:16],{},shift=shift)
  self.assertGreaterEqual(len(record_cluster(bare,163)['entities']),len(record_cluster(self.data,163)['entities']))
  withart,_=import_local_sprite(bytearray(self.data),163,44,335-256,keep=set())
  before=len(record_cluster(bytes(withart),163)['entities'])
  data,_,report=transplant_hooks(bytes(withart),163,44,donor[10:16],{},shift=shift)
  ents=record_cluster(data,163)['entities']
  self.assertGreater(len(ents),before)
  for raw in ents[before:]:
   self.assertEqual(raw[6]+(256 if raw[5]&128 else 0),335)
  copied=[r for p in report['copied_programs'] for r in p['map_refs'] if 'copied_to' in r]
  self.assertTrue(copied);self.assertTrue(all(before<=r['copied_to']<len(ents) for r in copied))
  self.assertEqual(len(record_cluster(data,163)['entities']),before+len({r['copied_to'] for r in copied}))

 def test_appended_template_is_not_mistaken_for_the_targets_own(self):
  # donor templates 17-21 are all class 335; copying 17 lands at target slot 18, which must not
  # then stand in for donor template 18 (each donor template gets its own copy)
  from behavior_transplant import transplant_hooks,placement_shift
  from native_class_placement import record_cluster
  donor=record_cluster(self.data,44)['entities'][35]
  _,_,report=transplant_hooks(self.data,163,44,donor[10:16],{},shift=placement_shift(donor[7:10],(20,20,4)))
  pairs={r['template']:r['copied_to'] for p in report['copied_programs'] for r in p['map_refs'] if 'copied_to' in r}
  self.assertIn(18,pairs);self.assertEqual(len(set(pairs.values())),len(pairs))

 def test_boss_copy_drops_text_warps_and_healing(self):
  from behavior_transplant import transplant_hooks,placement_shift,BOSS_DROPPED_OPCODES
  from native_class_placement import record_cluster
  from editor_session import EditSession
  from event_editor import reachable_instructions
  for op in (0x0D,0x5C,0xC4,0x39,0x53,0x52,0x9B,0x9C,0x96,0x97,0xC3,0x1C):self.assertIn(op,BOSS_DROPPED_OPCODES)
  donor=record_cluster(self.data,44)['entities'][35]   # Giant Slime (Large): its intro spawns parts, so it is kept
  data,hooks,report=transplant_hooks(self.data,163,44,donor[10:16],{},start_now=True,shift=placement_shift(donor[7:10],(20,20,4)))
  kept=[p for p in report['copied_programs'] if 'hook_value' in p];self.assertTrue(kept)
  s=EditSession.readonly(bytes(data))
  for p in kept:
   ops={op for _,op,_ in reachable_instructions(s,163,f"{p['bank']} {p['hook_value']&0x7F}")}
   self.assertFalse(ops&set(BOSS_DROPPED_OPCODES))
 def test_melzas_room_intro_is_left_out(self):
  # map 327 C 1 only plays Melzas's entrance and switches itself off; copied, it hung the game (BizHawk 2026-10-19)
  from behavior_transplant import transplant_hooks,placement_shift
  from native_class_placement import record_cluster
  donor=record_cluster(self.data,327)['entities'][0]
  _,hooks,report=transplant_hooks(self.data,163,327,donor[10:16],{},start_now=True,shift=placement_shift(donor[7:10],(20,20,4)))
  self.assertEqual(hooks,bytes(6));self.assertIn('intro',report['copied_programs'][0]['skipped'])

if __name__=='__main__':unittest.main()
