"""Recovered route interruption composition and retained failed queued prototype."""
from event_logic_compile import _Assembler, compile_speaker_dialogue
from project_state_runtime import compile_project_command, compile_project_condition
from native_default_route_profile import compile_default_route

def compile_immediate_interaction(data,catalogue,command,registry,busy,text_ref,*,map_id,reward,slot=None):
    from native_npc_continuation import compile_fixed_npc_handoff
    programs,_=compile_default_route(data,catalogue,command,map_id=map_id)
    def flag(value):return compile_project_command({'type':'set_switch','switch_scope':'project','switch_id':busy,'value':value},registry)
    interaction=_Assembler()
    interaction.data.extend(compile_project_condition({'type':'switch','switch_scope':'project','switch_id':busy,'value':True},registry))
    if slot is not None and (type(slot) is not int or not 0<=slot<16):raise ValueError('Snapshot slot must be0..15')
    snapshot=b'\xe6' if slot is None else bytes((0xE6,slot))
    restore=b'\xe7' if slot is None else bytes((0xE7,slot))
    interaction.branch(3,'end');interaction.data.extend(snapshot+flag(True))
    body=bytes.fromhex('1a0000')+compile_speaker_dialogue(0x80,text_ref)+b'\x39'+reward+flag(False)+restore+b'\xff'
    interaction.data.extend(compile_fixed_npc_handoff(body));interaction.label('end');interaction.data.append(255)
    programs['F']=interaction.finish()
    return programs,{'kind':'experimental-immediate-default-dialogue','catalogue':catalogue,'busy':busy,'snapshot_slot':slot,
        'snapshot_restore_opcodes':['E6','E7'],'dialogue_chain':True,'runtime_verified':False,
        'limits':['New authored MIPS, not vanilla opcodes',
                  'Single owner scratch' if slot is None else 'Indexed private snapshot for this authored instance',
                  'Independent runtime verification required for arbitrary placements']}

def compile_interaction(data,catalogue,command,registry,request,busy,text_ref,*,map_id,reward):
    programs,_=compile_default_route(data,catalogue,command,map_id=map_id)
    def condition(identifier):
        return compile_project_condition({'type':'switch','switch_scope':'project','switch_id':identifier,'value':True},registry)
    def set_flag(identifier,value):
        return compile_project_command({'type':'set_switch','switch_scope':'project','switch_id':identifier,'value':value},registry)
    interaction=_Assembler();interaction.data.extend(condition(busy));interaction.branch(3,'end')
    interaction.data.extend(condition(request));interaction.branch(3,'end')
    interaction.data.extend(set_flag(request,True));interaction.label('end');interaction.data.append(255)
    controller=_Assembler();controller.label('loop');controller.data.extend(programs['C'][:-4])
    controller.data.extend(condition(request));controller.branch(4,'loop')
    controller.data.extend(set_flag(busy,True)+set_flag(request,False))
    controller.data.extend(bytes.fromhex('1a0000')+compile_speaker_dialogue(0x80,text_ref)+b'\x39')
    controller.data.extend(reward+set_flag(busy,False));controller.branch(2,'loop');controller.data.append(255)
    return {'C':controller.finish(),'F':interaction.finish()}, {'kind':'experimental-default-route-dialogue',
        'catalogue':catalogue,'interaction_boundary':'Completed right/left loop','request':request,'busy':busy,
        'dialogue_chain':True,'speed_percent':100,'runtime_verified':False,
        'limits':['No immediate mid-leg interruption','Private state injected; original flags unchanged',
                  'No FacePlayer opcode claim','Empty-Contents production guard remains']}
