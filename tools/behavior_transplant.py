"""Carry an actor's map-owned behaviour scripts to another map.

A placed object/enemy/boss copied from another map ("donor") keeps the six
A-F hook bytes of its donor record. A hook with bit 0x80 names a root of the
donor map's own script banks; that code does not exist on the target map, so
the program is copied: every instruction reachable from the root (relative
branches and local calls followed, see event_editor.instructions) is taken as
one contiguous span of the donor's code and appended to the same bank of the
target map (native_script_allocation.append_native_process). Relative jumps
inside the span stay valid because the span keeps its layout; when the span
starts before the root, a leading relative jump (opcode 02) enters at the root.
Hooks without bit 0x80 select shared code and are kept unchanged.

Game flags: every set / clear / branch-on / wait-for of a persistent game flag
(operand 0001-07FF) in a copied program is moved to the same-numbered room
flag (operand | 8000h, the native temporary bank 8000-87FF, cleared on every map
load). So a placed object still works by itself (a lever that its own script
waits on, a block that remembers it moved while you are in the room) but never
sets or reads the donor's story/progress flags. Room flags already used by the
donor (8000h+) and the no-flag sentinel 0 are unchanged.

Not translated: references into the donor map's own text, actor slots,
spawn templates or tiles. The object always appears; whether such a program
behaves exactly as on its home map needs testing in game.
"""
import struct

MAX_SPAN = 16384
# Classes whose copied program spawns one map template that the event can choose
# (native_placement.spawned_class; default: the donor's own template). Generator: 2D Mud Man.
SPAWN_CHOICE_CATALOGUES = {394: "Generator"}
# Set flag, clear flag, branch if set / clear, toggle, wait until clear / set (operand is the
# u16 after the opcode); 33 / 34 test four flags (all set / all clear).
FLAG_OPCODES = (0x05, 0x06, 0x30, 0x31, 0x32, 0x35, 0x36)
FOUR_FLAG_OPCODES = (0x33, 0x34)
# Classes the compiler places only from one tested donor (projectile bundles,
# arena-free Werewolf, flame pillar, small key door, magic pot): the behaviour
# chooser keeps them on Automatic.
# Effect ops whose first operand is an entry of the map's effect table (minimum size).
EFFECT_OPCODES = {0xA2: 8, 0xA3: 9, 0x90: 2, 0x91: 2, 0x92: 3}
# Ops that change the entities a selector names (deactivate, animation, direction,
# lift, entity flags, blink): with a donor template the target map does not have,
# they would hit whatever the target has under that number.
SELECTOR_OPCODES = {0x5D: 2, 0x59: 3, 0x5A: 3, 0x5B: 4, 0x5E: 4, 0x62: 4, 0x63: 4, 0x64: 8, 0x86: 4}
# Where each op keeps an entity selector (research/us_decomp/vm_ops audits). A selector
# below 80h names a map template; one the map does not have stops the game.
SELECTOR_SPOTS = {0x07: (1,), 0x2C: (1,), 0x2E: (1,), 0x43: (1,), 0x59: (1,), 0x5A: (1,), 0x5B: (1,),
                  0x5C: (1,), 0x5D: (1,), 0x5E: (1,), 0x60: (1,), 0x61: (1,), 0x62: (1,), 0x63: (1,),
                  0x64: (1,), 0x65: (1,), 0x67: (1,), 0x86: (1,), 0x87: (1,), 0x88: (1,), 0x89: (1,),
                  0x8B: (1,), 0x8D: (1,), 0x96: (1,), 0x9F: (1,), 0xA1: (2,), 0xA3: (2,), 0xA9: (1,),
                  0xAA: (1,), 0xAC: (1,), 0xAD: (1,), 0xB2: (1, 2), 0xB4: (1,), 0xB5: (1,), 0xB6: (1,),
                  0xB7: (1,), 0xB8: (1,), 0xC4: (1,)}
# Tests (they set Result): an empty selection (8A, the entity's parent: none for placed
# objects) gives the same answer as a template that is not there.
CONDITION_SELECTS = frozenset({0x07, 0x2C, 0x43, 0x60, 0x61, 0x87, 0x8D, 0x9F, 0xA9, 0xAA, 0xAD, 0xB2, 0xB7, 0xB8})
FIXED_DONOR_CLASSES = frozenset({316, 323, 347, 350, 356, 409, 482})
# Absolute map positions in a program (native_event_knowledge): a boss placed elsewhere must act
# on the tile it stands on, not on the donor room's tiles, so these move with the boss.
# Pixel ops: X u16 at the spot, then Y u16, then height u16 (24 px per tile on X, 16 on Y).
PIXEL_XYZ_SPOT = {0x64: 2, 0x69: 1, 0x8A: 2, 0x93: 2, 0xA2: 2}
# Tile ops: (spots of tile X bytes, spots of tile Y bytes, spots of height bytes in 16 px steps).
TILE_SPOTS = {0x07: ((2, 3), (4, 5), (6, 7)), 0x3B: ((1, 2), (3, 4), (5, 6)), 0x3C: ((1, 2), (3, 4), (5, 6)),
              0x3D: ((1, 2), (3, 4), (5, 6)), 0x54: ((1,), (2,), ()), 0x55: ((1,), (2,), ()),
              0x9E: ((1,), (2,), ()), 0x85: ((1, 5), (2, 6), ())}
# A placed record keeps x / y / height in half-tiles of 12 / 8 / 8 pixels (raw[7:10]).
RECORD_PIXELS = (12, 8, 8)


def placement_shift(donor_position, target_position):
    """(dx, dy, dz pixels, dtile x, dtile y, dheight steps) from the donor boss to the placed one."""
    d = [t - s for s, t in zip(donor_position, target_position)]
    return (d[0] * RECORD_PIXELS[0], d[1] * RECORD_PIXELS[1], d[2] * RECORD_PIXELS[2],
            round(d[0] / 2), round(d[1] / 2), round(d[2] / 2))


def relocate_code(code, rows, low, shift):
    """Move the absolute positions of the copied program by `shift`; returns how many were moved.
    A value that would leave its field (0..255 tiles, 0..65535 pixels) is left as it was."""
    dx, dy, dz, tx, ty, th = shift
    moved = 0
    for offset, op, size in rows:
        at = offset - low
        spot = PIXEL_XYZ_SPOT.get(op)
        if spot is not None and size >= spot + 6:
            for k, delta in enumerate((dx, dy, dz)):
                value = struct.unpack_from("<H", code, at + spot + 2 * k)[0] + delta
                if delta and 0 <= value <= 0xFFFF:
                    struct.pack_into("<H", code, at + spot + 2 * k, value); moved += 1
        tiles = TILE_SPOTS.get(op)
        if tiles is not None:
            for group, delta in zip(tiles, (tx, ty, th)):
                for s in group:
                    if s < size and delta and 0 <= code[at + s] + delta <= 255:
                        code[at + s] += delta; moved += 1
    return moved


# A placed boss keeps its fight only: text boxes (and their waits / questions) and map
# changes, warp switches and healing of its home room's scenes are dropped from its copied programs.
BOSS_DROPPED_OPCODES = {0x0D: "Show text", 0x5C: "Show text spoken by character",
                        0xC4: "Show text with chosen speaker", 0x39: "Wait for text box to close",
                        0x44: "Ask Yes / No", 0x4C: "Text options", 0x4D: "Text advances by itself",
                        0x4F: "Text advances by itself (debug)", 0x51: "Hold text box",
                        0x52: "Use the activated warp portal", 0x53: "Change map",
                        0x9B: "Disable warps", 0x9C: "Enable warps",
                        0x96: "Heal characters", 0x97: "Add magic", 0xC3: "Restore life and magic",
                        # A placed Melzas never finishes its intro animation 01: the wait hung the room
                        # (BizHawk 2026-10-19, docs/2026-10-19-maker-boss-placement-audit.txt).
                        0x1C: "Wait for animation to play"}


def program_span(data, donor_map, bank, index, session=None, shift=None, drop=(), player_box=None):
    """(code bytes ending with FF, report) for root `bank index` of donor_map.
    `session` may be a reused read-only snapshot: appending code to other maps
    never moves or changes an existing root's code. Instructions whose opcode is
    in `drop` become no-ops of the same size."""
    from editor_session import EditSession
    from event_editor import reachable_instructions, script_roots
    if session is None:
        session = EditSession.readonly(bytes(data))
    data = session.data
    key = f"{bank} {index}"
    roots = script_roots(session, donor_map)
    if key not in roots:
        raise ValueError(f"Donor map {donor_map} has no script root {key}")
    start = roots[key][0]
    rows = reachable_instructions(session, donor_map, key)
    if not rows:
        raise ValueError(f"Donor script {key} on map {donor_map} is empty")
    low = min(offset for offset, _, _ in rows)
    high = max(offset + size for offset, _, size in rows)
    if high - low > MAX_SPAN:
        raise ValueError(f"Donor script {key} on map {donor_map} spans too much code")
    code = bytearray(data[low:high])
    moved = []
    for offset, op, size in rows:
        spots = [1] if op in FLAG_OPCODES and size >= 3 else ([1, 3, 5, 7] if op in FOUR_FLAG_OPCODES and size >= 9 else [])
        for spot in spots:
            at = offset - low + spot
            operand = struct.unpack_from("<H", code, at)[0]
            if operand and not operand & 0x8000 and operand <= 0x7FF:
                struct.pack_into("<H", code, at, operand | 0x8000); moved.append(operand)
    relocated = relocate_code(code, rows, low, shift) if shift else 0
    if player_box is not None:
        # Launcher / Four-Way Turret trigger options (2026-10-22): "always" removes every
        # player tile-box test (3B) and the jump that follows it; (x, y, r) makes each box the
        # placed object's tile +- r tiles (heights kept).
        for k, (offset, op, size) in enumerate(rows):
            if op != 0x3B or size < 5:
                continue
            at = offset - low
            if player_box == "always":
                code[at:at + size] = _skip(size)
                nxt = rows[k + 1] if k + 1 < len(rows) else None
                if nxt and nxt[1] in (0x03, 0x04) and nxt[0] == offset + size:
                    code[nxt[0] - low:nxt[0] - low + nxt[2]] = _skip(nxt[2])
            else:
                x, y, r = player_box
                code[at + 1:at + 5] = bytes((max(0, x - r), min(255, x + r), max(0, y - r), min(255, y + r)))
    dropped = []
    for offset, op, size in rows:
        if op in drop:
            code[offset - low:offset - low + size] = _skip(size); dropped.append(BOSS_DROPPED_OPCODES.get(op, hex(op)))
    rows = [r for r in rows if r[1] not in drop]
    code = bytes(code)
    entry = 3 if low < start else 0
    # References into the donor map's own lists (translated by transplant_hooks):
    # map texts (0D / 5C, index bit 7), spawn templates (2D) and effect entries.
    refs = []
    for offset, op, size in rows:
        at = offset - low + entry
        b = lambda k: code[offset - low + k]
        if op == 0x0D and size >= 3 and b(1) & 0x80:
            refs.append(("text", at + 1, b(1) & 0x7F))
        elif op == 0x5C and size >= 4 and b(2) & 0x80:
            refs.append(("text", at + 2, b(2) & 0x7F))
        if op == 0x2D and size >= 2:
            refs.append(("spawn", at, b(1), 2))
        elif op == 0x8A and size == 8:      # spawn template b1 at a position
            refs.append(("spawn", at, b(1), 8))
        elif op == 0x8B and size == 9:      # spawn template b2 at a selected entity
            refs.append(("spawn", at, b(2), 9))
        elif op in (0x85, 0x56):            # copy squares of the donor map: means nothing on another map
            refs.append(("tiles", at, op, size))
        for spot in SELECTOR_SPOTS.get(op, ()):
            if spot < size and b(spot) < 0x80:
                refs.append(("select", at, b(spot), size, spot, op))
        if op in EFFECT_OPCODES and size >= EFFECT_OPCODES[op]:
            refs.append(("effect", at, b(1), size))
        if op in (0x05, 0x06, 0x32) and size >= 3:
            refs.append(("flagset", at, b(1) | b(2) << 8))
        elif op == 0x36 and size == 3:
            refs.append(("flagwait", at, b(1) | b(2) << 8))
    if low < start:
        code = bytes([2]) + struct.pack("<h", 3 + start - low) + code
    if not code.endswith(b"\xff"):
        code += b"\xff"
    return code, {"donor_map": donor_map, "root": key, "code_bytes": len(code),
                  "span": [hex(low), hex(high)], "entry_jump": low < start,
                  "game_flags_made_room_flags": sorted({hex(v) for v in moved}), "map_refs": refs,
                  "positions_moved_with_placement": relocated,
                  **({"dropped": sorted(set(dropped))} if dropped else {})}


def transplant_hooks(data, target_map, donor_map, hooks, cache=None, start_now=False, shift=None,
                     spawns=None, spawn_target=None, player_box=None):
    """Install the donor's map-local programs on target_map.

    Returns (new data, six new hook bytes, report). `cache` (a dict kept per
    build) lets several copies of the same donor share one installed program.
    start_now (bosses): a wait for a flag that only the donor's room sets (its
    intro scene: Zazan waits for 83F2 on map 153) is passed at once, so the boss
    starts as it does in the game once its room lets it; flags its own programs
    set are still waited for.
    spawns (objects, 2026-10-22): placement shift used only for the donor spawn templates a
    copied program creates (Launcher 2D Flame, Generator 2D Mud Man): they are brought onto
    the target map at the placed object's offset instead of being removed; the program's
    absolute positions / player tile-box tests (Launcher 3B) move with the placement too
    (BizHawk 2026-10-22: unmoved boxes never fired); nothing is dropped. spawn_target: a template index on the
    target map that every spawn / template select of the copied programs uses instead
    (the Generator's "Spawns" option).
    """
    hooks = bytes(hooks)
    drop = BOSS_DROPPED_OPCODES if start_now or shift else ()
    if len(hooks) != 6:
        raise ValueError("Six A-F hook bytes required")
    cache = {} if cache is None else cache
    result = bytearray(hooks); copied = []
    own_sets = set()
    if start_now:
        if "_snapshot" not in cache:
            from editor_session import EditSession
            cache["_snapshot"] = EditSession.readonly(bytes(data))
        for i, value in enumerate(hooks):
            if value & 0x80:
                try:
                    _, info = program_span(data, donor_map, "ABCDEF"[i], value & 0x7F, cache["_snapshot"])
                except ValueError:
                    continue
                own_sets |= {r[2] for r in info.get("map_refs", []) if r[0] == "flagset"}
    for i, value in enumerate(hooks):
        if not value & 0x80:
            continue
        bank = "ABCDEF"[i]; index = value & 0x7F
        key = (target_map, donor_map, bank, index, bool(start_now), tuple(shift or ()), tuple(spawns or ()), spawn_target,
               player_box if isinstance(player_box, str) else tuple(player_box or ()))
        if key not in cache:
            from native_script_allocation import append_native_process
            if "_snapshot" not in cache:     # one decoding snapshot per build
                from editor_session import EditSession
                cache["_snapshot"] = EditSession.readonly(bytes(data))
            try:
                code, info = program_span(data, donor_map, bank, index, cache["_snapshot"], shift or spawns, drop, player_box)
            except ValueError as exc:
                # The donor points at a script its map does not have: leave
                # that hook empty instead of failing the whole object.
                cache[key] = 0; copied.append(dict(root=f"{bank} {index}", skipped=str(exc))); result[i] = 0
                continue
            refs = info.pop("map_refs", [])
            # a program that spawns or selects templates (the boss's parts, Giant Slime (Large) 2E 11..15)
            # is the fight's set-up, not an intro: kept (stress test 2026-10-21: the slime never woke up)
            if start_now and _intro_only(code, i) and not any(r[0] in ("spawn", "select") for r in refs):
                # A boss's room intro that ends by switching itself off (40 <own slot> 00) and spawns
                # nothing: left out, the boss starts with its own (native) fight. Melzas's copied
                # intro hung the game once it handed over (BizHawk 2026-10-19).
                cache[key] = 0; result[i] = 0
                copied.append(dict(root=f"{bank} {index}", skipped="room intro only (the boss fights without it)"))
                continue
            if start_now:
                code = bytearray(code); passed = []
                for r in refs:
                    if r[0] == "flagwait" and r[2] not in own_sets and code[r[1]] == 0x36:
                        code[r[1]:r[1] + 3] = _skip(3); passed.append(hex(r[2]))
                code = bytes(code)
                if passed:info["room_waits_passed"] = passed
            refs = [r for r in refs if r[0] not in ("flagset", "flagwait")]
            data, code, info["map_refs"] = translate_map_refs(data, target_map, donor_map, code, refs,
                                                               cache["_snapshot"].data, cache, shift or spawns,
                                                               boss_templates=bool(shift) or spawns is not None,
                                                               as_boss=bool(shift), spawn_target=spawn_target)
            data, allocation = append_native_process(data, target_map, bank, code)
            cache[key] = allocation["hook_value"]
            copied.append(dict(info, bank=bank, hook_value=allocation["hook_value"]))
        result[i] = cache[key]
    return data, bytes(result), {"donor_map": donor_map, "donor_hooks": hooks.hex(),
                                 "installed_hooks": bytes(result).hex(), "copied_programs": copied,
                                 "map_references_translated": True, "gameplay_verified": False}


def _intro_only(code, slot):
    """Does a copied program run straight through and end by switching its own slot off?"""
    tail = bytes(code).rstrip(bytes((0xFF,)))
    if not tail.endswith(bytes((0x40, slot, 0x00))):
        return False
    at = 0
    while at + 2 < len(tail):
        if tail[at] == 0x02 and struct.unpack_from("<h", tail, at + 1)[0] <= 0:
            return False          # a loop: a program that keeps running, not an intro
        at += 1
    return True


def local_text(data, map_id, index):
    """Raw bytes of map-local text `index` (no terminator), or None."""
    from map_block_repack import pointers, sections
    table = pointers(data)
    block = data[table[map_id]:table[map_id + 1]]
    start = sections(block)[6]
    if start + 256 > len(block):
        return None
    value = struct.unpack_from("<h", block, start + 2 * index)[0]
    if value < 256 or start + value >= len(block):
        return None
    end = block.find(0, start + value)
    return bytes(block[start + value:end if end >= 0 else len(block)])


def _skip(size):
    """An instruction of `size` bytes that does nothing: a jump over itself
    (02 size), or a one-frame wait (37 00) for two bytes."""
    if size == 1:
        return bytes((0x01,))
    if size == 2:
        return bytes((0x37, 0x00))
    return bytes((0x02,)) + struct.pack("<h", size) + bytes(size - 3)


def _catalogue(raw):
    return raw[6] + (256 if raw[5] & 128 else 0)


def _template_class_available(data, target_map, raw):
    """Is the sprite of a donor template present on the target map (local slot imported / global bank)?"""
    from native_class_placement import global_sprite_available
    if not raw[5] & 128:
        return bool(global_sprite_available(data, raw[6]))
    from local_sprite_import import layout
    b, h, s, e, sh = layout(data, target_map)
    return struct.unpack_from("<i", data, s + sh[3] + 4 * raw[6])[0] not in (0, -1)


def copy_template(data, target_map, donor_map, donor, index, cache, shift=None, as_boss=True):
    """Bring the donor map's spawn template `index` onto the target map (a boss's attacks and
    parts are spawned from such templates). Returns (data, new template number or None).

    The record keeps its class and stays dormant as in the donor; its position moves with the
    placed boss (half-tile deltas of `shift`) and its activation box becomes the whole target
    map. Its own map-local programs are copied with the same shift. None when the class's
    sprite is not on the target map or the template list is full (the caller skips the spawn).
    """
    from native_class_placement import record_cluster, append_record_cluster
    from map_block_repack import pointers, sections
    freezable = bool(cache.get("_freezable_flames")) and _catalogue(donor["entities"][index]) == 319 if index < len(donor["entities"]) else False
    key = ("template", target_map, donor_map, index, tuple(shift or ()), as_boss, freezable)
    if key in cache:
        return data, cache[key]
    entities = donor["entities"]
    cache[key] = None
    if index >= len(entities):
        return data, None
    raw = bytearray(entities[index])
    target = record_cluster(data, target_map)["entities"]
    if len(target) >= 0x7F:
        return data, None
    if not _template_class_available(data, target_map, raw):
        if not raw[5] & 128:
            return data, None
        # A boss's spawned piece of a class its home map also places (so not among the
        # boss's companion sprites): bring its art into the same slot. Every slot that
        # already holds a sprite on the target is kept, so nothing in use is reused.
        from local_sprite_import import import_local_sprite, layout
        b, h, s, e, sh = layout(data, target_map)
        present = {i for i in range((sh[4] - sh[3]) // 4)
                   if struct.unpack_from("<i", data, s + sh[3] + 4 * i)[0] not in (0, -1)}
        try:
            data, _ = import_local_sprite(data, target_map, donor_map, raw[6], keep=present)
        except ValueError as exc:
            cache["_template_skip"] = f"its sprite could not be brought onto map {target_map} ({exc})"
            return data, None
        target = record_cluster(data, target_map)["entities"]
    pp = pointers(data)
    h = sections(data[pp[target_map]:pp[target_map + 1]])
    width, tall = data[pp[target_map] + h[1]:pp[target_map] + h[1] + 2]
    if shift:
        for k, step in enumerate((shift[0] // RECORD_PIXELS[0], shift[1] // RECORD_PIXELS[1], shift[2] // RECORD_PIXELS[2])):
            limit = (width * 2, tall * 2, 255)[k]
            raw[7 + k] = min(max(raw[7 + k] + step, 0), limit - 1 if k < 2 else limit)
    raw[:4] = bytes((0, 0, width - 1, tall - 1))
    raw[16:18] = bytes(2)
    # The event compiler places its actors at fixed indices after the map's own records and
    # writes these templates after them (cache[("template_base", map)] is where they start),
    # so the actors keep the indices their watchers name; used alone, it is appended at once.
    base = cache.get(("template_base", target_map))
    deferred = cache.setdefault(("templates", target_map), []) if base is not None else None
    new = base + len(deferred) if base is not None else len(target)
    if new >= 0x80:
        cache["_template_skip"] = "the map's first 128 characters are all used"
        return data, None
    cache[key] = new      # before its programs are copied: a program that spawns it again finds it
    cache.setdefault(("appended", target_map), set()).add(new)
    if deferred is not None:
        deferred.append(bytes(raw))
    else:
        data, _ = append_record_cluster(data, target_map, entities=target + [bytes(raw)])
    if any(v & 0x80 for v in raw[10:16]):
        data, hooks, _ = transplant_hooks(data, target_map, donor_map, bytes(raw[10:16]), cache,
                                          **({"shift": shift} if as_boss else {"spawns": shift or (0,) * 6}))
        if deferred is not None:
            row = bytearray(deferred[new - base]); row[10:16] = hooks; deferred[new - base] = bytes(row)
        else:
            rows = record_cluster(data, target_map)["entities"]
            row = bytearray(rows[new]); row[10:16] = hooks; rows[new] = bytes(row)
            data, _ = append_record_cluster(data, target_map, entities=rows)
    if freezable:
        # Launcher option "Fireballs freezable (Ice Wand)": native_freezable_flame
        from native_freezable_flame import make_freezable
        rows = deferred if deferred is not None else record_cluster(data, target_map)["entities"]
        at = new - base if deferred is not None else new
        row = bytearray(rows[at]); data = make_freezable(data, target_map, row, new); rows[at] = bytes(row)
        if deferred is None:
            data, _ = append_record_cluster(data, target_map, entities=rows)
    return data, new


def translate_map_refs(data, target_map, donor_map, code, refs, donor_data, cache, shift=None, boss_templates=False,
                       as_boss=True, spawn_target=None):
    """Point a copied program's references to the donor map's own lists at the
    target map: its texts are copied into the target's text table, its effect
    entries into the target's effect table (global effects), and a spawn of a
    donor template the target does not have (2D, 8A, 8B: the game halts on a
    missing template: "Illigal InitData Number") is skipped."""
    from native_class_placement import record_cluster
    if target_map == donor_map:
        return data, code, []
    code = bytearray(code)
    done = []
    donor = record_cluster(donor_data, donor_map)
    for ref in refs:
        kind, at = ref[0], ref[1]
        if kind == "text":
            key = ("text", target_map, donor_map, ref[2])
            if key not in cache:
                raw = local_text(donor_data, donor_map, ref[2])
                if raw is None:
                    cache[key] = None
                else:
                    from native_text_allocation import append_local_text
                    data, report = append_local_text(data, target_map, raw.decode("latin-1"))
                    cache[key] = report["dialogue_reference"]
            if cache[key] is not None:
                code[at] = cache[key]
                done.append(dict(text=ref[2], to=cache[key] & 0x7F))
        elif kind == "tiles":
            code[at:at + ref[3]] = _skip(ref[3])
            done.append(dict(tiles=hex(ref[2]), removed=True))
        elif kind in ("spawn", "select"):
            template = ref[2]
            if spawn_target is not None and (code[at] == ref[5] if kind == "select" else code[at] in (0x2D, 0x8A, 0x8B)):
                code[at + (ref[4] if kind == "select" else (2 if ref[3] == 9 else 1))] = spawn_target
                done.append(dict(template=template, chosen=spawn_target))
                continue
            target = record_cluster(data, target_map)["entities"]
            # A record this transplant appended is not the target's own template of that number.
            if not (template < len(donor["entities"]) and template < len(target)
                    and template not in cache.get(("appended", target_map), ())
                    and _catalogue(donor["entities"][template]) == _catalogue(target[template])):
                # A boss's attacks and parts are spawned from donor templates: bring the template.
                if boss_templates and (code[at] == ref[5] if kind == "select" else code[at] in (0x2D, 0x8A, 0x8B)):
                    data, mapped = copy_template(data, target_map, donor_map, donor, template, cache, shift, as_boss)
                    if mapped is not None:
                        code[at + (ref[4] if kind == "select" else (2 if ref[3] == 9 else 1))] = mapped
                        done.append(dict(template=template, copied_to=mapped))
                        continue
                    why = cache.pop("_template_skip", None)
                    if why:
                        done.append(dict(template=template, not_copied=why))
                # A selector naming a template the map does not have is fatal in the
                # game ("Illegal InitData Number"): tests and speaker messages get a
                # harmless selector, anything else is skipped.
                if kind == "select" and code[at] == ref[5] and ref[5] in CONDITION_SELECTS:
                    code[at + ref[4]] = 0x8A; done.append(dict(select=template, replaced='8A'))
                elif kind == "select" and code[at] == ref[5] and ref[5] in (0x5C, 0xC4):
                    code[at + ref[4]] = 0x80; done.append(dict(select=template, replaced='80'))
                elif code[at] != 0x02 or kind == "spawn":
                    code[at:at + ref[3]] = _skip(ref[3])
                    done.append({kind: template, "removed": True})
        elif kind == "effect" and code[at] != 0x02:     # (not when the instruction was skipped above)
            index, size = ref[2], ref[3]
            rows = [donor["effects"][i:i + 12] for i in range(0, max(0, len(donor["effects"]) - 4), 12)]
            entry = rows[index] if index < len(rows) else None
            if entry is not None and not entry[4] & 0x80:
                from heal_tile import ensure_effects
                data, found = ensure_effects(data, target_map, [(entry[5], entry[9])])
                code[at + 1] = found[(entry[5], entry[9])]
                done.append(dict(effect=index, to=code[at + 1]))
            else:
                # the donor map's own effect sprite: skip the instruction
                code[at:at + size] = _skip(size)
                done.append(dict(effect=index, removed=True))
    return data, bytes(code), done


def synthetic_record(data, map_id, catalogue, x, y, height, direction=0):
    """A fresh 20-byte actor record for a class no map places (no donor).

    Global classes (0-255) use the shared sprite bank; local classes (256-511)
    need their sprite imported onto map_id first. No hooks, no contents."""
    from map_block_repack import pointers, sections
    pp = pointers(data)
    h = sections(data[pp[map_id]:pp[map_id + 1]])
    width, tall = data[pp[map_id] + h[1]:pp[map_id] + h[1] + 2]
    if not 0 <= x < width or not 0 <= y < tall:
        raise ValueError("Placement outside target tile grid")
    row = bytearray(20)
    row[:4] = bytes((0, 0, width - 1, tall - 1))
    row[4] = 1
    row[5] = 0x40 | (0x80 if catalogue >= 256 else 0) | (direction & 3)
    row[6] = catalogue & 0xFF
    row[7:10] = bytes((x * 2, y * 2, height * 2))
    return bytes(row)


def local_sprite_home(data, sprite_id):
    """First original map whose local sprite table holds this sprite's art."""
    from local_sprite_import import sprite_assets
    for m in range(483):
        try:
            sprite_assets(data, m, sprite_id)
            return m
        except Exception:
            continue
    return None


def program_shape(session, donor_map, bank, index):
    """What a map script does, ignoring its numbers: the sequence of opcodes.
    Two switches that each set their own flag have the same shape."""
    import hashlib
    from event_editor import reachable_instructions
    try:
        rows = reachable_instructions(session, donor_map, f"{bank} {index}")
    except Exception:
        return f"unreadable {donor_map} {bank}{index}", b""
    ops = bytes(op for _, op, _ in rows)
    return hashlib.sha1(ops).hexdigest()[:12], ops


def behaviour_variants(data, catalogue, cache=None):
    """Distinct behaviours of a class across the original maps.

    Every placed instance is grouped by what its six hooks actually run: shared
    hook values as they are, map-local hooks by the bytes of the program they
    call. Instances that run the same scripts form one variant, so only real
    differences are offered. Each variant names one donor (map, entity index)
    that the compiler copies, with its scripts, when the variant is chosen.
    """
    import hashlib
    from native_class_placement import record_cluster
    key = (len(data), hashlib.sha1(bytes(data[:0x800])).hexdigest(), catalogue)
    if cache is not None and key in cache:
        return cache[key]
    from editor_session import EditSession
    session = EditSession.readonly(bytes(data))
    groups = {}
    programs = {}
    for m in range(483):
        try:
            entities = record_cluster(data, m)["entities"]
        except Exception:
            continue
        for index, raw in enumerate(entities):
            if raw[6] + (256 if raw[5] & 128 else 0) != catalogue:
                continue
            signature = []
            for i, value in enumerate(raw[10:16]):
                if not value:
                    continue
                if value & 0x80:
                    pkey = (m, "ABCDEF"[i], value & 0x7F)
                    if pkey not in programs:
                        programs[pkey] = program_shape(session, *pkey)
                    signature.append(("ABCDEF"[i], "map", programs[pkey][0]))
                else:
                    signature.append(("ABCDEF"[i], "shared", value))
            group = groups.setdefault(tuple(signature), {"donor_map": m, "entity_index": index,
                                                         "maps": [], "instances": 0,
                                                         "banks": "".join(s[0] for s in signature)})
            if not group["instances"]:
                group["steps"] = {s[0]: len(programs[(m, s[0], raw[10 + "ABCDEF".index(s[0])] & 0x7F)][1])
                                  for s in signature if s[1] == "map"}
                group["does"] = describe(b"".join(programs[(m, s[0], raw[10 + "ABCDEF".index(s[0])] & 0x7F)][1]
                                                  for s in signature if s[1] == "map"))
            group["instances"] += 1
            if m not in group["maps"]:
                group["maps"].append(m)
    result = sorted(groups.values(), key=lambda g: (-g["instances"], g["donor_map"]))
    if cache is not None:
        cache[key] = result
    return result


def describe(ops):
    """A few plain words for what a script does (known opcodes only)."""
    from event_editor import EDITABLE
    words = []
    for op in ops:
        name = EDITABLE.get(op, (None,))[0]
        if name and name not in words and op not in (2, 3, 4, 0x30, 0x31, 0x74, 0x78):
            words.append(name)
    return words[:4]


# What some classes' copies do in the game, shown first in the Behaviour list.
BEHAVIOUR_NAMES = {(159, 13): 'Stand-on bubble (rises with Alundra on it, then pops)',
                   (160, 1): 'Stand-on bubble (rises with Alundra on it, then pops)',
                   (159, 2): 'Rising bubble, not stand-on (pops at height 6)',
                   (159, 17): 'Rising bubble, not stand-on (pops at height 20)',
                   (159, 18): 'Rising bubble, not stand-on (gone after 2 seconds)'}


def variant_label(number, variant):
    from map_names import map_label
    m = variant["donor_map"]
    where = map_label(m).rsplit(" (Map ", 1)[0]
    if variant["banks"]:
        steps = variant.get("steps", {})
        scripts = ", ".join(f"{bank} {steps[bank]} steps" if bank in steps else f"{bank} shared"
                            for bank in variant["banks"])
    else:
        scripts = "no map script (class AI only)"
    does = "; ".join(variant.get("does") or [])
    used = f"used {variant['instances']}× on {len(variant['maps'])} map{'s' if len(variant['maps']) != 1 else ''}"
    named = BEHAVIOUR_NAMES.get((m, variant.get("entity_index")))
    if named:
        return f"Behaviour {number}: {named} · as on map {m} {where}"
    return f"Behaviour {number}: as on map {m} {where} · {scripts}{' · ' + does if does else ''} · {used}"
