"""Map-only sounds the project plays on maps whose sound set lacks them (user 2026-10-23).

How the game picks and loads a map's sound effects (US ALUN_CD.EXE, disassembly 2026-10-23,
docs/2026-10-22-maker-demo-qa.txt):
* A map loads ONE sound-effect set: 0x8004AEF8 -> override table 0x800AA04C (map, flag, set;
  ends at map 0) else 0x800C8B90[map] (0x8004B0D8; relocated for new maps by editor_qol).
* 0x80049820 loads set s (index 0x801D7DC4) from DATA\\SOUND.BIN: VH [T[s], T[s]+4) opened
  at SPU 0x5D840 (SsVabOpenHeadSticky 0x80092314), VB [T[s]+4, T[s+1]) sent in 64 KB pieces;
  T = word list 0x800A9B9C (8 bytes per set). 0x800A9B94..0x800AA02C is one rising list of
  sector offsets (global bank, sets, music) ending at the file size.
* PlaySound 0x8004A128: a record (0x800AA150 + 0x16 * id) whose bank (+0) is -1 plays from the
  global bank; otherwise the +0x0C chain is followed to the record of the loaded set
  (0x8004A3D4); none -> nothing plays. The game keeps per-set copies of a sound as chain
  records (ids 512..961).
So a map-only sound is made to play on another map the game's way: its tone and sample are
added to the set that map loads (a new program in that set's VAB) and a chain record for that
set is added after the sound's last chain record.

Limits (direct observation): the map set's samples start at SPU 0x5D840 and reverb mode 4
(Studio Large, boot 0x8004946C) reserves from 0xF204 * 8 = 0x79020 (libspu table 0x800CBC54),
so a set's VB may be at most 0x79020 - 0x5D840 bytes. VH: the largest stock VH slot (6144).
New chain records use ids 502..510: bank -2 (PlaySound returns at once), no record chains to
them, no stock script plays them (BD/BE/BF/75 scan of maps 0..482), no stock animation sound,
no addiu/ori immediate in the executable (511 is an animation sound and is not used)."""
import struct

REC, REC_SIZE = 0x800AA150, 0x16
OFFSETS, OFFSETS_END = 0x800A9B94, 0x800AA02C   # last word = SOUND.BIN size
SET_TABLE = 0x800A9B9C
OVERRIDES = 0x800AA04C
SPU_BASE, SPU_LIMIT = 0x5D840, 0xF204 * 8
VH_LIMIT = 6144
# The set's VH is read to 0x80116D00 (0x8004984C) and kept there (SsVabOpenHeadSticky); the next
# address the executable references is 0x80119500 (0x800494A8...), so the buffer holds 0x2800 bytes.
# Used only with "Expand Sound Space" (more_sound_room; evidence in
# docs/2026-10-23-self-contained-classes.txt section 7).
VH_BUFFER = 0x80119500 - 0x80116D00
FREE_RECORDS = tuple(range(502, 510))   # 510: the map-table scratch record (native_map_sound_table)
SECTOR = 0x800


class SoundSetError(ValueError):
    pass


def _f(exe, va):
    return va - struct.unpack_from('<I', exe, 0x18)[0] + 0x800


def record(exe, n):
    return list(struct.unpack_from('<11h', exe, _f(exe, REC) + REC_SIZE * n))


def chain(exe, n):
    out, seen = [], set()
    while n and n not in seen and -32768 <= n < 963:
        seen.add(n); out.append(n); n = record(exe, n)[6]
    return out


def banks_of(exe, n):
    """Sets sound n plays in, or None when it is global (-1) or silent (-2)."""
    ids = chain(exe, n)
    if not ids or record(exe, ids[0])[0] in (-1, -2):
        return None
    return {record(exe, i)[0] for i in ids}


def map_sets(exe, m):
    """Every set map m can load: its table entry and its flag overrides."""
    hi = struct.unpack_from('<I', exe, _f(exe, 0x8004B0DC))[0] & 0xFFFF
    lo = struct.unpack_from('<h', exe, _f(exe, 0x8004B0E4))[0]
    table = (hi << 16) + lo
    sets = {struct.unpack_from('<i', exe, _f(exe, table) + 4 * m)[0]}
    k = 0
    while True:
        e = struct.unpack_from('<3i', exe, _f(exe, OVERRIDES) + 12 * k)
        if e[0] == 0:
            break
        if e[0] == m:
            sets.add(e[2])
        k += 1
    return sets


def _offsets(exe):
    a = _f(exe, OFFSETS); n = (OFFSETS_END - OFFSETS) // 4 + 1
    return a, list(struct.unpack_from(f'<{n}I', exe, a))


def _set_range(exe, s):
    o = _f(exe, SET_TABLE) + 8 * s
    return struct.unpack_from('<3I', exe, o)


def _pad(b):
    return bytes(b) + bytes(-len(b) % SECTOR)


class _Vab:
    @classmethod
    def empty(cls, template_vh):
        """A VAB with no programs, tones or samples, keeping the template's header fields."""
        vh = bytearray(template_vh[:0x20]) + bytes(128 * 16) + bytes(512)
        struct.pack_into('<3H', vh, 0x12, 0, 0, 0)
        struct.pack_into('<I', vh, 0x0C, len(vh))
        return cls(bytes(vh), b'')

    def __init__(self, vh, vb):
        if vh[:4] != b'pBAV':
            raise SoundSetError('Sound set header is not a VAB')
        self.vh = bytearray(vh); self.vb = bytearray(vb)
        self.nprog, self.ntone, self.nvag = struct.unpack_from('<3H', self.vh, 0x12)

    def tone_at(self, p, t):
        return 0x20 + 128 * 16 + (p * 16 + t) * 32

    def sizes_at(self):
        return 0x20 + 128 * 16 + self.nprog * 16 * 32

    def vag(self, n):
        sizes = struct.unpack_from('<256H', self.vh, self.sizes_at())
        start = sum(sizes[:n]) * 8
        return bytes(self.vb[start:start + sizes[n] * 8])

    def used(self):
        sizes = struct.unpack_from('<256H', self.vh, self.sizes_at())
        return 0x20 + 128 * 16 + self.nprog * 512 + 512, sum(sizes[:self.nvag + 1]) * 8

    def add_tone(self, src, p, t, base=None, count=1):
        """Add tones t .. t+count-1 of src program p (a sound record plays `count` consecutive
        tones, PlaySound 0x8004A25C..0x8004A3C4); return (program, first tone index). A program
        added earlier (index >= base) with the same program attributes and room for all of them
        takes them (up to 16 tones; no header growth); otherwise a new program nprog is
        appended. Samples the set already holds byte for byte are shared."""
        count = max(1, count)
        base = self.nprog if base is None else base
        vh_len, vb_len = self.used()
        sizes_at = self.sizes_at()
        sizes = list(struct.unpack_from('<256H', self.vh, sizes_at))
        attrs = bytes(src.vh[0x20 + 16 * p + 1:0x20 + 16 * p + 16])
        tones, new_samples, nvag = [], [], self.nvag
        for i in range(count):
            tone = bytearray(src.vh[src.tone_at(p, t + i):src.tone_at(p, t + i) + 32])
            sample = src.vag(struct.unpack_from('<h', tone, 0x16)[0])
            # a sample the set already holds (byte for byte) is shared, not sent again (2026-10-23)
            shared = next((j for j in range(1, nvag + 1) if sizes[j] * 8 == len(sample)
                           and (self.vag(j) if j <= self.nvag else new_samples[j - self.nvag - 1]) == sample), None)
            if shared is None:
                if nvag >= 254:
                    raise SoundSetError('no free sample number')
                nvag += 1; sizes[nvag] = len(sample) // 8; new_samples.append(sample); shared = nvag
            tones.append((tone, shared))
        target = next((q for q in range(base, self.nprog)
                       if self.vh[0x20 + 16 * q] + count <= 16 and bytes(self.vh[0x20 + 16 * q + 1:0x20 + 16 * q + 16]) == attrs), None)
        if target is not None:
            k = self.vh[0x20 + 16 * target]
            for i, (tone, vag_no) in enumerate(tones):
                struct.pack_into('<hh', tone, 0x14, target, vag_no)
                o = self.tone_at(target, k + i); self.vh[o:o + 32] = tone
            self.vh[0x20 + 16 * target] = k + count
            struct.pack_into('<256H', self.vh, sizes_at, *sizes)
        else:
            if self.nprog >= 128:
                raise SoundSetError('no free program number')
            if any(self.vh[0x20 + 16 * q] for q in range(self.nprog, 128)):
                raise SoundSetError('programs are not packed')
            target, k = self.nprog, 0
            block = bytearray(16 * 32)
            for i, (tone, vag_no) in enumerate(tones):
                struct.pack_into('<hh', tone, 0x14, target, vag_no)
                block[32 * i:32 * i + 32] = tone
            self.vh[0x20 + 16 * target] = count
            self.vh[0x20 + 16 * target + 1:0x20 + 16 * target + 16] = attrs
            self.vh = (self.vh[:sizes_at] + block + struct.pack('<256H', *sizes))
            self.nprog += 1
        if new_samples:
            self.vb = self.vb[:vb_len] + b''.join(new_samples)
        self.nvag = nvag
        self.ntone += count
        struct.pack_into('<3H', self.vh, 0x12, self.nprog, self.ntone, self.nvag)
        struct.pack_into('<I', self.vh, 0x0C, len(self.vh) + len(self.vb))
        return target, k


def _not_copyable(rec, multi_tone=True):
    """Why a record cannot be copied into another set, or None. Tone count 0: PlaySound plays
    nothing for it in the original game either (blez at 0x8004A264); seq >= 0: it plays a
    sequence, not tones."""
    if rec[10] <= 0:
        return 'it plays nothing in the original game (tone count 0: PlaySound returns at 0x8004A264)'
    if rec[10] > 1 and not multi_tone:
        return f'it plays {rec[10]} tones (multi-tone sounds are copied with "Expand Sound Space")'
    if rec[5] != -1:
        return f'it is a sound sequence (record +0x0A = {rec[5]}), which this copy does not carry'
    return None


def needed(exe, wants):
    """[(set, sound, map, source set)] for {map: sound ids} (or {map: {sound: (priority,
    source set)}}) that the map's sets cannot play, lowest priority first (authored sounds
    before class sounds). The source set picks which per-set copy of the sound is copied
    (a class's home room set); None: the first set that has it."""
    rows = []
    for m, ids in wants.items():
        info = ids if isinstance(ids, dict) else {n: (0, None) for n in ids}
        for n, v in info.items():
            prio, src = v if isinstance(v, tuple) else (v, None)
            rows.append((prio, m, n, src))
    out, seen = [], set()
    for prio, m, n, src in sorted(rows, key=lambda r: (r[0], r[1], r[2])):
        banks = banks_of(exe, n)
        if banks is None:
            continue
        for s in sorted(map_sets(exe, m)):
            if s not in banks and (s, n) not in seen:
                seen.add((s, n)); out.append((s, n, m, src if src in banks else None))
    return out


STOCK_CAP = 80256   # the largest stock map set's samples (sets 0..76)
# {map: [(sound id, record)]}: the own-set records apply() put in each map's data; written into
# the map's section 3 by install_map_tables (mod_export) - native_map_sound_table
MAP_TABLES = {}
# {map: factor}: maps where Melzas's speed setting also shortens his waits (set by mod_export)
AI_SPEED = {}
OWNERS = {}   # (map, sound) -> names of the placed classes / events that play it (for warnings)


def _owner(m, n, name):
    if name:
        OWNERS.setdefault((m, n), set()).add(name)


def _who(maps, n):
    names = sorted(set().union(*[OWNERS.get((m, n), set()) for m in maps]))
    return f" of {', '.join(names)}" if names else ''


def apply(exe, sound, wants, names=None, extended=False, own=None, record_gap=0x800, vh_limit=None, multi_tone=False):
    """(exe, sound.bin, report, warnings): the sets of maps in `wants` gain the map-only
    sounds they play, in order, while the set's samples stay within the cap (stock
    maximum 80,256 bytes; with `extended`, up to the reverb area). Sounds that do not
    fit, or find no spare record, are left out with a warning."""
    names = names or {}
    vh_cap = vh_limit or VH_LIMIT
    todo = needed(exe, wants)
    own = {m: v for m, v in (own or {}).items() if any(banks_of(exe, n) for n in v)}
    if not todo and not own:
        return exe, sound, [], []
    old_exe, old_sound = bytes(exe), bytes(sound)
    exe = bytearray(exe); sound = bytearray(sound); report = []; warnings = []
    MAP_TABLES.clear(); own_lines = []
    cap = SPU_LIMIT - SPU_BASE if extended else STOCK_CAP
    free = [i for i in FREE_RECORDS if record(exe, i)[0] == -2 and not any(record(exe, k)[6] == i for k in range(963))]
    newrecs = []                 # [record words]; index = key
    tail = {}                    # sound -> ('stock', id) | ('new', key): where its chain ends now
    by_set = {}
    for s, n, m, src in todo:
        by_set.setdefault(s, []).append((n, m, src))
    rewritten = set(); links = []
    by_set_maps = {m for _, _, m, _ in todo}
    for s in sorted(by_set, reverse=True):   # highest set first: lower offsets stay valid
        h, b, e = _set_range(exe, s)
        vab = _Vab(sound[h:b], sound[b:e]); added = False; base = vab.nprog
        for n, m, want_src in by_set[s]:
            label = f"sound {n} ({names.get(n) or 'map-only sound'}){_who([m], n)} on map {m}"
            src_id = next((i for i in chain(exe, n) if record(exe, i)[0] == want_src), None) if want_src is not None else None
            if src_id is None:
                src_id = next(i for i in chain(exe, n) if record(exe, i)[0] >= 0)
            src_rec = record(exe, src_id)
            why = _not_copyable(src_rec, multi_tone)
            if why:
                warnings.append(f"{label} not added: {why}"); continue
            sh, sb, se = _set_range(exe, src_rec[0])
            src = _Vab(sound[sh:sb], sound[sb:se])
            trial = _Vab(bytes(vab.vh), bytes(vab.vb))
            try:
                prog, slot = trial.add_tone(src, src_rec[1], src_rec[2], base, src_rec[10])
            except SoundSetError as err:
                warnings.append(f"{label} not added: {err}"); continue
            size = len(trial.vb)   # sample bytes; the disc copy (sector padded) is what is sent
            if len(_pad(trial.vb)) > SPU_LIMIT - SPU_BASE:
                warnings.append(f"{label} not added: sound set {s} would reach the reverb area ({len(_pad(trial.vb))} bytes sent, limit {SPU_LIMIT - SPU_BASE})"); continue
            if len(_pad(trial.vh)) > vh_cap:
                warnings.append(f"{label} not added: sound set {s} header would be {len(trial.vh)} bytes (limit {vh_cap})"); continue
            if size > cap:
                warnings.append(f"{label} not added: sound set {s} would need {size} bytes of sound memory (limit {cap})"); continue
            vab = trial; added = True
            rec = list(src_rec); rec[0] = s; rec[1] = prog; rec[2] = slot; rec[6] = 0
            # the record goes into the map's own data too (native_map_sound_table), not below the code
            MAP_TABLES.setdefault(m, []).append((n, rec))
            own_lines.append(f"Map {m}: sound set {s} now also holds {label.split(' on map')[0]} (record in the map's data)")
            if size > STOCK_CAP:
                warnings.append(f"Map {m}: sound set {s} uses {size} bytes of sound memory, more than any stock set ({STOCK_CAP})")
        if not added:
            continue
        rewritten.add(s)
        new = _pad(vab.vh) + _pad(vab.vb)
        delta = len(new) - (e - h)
        sound[h:e] = new
        a, words = _offsets(exe)
        nb = h + len(_pad(vab.vh))
        words = [nb if w == b and w > h else (w + delta if w >= e else w) for w in words]
        struct.pack_into(f'<{len(words)}I', exe, a, *words)
    # project maps' own sets (user 2026-10-23): a new set per new map holding only the
    # set-bound sounds that map plays, appended after the last byte of SOUND.BIN
    own_sets = {}; appended = 0
    stock_len = len(sound)
    def pick(n, want_src):
        banks = banks_of(exe, n) or set()
        ids_ = chain(exe, n)
        src_id = next((i for i in ids_ if record(exe, i)[0] == want_src), None) if want_src in banks else None
        return src_id if src_id is not None else next((i for i in ids_ if record(exe, i)[0] >= 0), None)

    _samples = {}

    def sample_of(n, want_src):
        """(sha1, length) of the sample the copy of n would bring (shared when equal)."""
        i = pick(n, want_src)
        if i is None:
            return None
        if i not in _samples:
            r = record(exe, i); sh, sb, se = _set_range(exe, r[0])
            try:
                src = _Vab(sound[sh:sb], sound[sb:se])
                tone = src.vh[src.tone_at(r[1], r[2]):src.tone_at(r[1], r[2]) + 32]
                raw = src.vag(struct.unpack_from('<h', tone, 0x16)[0])
                import hashlib
                _samples[i] = (hashlib.sha1(raw).hexdigest(), len(raw))
            except (SoundSetError, struct.error, IndexError):
                _samples[i] = None
        return _samples[i]

    def samples_size(wants_):
        found = {}
        for n, v in wants_.items():
            k = sample_of(n, v[1])
            if k:
                found[k[0]] = k[1]
        return sum(found.values())
    # maps share one own set while their sounds (same per-set copy) fit together: fewer records.
    # A map joins the group it adds the fewest new sounds to (2026-10-23).
    groups = []   # [maps, {sound: (prio, src)}]
    for m in sorted(own):
        mine = {n: v for n, v in own[m].items() if banks_of(exe, n)}
        best = None
        for g in groups:
            merged = dict(g[1])
            if any(n in merged and pick(n, merged[n][1]) != pick(n, v[1]) for n, v in mine.items()):
                continue
            for n, v in mine.items():
                merged[n] = min(merged.get(n, v), v)
            if samples_size(merged) <= cap:
                added = len(set(mine) - set(g[1]))
                if best is None or added < best[0]:
                    best = (added, g, merged)
        if best is not None:
            best[1][0].append(m); best[1][1] = best[2]
        else:
            groups.append([[m], mine])
    for maps, wants_g in groups:
        m = maps[0]
        S = OWN_FIRST + len({v[0] for v in own_sets.values()})
        h, b, e = _set_range(exe, min(map_sets(exe, m)))
        vab = _Vab.empty(sound[h:b])
        rows = sorted(wants_g.items(), key=lambda kv: (kv[1][0], kv[0]))
        for n, (prio, want_src) in rows:
            banks = banks_of(exe, n)
            if not banks:
                continue
            label = f"sound {n} ({names.get(n) or 'map-only sound'}){_who(maps, n)} on map{'s' if len(maps) > 1 else ''} {', '.join(map(str, maps))}"
            ids_ = chain(exe, n)
            src_id = next((i for i in ids_ if record(exe, i)[0] == want_src), None) if want_src in banks else None
            if src_id is None:
                src_id = next(i for i in ids_ if record(exe, i)[0] >= 0)
            src_rec = record(exe, src_id)
            why = _not_copyable(src_rec, multi_tone)
            if why:
                warnings.append(f"{label} not added: {why}"); continue
            sh, sb, se = _set_range(exe, src_rec[0])
            src = _Vab(sound[sh:sb], sound[sb:se])
            trial = _Vab(bytes(vab.vh), bytes(vab.vb))
            try:
                prog, slot = trial.add_tone(src, src_rec[1], src_rec[2], 0, src_rec[10])
            except SoundSetError as err:
                warnings.append(f"{label} not added: {err}"); continue
            size = len(trial.vb)
            if len(_pad(trial.vb)) > SPU_LIMIT - SPU_BASE:
                warnings.append(f"{label} not added: its own sound set would reach the reverb area"); continue
            if len(_pad(trial.vh)) > vh_cap:
                warnings.append(f"{label} not added: its own sound set header would be {len(trial.vh)} bytes (limit {vh_cap})"); continue
            if size > cap:
                warnings.append(f"{label} not added: its own sound set would need {size} bytes (limit {cap})"); continue
            vab = trial
            rec = list(src_rec); rec[0] = S; rec[1] = prog; rec[2] = slot; rec[6] = 0
            # the record goes into each of these maps' own data (native_map_sound_table), not
            # into a chain record below the game code
            for mm in maps:
                MAP_TABLES.setdefault(mm, []).append((n, rec))
            own_lines.append(f"Map{'s' if len(maps) > 1 else ''} {', '.join(map(str, maps))}: own sound set {S} holds {label.split(' on map')[0]} (record in the map's data)")
        if len(vab.vb) > STOCK_CAP:
            warnings.append(f"Map {', '.join(map(str, maps))}: own sound set {S} uses {len(vab.vb)} bytes of sound memory, more than any stock set ({STOCK_CAP})")
        if vab.nprog == 0:
            continue
        h = len(sound); sound += _pad(vab.vh); b = len(sound); sound += _pad(vab.vb)
        for mm in maps:
            own_sets[mm] = (S, h, b)
    for mm in [mm for mm in MAP_TABLES if mm >= 483 and mm not in own_sets and mm not in by_set_maps]:
        del MAP_TABLES[mm]
    appended = len(sound) - stock_len
    if not rewritten and not own_sets:
        return old_exe, old_sound, [], warnings
    # record ids: the proven-spare stock slots first, then a prepended block (chain-only
    # records below the table: ids are negative; PlaySound's chain walk 0x8004A3D4 /
    # 0x80049AF8 only stops on 0 and indexes base + id * 0x16 with signed halfwords)
    ids = [free.pop(0) if free else None for _ in newrecs]
    extra = [k for k, i in enumerate(ids) if i is None]
    table = _own_table(exe, own_sets, stock_len, len(sound)) if own_sets else None
    table_at = None
    code = None
    if MAP_TABLES:
        import native_map_sound_table as nmst
        nmst.verify(exe, struct.unpack_from('<I', exe, 0x18)[0])
        code = nmst.emit()
        table = (table or b'') + bytes((-len(table or b'')) % 4) + code
    speed_at = None
    if AI_SPEED:   # Melzas's speed setting: his waits too (native_ai_speed); fixed code + map list
        import native_ai_speed as nas
        nas.verify(exe, struct.unpack_from('<I', exe, 0x18)[0])
        table = (table or b'') + bytes((-len(table or b'')) % 4)
        speed_at = len(table)
        table = table + nas.emit_all(0) + nas.map_list(AI_SPEED)
    if extra or table:
        exe, first, table_at = _prepend_records(exe, len(extra), table, record_gap)
        load = struct.unpack_from('<I', exe, 0x18)[0]
        if code is not None:
            code_at = table_at + (speed_at if speed_at is not None else len(table)) - len(code)
            exe = nmst.patch(exe, load, code_at)
        if speed_at is not None:
            wrapper = table_at + speed_at; blob = nas.emit_all(wrapper + len(nas.emit_all(0)))
            exe[wrapper - load + 0x800:wrapper - load + 0x800 + len(blob)] = blob
            exe = nas.patch(exe, load, wrapper)
        for j, k in enumerate(extra):
            ids[k] = first + j
    for kind, at, key in links:
        where = at if kind == 'stock' else ids[at]
        if kind == 'new':
            newrecs[at][6] = ids[key]
        else:
            struct.pack_into('<h', exe, _f(exe, REC) + REC_SIZE * where + 0x0C, ids[key])
    for key, rec in enumerate(newrecs):
        struct.pack_into('<11h', exe, _f(exe, REC) + REC_SIZE * ids[key], *rec)
    if own_sets:
        exe = _install_own_sets(exe, own_sets, table_at)
    lines = [f"Map {m}: sound set {s} now also holds {what} (record {ids[key]})" for m, s, what, key in report] + own_lines
    verify(old_exe, old_sound, bytes(exe), bytes(sound[:stock_len]), rewritten)
    verify_records(old_exe, bytes(exe), {at for kind, at, _ in links if kind == 'stock'}, {i for i in ids if 0 <= i < 963})
    return bytes(exe), bytes(sound), lines, warnings


OWN_FIRST = 78   # first own set; 77 is a never-used filler whose header word is set 76's end
LOADER_BASE = (0x80049854, 0x3C11800B, 0x80049858, 0x26319B9C)   # lui s1,0x800B / addiu s1,s1,-0x6464


def _own_table(exe, own_sets, stock_len, total):
    """Set table words for the loader 0x80049820: stock sets 0-76 unchanged, filler 77,
    own sets 78.. (each set's end is the next set's header word)."""
    a, words = _offsets(exe)
    k = (SET_TABLE - OFFSETS) // 4
    table = list(words[k:k + 2 * 77 + 1])            # h0,b0 .. h76,b76, h77 (= end of set 76)
    table.append(stock_len)                           # b77: filler
    order = sorted(set(own_sets.values()))
    if [S for S, _, _ in order] != list(range(OWN_FIRST, OWN_FIRST + len(order))):
        raise SoundSetError('own sound sets are not numbered in order')
    for S, h, b in order:
        table += [h, b]
    table.append(total)
    return struct.pack(f'<{len(table)}I', *table)


def _install_own_sets(exe, own_sets, table_at):
    """Point the map-set loader at the new table; each project map's table entry -> its set."""
    va1, w1, va2, w2 = LOADER_BASE
    if struct.unpack_from('<2I', exe, _f(exe, va1)) != (w1, w2) or va2 != va1 + 4:
        raise SoundSetError('Map sound-set loader differs from the verified game code')
    hi = (table_at + 0x8000) >> 16; lo = (table_at - (hi << 16)) & 0xFFFF
    struct.pack_into('<2I', exe, _f(exe, va1), 0x3C110000 | hi, 0x26310000 | lo)
    hi_t = struct.unpack_from('<I', exe, _f(exe, 0x8004B0DC))[0] & 0xFFFF
    lo_t = struct.unpack_from('<h', exe, _f(exe, 0x8004B0E4))[0]
    mt = (hi_t << 16) + lo_t
    if mt == 0x800C8B90 and max(own_sets) >= 483:
        raise SoundSetError('New maps have no relocated map sound-set table')
    for m, (S, _, _) in own_sets.items():
        struct.pack_into('<i', exe, _f(exe, mt) + 4 * m, S)
    return exe


def _prepend_records(exe, count, table=None, gap=0x800):
    """One prepended block (editor prepend convention: bytes inserted before the module,
    load address lowered, 0x800 gap kept, native stack moved below by
    native_injection_stack.protect) holding `count` records and the optional set table.
    Returns (exe, first record id, table address)."""
    from native_injection_stack import protect
    load, size = struct.unpack_from('<II', exe, 0x18)
    tlen = len(table or b'')
    need = tlen + 4 + count * REC_SIZE + REC_SIZE
    # gap: the editor prepend convention leaves 0x800 unused bytes after the block; the test
    # option "More sound records" (packed_sound_records, off by default) uses 0 here - the
    # stack is below every prepended block (native_injection_stack.protect) and the gap below
    # the stock code (editor_qol prefix) stays. Evidence: docs/2026-10-23-self-contained-classes.txt
    expansion = (need + gap + 0x7FF) & ~0x7FF
    new_load = load - expansion
    from native_injection_stack import STACK_FLOOR
    if new_load < STACK_FLOOR:
        raise SoundSetError(f'No room below the game code for {count} more sound records (needs {need} bytes; code starts at {load:08X})')
    table_at = new_load if table else None
    start = new_load + ((tlen + 3) & ~3)
    first_addr = start + (-(start - REC)) % REC_SIZE
    first = (first_addr - REC) // REC_SIZE
    if first < -32768:
        raise SoundSetError('Sound records would be out of reach')
    prefix = bytearray(expansion)
    if table:
        prefix[:tlen] = table
    exe = bytearray(exe); exe[0x800:0x800] = prefix
    struct.pack_into('<II', exe, 0x18, new_load, size + expansion)
    exe, _ = protect(bytes(exe))
    return bytearray(exe), first, table_at


def verify_records(old_exe, exe, tails, spares):
    """Every stock sound id 0..962 keeps its record words, except the chain link of the
    records new copies were appended to and the spare slots that were filled."""
    for n in range(963):
        if n in spares:
            continue
        a, b = record(old_exe, n), record(exe, n)
        if n in tails:
            a[6] = b[6] = 0
        if a != b:
            raise SoundSetError(f'Sound record {n} changed')


def verify(old_exe, old_sound, exe, sound, rewritten):
    """Every set and music piece in the offset list holds the same bytes as before,
    except the rewritten sets (whose VH is a VAB); the list ends at the file size."""
    _, old = _offsets(old_exe); _, new = _offsets(exe)
    if new[-1] != len(sound) or any(b < a for a, b in zip(new, new[1:])):
        raise SoundSetError('Sound file offsets no longer match the rebuilt sound file')
    changed = set()
    for s in rewritten:
        k = (SET_TABLE - OFFSETS) // 4 + 2 * s
        changed |= {k, k + 1}
        if sound[new[k]:new[k] + 4] != b'pBAV':
            raise SoundSetError(f'Sound set {s} does not start with its header')
    for i in range(len(old) - 1):
        if i in changed:
            continue
        if old_sound[old[i]:old[i + 1]] != sound[new[i]:new[i + 1]]:
            raise SoundSetError(f'Sound file piece {i} moved without its bytes')


PLAY_TYPES = ('play_sound', 'play_sound_volume', 'native_play_sound')


def project_wants(session, stock, exe=None):
    """{map: BD sound ids} of the project's maps that their stock scripts do not play."""
    OWNERS.clear()
    if exe is None:
        from pathlib import Path
        exe = (Path(__file__).resolve().parents[1] / 'private-inputs/disc/ALUN_CD.EXE').read_bytes()
    from event_editor import script_roots, instructions
    doc = getattr(session, 'content_database', None) or {}
    maps = {g.get('map_id') for g in doc.get('event_graphs') or [] if type(g.get('map_id')) is int}
    slots = doc.get('new_map_slots') or {}

    def ids(sess, m):
        out = set()
        try:
            roots = script_roots(sess, m)
        except Exception:
            return out
        for key in roots:
            try:
                rows = instructions(sess, m, key, reachable=True)
            except Exception:
                continue
            for off, op, size in rows:
                if op == 0xBD and size >= 3:
                    out.add(struct.unpack_from('<H', sess.data, off + 1)[0])
        return out
    def walk(v):
        if isinstance(v, dict):
            yield v
            for x in v.values():
                yield from walk(x)
        elif isinstance(v, list):
            for x in v:
                yield from walk(x)
    definitions = {d.get('id'): d for d in doc.get('definitions') or []}
    authored = {}   # Play Sound commands, and the spawn sounds of the classes placed there
    placed = {}     # the placed classes' own set-bound sounds
    for g in doc.get('event_graphs') or []:
        m = g.get('map_id')
        if type(m) is not int:
            continue
        for row in walk(g):
            if row.get('type') in PLAY_TYPES and type(row.get('sound_id')) is int:
                authored.setdefault(m, set()).add(row['sound_id'])
        for p in g.get('pages') or []:
            for row in walk(definitions.get(p.get('class_id', g.get('class_id'))) or {}):
                if type(row.get('spawn_sound')) is int:
                    authored.setdefault(m, set()).add(row['spawn_sound'])
        # the placed class's own set-bound sounds: its animations' sounds and the scripts of
        # its copy in its home room (object_sound_banks.class_sounds, 2026-10-15)
        for n, src in class_sounds_of(g, definitions, exe).items():
            placed.setdefault(m, {}).setdefault(n, src)
    wants = {}
    for m in sorted(maps):
        base = m if m < 483 else (slots.get(str(m)) or {}).get('copied_from')
        own = ids(stock, base) if type(base) is int and 0 <= base < 483 else set()
        extra = {n: (2, src) for n, src in placed.get(m, {}).items()}
        extra.update({n: (1, None) for n in ids(session, m) - own})
        extra.update({n: (0, None) for n in authored.get(m, ())})
        if extra:
            wants[m] = extra
    return wants


def class_sounds_of(g, definitions, exe=None):
    """Set-bound sounds of the game classes an event places (enemies, bosses, objects, NPCs):
    the home room is the event's donor map, the class's fixed donor, or its first stock room."""
    import object_sound_banks as osb
    out = {}
    for p in g.get('pages') or []:
        d = definitions.get(p.get('class_id', g.get('class_id'))) or {}
        c = d.get('source', {}).get('catalogue_index')
        if type(c) is not int or d.get('source', {}).get('variant') and d['source']['variant'] not in ('demon', 'push_stool'):   # the stool plays its home room's push sound
            continue
        home = (g.get('native_placement') or {}).get('donor_map_id')
        fixed = d.get('source', {}).get('fixed_donor')
        if type(home) is not int and isinstance(fixed, list) and fixed:
            home = fixed[0]
        if type(home) is not int:
            try:
                home = osb._first_home(c)
            except Exception:
                home = None
        if type(home) is int and 0 <= home < 483:
            ent = (g.get('native_placement') or {}).get('donor_entity_index')
            ids = set(osb.class_sounds(c, home, ent if type(ent) is int and home == (g.get('native_placement') or {}).get('donor_map_id') else None))
            src = None
            if exe is not None:
                ids |= {n for n in native_class_sounds(exe, c, home) if banks_of(exe, n)}
                src = home_sound_set(exe, c, home)   # the home room's set
            for n in ids:
                out.setdefault(n, src)
                _owner(g.get('map_id'), n, d.get('name'))
    return out


PLAY_FUNCS = (0x8004A128, 0x80049A68)   # PlaySound, and its set-checking caller (0x80049A68 -> jal 0x8004A128)
BUILTIN_TABLES = {'A': 0x800C699C, 'C': 0x800C6D9C, 'D': 0x800C719C, 'E': 0x800C759C, 'F': 0x800C799C}  # 0x80039198


def _writes_a0(w):
    """The MIPS word writes register a0 (I-type rt, R-type rd)."""
    op = w >> 26
    if op == 0:
        return (w >> 11) & 31 == 4 and w & 0x3F not in (8, 0x18, 0x19, 0x1A, 0x1B, 0x11, 0x13)
    return op in (8, 9, 10, 11, 12, 13, 14, 15, 32, 33, 34, 35, 36, 37, 38) and (w >> 16) & 31 == 4


def _function_sounds(exe, start, depth=2, seen=None):
    """Constant sound ids a native function (and the functions it calls, `depth` levels)
    passes to PlaySound: `addiu/ori a0,zero,n` within the 6 words before a jal to
    PLAY_FUNCS or in its delay slot. Stops at the first `jr ra`."""
    seen = set() if seen is None else seen
    if start in seen or not 0x80010000 <= start < 0x800C0000:
        return set()
    seen.add(start)
    out = set(); load = struct.unpack_from('<I', exe, 0x18)[0]
    words = []
    a = start
    for _ in range(4000):
        o = a - load + 0x800
        if not 0x800 <= o < len(exe) - 4:
            break
        w = struct.unpack_from('<I', exe, o)[0]; words.append((a, w)); a += 4
        if w == 0x03E00008:
            o = a - load + 0x800; words.append((a, struct.unpack_from('<I', exe, o)[0])); break
    def a0_const(w):
        if w >> 16 in (0x2404, 0x3404):   # addiu a0,zero,n / ori a0,zero,n
            return w & 0xFFFF
        return None
    for i, (va, w) in enumerate(words):
        if w >> 26 != 3:
            continue
        target = (va & 0xF0000000) | ((w & 0x03FFFFFF) << 2)
        if target in PLAY_FUNCS:
            # the delay slot, else the last write to a0 within 16 words (no call in between):
            # Melzas's C program sets a0 = 295 13 words before its jal (0x8007C798 -> 0x8007C7CC)
            n = a0_const(words[i + 1][1]) if i + 1 < len(words) else None
            if n is None and not (i + 1 < len(words) and _writes_a0(words[i + 1][1])):
                for _, x in reversed(words[max(0, i - 16):i]):
                    if x >> 26 in (2, 3) or x & 0xFC00003F == 9:   # j/jal/jalr: a0 unknown
                        break
                    if _writes_a0(x):
                        n = a0_const(x)
                        break
            if n is not None:
                out.add(n)
        elif depth > 0 and target not in (0x8004A7B4, 0x8004A928):
            out |= _function_sounds(exe, target, depth - 1, seen)
    return out


_STOCK = []


def _stock_exe():
    """The stock ALUN_CD.EXE (class code is scanned there: a build's executable has patched
    call sites, e.g. Melzas's), or None."""
    if not _STOCK:
        from pathlib import Path
        try:
            _STOCK.append((Path(__file__).resolve().parents[1] / 'private-inputs/disc/ALUN_CD.EXE').read_bytes())
        except OSError:
            _STOCK.append(None)
    return _STOCK[0]


def native_class_sounds(exe, catalogue, home):
    """native built-in sound ids of a class in room home: the class capture's (taken from the
    original game, class_capture.py) when it has that room, else read now."""
    try:
        import class_capture
        h = class_capture.home(catalogue, home)
        if h is not None and 'native' in h:   # plus a fresh scan: captures predate the a0 tracking
            return set(h['native']) | _native_class_sounds(_stock_exe() or exe, catalogue, home)
    except Exception:
        pass
    return _native_class_sounds(_stock_exe() or exe, catalogue, home)


def home_sound_set(exe, catalogue, home):
    """The sound set of the class's home room in the ORIGINAL game (captured), else the
    table entry of exe."""
    try:
        import class_capture
        hs = class_capture.home_set(catalogue, home)
        if hs is not None:
            return hs
    except Exception:
        pass
    return struct.unpack_from('<i', exe, _f(exe, 0x800C8B90) + 4 * home)[0]


def _native_class_sounds(exe, catalogue, home):
    """Constant sound ids of a class's built-in programs (its sprite header's A/C/D/E/F
    program numbers, remake/assets sprite_headers from DATAS.BIN; table 0x800C699C.. per
    slot, called by 0x80039198)."""
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / 'remake/assets'
    try:
        if catalogue >= 256:
            hdr = json.loads((root / f'maps/{home:03d}/data.json').read_text()).get('sprite_headers', {}).get(str(catalogue))
        else:
            hdr = json.loads((root / 'sprites/global_headers.json').read_text()).get('sprite_headers', {}).get(str(catalogue))
    except (OSError, ValueError):
        return set()
    out = set()
    for slot, n in ((hdr or {}).get('sprite_programs') or {}).items():
        if slot in BUILTIN_TABLES and n:
            f = struct.unpack_from('<I', exe, _f(exe, BUILTIN_TABLES[slot] + 4 * n))[0]
            out |= _function_sounds(exe, f)
    return out


def _script_ids(sess, m):
    from event_editor import script_roots, instructions
    out = set()
    try:
        roots = script_roots(sess, m)
    except Exception:
        return out
    for key in roots:
        try:
            rows = instructions(sess, m, key, reachable=True)
        except Exception:
            continue
        for off, op, size in rows:
            if op == 0xBD and size >= 3:
                out.add(struct.unpack_from('<H', sess.data, off + 1)[0])
    return out


_UNCERTAIN = None


def uncertain_sounds(exe):
    """Set-bound ids the map set may be asked for by code not tied to a placed class: every
    constant PlaySound call in the executable and the animation sounds of the global
    sprites (remake/assets/sprites/global, from DATAS.BIN)."""
    global _UNCERTAIN
    if _UNCERTAIN is None:
        import glob, json
        from pathlib import Path
        load = struct.unpack_from('<I', exe, 0x18)[0]
        n = (len(exe) - 0x800) // 4
        W = struct.unpack_from(f'<{n}I', exe, 0x800)
        ids = set()
        for i, w in enumerate(W):
            if w >> 26 == 3 and (((load + 4 * i) & 0xF0000000) | ((w & 0x3FFFFFF) << 2)) in PLAY_FUNCS:
                for x in W[max(0, i - 6):i + 2][::-1]:
                    if x >> 16 in (0x2404, 0x3404):
                        ids.add(x & 0xFFFF); break
        root = Path(__file__).resolve().parents[1] / 'remake/assets/sprites/global'
        for f in glob.glob(str(root / '**/animations.json'), recursive=True):
            try:
                ids |= {a['sfx'] for a in json.loads(Path(f).read_text()).get('animations', []) if a.get('sfx')}
            except (OSError, ValueError):
                pass
        _UNCERTAIN = {k for k in ids if banks_of(exe, k)}
    return _UNCERTAIN


def own_wants(session, exe):
    """{new map: {sound: (priority, source set)}}: everything set-bound a project map can
    play, for its own sound set. (No unowned map-level ids: uncertain_sounds is not used for own sets since 2026-10-23.)"""
    import object_sound_banks as osb
    from entity_records import read_entities
    from map_inspector import inspect_map
    doc = getattr(session, 'content_database', None) or {}
    slots = doc.get('new_map_slots') or {}
    definitions = {d.get('id'): d for d in doc.get('definitions') or []}
    out = {}
    # every room the user made: new slots (483+) and original numbers saved over as new maps
    # (created_maps) - user 2026-10-26: any room they create uses its own set
    made = {int(k) for k in slots} | {m for m in doc.get('created_maps') or [] if type(m) is int}
    for key in sorted(made):
        m = int(key)
        if m < 483 and m not in (doc.get('created_maps') or []):
            continue
        try:
            ents = inspect_map(bytes(session.data), m)['entities']
        except Exception:
            continue
        prev = min(map_sets(exe, m))
        want = {}
        def put(n, prio, src):
            if banks_of(exe, n) and (n not in want or want[n][0] > prio):
                want[n] = (prio, src)
        # (2026-10-23, user: map-level sounds no class owns are not carried into the map's own set;
        # it holds its events' and scripts' sounds and its classes' own sounds)
        source = (slots.get(str(key)) or {}).get('copied_from')
        for e in ents:
            o = int(e['offset'], 16); raw = bytes(session.data[o:o + 20])
            c = raw[6] + (256 if raw[5] & 128 else 0)   # behavior_transplant.py:329
            home = source if type(source) is int else None
            if home is None:
                try:
                    home = osb._first_home(c)
                except Exception:
                    home = None
            for h in (home, osb._first_home(c) if c else None):
                if type(h) is int and 0 <= h < 483:
                    found = set(osb.class_sounds(c, h)) | native_class_sounds(exe, c, h)
                    if found:
                        hs = home_sound_set(exe, c, h)
                        try:
                            import class_capture
                            who = (class_capture.entry(c) or {}).get('name')
                        except Exception:
                            who = None
                        for n in found:
                            put(n, 2, hs)
                            if banks_of(exe, n):
                                _owner(m, n, who)
                        break
        for n in _script_ids(session, m):
            put(n, 1, prev)
        for g in doc.get('event_graphs') or []:
            if g.get('map_id') != m:
                continue
            for n, src in class_sounds_of(g, definitions, exe).items():
                put(n, 2, src)
            stack = [g]
            while stack:
                v = stack.pop()
                if isinstance(v, dict):
                    if v.get('type') in PLAY_TYPES and type(v.get('sound_id')) is int:
                        put(v['sound_id'], 0, None)
                    if type(v.get('spawn_sound')) is int:
                        put(v['spawn_sound'], 0, None)
                    stack.extend(v.values())
                elif isinstance(v, list):
                    stack.extend(v)
            for p in g.get('pages') or []:
                d = definitions.get(p.get('class_id', g.get('class_id'))) or {}
                stack = [d]
                while stack:
                    v = stack.pop()
                    if isinstance(v, dict):
                        if type(v.get('spawn_sound')) is int:
                            put(v['spawn_sound'], 0, None)
                        stack.extend(v.values())
                    elif isinstance(v, list):
                        stack.extend(v)
        if want:
            out[m] = want
    return out


def install_map_tables(data):
    """Append each map's own sound records (MAP_TABLES) to its section 3 (native_map_sound_table):
    sections 4-6 move down inside the map's own block, into its zero padding (text offsets are
    relative to the text section). Returns (data, warnings); a map without room keeps none."""
    import native_map_sound_table as nmst
    from map_slots import offsets
    data = bytearray(data); warnings = []
    values = offsets(data)
    for m, rows in sorted(MAP_TABLES.items()):
        b = values[m]; size = values[m + 1] - b
        block = bytes(data[b:b + size])
        h = list(struct.unpack_from('<7I', block, 0))
        blob = nmst.table(m, rows)
        used = len(block.rstrip(bytes(1))); used += (-used) % 4
        if used + len(blob) > size:
            # the block grows by whole 2048-byte steps (the CD reader's alignment); later maps
            # move down, nothing else of them changes
            from map_slots import serialize
            from map_loader_constraints import STOCK_MAX_MAP_BYTES
            grow = (used + len(blob) - size + 2047) & ~2047
            if size + grow > STOCK_MAX_MAP_BYTES:
                warnings.append(f"Map {m}: no room for {len(rows)} sound records within the largest map size; its own-set sounds stay silent")
                continue
            end = values[-1]; tail = bytes(data[end:])
            data = bytearray(data[:b + size]) + bytes(grow) + data[b + size:end]
            values = [v + grow if i > m else v for i, v in enumerate(values)]
            data = serialize(data, values) + tail
            size += grow
        new = bytearray(block[:h[4]] + blob + block[h[4]:used])
        for i in (4, 5, 6):
            h[i] += len(blob)
        struct.pack_into('<7I', new, 0, *h)
        data[b:b + size] = bytes(new) + bytes(size - len(new))
    return bytes(data), warnings
