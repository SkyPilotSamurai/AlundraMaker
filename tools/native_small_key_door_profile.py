"""Exact323 source41/24 key door; production uses retained C ownership.

The historical F-only variant remains explicitly experimental for reproducing
its recorded yielding-continuation failure.
"""
from native_key_door_profile import compile_door
SOURCE_RECORD=bytes.fromhex('0000333b01c0431a3a3298000000009800000000')
SOURCE_PROGRAMS={'A 24':bytes.fromhex('31ac0207002e80ff'),'F 24':bytes.fromhex('833d01598100041100bd3c00843d05ac022e80020700000d0100ff')}

def verify_source(data):
 from native_class_placement import record_cluster
 from editor_session import EditSession
 from event_editor import instructions
 if record_cluster(data,41)['entities'][24]!=SOURCE_RECORD:raise ValueError('Small key door323 donor differs')
 for key,expected in SOURCE_PROGRAMS.items():
  actual=b''.join(bytes(data[p:p+n]) for p,_,n in instructions(EditSession.readonly(data),41,key))
  if actual!=expected:raise ValueError('Small key door323 '+key+' differs')
 return True

def compile_small_key_door(registry,opened_id,text_ref,after=b'',retained_c=False):
 programs=compile_door(registry,opened_id,text_ref,after)
 if retained_c:
  from event_logic_compile import _Assembler
  from project_state_runtime import compile_project_condition,compile_project_command
  test=compile_project_condition(dict(type='switch',switch_scope='project',switch_id=opened_id,value=True),registry)
  set_open=compile_project_command(dict(type='set_switch',switch_scope='project',switch_id=opened_id,value=True),registry)
  f=_Assembler();f.data.extend(test);f.branch(3,'end')
  f.data.extend(bytes.fromhex('833d01598100'));f.branch(4,'locked')
  f.data.extend(bytes.fromhex('bd3c00843d'));f.data.extend(set_open);f.branch(2,'end')
  f.data.append(0);f.label('locked');f.data.extend(bytes((13,text_ref,0)));f.label('end');f.data.append(255)
  c=_Assembler();c.label('poll');c.data.append(0);c.data.extend(test);c.branch(4,'poll')
  c.data.extend(after);c.data.extend(bytes.fromhex('2e80ff'))
  programs['F']=f.finish();programs['C']=c.finish()
 return programs,{'class_id':323,'source_map':41,'source_entity':24,'removed_room_flag':'02AC','opened_id':opened_id,'key_item_id':61,'key_name':'Key','quantity_native_width':16,'failure':'Native locked dialogue, no consumption or continuation','success':'Remove one Key, private opened state, authored continuation, self inactive','experimental_retained_c':retained_c,'production_enabled':False,'gameplay_verified':False,'memory_card_persistent':False}

def compile_portable_small_key_door(registry,opened_id,text_ref,after=b''):
 programs,report=compile_small_key_door(registry,opened_id,text_ref,after,retained_c=True)
 report.update(production_enabled=True,experimental_retained_c=False,retained_c_continuation=True,
               success='Native F consumes one Key and sets private latch; retained C owns continuation and cleanup')
 return programs,report
