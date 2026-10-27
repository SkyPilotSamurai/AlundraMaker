"""Remember the result of slow build steps (Start as Meia's redrawn frames take
a minute or more) and reuse it while their inputs are unchanged.

A step's result is stored as the list of byte changes it made to the game
data, keyed by a hash of (step name, its options, the bytes it reads, the
source code of the modules that do the work). Next build with the same key:
the changes are applied in a moment instead of computing them again."""
import hashlib
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'game' / 'editor-cache' / 'build-steps'
KEEP = 12   # newest results kept per step


def _code_hash(modules):
    digest = hashlib.sha256()
    for name in modules:
        try:
            digest.update((ROOT / 'tools' / f'{name}.py').read_bytes())
        except OSError:
            digest.update(name.encode())
    return digest.hexdigest()


def byte_changes(before, after, chunk=65536):
    """[(offset, new bytes)] where after differs from before (same length)."""
    changes = []; a = memoryview(before); b = memoryview(after)
    for start in range(0, len(before), chunk):
        if a[start:start + chunk] == b[start:start + chunk]:
            continue
        x = bytes(a[start:start + chunk]); y = bytes(b[start:start + chunk]); i = 0; n = len(x)
        while i < n:
            if x[i] == y[i]:
                i += 1; continue
            j = i
            while j < n and (x[j] != y[j] or (j + 8 < n and x[j:j + 8] != y[j:j + 8])):
                j += 1
            changes.append((start + i, y[i:j])); i = j
    return changes


def cached_step(name, session, read_ranges, options, modules, run):
    """Run run() (which edits session.data in place and returns a report), or
    apply the remembered changes of an earlier identical run. read_ranges:
    [(start, end)] of the game data the step depends on."""
    digest = hashlib.sha256(repr((name, options, _code_hash(modules), len(session.data), list(read_ranges))).encode())
    for start, end in read_ranges:
        digest.update(bytes(session.data[start:end]))
    key = digest.hexdigest()[:32]
    path = CACHE / f'{name}-{key}.pickle'
    try:
        stored = pickle.loads(path.read_bytes())
        for offset, payload in stored['changes']:
            session.data[offset:offset + len(payload)] = payload
        report = stored['report']
        if isinstance(report, dict):
            report = dict(report, from_cache=True)
        return report
    except Exception:
        pass
    before = bytes(session.data)
    report = run()
    if len(session.data) == len(before):
        changes = byte_changes(before, bytes(session.data))
        try:
            CACHE.mkdir(parents=True, exist_ok=True)
            path.write_bytes(pickle.dumps({'changes': changes, 'report': report}))
            old = sorted(CACHE.glob(f'{name}-*.pickle'), key=lambda p: p.stat().st_mtime)
            for stale in old[:-KEEP]:
                stale.unlink()
        except Exception:
            pass   # not remembered: computed again next time
    return report
