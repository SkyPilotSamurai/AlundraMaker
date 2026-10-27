"""Mod option "Meia basic attack": Meia frames for sword attacks, carrying and damage.

Meia's own sprites (class 400 map 51, class 302 map 8) only stand, walk and
jump, so these frames are built from Alundra's: his pose (body pixels, already
in Meia's colours from player_costume's palette changes) with his head
replaced by Meia's head from her standing frame of the same direction.
* The head is found by matching Alundra's standing head (rows above 22 pixels
  over the origin, same direction) against the frame, within 18 pixels; a
  frame where it cannot be found (e.g. knocked flat) keeps his recoloured head.
* Alundra's hair/face pixels under the match are cleared, then Meia's head is
  drawn at the same offset.
* Quads drawn with other palettes than his body (17, flashes 20/21) - the
  sword, its swing trail, charge sparks - are kept as the game draws them.
* All built frames share one new 15-colour palette in global slot 10 (unused
  by every sprite in the game data).
The damage flash (palettes 20/21) is not kept on rebuilt frames.
Nothing here is verified in game.
"""
import struct

SWORD = (0x10, 0x14, 0x18, 0x3F, 0x41, 0x44, 0x46, 0x49, 0x4B)          # attacks / jump attacks / charge
CARRY = (0x05, 0x06, 0x07, 0x09, 0x0A, 0x0C, 0x2E, 0x2F, 0x30)          # lift, carry, throw, jumps with object
DAMAGE = (0x1C, 0x31)                                                    # knock back, damage taken
ACTION_ANIMATIONS = frozenset(SWORD + CARRY + DAMAGE)
BODY_PALETTES = (17, 20, 21)
PALETTE_SLOT = 10
NECK = -22          # head = pixels above this row (relative to the sprite origin)
SEARCH = 18


def _render(data, catalogue, map_id, anim, direction):
    from editor_session import EditSession
    from animation_preview import load_animation
    session = EditSession(bytes(data), None, verify=False)
    return load_animation(session, map_id, catalogue, anim, direction)


def _warm(c):
    """Hair and skin: warm colours (red clearly above blue). Clothes (blue,
    purple, lavender) and white sleeves are not warm."""
    return c[3] >= 128 and c[0] >= c[2] + 24 and max(c[:3]) >= 60


def _dark(c):
    return c[3] >= 128 and max(c[:3]) < 60


def _head(image, left, top):
    """(RGBA head image, left, top): hair and face only.

    Pixels above NECK that are warm (hair, skin), plus the dark outline touching
    them and small light details (eye whites, highlights) enclosed by them.
    Shoulders, sleeves and collars are left out."""
    from PIL import Image
    rows = NECK - top
    if rows <= 0:
        return None
    src = image.convert('RGBA'); w, h = src.width, min(src.height, rows)
    px = src.load()
    warm = {(x, y) for y in range(h) for x in range(w) if _warm(px[x, y])}
    keep = set(warm)
    for y in range(h):
        for x in range(w):
            c = px[x, y]
            if c[3] < 128 or (x, y) in warm:
                continue
            near = [(x + a, y + b) in warm for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]
            if _dark(c) and any(near):
                keep.add((x, y))                    # outline
            elif sum(near) >= 5:
                keep.add((x, y))                    # eye white / highlight inside the face
    # Fill holes: any pixel of hers enclosed by head pixels left, right and above
    # (hair highlights, shading) belongs to the head too.
    for _ in range(2):
        add = set()
        for y in range(h):
            for x in range(w):
                if (x, y) in keep or px[x, y][3] < 128:
                    continue
                if (any((x - a, y) in keep for a in range(1, w)) and any((x + a, y) in keep for a in range(1, w))
                        and any((x, y - b) in keep for b in range(1, h))):
                    add.add((x, y))
        if not add:
            break
        keep |= add
    out = Image.new('RGBA', (w, h))
    op = out.load()
    for x, y in keep:
        op[x, y] = px[x, y]
    box = out.getbbox()
    if box is None:
        return None
    return out.crop(box), left + box[0], top + box[1]


def _erase_points(head, ox, oy):
    """Pixels covered by Alundra's head (offset ox, oy), grown by one pixel, so
    no part of his hair or face is left next to Meia's."""
    hp = head.load(); out = set()
    for y in range(head.height):
        for x in range(head.width):
            if hp[x, y][3] >= 128:
                for a in (-1, 0, 1):
                    for b in (-1, 0, 1):
                        out.add((ox + x + a, oy + y + b))
    return out


def _hair(c):
    """Alundra's hair colours (yellow to brown, little blue); skin has more blue."""
    return c[3] >= 128 and c[0] >= c[2] + 24 and c[2] < 0.4 * c[0]


def _clear_hair_strands(work, ref, ox, oy, erased, chin, protect=()):
    """Hair of his that sticks out past the matched head (flying strands, spikes):
    hair-coloured pixels (and their outline) joined to the erased head, above his chin."""
    wp = work.load(); rp = ref.load()
    def colour(x, y):
        rx, ry = x - ox, y - oy
        return rp[rx, ry] if 0 <= rx < ref.width and 0 <= ry < ref.height else (0, 0, 0, 0)
    todo = list(erased); seen = set(erased)
    while todo:
        x, y = todo.pop()
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                n = (x + a, y + b)
                if n in seen or not (0 <= n[0] < work.width and 0 <= n[1] < min(work.height, chin)):
                    continue
                seen.add(n)
                if n not in protect and wp[n][3] >= 128 and _hair(colour(*n)):
                    wp[n] = (0, 0, 0, 0); todo.append(n)
    # lone outline pixels left floating
    for y in range(min(work.height, chin)):
        for x in range(work.width):
            if wp[x, y][3] >= 128 and _dark(wp[x, y]):
                if not any(0 <= x + a < work.width and 0 <= y + b < work.height and wp[x + a, y + b][3] >= 128
                           and not _dark(wp[x + a, y + b]) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b):
                    wp[x, y] = (0, 0, 0, 0)


def _drop_specks(image, max_size=4):
    """Remove tiny islands of pixels (left-over bits of his hair) of up to max_size pixels."""
    px = image.load(); w, h = image.size; seen = set()
    for y in range(h):
        for x in range(w):
            if (x, y) in seen or px[x, y][3] < 128:
                continue
            group = [(x, y)]; seen.add((x, y)); i = 0
            while i < len(group) and len(group) <= max_size:
                cx, cy = group[i]; i += 1
                for a in (-1, 0, 1):
                    for b in (-1, 0, 1):
                        n = (cx + a, cy + b)
                        if n not in seen and 0 <= n[0] < w and 0 <= n[1] < h and px[n][3] >= 128:
                            seen.add(n); group.append(n)
            if len(group) <= max_size:
                for n in group:
                    px[n] = (0, 0, 0, 0)


def _match(patch, frame):
    """Best (dx, dy, score) placing patch (image,left,top) over frame (image,left,top)."""
    pimg, pl, pt = patch; fimg, fl, ft = frame
    pp = pimg.load(); fp = fimg.load()
    opaque = [(x, y, pp[x, y]) for y in range(pimg.height) for x in range(pimg.width) if pp[x, y][3] >= 128]
    if not opaque:
        return None
    best = None
    for dy in range(-SEARCH, SEARCH + 1):
        for dx in range(-SEARCH, SEARCH + 1):
            score = 0.0
            for x, y, c in opaque:
                fx = pl + x + dx - fl; fy = pt + y + dy - ft
                if 0 <= fx < fimg.width and 0 <= fy < fimg.height:
                    d = fp[fx, fy]
                    if d[3] >= 128:
                        score += 1.0 if abs(d[0] - c[0]) + abs(d[1] - c[1]) + abs(d[2] - c[2]) < 90 else 0.25
                    else:
                        score -= 0.5
                else:
                    score -= 0.5
            if best is None or score > best[2]:
                best = (dx, dy, score)
    return best[0], best[1], best[2] / len(opaque)


def _unflashed(data, image_sets):
    """Copy of data where the damage-flash palettes (20, 21) of these image sets
    read as the normal body palette 17 (same colour indexes), for matching."""
    from player_costume import _global_bank
    out = bytearray(data)
    start, sheet, end, header = _global_bank(data)
    base = start + struct.unpack_from('<4I', data, start + struct.unpack_from('<i', data, start + header[3])[0])[3]
    for iset in image_sets:
        pos = base + iset * 2
        for q in range(data[pos + 1]):
            if out[pos + 3 + q * 14] in (20, 21):
                out[pos + 3 + q * 14] = 17
    return bytes(out)


THRESHOLD = 0.38


TORSO = 13          # rows below his chin searched for the backpack
BAG_INDEXES = (5, 6)
CLOTHES = (2, 3, 11, 12, 13, 14)   # palette 17 tunic greys and blues (her dress after recolouring)  # palette 17 browns of his backpack (also his hair, which is gone by then)


def _bag_colours(original):
    """(palette 17 colours, backpack core indexes, enclosed-edge indexes)."""
    from player_costume import _global_bank
    from sprite_frame_replace import rgb_of
    start, _, _, header = _global_bank(original)
    words = struct.unpack_from('<16H', original, start + header[5] + 17 * 32)
    return [rgb_of(w) for w in words]


def _index(colours, rgb, cache={}):
    key = (id(colours), rgb)
    if key not in cache:
        cache[key] = min(range(16), key=lambda k: sum((a - b) ** 2 for a, b in zip(colours[k], rgb)))
    return cache[key]


def _bag_pixels(ref, colours, row0):
    """Backpack pixels of a plain-colour frame (positions in ref), rows row0 .. row0+TORSO."""
    rp = ref.load(); w, h = ref.size
    def idx(x, y):
        c = rp[x, y]
        return None if c[3] < 128 else _index(colours, c[:3])
    rows = range(max(0, row0), min(h, row0 + TORSO))
    bag = {(x, y) for y in rows for x in range(w) if idx(x, y) in BAG_INDEXES}
    if not bag:
        return bag
    # Grow into what the brown encloses (highlights, outline, buckles, straps),
    # only inside the brown area's own box.
    bx0 = min(x for x, _ in bag) - 1; bx1 = max(x for x, _ in bag) + 1
    by0 = min(y for _, y in bag) - 1; by1 = max(y for _, y in bag) + 1
    for _ in range(4):
        grow = set()
        for y in range(max(0, by0), min(h, by1 + 1)):
            for x in range(max(0, bx0), min(w, bx1 + 1)):
                i = idx(x, y)
                if (x, y) in bag or i is None:
                    continue
                n = sum((x + a, y + b) in bag for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b)
                if n >= (3 if i in (1, 4, 8, 9, 10, 15) else 5):
                    grow.add((x, y))
        if not grow:
            break
        bag |= grow
    return bag


def _remove_backpack(work, ref, ox, oy, row0, colours, direction=0, protect=()):
    """Meia has no backpack: take his off. Brown backpack pixels (and the tan
    highlights and dark outline enclosed by them) from just above his chin to
    TORSO rows below. Where the body continues on both sides the hole is filled
    with the nearest clothes colour of that row, otherwise it becomes empty."""
    wp = work.load(); w, h = work.size; rp = ref.load()
    bag = {(x + ox, y + oy) for x, y in _bag_pixels(ref, colours, row0 - oy)}
    bag = {(x, y) for x, y in bag if 0 <= x < w and 0 <= y < h and wp[x, y][3] >= 128 and (x, y) not in protect}
    if not bag:
        return 0
    def cool(x, y):
        rx, ry = x - ox, y - oy
        if 0 <= rx < ref.width and 0 <= ry < ref.height and rp[rx, ry][3] >= 128:
            c = rp[rx, ry]
            return c[2] >= c[0] and max(c[:3]) >= 60
        return False
    clothes = [wp[x, y] for y in range(h) for x in range(w)
               if (x, y) not in bag and wp[x, y][3] >= 128 and cool(x, y)]
    fallback = max(set(clothes), key=clothes.count) if clothes else None

    def dress(x, y):
        """Nearest clothes colour (search outwards), else the frame's commonest one."""
        for r in range(1, 9):
            for a in range(-r, r + 1):
                for b in (-r, r):
                    for nx, ny in ((x + a, y + b), (x + b, y + a)):
                        if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in bag and wp[nx, ny][3] >= 128 and cool(nx, ny):
                            return wp[nx, ny]
        return fallback
    paint = {}
    for x, y in bag:
        def body(dx_, dy_):
            return any(0 <= x + dx_ * a < w and 0 <= y + dy_ * a < h and wp[x + dx_ * a, y + dy_ * a][3] >= 128
                       and (x + dx_ * a, y + dy_ * a) not in bag for a in range(1, 9))
        # Seen from behind (direction 1) the pack covers her back: fill it with her dress.
        # Otherwise only holes with body on both sides are filled; pack sticking out is cut away.
        if direction == 1:
            inside = (body(-1, 0) and body(1, 0)) or body(0, -1) or body(0, 1)
        else:
            inside = body(-1, 0) and body(1, 0)
        paint[(x, y)] = dress(x, y) if inside else None
    for (x, y), c in paint.items():
        wp[x, y] = c if c is not None else (0, 0, 0, 0)
    return len(bag)


def _prepare(original, image_sets, threshold):
    """Shared steps: heads per direction, head match per image set."""
    from editor_session import EditSession
    from animation_preview import animation_reader
    from player_costume import _player_image_sets, MEIA_CLASS, MEIA_MAP
    plain_preview = animation_reader(EditSession(_unflashed(original, image_sets), None, verify=False), 163, 0)[0]
    uses, _, _ = _player_image_sets(original)
    heads = {}
    for d in range(4):
        alundra = [f for f in _render(original, 0, 163, 0, d).frames if f.image is not None][0]
        meia = [f for f in _render(original, MEIA_CLASS, MEIA_MAP, 0, d).frames if f.image is not None][0]
        heads[d] = (_head(alundra.image, alundra.left, alundra.top), _head(meia.image, meia.left, meia.top))
    report = dict(head_swapped=0, head_not_found=[], backpack_pixels=0, scores={})
    matches = {}
    for iset in sorted(image_sets):
        try:
            ref, left, top = plain_preview.image_set(0, iset)[:3]
        except Exception:
            continue
        if ref is None:
            continue
        direction = sorted(uses.get(iset, {(0, 0, 0)}))[0][1]
        a_head, m_head = heads[direction]
        found = _match(a_head, (ref.convert('RGBA'), left, top)) if a_head and m_head else None
        report['scores'][iset] = None if found is None else round(found[2], 2)
        if found is None or found[2] < threshold:
            report['head_not_found'].append(iset); continue
        matches[iset] = (found[0], found[1], direction, ref.convert('RGBA'), left, top)
    return heads, matches, report


def _area(heads, match, colours):
    """Screen boxes redrawn for a frame: the head (his and hers) and his backpack."""
    dx, dy, direction, ref, rl, rt = match
    (himg, hl, ht), (mimg, ml, mt) = heads[direction]
    boxes = [(min(hl, ml) + dx, min(ht, mt) + dy, max(hl + himg.width, ml + mimg.width) + dx,
              max(ht + himg.height, mt + mimg.height) + dy)]
    bag = _bag_pixels(ref, colours, ht + dy + himg.height - rt - 2)
    if bag:
        xs = [x + rl for x, _ in bag]; ys = [y + rt for _, y in bag]
        boxes.append((min(xs) - 1, min(ys) - 1, max(xs) + 2, max(ys) + 2))
    return boxes


def _quads_in(data, base, iset, boxes):
    """(quads touching any box with a body palette, other drawn quads)."""
    hit, other = [], []
    pos = base + iset * 2
    for q in range(data[pos + 1]):
        at = pos + 2 + q * 14
        pal = data[at + 1]; w, h = data[at + 4], data[at + 5]
        if not (w and h):
            continue
        corners = struct.unpack_from('<8b', data, at + 6)
        xs, ys = corners[0::2], corners[1::2]
        if pal in BODY_PALETTES and any(min(xs) < box[2] and max(xs) > box[0]
                                        and min(ys) < box[3] and max(ys) > box[1] for box in boxes):
            hit.append(q)
        else:
            other.append(q)
    return hit, other


SKIN = (8, 9, 10)           # palette 17 skin tones (face, arms, hands)


def _arms(work, ref, ox, oy, head_shape, colours):
    """His arms and hands: skin-coloured pixels joined to skin outside his head
    (so not his face), with their outline and highlights."""
    wp = work.load(); rp = ref.load(); w, h = work.size
    def idx(x, y):
        rx, ry = x - ox, y - oy
        if 0 <= rx < ref.width and 0 <= ry < ref.height and rp[rx, ry][3] >= 128 and wp[x, y][3] >= 128:
            return _index(colours, rp[rx, ry][:3])
        return None
    skin = {(x, y) for y in range(h) for x in range(w) if idx(x, y) in SKIN}
    near_head = {(x + a, y + b) for x, y in head_shape for a in (-1, 0, 1) for b in (-1, 0, 1)}
    arms = set(); seen = set()
    for start in skin:
        if start in seen:
            continue
        group = [start]; seen.add(start); i = 0
        while i < len(group):
            x, y = group[i]; i += 1
            for a in (-1, 0, 1):
                for b in (-1, 0, 1):
                    n = (x + a, y + b)
                    if n in skin and n not in seen:
                        seen.add(n); group.append(n)
        outside = [p for p in group if p not in near_head]
        if not outside:
            continue                      # his face
        if len(outside) == len(group):
            arms.update(group); continue
        # Joined to his face (through the neck): keep the part outside his head and
        # what lies within 3 pixels of it (a hand at the edge of the head).
        out_set = set(outside)
        arms.update(p for p in group if p in out_set or any(
            (p[0] + a, p[1] + b) in out_set for a in range(-3, 4) for b in range(-3, 4)))
    edge = {(x + a, y + b) for x, y in arms for a in (-1, 0, 1) for b in (-1, 0, 1)}
    arms |= {p for p in edge - arms if 0 <= p[0] < w and 0 <= p[1] < h and idx(*p) in (1, 4, 15)}
    return arms


def _redraw(image, left, top, match, heads, bag):
    """His frame part with Meia's head and without hair strands or backpack.
    His arms and hands stay, drawn in front of her head as in his frame."""
    from PIL import Image
    dx, dy, direction, ref, rl, rt = match
    (himg, hl, ht), (mimg, ml, mt) = heads[direction]
    work = image.convert('RGBA').copy(); wp = work.load()
    rp = ref.load(); ox, oy = rl - left, rt - top
    shape = {p for p in _erase_points(himg, hl + dx - left, ht + dy - top)
             if 0 <= p[0] < work.width and 0 <= p[1] < work.height}
    arms = _arms(work, ref, ox, oy, shape, bag)
    arm_pixels = {p: wp[p] for p in arms}
    erased = set()
    for fx, fy in shape:
        if (fx, fy) in arms:
            continue
        rx, ry = fx - ox, fy - oy
        if 0 <= rx < ref.width and 0 <= ry < ref.height and rp[rx, ry][3] >= 128 \
                and _index(bag, rp[rx, ry][:3]) in CLOTHES:
            continue                      # his shoulders/collar stay (her dress colours)
        wp[fx, fy] = (0, 0, 0, 0); erased.add((fx, fy))
    chin = ht + dy + himg.height - top
    _clear_hair_strands(work, ref, ox, oy, erased, chin=chin, protect=arms)
    removed = _remove_backpack(work, ref, ox, oy, chin - 2, bag, direction, protect=arms)
    x0 = min(left, ml + dx); y0 = min(top, mt + dy)
    x1 = max(left + work.width, ml + dx + mimg.width); y1 = max(top + work.height, mt + dy + mimg.height)
    canvas = Image.new('RGBA', (x1 - x0, y1 - y0))
    canvas.alpha_composite(work, (left - x0, top - y0))
    canvas.alpha_composite(mimg, (ml + dx - x0, mt + dy - y0))
    cp = canvas.load()
    for (x, y), c in arm_pixels.items():              # arms in front of her head
        cp[x + left - x0, y + top - y0] = c
    _drop_specks(canvas, max_size=4)
    return canvas, x0, y0, removed


def _hidden_except(data, base, wanted):
    """Copy of data where, per image set, only the listed quads are drawn."""
    out = bytearray(data)
    for iset, show in wanted.items():
        pos = base + iset * 2
        for q in range(data[pos + 1]):
            if q not in show:
                at = pos + 2 + q * 14
                out[at + 4] = out[at + 5] = 0
    return bytes(out)


def _frame_base(data):
    from player_costume import _global_bank
    start, sheet, end, header = _global_bank(data)
    return start + struct.unpack_from('<4I', data, start + struct.unpack_from('<i', data, start + header[3])[0])[3]


def build_frames(original, costumed, image_sets, threshold=THRESHOLD):
    """({image set: (RGBA picture, left, top)}, {image set: quads to keep}, report).

    Only the body quads around the head and upper body are redrawn; legs,
    sword and effects stay as they are (pixels shared between frames stay
    shared). original: unchanged game data (matching, Meia's art); costumed:
    data after player_costume (body colours)."""
    from editor_session import EditSession
    from animation_preview import animation_reader
    heads, matches, report = _prepare(original, image_sets, threshold)
    base = _frame_base(costumed); bag = _bag_colours(original)
    keep, show = {}, {}
    for iset, m in matches.items():
        hit, other = _quads_in(costumed, base, iset, _area(heads, m, bag))
        show[iset], keep[iset] = hit, other
    upper_preview = animation_reader(EditSession(_hidden_except(_unflashed(costumed, matches), base, show),
                                                 None, verify=False), 163, 0)[0]
    out = {}
    for iset, m in matches.items():
        image, left, top = upper_preview.image_set(0, iset)[:3]
        if image is None:
            continue
        canvas, x0, y0, removed = _redraw(image, left, top, m, heads, bag)
        out[iset] = (canvas, x0, y0); report['head_swapped'] += 1; report['backpack_pixels'] += removed
    return out, keep, report


def action_image_sets(original, costume_sets, include):
    """Image sets used by the chosen action animations and not already part of the costume."""
    from player_costume import _player_image_sets
    uses, _, _ = _player_image_sets(original)
    return {i for i, u in uses.items() if any(a in include for a, _, _ in u) and i not in costume_sets}


def apply_heads_in_place(session, original, image_sets):
    """"Alundra for missing actions": no texture room for new frames, so the
    redrawn picture (Meia's head, no backpack) is written straight into the
    texels of his own head/upper-body quads (clipped to each quad, colours
    matched to palette 17). Every frame that draws those texels changes with
    it, which also gives his other weapon attacks her head. Only plain
    (unscaled, unmirrored) uses are written; their mirrored uses follow."""
    from editor_session import EditSession
    from animation_preview import animation_reader
    from sprite_frame_replace import Bank, rgb_of
    data = bytearray(session.data)
    bank = Bank(data); base = bank.frames_base(data, 0); users = bank.quad_users(data)
    heads, matches, report = _prepare(original, image_sets, THRESHOLD)
    report.pop('scores', None); report['quads_painted'] = 0
    bag = _bag_colours(original)
    colours = [rgb_of(w) for w in bank.palette_words(data, 17)]
    cache = {}

    def nearest(rgb):
        if rgb not in cache:
            cache[rgb] = min(range(1, 16), key=lambda k: sum((a - b) ** 2 for a, b in zip(colours[k], rgb)))
        return cache[rgb]
    show = {}
    for iset, m in matches.items():
        hit, _ = _quads_in(data, base, iset, _area(heads, m, bag))
        show[iset] = hit
    preview = animation_reader(EditSession(_hidden_except(_unflashed(bytes(data), matches), base, show),
                                           None, verify=False), 163, 0)[0]
    done = set()
    for iset, m in matches.items():
        image, left, top = preview.image_set(0, iset)[:3]
        if image is None:
            continue
        canvas, x0, y0, removed = _redraw(image, left, top, m, heads, bag)
        cp = canvas.load(); painted = False
        pos = base + iset * 2
        for q in show[iset]:
            at = pos + 2 + q * 14
            page, pal, sx, sy, w, h = struct.unpack_from('<6B', data, at)
            c = struct.unpack_from('<8b', data, at + 6)
            key = (page & 7, sx, sy, w, h)
            if key in done or c[2] - c[0] != w or c[5] - c[1] != h:
                continue
            if any(idx != 0 for idx, _, _ in users.get(key, ())):
                continue
            done.add(key); painted = True; report['quads_painted'] += 1
            p = page & 7
            for ty in range(h):
                for tx in range(w):
                    X, Y = c[0] + tx - x0, c[1] + ty - y0
                    px = cp[X, Y] if 0 <= X < canvas.width and 0 <= Y < canvas.height else (0, 0, 0, 0)
                    value = 0 if px[3] < 128 else nearest(px[:3])
                    o = p * 32768 + (sy + ty) * 128 + (sx + tx) // 2
                    if (sx + tx) % 2 == 0:
                        bank.raw[o] = (bank.raw[o] & 0xF0) | value
                    else:
                        bank.raw[o] = (bank.raw[o] & 0x0F) | (value << 4)
        if painted:
            report['head_swapped'] += 1; report['backpack_pixels'] += removed
    session.data = bank.write(data)
    return report


# When the new pictures do not fit the global texture room, these animations
# (least used first) get Meia's head painted into his own pixels instead.
DROP_ORDER = ((0x18,), (0x44, 0x46, 0x49, 0x4B), (0x14, 0x20), (0x2E, 0x2F, 0x30, 0x06, 0x0A), (0x1C,))


def apply_meia_actions(session, original, costume_sets, alundra_fallback=False):
    """Second costume pass (after player_costume.apply_costume). Edits session.data; returns a report."""
    from player_costume import _player_image_sets, _global_bank
    from sprite_frame_replace import replace_image_sets
    wanted = action_image_sets(original, costume_sets, ACTION_ANIMATIONS)
    if alundra_fallback:
        report = apply_heads_in_place(session, original, wanted)
        report['mode'] = 'head painted into shared quads'
        return report
    frames, keep, report = build_frames(original, bytes(session.data), wanted)
    report.pop('scores', None)
    if not frames:
        return dict(report, replaced=0)
    # Colours: the body palette 17 as player_costume left it (Meia's hair, his skin
    # tones, her dress colours); each frame keeps its own slot, so the damage
    # flash (20/21, same colour order) still flashes.
    start, _, _, header = _global_bank(session.data)
    words = list(struct.unpack_from('<16H', session.data, start + header[5] + 17 * 32))
    uses, _, _ = _player_image_sets(original)
    dropped = []
    for step in range(len(DROP_ORDER) + 1):
        gone = {a for group in DROP_ORDER[:step] for a in group}
        chosen = {i: v for i, v in frames.items()
                  if not {a for a, _, _ in uses[i] if a in ACTION_ANIMATIONS} <= gone}
        try:
            data, info = replace_image_sets(session.data, 0, chosen, palette=('keep', words), keep_indexes=keep)
            dropped = sorted(gone); break
        except ValueError as error:
            if 'texture bytes' not in str(error) or step == len(DROP_ORDER):
                raise
    session.data = bytearray(data)
    report.update(replaced=len(info['replaced']), image_sets=len(wanted),
                  free_texels=info['free_texels'], needed_texels=info['needed_texels'])
    rest = (set(frames) - set(info['replaced']))
    if rest:
        # No room for new pictures: paint her head into his own pixels for these.
        painted = apply_heads_in_place(session, original, rest)
        report.update(painted_in_place=painted.get('head_swapped', 0), animations_painted_in_place=dropped)
    return report
