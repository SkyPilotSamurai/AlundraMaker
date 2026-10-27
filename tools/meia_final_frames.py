"""Meia basic attack: the user's finished Meia frames (meia-final-1x.png).

game/sprite-sheets/meia-final/meia-final-1x.png holds hand-made Meia
pictures, 1:1 pixels, one frame per 72x56 cell. A frame's sprite origin sits at
x = 40 + 72 * column, y = 46 + 56 * row. Column 0 (idle) is ignored, so is the
second block (rows 4-7, a copy of rows 0-3). Blocks of four rows (direction
0-3), frames from column 1:
    rows  0-3  0x3F attack sword (same pictures as 0x10 / 0x44 / 0x49)
    rows  8-11 0x18 charge attack: left out (user), keeps the current frames
    rows 12-15 0x07 moving with object
    rows 16-19 0x0C hold object
    rows 20-23 0x05 pickup object
    rows 24-27 0x09 throw object
    rows 28-31 0x1C damage knock back
Jumping versions (0x14/0x41/0x46/0x4B jump attacks, 0x0A, 0x2F, 0x30, 0x06,
0x2E) and 0x31 damage taken have no art of their own: they get the standing
picture of the same direction and frame (JUMP_COPIES), which also leaves room
in the global texture sheet for everything else.
The charge attack (OVERLAY) is drawn over its current frames, so parts of
her body the art's rings cover keep the current pixels.
Only the body is taken from the art: the quads drawn with the player's body
palettes (17, flashes 20/21). The sword, swing trails and charge effects (other
palettes) stay as the game draws them, and art pixels that repeat them are
dropped. Every other image set of the action animations whose current body
picture is the same (or a left/right mirror) gets the same new picture.
Normal pictures use their own 15 colours in global palette slot 10; flash
pictures are matched to their own flash palette. Applied after meia_actions
(player_costume, Meia basic attack without "Alundra for missing actions").
Nothing here is verified in game.
"""
import hashlib
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'game' / 'sprite-sheets' / 'meia-final' / 'meia-final-1x.png'
GROUPS = ((0, 0x3F), (12, 0x07), (16, 0x0C), (20, 0x05), (24, 0x09), (28, 0x1C))
# (jump animation, standing animation, fixed standing frame or None = same frame)
JUMP_COPIES = ((0x41, 0x3F, None), (0x46, 0x3F, None), (0x4B, 0x3F, None), (0x14, 0x3F, None),
               (0x0A, 0x09, None), (0x2F, 0x07, None), (0x30, 0x0C, None),
               (0x06, 0x0C, 0), (0x2E, 0x0C, 0), (0x31, 0x1C, None))
# animations whose art is drawn over the current frames instead of replacing them
# (the charge attack: its rings/sparks cover her body in the art)
OVERLAY = (0x18,)
# animations whose whole frames come from the art (her sword and trails too)
WHOLE_FRAME = ()   # whole frames do not fit the texture sheet
BODY = (17, 20, 21)
FLASH = (20, 21)
PALETTE_SLOT = 10
MARGIN = 3


def art_digest():
    try:
        h = hashlib.sha256(ART.read_bytes())
    except OSError:
        return None
    for path in sorted((ART.parent / 'overrides').glob('*')):   # corrected sheets change the build too
        h.update(path.name.encode()); h.update(path.read_bytes())
    return h.hexdigest()[:16]


def origin(row, column):
    return 40 + 72 * column, 46 + 56 * row


def _quads(data, base, iset):
    pos = base + iset * 2
    return [struct.unpack_from('<6B', data, pos + 2 + q * 14)[1] for q in range(data[pos + 1])]


def _pictures(data, show):
    """{image set: (RGBA, left, top)} drawing only the listed quads of each set."""
    from editor_session import EditSession
    from animation_preview import animation_reader
    from meia_actions import _hidden_except, _frame_base
    preview = animation_reader(EditSession(_hidden_except(bytes(data), _frame_base(data), show), None, verify=False), 163, 0)[0]
    out = {}
    for iset, quads in show.items():
        if not quads:
            continue
        image, left, top = preview.image_set(0, iset)[:3]
        if image is not None:
            out[iset] = (image.convert('RGBA'), left, top)
    return out


def _cut(art, ox, oy, body, kept):
    """Body pixels of the art around one frame: the current body box (plus a
    margin). Where the kept quads (sword, trails, charge effects) draw, an art
    pixel is kept only when the body also draws there (1 pixel leeway) and its
    colour differs from the kept quad's; specks of 3 pixels or less are dropped."""
    image, left, top = body
    x0, y0 = ox + left - MARGIN, oy + top - MARGIN
    x1, y1 = ox + left + image.width + MARGIN, oy + top + image.height + MARGIN
    piece = art.crop((x0, y0, x1, y1))
    px = piece.load(); bp = image.load()

    def body_near(X, Y):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                u, v = X + dx, Y + dy
                if 0 <= u < image.width and 0 <= v < image.height and bp[u, v][3] >= 128:
                    return True
        return False
    for y in range(piece.height):
        for x in range(piece.width):
            p = px[x, y]
            if p[3] < 128:
                px[x, y] = (0, 0, 0, 0)
                continue
            px[x, y] = p[:3] + (255,)
            if kept is None:
                continue
            kimage, kl, kt = kept
            X, Y = x0 + x - (ox + kl), y0 + y - (oy + kt)
            if 0 <= X < kimage.width and 0 <= Y < kimage.height:
                k = kimage.getpixel((X, Y))
                if k[3] >= 128:
                    # the game draws its sword/trail here: never a second copy from the art
                    px[x, y] = (0, 0, 0, 0)
    # only pixels on (or within 2 of) her body as the game draws it: the art's own
    # copy of the sword, in a slightly different place, would show twice
    for y in range(piece.height):
        for x in range(piece.width):
            if px[x, y][3] >= 128:
                X, Y = x0 + x - (ox + left), y0 + y - (oy + top)
                if not any(0 <= X + dx < image.width and 0 <= Y + dy < image.height and bp[X + dx, Y + dy][3] >= 128
                           for dy in range(-2, 3) for dx in range(-2, 3)):
                    px[x, y] = (0, 0, 0, 0)
    _drop_specks(piece)
    box = piece.getbbox()
    if box is None:
        return None
    return piece.crop(box), x0 + box[0] - ox, y0 + box[1] - oy


def _drop_specks(image, size=3):
    px = image.load(); w, h = image.size; seen = set()
    for y in range(h):
        for x in range(w):
            if (x, y) in seen or px[x, y][3] < 128:
                continue
            group = [(x, y)]; seen.add((x, y)); i = 0
            while i < len(group):
                cx, cy = group[i]; i += 1
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        u, v = cx + dx, cy + dy
                        if 0 <= u < w and 0 <= v < h and (u, v) not in seen and px[u, v][3] >= 128:
                            seen.add((u, v)); group.append((u, v))
            if len(group) <= size:
                for u, v in group:
                    px[u, v] = (0, 0, 0, 0)


def _overlay(body, cut):
    """The current body picture with the art's body pixels drawn on top."""
    from PIL import Image
    (b, bl, bt), (c, cl, ct) = body, cut
    x0, y0 = min(bl, cl), min(bt, ct)
    x1, y1 = max(bl + b.width, cl + c.width), max(bt + b.height, ct + c.height)
    canvas = Image.new('RGBA', (x1 - x0, y1 - y0))
    canvas.alpha_composite(b.convert('RGBA'), (bl - x0, bt - y0))
    # only art pixels on (or within 2 pixels of) her current body: drops ring
    # pieces of neighbouring frames that reach into the cut
    bp = b.convert('RGBA').load(); cp = c.load(); top = Image.new('RGBA', c.size)
    tp = top.load()
    for y in range(c.height):
        for x in range(c.width):
            if cp[x, y][3] < 128:
                continue
            X, Y = cl + x - bl, ct + y - bt
            if any(0 <= X + dx < b.width and 0 <= Y + dy < b.height and bp[X + dx, Y + dy][3] >= 128
                   for dy in range(-2, 3) for dx in range(-2, 3)):
                tp[x, y] = cp[x, y]
    canvas.alpha_composite(top, (cl - x0, ct - y0))
    return canvas, x0, y0


def _same(a, b):
    return a.size == b.size and a.tobytes() == b.tobytes()


derived_from = [None]


def _derive(t, bodies, new, mirror=True):
    """New picture for image set t when its current body is the same as (or a
    left/right mirror of) the body of a set that already has one, else None.
    Side views the game draws as mirrors stay mirrors (and share texels)."""
    from PIL import ImageOps
    timage, tl, tt = bodies[t]
    for s, (pic, nl, nt) in new.items():
        simage, sl, st = bodies[s]
        if _same(timage, simage):
            derived_from[0] = s
            return pic, tl + nl - sl, tt + nt - st
        if mirror and _same(timage, ImageOps.mirror(simage)):
            # mirrored about the body box: distance from its right edge becomes distance from its left
            derived_from[0] = ('mirror', s)
            return ImageOps.mirror(pic), tl + (sl + simage.width) - (nl + pic.width), tt + nt - st
    return None


ART_MIRRORS = True      # True: a cell whose game body mirrors another uses that cell's art mirrored
NEAR_MIRROR = 0.0     # >0: side views differing from a mirror by at most this share pixels (saves texture room)


def _merge_near_mirrors(new, frame_set, report):
    """Right-facing pictures (direction 3) that are a left/right mirror of the
    left-facing one (direction 2) except for a few pixels become that exact
    mirror, so both share texels (the global texture sheet is full)."""
    import numpy as np
    from PIL import Image, ImageOps
    report['near_mirrors'] = 0
    for _, anim in GROUPS:
        for f in range(16):
            a, b = frame_set.get((anim, 2, f)), frame_set.get((anim, 3, f))
            if a is None or b is None or a == b or a not in new or b not in new:
                continue
            (pa, la, ta), (pb, lb, tb) = new[a], new[b]
            if pa.size == pb.size and ImageOps.mirror(pa).tobytes() == pb.tobytes():
                continue
            m = ImageOps.mirror(pa)
            if abs(m.width - pb.width) > 2 or abs(m.height - pb.height) > 2:
                continue
            A = np.array(pb).astype(int); best = None
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    W = max(pb.width, m.width) + 4; H = max(pb.height, m.height) + 4
                    X = np.zeros((H, W, 4), int); Y = X.copy()
                    X[2:2 + pb.height, 2:2 + pb.width] = A
                    Y[2 + dy:2 + dy + m.height, 2 + dx:2 + dx + m.width] = np.array(m)
                    ox, oy = X[:, :, 3] >= 128, Y[:, :, 3] >= 128
                    n = int(((ox != oy) | (ox & (np.abs(X[:, :, :3] - Y[:, :, :3]).sum(2) > 0))).sum())
                    if best is None or n < best[0]:
                        best = (n, dx, dy)
            n, dx, dy = best
            if n <= NEAR_MIRROR * int((A[:, :, 3] >= 128).sum()):
                new[b] = (m, lb + dx, tb + dy); report['near_mirrors'] += 1


OVERRIDES = ART.parent / 'overrides'
# direction drawn as the left/right mirror of another one in an override sheet
OVERRIDE_MIRRORS = {0x3F: {3: 2}}


def _apply_overrides(new, frame_set, kept, report):
    """Per-animation sheets the user corrected (overrides/<anim>.png + .json,
    the editor's export layout; the transparent colour is cleared). Their
    pixels replace the frame as drawn, except where the game draws the sword
    or trails. A mirrored direction takes the other direction's picture
    flipped around the sprite origin."""
    import json
    from PIL import Image, ImageOps
    report['override_frames'] = 0
    for meta_path in sorted(OVERRIDES.glob('*.json')):
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        anim = meta['animation']; key = tuple(meta.get('transparent', (179, 42, 57)))
        sheet = Image.open(meta_path.with_suffix('.png')).convert('RGBA')
        px = sheet.load()
        for y in range(sheet.height):
            for x in range(sheet.width):
                p = px[x, y]
                if p[:3] == key or p[3] < 128:
                    px[x, y] = (0, 0, 0, 0)
        pictures = {}
        for cell in meta['cells']:
            x0, y0, cw, ch = cell['cell']; ox, oy = cell['origin']
            piece = sheet.crop((x0, y0, x0 + cw, y0 + ch))
            iset = frame_set.get((anim, cell['direction'], cell['frame']))
            if iset is None:
                continue
            k = kept.get(iset)
            if k is not None:
                kimage, kl, kt = k; kp = kimage.load(); pp = piece.load()
                for y in range(piece.height):
                    for x in range(piece.width):
                        X, Y = x0 + x - ox - kl, y0 + y - oy - kt
                        if pp[x, y][3] and 0 <= X < kimage.width and 0 <= Y < kimage.height and kp[X, Y][3] >= 128:
                            pp[x, y] = (0, 0, 0, 0)
            box = piece.getbbox()
            if box is None:
                continue
            pictures[(cell['direction'], cell['frame'])] = (piece.crop(box), x0 + box[0] - ox, y0 + box[1] - oy)
        for (d, f), value in list(pictures.items()):
            source = OVERRIDE_MIRRORS.get(anim, {}).get(d)
            if source is not None and (source, f) in pictures:
                pic, left, top = pictures[(source, f)]
                value = (ImageOps.mirror(pic), -(left + pic.width), top)
            iset = frame_set.get((anim, d, f))
            if iset is not None:
                new[iset] = value; report['override_frames'] += 1


def build(data):
    """({image set: (RGBA, left, top)} normal, same for flash, {image set: kept quads}, report)."""
    from PIL import Image, ImageOps
    from player_costume import _player_image_sets
    from meia_actions import ACTION_ANIMATIONS, _frame_base
    art = Image.open(ART).convert('RGBA')
    base = _frame_base(data)
    uses, _, _ = _player_image_sets(data)
    frame_set = {}
    for iset, rows in uses.items():
        for a, d, f in rows:
            frame_set[(a, d, f)] = iset
    action = {i for i, rows in uses.items() if any(a in ACTION_ANIMATIONS for a, _, _ in rows)}
    pal = {i: _quads(data, base, i) for i in action}
    # sword attacks: whole frames from the art (her sword and trails replace the game's)
    whole = {i for i in pal if any(a in WHOLE_FRAME for a, _, _ in uses[i])}
    body_q = {i: list(range(len(v))) if i in whole else [q for q, p in enumerate(v) if p in BODY] for i, v in pal.items()}
    kept_q = {i: [] if i in whole else [q for q, p in enumerate(v) if p not in BODY] for i, v in pal.items()}
    bodies = _pictures(data, body_q)
    kept = _pictures(data, kept_q)
    new = {}; report = dict(cells=0, from_art=0, shared=0, mirrored=0, empty=0); sources = {}; report['sources'] = sources
    for row0, anim in GROUPS:
        for d in range(4):
            for column in range(1, 13):
                iset = frame_set.get((anim, d, column - 1))
                if iset is None:
                    continue
                report['cells'] += 1
                if iset in new or iset not in bodies:
                    continue
                derived = _derive(iset, bodies, new, mirror=ART_MIRRORS)
                if derived is not None:
                    new[iset] = derived; report['mirrored'] += 1; sources[iset] = ('like', derived_from[0], row0 + d, column)
                    continue
                ox, oy = origin(row0 + d, column)
                cut = _cut(art, ox, oy, bodies[iset], kept.get(iset))
                if cut is None:
                    report['empty'] += 1
                    continue
                if anim in OVERLAY:
                    cut = _overlay(bodies[iset], cut)
                new[iset] = cut; report['from_art'] += 1; sources[iset] = ('art', row0 + d, column)
    _apply_overrides(new, frame_set, kept, report)
    _merge_near_mirrors(new, frame_set, report)
    # jumping versions (tucked legs in his art) get the standing picture of the
    # same direction and frame, placed by their own body box (head and left edge)
    report['jump_copies'] = 0
    for target, source, fixed in JUMP_COPIES:
        for d in range(4):
            for f in range(16):
                t = frame_set.get((target, d, f))
                s = frame_set.get((source, d, f if fixed is None else fixed))
                if t is None or s is None or t in new or s not in new or t not in bodies:
                    continue
                pic, nl, nt = new[s]; _, sl, st = bodies[s]; _, tl, tt = bodies[t]
                new[t] = (pic, tl + nl - sl, tt + nt - st); report['jump_copies'] += 1; sources[t] = ('jump', s)
    # other action frames drawing the same body picture (or its mirror)
    for t in sorted(action):
        if t in new or t not in bodies:
            continue
        derived = _derive(t, bodies, new)
        if derived is not None:
            new[t] = derived; report['shared'] += 1; sources[t] = ('like', derived_from[0])
    normal = {i: v for i, v in new.items() if not all(pal[i][q] in FLASH for q in body_q[i])}
    flash = {i: v for i, v in new.items() if i not in normal}
    keep = {i: kept_q[i] for i in new}
    report.update(normal=len(normal), flash=len(flash))
    return normal, flash, keep, report


def palette_words(pictures):
    """16 colour words (0 = transparent) for the normal pictures' colours."""
    from collections import Counter
    from PIL import Image
    from sprite_frame_replace import word_of
    counts = Counter()
    for image, _, _ in pictures.values():
        for p in image.getdata():
            if p[3] >= 128:
                counts[word_of(p)] += 1
    words = [w for w, _ in counts.most_common()]
    if len(words) > 15:
        # reduce to 15 colours (weighted median cut)
        from sprite_frame_replace import rgb_of
        strip = Image.new('RGB', (sum(min(c, 4096) for c in counts.values()), 1))
        x = 0
        for w, c in counts.items():
            for _ in range(min(c, 4096)):
                strip.putpixel((x, 0), rgb_of(w)); x += 1
        q = strip.quantize(15, method=Image.Quantize.MEDIANCUT)
        flat = q.getpalette()[:45]
        words = [word_of(tuple(flat[i:i + 3])) for i in range(0, 45, 3)]
    return [0] + words + [0x0421] * (15 - len(words))


def apply_final_frames(session):
    """Edit session.data in place. Returns a report (or None without the art)."""
    if not ART.exists():
        return None
    from sprite_frame_replace import replace_image_sets
    normal, flash, keep, report = build(bytes(session.data))
    from meia_actions import _frame_base
    data = bytes(session.data); kept_out = []; base = _frame_base(data)
    if normal:
        words = palette_words(normal)
        single = [i for i in normal if len(_quads(data, base, i)) - len(keep[i]) == 1]
        data, info = replace_image_sets(data, 0, normal, palette=(PALETTE_SLOT, words),
                                        keep_indexes={i: keep[i] for i in normal}, first=single)
        report['replaced'] = len(info['replaced']); kept_out += info['kept']
        report['palette_colours'] = sum(1 for w in words[1:] if w != 0x0421)
    if flash:
        data, info = replace_image_sets(data, 0, flash, keep_indexes={i: keep[i] for i in flash})
        report['flash_replaced'] = len(info['replaced']); kept_out += info['kept']
    report['did_not_fit'] = sorted(kept_out)
    session.data[:] = data if len(data) == len(session.data) else session.data
    if len(data) != len(session.data):
        session.data = bytearray(data)
    report['art'] = art_digest(); report['gameplay_verified'] = False
    return report
