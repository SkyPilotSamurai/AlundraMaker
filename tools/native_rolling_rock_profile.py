"""Exact315 native two-leg rolling trajectory controller; no room-owned flag or actor target."""
from event_logic_compile import compile_logic
from project_state_runtime import compile_project_command,compile_project_condition
SOURCE_MAP=67
SOURCE_ENTITY=29
SOURCE_RECORD=bytes.fromhex('10251f3b01c33b2d51269e009e00000000000000')
INITIAL=bytes.fromhex('6280026163808000ff')
CONTROLLER=bytes.fromhex('bd370025bd2d001a061c011a030918bd19001e9000be1900bd2f001a061c011a030900bd19001e9000be190019ff')
def verify_source(datas):
 from native_class_placement import record_cluster
 from editor_session import EditSession
 from event_editor import instructions
 if record_cluster(datas,SOURCE_MAP)['entities'][SOURCE_ENTITY]!=SOURCE_RECORD:raise ValueError('Rolling315 source record differs')
 code=b''.join(bytes(datas[p:p+n]) for p,op,n in instructions(EditSession.readonly(datas),SOURCE_MAP,'C 30'))
 if code!=CONTROLLER:raise ValueError('Rolling315 source controller differs')
 initial=b''.join(bytes(datas[p:p+n]) for p,op,n in instructions(EditSession.readonly(datas),SOURCE_MAP,'A 30'))
 if initial!=INITIAL:raise ValueError('Rolling315 source initializer differs')
 return True

def compile_platform(registry,commands=None,*,leaf_emitter=None):
 def leaf(row):
  if row.get('switch_scope')=='project' or row.get('variable_scope')=='project':return compile_project_command(row,registry)
  if leaf_emitter:return leaf_emitter(row)
  raise ValueError('Rolling rock continuation needs verified native leaf')
 after=compile_logic(commands or [],leaf_emitter=leaf,project_condition_emitter=lambda r:compile_project_condition(r,registry))
 return {'A':INITIAL,'C':CONTROLLER[:-2]+(bytes.fromhex('1a00') if commands else b'')+after+CONTROLLER[-2:]},{'catalogue':315,'source_map':67,'source_entity':29,'source_programs':['A30','C30'],'native_traversal_operand':144,'native_animations':[6,3],'native_directions':[24,0],'continuation_after_native_second_leg':True,'authored_continuation_idle_animation':0 if commands else None,'native_lifecycle_instruction':'19 writes actor phase3 at32bit +10; actual removal awaits engine observation','private_flags_required':0,'source_room_dependencies':[],'gameplay_verified':False}
