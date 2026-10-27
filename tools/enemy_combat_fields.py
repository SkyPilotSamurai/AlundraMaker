"""Native BALANCE response bytes; no fabricated defense/contact-damage field."""
from native_attack_balance import analyse_native, selected_attack
from enemy_definition import BalanceTable

SOURCE_COMMIT='242b09a20ae1186c90278ba5f15f0f9a84104ef4'
SOURCE_ATTACK_TYPES=('Sword','Hammer','Arrow','Bom','Tackle','Fire','Ice',
                     'Earth Magic','Water Magic','Fire Magic','Wind Magic')
ATTACK_LABELS=('Sword / Neutral','Flail','Bow','Bomb','Tackle','Fire','Ice',
               'Earth Magic','Water Magic','Fire Magic','Wind Magic')
MODES={0:'scalar',0x40:'zero_hp',0x80:'skip_80',0xc0:'skip_c0'}


def decode_response(raw):
    if type(raw) is not int or not 0<=raw<=255:
        raise ValueError('Response must be an unsigned native byte')
    flags=raw&0xc0;factor=raw&0x3f
    return dict(raw=raw,mode=MODES[flags],flags=flags,factor_numerator=factor,
        factor_denominator=16,scalar_factor=factor/16 if flags==0 else None,
        minimum_damage=1 if flags==0 else None,
        scalar_path_effect='Subtract scaled power, at least one HP' if flags==0 else
            'Set HP to zero' if flags==0x40 else 'Preserve HP in this scalar calculation',
        collision_mode_basis='0x80 suppresses candidate collision in pinned source; 0xC0 differs',
        unknown='Complete collision/AI behavior is not represented by the scalar preview')


def encode_response(mode,factor_numerator):
    flags=next((bits for bits,label in MODES.items() if label==mode),None)
    if flags is None:raise ValueError('Choose scalar, zero_hp, skip_80 or skip_c0')
    if type(factor_numerator) is not int or not 0<=factor_numerator<=63:
        raise ValueError('Native response factor is 0..63 over denominator16')
    return flags|factor_numerator


def combat_fields(balance_data,entry,tier=0):
    record=BalanceTable(balance_data).record(entry,tier)
    responses=[dict(attack_type_index=i,source_label=SOURCE_ATTACK_TYPES[i-1],
        label_basis='Pinned source StaticVariables.cs:469; label mapping not runtime verified',
        offset=record['offset']+2+i,**decode_response(raw))
        for i,raw in enumerate(record['damage_responses'],1)]
    return dict(entry=entry,tier=tier,max_hp=record['max_hp'],
        max_hp_offset=record['offset']+2,fields_width_bits=8,
        incoming_responses=responses,attacks=record['attacks'],
        alias_entries=record['alias_entries'],defense_field=None,contact_damage_field=None,
        contact_note='Collision uses current animation-selected attack pair; independent contact field unproven')


def edit_response(session,entry,tier,attack_type_index,*,mode,factor_numerator):
    if type(attack_type_index) is not int or not 1<=attack_type_index<=11:
        raise ValueError('Response type must be1..11; type0 aliases maxHP and is not a resistance')
    record=BalanceTable(session.data).record(entry,tier)
    responses=list(record['damage_responses'])
    raw=encode_response(mode,factor_numerator);responses[attack_type_index-1]=raw
    offset,payload=BalanceTable(session.data).replacement(entry,tier,damage_responses=responses)
    session.replace(offset,payload,'Native incoming damage response')
    return dict(entry=entry,tier=tier,attack_type_index=attack_type_index,
        offset=record['offset']+2+attack_type_index,alias_entries=record['alias_entries'],
        **decode_response(raw))


def contact_attack_for_animation(balance_data,entry,tier,animation):
    """Expose actual routing, explicitly without assigning a universal contact slot."""
    selected=selected_attack(BalanceTable(balance_data).record(entry,tier),animation)
    return dict(selection=selected,contact_identity_proven=False,
                scope='Current animation pair, shared fallback if count insufficient')


def native_evidence(exe):
    matched=analyse_native(exe)
    return dict(module=matched['module'],sha256=matched['sha256'],
        native_sites=matched['native_sites'],source_commit=SOURCE_COMMIT,
        scalar_formula='max(1, (combined_power * response_byte) >> 4) when response&0xC0==0',
        modes=dict(MODES),native_width_bits=8,defense_field_proven=False,
        contact_damage_field_proven=False,runtime_verified=False,
        source_paths=['AlundraTools/AlundraEngine/Gameplay/EntityManager.cs:1235..1318',
                      'AlundraTools/AlundraEngine/Gameplay/EntityManager.cs:559..584',
                      'AlundraTools/AlundraEngine/StaticVariables.cs:469'])
