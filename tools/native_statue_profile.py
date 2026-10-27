"""Bounded class298 map2 sliding statue, with private per-instance state.

This is a one-time24pixel right slide initiated by interaction. It is not
generic movable-object physics. Source room flags and coordinates are removed.
"""
from event_logic_compile import _Assembler
from project_state_runtime import compile_project_command,compile_project_condition

CLASS_ID=298
SOURCE_MAP=2
SOURCE_ENTITY=9
SOURCE_RECORD=bytes.fromhex('0000333b01c32a22301a8a008a00008a00000000')
SOURCE_PROGRAMS={'A 10':bytes.fromhex('3179030d006580180000000000ff'),
 'C 10':bytes.fromhex('3664800664803b101018180d0d4b0579031a01bd19001e1800be19001a00ff'),
 'F 10':bytes.fromhex('056480ff')}

def verify_source(data):
    from editor_session import EditSession
    from native_class_placement import record_cluster
    from event_editor import instructions
    if record_cluster(data,SOURCE_MAP)['entities'][SOURCE_ENTITY]!=SOURCE_RECORD:raise ValueError('Statue298 donor differs')
    session=EditSession.readonly(data)
    for root,expected in SOURCE_PROGRAMS.items():
        actual=b''.join(bytes(data[pos:pos+size]) for pos,_,size in instructions(session,SOURCE_MAP,root))
        if actual!=expected:raise ValueError('Statue298 native map program differs')
    return True

def compile_statue(registry,moved_id,request_id,x,y,height,after=b''):
    if moved_id==request_id:raise ValueError('Statue request and moved state must be distinct')
    if not 1<=x<=254 or not 0<=y<=255 or not 0<=height<=255:raise ValueError('Statue approach tile outside native bounds')
    def test(identity):return compile_project_condition({'type':'switch','switch_scope':'project','switch_id':identity,'value':True},registry)
    def setflag(identity,value):return compile_project_command({'type':'set_switch','switch_scope':'project','switch_id':identity,'value':value},registry)
    a=_Assembler();a.data.extend(test(moved_id));a.branch(4,'end');a.data.extend(bytes.fromhex('6580180000000000'));a.label('end');a.data.append(255)
    c=_Assembler();c.data.extend(test(moved_id));c.branch(3,'end');c.label('poll');c.data.append(0);c.data.extend(test(request_id));c.branch(4,'poll')
    c.data.extend(setflag(request_id,False))
    c.data.extend(setflag(moved_id,True));c.data.extend(bytes.fromhex('09181a01bd19001e1800be19001a0000'));c.data.extend(after);c.label('end');c.data.append(255)
    f=_Assembler();f.data.extend(test(moved_id));f.branch(3,'end');f.data.extend(setflag(request_id,True));f.label('end');f.data.append(255)
    return {'A':a.finish(),'C':c.finish(),'F':f.finish()},{'class_id':298,'source_map':2,'source_entity':9,
        'removed_flags':['0379','8064'],'moved_id':moved_id,'request_id':request_id,'excluded_room_gate':'Player-specific tile16,24,height13, source3B/4B puzzle condition',
        'movement':'right24pixels, animation1, native shared speed128, idle0; one slide per session state',
        'memory_card_persistent':False,'gameplay_verified':False}
