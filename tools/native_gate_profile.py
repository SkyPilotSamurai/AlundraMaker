"""Bounded325 gate native rise/hold/fall controlled by explicitprivate switch."""
from event_logic_compile import _Assembler,compile_logic
from project_state_runtime import compile_project_command,compile_project_condition
SOURCE_MAP=39
SOURCE_ENTITY=2
SOURCE_RECORD=bytes.fromhex('0a1c0d1f01804508120800008200000000000000')
SOURCE_CONTROLLER=bytes.fromhex('00310380ffff310380faff1b00012030001b000000003103800d00310380080002f5ff1625170002d9ffff')

def verify_source(datas):
 from native_class_placement import record_cluster
 from editor_session import EditSession
 from event_editor import instructions
 if record_cluster(datas,39)['entities'][2]!=SOURCE_RECORD:raise ValueError('Gate325 source record differs')
 c=b''.join(bytes(datas[p:p+n]) for p,_,n in instructions(EditSession.readonly(datas),39,'C 2'))
 if c!=SOURCE_CONTROLLER:raise ValueError('Gate325 source controller differs')
 return True

def compile_gate(registry,open_switch_id,commands=None,*,leaf_emitter=None):
 registry.get('switches',open_switch_id)
 condition={'type':'switch','switch_scope':'project','switch_id':open_switch_id,'value':True}
 def leaf(row):
  if row.get('switch_scope')=='project' or row.get('variable_scope')=='project':return compile_project_command(row,registry)
  if leaf_emitter:return leaf_emitter(row)
  raise ValueError('Gate continuation needs verified native leaf')
 after=compile_logic(commands or [],leaf_emitter=leaf,project_condition_emitter=lambda r:compile_project_condition(r,registry))
 a=_Assembler()
 # 2026-10-23: on map entry with the switch already ON the gate is put straight at its open
 # position (same native Z force/displacement wait, 48px in one step, no sounds, no replay of
 # the Activate contents); with it OFF it starts closed. Then it follows the switch.
 a.data.extend(compile_project_condition(condition,registry));a.branch(4,'closed')
 a.data.extend(bytes.fromhex('1b0030'+'2030001b0000'));a.branch(2,'open')
 a.label('closed');a.data.append(0);a.data.extend(compile_project_condition(condition,registry));a.branch(4,'closed')
 a.data.extend(bytes.fromhex('bd1900'+'1b00012030001b0000'+'be1900'+'bde000'));a.data.extend(after)   # the game's gate sounds (map 424): motor while it moves, clunk when it stops
 a.label('open');a.data.append(0);a.data.extend(compile_project_condition(condition,registry));a.branch(3,'open')
 a.data.extend(bytes.fromhex('bd1900'+'16251700'+'be1900'+'bde000'));a.branch(2,'closed');a.data.append(255)
 return {'C':a.finish()},{'catalogue':325,'source_map':39,'source_entity':2,'source_program':'C 2','native_flag_replaced':'8003','open_switch_id':open_switch_id,'open_distance_pixels':48,'close_wait':'Native25 ground orsupportcollision','continuation_after_full_open':True,'gameplay_verified':False,'uncertainties':['Hardware not tested','No save/hardwareclaim']}
