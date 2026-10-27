"""Recovered lever305 animation controller with private per-instance state.

No donor room flags are retained. Both native open/close animation paths run
authored activation commands after1C01, before clearing the request flag.
This profile is still experimental until placed-object gameplay is verified.
"""
from native_object_controller import rebind_controller
from event_logic_compile import compile_logic
from project_state_runtime import compile_project_command,compile_project_condition

CLASS_ID=305
SOURCE_MAP=22
SOURCE_ENTITY=0
SOURCE_RECORD=bytes.fromhex('2200331e01c2314a0e0400008181000000000000')
CONTROLLER=bytes.fromhex('3002800a002a0002f9ff2b30018011001a031c011a0006028002e7ff1a021c011a0106028002dbffff')
CONTACT=bytes.fromhex('2b320180050280ff')

def verify_source(datas):
    from native_class_placement import record_cluster
    from editor_session import EditSession
    from event_editor import instructions
    if record_cluster(datas,SOURCE_MAP)['entities'][SOURCE_ENTITY]!=SOURCE_RECORD:
        raise ValueError('Lever305 donor record differs from recovered profile')
    session=EditSession.readonly(datas)
    for root,expected in [('C 1',CONTROLLER),('D 1',CONTACT)]:
        found=b''.join(bytes(datas[pos:pos+size]) for pos,_,size in instructions(session,SOURCE_MAP,root))
        if found!=expected:raise ValueError('Lever305 donor controller differs from recovered profile')
    return True

def compile_lever(registry,state_id,request_id,commands=None,*,can_deactivate=False,release_commands=None):
    if state_id==request_id:raise ValueError('Lever state and request need separate switches')
    registry.get('switches',state_id);registry.get('switches',request_id)
    continuation=compile_logic(commands or [],
        leaf_emitter=lambda row:compile_project_command(row,registry),
        project_condition_emitter=lambda row:compile_project_condition(row,registry))
    release=compile_logic(release_commands or [],
        leaf_emitter=lambda row:compile_project_command(row,registry),
        project_condition_emitter=lambda row:compile_project_condition(row,registry))
    bindings={0x8001:state_id,0x8002:request_id}
    # offset 22: the lever goes back (off, Deactivate actions); 34: it is pulled (on, Activate actions)
    c,report=rebind_controller(CONTROLLER,bindings,registry,
        insert_before={22:release,34:continuation})
    d,contact_report=rebind_controller(CONTACT,bindings,registry)
    d=bytes.fromhex('bd3c00')+d   # the lever's click when hit (map 36 copies: BD3C first)
    if not can_deactivate:   # pulled: it stays pulled
        from event_logic_compile import _Assembler
        a=_Assembler();a.data.extend(compile_project_condition({'type':'switch','switch_scope':'project','switch_id':state_id,'value':True},registry))
        # pulled: hit again it stays quiet. The hit is still acknowledged (2B, +6C bit0, as the lever's own
        # contact program does first); skipping it left the game's 'nothing happens' noise (user 2026-10-26)
        a.branch(3,'locked');a.data.extend(d[:-1]);a.branch(2,'end')
        a.label('locked');a.data.append(0x2B);a.label('end');a.data.append(0xFF);d=a.finish()
    return {'C':c,'D':d},{'class_id':CLASS_ID,'source_map':SOURCE_MAP,
        'source_entity':SOURCE_ENTITY,'controller':report,'contact':contact_report,
        'state_id':state_id,'request_id':request_id,'continuation_length':len(continuation),
        'gameplay_verified':False,'memory_card_persistent':False}
