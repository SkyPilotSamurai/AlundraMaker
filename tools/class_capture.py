"""Self-contained database classes (user 2026-10-23: "I want the extracted data used for default
building of database events, not needing to keep the maps on which they are originally on").

One capture per game class, taken once from the ORIGINAL game (the object library's map blocks,
the stock ALUN_CD.EXE and DATA/SOUND.BIN) and kept in private-inputs/object-library/classes.json
(private, regenerable; sound samples in private-inputs/object-library/sounds/SHA1.vag):

  maps          every stock map the build may read the class from: its placements, and for a class
                no map places, the map holding its local sprite (behavior_transplant.local_sprite_home)
  active_home   the first stock room where a placement has no entity hooks (A-F all 0), else the
                first room with a placement (object_sound_banks._first_home rule, 2026-10-23)
  homes         per placement map: that room's sound set (stock table 0x800C8B90) and the class's
                set-bound sounds there - animation sounds (remake/assets animations.json, from
                DATAS.BIN), its copy's scripts (BD/BE/BF), native built-in PlaySound constants
                (map_sound_sets._native_class_sounds) - each with the record of the home set's copy,
                its tone (32 bytes) and the sample's sha1 / length

The build reads these instead of the original maps: stock_donors.donor_maps() takes every captured
map of each placed class (so an edited / replaced one is always read from the original), and the
sound collectors (object_sound_banks, map_sound_sets) take homes, sounds and home sets from here.
The map blocks themselves stay the object library's (maps/MMM.blk.gz, byte-for-byte originals):
the compiler copies records, programs, sprites, pages, palettes, spawn templates and effects from
those, so exported bytes are unchanged.

    python tools/class_capture.py build      capture every class (needs the object library)
    python tools/class_capture.py show CCC   print one class's capture
"""
import hashlib, json, struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / 'private-inputs/object-library'
PATH = LIBRARY / 'classes.json'
SOUNDS = LIBRARY / 'sounds'
EXE = ROOT / 'private-inputs/disc/ALUN_CD.EXE'
SOUND_BIN = ROOT / 'private-inputs/disc/DATA/SOUND.BIN'
FORMAT = 'alundra-class-capture-v2'   # v2: script sounds of the class's own placement only
SFX_TABLE = 0x800C8B90
_CACHE = {}


def _sha1(raw):
    return hashlib.sha1(raw).hexdigest()


def load(path=PATH):
    """The capture (dict) when it matches the object library, else None."""
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return None
    hit = _CACHE.get(path)
    if hit and hit[0] == stamp:
        return hit[1]
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    import object_library
    ix = object_library.index(path.parent) or {}
    if value.get('format') != FORMAT or value.get('source_sha256') != ix.get('source_sha256'):
        value = None
    _CACHE[path] = (stamp, value)
    return value


def entry(catalogue, path=PATH):
    cap = load(path)
    return None if cap is None else cap['classes'].get(str(catalogue))


def maps_of(catalogue, path=PATH):
    e = entry(catalogue, path)
    return None if e is None else list(e['maps'])


def active_home(catalogue, path=PATH):
    e = entry(catalogue, path)
    return None if e is None else e.get('active_home', -1)


def home(catalogue, m, path=PATH):
    e = entry(catalogue, path)
    return None if e is None else (e.get('homes') or {}).get(str(m))


def home_set(catalogue, m, path=PATH):
    h = home(catalogue, m, path)
    return None if h is None else h['set']


def sounds(catalogue, m, origins=None, path=PATH):
    """Captured set-bound sound ids of the class in home room m (None: not captured)."""
    h = home(catalogue, m, path)
    if h is None:
        return None
    return [s['id'] for s in h['sounds'] if origins is None or set(s['origins']) & set(origins)]


def _f(exe, va):
    return va - struct.unpack_from('<I', exe, 0x18)[0] + 0x800


def _sound_detail(exe, sound, n, home_set_):
    import map_sound_sets as mss
    ids = mss.chain(exe, n)
    pick = next((i for i in ids if mss.record(exe, i)[0] == home_set_), None)
    if pick is None:
        pick = next((i for i in ids if mss.record(exe, i)[0] >= 0), None)
    if pick is None:
        return None
    rec = mss.record(exe, pick)
    out = dict(id=n, record_id=pick, record=rec, sets=sorted(mss.banks_of(exe, n) or ()))
    try:
        h, b, e = mss._set_range(exe, rec[0])
        vab = mss._Vab(sound[h:b], sound[b:e])
        tone = bytes(vab.vh[vab.tone_at(rec[1], rec[2]):vab.tone_at(rec[1], rec[2]) + 32])
        sample = vab.vag(struct.unpack_from('<h', tone, 0x16)[0])
        out.update(tone_hex=tone.hex(), program_hex=bytes(vab.vh[0x20 + 16 * rec[1]:0x20 + 16 * rec[1] + 16]).hex(),
                   sample_sha1=_sha1(sample), sample_len=len(sample))
        SOUNDS.mkdir(parents=True, exist_ok=True)
        p = SOUNDS / f'{_sha1(sample)}.vag'
        if not p.exists():
            p.write_bytes(sample)
    except Exception as error:   # not a single-tone effect / no VAB: record kept, no sample
        out['sample_error'] = str(error)[:120]
    return out


def capture_class(catalogue, info, stock, exe, sound):
    """One class's capture from the original game data."""
    import object_sound_banks as osb
    import map_sound_sets as mss
    from map_inspector import inspect_map
    places = sorted((p[0], p[1]) for p in (info or {}).get('placements', []))
    maps = sorted({m for m, _ in places})
    active = places[0][0] if places else None
    for m, i in places:
        try:
            if not any(inspect_map(stock, m)['entities'][i]['programs'].values()):
                active = m; break
        except Exception:
            break
    sprite_home = None
    if not maps and catalogue >= 256:
        from behavior_transplant import local_sprite_home
        sprite_home = local_sprite_home(stock, catalogue - 256)
        if sprite_home is not None:
            maps = [sprite_home]
    homes = {}
    for m in maps:
        hs = struct.unpack_from('<i', exe, _f(exe, SFX_TABLE) + 4 * m)[0]
        origins = {}
        for n in osb._class_sounds_split(catalogue, m, 'animation'):
            origins.setdefault(n, []).append('animation')
        ent = osb.home_entity(catalogue, m, stock)
        for n in osb._class_sounds_split(catalogue, m, 'script', ent, stock):
            origins.setdefault(n, []).append('script')
        for n in mss._native_class_sounds(exe, catalogue, m):
            if mss.banks_of(exe, n):   # set-bound only (global ones need nothing)
                origins.setdefault(n, []).append('native')
        rows = []
        for n in sorted(origins):
            d = _sound_detail(exe, sound, n, hs)
            if d is not None:
                d['origins'] = sorted(set(origins[n]))
                rows.append(d)
        native = sorted(mss._native_class_sounds(exe, catalogue, m))
        homes[str(m)] = dict(set=hs, entity=ent, list=osb._class_sounds(catalogue, m, ent, stock), native=native, sounds=rows)
    return dict(catalogue=catalogue, name=(info or {}).get('name'), kind=(info or {}).get('kind'),
                placements=[list(p) for p in places], maps=maps, sprite_home=sprite_home,
                active_home=active, homes=homes)


def build(path=PATH, progress=print):
    import object_library
    ix = object_library.index(path.parent)
    if not (ix and ix.get('complete')):
        raise SystemExit('No complete object library (python tools/object_library.py build)')
    stock = object_library.original_data(path.parent)
    if stock is None:
        raise SystemExit('Object library cannot rebuild the original data')
    exe = EXE.read_bytes(); sound = SOUND_BIN.read_bytes()
    classes = {}
    for k in sorted(ix['objects'], key=int):
        info = object_library.object_info(int(k), path.parent)
        classes[k] = capture_class(int(k), info, stock, exe, sound)
        if int(k) % 50 == 0:
            progress(f'class {k}')
    value = dict(format=FORMAT, source_sha256=ix['source_sha256'], exe_sha1=_sha1(exe), sound_sha1=_sha1(sound),
                 classes=classes)
    path.write_text(json.dumps(value, separators=(',', ':')))
    _CACHE.pop(path, None)
    progress(f'{len(classes)} classes captured -> {path}')
    return value


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'tools'))
    if sys.argv[1:2] == ['build']:
        build()
    elif sys.argv[1:2] == ['show']:
        print(json.dumps(entry(int(sys.argv[2])), indent=1))
    else:
        print(__doc__)
