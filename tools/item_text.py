"""In-game item, weapon and armor text (user 2026-10-26).

DATA/ETC_USA.R (decoder: xcasadio AlundraTools EtcResUsa.cs @242b09a, lines 54-86; disc_extract.do_text):
1024 signed 16-bit offsets, then NUL-terminated latin-1 strings. 0x200+id = name, 0x280+id = description,
0x300+id = description second line; id = native item id (0..97, catalogue index - 30). '{B' is an apostrophe.
The file is rebuilt with every string kept; it may not grow past the stock size, since the size of the
game's load buffer for it is not recovered. Class data 'game_text' = {name, description, description2}."""
import struct

NAME = 'DATA/ETC_USA.R'
FIELDS = (('name', 0x200), ('description', 0x280), ('description2', 0x300))


def _at(raw, slot):
    off = struct.unpack_from('<h', raw, 2 * slot)[0]
    if off < 0x800 or off >= len(raw):
        return None
    return raw[off:raw.index(0, off)].decode('latin-1')


def _show(text):
    return None if text is None else text.replace('{B', "'")


def native_id(row):
    from item_categories import item_id
    try:
        return item_id(row)
    except ValueError:
        return None


def stock(raw, row):
    n = native_id(row)
    return {} if n is None else {key: _show(_at(raw, base + n)) or '' for key, base in FIELDS}


def patch(raw, definitions):
    """Rebuild ETC_USA.R with every class's edited text; returns (bytes, report)."""
    strings = [_at(raw, slot) for slot in range(1024)]; report = []; seen = {}
    for row in definitions:
        text = (row.get('data') or {}).get('game_text') or {}
        n = native_id(row)
        if not text or n is None or row.get('kind') not in ('item', 'weapon', 'armor') or row.get('clone_of'):
            continue
        for key, base in FIELDS:
            if key not in text:
                continue
            value = str(text[key]).replace("'", '{B')
            try:
                value.encode('latin-1')
            except UnicodeEncodeError:
                raise ValueError(f"{row.get('name')}: game text can only use plain letters")
            if '\0' in value:
                raise ValueError(f"{row.get('name')}: game text cannot contain a NUL")
            if seen.get(base + n, value) != value:
                raise ValueError(f"{row.get('name')}: two classes change the same game text")
            seen[base + n] = value
            if strings[base + n] != value:
                strings[base + n] = value; report.append(dict(item=n, field=key))
    if not report:
        return bytes(raw), []
    out = bytearray(0x800); placed = {}
    for slot, value in enumerate(strings):
        if value is None:
            struct.pack_into('<h', out, 2 * slot, struct.unpack_from('<h', raw, 2 * slot)[0] if struct.unpack_from('<h', raw, 2 * slot)[0] < 0x800 else -1)
            continue
        if value not in placed:
            placed[value] = len(out); out += value.encode('latin-1') + b'\0'
        struct.pack_into('<h', out, 2 * slot, placed[value])
    if len(out) > len(raw):
        raise ValueError(f'Game text is {len(out) - len(raw)} bytes longer than the game allows')
    out += bytes(len(raw) - len(out))
    return bytes(out), report
