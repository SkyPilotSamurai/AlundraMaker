"""How the game's healing items heal Alundra, and editing it (user 2026-10-26).

From the remake's ports of the native item code (remake/engine/drops.py) and the stock US 1.1
ALUN_CD.EXE (static, 2026-10-26). The same routine runs when the item is used from the menu and
when it is used at once on pick-up (e.g. Herbs 0x80033560 is called from 0x8003466C and 0x80034E68).
Editable life heals (patched in place, no new code):
  Herbs 0x24          0x80033560: life += max(at_least, max_life >> shift)  sra 0x8003357C, slti 0x80033580, li 0x8003358C
  Strength Tonic 0x29 0x8003380C: same, sra 0x80033830, slti 0x80033834, li 0x80033840
  Large Life Drop 0x56 0x80033698: same, sra 0x800336BC, slti 0x800336C0, li 0x800336CC
  Life Drop 0x55      0x800335FC: life += max(1, max_life >> shift)          sra 0x80033618 (minimum fixed at 1)
  Small Life Drop 0x54 0x8003353C: life += amount                           addiu 0x80033544
Life never goes above max life. Keyed by item id; class data 'heal_divisor' (1/2/4/8/16/32 = all ..
a thirty-second), 'heal_at_least', 'heal_amount'."""
import struct

HEALS = {
    0x24: 'Heals a quarter of max life (at least 5)',
    0x25: 'Heals life to the maximum',
    0x26: 'Restores magic to the maximum',
    0x27: 'Heals life and magic to the maximum',
    0x29: 'Heals half of max life (at least 10)',
    0x50: 'Adds 1 to max magic and fills magic',
    0x51: 'Restores 1 magic',
    0x52: 'Restores magic to the maximum',
    0x53: 'Adds 1 to max life and fills life',
    0x54: 'Heals 2 life',
    0x55: 'Heals a quarter of max life (at least 1)',
    0x56: 'Heals half of max life (at least 5)',
}
# item id: (sra address, stock shift, slti address, li address, stock minimum) or ('amount', address, stock)
SITES = {
    0x24: (0x8003357C, 2, 0x80033580, 0x8003358C, 5),
    0x29: (0x80033830, 1, 0x80033834, 0x80033840, 10),
    0x56: (0x800336BC, 1, 0x800336C0, 0x800336CC, 5),
    0x55: (0x80033618, 2, None, None, 1),
    0x54: ('amount', 0x80033544, 2, 0x2463, 'Heals', 'life'),
    0x53: ('amount', 0x80033ADC, 1, 0x2442, 'Adds', 'to max life (and fills life)'),
    0x51: ('amount', 0x80033CB4, 1, 0x2404, 'Restores', 'magic'),
    0x50: ('amount', 0x80033F28, 1, 0x2404, 'Adds', 'to max magic (and fills magic)'),
}
# 0x53 0x80033ADC addiu v0,v0,1 (max life + 1); 0x51 0x80033CB0 (Magic Elixyr used from the menu runs 0x80033DF0, magic to the maximum: remake items.py use38) (a0 = 1 at
# 0x80033CB4, magic + a0 via 0x8004F59C); 0x50 0x80033F28 (max magic + a0 via 0x8004F4D0).
DIVISORS = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4, 32: 5}


def heal_text(row):
    return HEALS.get(((row or {}).get('source') or {}).get('item_id'), '')


def item_id(row):
    return ((row or {}).get('source') or {}).get('item_id')


def editable(row):
    return item_id(row) in SITES


def current(row):
    """(divisor, at_least) or ('amount', n) for an editable item, the class's values or the game's."""
    site = SITES[item_id(row)]; data = (row or {}).get('data') or {}
    if site[0] == 'amount':
        return ('amount', data.get('heal_amount', site[2]))
    return (data.get('heal_divisor', 1 << site[1]), data.get('heal_at_least', site[4]))


def _word(exe, load, address):
    return struct.unpack_from('<I', exe, address - load + 0x800)[0]


def patch(exe, definitions):
    """Write every item class's changed heal values into the executable (in place)."""
    exe = bytearray(exe); load = struct.unpack_from('<I', exe, 0x18)[0]; report = []
    for row in definitions:
        n = item_id(row)
        if row.get('kind') != 'item' or n not in SITES or row.get('clone_of'):
            continue
        site = SITES[n]; data = row.get('data') or {}
        if site[0] == 'amount':
            amount = data.get('heal_amount')
            if amount is None or amount == site[2]:
                continue
            if type(amount) is not int or not 1 <= amount <= 999:
                raise ValueError(f"{row.get('name')}: heal amount must be 1-999")
            w = _word(exe, load, site[1])
            done = next((r for r in report if r.get('address') == site[1]), None)
            if done is not None:   # a routine shared by two items (Magic Elixyr / Magic Drop)
                if done['amount'] != amount:
                    raise ValueError(f"{row.get('name')}: shares its routine with another item; give both the same amount")
                continue
            if w != (site[3] << 16) | site[2]:
                raise ValueError(f"{row.get('name')}: heal code differs from the stock game")
            struct.pack_into('<I', exe, site[1] - load + 0x800, (site[3] << 16) | amount)
            report.append(dict(item=n, amount=amount, address=site[1])); continue
        sra, shift, slti, li, least = site
        divisor = data.get('heal_divisor'); at_least = data.get('heal_at_least')
        if divisor is not None and divisor != 1 << shift:
            if divisor not in DIVISORS:
                raise ValueError(f"{row.get('name')}: heal part must be 1/1, 1/2, 1/4, 1/8, 1/16 or 1/32")
            w = _word(exe, load, sra)
            if (w & 0xFFE0003F) != 0x00000003 or (w >> 6) & 31 != shift:
                raise ValueError(f"{row.get('name')}: heal code differs from the stock game")
            struct.pack_into('<I', exe, sra - load + 0x800, (w & ~(31 << 6)) | DIVISORS[divisor] << 6)
            report.append(dict(item=n, divisor=divisor))
        if at_least is not None and at_least != least:
            if slti is None:
                raise ValueError(f"{row.get('name')}: its minimum heal is fixed")
            if type(at_least) is not int or not 0 <= at_least <= 999:
                raise ValueError(f"{row.get('name')}: minimum heal must be 0-999")
            a, b = _word(exe, load, slti), _word(exe, load, li)
            if a & 0xFFFF != least or b & 0xFFFF != least or a >> 26 != 10 or b >> 26 != 9:
                raise ValueError(f"{row.get('name')}: heal code differs from the stock game")
            struct.pack_into('<I', exe, slti - load + 0x800, (a & 0xFFFF0000) | at_least)
            struct.pack_into('<I', exe, li - load + 0x800, (b & 0xFFFF0000) | at_least)
            report.append(dict(item=n, at_least=at_least))
    return bytes(exe), report
