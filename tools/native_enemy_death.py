"""Recovered bounded death-only continuation; native E callback is handed back.

Production enabled only for independently tested callback profiles. HP zero is checked on native logic actor A1. Custom E
is removed using native40 after continuation, retaining native destruction/drop
on the following scheduler tick. Living deactivation must award nothing.
"""
import hashlib
from event_vm_compatibility import STOCK_EXE_SHA256,_read_virtual
from event_logic_compile import _Assembler,compile_logic
from project_state_runtime import compile_project_condition,compile_project_command

TESTED_DEATH_CALLBACKS = {
 329: [('A',1),('C',26),('D',1),('E',1),('F',0)],
 335: [('A',1),('C',1),('D',1),('E',1),('F',0)],
 338: [('A',0),('C',15),('D',12),('E',1),('F',0)],
 341: [('A',0),('C',16),('D',12),('E',1),('F',0)],
 344: [('A',0),('C',17),('D',5),('E',1),('F',0)],
 362: [('A',0),('C',2),('D',2),('E',1),('F',0)],
 365: [('A',0),('C',32),('D',2),('E',1),('F',0)],
 371: [('A',0),('C',34),('D',2),('E',1),('F',0)],
}

SLICES={
 0x80042E2C:bytes.fromhex('2120200221284002213060028010100021105e000000438c'),
 0x80042E5C:bytes.fromhex('09f8600021388002'),
 0x8003AE00:bytes.fromhex('1400228e'), # LW V0,14(S1), actor HP passed to balance.
 0x8003AE8C:bytes.fromhex('140032ae'), # SW S2,14(S1), balance result.
 0x8003F260:bytes.fromhex('0000c38c000000000100629002006590010003241e80013c405f23ac80100200211044004c0045ac0800e00303000224'),
 0x800815C8:bytes.fromhex('e8ffbd271000bfafb9eb000cffff05241000bf8f1800bd270800e00300000000'),
}

def verify_native_contract(exe):
    if hashlib.sha256(exe).hexdigest()!=STOCK_EXE_SHA256:raise ValueError('Death-query recovery requires exact stock main EXE')
    for address,expected in SLICES.items():
        if _read_virtual(exe,address,len(expected))!=expected:raise ValueError('Recovered death contract changed')
    return {'native_hp_width':32,'hp_offset':0x14,'logic_actor_register':'a1',
      'native_E1':0x800815C8,'native_destroy_with_contents':0x8003AEE4,
      'hand_back_opcode':0x40,'hand_back_bank_index':4,'runtime_verified':False}

def emit_hp_zero_query():
    from project_state_runtime import _Mips
    m=_Mips();m.load(8,5,0x14);m.i(11,8,8,1);m.i(43,7,8,0x2c)
    m.i(9,0,2,1);m.words.extend([0x03E00008,0]);return m.finish()

DEATH_ACTIONS = {'change_money','give_item','show_dialogue','set_switch','set_variable','wait','if',
                 'play_sound','stop_sound','change_music','lock_movement','unlock_movement','deactivate_switch',
                 'back_to_title','play_ending','play_movie'}   # Change Map / 0xBB ends (user 2026-10-27)


def compile_death_E(registry,latch_id,commands,*,clear_latch_before_handoff=False,leaf_emitter=None,project_condition_emitter=None):
    condition={'type':'switch','switch_scope':'project','switch_id':latch_id,'value':True}
    registry.get('switches',latch_id)
    a=_Assembler();a.data.extend(compile_project_condition(condition,registry));a.branch(3,'native')
    a.data.append(0xE5);a.branch(4,'native')
    a.data.extend(compile_project_command(dict(condition,type='set_switch'),registry))
    a.data.extend(compile_logic(commands,leaf_emitter=leaf_emitter,project_condition_emitter=project_condition_emitter))
    a.label('native')
    if clear_latch_before_handoff:
        a.data.extend(compile_project_command(dict(condition,type='set_switch',value=False),registry))
    a.data.extend(bytes((0x40,4,0,0xff)))
    return a.finish()
