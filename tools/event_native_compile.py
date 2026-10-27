"""Bounded authored replacement of one existing native event process.

No new entities, map regions, scripts or inventory hooks are allocated. Native
flag writes and map changes use the same encodings as event_editor. The caller
must explicitly bind a project page to an existing F/interact or D/touch root.
"""
import hashlib
import struct
from event_editor import instructions, script_roots


def native_binding(session, map_id, script_key):
    """Capture a preimage for an explicitly selected existing native process."""
    rows = instructions(session, map_id, script_key)
    if not rows or rows[-1][1] != 255:
        raise ValueError("Existing process must decode completely through End process")
    start = rows[0][0]
    stop = rows[-1][0] + rows[-1][2]
    return {"map_id": map_id, "script_key": script_key, "process_sha256": hashlib.sha256(session.data[start:stop]).hexdigest()}


def compile_bound_event(session, graph):
    """Return (offset, replacement bytes) after preimage/capacity validation."""
    if graph.get("native_placement", {}).get("presence_by_page_condition", False):
        raise ValueError("Condition-based presence only applies to newly placed NPCs, not existing native events")
    binding = graph.get("native_binding")
    if not isinstance(binding, dict):
        raise ValueError("Choose an existing native process to replace; new event allocation is not supported")
    if binding.get("map_id") != graph.get("map_id"):
        raise ValueError("Event map changed since native process selection; reselect the process")
    pages = graph.get("pages", [])
    if len(pages) != 1:
        raise ValueError("Native process replacement supports one unconditional page")
    page = pages[0]
    if page.get("default_move_route"):
        raise ValueError("Default route controller export is not yet validated; it cannot be silently ignored")
    if page.get("conditions") or page.get("class_id", graph.get("class_id")) is not None:
        raise ValueError("Page conditions and new class placement cannot be installed yet")
    key = binding.get("script_key")
    trigger = page.get("trigger", graph.get("trigger"))
    expected = {"interact": "F", "touch": "D"}.get(trigger)
    if not isinstance(key, str) or not expected or not key.startswith(expected + " "):
        raise ValueError("Choose F for an existing interaction or D for an existing touch process")
    roots = script_roots(session, graph["map_id"])
    if key not in roots:
        raise ValueError("Bound process no longer exists")
    rows = instructions(session, graph["map_id"], key)
    if not rows or rows[-1][1] != 255:
        raise ValueError("Existing process must decode completely through End process")
    start = rows[0][0]; stop = rows[-1][0] + rows[-1][2]
    if any(other != key and start <= value[0] < stop for other, value in roots.items()):
        raise ValueError("Process storage is shared with another root; replacement refused")
    for other in roots:
        if other == key:
            continue
        for offset, opcode, size in instructions(session, graph["map_id"], other):
            if opcode in (0x57, 0x58, *range(0x78, 0x82)):
                raise ValueError("Other processes use indirect/choice branches; storage isolation cannot be proven")
            if opcode == 2:
                # Goto has a relative operand, but the archived evidence does
                # not establish a universal dispatcher base. Reject this map
                # rather than guess whether it reaches the replacement.
                raise ValueError("Another process uses Goto; storage isolation cannot be proven")
            if opcode in (3, 4, 0x30):
                target = offset + struct.unpack_from("<h", session.data, offset + size - 2)[0]
                if start <= target < stop:
                    raise ValueError("Another process branches into this storage; replacement refused")
    current = bytes(session.data[start:stop])
    if hashlib.sha256(current).hexdigest() != binding.get("process_sha256"):
        raise ValueError("Bound native process changed since selection; reselect it before compiling")
    output = bytearray()
    commands = page.get("commands", [])
    for index, command in enumerate(commands):
        kind = command.get("type")
        if kind == "show_dialogue":
            native_offset = command.get("native_instruction_offset")
            row = next((row for row in rows if row[0] == native_offset and row[1] in (0x0D, 0x5C)), None)
            if row is None or command.get("speaker") is not None:
                raise ValueError("Dialogue must reuse an existing Show Text instruction; new speaker assignment is not compiled")
            _dialogue_patch(session, graph["map_id"], command)
            output.extend(session.data[native_offset:native_offset + row[2]])
        elif kind == "change_music":
            from music_database import encode_music
            output.extend(encode_music(command.get("music_id")))
        elif kind == "play_sound":
            from sound_database import encode_sound
            output.extend(encode_sound(command.get("sound_id")))
        elif kind == "stop_sound":
            from sound_database import encode_stop_sound
            output.extend(encode_stop_sound(command.get("sound_id")))
        elif kind == "set_switch":
            operand = command.get("native_flag_operand")
            if (type(operand) is not int or not (0 <= operand <= 0x07FF or 0x8000 <= operand <= 0x87FF)
                    or type(command.get("value")) is not bool):
                raise ValueError("Set switch needs an explicitly selected native flag operand and ON/OFF value")
            output.extend(struct.pack("<BH", 5 if command["value"] else 6, operand))
        elif kind == "warp_player":
            if index != len(commands) - 1:
                raise ValueError("Change map must be the final command")
            values = [command.get(k) for k in ("map_id", "x", "y")]
            z = command.get("z")
            if not all(type(v) is int for v in values) or not 0 <= values[0] < 2547 or not all(0 <= v <= 255 for v in values[1:]) or type(z) is not int or not 0 <= z <= 255:
                raise ValueError("Change map needs valid native map, X, Y and explicit Z coordinates")
            output.extend(struct.pack("<BH5B", 0x53, *values, z, 0, 0))
        elif kind == "repeat":
            raise ValueError("Repeat actions currently require a newly allocated event process, not existing native replacement storage")
        else:
            raise ValueError(f"{kind} has no verified native compiler yet")
    output.append(255)
    if len(output) > len(current):
        raise ValueError(f"Process has {len(current)} bytes; commands need {len(output)} bytes")
    return start, bytes(output).ljust(len(current), b"\xff")


def _dialogue_patch(session, map_id, command):
    from map_text import dialogue_entry
    row = dialogue_entry(session, map_id, command["native_instruction_offset"])
    if row is None:
        raise ValueError("Dialogue entry cannot be resolved")
    _, offset, old = row
    if hashlib.sha256(old).hexdigest() != command.get("native_text_sha256"):
        raise ValueError("Dialogue changed since selection; reselect it before compiling")
    text = command.get("text")
    if not isinstance(text, str):
        raise ValueError("Dialogue needs text")
    auto_wrap = command.get("auto_wrap", False)
    if type(auto_wrap) is not bool:
        raise ValueError("Automatic dialogue wrapping must be ON/OFF")
    if auto_wrap:
        from dialogue_layout import format_dialogue
        text = format_dialogue(text)
    try:
        raw = text.encode("latin-1")
    except UnicodeEncodeError:
        raise ValueError("Dialogue contains characters outside the game's byte character set")
    if b"\0" in raw or len(raw) > len(old):
        raise ValueError(f"Existing dialogue has capacity for {len(old)} bytes")
    return offset, raw.ljust(len(old), b" ")


def dialogue_binding(session, map_id, offset):
    """Capture an existing speaker/text reference for a Show Text command."""
    from map_text import dialogue_entry, dialogue_reference
    if dialogue_reference(session.data, offset) is None:
        raise ValueError("Choose an existing Show Text instruction")
    row = dialogue_entry(session, map_id, offset)
    if row is None:
        raise ValueError("Dialogue entry cannot be resolved")
    return {"native_instruction_offset": offset,
            "native_text_sha256": hashlib.sha256(row[2]).hexdigest()}


def bound_event_replacements(session, graph):
    process = compile_bound_event(session, graph)
    return [process] + [_dialogue_patch(session, graph["map_id"], command)
                        for command in graph["pages"][0].get("commands", [])
                        if command.get("type") == "show_dialogue"]
