"""Validated project event graphs, inspired by RPG Maker's page/list model.

These records are editor metadata. This module does not compile or execute
custom commands in the PS1 game.
"""
from copy import deepcopy

TRIGGERS = ("interact", "activate", "touch", "hit", "event_touch", "autorun", "parallel", "switch", "death", "deactivate")
HIT_SOURCES = ("sword", "flail", "bow", "fire_wand", "ice_wand", "bomb", "spring_bean")
COMPARISONS = ("==", "!=", "<", "<=", ">", ">=")
VARIABLE_OPS = ("set", "add", "subtract", "multiply", "divide", "modulo")
DIRECTIONS = ("up", "down", "left", "right")
COMMANDS = ("show_dialogue", "ask_question", "give_item", "change_money", "set_switch", "set_variable",
            "move_actor", "face_actor", "change_graphic", "set_event_active", "spawn_class",
            "warp_player", "change_player_character", "wait", "if", "repeat", "play_sound", "change_music",
            "lock_movement", "unlock_movement", "change_animation", "deactivate_switch", "erase_event")
from native_event_authoring import COMMANDS as _NATIVE_COMMANDS, CONDITIONS as _NATIVE_CONDITIONS
COMMANDS = COMMANDS + tuple(_NATIVE_COMMANDS)


def _integer(value, label, low=0, high=65535):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be {low}..{high}")


def _condition(condition):
    if not isinstance(condition, dict):
        raise ValueError("Condition must be an object")
    kind = condition.get("type")
    op = condition.get("operator", "==")
    if op not in COMPARISONS:
        raise ValueError("Condition uses an unsupported comparison")
    if kind == "switch":
        _integer(condition.get("switch_id"), "Switch ID")
        if type(condition.get("value")) is not bool or op not in ("==", "!="):
            raise ValueError("Switch conditions compare ON/OFF")
    elif kind == "variable":
        _integer(condition.get("variable_id"), "Variable ID")
        operand = condition.get("value")
        if isinstance(operand, dict):
            if operand.get("type") != "variable":
                raise ValueError("Variable operands must refer to another variable")
            _integer(operand.get("variable_id"), "Operand variable ID")
        elif type(operand) not in (int, float):
            raise ValueError("Variable comparison needs a numeric value")
    elif kind == "item":
        if not isinstance(condition.get("item_class_id"), str) or not condition["item_class_id"]:
            raise ValueError("Item conditions need an item class ID")
        _integer(condition.get("quantity", 1), "Item quantity", 1, 999)
        if op not in ("==", "!=", ">=", "<"):
            raise ValueError("Item conditions support ==, !=, >=, and <")
    elif kind in _NATIVE_CONDITIONS:
        from native_event_authoring import validate_condition
        validate_condition(condition)
    else:
        raise ValueError("Condition type must be switch, variable, or item")


def _commands(rows, depth=0):
    if not isinstance(rows, list) or len(rows) > 512:
        raise ValueError("Each command list must contain at most 512 commands")
    if depth > 16:
        raise ValueError("Event condition nesting is limited to 16 levels")
    for row in rows:
        if not isinstance(row, dict) or row.get("type") not in COMMANDS:
            raise ValueError("Command has an unsupported type")
        kind = row["type"]
        if kind in _NATIVE_COMMANDS:
            from native_event_authoring import validate_command
            validate_command(row)
            continue
        if kind == "show_dialogue":
            if not isinstance(row.get("text"), str):
                raise ValueError("Dialogue command needs text")
            if row.get("speaker") is not None and not isinstance(row["speaker"], str):
                raise ValueError("Dialogue speaker must be a name or actor reference")
        elif kind == "give_item":
            if not isinstance(row.get("item_class_id"), str) or not row["item_class_id"]:
                raise ValueError("Give item needs an item class ID")
            _integer(row.get("quantity", 1), "Item quantity", 1, 999)
            if "obtained_message" in row and not isinstance(row["obtained_message"], str):
                raise ValueError("Obtained message must be text")
        elif kind == "set_switch":
            _integer(row.get("switch_id"), "Switch ID")
            if type(row.get("value")) is not bool:
                raise ValueError("Switch value must be ON or OFF")
        elif kind == "change_money":
            _integer(row.get('amount'), 'Money to add', 0, 65535)
        elif kind == "set_variable":
            _integer(row.get("variable_id"), "Variable ID")
            if row.get("operation") not in VARIABLE_OPS:
                raise ValueError("Variable operation is unsupported")
            value = row.get("value")
            if isinstance(value, dict):
                if value.get("type") != "variable":
                    raise ValueError("Variable action operand must be a constant or variable")
                _integer(value.get("variable_id"), "Operand variable ID")
            elif type(value) not in (int, float):
                raise ValueError("Variable action needs a numeric operand")
            if row.get("operation") in ("divide", "modulo") and type(value) in (int, float) and value == 0:
                raise ValueError("Variable cannot be divided by zero")
        elif kind == "face_actor":
            if row.get("target") not in ("this_event", "self"):
                raise ValueError("Facing currently targets This event")
            if row.get("direction") not in (*DIRECTIONS, "player", "away_from_player"):
                raise ValueError("Choose player, away from player, up, down, left or right")
        elif kind == "move_actor":
            if 'movement_speed' in row:_integer(row['movement_speed'],'Movement speed percent',1,400)
            if row.get('blocked_behavior','wait') not in ('wait','skip'):raise ValueError('Blocked movement must wait or skip')
            for animation_key in ('moving_animation','idle_animation'):
                if row.get(animation_key) is not None:_integer(row[animation_key],animation_key.replace('_',' '),0,255)
            if not isinstance(row.get("target"), str) or not row["target"]:
                raise ValueError("Movement needs an actor or event target")
            mode = row.get("mode")
            if mode not in ("toward_player", "walk_tiles", "route"):
                raise ValueError("Movement mode must be toward_player, walk_tiles, or route")
            if mode == "walk_tiles":
                _integer(row.get("tiles"), "Walk distance", 1, 255)
                if row.get("direction") not in DIRECTIONS:
                    raise ValueError("Walk direction must be up, down, left, or right")
            if mode == "route":
                route = row.get("route")
                if not isinstance(route, list) or not route or len(route) > 255 or any(step not in DIRECTIONS for step in route):
                    raise ValueError("Route must be a list of up to 255 tile directions")
        elif kind == 'change_player_character':
            if row.get('character') not in ('Alundra','Meia'):
                raise ValueError('Player character must be Alundra or Meia')
            for key in ('meia_basic_attack','meia_alundra_fallback'):
                if type(row.get(key,False)) is not bool:raise ValueError('Meia options must be ON or OFF')
        elif kind == "change_graphic":
            if not all(isinstance(row.get(key), str) and row[key] for key in ("target", "graphic")):
                raise ValueError("Graphic change needs an actor target and graphic reference")
        elif kind == "set_event_active":
            if not isinstance(row.get("event_id"), str) or not row["event_id"] or type(row.get("active")) is not bool:
                raise ValueError("Event visibility needs an event ID and active state")
        elif kind == "spawn_class":
            if not isinstance(row.get("class_id"), str) or not row["class_id"]:
                raise ValueError("Spawn needs an object, NPC, or enemy class ID")
            position = row.get("position")
            if not isinstance(position, list) or len(position) != 2:
                raise ValueError("Spawn position must be [x, y]")
            for axis, value in zip("xy", position):
                _integer(value, "Spawn " + axis, 0, 255)
        elif kind == "warp_player":
            _integer(row.get("map_id"), "Destination map", 0, 2546)
            _integer(row.get("x"), "Destination X", 0, 255)
            _integer(row.get("y"), "Destination Y", 0, 255)
        elif kind == "change_music":
            from music_database import encode_music
            encode_music(row.get("music_id"))
        elif kind == "play_sound":
            _integer(row.get("sound_id"), "Sound effect ID", 0, 255)
        elif kind == "wait":
            _integer(row.get("frames"), "Wait frames", 1, 65535)
        elif kind == "change_animation":
            _integer(row.get("animation_id"), "Animation", 0, 255)
        elif kind == "deactivate_switch":
            if not isinstance(row.get("event_id"), str) or not row["event_id"]:
                raise ValueError("Activate / Deactivate Switch needs a switch event")
            if type(row.get("active", False)) is not bool:
                raise ValueError("Choose Activated or Deactivated")
        if kind == "ask_question":
            if not isinstance(row.get("text"), str):
                raise ValueError("Ask A Question needs text")
            _commands(row.get("then", []), depth + 1)
            _commands(row.get("else", []), depth + 1)
        elif kind == "if":
            _condition(row.get("condition"))
            _commands(row.get("then", []), depth + 1)
            _commands(row.get("else", []), depth + 1)
        elif kind == 'repeat':
            _integer(row.get('count'),'Repeat count',1,255)
            _commands(row.get('commands',[]),depth+1)


def validate_event_graph(row):
    """Raise ValueError unless row is a standalone, bounded map event graph."""
    if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
        raise ValueError("Event graph needs a stable ID")
    if not isinstance(row.get("name"), str) or not row["name"].strip():
        raise ValueError("Event graph needs a name")
    _integer(row.get("map_id"), "Map ID", 0, 2546)
    region = row.get("region")
    if not isinstance(region, list) or len(region) != 4:
        raise ValueError("Event region must be [x, y, width, height] in map tiles")
    x, y, width, height = region
    _integer(x, "Region X", 0, 255);_integer(y, "Region Y", 0, 255)
    _integer(width, "Region width", 1, 256);_integer(height, "Region height", 1, 256)
    if x + width > 256 or y + height > 256:
        raise ValueError("Event region exceeds the editor's 256-tile coordinate envelope")
    if row.get("trigger") not in TRIGGERS:
        raise ValueError("Event trigger is unsupported")
    if row["trigger"] == "switch":
        _integer(row.get("switch_id"), "Trigger switch ID")
    pages = row.get("pages")
    if not isinstance(pages, list) or not pages or len(pages) > 32:
        raise ValueError("An event needs 1-32 pages")
    page_ids = set()
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get("id"), str) or not page["id"]:
            raise ValueError("Each event page needs a stable ID")
        if page["id"] in page_ids:
            raise ValueError("Event page IDs must be unique")
        page_ids.add(page["id"])
        if not isinstance(page.get("name"), str) or not page["name"].strip():
            raise ValueError("Each event page needs a name")
        if "idle_animation_enabled" in page and type(page["idle_animation_enabled"]) is not bool:
            raise ValueError("Idle animation must be a checkbox value")
        if "float" in page and type(page["float"]) is not bool:
            raise ValueError("Float must be a checkbox value")
        if "float_height" in page and (type(page["float_height"]) is not int or not 0 <= page["float_height"] <= 512):
            raise ValueError("Float height must be 0..512 pixels")
        route=page.get('default_move_route')
        if route is not None:
            if not isinstance(route,dict) or route.get('type')!='move_actor':raise ValueError('Default route must be a movement command')
            if type(route.get('repeat',True)) is not bool:raise ValueError('Default route Repeat must be ON/OFF')
            _commands([route])
        page_trigger=page.get("trigger",row.get("trigger"))
        if page_trigger not in TRIGGERS:
            raise ValueError("Event page trigger is unsupported")
        handlers=page.get("trigger_actions")
        if handlers is not None:
            if not isinstance(handlers,list) or not handlers or len(handlers)>len(TRIGGERS):
                raise ValueError("A page needs 1..8 trigger tabs")
            seen_triggers=set()
            for handler in handlers:
                if not isinstance(handler,dict) or handler.get("trigger") not in TRIGGERS:
                    raise ValueError("Trigger tab has an unsupported trigger")
                trigger=handler["trigger"]
                if trigger in seen_triggers:raise ValueError("Each event can have one tab per trigger")
                seen_triggers.add(trigger)
                if type(handler.get("destroy_after",False)) is not bool:
                    raise ValueError("Destroy after event must be a checkbox value")
                sources=handler.get("hit_sources",[])
                if (not isinstance(sources,list) or any(not isinstance(source,str) for source in sources)
                        or len(set(sources))!=len(sources) or any(source not in HIT_SOURCES for source in sources)):
                    raise ValueError("Hit filters must be unique weapon or magic choices")
                _commands(handler.get("commands",[]))
        page_class=page.get("class_id",row.get("class_id"))
        if page_class is not None and not isinstance(page_class,str):
            raise ValueError("Event page class ID must be a database ID or empty")
        if "contained_item_class_id" in page and page["contained_item_class_id"] is not None and not isinstance(page["contained_item_class_id"],str):
            raise ValueError("Chest item must be a database class ID or empty")
        conditions = page.get("conditions", [])
        if not isinstance(conditions, list) or len(conditions) > 32:
            raise ValueError("Each page supports up to 32 conditions")
        for condition in conditions:
            _condition(condition)
        _commands(page.get("commands", []))
    return deepcopy(row)


def new_event_graph(event_id, map_id, name="New map event", x=0, y=0,
                    class_id=None):
    """Create a project event at a map tile, optionally backed by a DB class.

    The position/class link are authoring metadata until the native record
    allocator and event compiler have been verified for the target build.
    """
    return validate_event_graph({
        "id": event_id, "name": name, "map_id": map_id,
        "region": [x, y, 1, 1], "class_id": None,
        "trigger": "interact", "switch_id": None,
        "pages": [{"id": "page:0001", "name": "Default", "trigger": "interact",
                   "class_id": class_id, "conditions": [], "commands": []}],
        "notes": "Standalone event region; no NPC or object is required."
    })


DEFAULT_EVENT_NAME = "New map event"


def class_event_name(current_name, definition, auto_bases=()):
    """Name an event after its NPC/object/enemy class while it still has an
    automatic name (the generic default, or one taken from ``auto_bases``).
    Empty events (no class) and warps keep their name."""
    if not is_auto_name(current_name, auto_bases) or not definition:
        return current_name
    if definition.get("source", {}).get("variant") == "warp_panel":
        return current_name
    return definition.get("name") or current_name


def is_auto_name(name, auto_bases=()):
    """True for the default name or ``base``/``base A``.. from auto naming."""
    if name == DEFAULT_EVENT_NAME:
        return True
    for base in auto_bases:
        if base and (name == base or (name.startswith(base + " ")
                     and _letter_index(name[len(base) + 1:]) is not None)):
            return True
    return False


def _letters(index):
    """0 -> A, 25 -> Z, 26 -> AA (spreadsheet-style)."""
    text = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        text = chr(65 + rest) + text
    return text


def _letter_index(text):
    if not text or not text.isalpha() or not text.isupper():
        return None
    value = 0
    for char in text:
        value = value * 26 + ord(char) - 64
    return value - 1


def lettered_name(base, taken):
    """Pick ``base`` or ``base A/B/C..`` so names on one map stay distinct.

    Returns (name, rename) where ``rename`` is the new name for an existing
    plain ``base`` (it becomes ``base A`` once a second one appears), or None.
    """
    used = set()
    plain = base in taken
    for name in taken:
        if name.startswith(base + " "):
            index = _letter_index(name[len(base) + 1:])
            if index is not None:
                used.add(index)
    if not plain and not used:
        return base, None
    rename = None
    if plain:
        first = next(i for i in range(len(used) + 1) if i not in used)
        used.add(first)
        rename = f"{base} {_letters(first)}"
    nxt = next(i for i in range(len(used) + 1) if i not in used)
    return f"{base} {_letters(nxt)}", rename


def chest_item_for_page(page, definition):
    """Resolve per-placement chest contents, then the shared class default."""
    if "contained_item_class_id" in page:
        return page["contained_item_class_id"]
    return definition.get("data", {}).get("contained_item_class_id")


def ensure_trigger_actions(page):
    """Upgrade a legacy single-trigger page to editable trigger tabs in place."""
    if "trigger_actions" not in page:
        page["trigger_actions"] = [{
            "trigger": page.get("trigger", "interact"),
            "commands": deepcopy(page.get("commands", [])),
            "hit_sources": [],
            "destroy_after": False,
        }]
    return page["trigger_actions"]
