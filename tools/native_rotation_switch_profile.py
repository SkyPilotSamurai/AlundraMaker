"""Explicit308 rotation-switch variant; foreign actor3 commands become authored actions."""
from event_logic_compile import _Assembler,compile_logic
from project_state_runtime import compile_project_command,compile_project_condition
SOURCE_MAP=126
SOURCE_ENTITY=0
SOURCE_RECORD=bytes.fromhex('0000123b01c134066a0200008181000000000000')
CONTROLLER=bytes.fromhex('360a80060a801a011c011a0009185b0301182a360a80060a801a011c011a0009005b0301002a360a80060a801a011c011a0009085b0301082a360a80060a801a011c011a0009105b0301102a49ff')
CONTACT=bytes.fromhex('050a802bff')
def verify_source(datas):
 from native_class_placement import record_cluster
 from editor_session import EditSession
 from event_editor import instructions
 if record_cluster(datas,SOURCE_MAP)['entities'][SOURCE_ENTITY]!=SOURCE_RECORD:raise ValueError('Rotation308 source record differs')
 for bank,expected in [('C',CONTROLLER),('D',CONTACT)]:
  actual=b''.join(bytes(datas[p:p+n]) for p,op,n in instructions(EditSession.readonly(datas),SOURCE_MAP,bank+' 1'))
  if actual!=expected:raise ValueError('Rotation308 source controller differs')
 return True

def compile_rotation_switch(registry,request_id,commands=None,*,leaf_emitter=None,initial_direction=16):
 registry.get('switches',request_id)
 if type(initial_direction) is not int or initial_direction not in (0,8,16,24):raise ValueError('Rotation switch initial direction must be native cardinal')
 condition={'type':'switch','switch_scope':'project','switch_id':request_id,'value':True}
 def leaf(row):
  if row.get('switch_scope')=='project' or row.get('variable_scope')=='project':return compile_project_command(row,registry)
  if leaf_emitter:return leaf_emitter(row)
  raise ValueError('Rotation continuation needs a verified native leaf')
 after=compile_logic(commands or [],leaf_emitter=leaf,project_condition_emitter=lambda r:compile_project_condition(r,registry))
 reset=compile_project_command({'type':'set_switch','switch_scope':'project','switch_id':request_id,'value':False},registry)
 a=_Assembler()
 for i,direction in enumerate((24,0,8,16)):
  a.label('wait'+str(i));a.data.append(0);a.data.extend(compile_project_condition(condition,registry));a.branch(4,'wait'+str(i))
  a.data.extend(reset);a.data.extend(bytes.fromhex('1a011c011a00'));a.data.extend(bytes((9,direction)));a.data.extend(after);a.data.append(0x2A)
 a.branch(2,'wait0');a.data.append(255)
 contact=compile_project_command({'type':'set_switch','switch_scope':'project','switch_id':request_id,'value':True},registry)+bytes.fromhex('2bff')
 return {'A':bytes((9,initial_direction,255)),'C':a.finish(),'D':contact},{'catalogue':308,'source_map':126,'source_entity':0,'source_programs':['C1','D1'],'native_request_replaced':'800A','foreign_actor_handoff_removed':['5B 03 01 18','5B 03 01 00','5B 03 01 08','5B 03 01 10'],'native_self_directions':[24,0,8,16],'native_animation':1,'idle_animation':0,'continuation_after_native_animation':True,'activation_bit0_disable_enable':True,'gameplay_verified':False,'scope':'Explicit authored rotation controller only; original actor3 handoff replaced by authored Activate contents; no passive/map91 equivalence'}
