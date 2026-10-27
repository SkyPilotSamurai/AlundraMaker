"""Bounded BALANCE.BIN records; field meanings are pinned-source reported.

Source: xcasadio/alundra-datas-analyser 242b09a20ae1186c90278ba5f15f0f9a84104ef4,
AlundraTools/AlundraEngine/Balance/{BalanceBin,BalanceRecord,BalanceAttack}.cs.
Edits are GLOBAL definitions, not independent per-entity enemy clones.
"""
import struct
import hashlib
from editor_session import EditSession

BALANCE_SHA256 = '6c3f125fc7a8709e75539df9b62f1cbeeec6bc48e7140c2e6d1575d4c642a9b2'


class BalanceSession(EditSession):
    def __init__(self, data, path=None, verify=True):
        if verify and hashlib.sha256(data).hexdigest() != BALANCE_SHA256:
            raise ValueError('Unknown BALANCE.BIN build')
        BalanceTable(data)
        super().__init__(data, path, verify=False)

    def patch(self):
        result = super().patch()
        result['format'] = 'alundra-balance-patch-v1'
        return result

    def apply_patch(self, patch):
        if patch.get('format') != 'alundra-balance-patch-v1':
            raise ValueError('Expected BALANCE patch')
        translated = dict(patch, format='alundra-datas-patch-v1')
        # Base method validates all preimages and hashes before any mutation.
        super().apply_patch(translated)

    def edit_stats(self, entry, tier=0, **fields):
        offset, replacement = BalanceTable(self.data).replacement(entry, tier, **fields)
        self.replace(offset, replacement, 'Global balance definition')


class BalanceTable:
    def __init__(self, data):
        self.data = bytes(data)
        if len(data) < 2:
            raise ValueError('Truncated balance table')
        first = struct.unpack_from('<h', data)[0]
        if first < 2 or first % 2 or first > len(data):
            raise ValueError('Invalid balance table boundary')
        self.offsets = struct.unpack_from('<' + 'h' * (first // 2), data)
        self.chains = []
        for start in self.offsets:
            chain = []
            offset = start
            while True:
                if offset < first or offset + 15 > len(data):
                    raise ValueError('Balance record outside file')
                level, size = data[offset:offset + 2]
                count = data[offset + 14]
                if size < 15 + 2 * count or offset + size > len(data):
                    raise ValueError('Invalid balance record size')
                chain.append(offset)
                if level == 255:
                    break
                offset += size
            self.chains.append(tuple(chain))

    def entry_for_sprite(self, sprite):
        if not isinstance(sprite, int) or not 0 <= sprite < len(self.offsets):
            raise ValueError('Sprite outside balance table')
        return 0x1e if 0x1f <= sprite <= 0x7f else sprite

    def entry_for_item(self, item):
        if not isinstance(item, int) or not 0 <= item <= 0x61 or item + 0x1e >= len(self.offsets):
            raise ValueError('Item outside balance table')
        return item + 0x1e

    def record(self, entry, tier=0):
        if not isinstance(entry, int) or not 0 <= entry < len(self.chains):
            raise ValueError('Invalid definition entry')
        if not isinstance(tier, int) or not 0 <= tier < len(self.chains[entry]):
            raise ValueError('Invalid tier index')
        offset = self.chains[entry][tier]
        data = self.data
        return dict(offset=offset, level=data[offset], size=data[offset+1],
                    max_hp=data[offset+2], damage_responses=list(data[offset+3:offset+14]),
                    attacks=[dict(attribute=data[offset+15+2*i], power=data[offset+16+2*i])
                             for i in range(data[offset+14])],
                    alias_entries=[i for i, chain in enumerate(self.chains) if offset in chain])

    def selected_tier(self, entry, threshold):
        if not isinstance(threshold, int) or not 0 <= threshold <= 255:
            raise ValueError('Tier threshold must be a byte')
        self.record(entry)
        return next(i for i, offset in enumerate(self.chains[entry]) if self.data[offset] >= threshold)

    def replacement(self, entry, tier=0, *, max_hp=None, damage_responses=None, attacks=None):
        """Return (offset, bytes) for a fixed-size change; keep headers/padding intact.

        Pass to an undoable buffer's replace method. This never allocates a type.
        """
        record = self.record(entry, tier)
        offset = record['offset']
        result = bytearray(self.data[offset:offset+record['size']])
        def byte(value):
            if not isinstance(value, int) or not 0 <= value <= 255:
                raise ValueError('Stat values must be bytes')
            return value
        if max_hp is not None:
            result[2] = byte(max_hp)
        if damage_responses is not None:
            if len(damage_responses) != 11:
                raise ValueError('Exactly 11 damage responses required')
            result[3:14] = bytes(byte(v) for v in damage_responses)
        if attacks is not None:
            if len(attacks) != len(record['attacks']):
                raise ValueError('Cannot resize attack list')
            for i, attack in enumerate(attacks):
                result[15+2*i] = byte(attack['attribute'])
                result[16+2*i] = byte(attack['power'])
        return offset, bytes(result)
