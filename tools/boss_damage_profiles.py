"""Boss resistance profiles from existing BALANCE bytes, not invented formulas."""
import hashlib
from enemy_definition import BalanceTable, BALANCE_SHA256
from native_attack_balance import damage_preview
from enemy_combat_fields import combat_fields, native_evidence

BOSSES={509:'Zorgia',479:'Dark Dragon',418:'Melzas',463:'Final Melzas'}
# These associations are pinned-source reported, not native function boundaries.
SOURCE_HANDLERS={509:dict(line=441,handler='AI_FUN_8007e2a0',reaction_animation=8),
    479:dict(line=714,handler='AI_FUN_8007e628',reaction_animation=7),
    418:dict(line=764,handler='AI_FUN_8007e754',reaction_animation=7),
    463:dict(line=1025,handler='AI_FUN_8007eb58',reaction_animation=1)}


def boss_profile(balance_data,index,tier=0):
    if index not in BOSSES:raise ValueError('Choose a researched boss catalogue identity')
    table=BalanceTable(balance_data);record=table.record(index,tier)
    # A synthetic attack record supplies already-combined power, so the preview
    # does not silently assume equipment/charge state or a player animation.
    incoming=[]
    for response in combat_fields(balance_data,index,tier)['incoming_responses']:
        samples=[]
        for power in (8,16,32,64):
            attack=dict(offset=0,max_hp=1,damage_responses=[16]*11,
                attacks=[dict(attribute=response['attack_type_index'],power=power)])
            sample=damage_preview(attack,0,response['raw'],record['max_hp'])
            sample['combined_power']=power
            samples.append(sample)
        incoming.append(dict(response,samples=samples))
    return dict(catalogue_index=index,name=BOSSES[index],tier=tier,
        balance_sha256=hashlib.sha256(balance_data).hexdigest(),record=record,
        incoming_responses=incoming,source_handler=SOURCE_HANDLERS[index],
        formula='max(1, floor(combined incoming power * response /16)) for scalar response',
        stock_power_pair_shared=len(record['attacks'])==1,
        controls=dict(max_hp='record+2 unsigned byte',
            incoming_response='record+3..13 existing bytes, editor incoming-response helper',
            outgoing_attack_power='existing pair power bytes; emitted actors use their own records'),
        separate_boss_formula_identified=False,code_patch_required_for_response_edit=False,
        limitations=['Hit/collision/AI vulnerability windows not simulated',
                     'Source handler association is not a newly verified native callback boundary',
                     'No independent charged-hit cap or defense scalar proved'])


def research_report(exe,balance_data):
    if hashlib.sha256(balance_data).hexdigest()!=BALANCE_SHA256:
        raise ValueError('Stock profile evidence needs fingerprinted original BALANCE.BIN')
    return dict(native=native_evidence(exe),balance_module='BALANCE.BIN',
        balance_sha256=BALANCE_SHA256,
        profiles=[boss_profile(balance_data,i) for i in BOSSES],runtime_verified=False)
