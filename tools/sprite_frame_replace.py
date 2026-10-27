"""Replace frame pictures (image sets) of a sprite with new art.

Works on both sprite banks:
* global (classes 0-255, start of DATAS): 8 texture pages, EZ-compressed into a
  fixed room (sheet .. end); the new texture must fit that room;
* map-local (classes 256-511 on one map): the map's sprite section (3) and
  texture section (4, up to 5 pages); the texture section may grow and a blank
  page may be added when the existing pages are full.

An image set is a list of 14-byte quads (page, palette, sx, sy, w, h, 8 signed
corner bytes). New art is written into texels that only the replaced pictures
used, plus large blank (0) areas no quad covers (2-texel margin), each piece
keeping one transparent texel right of and below it (the GPU samples one
texel past a quad's far edge). A picture is cut into horizontal strips when
needed but never uses more quads than the image set already has, so record
sizes never change. Quads the caller keeps (e.g. a sword drawn with its own
palette) stay first and unchanged.

Colours: each picture is matched to a 15-colour palette (index 0 transparent):
by default the palette its first replaced quad already uses (edited sheets
keep the game's colours), or a palette slot + 16 colour words the caller
writes. Identical and left/right mirrored pictures share pixels.
Nothing here is verified in game; the costume code uses the same rules.
"""
import struct
from collections import defaultdict


def rgb_of(word):
    return ((word & 31) << 3, ((word >> 5) & 31) << 3, ((word >> 10) & 31) << 3)


def word_of(rgb):
    r, g, b = rgb[:3]
    return ((r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)) or 0x0421


class Bank:
    """One sprite bank (global or one map's local bank) with its decoded texture."""
    def __init__(self, data, map_id=None):
        from texture_codec import unpack_ez
        self.map_id = map_id
        if map_id is None:
            self.kind = 'global'
            self.start, sheet = struct.unpack_from('<2I', data)
            end = struct.unpack_from('<I', data, 0x14)[0]
            self.bound = sheet
            self.header = struct.unpack_from('<12I', data, self.start)
            self.texture_at, self.room = sheet, end - sheet
            self.raw = bytearray(unpack_ez(bytes(data[sheet:end]), limit=262144)[0])
            self.effects = False
            self.max_pages = 8
        else:
            from local_sprite_import import layout
            self.kind = 'local'
            b, h, s, e, sh = layout(data, map_id)
            self.start, self.bound, self.header = s, e, sh
            self.texture_at, self.room = b + h[4], h[5] - h[4]
            self.raw = bytearray(unpack_ez(bytes(data[b + h[4]:b + h[5]]), limit=262144)[0])
            self.effects = False
            for at in range(s + sh[4], s + sh[5], 4):
                value = struct.unpack_from('<i', data, at)[0]
                if value == 0:
                    break
                if value != -1:
                    self.effects = True
            self.max_pages = 5
        self.raw.extend(bytes((-len(self.raw)) % 32768))

    @property
    def pages(self):
        return len(self.raw) // 32768

    def sprites(self, data):
        table, stop = self.header[3:5]
        for idx in range((stop - table) // 4):
            ptr = struct.unpack_from('<i', data, self.start + table + idx * 4)[0]
            if ptr > 0:
                yield idx, ptr

    def frames_base(self, data, idx):
        table = self.header[3]
        ptr = struct.unpack_from('<i', data, self.start + table + idx * 4)[0]
        if ptr <= 0:
            raise ValueError('This class has no sprite in this bank')
        return self.start + struct.unpack_from('<4I', data, self.start + ptr)[3]

    def image_sets(self, data, idx):
        from entity_animation import parse_sprite_animation_record
        sets = parse_sprite_animation_record(data, self.start, self.bound, idx, *self.header[3:5])
        return {0} | {f.image_set_index for a in sets for st in a.streams if st for f in st.frames}

    def quad_users(self, data):
        """{(page, sx, sy, w, h): {(sprite, image set, quad)}} for every drawn quad."""
        users = defaultdict(set)
        for idx, _ in self.sprites(data):
            try:
                base = self.frames_base(data, idx); isets = self.image_sets(data, idx)
            except Exception:
                continue
            for i in isets:
                pos = base + i * 2
                if pos + 2 > len(data):
                    continue
                for q in range(data[pos + 1]):
                    page, pal, sx, sy, w, h = struct.unpack_from('<6B', data, pos + 2 + q * 14)
                    if w and h:
                        users[(page & 7, sx, sy, w, h)].add((idx, i, q))
        return users

    def palette_words(self, data, slot):
        at = self.start + self.header[5] + slot * 32
        if at + 32 > self.start + self.header[6]:
            raise ValueError(f'Palette slot {slot} is outside this bank')
        return list(struct.unpack_from('<16H', data, at))

    def write(self, data):
        """data with this bank's texture packed back (and the palette/quad edits already in data)."""
        from texture_codec import pack_ez, pack_ez_fit, unpack_ez
        header = bytes(data[self.texture_at:self.texture_at + 6])
        raw = bytes(self.raw)
        if self.kind == 'global':
            packed = pack_ez_fit(raw, header, self.room)
            if len(packed) > self.room:
                raise ValueError(f'New sprite art needs {len(packed)} texture bytes; the global sheet has {self.room}')
            if unpack_ez(packed, limit=262144)[0] != raw:
                raise ValueError('Texture round-trip failed')
            out = bytearray(data)
            out[self.texture_at:self.texture_at + self.room] = packed + bytes(self.room - len(packed))
            return out
        from map_block_repack import replace_section
        from map_loader_constraints import validate_layout
        while len(raw) > 32768 and not any(raw[-32768:]) and len(raw) // 32768 > self._original_pages:
            raw = raw[:-32768]
        packed = pack_ez(raw, header); packed += bytes((-len(packed)) % 4)
        result = replace_section(bytes(data), self.map_id, 4, packed)
        validate_layout(result)
        return bytearray(result)


def _quantizer(words):
    from PIL import Image
    pal = []
    for w in words[1:16]:
        pal += list(rgb_of(w))
    image = Image.new('P', (1, 1)); image.putpalette(pal + pal[-3:] * (256 - 15))
    return image


def indexed(image, words):
    """RGBA -> bytes of palette indexes 0-15 (alpha < 128 -> 0)."""
    from PIL import Image
    rgb = Image.new('RGB', image.size); rgb.paste(image.convert('RGB'), mask=image.split()[3])
    q = rgb.quantize(palette=_quantizer(words), dither=Image.Dither.NONE)
    px = bytearray(q.tobytes()); alpha = image.split()[3].tobytes()
    for i, a in enumerate(alpha):
        px[i] = 0 if a < 128 else min(14, px[i]) + 1
    return bytes(px)


def replace_image_sets(data, catalogue, replacements, map_id=None, palette=None, keep_quads=None, keep_indexes=None, dry_run=False, users=None, first=()):
    """See _replace_once. A picture that does not fit keeps its old quads, so its
    old texels must not be reused: the pass is repeated without such pictures
    until everything left fits."""
    replacements = dict(replacements); left_out = []
    if users is None:
        users = Bank(data, map_id).quad_users(data)
    while True:
        out, report = _replace_once(data, catalogue, replacements, map_id, palette, keep_quads, keep_indexes,
                                    dry_run=True, users=users, first=first)
        if not report['kept']:
            break
        left_out += report['kept']
        for iset in report['kept']:
            replacements.pop(iset, None)
        if not replacements:
            break
    out, report = _replace_once(data, catalogue, replacements, map_id, palette, keep_quads, keep_indexes,
                                dry_run=dry_run, users=users, first=first)
    report['kept'] = sorted(set(report['kept']) | set(left_out))
    return out, report


def _replace_once(data, catalogue, replacements, map_id=None, palette=None, keep_quads=None, keep_indexes=None, dry_run=False, users=None, first=()):
    """Write new pictures for image sets of one class.

    replacements: {image set: (RGBA image, left, top)}; left/top place the
    picture's top-left corner relative to the sprite origin (as the frames of
    animation_preview.load_animation report them).
    palette: None (use each picture's current palette), (slot, 16 words) written to
    that slot, or ('keep', 16 words): colours matched to these words while each
    picture keeps its own palette slot (e.g. damage-flash palettes).
    keep_quads: optional function(quad tuple) -> True to keep that quad as it is;
    keep_indexes: optional {image set: [quad numbers to keep]}.
    dry_run: place only (report what fits), data unchanged.
    users: a Bank.quad_users result to reuse (same data).
    first: image sets placed before the others (default: largest first only).
    Returns (new data, report)."""
    from PIL import ImageOps
    from player_costume import _Packer, _add_blank_space
    data = bytearray(data)
    if map_id is None and not 0 <= catalogue < 256:
        raise ValueError('Global sprites are classes 0-255')
    if map_id is not None and not 256 <= catalogue < 512:
        raise ValueError('Map-local sprites are classes 256-511')
    bank = Bank(data, map_id); bank._original_pages = bank.pages
    idx = catalogue & 255
    base = bank.frames_base(data, idx)
    users = bank.quad_users(data) if users is None else users
    keep = {}
    for iset in replacements:
        pos = base + iset * 2; count = data[pos + 1]
        quads = [struct.unpack_from('<6B8b', data, pos + 2 + q * 14) for q in range(count)]
        keep[iset] = [q for q in range(count) if (keep_quads and keep_quads(quads[q]))
                      or q in (keep_indexes or {}).get(iset, ())]
    replaced = {(idx, i, q) for i in replacements for q in range(data[base + i * 2 + 1]) if q not in keep[i]}
    pages = max(bank.pages, 1)
    free = [bytearray(65536) for _ in range(8)]; blocked = [bytearray(65536) for _ in range(8)]
    for (page, sx, sy, w, h), who in users.items():
        target = free if who <= replaced else blocked
        for y in range(sy, min(256, sy + h)):
            span = min(256, sx + w) - sx
            target[page][y * 256 + sx: y * 256 + sx + span] = b'\x01' * span
    for page in range(8):
        f, b = free[page], blocked[page]
        for i in range(65536):
            if b[i]:
                f[i] = 0
        if page >= pages:
            free[page] = bytearray(65536)
    if not bank.effects:
        raw8 = bytes(bank.raw) + bytes(8 * 32768 - len(bank.raw))
        _add_blank_space(raw8, free, blocked, margin=2)
        for page in range(pages, 8):
            free[page] = bytearray(65536)

    def clear_map():
        raw = bank.raw
        out = []
        for p in range(8):
            if p >= bank.pages:
                out.append(bytearray(65536)); continue
            row = bytearray(65536)
            chunk = raw[p * 32768:(p + 1) * 32768]
            for i in range(65536):
                if not free[p][i] and not (chunk[(i // 256) * 128 + (i % 256) // 2] >> (4 * (i % 2))) & 15:
                    row[i] = 1
            out.append(row)
        return out
    packer = _Packer(free, clear_map())
    free_texels = sum(f.count(1) for f in free)
    report = dict(bank=bank.kind, map_id=map_id, catalogue_index=catalogue, replaced=[], kept=[], strips=0)
    shared = {}   # (size, pixels, palette) -> (pieces, flipped)

    def palette_for(iset):
        if palette is not None and palette[0] != 'keep':
            return palette
        pos = base + iset * 2; count = data[pos + 1]
        q = next((q for q in range(count) if q not in keep[iset]), None)
        slot = data[pos + 2 + q * 14 + 1] if q is not None else 0
        if palette is not None:          # ('keep', words): match these colours, keep the quad's slot
            return slot, palette[1]
        return slot, bank.palette_words(data, slot)

    def trimmed(item):
        image, left, top = item
        image = image.convert('RGBA'); box = image.getbbox()
        if box is None:
            return image.crop((0, 0, 1, 1)), left, top
        return image.crop(box), left + box[0], top + box[1]
    items = {i: trimmed(v) for i, v in replacements.items()}
    first = set(first)   # optional: pictures placed before the rest (e.g. ones with a single quad)
    order = sorted(items, key=lambda i: (i not in first, -(items[i][0].width * items[i][0].height), i))
    for iset in order:
        image, left, top = items[iset]
        pos = base + iset * 2; count = data[pos + 1]
        room = count - len(keep[iset])
        slot, words = palette_for(iset)
        w, h = image.size
        pixels = indexed(image, words)
        key = (image.size, pixels, slot)
        mirror_key = (image.size, indexed(ImageOps.mirror(image), words), slot)
        pieces = flipped = None
        if key in shared:
            pieces, flipped = shared[key]
        elif mirror_key in shared:
            pieces, flipped = shared[mirror_key][0], not shared[mirror_key][1]
        if pieces is None and room > 0:
            def strips(parts):
                """Horizontal strips, each trimmed to its own non-empty columns."""
                strip = -(-h // parts); out = []
                for p in range(parts):
                    sy0 = p * strip; sh = min(strip, h - sy0)
                    if sh <= 0:
                        break
                    cols = [x for x in range(w) if any(pixels[(sy0 + yy) * w + x] for yy in range(sh))]
                    if not cols:
                        continue
                    rows_used = [yy for yy in range(sh) if any(pixels[(sy0 + yy) * w + x] for x in range(cols[0], cols[-1] + 1))]
                    out.append((sy0 + rows_used[0], rows_used[-1] - rows_used[0] + 1, cols[0], cols[-1] - cols[0] + 1))
                return out

            def attempt():
                # most strips first: tighter pieces use fewer texels
                for parts in range(room, 0, -1):
                    trial = []; ok = True
                    for sy0, sh, x0, sw in strips(parts):
                        spot = packer.place(sw, sh)
                        if spot is None:
                            ok = False; break
                        trial.append((spot[0], spot[1], spot[2], sw, sh, sy0, spot[3], x0))
                    if ok and trial:
                        return trial
                    for page, px, py, pw, ph, _, border, _ in trial:
                        packer.release(page, px, py, pw, ph, border)
                return None
            trial = attempt()
            if trial is None and bank.kind == 'local' and bank.pages < bank.max_pages:
                new = bank.pages; bank.raw.extend(bytes(32768))
                packer.free[new][:] = b'\x01' * 65536
                for y in range(256):          # keep the far edge as the border column/row
                    packer.free[new][y * 256 + 255] = 0
                packer.free[new][255 * 256:] = bytes(256)
                packer.clear[new][:] = b'\x01' * 65536
                trial = attempt()
            if trial is not None:
                for page, px, py, pw, ph, sy, border, x0 in trial:
                    for i in border:
                        o = page * 32768 + (i // 256) * 128 + (i % 256) // 2
                        bank.raw[o] = bank.raw[o] & 0xF0 if (i % 256) % 2 == 0 else bank.raw[o] & 0x0F
                    for yy in range(ph):
                        for xx in range(pw):
                            v = pixels[(sy + yy) * w + x0 + xx]
                            o = page * 32768 + (py + yy) * 128 + (px + xx) // 2
                            bank.raw[o] = (bank.raw[o] & 0xF0) | v if (px + xx) % 2 == 0 else (bank.raw[o] & 0x0F) | (v << 4)
                pieces = [t[:6] + (t[7],) for t in trial]; flipped = False
                shared[key] = (pieces, flipped)
        if pieces is None or len(pieces) > room or not (-128 <= left and left + w <= 127 and -128 <= top and top + h <= 127):
            report['kept'].append(iset); continue
        kept_rows = [bytes(data[pos + 2 + q * 14: pos + 16 + q * 14]) for q in keep[iset]]
        first_page_byte = data[pos + 2 + next(q for q in range(count) if q not in keep[iset]) * 14]
        rows = []
        for page, px, py, pw, ph, sy, x0 in pieces:
            # a mirrored picture uses the same pieces at mirrored columns
            x1, y1 = left + (w - x0 - pw if flipped else x0), top + sy
            if flipped:
                rows.append(struct.pack('<6B8b', (first_page_byte & ~7) | page, slot, max(0, px - 1), py, pw, ph,
                                        x1 + pw, y1, x1, y1, x1 + pw, y1 + ph, x1, y1 + ph))
            else:
                rows.append(struct.pack('<6B8b', (first_page_byte & ~7) | page, slot, px, py, pw, ph,
                                        x1, y1, x1 + pw, y1, x1, y1 + ph, x1 + pw, y1 + ph))
        rows = kept_rows + rows
        rows += [bytes(14)] * (count - len(rows))
        data[pos + 2: pos + 2 + count * 14] = b''.join(rows)
        report['replaced'].append(iset); report['strips'] += len(pieces)
    if dry_run:
        report['free_texels'] = free_texels
        return bytes(data), report
    from player_costume import _clear_unused
    _clear_unused(bank.raw, packer.free)
    if palette is not None and palette[0] != 'keep':
        slot, words = palette
        at = bank.start + bank.header[5] + slot * 32
        if at + 32 > bank.start + bank.header[6]:
            raise ValueError(f'Palette slot {slot} is outside this bank')
        data[at:at + 32] = struct.pack('<16H', *words)
    data = bank.write(data)
    report['texture_pages'] = bank.pages
    report['free_texels'] = free_texels
    report['needed_texels'] = sum(items[i][0].width * items[i][0].height for i in items)
    report['gameplay_verified'] = False
    return data, report
