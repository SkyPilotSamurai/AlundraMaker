"""Bounded native312 lift profile; no donor flags or room commands."""
import hashlib
from event_logic_compile import compile_logic
from project_state_runtime import compile_project_command,compile_project_condition
SOURCE_MAP=29
SOURCE_ENTITY=28
SOURCE_RECORD=bytes.fromhex('0024173b01c0380a520200009d00000000000000')
SOURCE_CONTROLLER=bytes.fromhex('003e04feff37141b00012028001b0000371e162028001749ff')

def verify_source(datas):
 from native_class_placement import record_cluster
 from editor_session import EditSession
 from event_editor import instructions
 if record_cluster(datas,SOURCE_MAP)['entities'][SOURCE_ENTITY]!=SOURCE_RECORD:raise ValueError('Platform312 donor differs')
 code=b''.join(bytes(datas[p:p+n]) for p,_,n in instructions(EditSession.readonly(datas),SOURCE_MAP,'C 29'))
 if code!=SOURCE_CONTROLLER:raise ValueError('Platform312 controller differs')
 return {'record_sha256':hashlib.sha256(SOURCE_RECORD).hexdigest(),'controller_sha256':hashlib.sha256(code).hexdigest()}

def compile_platform(registry,commands=None,*,leaf_emitter=None):
 def leaf(row):
  if row.get('switch_scope')=='project' or row.get('variable_scope')=='project':return compile_project_command(row,registry)
  if leaf_emitter:return leaf_emitter(row)
  raise ValueError('Platform continuation needs verified native leaf')
 continuation=compile_logic(commands or [],leaf_emitter=leaf,project_condition_emitter=lambda r:compile_project_condition(r,registry))
 # Retain the complete source standing/vertical-motion cycle. The native49
 # restarts this process after return to its original altitude, following
 # the inserted continuation. No direction/position/room flag is transplanted.
 code=SOURCE_CONTROLLER[:-2]+continuation+SOURCE_CONTROLLER[-2:]
 return {'C':code},{'catalogue':312,'source_map':29,'source_entity':28,'source_program':'C 29','retained_native_opcodes':['00','3E','04','37','1B','20','16','17','49','FF'],'vertical_distance':40,'force_z_source_raw':256,'authored_continuation_after_return':True,'foreign_flags':[],'gameplay_verified':False,'uncertainties':['Native physics/collision/rider behavior needs actual exported gameplay','Room/save reload and hardware not verified']}
