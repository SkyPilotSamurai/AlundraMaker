"""Native313 moving-platform map52 variant; actor-owned distance wait retained."""
import hashlib
from event_logic_compile import compile_logic
from project_state_runtime import compile_project_command,compile_project_condition
SOURCE_MAP=52
SOURCE_ENTITY=7
SOURCE_RECORD=bytes.fromhex('001e0f3b01c03912400482008700000000000000')
LOAD=bytes.fromhex('6280006063800001ff')
CONTROLLER=bytes.fromhex('0b0150000a49ff')

def verify_source(datas):
 from native_class_placement import record_cluster
 from editor_session import EditSession
 from event_editor import instructions
 if record_cluster(datas,SOURCE_MAP)['entities'][SOURCE_ENTITY]!=SOURCE_RECORD:raise ValueError('Platform313 source record differs')
 for bank,key,expected in [('A','A 2',LOAD),('C','C 7',CONTROLLER)]:
  code=b''.join(bytes(datas[p:p+n]) for p,_,n in instructions(EditSession.readonly(datas),SOURCE_MAP,key))
  if code!=expected:raise ValueError('Platform313 controller differs')
 return {'record_sha256':hashlib.sha256(SOURCE_RECORD).hexdigest(),'A_sha256':hashlib.sha256(LOAD).hexdigest(),'C_sha256':hashlib.sha256(CONTROLLER).hexdigest()}

def compile_platform(registry,commands=None,*,leaf_emitter=None,direction=None):
 def leaf(row):
  if row.get('switch_scope')=='project' or row.get('variable_scope')=='project':return compile_project_command(row,registry)
  if leaf_emitter:return leaf_emitter(row)
  raise ValueError('Unverified moving platform continuation')
 continuation=compile_logic(commands or [],leaf_emitter=leaf,project_condition_emitter=lambda r:compile_project_condition(r,registry))
 load=LOAD
 if direction is not None:
  if type(direction)is not int or direction not in (0,8,16,24):raise ValueError('Unverified native facing direction')
  load=LOAD[:-1]+bytes([9,direction,255])
 code=CONTROLLER[:4]+continuation+CONTROLLER[4:]
 return {'A':load,'C':code},{'catalogue':313,'source_map':52,'source_entity':7,'source_programs':['A 2','C 7'],'variant':'native horizontal animation1 shuttle, distinct from first donor22 room-gated lift','distance_pixels':80,'continuation_after_distance_wait':True,'direction_override':direction,'foreign_flags':[],'gameplay_verified':False,'uncertainties':['Native blocked-motion/resume and animation movement speed need actual gameplay','Room/save reload and hardware not verified']}
