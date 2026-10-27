"""Event-page commands and conditions that mimic native Alundra event commands.

Each entry is compiled to the game's own command (see native_event_knowledge.py
for what the game does with it). Added 2026-10-12 from the native command usage
counts across all 483 maps.
"""
import struct

# {'life': i, 'magic': i}: the map's healing sparkle effect entries while the
# event compiler builds that map's events (None elsewhere: plain C3).
HEAL_EFFECTS = None
EFFECT_BANKS = 29     # global effect banks (remake/assets/effects/global)
EFFECT_NAMES = {0: 'Shadow', 1: 'Water Ripple', 14: 'Healing Sparkle'}
EFFECT_CHOICES = {f"{n} {EFFECT_NAMES.get(n, 'Effect')}": n for n in range(EFFECT_BANKS)}
SHOW_EFFECTS = None   # {(global effect, animation): map effect index}, set per map by the event compiler

ACTOR = {'This character': 0x80, 'The player': 0x81}
YESNO = {'Yes': True, 'No': False}
BUTTONS = {'Circle (talk / confirm)': 0x20, 'Cross (jump)': 0x40, 'Square (attack)': 0x80, 'Triangle (item)': 0x10,
           'Up': 0x1000, 'Down': 0x4000, 'Left': 0x8000, 'Right': 0x2000, 'L1': 0x04, 'R1': 0x08, 'Start': 0x800}
BUTTON_MODE = {'Being held': 0, 'Just pressed': 1, 'Just released': 2}
COLOURS = {'Black': (0, 0, 0), 'White': (255, 255, 255), 'Dark grey': (32, 32, 32), 'Red': (255, 0, 0)}
# overlay colour and blend of each fade (2 = subtract, 1 = add): black takes all light away, dark grey
# dims (map 199: AF 20 20 20 02), white and red add light
FADES = {'Black': ((255, 255, 255), 2), 'Dark grey': ((32, 32, 32), 2), 'White': ((255, 255, 255), 1), 'Red': ((255, 0, 0), 1)}

# type: (menu label, menu group, defaults, {key: (label, choices or None)})
COMMANDS = {
    # Play Victory: Alundra raises his sword, the victory fanfare plays and the text shows, as when a
    # boss is beaten in the game (tools/boss_victory.py; the event compiler adds the text).
    'play_victory': ('Play Victory', 'Messages', {'text': 'Defeated the boss.'}, {'text': ('Text', None)}),
    # Self Switches A-D: the event's own private switches (never story flags); built as
    # project switches "<event> Self Switch A" by the event compiler (_self_switches).
    'set_self_switch': ('Control Self Switch', 'Game Progression', {'letter': 'A', 'value': True},
        {'letter': ('Self Switch', {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D'}), 'value': ('Turn', {'ON': True, 'OFF': False})}),
    'set_passability': ('Change Tile Passability', 'Map And Timing',
        {'x': 0, 'y': 0, 'width': 1, 'height': 1, 'walkable': False, 'blocks': 'everyone'},
        {'x': ('Tile X', None), 'y': ('Tile Y', None), 'width': ('Width (tiles)', None), 'height': ('Height (tiles)', None),
         'walkable': ('Make the tiles', {'Blocked': False, 'Walkable': True}),
         'blocks': ('Blocks', {'Everyone (walls, gates)': 'everyone', 'Only the player': 'player'})}),
    'copy_map_tiles': ('Change Map Tiles (Open Door / Bridge)', 'Map And Timing',
        {'from_x': 0, 'from_y': 0, 'width': 1, 'height': 1, 'to_x': 0, 'to_y': 0},
        {'from_x': ('Copy from tile X', None), 'from_y': ('Copy from tile Y', None), 'width': ('Width (tiles)', None),
         'height': ('Height (tiles)', None), 'to_x': ('Paste at tile X', None), 'to_y': ('Paste at tile Y', None)}),
    'wait_animation': ('Wait For Animation', 'Characters And Objects', {'times': 1},
        {'times': ('Wait until it has played this many times', None)}),
    'jump_actor': ('Jump', 'Movement', {'target': 0x80, 'height': 16, 'speed': 2, 'fall_back': True},
        {'target': ('Character', ACTOR), 'height': ('Height in pixels (default 16 = one level)', None),
         'speed': ('Rising speed, pixels per frame (default 2)', None),
         'fall_back': ('Fall back down afterwards (default on)', None)}),
    'set_gravity': ('Gravity On / Off', 'Movement', {'on': True},
        {'on': ('Gravity for this character', {'On (falls and lands)': True, 'Off (floats)': False})}),
    'show_effect': ('Show Effect', 'Characters And Objects', {'effect': 14, 'animation': 0, 'target': 0x81, 'dx': 0, 'dy': 0, 'dz': 0},
        {'effect': ('Effect', EFFECT_CHOICES), 'animation': ('Animation', None), 'target': ('At', ACTOR), 'dx': ('X offset (pixels)', None),
         'dy': ('Y offset (pixels)', None), 'dz': ('Height offset (pixels)', None)}),
    'camera': ('Move Camera', 'Map And Timing', {'mode': 'player', 'x': 0, 'y': 0, 'z': 0},
        {'mode': ('Camera', {'Follow the player': 'player', 'Follow this character': 'this', 'Look at a tile': 'tile'}),
         'x': ('Tile X (Look at a tile)', None), 'y': ('Tile Y (Look at a tile)', None), 'z': ('Height (Look at a tile)', None)}),
    'fade_screen': ('Fade Screen', 'Map And Timing', {'colour': 'Black', 'direction': 'out', 'frames': 60, 'wait': True},
        {'colour': ('Colour', {k: k for k in COLOURS}), 'direction': ('Fade', {'To the colour': 'out', 'Back to normal': 'in'}),
         'frames': ('Over frames (60 = 1 second)', None), 'wait': ('Wait until it finishes', None)}),
    # Back To Title / Play Ending (user 2026-10-27). Static, stock US 1.1: a room change's type
    # (0x801F11F8, set by Change Map 0x53 byte 6) is read after the room loads (0x8002C6A8):
    # 11 starts the title program ("title failed to start" message, 0x8002C78C), 9 runs
    # cdrom:\END.EXE, the ending movie and credits (0x8002C70C). 0xBB requests type 9 off map 477
    # (the game-over map) -- how the last map starts the ending.
    'back_to_title': ('Back To Title', 'Other', {}, {}),
    'play_ending': ('Play Ending', 'Game Progression', {}, {}),   # older saves; the menu has Play Movie
    # Play Movie (play_movie.py): ends the game with one of the disc's movies (user 2026-10-27)
    'play_movie': ('Play Movie', 'Other', {'movie': 2},
        {'movie': ('Movie', {'Opening logo': 0, 'Opening': 1, 'Ending (then credits)': 2, 'Credits': 3})}),
    'take_item': ('Take Item', 'Items And Money', {'item_class_id': ''}, {}),
    'pay_money': ('Take Money', 'Items And Money', {'amount': 1}, {'amount': ('Amount', None)}),
    'restore_life': ('Recover All Life And Magic', 'Items And Money', {}, {}),
    'raise_max_mp': ('Raise Maximum Magic', 'Items And Money', {'amount': 1}, {'amount': ('Magic to add', None)}),
    'raise_max_life': ('Raise Maximum Life', 'Items And Money', {'amount': 1}, {'amount': ('Hearts to add', None)}),
    'stop_sound': ('Stop Sound', 'Audio', {'sound_id': 1}, {}),
    'play_sound_volume': ('Play Sound (Volume)', 'Audio', {'sound_id': 1, 'volume': 127},   # new sounds start at max (user 2026-10-26)
        {'volume': ('Volume (0-127)', None)}),
}

# type: (label, defaults, fields)
CONDITIONS = {
    'self_switch': ('Self Switch is ON', {'letter': 'A', 'value': True},
        {'letter': ('Self Switch', {'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D'}), 'value': ('Is ON', YESNO)}),
    'player_area': ('Player is inside an area', {'x1': 0, 'y1': 0, 'x2': 0, 'y2': 0, 'z1': 0, 'z2': 31, 'value': True},
        {'x1': ('Tile X from', None), 'x2': ('Tile X to', None), 'y1': ('Tile Y from', None), 'y2': ('Tile Y to', None),
         'z1': ('Height from', None), 'z2': ('Height to', None), 'value': ('Is inside', YESNO)}),
    'template_gone': ('Map character is gone (defeated / removed)', {'template': 0, 'value': True},
        {'template': ('Map template number', None), 'value': ('Is gone', YESNO)}),
    'button': ('Button is pressed', {'button': 0x20, 'mode': 1, 'value': True},
        {'button': ('Button', BUTTONS), 'mode': ('When', BUTTON_MODE), 'value': ('Is pressed', YESNO)}),
    'random': ('Random chance', {'percent': 50, 'value': True}, {'percent': ('Chance (%)', None), 'value': ('Happens', YESNO)}),
    'money': ('Player has money', {'amount': 1, 'value': True}, {'amount': ('At least', None), 'value': ('Has it', YESNO)}),
    'yes_no': ('Player answers Yes (asks Yes / No)', {'value': True}, {'value': ('Answer is Yes', YESNO)}),
    'chest_opened': ('Chest already opened', {'template': 0, 'value': True},
        {'template': ('Chest map template number', None), 'value': ('Is opened', YESNO)}),
}


def _int(row, key, low, high, label=None):
    v = row.get(key)
    if type(v) is not int or not low <= v <= high:
        raise ValueError(f"{label or key.replace('_', ' ').title()} must be {low}..{high}")
    return v


def validate_command(row):
    compile_command(row, item_resolver=lambda r: 1)


def validate_condition(cond):
    compile_condition(cond)


def compile_command(row, item_resolver=None):
    t = row['type']
    if t == 'set_self_switch':   # (checked here; the event compiler turns it into the event's own switch)
        if row.get('letter') not in ('A', 'B', 'C', 'D') or type(row.get('value')) is not bool:
            raise ValueError('Self Switch must be A, B, C or D, ON or OFF')
        return bytes((0x05, 0x00, 0x80))
    if t == 'play_victory':   # (checked here; the event compiler adds the text and builds it)
        from boss_victory import sequence
        return sequence(0x80, delay=False)
    if t == 'set_passability':
        x, y = _int(row, 'x', 0, 127), _int(row, 'y', 0, 127)
        w, h = _int(row, 'width', 1, 64), _int(row, 'height', 1, 64)
        if w * h > 64: raise ValueError('Change at most 64 tiles per command')
        bits = 0x40 if row.get('blocks', 'everyone') == 'everyone' else 0x01
        op = 0x55 if row.get('walkable') else 0x54
        return b''.join(bytes((op, x + i, y + j, bits, 0)) for j in range(h) for i in range(w))
    if t == 'copy_map_tiles':
        return bytes((0x85, _int(row, 'from_x', 0, 127), _int(row, 'from_y', 0, 127), _int(row, 'width', 1, 64),
                      _int(row, 'height', 1, 64), _int(row, 'to_x', 0, 127), _int(row, 'to_y', 0, 127)))
    if t == 'wait_animation':
        return bytes((0x1C, _int(row, 'times', 1, 255)))
    if t == 'jump_actor':
        # Rise at a steady speed with gravity off, for as many frames as the height needs,
        # then stop and (optionally) turn gravity back on so the character falls.
        sel = row.get('target', 0x80)
        if 'strength' in row and 'height' not in row:          # older saves: speed only
            return struct.pack('<BBh', 0x5E, sel, _int(row, 'strength', 1, 32) * 256)
        height, speed = _int(row, 'height', 1, 2000, 'Height'), _int(row, 'speed', 1, 16, 'Speed')
        frames = -(-height // speed)
        if frames > 255: raise ValueError('Height ÷ speed must be at most 255 frames: raise the speed')
        code = struct.pack('<BBH', 0x63, sel, 0x100) + struct.pack('<BBh', 0x5E, sel, speed * 256)
        code += bytes((0x37, frames)) + struct.pack('<BBh', 0x5E, sel, 0)
        if row.get('fall_back', True): code += struct.pack('<BBH', 0x62, sel, 0x100)
        return code
    if t == 'set_gravity':
        return bytes((0x16 if row.get('on', True) else 0x17,))
    if t == 'show_effect':
        # The game's global effect bank n, animation a: the event compiler adds
        # a waiting entry for it to the map's effect table (A3 starts an entry
        # of that table by index, at the character + offset).
        key = (_int(row, 'effect', 0, EFFECT_BANKS - 1), _int(row, 'animation', 0, 5) if 'animation' in row else 0)
        index = (SHOW_EFFECTS or {}).get(key, 0)
        return struct.pack('<BBBhhh', 0xA3, index, row.get('target', 0x81),
                           _int(row, 'dx', -512, 512), _int(row, 'dy', -512, 512), _int(row, 'dz', -512, 512))
    if t == 'camera':
        mode = row.get('mode', 'player')
        if mode == 'player': return bytes((0x67, 0x81))
        if mode == 'this': return bytes((0x67, 0x80))
        x, y, z = _int(row, 'x', 0, 127), _int(row, 'y', 0, 127), _int(row, 'z', 0, 63)
        return struct.pack('<B3H', 0x69, x * 24 + 12, y * 16 + 8, z * 16)
    if t == 'fade_screen':
        # AF r g b blend frames keep: a full-screen overlay fading to r g b,
        # blended by subtracting (2) or adding (1). The game's own: to black =
        # AF FF FF FF 02 78 01 (subtract white, kept on), back = AF 00 00 00 02 78 00
        # (same blend, gone when it arrives); white uses blend 1. The script then
        # waits until the fade is done (00 B1 04 FE FF, map 030 C29).
        target, blend = FADES.get(row.get('colour'), FADES['Black'])
        frames = _int(row, 'frames', 1, 255)
        out = row.get('direction', 'out') == 'out'
        r, g, b = target if out else (0, 0, 0)
        code = bytes((0xAF, r, g, b, blend, frames, 1 if out else 0))
        if row.get('wait', True): code += bytes((0x00, 0xB1, 0x04, 0xFE, 0xFF))
        return code
    if t == 'take_item':
        if item_resolver is None: raise ValueError('Take Item needs an item')
        if not row.get('item_class_id'): raise ValueError('Choose the item to take')
        return bytes((0x84, item_resolver(row)))
    if t == 'pay_money':
        return struct.pack('<BH', 0x99, _int(row, 'amount', 1, 65535))
    if t == 'restore_life':
        # Alundra stands while the game's healing sparkles rise around him
        # (sound 31, map 379 B1), then C3. The sparkle entries are added to the
        # map's effect table by the event compiler (HEAL_EFFECTS, per map).
        from heal_tile import restore_all_bytes
        return restore_all_bytes(HEAL_EFFECTS)
    if t == 'change_player_character':
        if row.get('character') not in ('Alundra', 'Meia'): raise ValueError('Player character must be Alundra or Meia')
        return bytes((0xEB, 1 if row['character'] == 'Meia' else 0))
    if t == 'raise_max_mp':
        return bytes((0xEA, _int(row, 'amount', 1, 4)))
    if t == 'raise_max_life':
        return bytes((0xBC, _int(row, 'amount', 1, 50)))
    if t == 'stop_sound':
        return bytes((0x75, _int(row, 'sound_id', 0, 255, 'Sound')))   # StopSound 0x8004A7B4
    if t == 'play_sound_volume':
        v = _int(row, 'volume', 0, 127)
        sid = _int(row, 'sound_id', 0, 65535)
        # BD starts the sound; BF only sets the volume of a sound that is playing
        # (the game's scripts always play it with BD first, then BF).
        return struct.pack('<BH', 0xBD, sid) + struct.pack('<BHBB', 0xBF, sid, v, v)
    if t == 'back_to_title':
        # Change map to 477 (the game-over map, as dying does) with room-change type 11 (title)
        return bytes((0x53, 0xDD, 0x01, 0, 0, 0, 11, 0))
    if t == 'play_ending':
        return bytes((0xBB,))
    if t == 'play_movie':
        from play_movie import compile_command as _movie
        return _movie(row)
    raise ValueError(f'{t} has no native compiler')


def compile_condition(cond):
    """(test bytes, branch opcode that jumps when the condition FAILS)."""
    t = cond.get('type'); want = cond.get('value', True)
    if type(want) is not bool: raise ValueError('Condition value must be Yes/No')
    if t == 'self_switch':   # (checked here; the event compiler turns it into the event's own switch)
        if cond.get('letter') not in ('A', 'B', 'C', 'D'): raise ValueError('Self Switch must be A, B, C or D')
        return bytes((0x0A,)), (0x04 if want else 0x03)   # placeholder test (never built as is)
    if t == 'player_area':
        v = [_int(cond, k, 0, 127) for k in ('x1', 'x2', 'y1', 'y2', 'z1', 'z2')]
        raw = bytes([0x3B] + v)
    elif t == 'template_gone':
        raw = bytes((0x2C, _int(cond, 'template', 0, 127, 'Map template')))
    elif t == 'button':
        raw = struct.pack('<BHB', 0x2F, _int(cond, 'button', 1, 0xFFFF), _int(cond, 'mode', 0, 3))
    elif t == 'random':
        p = _int(cond, 'percent', 0, 100)
        raw = bytes((0x8C, max(0, min(255, round(256 * (100 - p) / 100)))))
    elif t == 'money':
        raw = struct.pack('<BH', 0x9A, _int(cond, 'amount', 0, 65535))
    elif t == 'yes_no':
        if cond.get('_after_prompt'):
            # The game's own question (maps 021, 134, 147, 394): the message
            # before it ends with \\999\\Y (sets map flag 83E7 when the text
            # reaches its end) and stays open (close mode 4); the Yes / No
            # appears beside it, the message closes (51) and the script waits
            # for it to be gone (39) before going on.
            # 2026-10-22: randomizer door pattern (0D text mode 0, 39, 44); the
            # 50/36/51 form above showed the box but took no button.
            raw = bytes((0x39, 0x44))
        else:
            raw = bytes((0x44,))
    elif t == 'chest_opened':
        raw = bytes((0x9F, _int(cond, 'template', 0, 127, 'Map template')))
    else:
        raise ValueError(f'{t} condition has no native compiler')
    return raw, (0x04 if want else 0x03)


def summary(row):
    t = row['type']
    if t == 'set_self_switch': return f"Self Switch {row.get('letter', 'A')} = {'ON' if row.get('value', True) else 'OFF'}"
    if t == 'set_passability':
        return f"{row['width']}×{row['height']} at {row['x']},{row['y']} → {'walkable' if row.get('walkable') else 'blocked'}"
    if t == 'copy_map_tiles':
        return f"{row['width']}×{row['height']} from {row['from_x']},{row['from_y']} to {row['to_x']},{row['to_y']}"
    if t == 'wait_animation': return f"{row['times']} time(s)"
    if t == 'jump_actor':
        who = 'Player' if row.get('target') == 0x81 else 'This character'
        if 'height' not in row: return f"{who} at {row.get('strength')} px/frame"
        return f"{who} up {row['height']} px at {row['speed']} px/frame" + (', falls back' if row.get('fall_back', True) else ', stays up')
    if t == 'set_gravity': return 'On' if row.get('on', True) else 'Off'
    if t == 'play_victory': return row.get('text') or 'Defeated the boss.'
    if t == 'show_effect': return f"Effect {row['effect']} at {'the player' if row.get('target') == 0x81 else 'this character'}"
    if t == 'camera':
        return {'player': 'Follow the player', 'this': 'Follow this character'}.get(row.get('mode'), f"Look at {row['x']},{row['y']}")
    if t == 'fade_screen': return f"{'To' if row.get('direction') == 'out' else 'From'} {row.get('colour')} over {row['frames']} frames"
    if t == 'pay_money': return f"Money − {row['amount']}"
    if t == 'raise_max_mp': return f"+{row['amount']}"
    if t == 'raise_max_life': return f"+{row['amount']}"
    if t == 'restore_life': return 'Full life and magic'
    if t == 'stop_sound': return f"Stop sound {row['sound_id']}"
    if t == 'play_sound_volume': return f"Sound {row['sound_id']} at volume {row['volume']}"
    if t == 'back_to_title': return 'Title screen'
    if t == 'play_ending': return 'Ending movie and credits'
    if t == 'play_movie':
        from play_movie import MOVIE_NAMES
        return MOVIE_NAMES.get(row.get('movie'), 'Movie')
    return ''


def condition_summary(cond):
    t = cond['type']; neg = '' if cond.get('value', True) else 'NOT '
    if t == 'self_switch': return f"Self Switch {cond.get('letter', 'A')} is {'ON' if cond.get('value', True) else 'OFF'}"
    if t == 'player_area': return f"{neg}Player in {cond['x1']}-{cond['x2']}, {cond['y1']}-{cond['y2']}"
    if t == 'template_gone': return f"{neg}Template {cond['template']} gone"
    if t == 'button':
        name = next((k for k, v in BUTTONS.items() if v == cond['button']), hex(cond['button']))
        return f"{neg}{name} {next((k for k, v in BUTTON_MODE.items() if v == cond.get('mode')), '').lower()}"
    if t == 'random': return f"{neg}{cond['percent']}% chance"
    if t == 'money': return f"{neg}Money ≥ {cond['amount']}"
    if t == 'yes_no': return f"Answer is {'Yes' if cond.get('value', True) else 'No'}"
    if t == 'chest_opened': return f"{neg}Chest (template {cond['template']}) opened"
    return t
