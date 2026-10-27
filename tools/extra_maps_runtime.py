"""Game code support for maps beyond 483 (see map_slots.py).

Static evidence, stock US v1.1 ALUN_CD.EXE (12f12eaf...):
* 8002C2B0 jal 80083F04 (read file) with a3=0x7B8 in the delay slot: the
  DATAS header (10 words + 484 map offsets) is read into 801EF440. The words
  right after it (801EFBF8, 801EFBFC, 801EFC00, 801EFC08) are other variables,
  so the RAM copy cannot simply grow.
* 8002C344/8002C360: s4 = 801EF468 (offset of map m), s5 = s4 + 4 (offset of
  map m+1); both are only used at 8002C480/8002C484 by the map CD read
  (a2 = table[m], a3 = table[m+1] - table[m]).
* 8004AFD4/AFDC: map -> default music, 483-word table at 800C8404.
* 8004B0DC/B0E4: map -> sound-effect bank, 483-word table at 800C8B90
  (xcasadio GetSoundGroupByMapId / VabIndexByMapId).
* 80083DBC: the new-game loop sets all 500 map-index entries to themselves.
* 800318E4..80031904: a door (portal) stores table[destination] (lh from the
  500-entry index table at 801DD434) as the next map. Event transfers
  (opcode 53, 8003F67C) store the map number directly, no table.

Patch: a hook calls the original header read, then reads 0x800 header bytes
into a buffer of its own and, with expanded maps, the extended offset table
right behind entry 500 (buffer + 0x7FC); the map loader takes offsets from
that buffer (s4 = buffer + 0x28, next offset from 4(v0)); music and sound-bank
lookups use copies sized for every map; doors to maps >= 500 skip the index
table. Original words are checked before every write. Static only: needs
emulator testing.
"""
import struct

READ_FILE = 0x80083F04
DATAS_NAME = 0x800C7DD4
SITES = {   # va: stock word
    0x8002C2B0: 0x0C020FC1,   # jal 80083F04 (header read)
    0x8002C2B4: 0x240707B8,   # addiu a3,zero,0x7B8 (delay slot, kept)
    0x8002C344: 0x24540014,   # addiu s4,v0,0x14
    0x8002C360: 0x24550018,   # addiu s5,v0,0x18
    0x8002C484: 0x00551021,   # addu v0,v0,s5
    0x8002C48C: 0x8C470000,   # lw a3,0(v0)
    0x8004AFD4: 0x3C01800D,   # lui at,0x800D   (music table)
    0x8004AFDC: 0x8C228404,   # lw v0,-0x7BFC(at)
    0x8004B0DC: 0x3C01800D,   # lui at,0x800D   (sound bank table)
    0x8004B0E4: 0x8C228B90,   # lw v0,-0x7470(at)
}
DOOR_SITES = {
    0x800318F4: 0x3C01801E,   # lui at,0x801E
    0x800318F8: 0x00220821,   # addu at,at,v0       (v0 = destination * 2)
    0x800318FC: 0x8428D434,   # lh t0,-0x2BCC(at)   index table 801DD434
}
MUSIC_TABLE, SFX_TABLE, STOCK_MAPS, SLOT_MAPS = 0x800C8404, 0x800C8B90, 483, 500
WRAPPER_WORDS, DOOR_WORDS = 23, 10
HEADER_SIZE = 0x800


class Block:
    """Address-independent description; called with its address to build bytes."""

    def __init__(self, music, sfx, ext_offset=0, ext_count=0):
        if len(music) != len(sfx) or len(music) < SLOT_MAPS:
            raise ValueError('Per-map tables need an entry for every map')
        self.music, self.sfx, self.ext_offset, self.ext_count = list(music), list(sfx), ext_offset, ext_count
        buffer = HEADER_SIZE - 4 + 4 * ext_count
        self.buffer_size = buffer + (-buffer) % 8
        self.length = (WRAPPER_WORDS + DOOR_WORDS) * 4 + self.buffer_size + 8 * len(music)

    def layout(self, address):
        door = address + WRAPPER_WORDS * 4
        buffer = door + DOOR_WORDS * 4
        music = buffer + self.buffer_size
        sfx = music + 4 * len(self.music)
        return door, buffer, music, sfx

    def __call__(self, address):
        if address % 8:
            raise ValueError('Extra map block must be 8-byte aligned')
        door, buffer, music, sfx = self.layout(address)
        jal = 0x0C000000 | ((READ_FILE >> 2) & 0x3FFFFFF)
        nh, nl = hi_lo(DATAS_NAME); bh, bl = hi_lo(buffer); eh, el = hi_lo(buffer + 0x7FC)
        code = [
            0x27BDFFE8, 0xAFBF0010,                 # addiu sp,-24 / sw ra,16(sp)
            jal, 0x00000000,                        # original header read
            0x3C040000 | nh, 0x24840000 | nl,       # a0 = DATAS name
            0x3C050000 | bh, 0x24A50000 | bl,       # a1 = header buffer
            0x00003021, jal, 0x24070800,            # a2 = 0; read 0x800 bytes
        ]
        if self.ext_count:
            code += [0x3C040000 | nh, 0x24840000 | nl,
                     0x3C050000 | eh, 0x24A50000 | el,            # a1 = buffer + 0x7FC
                     0x3C060000 | (self.ext_offset >> 16), 0x34C60000 | (self.ext_offset & 0xFFFF),  # a2 = table offset
                     jal, 0x24070000 | (4 * self.ext_count)]     # read the extended offsets
        else:
            code += [0] * 8
        code += [0x8FBF0010, 0x27BD0018, 0x03E00008, 0x00000000]  # lw ra / addiu sp / jr ra / nop
        assert len(code) == WRAPPER_WORDS
        door_code = [
            0x00024042,   # srl t0,v0,1          destination map
            0x2D0101F4,   # sltiu at,t0,500
            0x10200004,   # beqz at,done         500+: use the number itself
            0x00000000,
            0x3C01801E,   # lui at,0x801E
            0x00220821,   # addu at,at,v0
            0x8428D434,   # lh t0,-0x2BCC(at)    index table (map variants)
            0x03E00008, 0x00000000,   # done: jr ra / nop
            0x00000000,
        ]
        assert len(door_code) == DOOR_WORDS
        raw = struct.pack(f'<{WRAPPER_WORDS}I', *code) + struct.pack(f'<{DOOR_WORDS}I', *door_code)
        raw += bytes(self.buffer_size)
        raw += struct.pack(f'<{len(self.music)}i', *self.music) + struct.pack(f'<{len(self.sfx)}i', *self.sfx)
        assert len(raw) == self.length
        return raw


def hi_lo(address):
    hi = (address + 0x8000) >> 16 & 0xFFFF
    return hi, address & 0xFFFF


def patch_sites(exe, address, offset, block):
    """Write the hooks. offset(exe, va) -> file offset (from native_lr_swaps)."""
    door, buffer, music, sfx = block.layout(address)
    for va, stock in {**SITES, **DOOR_SITES}.items():
        found = struct.unpack_from('<I', exe, offset(exe, va))[0]
        if found != stock:
            raise ValueError(f'New maps: game code at {va:08X} differs ({found:08X}); another patch changed the map loader')
    table_hi, table_lo = hi_lo(buffer + 0x28)
    mh, ml = hi_lo(music); sh, sl = hi_lo(sfx)
    words = {
        0x8002C2B0: 0x0C000000 | ((address >> 2) & 0x3FFFFFF),
        0x8002C344: 0x3C140000 | table_hi,          # lui s4,hi(table)
        0x8002C360: 0x26940000 | table_lo,          # addiu s4,s4,lo(table)   (s5 no longer needed)
        0x8002C484: 0x00541021,                     # addu v0,v0,s4
        0x8002C48C: 0x8C470004,                     # lw a3,4(v0)
        0x8004AFD4: 0x3C010000 | mh, 0x8004AFDC: 0x8C220000 | ml,
        0x8004B0DC: 0x3C010000 | sh, 0x8004B0E4: 0x8C220000 | sl,
    }
    if block.ext_count:
        words.update({0x800318F4: 0x0C000000 | ((door >> 2) & 0x3FFFFFF),   # jal door helper
                      0x800318F8: 0, 0x800318FC: 0})
    for va, word in words.items():
        struct.pack_into('<I', exe, offset(exe, va), word)
    return dict(feature='new_map_slots_hooks', block=hex(address), header_buffer=hex(buffer),
                music_table=hex(music), sound_bank_table=hex(sfx), maps=len(block.music),
                expanded_maps=block.ext_count, door_helper=hex(door) if block.ext_count else None,
                hooked=[hex(v) for v in words])


def stock_tables(exe, offset):
    music = list(struct.unpack_from(f'<{STOCK_MAPS}i', exe, offset(exe, MUSIC_TABLE, STOCK_MAPS * 4)))
    sfx = list(struct.unpack_from(f'<{STOCK_MAPS}i', exe, offset(exe, SFX_TABLE, STOCK_MAPS * 4)))
    return music, sfx


SOUND_SET_CONFLICTS = []


def boss_sound_banks(document, sfx):
    """{map: sound-effect bank}: a map with a boss uses the boss's home map's sound
    bank (its roars, attacks and effects live there); area music is left alone.
    Two bosses that need different banks cannot both have their sounds on one map
    (the first keeps them; SOUND_SET_CONFLICTS lists the others)."""
    del SOUND_SET_CONFLICTS[:]
    import object_library
    document = document or {}
    definitions = {r.get('id'): r for r in document.get('definitions') or []}
    chosen = {}
    for g in document.get('event_graphs') or []:
        m = g.get('map_id')
        for page in g.get('pages') or []:
            d = definitions.get(page.get('class_id', g.get('class_id'))) or {}
            if d.get('kind') != 'boss' or page.get('act_as_npc') and len(g.get('pages') or []) == 1:
                continue
            c = d.get('source', {}).get('catalogue_index')
            home = (g.get('native_placement') or {}).get('donor_map_id')
            fixed = d.get('source', {}).get('fixed_donor')
            if type(home) is not int and isinstance(fixed, list) and fixed:
                home = fixed[0]
            if type(home) is not int:
                info = object_library.object_info(c) if type(c) is int else None
                maps = sorted({p[0] for p in (info or {}).get('placements', [])})
                home = maps[0] if maps else None
            if type(home) is not int or not 0 <= home < len(sfx) or type(m) is not int:
                continue
            bank = sfx[home]
            old = chosen.get(m)
            if old is not None and old[0] != bank:
                # the first boss placed keeps its sounds; the other one's own sounds are wrong there
                SOUND_SET_CONFLICTS.append(f"Map {m}: {old[1]} and {d.get('name')} need different sound sets ({old[0]} and {bank}); {old[1]}'s is used")
                continue
            chosen[m] = (bank, d.get('name'))
    return {m: v[0] for m, v in chosen.items()}


def block_for(exe, offset, document, data):
    """Block with music / sound-bank tables for every map: stock values, the
    mod's music choices, and each new map's template sound bank.

    A map copied whole (map_create.create_copy_of_map, with copy_map_document
    carrying its events along) inherits its source's music and keeps the sound
    set its copied objects (including a copied boss) actually play in, instead
    of being overridden as if it were an empty new map."""
    from map_slots import map_count, ext_info
    total = max(SLOT_MAPS, map_count(data))
    music, sfx = stock_tables(exe, offset)
    music += [0] * (total - STOCK_MAPS); sfx += [0] * (total - STOCK_MAPS)
    slots = (document or {}).get('new_map_slots', {})
    copied = {}   # new map -> its stock source, for maps copied whole with their contents
    for m in range(STOCK_MAPS, map_count(data)):
        info = slots.get(str(m), {})
        template = info.get('template_map', 0)
        sfx[m] = sfx[template] if 0 <= template < STOCK_MAPS else 0
        source = info.get('copied_from')
        if type(source) is int and 0 <= source < STOCK_MAPS:
            music[m] = music[source]; sfx[m] = sfx[source]; copied[m] = source
    bosses = boss_sound_banks(document, sfx[:STOCK_MAPS])
    for m, bank in bosses.items():
        if 0 <= m < total:
            sfx[m] = bank
    # new maps without a boss: the sound set their game objects' own sounds are in (object_sound_banks)
    from object_sound_banks import choose
    taken = set(bosses) | set(copied)   # a copied map's sound bank already matches its copied contents
    for m, bank in choose(document, sfx[:STOCK_MAPS], {m: sfx[m] for m in range(STOCK_MAPS, total)}, taken, STOCK_MAPS).items():
        if 0 <= m < total:
            sfx[m] = bank
    for key, track in ((document or {}).get('map_music') or {}).items():
        m = int(key)
        if 0 <= m < total and type(track) is int:
            music[m] = track
    ext_offset, ext_count = ext_info(data)
    return Block(music, sfx, ext_offset, ext_count)