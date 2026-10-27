"""Append map-local text while preserving all existing slots and text bytes."""
import struct
from map_block_repack import pointers, sections, replace_block
from map_loader_constraints import validate_layout


def append_local_text(datas, map_id, text, *, auto_wrap=False, taken=()):
    if type(map_id) is not int or not 0 <= map_id < 2547:
        raise ValueError("Map outside native table")
    if not isinstance(text, str):
        raise ValueError("Dialogue needs text")
    if type(auto_wrap) is not bool:raise ValueError('Automatic dialogue wrapping must be ON/OFF')
    if auto_wrap:
        from dialogue_layout import format_dialogue
        text=format_dialogue(text)
    # The native text stream represents newlines with a literal backslash-N
    # control, as in retail map strings, rather than a UI textarea's LF byte.
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\N")
    try:
        payload = text.encode("latin-1")
    except UnicodeEncodeError:
        raise ValueError("Dialogue contains characters outside the game's byte character set")
    if b"\0" in payload:
        raise ValueError("Dialogue cannot contain a zero byte")
    table = pointers(datas)
    from map_block_repack import _trim_text_tail
    # new text goes right after the last string, not after the 2048 padding
    block = bytearray(_trim_text_tail(bytes(datas[table[map_id]:table[map_id + 1]])))
    start = sections(block)[6]
    if start + 256 > len(block):
        raise ValueError("Map has no complete128-slot text table")
    values = list(struct.unpack_from("<128h", block, start))
    # Retail maps populate all128 pointers, including empty/Disuse slots. Never
    # replace a slot referenced by any existing constant Show Text byte pattern;
    # scanning every byte (including unreachable payload) is conservative and
    # intentionally permits false positives instead of missing an instruction.
    from native_script_allocation import script_tables
    boundary = sections(block)
    _, _, code, _ = script_tables(block[boundary[3]:boundary[4]])
    used = set()
    for pos, opcode in enumerate(code):
        operand = {0x0D: 1, 0x5C: 2}.get(opcode)
        if operand is not None and pos + operand < len(code) and code[pos + operand] & 128:
            used.add(code[pos + operand] & 127)
    used |= set(taken)   # slots shown by code not in the map yet (death texts in the victory watcher)
    slot = None
    for i, value in enumerate(values):
        if i in used:
            continue
        if value == 0:
            slot = i; break
        if value < 256 or not start + value < len(block):
            continue
        end = block.find(0, start + value)
        if end < 0:
            continue
        old = bytes(block[start + value:end])
        if old in (b"", b"#Disuse", b"\\C#Disuse", b"\\D#Disuse", b"\\E#Disuse", b"\\F#Disuse"):
            slot = i; break
    if slot is None:
        # A project map (new map or a copy of one, 483+, or a blank map saved over an old one):
        # every slot is filled with the copied room's texts. Reuse the last one no script of
        # this map shows (2026-10-21: Melzas in a fresh copy of the Dark Dragon room).
        from local_sprite_import import PROJECT_BLANK_MAPS
        if map_id >= 483 or map_id in PROJECT_BLANK_MAPS:
            slot = next((i for i in range(127, 0, -1) if i not in used), None)
    if slot is None:
        raise ValueError("Map has no unused native text slot")
    relative = len(block) - start
    pool_report = {}
    if not 256 <= relative <= 32767 or relative + len(payload) + 1 > 32768:
        # Repeated sector-aligned section replacements can leave a large tail
        # after the mapped strings. Retain that whole tail rather than assume
        # it is disposable padding, and keep every old string offset unchanged.
        from native_text_pool_repack import repack_pool
        block, pool_report = repack_pool(block, start, values, slot, payload)
    else:
        struct.pack_into("<h", block, start + 2 * slot, relative)
        block.extend(payload + b"\0")
    result = replace_block(datas, map_id, block)
    validate_layout(result)
    return result, {"map_id": map_id, "text_index": slot,
                    "dialogue_reference": 128 | slot,
                    "text_bytes": len(payload),"auto_wrap":auto_wrap,
                    "layout_metrics":"pinned randomizer source" if auto_wrap else "author-supplied controls",
                    "gameplay_verified": False, **pool_report}
