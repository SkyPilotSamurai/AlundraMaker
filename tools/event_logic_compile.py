"""Compile bounded authoring logic to vanilla Alundra event bytecode.

No script allocation or runtime claims are made here. Switch IDs must be bound
explicitly to native operands, not assumed to be free flags. Wait counts are
native scheduler steps, whose relation to display frames is not established.
See docs/2026-10-05-event-logic-compiler.txt for build-specific evidence.
"""
import struct


def _uint(value, label, maximum=65535, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer {minimum}..{maximum}")
    return value


def compile_spawn_template(template_index, x, y, z):
    """Spawn an existing verified map-local InitData, using WORLD pixels.

    Caller must establish template presence/asset validity and convert tile
    coordinates to pixels. This function never treats an item/sprite ID as an
    InitData index. Z follows native 16.16 fixed-point encoding, not warp units.
    """
    return struct.pack('<BB3H', 0x8A,
                       _uint(template_index, 'Map-local InitData index', 255),
                       _uint(x, 'World X'), _uint(y, 'World Y'), _uint(z, 'World Z'))


def compile_spawn_at_player(template_index):
    """Spawn verified InitData at player's exact XYZ (native selector81)."""
    return bytes((0x8B, 0x81, _uint(template_index, 'Map-local InitData index', 127))) + bytes(6)


def compile_give_pickup(template_index):
    """Alias named for the UI's Give Item (pickup) native leaf operation."""
    return compile_spawn_at_player(template_index)


def compile_wait_template_absent(template_index):
    """Yield/poll until no entity refers to InitData; NOT proof of collection.

    Native search observes record references while the event owner is alive.
    Destruction cleanup/ref removal must occur for this to finish. Cancellation,
    collection failure, effects and caps are not equivalent to successful grant.
    Use only with a verified template lifetime, never label 'wait obtained'.
    """
    index = _uint(template_index, 'Map-local InitData index', 127)
    # 00 yields and advances;2C checks absence;04 loops when result isfalse.
    return bytes((0, 0x2C, index, 4, 0xFD, 0xFF))


def compile_speaker_dialogue(selector, text_ref, mode=0):
    """Native5C resolves an existing actor's name/portrait then opens text.

    Low selectors reference InitData0..127;80self/81player are special. Caller
    proves actor is present and text_ref points to its freshly allocated/native
    text entry. A missing match does not invent a portrait. Only mode0currently
    emitted, since other textbox modes lack a validated UI contract.
    """
    _uint(selector, 'Native speaker selector', 0x81)
    _uint(text_ref, 'Native dialogue byte reference', 255)
    # mode 0: the box stops the world (mode flag 8); mode 1: scripts keep running
    # (flag 0x10), used by every stock question so its script can close the box.
    if type(mode) is not int or mode not in (0, 1):
        raise ValueError('Dialogue mode must be 0 or 1')
    return bytes((0x5C, selector, text_ref, mode))


def find_item_template(data, item_index):
    """Find a hook/flag-free GLOBAL item record; return donor metadata or None.

    An exact donor avoids assigning another map's local scripts or flag state.
    Returned raw bytes are unchanged; caller disables auto-spawn on its COPY.
    Compatibility parsing is delegated to existing validated map inspection.
    """
    from map_inspector import inspect_map
    index = _uint(item_index, 'Native inventory item index', 89, 1)
    for map_id in range(483):
        for row in inspect_map(data, map_id)['entities']:
            offset = int(row['offset'], 16)
            raw = bytes(data[offset:offset + 20])
            if (raw[6] == index + 0x1E and not raw[5] & 0x80
                    and raw[4] == 1 and raw[10:] == bytes(10)):
                return {'map_id': map_id, 'entity_index': row['index'],
                        'offset': offset, 'raw': raw}
    return None


def item_pickup_template(item_index):
    """Build disabled-at-load global item InitData for a PICKUP, not grant.

    Mirrors observed stock hook-free ground herb templates. Item0 means none;
    inventory1..89 maps to global sprite index+1E. Caller must verify each target
    build's global sprite table and stock item pickup behavior, allocate a new
    map-local template index, and enforce repeat/collection conditions. This
    yields ordinary stock collection behavior, including caps; never promise
    an immediate inventory change or custom obtained text.
    """
    index = _uint(item_index, 'Native inventory item index', 89, 1)
    row = bytearray(20)
    row[:4] = bytes((0, 0, 51, 59))
    row[4] = 1  # native enabled record
    row[5] = 0  # global sprite; deliberately lacks initial-load spawn bit40
    row[6] = index + 0x1E
    return bytes(row)


def verified_item_pickup_template(data, item_index):
    """Return synthetic global pickup template only for stock-like item AI.

    Dedicated global bank uses DATAS file words0/4, NOT map0. Require positive
    target, bounded native animation/frame pointers and the same builtin A/CT
    callbacks as Herb (FF/FF), with no D/E/F hooks. This establishes structural
    eligibility; the caller still owns executable compatibility/gameplay tests.
    Unsupported/missing assets return None; malformed containers raise.
    """
    _uint(item_index, 'Native inventory item index', 89, 1)
    if len(data) < 8:
        raise ValueError('Missing global DATAS bank')
    start, stop = struct.unpack_from('<2I', data)
    if not 0x800 <= start < start + 48 <= stop <= len(data):
        raise ValueError('Unsupported global sprite bank bounds')
    h = struct.unpack_from('<12I', data, start)
    table, end_table = h[3:5]
    if not 48 <= table <= end_table <= stop - start or (end_table - table) % 4:
        raise ValueError('Invalid global sprite table bounds')

    def header(index):
        if index >= (end_table - table) // 4:
            return None
        pointer = struct.unpack_from('<i', data, start + table + 4 * index)[0]
        if pointer <= 0:
            return None
        if not 48 <= pointer <= stop - start - 32:
            raise ValueError('Global sprite header outside bank')
        row = bytes(data[start + pointer:start + pointer + 32])
        sets, animations, collision, frames = struct.unpack_from('<4I', row)
        if not pointer + 32 <= sets < animations <= collision <= frames < stop - start:
            return None
        return row

    herb = header(0x24 + 0x1E)
    target = header(item_index + 0x1E)
    expected_callbacks = bytes((255, 255, 0, 0, 0))
    if herb is None or target is None or herb[19:24] != expected_callbacks or target[19:24] != expected_callbacks:
        return None
    # MoreFlags/CanPickup shared by observed stock ground items. Portrait/shadow
    # bits and dimensions legitimately differ between items, so retain asset's.
    if target[16:18] != herb[16:18]:
        return None
    return item_pickup_template(item_index)


def verified_chest_template(data, item_index):
    """Build an ephemeral stock global1E chest containing a verified pickup.

    Collectionflag0 is intentionally no persistence. Caller owns map placement
    and must present room-reload repeat behavior. Chest-looking catalogue227
    has no stock chest callbacks and is NOT accepted as an equivalent class.
    """
    from native_class_placement import global_sprite_available
    if verified_item_pickup_template(data, item_index) is None:
        return None
    if not global_sprite_available(data, 0x1E):
        return None
    start = struct.unpack_from('<I', data)[0]
    table = struct.unpack_from('<I', data, start + 12)[0]
    pointer = struct.unpack_from('<i', data, start + table + 4 * 0x1E)[0]
    header = bytes(data[start + pointer:start + pointer + 32])
    if header[19:24] != bytes((255, 0, 0, 0, 255)):
        return None
    row = bytearray(20)
    row[:4] = bytes((0, 0, 51, 59))
    row[4:7] = bytes((1, 0x40, 0x1E))
    struct.pack_into('<H', row, 18, item_index)
    return bytes(row)


class _Assembler:
    def __init__(self):
        self.data = bytearray()
        self.labels = {}
        self.fixups = []
        self.counter = 0

    def name(self):
        self.counter += 1
        return self.counter

    def label(self, name):
        self.labels[name] = len(self.data)

    def branch(self, opcode, target, operand=None):
        start = len(self.data)
        self.data.append(opcode)
        if operand is not None:
            self.data.extend(struct.pack('<H', operand))
        self.fixups.append((len(self.data), start, target))
        self.data.extend(b'\0\0')

    def finish(self):
        for offset, start, label in self.fixups:
            delta = self.labels[label] - start
            if not -32768 <= delta <= 32767 or delta == 0:
                raise ValueError('Native branch exceeds signed 16-bit displacement or yields at zero')
            struct.pack_into('<h', self.data, offset, delta)
        return bytes(self.data)


from native_event_authoring import COMMANDS as _NATIVE_COMMANDS, CONDITIONS as _NATIVE_CONDITIONS


def compile_logic(commands, leaf_emitter=None, *, item_resolver=None,
                  switch_resolver=None, conditions=(), continuation_proven=False,
                  project_condition_emitter=None, _locked=False):
    """Return bytes without FF terminator; caller owns text, actors and storage.

    leaf_emitter(command) supplies bytes for other independently verified native
    commands or raises ValueError. Resolvers accept the complete command or
    condition and must return a verified native operand/index. No input mutation.
    """
    asm = _Assembler()

    def flag(row):
        value = row.get('native_flag_operand')
        if value is None and switch_resolver is not None:
            value = switch_resolver(row)
        value = _uint(value, 'Explicit native flag operand')
        if value & 0x7FFF > 0x07FF:
            raise ValueError('Native flag operand is outside the initialized 2048-bit bank')
        return value

    def item(row):
        value = row.get('native_item_id')
        if value is None and item_resolver is not None:
            value = item_resolver(row)
        return _uint(value, 'Native inventory item index', 89)

    def test(condition, false_label):
        if not isinstance(condition, dict):
            raise ValueError('Conditional branch needs a condition')
        kind = condition.get('type')
        operator = condition.get('operator', '==')
        if condition.get('switch_scope') == 'project' or condition.get('variable_scope') == 'project':
            if project_condition_emitter is None:
                raise ValueError('Project condition requires an installed private-state runtime backend')
            raw = project_condition_emitter(condition)
            if not isinstance(raw, bytes) or not raw:
                raise ValueError('Project condition compiler did not return bytecode')
            asm.data.extend(raw)
            asm.branch(4, false_label)
            return
        if kind == 'switch':
            value = condition.get('value')
            if type(value) is not bool or operator not in ('==', '!='):
                raise ValueError('Switch condition needs ON/OFF and == or !=')
            expected = value if operator == '==' else not value
            # 30 branches when SET, 31 when CLEAR: jump on failed condition.
            asm.branch(0x31 if expected else 0x30, false_label, flag(condition))
        elif kind == 'item':
            quantity = _uint(condition.get('quantity', 1), 'Inventory threshold', 255, 1)
            index = item(condition)
            if operator not in ('>=', '<', '==', '!='):
                raise ValueError('Unsupported native inventory comparison')
            def threshold(n):
                asm.data.extend(bytes((0x83, index, n)))
            if operator in ('>=', '<'):
                threshold(quantity)
                asm.branch(4 if operator == '>=' else 3, false_label)
            else:
                if quantity == 255:
                    raise ValueError('Exact inventory comparison at 255 needs an unrepresentable threshold 256')
                threshold(quantity)
                if operator == '==':
                    asm.branch(4, false_label)
                    threshold(quantity + 1)
                    asm.branch(3, false_label)
                else:
                    success = asm.name()
                    asm.branch(4, success)
                    threshold(quantity + 1)
                    asm.branch(4, false_label)
                    asm.label(success)
        elif kind in _NATIVE_CONDITIONS:
            from native_event_authoring import compile_condition
            raw, fail = compile_condition(condition)
            if operator == '!=': fail ^= 0x07   # 03 <-> 04
            asm.data.extend(raw)
            asm.branch(fail, false_label)
        else:
            raise ValueError(f'{kind} condition has no verified native compiler')

    # The player is held still (10 59 81 00 ... 11) while a Yes / No question is
    # answered and while a Repeat that takes time runs (a Player Touch event
    # stops when he walks off its tile), unless the event already locked him.
    hold = {'locked': _locked}
    LOCK, UNLOCK = bytes((0x10, 0x59, 0x81, 0x00)), bytes((0x11,))
    INSTANT = {'change_money', 'set_switch', 'set_variable', 'pay_money', 'take_item', 'raise_max_life', 'raise_max_mp', 'change_player_character',
               'set_passability', 'copy_map_tiles', 'play_sound', 'native_play_sound', 'stop_sound', 'change_music', 'play_sound_volume',
               'face_actor', 'change_animation', 'set_gravity', 'lock_movement', 'unlock_movement'}

    def walk_all(rows):
        for r in rows or []:
            if isinstance(r, dict):
                yield r
                yield from walk_all(r.get('then')); yield from walk_all(r.get('else')); yield from walk_all(r.get('commands'))

    def emit(rows, depth=0):
        if not isinstance(rows, list) or len(rows) > 512 or depth > 16:
            raise ValueError('Command list/nesting exceeds authoring limits')
        prelocked = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError('Command must be an object')
            kind = row.get('type')
            # A question message: hold the player before it opens, not between
            # the message and its Yes / No.
            nxt = rows[index + 1] if index + 1 < len(rows) else None
            if (kind == 'show_dialogue' and not hold['locked'] and isinstance(nxt, dict) and nxt.get('type') == 'if'
                    and isinstance(nxt.get('condition'), dict) and nxt['condition'].get('type') == 'yes_no'
                    and nxt['condition'].get('switch_scope') != 'project'):
                asm.data.extend(LOCK); hold['locked'] = True; prelocked.add(id(nxt))
            if kind == 'lock_movement':hold['locked'] = True
            elif kind == 'unlock_movement':hold['locked'] = False
            if row.get('switch_scope') == 'project' or row.get('variable_scope') == 'project':
                if leaf_emitter is None:
                    raise ValueError('Project state command requires an installed private-state runtime backend')
                raw = leaf_emitter(row)
                if not isinstance(raw, bytes) or not raw:
                    raise ValueError('Project state compiler did not return bytecode')
                asm.data.extend(raw)
            elif kind == 'set_switch':
                if type(row.get('value')) is not bool:
                    raise ValueError('Switch value must be ON/OFF')
                asm.data.extend(struct.pack('<BH', 5 if row['value'] else 6, flag(row)))
            elif kind == 'change_music':
                from music_database import encode_music
                asm.data.extend(encode_music(row.get('music_id')))
            elif kind == 'play_sound':
                from sound_database import encode_sound
                asm.data.extend(encode_sound(row.get('sound_id')))
            elif kind == 'stop_sound':
                from sound_database import encode_stop_sound
                asm.data.extend(encode_stop_sound(row.get('sound_id')))
            elif kind == 'native_play_sound':
                # BD lo hi: the game's PlaySound 0x8004A128 (handler 0x8004278C). Export-internal
                # (Step On Switch (Floor) press click); opcode 75 is StopSound 0x8004A7B4.
                asm.data.extend(struct.pack('<BH', 0xBD, _uint(row.get('sound_id'), 'Sound', 65535, 0)))
            elif kind == 'wait':
                asm.data.extend(bytes((0x37, _uint(row.get('frames'), 'Native wait count', 255, 1))))
            elif kind == 'change_player_character':   # EB nn (native_player_swap)
                from native_event_authoring import compile_command
                asm.data.extend(compile_command(row))
            elif kind in _NATIVE_COMMANDS:
                from native_event_authoring import compile_command
                asm.data.extend(compile_command(row, item_resolver=item))
            elif kind == 'change_money':
                asm.data.extend(struct.pack('<BH', 0x98, _uint(row.get('amount'), 'Money to add')))
            elif kind == 'repeat':
                body = row.get('commands')
                if not isinstance(body, list) or len(body) > 512 or any(not isinstance(command, dict) or command.get('type') in ('if', 'repeat') for command in body):
                    raise ValueError('Repeat actions need a linear command list without nested Repeat or If')
                from native_event_variables import compile_counted_repeat
                raw = compile_logic(body, leaf_emitter, item_resolver=item_resolver,
                    switch_resolver=switch_resolver, continuation_proven=continuation_proven,
                    project_condition_emitter=project_condition_emitter, _locked=True)
                held = not hold['locked'] and any(r.get('type') not in INSTANT for r in body)
                if held:asm.data.extend(LOCK)
                asm.data.extend(compile_counted_repeat(raw, row.get('count'),
                    continuation_proven=continuation_proven))
                if held and not any(r.get('type') == 'lock_movement' for r in body):asm.data.extend(UNLOCK)
            elif kind == 'if':
                alternative, end = asm.name(), asm.name()
                condition = row.get('condition')
                held = (isinstance(condition, dict) and condition.get('type') == 'yes_no'
                        and condition.get('switch_scope') != 'project' and not hold['locked'])
                if id(row) in prelocked:held = True
                elif held:
                    asm.data.extend(LOCK); hold['locked'] = True
                before = hold['locked']
                test(condition, alternative)
                emit(row.get('then', []), depth + 1)
                if row.get('else'):
                    asm.branch(2, end)
                asm.label(alternative)
                hold['locked'] = before
                emit(row.get('else', []), depth + 1)
                asm.label(end)
                if held:
                    branches = list(walk_all(row.get('then'))) + list(walk_all(row.get('else')))
                    if not any(r.get('type') == 'lock_movement' for r in branches):
                        asm.data.extend(UNLOCK); hold['locked'] = False
            elif leaf_emitter is not None:
                raw = leaf_emitter(row)
                if not isinstance(raw, bytes) or not raw:
                    raise ValueError('Native leaf emitter must return nonempty bytes')
                asm.data.extend(raw)
            else:
                raise ValueError(f'{kind} has no verified native compiler')
    if not isinstance(conditions, (list, tuple)) or len(conditions) > 32:
        raise ValueError('Page conditions must contain at most 32 conditions')
    skip = asm.name()
    for condition in conditions:
        test(condition, skip)
    emit(commands)
    asm.label(skip)
    return asm.finish()


def compile_page_dispatch(pages, leaf_emitter=None, *, item_resolver=None,
                          switch_resolver=None, continuation_proven=False,
                          project_condition_emitter=None):
    """Highest matching page executes once; AND conditions; no match does none.

    Pages ordered lowest->highest. Native actor appearance/trigger selection is
    the caller's responsibility. Each body/text leaf is compiled only once;
    this dispatch has no implicit page repetition or actor visibility behavior.
    Returned bytes excludeFF. Caller forbids unsupported terminal/mapping ops.
    """
    if not isinstance(pages, list) or not 1 <= len(pages) <= 32:
        raise ValueError('Page dispatcher needs 1..32 pages')
    output = bytearray()
    exits = []

    def leaf(row):
        if row.get('type') == '_page_dispatch_end':
            return b'\x02\0\0'
        if leaf_emitter is None:
            raise ValueError(f"{row.get('type')} has no verified native compiler")
        return leaf_emitter(row)

    for page in reversed(pages):
        if not isinstance(page, dict) or not isinstance(page.get('commands', []), list):
            raise ValueError('Page needs a command list')
        chunk = compile_logic(page.get('commands', []) + [{'type': '_page_dispatch_end'}], leaf,
                              item_resolver=item_resolver, switch_resolver=switch_resolver,
                              conditions=page.get('conditions', []), continuation_proven=continuation_proven,
                              project_condition_emitter=project_condition_emitter)
        output.extend(chunk)
        exits.append(len(output) - 3)
    for start in exits:
        delta = len(output) - start
        if not 1 <= delta <= 32767:
            raise ValueError('Page exit exceeds signed16 branch range')
        struct.pack_into('<h', output, start + 1, delta)
    return bytes(output)
