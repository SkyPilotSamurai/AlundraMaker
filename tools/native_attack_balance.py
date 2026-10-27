"""Native-matched animation-to-BALANCE attack routing, not a full combat model.

Animation IDs route to existing power/attribute pairs. The fallback pair is
shared across animations; it is not universally proved to mean contact damage.
"""
import hashlib
import struct
from alundra_memory import parse_exe
from enemy_definition import BalanceTable
from native_save_coverage import STOCK_SHA256

SITES={
 0x80039434:(0x8E0501C4,),
 0x80039464:(0x90A3000E,0x00000000,0x10600009,0x24C20001,0x0043102A,
             0x10400004,0x00061040,0x00451021,0x0800E526,0x24420011,
             0x0800E526,0x24A2000F,0x00001021,0xAE0201C8),
 0x800455DC:(0x90870000,0x00000000,0x10E00068,0x30E2000F,0x00A21021,
             0x90490002,0x00000000,0x312300C0),
 0x80045614:(0x90880001,0x30E20080,0x10400021,0x01090018,
             0x3C028015,0x8C4233B0,0x00002821,0x244A0001,0x00021040,
             0x2447000F,0x3C01801F,0x00250821,0x8C239E68),
 0x80045654:(0x9062000E,0x00000000,0x10400007,0x0142102A,0x10400003,
             0x00671021,0x080115A0,0x24420002,0x080115A0,0x2462000F,
             0x00001021,0x10400004,0x00000000,0x90420001,0x00000000,
             0x01024021,0x24A50008,0x28A20018,0x1440FFE7,0x01090018),
 0x800456A4:(0x00005812,0x000B1903,0x14600003,0x0066102A,0x24030001,
             0x0066102A,0x10400002,0x00002821,0x00C32823),
 0x800455FC:(0x10600005,0x24020040,0x10620049,0x00C01021,0x080115E3,0x00000000),
 0x8004572C:(0x3C02801B,0x8C42C6C8,0x00000000,0x04410014,0x00001021,
             0x3C02801B,0x8C42C6CC,0x00000000,0x30420800,0x1040000E,0x00001021),
 0x80045780:(0x080115E3,0x00000000,0x00C01021,0x03E00008,0x00000000),
}


def analyse_native(exe):
    if hashlib.sha256(exe).hexdigest()!=STOCK_SHA256:
        raise ValueError('Native attack routing requires fingerprinted stock ALUN_CD.EXE')
    header=parse_exe(exe);rows=[]
    for pc,words in SITES.items():
        offset=pc-header['load_address']+0x800
        raw=struct.pack('<'+'I'*len(words),*words)
        if exe[offset:offset+len(raw)]!=raw:raise ValueError(f'Attack site mismatch at {pc:08X}')
        rows.append(dict(virtual_address=f'0x{pc:08X}',exe_offset=f'0x{offset:X}',
                         words=[f'{w:08X}' for w in words]))
    return dict(module='ALUN_CD.EXE',sha256=STOCK_SHA256,
        build='Local USA-labelled Rev1 input, exact fingerprint',native_sites=rows,
        routing='count zero => null; animation+1 < count => pair animation+1; otherwise pair0',
        record_attack_count_offset=14,record_pairs_offset=15,pair_size=2,
        native_attribute_width_bits=8,native_power_width_bits=8,
        entity_balance_pointer_offset='0x1C4',entity_attack_pointer_offset='0x1C8',
        native_pointer_width_bits=32,equipped_animation_id_address='0x801533B0',
        equipped_balance_pointer_base='0x801E9E68',equipped_record_stride=8,equipped_slots=3,
        runtime_verified=False,contact_damage_identity_proven=False,
        weapon_charge_threshold_address=None,
        limitations=['Selected native routing/damage slices, not complete combat/AI',
                     'Fallback pair0 is shared, not universally contact damage',
                     'No charge duration or attack collision classification established'])


def selected_attack(record,animation):
    if type(animation) is not int or not 0<=animation<=0x7ffffffe:
        raise ValueError('Animation must be a nonnegative native signed index')
    attacks=record['attacks'];count=len(attacks)
    if not count:return None
    index=animation+1 if animation+1<count else 0
    pair=attacks[index]
    return dict(pair,index=index,attribute_offset=record['offset']+15+index*2,
                power_offset=record['offset']+16+index*2,fallback=index==0,
                uses_equipment_power=bool(pair['attribute']&0x80),
                response_type=pair['attribute']&15)


def catalogue_entries(report):
    common=dict(module=report['module'],module_sha256=report['sha256'],
                build=report['build'],runtime_verified=False,
                confidence='Native exact-site instructions and derived routing',
                limitations=report['limitations'])
    result=[]
    rows=(
        ('routing','Code / Native combat','Per-animation balance pair routing',
         '0x80039464..0x80039498',dict(address_space='PS1 virtual code / EXE offsets',
             references=['0x80039434 balance pointer load','0x80039498 attack pointer store'],
             native_sites=report['native_sites'][:2],routing=report['routing'])),
        ('damage','Code / Native combat','Selected scalar damage and equipped power paths',
         '0x800455DC..0x800456C4',dict(address_space='PS1 virtual code / EXE offsets',
             native_sites=report['native_sites'][2:],native_power_width_bits=8,
             native_attribute_width_bits=8,scope='Selected bounded slices; entire combat unresolved')),
        ('player-animation','RAM / Native combat','Player animation used to select equipped item powers',
         '0x801533B0',dict(address_space='PS1 virtual RAM / physical RAM',native_access_width_bits=32,
             references=['0x80045624 LUI / 0x80045628 LW'])),
        ('equipped-pointers','RAM / Native combat','Equipped balance-record pointers',
         '0x801E9E68,0x801E9E70,0x801E9E78',dict(address_space='PS1 virtual RAM / physical RAM',
             native_access_width_bits=32,references=['0x8004563C..0x80045644','0x80045694..0x8004569C'],
             stride_bytes=8,count=3,other_word_meaning='unknown in this pass')),
        ('entity-balance','RAM / Native entity fields','Entity balance-record pointer',
         'entity+0x1C4',dict(address_space='Relative native entity field',native_access_width_bits=32,
             references=['0x80039434 LW'])),
        ('entity-attack','RAM / Native entity fields','Entity current attack-pair pointer',
         'entity+0x1C8',dict(address_space='Relative native entity field',native_access_width_bits=32,
             references=['0x80039498 SW'])),
    )
    for key,group,name,address,details in rows:
        result.append(dict(id='native-attack-20261005:'+key,group=group,name=name,
            addresses=address,status='Static evidence; no gameplay validation',
            source='data/2026-10-05-native-animation-attack-routing.json',details=dict(common,**details)))
    return result


def attack_edit(session,entry,tier,animation,*,power=None,attribute=None,allow_shared_fallback=False):
    """Change existing pair with undo. Explicit opt-in required for shared fallback."""
    table=BalanceTable(session.data);record=table.record(entry,tier)
    selection=selected_attack(record,animation)
    if selection is None:raise ValueError('Record has no native attack pairs')
    if selection['fallback'] and not allow_shared_fallback:
        raise ValueError('Animation uses shared fallback pair0; edit affects other fallback animations')
    attacks=[dict(a) for a in record['attacks']]
    if power is not None:attacks[selection['index']]['power']=power
    if attribute is not None:attacks[selection['index']]['attribute']=attribute
    offset,raw=table.replacement(entry,tier,attacks=attacks)
    session.replace(offset,raw,'Native animation attack power / attribute')
    return dict(selection,alias_entries=record['alias_entries'],
                scope='Existing balance pair; every user of aliased record')


def target_response(record,attribute):
    """Native record+2+(attribute&15); no fabricated extra response slots."""
    if type(attribute) is not int or not 0<=attribute<=255:
        raise ValueError('Attack attribute must be a byte')
    slot=attribute&15
    if slot==0:return record['max_hp']
    if slot>11:raise ValueError('Attribute selects beyond the decoded native response fields')
    return record['damage_responses'][slot-1]


def damage_preview(record,animation,response,hp,equipped_records=(),*,equipment_animation=None):
    """Reproduce selected native scalar path. No collision, invulnerability or AI."""
    if type(response) is not int or not 0<=response<=255:raise ValueError('Response must be a byte')
    if type(hp) is not int or not 0<=hp<=0x7fffffff:raise ValueError('HP must be a nonnegative signed word')
    if len(equipped_records)>3:raise ValueError('Native equipped balance loop has only three slots')
    attack=selected_attack(record,animation)
    if attack is None or attack['attribute']==0:return dict(hp_after=hp,damage=0,mode='no-effect')
    mode=response&0xc0
    if mode==0x40:return dict(hp_after=0,damage=hp,mode='instant-zero-hp')
    if mode!=0:return dict(hp_after=hp,damage=0,mode='non-damaging-response')
    power=attack['power']
    if attack['uses_equipment_power']:
        if equipped_records and equipment_animation is None:
            raise ValueError('Equipment power needs the separate native player animation index')
        for item in equipped_records:
            selected=selected_attack(item,equipment_animation) if item else None
            if selected:power+=selected['power']
    damage=max(1,power*response>>4)
    return dict(hp_after=max(0,hp-damage),damage=damage,combined_power=power,
                mode='scalar-damage',note='Damage may exceed current HP; no collision or scheduler model')
