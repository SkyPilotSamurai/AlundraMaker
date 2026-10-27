"""Bounded wall306 toggle, preserving self-selector native flags/animations."""
from event_logic_compile import _Assembler,compile_logic
from project_state_runtime import compile_project_command,compile_project_condition

SOURCE_MAP=40
SOURCE_ENTITY=9
SOURCE_RECORD=bytes.fromhex('1018232b01c03232380600008781000000000000')
CONTROLLER=bytes.fromhex('638001003002800d00628000080002f6ff6380000830018011001a031c011a0006028002e1ff1a021c011a0106028002d5ffff')
CONTACT=bytes.fromhex('bdff0063800008320180050280ff')


def verify_source(datas):
    from native_class_placement import record_cluster
    from editor_session import EditSession
    from event_editor import instructions
    if record_cluster(datas,SOURCE_MAP)['entities'][SOURCE_ENTITY]!=SOURCE_RECORD:
        raise ValueError('Wall306 donor record differs')
    session=EditSession.readonly(datas)
    for key,expected in [('C 7',CONTROLLER),('D 1',CONTACT)]:
        actual=b''.join(bytes(datas[p:p+n]) for p,_,n in instructions(session,SOURCE_MAP,key))
        if actual!=expected:raise ValueError('Wall306 donor controller differs')
    return True


def compile_wall_switch(registry,state_id,request_id,commands=None,*,leaf_emitter=None,can_deactivate=False,release_commands=None):
    if state_id==request_id:raise ValueError('Wall306 state/request must differ')
    for identifier in (state_id,request_id):registry.get('switches',identifier)
    def flag(identifier,value,condition=False):
        row={'type':'switch' if condition else 'set_switch','switch_scope':'project','switch_id':identifier,'value':value}
        return (compile_project_condition if condition else compile_project_command)(row,registry)
    def leaf(row):
        if row.get('switch_scope')=='project' or row.get('variable_scope')=='project':return compile_project_command(row,registry)
        if leaf_emitter:return leaf_emitter(row)
        raise ValueError('Unverified wall306 leaf')
    continuation=compile_logic(commands or [],leaf_emitter=leaf,
        project_condition_emitter=lambda row:compile_project_condition(row,registry))
    # Can Deactivate: hitting it again switches it off (Deactivate actions); else it stays on
    release=compile_logic(release_commands or [],leaf_emitter=leaf,
        project_condition_emitter=lambda row:compile_project_condition(row,registry))
    c=_Assembler();c.data.extend(bytes.fromhex('63800100'));c.label('poll')
    c.data.extend(flag(request_id,True,True));c.branch(3,'action')
    c.data.extend(bytes.fromhex('6280000800'));c.branch(2,'poll')
    c.label('action');c.data.extend(bytes.fromhex('63800008'))
    c.data.extend(flag(state_id,True,True));c.branch(3,'open')
    for label,animation in [('close',bytes.fromhex('1a031c011a00')),('open',bytes.fromhex('1a021c011a01'))]:
        if label=='open':c.label(label)
        c.data.extend(animation);c.data.extend(continuation if label=='open' else release);c.data.extend(flag(request_id,False));c.branch(2,'poll')
    c.data.append(0xFF)
    d=_Assembler()
    if not can_deactivate:   # already on: it stays on
        d.data.extend(flag(state_id,True,True));d.branch(3,'end')
    d.data.extend(bytes.fromhex('bd3c0063800008'))   # the wall switch's click BD3C (map 57 / 363 copies)
    d.data.extend(flag(state_id,True,True));d.branch(4,'turn_on')
    d.data.extend(flag(state_id,False));d.branch(2,'request')
    d.label('turn_on');d.data.extend(flag(state_id,True));d.label('request')
    d.data.extend(flag(request_id,True));d.label('end');d.data.append(0xFF)
    return {'C':c.finish(),'D':d.finish()},{'class_id':306,'source_map':40,'source_entity':9,
        'native_flags_replaced':['8001','8002'],'state_id':state_id,'request_id':request_id,
        'retained_actor_flags':{'selector':128,'bits':[1,2048],'source_meanings':['ClassA','ClassC'],
                               'native_field_width':32,'native_field_offset':108},
        'native_animation_sequence':'2→1 on activation,3→0 on deactivation, each after1C01 wait',
        'continuation_length':len(continuation),'gameplay_verified':False,'memory_card_persistent':False,
        'uncertainties':['Actual trigger/controller collision contract not yet tested','BD00FF audio identity unknown']}
