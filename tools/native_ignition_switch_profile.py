"""Bounded map58 ignition307 reconstruction, retaining native hit dispatch.

Private per-instance state replaces flags016D/8064. ClassA, ignition animation
and native wait sequence are retained. Isolated fixtures observed Sword and
Fire Wand ignition plus ordered money. Production export is separately checked;
no F hook is installed and fire-only filtering is not claimed.
"""
import hashlib
from event_logic_compile import _Assembler,compile_logic
from project_state_runtime import compile_project_command,compile_project_condition
SOURCE_HASHES={'record':'a7edd6c4e76c02690eba4f02496f35a3a3646cef9356e4ba7ea759f869c502bb',
 'C 1':'357cf1ab3d7c3e9c2e429dfe2bb55af69ed3f96c2312366d3d26a7a5740a0d39',
 'D 1':'ab5c7a22203fd3a388bf9bd789cb851ac030347e0b14cf93284af471898bc132'}


def verify_source(datas):
    from native_class_placement import record_cluster
    from editor_session import EditSession
    from event_editor import instructions
    record=record_cluster(datas,58)['entities'][1]
    hashes={'record':hashlib.sha256(record).hexdigest()}
    session=EditSession.readonly(datas)
    for key in ('C 1','D 1'):
        code=b''.join(bytes(datas[p:p+n]) for p,_,n in instructions(session,58,key))
        hashes[key]=hashlib.sha256(code).hexdigest()
    if hashes!=SOURCE_HASHES:raise ValueError('Ignition switch307 donor controller differs')
    return hashes


# Attack element (command 87) = attack type - 1: Bombable Rock 243 checks element 3
# (bombs, type 4); Fireball (fire wand) attacks with type 6, Ice Ball (ice wand) 7.
# The game's own torches (maps 92, 303, 337, 343, 444, 446...): 87 80 06 lights, 87 80 07 puts out.
FIRE_ELEMENT, ICE_ELEMENT, BOMB_ELEMENT = 6, 7, 3


def compile_ignition_switch(registry,latch_id,request_id,commands=None,*,leaf_emitter=None,off_request_id=None,allow_bomb=False,release_commands=None):
    """The fire wand lights it (runs the Activate contents), the ice wand puts it
    out again; with Bomb Activation a bomb lights it too. Other weapons do nothing."""
    if latch_id==request_id:raise ValueError('Ignition latch and hit request need separate switches')
    for identifier in (latch_id,request_id)+((off_request_id,) if off_request_id is not None else ()):registry.get('switches',identifier)
    def state(identifier,value,condition=False):
        row={'type':'switch' if condition else 'set_switch','switch_scope':'project',
             'switch_id':identifier,'value':value}
        return (compile_project_condition if condition else compile_project_command)(row,registry)
    c=_Assembler();c.data.extend(state(latch_id,True,True));c.branch(3,'already')
    c.label('unlit');c.data.extend(bytes((0x1A,0,0x2A)))
    c.label('poll');c.data.append(0);c.data.extend(state(request_id,True,True));c.branch(4,'poll')
    c.data.extend(state(request_id,False))
    if off_request_id is not None:c.data.extend(state(off_request_id,False))
    # Native BD2700 remains the stock u16 audio call (the game's ignition sound).
    c.data.extend(bytes.fromhex('2bbd27001a021c012b1a01'))
    c.data.extend(state(latch_id,True))
    def emit(row):
        if row.get('switch_scope')=='project' or row.get('variable_scope')=='project':
            return compile_project_command(row,registry)
        if leaf_emitter:return leaf_emitter(row)
        raise ValueError('Unverified ignition continuation leaf')
    continuation=compile_logic(commands or [],leaf_emitter=emit,
        project_condition_emitter=lambda row:compile_project_condition(row,registry))
    c.data.extend(continuation)
    if off_request_id is None:
        c.data.append(0);c.data.append(0xFF)
        c.label('already');c.data.extend(bytes((0x1A,1,0xFF)))
    else:
        # lit: stays hittable; the ice wand puts it out and it can be lit again
        c.label('already');c.data.extend(bytes((0x1A,1,0x2A)))
        c.label('lit_poll');c.data.append(0);c.data.extend(state(off_request_id,True,True));c.branch(4,'lit_poll')
        c.data.extend(state(off_request_id,False));c.data.extend(state(request_id,False));c.data.extend(state(latch_id,False))
        c.data.extend(bytes((0x1A,0)))
        c.data.extend(compile_logic(release_commands or [],leaf_emitter=emit,
            project_condition_emitter=lambda row:compile_project_condition(row,registry)))   # Deactivate actions
        c.branch(2,'unlit')
    da=_Assembler()
    checks=[(FIRE_ELEMENT,request_id)]+([(BOMB_ELEMENT,request_id)] if allow_bomb else [])+([(ICE_ELEMENT,off_request_id)] if off_request_id is not None else [])
    for n,(element,target) in enumerate(checks):
        da.data.extend(bytes((0x87,0x80,element)));da.branch(4,f'next{n}');da.data.extend(state(target,True));da.label(f'next{n}')
    da.data.append(0xFF);d=da.finish()
    return {'C':c.finish(),'D':d},{'class_id':307,'donor_map':58,'donor_entity':1,
        'native_flags_replaced':['016D','8064'],'latch_id':latch_id,'request_id':request_id,
        'native_reaction':'ClassA collision D hit dispatch; C animation0→2→1 with1C01 wait',
        'source_hashes':SOURCE_HASHES,'continuation_length':len(continuation),
        'gameplay_verified':False,'memory_card_persistent':False,
        'activation':'fire wand'+(' or bomb' if allow_bomb else '')+('; ice wand puts it out' if off_request_id is not None else ''),
        'observed_attack_families':['Sword','Fire Wand'],
        'uncertainties':['Other attack families not tested; fire-only behavior is not claimed',
                         'BD0027 sound identity not named','No release/reset behavior claimed']}
