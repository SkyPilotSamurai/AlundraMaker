"""Sound sets for maps the project made (user 2026-10-15: objects play the wrong sound).

Many sounds belong to a map's own sound set: the game's PlaySound (0x8004A128)
follows a sound's record chain (+0x0C) to the record made for the bank the current
map loaded (0x800C8B90[map]); with none, nothing - or not that object's sound -
plays. A game object's animation sounds (anim set tail, played as the animation
starts) and its scripts' sounds are mostly in its home room's set: the Spiky Floor
(sound 114: sets 10 / 15 / 16, 138: 12 / 14 / 15 / 16 / 46 / 48 / 50) is silent or
wrong in a new map that has the template's set 0.

For each new map (483+) without a boss (bosses already choose their home set), the
editor counts, for every game object / enemy / NPC placed there, the set-bound
sounds of its home room, and gives the map the set that plays the most of them, if
that is more than its own set plays. Stock maps keep their own set."""
import json, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / 'private-inputs/disc/ALUN_CD.EXE'
SOUND_REC, SOUND_COUNT = 0x800AA150, 0x80026848
_RECORDS = None
REPORT = []


def records():
    global _RECORDS
    if _RECORDS is None:
        _RECORDS = {}
        try:
            d = EXE.read_bytes(); t = struct.unpack_from('<I', d, 0x18)[0]
            f = lambda va: va - t + 0x800
            count = struct.unpack_from('<i', d, f(SOUND_COUNT))[0]
            for n in range(count + 1):
                r = struct.unpack_from('<11h', d, f(SOUND_REC) + 0x16 * n)
                _RECORDS[n] = (r[0], r[6])
        except (OSError, struct.error):
            pass
    return _RECORDS


def banks_of(n):
    """Sets a sound id plays in, or None for a global (any set) / no-sound id."""
    rec = records()
    out, seen = set(), set()
    while n in rec and n not in seen:
        seen.add(n); bank, nxt = rec[n]
        if bank in (-1, -2):
            return None
        out.add(bank)
        if not nxt:
            break
        n = nxt
    return out or None


def _script_sounds(code_hex):
    from event_editor import SIZES
    b = bytes.fromhex(code_hex); p = 0; out = []
    while p < len(b):
        op = b[p]; size = SIZES.get(op)
        if not size:
            break
        if op in (0xBD, 0xBE, 0xBF) and p + 2 < len(b):
            out.append(b[p + 1] | b[p + 2] << 8)
        p += size
    return out


_SOUNDS = None


def _sound_cache():
    """{"catalogue:home": [sound ids]} remembered on disk (the object library and
    the game's sound records never change; reading them took seconds per build)."""
    global _SOUNDS
    if _SOUNDS is None:
        try:
            _SOUNDS = json.loads(_cache_path().read_text())
        except (OSError, ValueError):
            _SOUNDS = {}
    return _SOUNDS


def _cache_path():
    import hashlib
    try:
        stamp = hashlib.sha1((ROOT / 'private-inputs/object-library/index.json').read_bytes()).hexdigest()[:12]
    except OSError:
        stamp = 'none'
    return ROOT / 'private-inputs/editor-cache' / f'object-sounds-v2-{stamp}.json'


def class_sounds(catalogue, home, entity=None):
    """Set-bound sound ids of a game class in its home room: its animation sounds and the
    programs of ITS OWN placement there (its A-F hooks: entity, or the room's home placement,
    home_entity) - never other entities' or the room's programs (user 2026-10-23). From the
    class capture (class_capture.py: taken once from the original game) when it has this room,
    else read and remembered."""
    try:
        import class_capture
        h = class_capture.home(catalogue, home)
        if h is not None and 'list' in h and entity in (None, h.get('entity')):
            # plus its animation sounds read now: captures used the wrong +0x100 byte (2026-10-26)
            return list(h['list']) + ([n for n in _class_sounds_split(catalogue, home, 'animation') if n not in h['list']] if catalogue == 418 else [])
    except Exception:
        pass
    cache = _sound_cache(); key = f'{catalogue}:{home}' + ('' if entity is None else f':{entity}')
    if key in cache:
        return list(cache[key])
    found = _class_sounds(catalogue, home, entity)
    cache[key] = found
    try:
        path = _cache_path(); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache))
    except OSError:
        pass
    return list(found)


def _class_sounds(catalogue, home, entity=None, data=None):
    return (_class_sounds_split(catalogue, home, 'animation')
            + _class_sounds_split(catalogue, home, 'script', entity, data))


_STOCK = []


def _stock_data():
    """The original DATAS.BIN (object library, else the disc copy), read once."""
    if not _STOCK:
        import object_library
        data = object_library.original_data() if object_library.available() else None
        _STOCK.append(data if data is not None else (ROOT / 'private-inputs/disc/DATA/DATAS.BIN').read_bytes())
    return _STOCK[0]


def home_entity(catalogue, home, data=None):
    """The class's own placement in room home: the first one with no entity hooks (A-F all 0),
    else the first one; None when the room does not place it."""
    import object_library
    from map_inspector import inspect_map
    info = object_library.object_info(catalogue) or {}
    idx = sorted(p[1] for p in info.get('placements', []) if p[0] == home)
    if not idx:
        return None
    try:
        ents = inspect_map(data if data is not None else _stock_data(), home)['entities']
        return next((i for i in idx if not any(ents[i]['programs'].values())), idx[0])
    except Exception:
        return idx[0]


def _class_sounds_split(catalogue, home, origin, entity=None, data=None):
    """Set-bound sounds of one origin: 'animation' (its animation set's sounds in the home
    room) or 'script' (the programs of its own placement there), in order, with repeats."""
    out = []
    if origin == 'animation':
        # The game's rule (0x8003949C): sound = set byte +0x0C, + 0x100 when bit 0x20 of byte
        # +0x0D (the acceleration/anim-flags byte) is set. Melzas's hurt animation 7: 36 -> 292.
        # (remake animations.json and anim_tails.py test the +0x0B flags byte instead.)
        try:
            if catalogue != 418:
                raise LookupError('old reading')
            from editor_session import EditSession
            from animation_preview import animation_reader
            _, sets = animation_reader(EditSession.readonly(bytes(data if data is not None else _stock_data())), home, catalogue)
            # only Melzas (418) for now (user 2026-10-26: add only what was asked; other classes keep
            # the old reading until asked)
            out += [st.tail[2] + (0x100 if st.tail[3] & 0x20 else 0) for st in sets if st.tail[2]]
        except Exception:
            try:
                meta = json.loads((ROOT / f'remake/assets/maps/{home:03d}/sprites/{catalogue}/animations.json').read_text())
                out += [a.get('sfx') for a in meta.get('animations', []) if a.get('sfx')]
            except (OSError, ValueError, TypeError):
                pass
        return [n for n in out if banks_of(n)]
    try:
        import object_library
        from map_inspector import inspect_map
        info = object_library.object_info(catalogue) or {}
        if entity is None:
            entity = home_entity(catalogue, home, data)
        if entity is None:
            return []
        hooks = inspect_map(data if data is not None else _stock_data(), home)['entities'][entity]['programs']
        if not any(hooks.values()):
            return []   # a placement without hooks runs no map program
        # the variant of exactly this placement, else the variant with the same hooks in this room
        rows = [v for v in info.get('variants', []) if v.get('donor_map') == home]
        v = next((v for v in rows if v.get('entity_index') == entity), None)
        if v is None:
            v = next((v for v in rows if all((int(v['hooks_hex'][2 * k:2 * k + 2], 16) or 0) == (hooks.get(b) or 0)
                                             for k, b in enumerate('ABCDEF'))), None)
        for prog in ((v or {}).get('programs') or {}).values():
            if prog.get('code_hex'):
                out += _script_sounds(prog['code_hex'])
    except Exception:
        pass
    return [n for n in out if banks_of(n)]


_HOMES = {}


def _first_home(c):
    """The class's home room: the first stock room where a placement has no entity hooks
    (A-F all 0, active by default; e.g. Roper: map 337/338 copies wait on castle scripts,
    351 ones are active, user 2026-10-23), else the first room with a placement."""
    if c not in _HOMES:
        try:
            import class_capture
            captured = class_capture.active_home(c)
        except Exception:
            captured = None
        if captured is not None:   # captured from the original game (class_capture.py)
            _HOMES[c] = None if captured == -1 else captured
            return _HOMES[c]
        import object_library
        info = object_library.object_info(c) or {}
        places = sorted((p[0], p[1]) for p in info.get('placements', []))
        _HOMES[c] = places[0][0] if places else None
        try:
            from map_inspector import inspect_map
            data = (ROOT / 'private-inputs/disc/DATA/DATAS.BIN').read_bytes()
            for m, i in places:
                if not any(inspect_map(data, m)['entities'][i]['programs'].values()):
                    _HOMES[c] = m; break
        except Exception:
            pass
    return _HOMES[c]


def choose(document, sfx, current, taken, stock_maps=483):
    """{new map: set} for maps without a boss whose objects play more sounds in
    another set; REPORT lists what still cannot sound right."""
    del REPORT[:]
    import object_library
    definitions = {r.get('id'): r for r in (document or {}).get('definitions') or []}
    wants = {}
    for g in (document or {}).get('event_graphs') or []:
        m = g.get('map_id')
        if type(m) is not int or m < stock_maps or m in taken:
            continue
        d = definitions.get((g.get('pages') or [{}])[0].get('class_id', g.get('class_id'))) or {}
        c = d.get('source', {}).get('catalogue_index')
        if type(c) is not int or d.get('source', {}).get('variant') and d['source']['variant'] not in ('demon', 'push_stool'):   # the stool plays its home room's push sound
            continue
        home = (g.get('native_placement') or {}).get('donor_map_id')
        fixed = d.get('source', {}).get('fixed_donor')
        if type(home) is not int and isinstance(fixed, list) and fixed:
            home = fixed[0]
        if type(home) is not int:
            home = _first_home(c)
        if type(home) is not int or not 0 <= home < len(sfx):
            continue
        for n in class_sounds(c, home):
            wants.setdefault(m, []).append((n, d.get('name')))
    chosen = {}
    for m, sounds in wants.items():
        own = current.get(m, 0)
        candidates = {b for n, _ in sounds for b in banks_of(n)} | {own}
        score = lambda b: sum(b in banks_of(n) for n, _ in sounds)
        best = max(sorted(candidates), key=lambda b: (score(b), b == own))
        if score(best) > score(own):
            chosen[m] = best
        lost = sorted({name for n, name in sounds if chosen.get(m, own) not in banks_of(n)})
        if lost:
            REPORT.append(f"Map {m}: sound set {chosen.get(m, own)}; some sounds of {', '.join(lost)} belong to another set")
    return chosen
