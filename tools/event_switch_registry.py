"""Named bindings for existing initialized native flags; never auto-allocate.

Native mask arithmetic addresses4096bytes but both reset routines initialize
only256bytes. No static non-reference survey proves a spare/save-persistent bit.
See docs/2026-10-05-native-switch-bank-bounds.txt.
"""
from copy import deepcopy
from native_flags import locate_flag


def validate_native_flag_operand(value):
    if type(value) is not int or not 0 <= value <= 0xFFFF or value & 0x7FFF > 0x7FF:
        raise ValueError('Choose an initialized native flag: 0000..07FF or 8000..87FF')
    return value


class EventSwitchRegistry:
    def __init__(self, entries=()):
        self.entries = {}
        for entry in entries:
            self.bind(entry['switch_id'], entry['name'], entry['native_flag_operand'],
                      evidence=entry.get('evidence'), purpose=entry.get('purpose'))

    def bind(self, switch_id, name, native_flag_operand, *, evidence, purpose):
        """Bind an explicit existing game flag, preserving the binding's intent.

        Evidence must identify its source and purpose must explain intentional
        game-state use. Neither field certifies an unused flag or memory-card
        persistence. Registry refuses assigning two project IDs to one flag.
        """
        if type(switch_id) is not int or not 0 <= switch_id <= 65535:
            raise ValueError('Project switch ID must be 0..65535')
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Switch needs a name')
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError('Existing game flag binding needs evidence')
        if not isinstance(purpose, str) or not purpose.strip():
            raise ValueError('Explain the intentional use of this existing game flag')
        operand = validate_native_flag_operand(native_flag_operand)
        if any(k != switch_id and r['native_flag_operand'] == operand for k, r in self.entries.items()):
            raise ValueError('Native flag already belongs to another named project switch')
        native = locate_flag(operand)
        row = dict(switch_id=switch_id, name=name.strip(), native_flag_operand=operand,
                   evidence=evidence.strip(), purpose=purpose.strip(),
                   bank='temporary' if native['bank'] else 'persistent',
                   word_address=native['word_address'], word_mask=native['word_mask'],
                   lifetime='map-reset' if native['bank'] else 'game-state; native save staging coverage proven, save/reload behavior unverified',
                   status='explicit existing-game binding; not allocated new memory')
        self.entries[switch_id] = row
        return deepcopy(row)

    def resolve(self, command):
        explicit = command.get('native_flag_operand')
        if explicit is not None:
            return validate_native_flag_operand(explicit)
        switch_id = command.get('switch_id')
        if type(switch_id) is not int or switch_id not in self.entries:
            raise ValueError('Select a named switch bound to an existing game flag')
        return self.entries[switch_id]['native_flag_operand']

    def export(self):
        return [deepcopy(self.entries[k]) for k in sorted(self.entries)]

    def allocate(self, *args, **kwargs):
        raise ValueError('Automatic new game flag allocation is not proven; use an evidenced existing flag or an injected private-state backend')
