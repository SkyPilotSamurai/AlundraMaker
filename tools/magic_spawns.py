"""What each magic spawns when Alundra uses it, and changing it (user 2026-10-26).

Stock US 1.1 ALUN_CD.EXE (static, 2026-10-26; the item code is ported in remake/engine/items.py):
each magic routine spawns a global-bank class with 0x8003A860(Alundra, 0 = global, a2 = sprite,
x, y, z, dir); a2 is a fixed `addiu a2, zero, n` at the addresses below. Changing n spawns another
global class (0-150) in its place, with the magic's own placement and timing. Water Scroll and
Water Book share one routine (0x80035F1C), so they share their class. Class data 'magic_spawns'
= {address: catalogue index}, on the magic item."""
import struct

# item id: [(address, stock sprite, what it is)]
SITES = {
    43: [(0x80035B40, 0x10, 'Rocks')],
    44: [(0x80035E00, 0x11, 'Boulders')],
    45: [(0x80035FF0, 0x13, 'Water (shared with Water Book)')],
    46: [(0x80035FF0, 0x13, 'Water (shared with Water Scroll)')],
    47: [(0x80036294, 0x14, 'Fire'), (0x80036370, 0x17, 'Sparks')],
    48: [(0x800364B4, 0x15, 'Fire storm')],
    49: [(0x80036860, 0x16, 'Whirlwind'), (0x800368EC, 0x16, 'Whirlwind (second)')],
    50: [(0x80036AD8, 0x18, 'Tornado')],
}
GLOBAL_SPRITES = 151
# Any item Circle can use (ids 31-50: the start/end/tick jump tables are indexed by id - 31) can be
# given the Magic category and behave like one of the magic above (user 2026-10-27).
USABLE = range(31, 51)
DEFAULT_LIKE = min(SITES)


def sites(row):
    """The spawn sites the item's magic runs: its own, or those of the magic it behaves like."""
    return SITES.get(behaves_like(row), [])


# "Behaves like another magic" (user 2026-10-26). Static, stock US 1.1: Circle starts, ends and
# ticks the item in use through three 20-word jump tables indexed by item id - 31 (0x80035188 ->
# 0x8002339C, 0x80035864 -> 0x800233EC, 0x80036BB0 -> 0x800235F4); each case passes the item id
# (0x801F121C) in a0. Its XA clip is the byte 0x80023365 + item id. Pointing an item's three
# entries and clip at another magic's runs that magic's code; the spawned class then follows that
# magic's routine, so it is shared with that magic. Class data 'magic_behaves_like' = item id.
JUMP_TABLES = (0x8002339C, 0x800233EC, 0x800235F4)
XA_CLIPS = 0x80023365


def behaves_like(row):
    own = ((row or {}).get('source') or {}).get('item_id')
    donor = (((row or {}).get('data') or {}).get('magic_behaves_like'))
    return donor if own in USABLE and donor in SITES else own


# Water's routine 0x80035F1C compares its item id (a0, kept in s0) with Water Scroll 0x2D (0x80035F88,
# 0x800360FC): another id gets Water Book's table and full heal. An item behaving like Water Scroll
# ticks through WaterScrollStub instead of item_tick's own case 0x80036C64 (lui/lw a0 = item in use;
# jal 0x80035F1C; j 0x80036CE0; move v1,v0), the same case with a0 = 0x2D (user 2026-10-27).
WATER_SCROLL, WATER_TICK, TICK_DONE = 45, 0x80035F1C, 0x80036CE0


def needs_water_stub(definitions):
    return any(row.get('kind') == 'item' and not row.get('clone_of') and (row.get('source') or {}).get('item_id') != WATER_SCROLL
               and behaves_like(row) == WATER_SCROLL for row in definitions)


class WaterScrollStub:
    length = 20
    def __call__(self, address):
        return struct.pack('<5I', 0x24040000 | WATER_SCROLL, 0x0C000000 | (WATER_TICK >> 2 & 0x3FFFFFF), 0,
                           0x08000000 | (TICK_DONE >> 2 & 0x3FFFFFF), 0x00401821)   # addiu a0,zero,0x2D; jal; nop; j; move v1,v0


def patch_behaviour(exe, definitions, water_stub=None):
    exe = bytearray(exe); load = struct.unpack_from('<I', exe, 0x18)[0]; stock = bytes(exe); report = []
    for row in definitions:
        own = ((row.get('source') or {}).get('item_id')); donor = behaves_like(row)
        if row.get('kind') != 'item' or row.get('clone_of') or own not in USABLE or donor == own:
            continue
        for table in JUMP_TABLES:
            o = table - load + 0x800
            exe[o + 4 * (own - 31):o + 4 * (own - 31) + 4] = stock[o + 4 * (donor - 31):o + 4 * (donor - 31) + 4]
        if donor == WATER_SCROLL:
            if water_stub is None: raise ValueError(f"{row.get('name')}: Water Scroll behaviour needs its stub")
            struct.pack_into('<I', exe, JUMP_TABLES[2] - load + 0x800 + 4 * (own - 31), water_stub)
        o = XA_CLIPS - load + 0x800; exe[o + own] = stock[o + donor]
        report.append(dict(item=own, behaves_like=donor))
    return bytes(exe), report


def current(row, address, stock):
    return (((row or {}).get('data') or {}).get('magic_spawns') or {}).get(str(address), stock)


def patch(exe, definitions, datas=None):
    palette_ok = {}
    exe = bytearray(exe); load = struct.unpack_from('<I', exe, 0x18)[0]; report = []; done = {}
    for row in definitions:
        if row.get('kind') != 'item' or row.get('clone_of'):
            continue
        for address, stock, what in sites(row):
            n = current(row, address, stock)
            if n == stock:
                continue
            if type(n) is not int or not 0 <= n < GLOBAL_SPRITES:
                raise ValueError(f"{row.get('name')}: {what} must be a global class (0-{GLOBAL_SPRITES - 1})")
            if n not in palette_ok:
                import global_sprite_recolor   # at most 4 palettes (user 2026-10-27)
                palette_ok[n] = len(global_sprite_recolor.palettes_of(datas, n)) <= 4 if datas else True
            if not palette_ok[n]:
                raise ValueError(f"{row.get('name')}: {what} can only spawn a class with at most 4 palettes")
            if address in done:
                if done[address] != n:
                    raise ValueError(f"{row.get('name')}: shares its magic with another item; give both the same class")
                continue
            o = address - load + 0x800
            if struct.unpack_from('<I', exe, o)[0] != (0x24060000 | stock):
                raise ValueError(f"{row.get('name')}: magic code differs from the stock game")
            struct.pack_into('<I', exe, o, 0x24060000 | n)
            done[address] = n; report.append(dict(item=row['source']['item_id'], address=hex(address), sprite=n))
    return bytes(exe), report
