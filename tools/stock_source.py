"""The original game's data, from this computer (user request 2026-10-16).

Every default game asset the editor shows - the database's game entries, the
tile picker's lists (bushes, water / ice / lava, floors, walls, slopes, map
objects, trees, indoor / outdoor sheets) and the pictures of game objects - is
built from the original game kept here, not from the game that is opened:
  1. game/disc/DATA/DATAS.BIN when it is the original (sha256 of the
     object library's index, or the known US Rev 1 when there is no library);
  2. else the object library's copy (game/object-library, put back
     together and checked).
Only then is the opened game looked at, for what it changes: maps whose bytes
differ from the original are read from it (map_differences); everything that
matches is skipped. With no local copy at all the opened game's original is
used, as before."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISC_DATAS = ROOT / 'game/disc/DATA/DATAS.BIN'
US_REV1_SHA256 = None   # filled from the object library's index when there is one
_cache = {}


def local_stock():
    """bytes of the original DATAS.BIN from this computer, or None."""
    if 'data' in _cache:
        return _cache['data']
    data = None
    try:
        import object_library
        ix = object_library.index() if object_library.available() else None
    except Exception:
        object_library, ix = None, None
    want = (ix or {}).get('source_sha256') or (ix or {}).get('datas_sha256')
    try:
        raw = DISC_DATAS.read_bytes()
        if want is None or hashlib.sha256(raw).hexdigest() == want:
            data = raw
    except OSError:
        pass
    if data is None and ix is not None:
        try:
            data = object_library.original_data()
        except Exception:
            data = None
    _cache['data'] = data
    return data


def catalogue_base(session):
    """The original data default game assets are built from: this computer's
    copy, else the opened game's original."""
    stock = local_stock()
    if stock is not None:
        return stock
    return bytes(getattr(session, 'original', None) or session.data)


def map_differences(session, maps=range(483)):
    """Original maps whose block in the opened game's original data differs from
    the extracted original (only those need reading from the opened game).
    Compared by the fingerprints saved with the object library (sha1 of each
    map block), so the original game itself is not loaded for this."""
    opened = getattr(session, 'original', None)
    if opened is None:
        return []
    opened = bytes(opened)
    from map_slots import offsets
    b = offsets(opened)
    prints = None
    try:
        import object_library
        if object_library.available():
            prints = object_library.index().get('map_fingerprints')
    except Exception:
        prints = None
    if prints is None:   # no library: compare with the disc copy
        stock = local_stock()
        if stock is None or stock == opened:
            return []
        a = offsets(stock)
        prints = [hashlib.sha1(stock[a[m]:a[m + 1]]).hexdigest() for m in range(len(a) - 1)]
    out = []
    for m in maps:
        if m >= len(prints) or m + 1 >= len(b) or hashlib.sha1(memoryview(opened)[b[m]:b[m + 1]]).hexdigest() != prints[m]:
            out.append(m)
    return out
