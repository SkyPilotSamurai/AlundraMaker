"""Mod option "Start as Meia": Alundra stays the real player (warps, jump, HUD,
damage, items and saves are unchanged) but looks like Meia while he walks and jumps;
every other animation keeps his own frames.

How (build time, global sprite bank at the start of DATAS):
* Every image set (frame picture) of global class 0 that only walking/jumping
  animations (COSTUME_ANIMATIONS) use is redrawn as a Meia pose: Meia (map-local class 400 on map 51,
  the dream-scene Meia that has jump frames) animation chosen by MEIA_FOR, same
  direction slot, frame k -> Meia frame k mod its frame count.
* Meia's pixels go into texture-page pixels that only those costume image sets
  use (Alundra's own non-attack art, which no longer shows), never pixels any
  other sprite or attack frame uses. A frame that does not fit as one piece is
  cut into horizontal strips, up to the image set's quad count.
* Colours: all Meia frames share one 15-colour palette written to global palette
  slot PALETTE_SLOT (no sprite quad uses it in the stock data).
* The image set keeps its quad count; unused quads become empty. Animation
  streams, frame delays and collision boxes are unchanged (Alundra's).
* The global texture sheet is recompressed into its existing room.
Not verified in game. Image sets shared with attack animations keep Alundra.
"""
import struct
from collections import defaultdict

MEIA_CLASS, MEIA_MAP = 400, 51
# Alundra's own palettes whose blue clothing tones turn to Meia's lavender, so the
# frames that stay Alundra's (standing, running, attacks, ...) wear her colours.
# 12/17/18 are also used by charged arrows and the wave sword effects (their blue
# tints turn lavender too); ice magic uses other palettes and keeps its blue.
RECOLOR_PALETTES = (12, 17, 18)
# Hair and shoes: palette 17 holds Alundra's hair ramp (4-7, dark brown to
# yellow) and his shoe/belt tans (8-10), found by where those colours sit in his
# frames. They take the matching shades of Meia's own sprite (class 400): her
# softer blonde hair and brown shoes. Palette 17 is also used by charged arrows
# and the wave sword effects, whose gold shades follow.
# 8-10 are his skin tones (face, arms), so they stay; his shoes share the hair
# ramp 4-7 and follow it.
MEIA_COLOURS = {(17, 4): (57, 41, 16), (17, 5): (123, 90, 0), (17, 6): (213, 180, 41), (17, 7): (240, 230, 160)}


def rgb555(rgb, keep=0):
    r, g, b = rgb
    return (keep & 0x8000) | (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10) or 0x0421


# Meia's dress shades, darkest to lightest, sampled from her walking frames
# (class 400): Alundra's blue tunic shades map onto them by brightness.
MEIA_DRESS = ((32, 24, 57), (98, 57, 98), (139, 98, 131), (196, 172, 196))


def meia_tones(word):
    """Blue (hue 190-265 deg, some saturation, not the near-black outline) ->
    the Meia dress shade of similar brightness; other colours unchanged."""
    import colorsys
    if not word & 0x7FFF:
        return word
    r, g, b = (word & 31) / 31, ((word >> 5) & 31) / 31, ((word >> 10) & 31) / 31
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if not (190 <= h * 360 <= 265 and s >= 0.25 and v >= 0.15):
        return word
    shade = MEIA_DRESS[0 if v < 0.3 else 1 if v < 0.5 else 2 if v < 0.7 else 3]
    return rgb555(shade, word)


PALETTE_SLOT = 11
# Only standing, walking and jumping become Meia (user, 2026-10-08); every other
# player animation (running, swimming, climbing, attacks, hurt, ...) keeps Alundra.
# Meia's animations as the Elene dream controller (map 51, root B2) plays them:
# on the ground 00 standing / 09 moving; jump start 10 still / 12 moving; in the
# air 11 still / 13 moving.
IDLE, WALK, RUN = 0x00, 0x09, 0x09
JUMP_START, JUMP_START_MOVING, JUMP_AIR, JUMP_AIR_MOVING = 0x10, 0x12, 0x11, 0x13
JUMP_POSE, JUMP_MOVE = JUMP_START, JUMP_AIR_MOVING   # older names
MEIA_FOR = {0x00: IDLE, 0x36: IDLE,          # Idle (standing), LoadingMap (same frames)
            0x01: WALK,                      # Moving
            0x2B: JUMP_START,                # start jump (standing)
            0x02: JUMP_START_MOVING,         # start jump while moving
            0x2D: JUMP_AIR,                  # jump (standing)
            0x2C: JUMP_AIR_MOVING}           # jump moving
COSTUME_ANIMATIONS = frozenset(MEIA_FOR)
KEEP_ALUNDRA = frozenset(range(0x100)) - COSTUME_ANIMATIONS


# Moves shown with Meia's walk when "Meia basic attack" is on without "Alundra for
# missing actions" (sprint, dash, climbing, swimming, sand, mine cart moving).
MOVING = frozenset((0x03, 0x04, 0x0E, 0x0F, 0x1B, 0x23, 0x24, 0x28, 0x29, 0x37, 0x3E))


def meia_animation(player_animation):
    return MEIA_FOR.get(player_animation, WALK if player_animation in MOVING else IDLE)


def _global_bank(data):
    start, sheet = struct.unpack_from('<2I', data)
    end = struct.unpack_from('<I', data, 0x14)[0]
    header = struct.unpack_from('<12I', data, start)
    return start, sheet, end, header


def _player_image_sets(data):
    """{image set: {(animation, direction, frame)}} for class 0, plus quad users of every global sprite."""
    from entity_animation import parse_sprite_animation_record
    start, sheet, end, header = _global_bank(data)
    table, stop = header[3:5]
    uses = defaultdict(set); quads = defaultdict(set); frames_of = {}
    for idx in range((stop - table) // 4):
        ptr = struct.unpack_from('<i', data, start + table + idx * 4)[0]
        if ptr <= 0:
            continue
        try:
            sets = parse_sprite_animation_record(data, start, sheet, idx, table, stop)
        except Exception:
            continue
        frames = struct.unpack_from('<4I', data, start + ptr)[3]
        frames_of[idx] = start + frames
        for a in sets:
            for direction, st in enumerate(a.streams):
                if not st:
                    continue
                for k, f in enumerate(st.frames):
                    if idx == 0:
                        uses[f.image_set_index].add((a.index, direction, k))
                    pos = start + frames + f.image_set_index * 2
                    count = data[pos + 1]
                    for q in range(count):
                        page, pal, sx, sy, w, h = struct.unpack_from('<6B', data, pos + 2 + q * 14)
                        if w and h:
                            quads[(page & 7, sx, sy, w, h)].add((idx, f.image_set_index))
    return uses, quads, frames_of[0]


def _meia_frames(session, wanted):
    """{(anim, dir, k): (RGBA image, left, top)} for the Meia poses needed."""
    from animation_preview import load_animation
    out = {}; clips = {}
    for anim, direction, k, n in wanted:
        key = (anim, direction)
        if key not in clips:
            # Meia's pictures come from the original game's map 51, whatever the project did to it
            from stock_donors import source_for
            clips[key] = load_animation(source_for(session, MEIA_MAP), MEIA_MAP, MEIA_CLASS, anim, direction)
        clip = clips[key]
        usable = [f for f in clip.frames if f.image is not None]
        # Same point in the cycle: Alundra's frame k of n -> Meia's frame k*m/n
        # (e.g. his 6-frame walk plays her 4 steps in order, not 0,1,2,3,0,1).
        f = usable[min(len(usable) - 1, k * len(usable) // max(1, n))]
        out[(anim, direction, k, n)] = (f.image.convert('RGBA'), f.left, f.top, f.image_set_index)
    return out


def _add_blank_space(raw, free, covered, margin=4):
    from entity_preview import indexed_sprite_page
    for page in range(8):
        px = indexed_sprite_page(raw, page).tobytes()
        blank = bytearray(1 if (px[i] == 0 and not covered[page][i] and not free[page][i]) else 0 for i in range(65536))
        # erode by `margin` in both directions (row runs, then column runs)
        rows = bytearray(65536)
        for y in range(256):
            run = 0
            line = blank[y * 256:(y + 1) * 256]
            ok = bytearray(256)
            for x in range(256):
                run = run + 1 if line[x] else 0
                if run > 2 * margin:
                    ok[x - margin] = 1
            rows[y * 256:(y + 1) * 256] = ok
        for x in range(256):
            run = 0
            for y in range(256):
                run = run + 1 if rows[y * 256 + x] else 0
                if run > 2 * margin:
                    free[page][(y - margin) * 256 + x] = 1


def _meia_portrait(session):
    """Meia's dialogue portrait (class 302 on map 8), the same 48x56 size as the menu portrait."""
    from entity_preview import cached_preview
    try:
        from stock_donors import source_for
        found = cached_preview(source_for(session, 8), 8).portrait(302 & 255)
    except Exception:
        return None
    return None if found is None else found[0].convert('RGBA')


def _clear_unused(raw, free):
    """Writable texels nothing uses any more -> 0 (smaller texture, and blank
    space a later pass can use)."""
    for page in range(min(8, len(raw) // 32768)):
        mask = free[page]
        if not mask.count(1):
            continue
        base = page * 32768
        for i in range(65536):
            if mask[i]:
                o = base + (i // 256) * 128 + (i % 256) // 2
                raw[o] = raw[o] & 0xF0 if i % 2 == 0 else raw[o] & 0x0F


class _Packer:
    """First-fit placement in writable texels (free). A piece also needs one
    transparent texel to its right and below (the GPU can sample one texel past
    a quad's far edge): those may be writable texels (cleared to 0) or texels
    that are already 0 in other art (clear), which are only read."""
    def __init__(self, free, clear=None):
        self.free = free
        self.clear = clear or [bytearray(65536) for _ in range(8)]

    def _fits(self, page, x, y, w, h):
        m = self.free[page]
        for yy in range(y, y + h):
            if m[yy * 256 + x: yy * 256 + x + w].count(1) != w:
                return False
        return True

    def _border(self, page, x, y, w, h):
        """Writable border texels, or None when the border is not transparent."""
        if x + w >= 256 or y + h >= 256:
            return None
        m, c = self.free[page], self.clear[page]; out = []
        for i in [(y + yy) * 256 + x + w for yy in range(h + 1)] + [(y + h) * 256 + x + xx for xx in range(w)]:
            if m[i]:
                out.append(i)
            elif not c[i]:
                return None
        return out

    def place(self, w, h):
        """(page, x, y, writable border indexes) or None."""
        for page in range(8):
            m = self.free[page]
            for y in range(0, 256 - h):
                row = m[y * 256: y * 256 + 256]
                x = row.find(b'\x01' * w)
                while x != -1:
                    if self._fits(page, x, y, w, h):
                        border = self._border(page, x, y, w, h)
                        if border is not None:
                            for yy in range(y, y + h):
                                m[yy * 256 + x: yy * 256 + x + w] = bytes(w)
                            for i in border:
                                m[i] = 0
                            return page, x, y, border
                    x = row.find(b'\x01' * w, x + 1)
        return None

    def release(self, page, x, y, w, h, border):
        m = self.free[page]
        for yy in range(y, y + h):
            m[yy * 256 + x: yy * 256 + x + w] = b'\x01' * w
        for i in border:
            m[i] = 1


def apply_costume(session, basic_attack=False, alundra_fallback=False):
    """Edit session.data in place (one undo group when available). Returns a report."""
    from PIL import Image
    from texture_codec import unpack_ez, pack_ez_fit
    data = session.data
    start, sheet, end, header = _global_bank(data)
    uses, quads, frames_base = _player_image_sets(data)
    # Meia basic attack: attacks, carrying and damage get built Meia frames
    # (meia_actions). Without "Alundra for missing actions" every other move
    # shows Meia standing or walking, so Alundra never appears.
    if basic_attack and not alundra_fallback:
        from meia_actions import ACTION_ANIMATIONS
        dressed = frozenset(range(0x100)) - ACTION_ANIMATIONS
    else:
        dressed = COSTUME_ANIMATIONS
    original = bytes(data)
    costume = {i: sorted(u) for i, u in uses.items() if {a for a, _, _ in u} <= dressed}
    # Pixels only costume image sets use may be overwritten.
    free = [bytearray(65536) for _ in range(8)]; blocked = [bytearray(65536) for _ in range(8)]
    for (page, sx, sy, w, h), users in quads.items():
        mine = all(c == 0 and i in costume for c, i in users)
        target = free if mine else blocked
        for y in range(sy, min(256, sy + h)):
            span = min(256, sx + w) - sx
            target[page][y * 256 + sx: y * 256 + sx + span] = b'\x01' * span
    for page in range(8):
        f, b = free[page], blocked[page]
        for i in range(65536):
            if b[i]:
                f[i] = 0
    # Also large blank areas: pixels that are 0, used by no sprite quad, with a
    # 2-pixel blank margin all round (keeps clear of art the code draws itself).
    raw0, _ = unpack_ez(bytes(data[sheet:end]), limit=262144)
    # The pause-menu portrait (image set 0 of class 0, no animation uses it):
    # its pixels are kept out of the packer and replaced by Meia's portrait.
    portrait_pos = frames_base
    p_page, _, p_sx, p_sy, p_w, p_h = struct.unpack_from('<6B', data, portrait_pos + 2)
    p_page &= 7
    for y in range(p_sy, min(256, p_sy + p_h)):
        blocked[p_page][y * 256 + p_sx: y * 256 + min(256, p_sx + p_w)] = b'\x01' * (min(256, p_sx + p_w) - p_sx)
        free[p_page][y * 256 + p_sx: y * 256 + min(256, p_sx + p_w)] = bytes(min(256, p_sx + p_w) - p_sx)
    _add_blank_space(raw0, free, blocked, margin=2)
    # Which Meia pose each costume image set shows (its first use decides).
    choice = {}
    lengths = {}
    for u in uses.values():
        for a, dr, k in u:
            lengths[(a, dr)] = max(lengths.get((a, dr), 0), k + 1)
    for iset, u in costume.items():
        anim, direction, k = u[0]
        choice[iset] = (meia_animation(anim), direction, k, lengths[(anim, direction)])
    poses = _meia_frames(session, set(choice.values()))
    # One shared 15-colour palette (+ transparent index 0).
    portrait = _meia_portrait(session)
    images = list({id(v[0]): v[0] for v in poses.values()}.values()) + ([portrait] if portrait is not None else [])
    atlas = Image.new('RGBA', (sum(im.width for im in images), max(im.height for im in images)))
    x = 0
    for im in images:
        atlas.paste(im, (x, 0)); x += im.width
    opaque = Image.new('RGB', atlas.size)
    opaque.paste(atlas.convert('RGB'), mask=atlas.split()[3])
    quant = opaque.quantize(colors=15, method=Image.Quantize.MEDIANCUT)
    pal = quant.getpalette()[:45]
    words = [0] + [0x8000 * 0 | (pal[i * 3] >> 3) | ((pal[i * 3 + 1] >> 3) << 5) | ((pal[i * 3 + 2] >> 3) << 10) or 0x0421
                   for i in range(15)]
    palette_at = start + header[5] + PALETTE_SLOT * 32
    if palette_at + 32 > start + header[6]:
        raise ValueError('Global palette table has no slot 11')

    def indexed(im):
        rgb = Image.new('RGB', im.size); rgb.paste(im.convert('RGB'), mask=im.split()[3])
        q = rgb.quantize(palette=quant, dither=Image.Dither.NONE)
        alpha = im.split()[3].tobytes(); px = bytearray(q.tobytes())
        for i, a in enumerate(alpha):
            px[i] = 0 if a < 128 else px[i] + 1
        return bytes(px)

    raw = bytearray(raw0)
    clear = [bytearray(1 if (not free[p][i] and not (raw0[p * 32768 + (i // 256) * 128 + (i % 256) // 2] >> (4 * (i % 2))) & 15) else 0
                       for i in range(65536)) for p in range(8)]
    for y in range(p_sy, min(256, p_sy + p_h)):   # the portrait gets new pixels
        clear[p_page][y * 256 + p_sx: y * 256 + min(256, p_sx + p_w)] = bytes(min(256, p_sx + p_w) - p_sx)
    packer = _Packer(free, clear)
    placed = {}   # Meia image set -> (pieces [(page, x, y, w, h, strip_top)], left, top, flipped)
    mirrors = {}  # (size, pixels) -> Meia image set placed with those pixels
    out = bytearray(data)
    report = dict(costume_image_sets=len(costume), meia_frames=len(poses), strips=0, kept_alundra=[])
    # Trim transparent borders, then place the largest Meia poses first.
    for key, (image, left, top, meia_set) in list(poses.items()):
        box = image.getbbox()
        if box and box != (0, 0, image.width, image.height):
            poses[key] = (image.crop(box), left + box[0], top + box[1], meia_set)
    def area(iset):
        im = poses[choice[iset]][0]
        return -(im.width * im.height)
    for iset in sorted(costume, key=lambda i: (area(i), i)):
        pos = frames_base + iset * 2
        count = data[pos + 1]
        image, left, top, meia_set = poses[choice[iset]]
        if meia_set not in placed:
            # Left/right mirror pairs share pixels: draw the mirror with flipped quads.
            from PIL import ImageOps
            same = mirrors.get((image.size, image.tobytes()))
            mirror = mirrors.get((image.size, ImageOps.mirror(image).tobytes()))
            if same is not None:                 # identical picture already placed
                placed[meia_set] = (placed[same][0], left, top, placed[same][3])
            elif mirror is not None:
                placed[meia_set] = (placed[mirror][0], left, top, not placed[mirror][3])
        if meia_set not in placed:
            pixels = indexed(image); w, h = image.size
            pieces = None
            for parts in range(1, count + 1):
                strip = -(-h // parts); trial = []; ok = True
                for p in range(parts):
                    sh = min(strip, h - p * strip)
                    if sh <= 0:
                        break
                    # 1 transparent texel right of and below each piece: the GPU can
                    # sample one texel past a quad's far edge, which showed as a
                    # stray line next to tightly packed art. (Left/top edges start
                    # exactly on the quad's first texel.)
                    spot = packer.place(w, sh)
                    if spot is None:
                        ok = False; break
                    trial.append((spot[0], spot[1], spot[2], w, sh, p * strip, spot[3]))
                if ok:
                    pieces = trial; break
                for page, px, py, pw, ph, _, border in trial:   # give the space back
                    packer.release(page, px, py, pw, ph, border)
            if pieces is None:
                report['kept_alundra'].append(iset); continue
            for page, px, py, pw, ph, sy, border in pieces:
                for i in border:                  # writable border texels -> transparent
                    o = page * 32768 + (i // 256) * 128 + (i % 256) // 2
                    raw[o] = raw[o] & 0xF0 if (i % 256) % 2 == 0 else raw[o] & 0x0F
                for yy in range(ph):
                    for xx in range(pw):
                        v = pixels[(sy + yy) * w + xx]
                        o = page * 32768 + (py + yy) * 128 + (px + xx) // 2
                        raw[o] = (raw[o] & 0xF0) | v if (px + xx) % 2 == 0 else (raw[o] & 0x0F) | (v << 4)
            pieces = [piece[:6] for piece in pieces]
            placed[meia_set] = (pieces, left, top, False)
            mirrors[(image.size, image.tobytes())] = meia_set
        pieces, left, top, flipped = placed[meia_set]
        if len(pieces) > count:
            report['kept_alundra'].append(iset); continue
        first_page_byte = data[pos + 2]
        for q in range(count):
            at = pos + 2 + q * 14
            if q < len(pieces):
                page, px, py, pw, ph, sy = pieces[q]
                x1, y1 = left, top + sy
                if flipped:
                    # Mirrored quad: corners run right to left; the native sampler reads
                    # one texel further right on flipped quads (entity_preview), so sx - 1.
                    out[at:at + 14] = struct.pack('<6B8b', (first_page_byte & ~7) | page, PALETTE_SLOT, max(0, px - 1), py, pw, ph,
                                                  x1 + pw, y1, x1, y1, x1 + pw, y1 + ph, x1, y1 + ph)
                else:
                    out[at:at + 14] = struct.pack('<6B8b', (first_page_byte & ~7) | page, PALETTE_SLOT, px, py, pw, ph,
                                                  x1, y1, x1 + pw, y1, x1, y1 + ph, x1 + pw, y1 + ph)
            else:
                out[at:at + 14] = bytes(14)
        report['strips'] += len(pieces)
    out[palette_at:palette_at + 32] = struct.pack('<16H', *words)
    for slot in RECOLOR_PALETTES:
        at = start + header[5] + slot * 32
        old = struct.unpack_from('<16H', data, at)
        out[at:at + 32] = struct.pack('<16H', *(meia_tones(w) for w in old))
    for (slot, index), rgb in MEIA_COLOURS.items():
        at = start + header[5] + slot * 32 + index * 2
        out[at:at + 2] = struct.pack('<H', rgb555(rgb, struct.unpack_from('<H', data, at)[0]))
    report_recolor = list(RECOLOR_PALETTES)
    if portrait is not None and portrait.size == (p_w, p_h):
        pixels = indexed(portrait)
        for yy in range(p_h):
            for xx in range(p_w):
                v = pixels[yy * p_w + xx]; o = p_page * 32768 + (p_sy + yy) * 128 + (p_sx + xx) // 2
                raw[o] = (raw[o] & 0xF0) | v if (p_sx + xx) % 2 == 0 else (raw[o] & 0x0F) | (v << 4)
        out[portrait_pos + 3] = PALETTE_SLOT
        report['menu_portrait'] = 'Meia'
    _clear_unused(raw, packer.free)
    packed = pack_ez_fit(bytes(raw), bytes(data[sheet:sheet + 6]), end - sheet)
    if len(packed) > end - sheet:
        raise ValueError(f'Meia costume texture needs {len(packed)} bytes; the sprite sheet has {end - sheet}')
    if unpack_ez(packed, limit=262144)[0] != bytes(raw):
        raise ValueError('Meia costume texture round-trip failed')
    out[sheet:end] = packed + bytes(end - sheet - len(packed))
    session.data = out if not isinstance(session.data, bytearray) else out
    report['texture_bytes'] = len(packed)
    report['room'] = end - sheet
    report['recoloured_palettes'] = report_recolor
    report['gameplay_verified'] = False
    if basic_attack:
        from meia_actions import apply_meia_actions
        report['meia_actions'] = apply_meia_actions(session, original, set(costume), alundra_fallback)
        if not alundra_fallback:
            # the user's finished Meia frames (meia-final-1x.png), drawn over the built ones
            from meia_final_frames import apply_final_frames
            report['meia_final_frames'] = apply_final_frames(session)
    return report
