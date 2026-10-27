"""Source-guarded314 native rolling with an explicit authored completion tile.

Explicit-target-only production: exact source126/3, native collision/force-idle and
Up-direction branch retained. Room032F is replaced by authored commands.
"""
from event_logic_compile import compile_logic
from project_state_runtime import compile_project_command,compile_project_condition
SOURCE_MAP=126
SOURCE_ENTITY=3
SOURCE_RECORD=bytes.fromhex('0000123b01c13a0a680284008400000000000000')
INITIAL=bytes.fromhex('161a01ff')
CONTROLLER=bytes.fromhex('006e04feff1a00078004052f2f050504f1ff58eeff0a00eeffeeff00052f0319ff')

def verify_source(datas):
 from native_class_placement import record_cluster
 from editor_session import EditSession
 from event_editor import instructions
 if record_cluster(datas,SOURCE_MAP)['entities'][SOURCE_ENTITY]!=SOURCE_RECORD:raise ValueError('Small rolling314 source record differs')
 for key,expected in [('A 4',INITIAL),('C 4',CONTROLLER)]:
  code=b''.join(bytes(datas[p:p+n]) for p,op,n in instructions(EditSession.readonly(datas),SOURCE_MAP,key))
  if code!=expected:raise ValueError('Small rolling314 source '+key+' differs')
 return True

def compile_controller(registry,target,commands=None,*,facing='up',leaf_emitter=None):
 if facing!='up':raise ValueError('Small rolling314 completion is observed only for Up facing')
 if not isinstance(target,dict) or set(target)!={'x','y','height'}:raise ValueError('Choose an explicit rolling completion tile and height')
 values=[target[k] for k in ('x','y','height')]
 if any(type(v) is not int or not 0<=v<=127 for v in values):raise ValueError('Rolling completion tile/height outside0..127')
 if values[2]!=1:raise ValueError('Small rolling314 currently needs target tile height1')
 def leaf(row):
  if row.get('switch_scope')=='project' or row.get('variable_scope')=='project':return compile_project_command(row,registry)
  if leaf_emitter:return leaf_emitter(row)
  raise ValueError('Rolling completion requires a verified native action')
 after=compile_logic(commands or [],leaf_emitter=leaf,project_condition_emitter=lambda r:compile_project_condition(r,registry))
 x,y,z=values
 area=bytes([7,0x80,x,x,y,y,z,z])
 code=CONTROLLER[:7]+area+CONTROLLER[15:28]+after+CONTROLLER[-2:]
 return {'A':INITIAL,'C':code},{'catalogue':314,'source_map':126,'source_entity':3,'explicit_completion_tile':dict(target),'native_force_idle_direction_branch_retained':True,'source_room_flag032F_reused':False,'completion_after_matching_tile_and_direction':True,'native_removal19_retained':True,'private_flags_required':0,'production_enabled':True,'gameplay_verified':False}
