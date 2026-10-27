"""Readable names for BALANCE.BIN attack attribute bytes.

Byte layout (native collision code; same reading as xcasadio BalanceAttack.cs,
commit 242b09a2, and our 2026-10-05 combat-field notes):
* 0              no attack: this animation's hitbox does not hurt anything.
* bits 0-3       attack type. It picks which of the target's 11 damage
                 responses is used (type n -> response n-1). 1..11 below.
                 Types 6/10 also show the burn effect, 7/9 the freeze effect.
* bit 7 (0x80)   adds the power of equipped items to the attack power.
* bits 4-6       never set in the stock US file; meaning unknown.
"""
import re

ATTACK_TYPES = {
    1: 'Sword / Neutral', 2: 'Flail', 3: 'Bow', 4: 'Bomb', 5: 'Tackle', 6: 'Fire', 7: 'Ice',
    8: 'Earth Magic', 9: 'Water Magic', 10: 'Fire Magic', 11: 'Wind Magic',
}
EQUIPMENT_BIT = 0x80
EQUIPMENT_SUFFIX = ' + Equipment Power'
NONE_LABEL = 'None (No Attack)'


def attribute_label(value):
    value = int(value)
    if not 0 <= value <= 255:
        raise ValueError('Attack attribute must be 0..255')
    if value == 0:
        return NONE_LABEL
    kind = value & 0x0F
    known = kind in ATTACK_TYPES and not value & 0x70
    if not known:
        return f'Unknown ({value})'
    return ATTACK_TYPES[kind] + (EQUIPMENT_SUFFIX if value & EQUIPMENT_BIT else '')


def attribute_choices(current=None):
    """Label -> byte, in a stable order. An unusual current value is kept as Unknown (n)."""
    values = [0] + list(ATTACK_TYPES) + [EQUIPMENT_BIT | k for k in ATTACK_TYPES]
    if current is not None and int(current) not in values:
        values.append(int(current))
    return {attribute_label(v): v for v in values}


def parse_attribute(text):
    """Accept a label from attribute_choices or a plain number (decimal or 0x..)."""
    text = str(text).strip()
    if text == NONE_LABEL:
        return 0
    match = re.fullmatch(r'Unknown \((\d+)\)', text)
    if match:
        return int(match.group(1))
    for value, name in ATTACK_TYPES.items():
        if text == name:
            return value
        if text == name + EQUIPMENT_SUFFIX:
            return EQUIPMENT_BIT | value
    try:
        value = int(text, 0)
    except ValueError:
        raise ValueError(f'Unknown attack attribute: {text}') from None
    if not 0 <= value <= 255:
        raise ValueError('Attack attribute must be 0..255')
    return value


def attribute_box(parent, variable, value, width=26):
    """Read-only dropdown bound to variable (which holds the label)."""
    from tkinter import ttk
    variable.set(attribute_label(value))
    return ttk.Combobox(parent, textvariable=variable, values=list(attribute_choices(value)),
                        state='readonly', width=width)
