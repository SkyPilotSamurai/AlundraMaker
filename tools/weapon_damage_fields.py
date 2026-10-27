"""Weapon normal/charged native power targets; no invented item pair indexes.

Pinned xcasadio242b09a20ae1186c90278ba5f15f0f9a84104ef4:
StaticVariables.cs699-726/1265+, PlayerManager.cs955-1034/1410-1457.
Native table bytes independently matched at80028BB8 and80028C1C.
"""
import struct
from copy import deepcopy
from enemy_definition import BalanceTable
from alundra_memory import parse_exe
from native_attack_balance import selected_attack, SITES as COMBAT_SITES
ITEM_FLAGS=bytes.fromhex('000001020308090a0b06070000000500040000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000')
INIT_FLAGS=bytes.fromhex('00100000001400000000000000013f00000041000000181b1400014400000046000000181c140001490000004b000000181d140001110b0a20150b0a20110c0a2001110e0a20150e0a20110f0a2000120000001600000000000000014000000042000000190000000013030810170300100000000001130408101704081013070808000000000000000000000000000010000000140000000000000001000100010001000100000000000000000000000000000000000000010000000000000100000001000000010000000100010000000000000000000000000000000000000000000000000000000000000000010001000100010001000000000000000000000000000000010000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000')
WEAPON_IDS=(1,2,3,4,5,6,7,8,9,10,14,16)
TABLE_SITES={0x80028BB8:ITEM_FLAGS,0x80028C1C:INIT_FLAGS}
CODE_SITES={0x80032048:(0x3C018003,0x00220821,0x90228BB8),
 0x8002F02C:(0x00031880,0x00641821,0x3C048003,0x24848C1D,0x00641821,0x90640008),
 0x8002F0A0:(0x00031880,0x00621821,0x3C028003,0x24428C1D,0x0800BC38,0x00621821),
 0x8002F0CC:(0x00031880,0x00621821,0x3C028003,0x24428C21,0x00621821,0x90640000)}


def verify_weapon_routing(exe):
 header=parse_exe(exe)
 for pc,raw in dict(TABLE_SITES,**{}).items():
  offset=pc-header['load_address']+0x800
  if offset<0x800 or exe[offset:offset+len(raw)]!=raw:raise ValueError(f'Weapon routing table changed at{pc:08X}')
 for pc,words in {**COMBAT_SITES,**CODE_SITES}.items():
  raw=struct.pack('<'+'I'*len(words),*words);offset=pc-header['load_address']+0x800
  if offset<0x800 or exe[offset:offset+len(raw)]!=raw:raise ValueError(f'Weapon routing code changed at{pc:08X}')
 return True


def _target(table,entry,animation,role):
 record=table.record(entry,0);pair=selected_attack(record,animation)
 if pair is None or not pair['attribute']&15:return None
 return dict(entry=entry,tier=0,pair_index=pair['index'],power=pair['power'],attribute=pair['attribute'],power_offset=pair['power_offset'],role=role)


def _effect_targets(table,entry,role):
 record=table.record(entry,0)
 return [dict(entry=entry,tier=0,pair_index=i,power=p['power'],attribute=p['attribute'],power_offset=record['offset']+16+2*i,role=role)
  for i,p in enumerate(record['attacks']) if p['attribute']&0x80 and p['attribute']&15]


def weapon_damage_profile(balance_data,item_id,exe=None):
 if type(item_id) is not int or item_id not in WEAPON_IDS:raise ValueError('Choose a researched native weapon item')
 if exe is not None:verify_weapon_routing(exe)
 table=BalanceTable(balance_data);flag=ITEM_FLAGS[item_id];row=INIT_FLAGS[flag*13:flag*13+13]
 normal_anim=row[1];jump_anim=row[5];charge_anim=row[9]
 normal=[];charged=[];notes=[];base=[]
 if item_id in (1,2,3,4,8):
  base=[_target(table,item_id+30,normal_anim,'equipped weapon power')];base=[t for t in base if t]
  normal=[t for t in (_target(table,0,normal_anim,'normal player animation'),_target(table,0,jump_anim,'jump player animation')) if t]
  if charge_anim:charged=[t for t in [_target(table,0,charge_anim,'charged player animation')] if t]
  if item_id in (2,3,4):notes.append('Charged player pair is shared across Sword, Fiend Blade and Holy Sword. Changing it affects all three.')
 elif item_id in (9,10):
  normal=[t for t in (_target(table,0,normal_anim,'normal player animation'),_target(table,0,jump_anim,'jump player animation')) if t]
  if charge_anim:charged=[t for t in [_target(table,0,charge_anim,'charged player animation')] if t]
 else:
  if row[2]:normal=_effect_targets(table,row[2],'normal spawned effect')
  if charge_anim and row[10]:charged=_effect_targets(table,row[10],'charged spawned effect')
  if item_id==7:notes.append('Spirit Wand uses a magic sequence; no normal/charged power mapping is emitted by this helper.')
 normal_value=normal[0]['power']+sum(t['power'] for t in base) if normal else None
 charge_value=charged[0]['power']+sum(t['power'] for t in base) if charged else None
 if any(t['power']!=normal[0]['power'] for t in normal[1:]):notes.append('Normal targets currently differ; editing normal synchronizes the listed targets.')
 if any(t['power']!=charged[0]['power'] for t in charged[1:]):notes.append('Charge targets currently differ; editing charge synchronizes the listed targets.')
 if base:notes.append('Displayed power includes the equipped weapon contribution and player animation contribution. Armor/item equipped contributions and victim response are excluded.')
 if item_id in (2,3,4):notes.append('Sword charge also spawns a separate beam effect; this field edits the charged player contact contribution, not that beam.')
 return dict(item_id=item_id,weapon_flag=flag,normal_animation=normal_anim,charged_animation=charge_anim,
  normal=dict(value=normal_value,power=normal_value,minimum=normal[0]['power'] if base and normal else 0,maximum=normal[0]['power']+255 if base and normal else 255,targets=normal,base_targets=base,available=bool(normal)),
  charge=dict(value=charge_value,power=charge_value,minimum=sum(t['power'] for t in base),maximum=255+sum(t['power'] for t in base),targets=charged,base_targets=base,available=bool(charged)),
  notes=notes,source_spawn_mapping=True,native_table_verified=exe is not None,
  limitations=['Power before victim resistance, not promised final HP damage','Charge speed/animation duration not edited','No new attack pairs or modified routing tables created'])


def edit_weapon_damage(session,item_id,*,normal=None,charge=None,exe=None):
 profile=weapon_damage_profile(session.data,item_id,exe);edits={};base=sum(t['power'] for t in profile['normal']['base_targets'])
 for mode,value in (('normal',normal),('charge',charge)):
  if value is None:continue
  if type(value) is not int or not 0<=value<=510:raise ValueError('Weapon combined power must be a whole number0..510')
  field=profile[mode]
  if not field['available']:raise ValueError(f'No researched{mode} damage targets for this weapon')
  if mode=='normal' and field['base_targets']:
   fixed=field['targets'][0]['power'];new_base=value-fixed
   if not 0<=new_base<=255:raise ValueError('Normal power minus fixed player contribution must fit0..255')
   if len(field['base_targets'])!=1:raise ValueError('Multiple base contributions cannot be edited ambiguously')
   target=field['base_targets'][0];edits[target['power_offset']]=new_base;base=new_base
  else:
   power=value-base
   if not 0<=power<=255:raise ValueError('Power minus equipped weapon contribution must fit0..255')
   for target in field['targets']:edits[target['power_offset']]=power
 if not edits:return dict(profile=profile,changed_offsets=[],changed_entries=[])
 # One atomic undo entry; preserve all unrelated bytes in the enclosing span.
 lo=min(edits);hi=max(edits)+1;raw=bytearray(session.data[lo:hi])
 for offset,value in edits.items():raw[offset-lo]=value
 session.replace(lo,bytes(raw),'Weapon normal / charged native powers')
 return dict(profile=weapon_damage_profile(session.data,item_id,exe),changed_offsets=[offset for offset in sorted(edits) if session.data[offset]!=session.original[offset]],shared_notes=profile['notes'],changed_entries=sorted({t['entry'] for mode in ('normal','charge') for t in profile[mode]['targets']+profile[mode]['base_targets'] if t['power_offset'] in edits}))
