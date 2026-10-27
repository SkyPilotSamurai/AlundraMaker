"""Custom accessories: defence, attack and recovery options (user 2026-10-27).

Stock US 1.1 ALUN_CD.EXE / BALANCE.BIN, static:
- Item table 0x800C7DE8, 8 bytes per item id; byte 2 & 0x7F = type. Items 51-56 (Olga's Ring, Oak's
  Ring, Silver Armlet, Nava's Charm, Recovery Ring, Refresher) are type 3; items 31-50 type 0.
- Every frame 0x80030CA4 takes, for the selected item (0x8004F784) when its type is 3, its balance
  record (0x80045508(id): BALANCE.BIN entry 30 + id) as the third damage-table source
  (0x801E9E78, used by 0x80031018..: damage per attack type = armour + (value - 16), 128 = none).
- The accessories' records differ only in data: rings 51/52 one attack (attribute 1, power 3);
  Silver Armlet 15 x 11 damage values; Nava's Charm the same with type 6 = 128; Recovery Ring /
  Refresher 'max HP' byte 200 (the same for both).
A custom accessory (item 31-50) becomes type 3 (EXE byte) and its own balance record takes the chosen
defence values (11) and recovery byte, in place (records keep their size; items 31-50 have no attack
entry, so attack is not offered for them).
Class data 'accessory' = {'defence': [11 x 0-63 or 128], 'recovery': 0-255}."""
import struct

ITEM_TABLE = 0x800C7DE8
USABLE = range(31, 51)


def settings(definitions):
    out = {}
    for row in definitions:
        a = (row.get('data') or {}).get('accessory'); n = (row.get('source') or {}).get('item_id')
        if row.get('kind') != 'item' or row.get('clone_of') or not a:
            continue
        from item_categories import category_for
        if category_for(row) != 'Accessory':
            continue   # only while its category is Accessory (user 2026-10-27)
        if n not in USABLE:
            raise ValueError(f"{row.get('name')}: only items 31-50 can be made accessories")
        d = a.get('defence') or [16] * 11; r = a.get('recovery', 0)
        if len(d) != 11 or any(type(v) is not int or not (0 <= v <= 63 or v == 128) for v in d):
            raise ValueError(f"{row.get('name')}: defence values are 0-63 or 128 (no damage)")
        if type(r) is not int or not 0 <= r <= 255:
            raise ValueError(f"{row.get('name')}: recovery must be 0-255")
        out[n] = dict(defence=list(d), recovery=r)
    return out or None


def patch_exe(exe, chosen):
    exe = bytearray(exe); load = struct.unpack_from('<I', exe, 0x18)[0]
    for n in chosen:
        o = ITEM_TABLE - load + 0x800 + 8 * n + 2
        if exe[o] & 0x7F not in (0, 3): raise ValueError(f'Custom accessory: item {n} type differs from the stock game')
        exe[o] = (exe[o] & 0x80) | 3
    return bytes(exe)


def patch_balance(data, chosen):
    """BALANCE.BIN bytes -> bytes with each item's defence and recovery written in place (build copy)."""
    from enemy_definition import BalanceTable
    data = bytearray(data)
    for n, c in chosen.items():
        offset, raw = BalanceTable(bytes(data)).replacement(30 + n, 0, max_hp=c['recovery'], damage_responses=c['defence'])
        data[offset:offset + len(raw)] = raw
    return bytes(data)
