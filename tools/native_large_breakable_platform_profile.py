"""Exact322 standing-delay-collapse controller; no room-owned flag or actor target."""
from event_logic_compile import compile_logic
from project_state_runtime import compile_project_command,compile_project_condition
SOURCE_MAP=69
SOURCE_ENTITY=28
SOURCE_RECORD=bytes.fromhex('1e00333b0180425d430b00009d00000000000000')
CONTROLLER=bytes.fromhex('003e04feff37641a051c0119ff')
def verify_source(datas):
 from native_class_placement import record_cluster
 from editor_session import EditSession
 from event_editor import instructions
 if record_cluster(datas,SOURCE_MAP)['entities'][SOURCE_ENTITY]!=SOURCE_RECORD:raise ValueError('Breakable322 source record differs')
 code=b''.join(bytes(datas[p:p+n]) for p,op,n in instructions(EditSession.readonly(datas),SOURCE_MAP,'C 29'))
 if code!=CONTROLLER:raise ValueError('Breakable322 source controller differs')
 return True

def compile_platform(registry,commands=None,*,leaf_emitter=None):
 def leaf(row):
  if row.get('switch_scope')=='project' or row.get('variable_scope')=='project':return compile_project_command(row,registry)
  if leaf_emitter:return leaf_emitter(row)
  raise ValueError('Breakable platform continuation needs verified native leaf')
 after=compile_logic(commands or [],leaf_emitter=leaf,project_condition_emitter=lambda r:compile_project_condition(r,registry))
 return {'C':CONTROLLER[:-2]+after+CONTROLLER[-2:]},{'catalogue':322,'source_map':69,'source_entity':28,'source_program':'C29','native_delay_operand':100,'native_activation_animation':5,'continuation_after_native_animation':True,'native_lifecycle_instruction':'19 writes actor phase3 at32bit +10; actual removal awaits engine observation','private_flags_required':0,'source_room_dependencies':[],'gameplay_verified':False}
