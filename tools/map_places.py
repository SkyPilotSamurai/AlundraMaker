"""Indoor or outdoor map, for the tile picker's Indoor / Outdoor tabs (user
request 2026-10-15). Outdoor: the overworld and other open-air places by name
(outside, desert, bridge, balcony, ...) or a map whose floor is mostly grass
(survey of the original 483 maps: share of green floor pixels >= 0.5, caves,
mines, shrines, lairs and boss rooms excepted). Everything else - houses,
caves, dungeons - is indoor. A new map goes by its name."""
from map_names import map_label

OUTDOOR = frozenset([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 44, 51, 146, 153, 157, 158, 159, 160, 161, 162, 169, 176, 183, 186, 193, 198, 205, 212, 219, 226, 230, 237, 241, 248, 252, 259, 266, 271, 275, 282, 289, 293, 297, 301, 305, 310, 330, 331, 335, 351, 352, 353, 354, 355, 356, 357, 364, 367, 368, 371, 378, 379, 382, 383, 384, 385, 386, 393, 395, 399, 402, 403, 404, 405, 406, 407, 416, 433, 434, 437, 439, 440, 450, 456, 478, 479, 481])
_KEYS = ('overworld', 'outside', 'outlook', 'desert', 'arrival cutscene', 'balcony', 'bridge', 'fairy pond', 'mill cutscene')


def map_place(m):
    """'outdoor' or 'indoor'."""
    if m in OUTDOOR:
        return 'outdoor'
    if m >= 483:
        name = map_label(m).rsplit(' (Map', 1)[0].lower()
        if any(k in name for k in _KEYS):
            return 'outdoor'
    return 'indoor'


def place_sheet(session, kind, part):
    """Every different floor (kind 'floors') or wall tile ('walls') of the
    original game's indoor or outdoor maps (part), similar ones together:
    (sheet image, [(map, code), ...] in sheet order, FLOOR_COLUMNS wide).
    Built from bush_catalogue's whole-game catalogue; kept on the session
    and in private-inputs/editor-cache."""
    import hashlib, pickle
    from io import BytesIO
    from pathlib import Path
    from PIL import Image
    store = session.__dict__.setdefault('_place_sheets', {})
    if (kind, part) in store:
        return store[(kind, part)]
    from stock_source import catalogue_base
    original = catalogue_base(session)   # this computer's original game (2026-10-16)
    digest = hashlib.sha256(original).hexdigest()[:16]
    cache = Path(__file__).resolve().parents[1] / 'private-inputs' / 'editor-cache' / f'place-{kind}-{part}-v1-{digest}.pickle'
    try:
        data = pickle.loads(cache.read_bytes())
        result = (Image.open(BytesIO(data['sheet'])).convert('RGBA'), data['entries'])
        store[(kind, part)] = result
        return result
    except Exception:
        pass
    from area_map import MapRenderer
    from bush_catalogue import floor_catalogue, wall_catalogue, floor_sheet
    from editor_session import EditSession
    source = session if original == bytes(session.data) else EditSession(original, verify=False)
    catalogue = (floor_catalogue if kind == 'floors' else wall_catalogue)(source)
    entries = [(m, code) for m, code, _ in catalogue['entries'] if map_place(m) == part]
    renderers = {}; images = []
    for m, code in entries:
        renderer = renderers.get(m)
        if renderer is None:
            renderer = renderers[m] = MapRenderer(source, m)
        images.append(renderer.tile(code))
    sheet, blocks = floor_sheet(images)
    ordered = [entries[i] for _, members in blocks for i in members]
    result = (sheet, ordered)
    store[(kind, part)] = result
    try:
        buffer = BytesIO(); sheet.save(buffer, 'PNG')
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps(dict(sheet=buffer.getvalue(), entries=ordered)))
    except Exception:
        pass
    return result
