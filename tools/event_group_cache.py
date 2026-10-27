"""Remember each map's compiled events between builds (2026-10-15: build time).

The build compiles the events map by map (event_export). A map whose inputs are
the same as in an earlier build gets that build's result back instead of being
compiled again: its finished map block, the project switches the compile made,
and its report. The inputs are everything the compile reads:
* the editor's code the compile can run (tools/*.py without the windows, tile
  picker and one-off scripts: _compile_file) and the object library;
* the original game data;
* the Database apart from the events (definitions, options, ...);
* this map's events, the project switches made so far, this map's block before
  the compile, the data's head and map count, and the stock maps the project
  changed (their blocks).
A result is stored only when the compile changed nothing but this map's block.
Delete game/editor-cache/event-groups to start afresh."""
import hashlib, json, os, pickle, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'game' / 'editor-cache' / 'event-groups'
KEEP = 4000
_CODE = {}
_ORIG = {}


# Files the event compile never runs: the editor's windows and tile picker, and
# one-off scripts (tests, audits, builders of test projects, exports). A change
# to them no longer makes every map compile again (2026-10-16).
_NOT_COMPILE_PREFIXES = ('audit_', 'bizhawk_', 'benchmark_', 'build_', 'validate_', 'record_', 'create_',
                         'summarize_', 'check_', 'capture_', 'compare_', 'review_', 'diagnose_', 'archive_',
                         'trace_', 'render_', 'remake_', 'test_', 'qa_', 'merge_all_', 'write_item_')
_NOT_COMPILE_FILES = {'area_ui.py', 'editor_ui.py', 'liquid_catalogue.py', 'tree_catalogue.py', 'map_places.py',
                      'wrap_tabs.py', 'zoom_canvas.py', 'editor_theme.py', 'editor_launcher.py', 'stock_source.py',
                      'ui_layouts.py', 'ui_title_case.py', 'history_icons.py'}


def _compile_file(f):
    name = f.name
    return not (name.endswith('_ui.py') or name in _NOT_COMPILE_FILES or name.startswith(_NOT_COMPILE_PREFIXES))


def _code_hash():
    files = sorted(f for f in (ROOT / 'tools').glob('*.py') if _compile_file(f))
    stamp = tuple((f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in files)
    if stamp not in _CODE:
        d = hashlib.sha256()
        for f in files:
            d.update(f.name.encode()); d.update(f.read_bytes())
        for name in ('index.json',):
            try:
                d.update((ROOT / 'game/object-library' / name).read_bytes())
            except OSError:
                pass
        _CODE.clear(); _CODE[stamp] = d.hexdigest()
    return _CODE[stamp]


def _original_hash(original):
    key = (id(original), len(original))
    if key not in _ORIG:
        _ORIG.clear(); _ORIG[key] = hashlib.sha1(memoryview(original)).hexdigest()
    return _ORIG[key]


def static_hash(database, original=b''):
    """What is the same for every map group of one build: the editor's code, the
    object library, the original data and the Database without its events and
    project switches."""
    rest = {k: v for k, v in (database or {}).items() if k not in ('event_graphs', 'project_state')}
    d = hashlib.sha256()
    d.update(_code_hash().encode()); d.update(_original_hash(original or b'').encode())
    d.update(json.dumps(rest, sort_keys=True, default=str).encode())
    return d.hexdigest()


def group_key(session, group, static, changed_stock, pending=None):
    from map_slots import offsets
    if os.environ.get('ALUNDRA_NO_EVENT_CACHE'):
        return None
    maps = {g.get('map_id') for g in group}
    if len(maps) != 1:
        return None
    m = maps.pop()
    data = session.data
    o = offsets(data)
    if type(m) is not int or not 0 <= m < len(o) - 1:
        return None
    d = hashlib.sha256()
    db = getattr(session, 'content_database', None) or {}
    for part in (static,
                 json.dumps(group, sort_keys=True, default=str),
                 json.dumps(db.get('project_state'), sort_keys=True, default=str),
                 json.dumps(db.get('created_maps'), sort_keys=True, default=str),
                 str(len(o)), str(sorted(changed_stock or ()))):
        d.update(part.encode()); d.update(b'\0')
    view = memoryview(data)
    pending = pending or {}
    block = lambda n: pending[n] if n in pending else view[o[n]:o[n + 1]]
    d.update(view[:0x28]); d.update(view[0x800:o[0]])   # the head without the map offset table
    d.update(block(m))
    for s in sorted(changed_stock or ()):
        if s != m and 0 <= s < len(o) - 1:
            d.update(block(s))
    return m, d.hexdigest()


def load(key):
    try:
        path = CACHE / f'{key[1]}.bin'
        value = pickle.loads(zlib.decompress(path.read_bytes()))
        try:
            os.utime(path)   # recently used: kept by prune()
        except OSError:
            pass
        return value
    except (OSError, ValueError, pickle.PickleError, zlib.error, EOFError):
        return None


def store(key, before, compiled):
    """Keep compiled's result for key, if it only changed map key[0]'s block."""
    from map_slots import offsets
    from stock_donors import replace_blocks
    m = key[0]
    after = compiled.data
    ob, oa = offsets(before), offsets(after)
    if len(ob) != len(oa):
        return False
    block = bytes(memoryview(after)[oa[m]:oa[m + 1]])
    if replace_blocks(before, {m: block}) != after:
        return False      # it changed more than its own map: always compile it
    db = getattr(compiled, 'content_database', None) or {}
    value = {'map': m, 'block': block, 'project_state': db.get('project_state'),
             'created_maps': db.get('created_maps'),
             'report': getattr(compiled, 'native_event_export_report', []),
             'route_slots': getattr(compiled, 'actor_route_resume_slots', 0),
             'melzas_places': {k: v for k, v in (getattr(compiled, 'melzas_places', None) or {}).items() if k == m},
             'boss_places': {c: {k: v for k, v in rows.items() if k == m}
                             for c, rows in (getattr(compiled, 'boss_places', None) or {}).items() if m in rows}}
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = CACHE / f'{key[1]}.tmp'
        tmp.write_bytes(zlib.compress(pickle.dumps(value, protocol=4), 3))
        os.replace(tmp, CACHE / f'{key[1]}.bin')
    except OSError:
        return False
    return True


def prune():
    """Keep the newest KEEP results (once per build)."""
    try:
        files = sorted(CACHE.glob('*.bin'), key=lambda p: p.stat().st_mtime)
        for old in files[:-KEEP]:
            old.unlink()
    except OSError:
        pass
