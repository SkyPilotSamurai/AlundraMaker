"""Map start markers and guarded new-game spawn compilation."""
import struct
from area_map import grid
from intro_skip import EXE_FIELDS
from alundra_memory import parse_exe


def resolve_start_point(session, point):
    """Validate an authored map/tile and derive Z from its current floor height."""
    if not isinstance(point, dict):
        raise ValueError("Start point must be a map tile")
    map_id, x, y = (point.get(key) for key in ("map_id", "x", "y"))
    if any(type(value) is not int for value in (map_id, x, y)):
        raise ValueError("Start point map and tile coordinates must be whole numbers")
    if not 0 <= map_id < 2547:
        raise ValueError("Start point map must be 0 through 2546")
    width, height, cells = grid(session, map_id)
    if not 0 <= x < width or not 0 <= y < height:
        raise ValueError("Start point must be inside the selected map")
    cell = cells[y * width + x]
    return {"map_id": map_id, "x": x, "y": y, "z": cell["values"][3]}


def set_start_point(document, session, map_id, x, y):
    """Store one S marker and ensure new games bypass the opening sequence."""
    point = resolve_start_point(session, {"map_id": map_id, "x": x, "y": y})
    options = document.setdefault("mod_options", {})
    options["start_point"] = point
    # Skip intro is not ticked for the user; the build skips the opening for a start point by itself
    return point


def patch_start_point_spawn(exe, point):
    """Patch only the known USA 1.1 new-game coordinate immediates.

    This is a static code/data patch. It does not establish that arbitrary
    maps have safe new-game initialization or a gameplay-valid arrival tile.
    """
    map_id, x, y, z = (point.get(key) for key in ("map_id", "x", "y", "z"))
    if any(type(value) is not int for value in (map_id, x, y, z)):
        raise ValueError("Compiled start point needs integer map, tile and height values")
    if not 0 <= map_id < 2547 or not 0 <= x <= 255 or not 0 <= y <= 255 or not 0 <= z <= 255:
        raise ValueError("Start point is outside native map-coordinate limits")
    info = parse_exe(exe)
    data = bytearray(exe)
    # EXE_FIELDS: player X/Y/Z, new-game map, camera X/Y, camera Z store.
    values = (x, y, z, map_id, x, y, None)
    sites = []
    for (address, stock, intro, label), value in zip(EXE_FIELDS, values):
        offset = 0x800 + address - info["load_address"]
        if not 0x800 <= offset <= 0x800 + info["load_size"] - 4:
            raise ValueError("Start-point code outside executable payload")
        found = struct.unpack_from("<I", data, offset)[0]
        wanted = (intro & 0xFFFF0000) | value if value is not None else intro
        if found not in (stock, intro, wanted):
            raise ValueError(f"Start-point instruction changed at {address:08X}: {label}")
        sites.append({"native_address": hex(address), "file_offset": hex(offset),
                      "field": label, "before_word": f"{found:08x}",
                      "after_word": f"{wanted:08x}"})
    for site in sites:
        struct.pack_into("<I", data, int(site["file_offset"], 16),
                         int(site["after_word"], 16))
    return bytes(data), {"format": "alundra-editor-start-point-v1",
                         "spawn": dict(point), "sites": sites,
                         "gameplay_verified": False, "hardware_verified": False}


def native_start_point(exe):
    """Read the game's own new-game map/tile from the EXE (stock or modded).

    Uses the same four instructions patch_start_point_spawn edits:
    player X, Y, Z and new-game map (intro_skip.EXE_FIELDS[0:4])."""
    info = parse_exe(exe)
    values = []
    for address, stock, intro, label in EXE_FIELDS[:4]:
        offset = 0x800 + address - info["load_address"]
        if not 0x800 <= offset <= 0x800 + info["load_size"] - 4:
            raise ValueError("New-game start code outside executable payload")
        word = struct.unpack_from("<I", exe, offset)[0]
        if word & 0xFFFF0000 == intro & 0xFFFF0000:
            values.append(word & 0xFFFF)          # addiu reg,zero,value
        elif word == stock and stock & 0xFFFF0000 != intro & 0xFFFF0000:
            values.append(0)                      # move reg,zero
        else:
            raise ValueError(f"New-game start instruction changed at {address:08X}: {label}")
    x, y, z, map_id = values
    return {"map_id": map_id, "x": x, "y": y, "z": z}


def source_exe(editor):
    """The opened game's ALUN_CD.EXE (edited copy if the mod changed it)."""
    from pathlib import Path
    session = editor.session
    extra = getattr(session, "extra_files", {}).get("ALUN_CD.EXE")
    if extra is not None:
        return bytes(extra.data)
    cached = getattr(session, "_source_exe_cache", None)
    if cached is not None:
        return cached
    root = Path(__file__).resolve().parents[1]
    path = getattr(session, "path", None)
    if getattr(session, "source_verified", False):
        exe = (root / "private-inputs/disc/ALUN_CD.EXE").read_bytes()
    elif path is not None and Path(path).suffix.lower() == ".bin":
        from mod_export import read_datas
        exe = read_datas(path, "ALUN_CD.EXE")
    else:
        raise ValueError("Open the game disc to read its new-game start point")
    try:
        session._source_exe_cache = exe
    except AttributeError:
        pass
    return exe


def effective_start_point(editor):
    """Where a new game will begin with this mod: (point, label, authored).

    Your own S marker wins; otherwise the start chosen by Open World or Skip
    intro; otherwise the start read from the game's own data."""
    options = (editor.database.document.get("mod_options") or {})
    point = options.get("start_point")
    if isinstance(point, dict):
        return resolve_start_point(editor.session, point), "Start point", True
    if options.get("open_world"):
        return {"map_id": 242, "x": 38, "y": 12, "z": 2}, "Game start", False
    if options.get("skip_intro"):
        from intro_skip import ARRIVAL
        return dict(ARRIVAL), "Game start", False
    return native_start_point(source_exe(editor)), "Game start", False
