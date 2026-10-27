"""Hue / saturation for global-bank classes (user 2026-10-27: spawned magic).

The global sprite bank is at the start of DATAS.BIN (u32 0 = sprite info, u32 4 = sheets, u32 0x14 =
end; entity_preview.cached_preview). Its palette table (info + header[5], 32 bytes each) is shared by
every map, so a recoloured palette changes that class everywhere it appears - and every other
global sprite that uses the same palette (reported). Palettes a sprite uses are read from every
frame the editor's decoder draws (EntityPreview.fullest_frame over 8 facings)."""
import struct
from entity_preview import EntityPreview
from types import SimpleNamespace
from local_sprite_recolor import shift_hue


class _Recorder(EntityPreview):
    def compose_images(self, pos, count):
        for i in range(count):
            self.used.add(self.read('6B8b', pos + 2 + i * 14)[1])
        return super().compose_images(pos, count)


def _bank(data):
    start, sheet = struct.unpack_from('<2I', data); end = struct.unpack_from('<I', data, 0x14)[0]
    if not 0 <= start < sheet < end <= len(data): raise ValueError('Global sprite bank bounds invalid')
    view = SimpleNamespace(data=data, layout=lambda ignored: (0, (0, 0, 0, start, sheet, end, 0)))
    return _Recorder(view, 0)


def palettes_of(data, sprite):
    bank = _bank(data); bank.used = set()
    for d in range(8): bank.fullest_frame(sprite, d)
    return bank.used


def sprite_count(data):
    b = _bank(data); table, stop = b.header[3:5]; return (stop - table) // 4


def recolor(data, wanted):
    """wanted {global sprite index: (hue degrees, saturation %)} -> (new DATAS, report)."""
    data = bytearray(data); bank = _bank(data); report = []
    base = bank.start + bank.header[5]; count = (bank.header[6] - bank.header[5]) // 32
    owners = {}
    for sprite, (hue, sat) in sorted(wanted.items()):
        if (hue, sat) == (0, 100): continue
        used = palettes_of(data, sprite)
        if not used: raise ValueError(f'Global class {sprite}: no palette found to recolour')
        for p in sorted(used):
            if p >= count: raise ValueError(f'Global class {sprite}: palette {p} outside the table')
            owners[p] = (hue, sat, sprite)   # shared with another recoloured class: the later class's colour (user 2026-10-27)
    for p, (hue, sat, sprite) in sorted(owners.items()):
        o = base + 32 * p
        words = struct.unpack_from('<16H', data, o)
        struct.pack_into('<16H', data, o, *shift_hue(list(words), hue, sat))
        report.append(dict(sprite=sprite, palette=p, hue=hue, saturation=sat))
    return bytes(data), report


def sharers(data, sprite):
    """Other global sprites that use any palette of this one (they change colour with it)."""
    mine = palettes_of(data, sprite); out = []
    for i in range(sprite_count(data)):
        if i != sprite:
            try:
                if palettes_of(data, i) & mine: out.append(i)
            except Exception: pass
    return out
