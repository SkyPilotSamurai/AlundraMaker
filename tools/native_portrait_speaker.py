"""Portrait and name of a database NPC that is not on the map (user 2026-10-26).

Stock ALUN_CD.EXE US 1.1, op 5C (0x8003FAF0) shows the speaker actor's portrait with
0x80059AE4(&X, &Y, &Z, &camX 0x801EF434; &camY 0x801EF438, u, v, w, h, clut, tpage), where
u..h and the page/palette bytes are the first quad of the sprite record's frame root
(actor+0x64 -> record, record+0x0C -> frames; entity_preview.decode_portrait), tpage =
u16 0x801F2E10[actor+0x1B0 + (page & 7)] and clut = u16 0x8012E2A0[actor+0x1B4 + palette].
Those tables are built at 0x8002C1C0 (tpage ids for VRAM x 320..960, y 0/256, 4 blend rows of
22) and 0x8002C24C (clut ids x 0..256, rows 480..511, index = column*32 + row). The bases are
set by 0x8003A424: map-local sprite 0 / 0x20, global sprite 11 / 0x60. Then 0x8005C0A8(id)
sets the speaker name. Details: docs/2026-10-26-portrait-without-speaker.txt.

  F2 tpage_index clut_index u v w h id_lo id_hi   (9 bytes)

When the NPC's sprite is not on the map, the export copies only its portrait image into an
all-zero area of the map's texture bank that no sprite quad of the map uses, and appends its
palette (no entity, nothing else moves); the map loader uploads both. Indices are computed at export. The portrait
starts from Alundra's position. Waits (yields) while a dialogue box is busy (0x80045F8C, as
0x80042F74 does). Original MIPS, not recovered vanilla code. Not verified in game."""
import struct

OPCODE = 0xF2
SIZE = 9
PORTRAIT = 0x80059AE4
NAME = 0x8005C0A8
BUSY = 0x80045F8C
TPAGES = 0x801F2E10
CLUTS = 0x8012E2A0
PLAYER_XYZ = 0x801AC80C
CAMERA_X, CAMERA_Y = 0x801EF434, 0x801EF438
LOCAL_TPAGE, LOCAL_CLUT = 0, 0x20
STOCK = {PORTRAIT: 0x27BDFFC8, NAME: 0x3C02801F, BUSY: None, 0x8003FBC8: 0x0C000000 | (PORTRAIT >> 2 & 0x3FFFFFF),
         0x8003FBD4: 0x0C000000 | (NAME >> 2 & 0x3FFFFFF), 0x8003A44C: 0x2402000B, 0x8003A454: 0x24020060}


def verify(exe, load=0x80020000):
    for address, word in STOCK.items():
        if word is not None and struct.unpack_from('<I', exe, address - load + 0x800)[0] != word:
            raise ValueError('Portrait speaker: unexpected stock code at 0x%08X' % address)


def _jal(address):
    return 0x0C000000 | (address >> 2 & 0x3FFFFFF)


def emit():
    """a2 -> opcode pointer. Returns 0 (yield) while dialogue is busy, else 9."""
    w = []
    I = lambda op, rs, rt, im: w.append(op << 26 | rs << 21 | rt << 16 | (im & 0xFFFF))
    SP, RA, S0, V0, A0, A1, A2, A3, T0, T1, AT = 29, 31, 16, 2, 4, 5, 6, 7, 8, 9, 1
    def li(rt, v): I(15, 0, rt, (v + 0x8000) >> 16); I(9, rt, rt, v)
    I(9, SP, SP, -0x40); I(43, SP, RA, 0x38); I(43, SP, S0, 0x34)
    I(35, A2, S0, 0); w.append(_jal(BUSY)); w.append(0)
    busy_at = len(w); w.append(0); w.append(0)                  # bnez v0, busy
    I(36, S0, V0, 1); w.append(0); w.append(V0 << 16 | V0 << 11 | 1 << 6)   # lbu; sll v0,v0,1
    I(15, 0, AT, (TPAGES + 0x8000) >> 16); w.append(AT << 21 | V0 << 16 | AT << 11 | 0x21); I(37, AT, T0, TPAGES)
    I(36, S0, V0, 2); w.append(0); w.append(V0 << 16 | V0 << 11 | 1 << 6)
    I(15, 0, AT, (CLUTS + 0x8000) >> 16); w.append(AT << 21 | V0 << 16 | AT << 11 | 0x21); I(37, AT, T1, CLUTS); w.append(0)
    I(43, SP, T1, 0x24); I(43, SP, T0, 0x28)
    for k, off in ((3, 0x14), (4, 0x18), (5, 0x1C), (6, 0x20)):
        I(36, S0, V0, k); w.append(0); I(43, SP, V0, off)
    li(V0, CAMERA_Y); I(43, SP, V0, 0x10)
    li(A0, PLAYER_XYZ); I(9, A0, A1, 4); I(9, A0, A2, 8); li(A3, CAMERA_X)
    w.append(_jal(PORTRAIT)); w.append(0)
    I(36, S0, A0, 7); I(36, S0, V0, 8); w.append(0); w.append(V0 << 16 | V0 << 11 | 8 << 6); w.append(A0 << 21 | V0 << 16 | A0 << 11 | 0x25)
    w.append(_jal(NAME)); w.append(0)
    done_at = len(w); w.append(0); I(9, 0, V0, SIZE)              # b out; v0 = 9
    busy = len(w); I(9, 0, V0, 0)
    out = len(w); I(35, SP, RA, 0x38); I(35, SP, S0, 0x34); w.append(0x03E00008); I(9, SP, SP, 0x40)
    w[busy_at] = 5 << 26 | V0 << 21 | ((busy - busy_at - 1) & 0xFFFF)
    w[done_at] = 4 << 26 | ((out - done_at - 1) & 0xFFFF)
    return struct.pack('<%dI' % len(w), *w)


def portrait_quad(data, map_id, slot):
    """First quad of a map-local sprite's portrait frame: (page, palette, u, v, w, h), or None."""
    from local_sprite_import import sprite_assets
    assets = sprite_assets(data, map_id, slot)
    record = assets['record']
    if not data[record + 18] & 0x80:   # HasPortrait (actor+0x6C bit 0x00800000, op 5C)
        return None
    q = record - assets['relative'] + assets['roots'][3] + 2
    return tuple(data[q:q + 6])


def _free_area(raw, used, w, h, blank=True):
    """(page, u, v) of a w*h area whose texels are all 0 and no sprite quad uses, else None."""
    for page in range(len(raw) // 32768):
        rows = [raw[page * 32768 + y * 128:page * 32768 + y * 128 + 128] for y in range(256)]
        for v in range(0, 257 - h, 8):
            for u in range(0, 257 - w, 8):
                if any((page, x // 8, y // 8) in used for y in range(v, v + h, 8) for x in range(u, u + w, 8)):
                    continue
                if blank and any(rows[y][u // 2:(u + w + 1) // 2].strip(bytes(1)) for y in range(v, v + h)):
                    continue
                return page, u, v
    return None


def place_portrait(data, map_id, home, slot, keep=(), taken=None):
    """Copy only the portrait image of `slot` (home map) into a free area of this map's texture
    bank, and append its palette. Nothing else of the map moves or changes. (data, quad) or None."""
    from local_sprite_import import layout, sprite_assets, MAX_PALETTES
    from texture_codec import unpack_ez, pack_ez
    from map_block_repack import replace_section
    from map_loader_constraints import validate_layout
    from native_class_placement import record_cluster
    quad = portrait_quad(data, home, slot)
    if quad is None:
        return None
    page, palette, u, v, w, h = quad
    if u + w > 256 or v + h > 256:
        return None
    db, dh, ds, de, dsh = layout(data, home)
    draw, _ = unpack_ez(data[db + dh[4]:db + dh[5]], limit=262144)
    tb, th, ts, te, tsh = layout(data, map_id)
    traw, _ = unpack_ez(data[tb + th[4]:tb + th[5]], limit=262144)
    # A new map (483+ or an original map saved as a new map) keeps its template's sprite table:
    # art of slots nothing on it places is free, as in import_local_sprite (keep = slots events place).
    from local_sprite_import import PROJECT_BLANK_MAPS
    cluster = record_cluster(data, map_id)
    reuse = map_id >= 483 or map_id in PROJECT_BLANK_MAPS
    in_use = {raw[6] for raw in cluster['entities'] if raw[5] & 128} | set(keep)
    effects = any(struct.unpack_from('<i', data, a)[0] not in (0, -1) for a in range(ts + tsh[4], ts + tsh[5], 4))
    blank = not (reuse and (not effects or not any(cluster['events'])))   # effect art is not decoded
    used = set()   # 8x8 cells any sprite quad of this map draws from
    for i in range((tsh[4] - tsh[3]) // 4):
        if struct.unpack_from('<i', data, ts + tsh[3] + i * 4)[0] in (0, -1) or (reuse and i not in in_use):
            continue
        for q in sprite_assets(data, map_id, i)['quads']:
            qp, _, qu, qv, qw, qh = data[q:q + 6]
            used.update((qp & 7, x // 8, y // 8) for y in range(qv, min(256, qv + qh) + 7, 8) for x in range(qu, min(256, qu + qw) + 7, 8))
    taken = set() if taken is None else taken   # cells of portraits placed earlier on this map
    spot = _free_area(traw, used | taken, w, h, blank)
    tcount = (tsh[6] - tsh[5]) // 32
    start = ds + dsh[5] + palette * 32
    if spot is None:
        print('Portrait: no free %dx%d texture area on map %d' % (w, h, map_id))
    if spot is None or palette >= (dsh[6] - dsh[5]) // 32:
        return None
    colours = bytes(data[start:start + 32])
    table = [bytes(data[ts + tsh[5] + 32 * i:ts + tsh[5] + 32 * i + 32]) for i in range(tcount)]
    if colours not in table and tcount + 1 > MAX_PALETTES:
        print('Portrait: map %d has %d palettes (limit %d)' % (map_id, tcount, MAX_PALETTES))
        return None
    if bytes(data[ts + tsh[5] + 32 * tcount:ts + tsh[6]]) != bytes(4):
        return None
    tp, tu, tv = spot
    taken.update((tp, x // 8, y // 8) for y in range(tv, tv + h, 8) for x in range(tu, tu + w, 8))
    traw = bytearray(traw)
    for y in range(h):   # 4 bpp, u and w even
        src = page * 32768 + (v + y) * 128 + u // 2
        dst = tp * 32768 + (tv + y) * 128 + tu // 2
        traw[dst:dst + (w + 1) // 2] = draw[src:src + (w + 1) // 2]
    if colours in table:   # an identical palette is already on the map: only the image changes
        page_head = bytes(data[tb + th[4]:tb + th[4] + 6])
        packed = pack_ez(bytes(traw), page_head); packed += bytes((-len(packed)) % 4)
        result = replace_section(data, map_id, 4, packed); validate_layout(result)
        return result, (tp, table.index(colours), tu, tv, w, h)
    # palette appended the way import_local_sprite does: new palette table + relocated cluster
    section = bytearray(data[ts:te]); section.extend(bytes((-len(section)) % 4))
    roots = list(tsh); roots[5] = len(section)
    section.extend(data[ts + tsh[5]:ts + tsh[5] + 32 * tcount] + data[start:start + 32] + bytes(4))
    shift = len(section) - tsh[6]
    section.extend(data[ts + tsh[6]:ts + tsh[0]])
    for i in range(6, 12):
        roots[i] = tsh[i] + shift
    roots[0] = len(section); section.extend(b''.join(cluster['entities']) + cluster['entity_terminator'])
    roots[1] = len(section); section.extend(cluster['effects'])
    roots[2] = len(section); section.extend(b''.join(cluster['events']) + bytes(4))
    section.extend(bytes((-len(section)) % 4)); struct.pack_into('<12I', section, 0, *roots)
    page_head = bytes(data[tb + th[4]:tb + th[4] + 6])
    result = replace_section(data, map_id, 3, section)
    packed = pack_ez(bytes(traw), page_head); packed += bytes((-len(packed)) % 4)
    result = replace_section(result, map_id, 4, packed); validate_layout(result)
    return result, (tp, tcount, tu, tv, w, h)


def compile_portrait(data, map_id, catalogue, keep=(), taken=None):
    """(data, F2 bytes); the NPC's portrait is put on this map when absent. (data, None) if impossible."""
    from local_sprite_import import sprite_assets
    if type(catalogue) is not int or not 256 <= catalogue < 512:
        return data, None
    slot = catalogue - 256
    try:
        sprite_assets(data, map_id, slot)
        quad = portrait_quad(data, map_id, slot)
    except ValueError:
        from behavior_transplant import local_sprite_home
        home = local_sprite_home(data, slot)
        placed = None if home is None else place_portrait(data, map_id, home, slot, keep, taken)
        if placed is None:
            return data, None
        data, quad = placed
    if quad is None:
        return data, None
    page, palette, u, v, w, h = quad
    clut = LOCAL_CLUT + palette
    if clut >= 160 or not w or not h:
        return data, None
    return data, bytes((OPCODE, LOCAL_TPAGE + (page & 7), clut, u, v, w, h, catalogue & 0xFF, catalogue >> 8))
