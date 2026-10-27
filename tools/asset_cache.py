"""Per-game-data disk cache shared by every project (user 2026-10-27).

Lives in private-inputs/cache/<first 16 hex of the game data's sha256>/, so a
new project on the same game data reuses what earlier ones built:
  database.json.gz  the Database straight after first indexing (skips the slow
                    first-open indexing for new projects)
  icons/<key>.png   cropped class pictures (Database, spawned attacks...)
Everything here can be deleted at any time; it is rebuilt as needed.
"""
import gzip, hashlib, json, os, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'private-inputs' / 'cache'
SNAPSHOT_VERSION = 1
_lock = threading.Lock()


_stamp = None


def code_stamp():
    """Changes whenever the editor code changes, so nothing cached by an older version
    is reused (user 2026-10-27)."""
    global _stamp
    if _stamp is None:
        h = hashlib.sha1()
        here = Path(__file__).resolve().parent
        for n in ('asset_cache', 'content_database', 'database_catalogue', 'catalogue_names',
                  'entity_preview', 'stock_donors', 'stock_source', 'object_library', 'global_sprite_recolor'):
            path = here / (n + '.py')
            if path.is_file(): h.update(path.read_bytes())
        _stamp = h.hexdigest()[:12]
    return _stamp


def folder(digest):
    # one folder per game data and editor version; older versions' folders are removed
    if not digest: return None
    d = BASE / f'{str(digest)[:16]}-{code_stamp()}'
    _prune(str(digest)[:16], d)
    return d


_pruned = set()


def _prune(prefix, keep):
    if prefix in _pruned: return
    _pruned.add(prefix)
    try:
        import shutil
        for old in BASE.glob(prefix + '*'):
            if old != keep and old.is_dir(): shutil.rmtree(old, ignore_errors=True)
    except Exception:
        pass


def _atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f'.{os.getpid()}.{threading.get_ident()}.tmp')
    tmp.write_bytes(data)
    os.replace(tmp, path)


# -- Database snapshot ---------------------------------------------------------
def load_database(digest, code_version):
    d = folder(digest)
    if d is None: return None
    path = d / 'database.json.gz'
    try:
        doc = json.loads(gzip.decompress(path.read_bytes()))
    except (OSError, ValueError, EOFError):
        return None
    if doc.get('_cache') != [SNAPSHOT_VERSION, code_version]: return None
    doc.pop('_cache', None)
    return doc


def save_database(digest, code_version, document):
    d = folder(digest)
    if d is None: return
    try:
        doc = dict(document); doc['_cache'] = [SNAPSHOT_VERSION, code_version]
        _atomic_write(d / 'database.json.gz', gzip.compress(json.dumps(doc, separators=(',', ':')).encode(), 1))
    except Exception:
        pass


# -- Class icons -----------------------------------------------------------------
_LOOK_KEYS = ('sprite', 'graphic', 'palette', 'reference', 'look', 'import')


def icon_key(row):
    data = row.get('data', {}) or {}
    look = {k: data[k] for k in sorted(data) if any(s in k for s in _LOOK_KEYS)}
    blob = repr((row.get('source'), look)).encode()
    return hashlib.sha1(blob).hexdigest()


def load_icon(digest, row):
    d = folder(digest)
    if d is None: return False, None
    path = d / 'icons' / (icon_key(row) + '.png')
    if path.is_file():
        try:
            from PIL import Image
            if path.stat().st_size == 0: return True, None   # cached "no picture"
            with Image.open(path) as im: return True, im.convert('RGBA')
        except Exception:
            return False, None
    return False, None


def save_icon(digest, row, image):
    d = folder(digest)
    if d is None: return
    try:
        import io
        buf = io.BytesIO()
        if image is not None: image.save(buf, 'PNG', optimize=False)
        _atomic_write(d / 'icons' / (icon_key(row) + '.png'), buf.getvalue())
    except Exception:
        pass
