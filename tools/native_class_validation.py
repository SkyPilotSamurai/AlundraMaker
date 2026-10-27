"""Reject authoring-only class edits when a graph installs an actor/item."""


def require_native_class_definition(session, definition, *, allow_map_class_hue=False):
    from content_database import TEMPLATES
    kind = definition.get('kind')
    data = definition.get('data', {})
    source = definition.get('source', {})
    baseline = source.get('native_data_baseline', {})
    defaults = TEMPLATES.get(kind, {})
    tiers = data.get('balance_tiers', [])
    balance = getattr(session, 'extra_files', {}).get('DATA/BALANCE.BIN')
    entry = source.get('balance_entry')
    if balance is not None and type(entry) is int:
        from enemy_definition import BalanceTable
        record = BalanceTable(balance.data).record(entry, 0)
        native_stats = {'max_hp': record['max_hp'], 'attacks': record['attacks'],
                        'damage_responses_raw': record['damage_responses']}
    elif tiers:
        native_stats = {'max_hp': tiers[0].get('max_hp'), 'attacks': tiers[0].get('attacks_raw'),
                        'damage_responses_raw': tiers[0].get('damage_responses_raw')}
    else:
        native_stats = {}
    for key, value in data.items():
        if key == 'palette_shift' and allow_map_class_hue:
            if not isinstance(value, dict) or set(value) - {'hue_degrees', 'saturation_percent'}:
                raise ValueError('Native palette fork only supports hue_degrees and saturation_percent')
            continue
        if key == 'palette_shift' and isinstance(value, dict) and not value.get('hue_degrees', 0) and value.get('saturation_percent', 100) == 100:
            continue   # unchanged colours
        if key == 'custom_ai':
            continue   # built by native_custom_ai (Edit AI > Custom)
        if key in ('speed_percent', 'move_speed_percent', 'spawn_attacks', 'ai_movement', 'ai_idle_animation'):   # ai_*: Edit AI (NPC stand still) built by the event compiler
            continue   # installed per map by class_looks (frame delays)
        if key in ('notes', 'contained_item_class_id', 'while_pressured', 'dialogue_voice', 'heal_divisor', 'heal_at_least', 'heal_amount', 'magic_spawns'):   # dialogue_voice: a text control code (npc_voices)   # while_pressured: built by the step-on switch controller
            continue
        if key == 'balance_tiers':
            if key in baseline and value != baseline[key]:
                raise ValueError('Class balance tier edits are not installed by actor placement; use the native balance editor')
            continue
        if key in native_stats and value == native_stats[key]:
            continue
        expected = baseline.get(key, defaults.get(key))
        if key in baseline and value != expected:
            raise ValueError(f"{definition.get('name', definition.get('id', 'Class'))}: changed class setting {key} is not compiled into the native game yet")
        if value == expected or value is None or value == [] or value == {} or value == '':
            continue
        raise ValueError(f"{definition.get('name', definition.get('id', 'Class'))}: class setting {key} is not compiled into the native game yet")
