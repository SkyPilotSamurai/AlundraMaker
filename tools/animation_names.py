"""Names for a class's animations (user 2026-10-11): your own names first
(saved in the project), else Alundra's known names, else a name worked out
from the game data: Attack (the animation has a damaging attack pair),
Walking (it moves), Idle (still and looping), or an action that plays once."""


def auto_names(session, row, choices, balance_data=None):
    from player_attacks import PLAYER_ANIMATIONS, words
    index = row.get('source', {}).get('catalogue_index')
    if row.get('kind') in ('player', 'weapon') or index == 0:
        out = {}
        for r in choices:
            label = PLAYER_ANIMATIONS.get(r['index'])
            out[r['index']] = words(label) if label and not label.startswith('Reserved') else ''
        return out
    attacks = []
    entry = row.get('source', {}).get('balance_entry')
    if balance_data is not None and type(entry) is int:
        try:
            from enemy_definition import BalanceTable
            attacks = BalanceTable(balance_data).record(entry, 0)['attacks']
        except Exception:
            attacks = []
    out = {}
    walk = idle = attack = action = 0
    for r in choices:
        a = r['index']
        pair = attacks[a + 1] if a + 1 < len(attacks) else None
        terms = [t for t in r.get('direction_terminators', ()) if t]
        loops = all(t == '01' for t in terms) if terms else True
        if row.get('kind') in ('enemy', 'boss') and pair and pair.get('attribute') and pair.get('power'):
            attack += 1; name = 'Attack' if attack == 1 else f'Attack {attack}'
        elif r.get('native_speed_raw'):
            walk += 1; name = 'Walking' if walk == 1 else f'Walking {walk}'
        elif loops:
            idle += 1; name = 'Idle' if idle == 1 else f'Idle {idle}'
        else:
            nxt = next((t for t in terms if t != '01' and len(t) == 4), None)
            action += 1
            name = f'Action {action}'
            if nxt and nxt[:2] == '00' and nxt != '0080':
                name += f' (then {int(nxt[2:], 16)})'
        out[a] = name
    return out


def class_names(document, class_id):
    return document.setdefault('animation_names', {}).setdefault(class_id, {})


def display_name(document, row, auto, index):
    own = (document.get('animation_names', {}).get(row['id'], {}) or {}).get(str(index))
    name = own or auto.get(index, '')
    return f"{index} - {name}" if name else str(index)
