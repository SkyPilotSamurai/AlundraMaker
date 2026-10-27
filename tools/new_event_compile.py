"""Compile one-page new native map events with local donor actors or regions."""
from copy import copy, deepcopy
import struct
# NPC classes that are animals (dog, Puku, chicken, crow): they do not turn to
# face Alundra when talked to.
NOT_HUMAN = frozenset({289, 335, 380, 381})
from event_logic_compile import compile_logic, compile_give_pickup, compile_wait_template_absent, find_item_template, verified_item_pickup_template, verified_chest_template, compile_speaker_dialogue
from native_script_allocation import append_native_process
from native_text_allocation import append_local_text
from native_class_placement import record_cluster, donor_record_for_map, append_record_cluster, resolve_class_donor
from map_block_repack import pointers, sections
from native_class_validation import require_native_class_definition


# Persistent game flags no original map script, entity or EXE immediate
# uses (scanned 2026-10-11 over maps 0-482 and ALUN_CD.EXE): one per authored
# chest, so an opened chest stays open. The choice is stored in the project
# (document['chest_flags']) so a chest keeps its flag across builds.
FREE_CHEST_FLAGS = (2046,2045,2044,2043,2042,2041,2040,2039,2038,2037,2036,2035,2034,2033,2032,2031,
    2030,2029,2028,2027,2026,2025,2024,2023,2022,2021,2020,2019,2018,2017,2016,2015,2014,2013,2012,
    2011,2010,2009,2008,2007,2006,2005,2004,1999,1998,1997,1996,1995,1994,1993,1992,1991,1990,1989,
    1988,1987,1986,1985,1984,1983,1982,1981,1980,1979)


def chest_flag_for(document, graph_id):
    flags = document.setdefault('chest_flags', {}) if isinstance(document, dict) else {}
    if graph_id not in flags:
        taken = set(flags.values())
        free = [f for f in FREE_CHEST_FLAGS if f not in taken]
        if not free:
            raise ValueError("Too many chests: no saved game flag left for another one")
        flags[graph_id] = free[0]
    return flags[graph_id]


def _presence_condition(graph):
    """RPG-style presence: a placed actor whose every page has conditions is
    only in the map while some page's conditions all hold. Returns a list of
    pages, each a list of ('flag', operand, when_set) or ('project', condition),
    or None (always present)."""
    placement = graph.get("native_placement", {})
    if graph.get("native_binding") is not None:   # always on for placed events (user choice)
        return None
    pages = graph.get("pages", [])
    blockers = graph.get("_blockers") or []   # later pages of a split event (see _split_pages)
    if not pages or (any(not page.get("conditions") for page in pages) and not blockers):
        return None
    if pages[0].get("class_id", graph.get("class_id")) is None:
        return None   # an invisible region: its pages already decide what runs
    from event_switch_registry import validate_native_flag_operand

    def tests_of(conditions):
        tests = []
        for condition in conditions:
            if not isinstance(condition, dict):
                raise ValueError("Page condition must be an object")
            if condition.get("type") == "item" or condition.get("type") in _PAGE_NATIVE_CONDITIONS:
                # 2026-10-22 QA: item / money / chest ... page conditions were refused here and the
                # build dropped the whole event; they now become native tests in the watcher.
                tests.append(("code", condition)); continue
            if condition.get("type") not in ("switch", "variable"):
                raise ValueError("Page conditions can use switches, variables, items and the game conditions")
            if condition["type"] == "switch" and "native_flag_operand" in condition:
                operator = condition.get("operator", "==")
                if operator not in ("==", "!=") or type(condition.get("value", True)) is not bool:
                    raise ValueError("Switch conditions need ON/OFF and equals / not equals")
                value = condition.get("value", True)
                tests.append(("flag", validate_native_flag_operand(condition["native_flag_operand"]),
                              value if operator == "==" else not value))
            else:
                tests.append(("project", condition))
        return tests
    result = _Presence(tests_of(page.get("conditions") or []) for page in pages)
    result.blockers = [tests_of(conditions) for conditions in blockers]
    return result


_PAGE_NATIVE_CONDITIONS = ("money", "chest_opened", "template_gone", "player_area", "button", "random")


def _run_controller(graph, body, autorun, project_condition, item_resolver, interact_area=None):
    """Autorun / Parallel page (2026-10-22): a whole-map B controller. It waits (00, one
    frame) until the page is in force (its conditions hold and no later page's do).
    Autorun: player locked, the actions run once, then it waits until the page stops being in
    force before it can run again. Parallel: the actions run again and again while in force."""
    from event_logic_compile import _Assembler
    page = graph["pages"][0]
    if len(graph["pages"]) != 1:
        raise ValueError("Autorun / Parallel pages are built one page per controller")
    asm = _Assembler()
    tests = lambda conditions: [("code", _native_page_test(c, item_resolver)) if t[0] == "code" else
                                ("test", project_condition(c)) if t[0] == "project" else t
                                for c, t in zip(conditions, _page_tests(conditions))]
    def emit(conditions, fail):
        for t in tests(conditions):
            if t[0] == "flag":
                asm.branch(0x31 if t[2] else 0x30, fail, t[1])
            elif t[0] == "code":
                for raw, branch in t[1]:
                    asm.data.extend(raw); asm.branch(branch, fail)
            else:
                asm.data.extend(t[1]); asm.branch(4, fail)
    def in_force(fail):
        for n, later in enumerate(graph.get("_blockers") or []):
            emit(later, f"free{n}_{fail}"); asm.branch(2, fail); asm.label(f"free{n}_{fail}")
        emit(page.get("conditions") or [], fail)
    asm.label("poll"); asm.data.append(0)
    in_force("poll")
    if autorun:
        asm.data.extend(bytes((0x10, 0x59, 0x81, 0x00))); asm.data.extend(body); asm.data.append(0x11)
        asm.label("wait"); asm.data.append(0)
        in_force("poll"); asm.branch(2, "wait")
    else:
        if interact_area is not None:   # Interact, no character (2026-10-23): player in the tile area (3B)
            x, y, w, h = interact_area      # and Square just pressed (2F 0080 01; the button used to talk to NPCs), then the actions
            asm.data.extend(bytes((0x3B, x, x + w - 1, y, y + h - 1, 0, 127))); asm.branch(4, "poll")
            asm.data.extend(bytes((0x2F, 0x80, 0x00, 0x01))); asm.branch(4, "poll")
        asm.data.extend(body); asm.branch(2, "poll")
    return asm.finish() + bytes((0xFF,))


def _page_tests(conditions):
    """('flag', operand, when_set) / ('project', condition) / ('code', condition) per condition."""
    from event_switch_registry import validate_native_flag_operand
    tests = []
    for condition in conditions:
        if not isinstance(condition, dict):
            raise ValueError("Page condition must be an object")
        if condition.get("type") == "item" or condition.get("type") in _PAGE_NATIVE_CONDITIONS:
            tests.append(("code", condition)); continue
        if condition.get("type") not in ("switch", "variable"):
            raise ValueError("Page conditions can use switches, variables, items and the game conditions")
        if condition["type"] == "switch" and "native_flag_operand" in condition:
            operator = condition.get("operator", "==")
            if operator not in ("==", "!=") or type(condition.get("value", True)) is not bool:
                raise ValueError("Switch conditions need ON/OFF and equals / not equals")
            value = condition.get("value", True)
            tests.append(("flag", validate_native_flag_operand(condition["native_flag_operand"]),
                          value if operator == "==" else not value))
        else:
            tests.append(("project", condition))
    return tests


def _native_page_test(condition, item_resolver):
    """[(test bytes, branch that jumps when it FAILS)] for an item or game page condition."""
    from native_event_authoring import compile_condition
    if condition["type"] != "item":
        raw, fail = compile_condition(condition)
        return [(raw, fail ^ 0x07 if condition.get("operator") == "!=" else fail)]
    if item_resolver is None:
        raise ValueError("Item page condition needs the item list of the build")
    quantity, op = condition.get("quantity", 1), condition.get("operator", ">=")
    if type(quantity) is not int or not 1 <= quantity <= 254:
        raise ValueError("Item page condition quantity must be 1..254")
    index = item_resolver(condition)
    at_least = lambda n: bytes((0x83, index, n))
    if op == ">=": return [(at_least(quantity), 4)]
    if op == "<": return [(at_least(quantity), 3)]
    if op == "==": return [(at_least(quantity), 4), (at_least(quantity + 1), 3)]
    raise ValueError("Item page conditions support >=, < and ==")


class _Presence(list):
    '''Pages that show the actor (any page whose conditions all hold), and `blockers`:
    later pages that, while in force, hide it whatever its own page says.'''
    blockers = ()


def _presence_watcher(data, map_id, presence, template, actor_index, project_condition, w, h, once=None, item_resolver=None):
    """Map controller that spawns the actor while its page conditions match."""
    if template is None:
        raise ValueError("Condition-based presence needs a placed actor, not an invisible region")
    from native_actor_lifecycle import compile_condition_presence_watcher
    from native_script_allocation import append_native_process
    if actor_index >= 127:
        raise ValueError("Conditional actor exceeds native owned-template selector capacity")
    convert = lambda test: test if test[0] == "flag" else ("code", _native_page_test(test[1], item_resolver))         if test[0] == "code" else ("test", project_condition(test[1]))
    native = lambda pages: [[convert(test) for test in page_tests] for page_tests in pages]
    code = compile_condition_presence_watcher(native(presence), actor_index, once,
                                              blockers=native(getattr(presence, "blockers", ()))) + b"\xff"
    data, watcher = append_native_process(data, map_id, "B", code)
    watcher.update(opcodes=_generated_opcodes(code), template_index=actor_index,
        pages=[[list(test) if test[0] == "flag" else [test[0] if test[0] == "code" else "project", test[1]] for test in page_tests] for page_tests in presence],
        region=[0, 0, w - 1, h - 1], gameplay_verified=False,
        limits=["Separate map controller; ordinary map scheduling still applies",
                "Respawn resets the actor's animation/AI state; native asset callbacks remain active",
                "Interaction while a switch changes needs emulator validation"])
    return data, watcher


def _once_per_visit(graph, definition, state_registry, state_slots, project_condition):
    """Spawn latch for the presence watcher. Enemies and bosses spawn once per visit, so a
    killed one stays dead until the room is entered again (Destroy after: for good)."""
    from project_state_runtime import compile_project_command
    once = graph.get('_once')
    if once is None:
        if definition.get('kind') not in ('enemy', 'boss') or (graph.get('native_placement') or {}).get('instant_respawn'):
            return None
        once = graph['_once_visit'] = graph.get('_once_visit') or {
            'killed': None, 'spawned': state_registry.create('switches', graph['name'] + ' spawned this visit')['id']}
    sw = lambda i, v: compile_project_command({'type': 'set_switch', 'switch_scope': 'project', 'switch_id': i, 'value': v}, state_registry, state_slots)
    sp = once['spawned']
    return {'clear_spawned': sw(sp, False), 'set_spawned': sw(sp, True),
            'set_killed': sw(once['killed'], True) if once['killed'] is not None else b'',
            'spawned_test': project_condition({'type': 'switch', 'switch_scope': 'project', 'switch_id': sp, 'value': True})}


def _generated_opcodes(code):
    from event_editor import SIZES
    from project_state_runtime import OPCODES
    sizes = {**SIZES, **OPCODES, 0xE5:1, 0xE6:2, 0xE7:2,0xE8:1,0xE9:3,0xEC:3,0xED:3,0xEE:1,0xEA:2,0xEB:2,0xEF:2,0xF0:1,0xF1:7,0xF2:9}
    opcodes = []; position = 0
    while position < len(code):
        opcode = code[position]; size = sizes.get(opcode)
        if not size or position + size > len(code):
            raise ValueError("Generated native code did not decode through its full length")
        opcodes.append(opcode); position += size
    return sorted(set(opcodes))


def validate_new_event(graph, *, recovered_activation=False, recovered_death=False, recovered_default_route=False):
    pages = graph.get("pages", [])
    if not isinstance(pages, list) or not pages or len(pages) > 32:
        raise ValueError("New native events need1..32 pages")
    if any(page.get("default_move_route") for page in pages) and not recovered_default_route:
        raise ValueError("Default movement route export needs a verified per-actor controller; the route was saved but cannot be silently ignored")
    page = pages[0]
    for current in pages:
        handlers=current.get('trigger_actions',[])
        if len(handlers)>1:
            raise ValueError('This page has multiple trigger tabs; exporting Interact/Touch together needs a multi-hook actor controller')
        for handler in handlers:
            if handler.get('trigger')=='hit':
                if not handler.get('hit_sources'):
                    raise ValueError('Choose at least one weapon or magic type for the Hit trigger')
                raise ValueError('Hit filters are saved in the event editor; a verified native attack-hit callback is not yet available for export')
        if current.get('idle_animation_enabled') is False and current.get('class_id',graph.get('class_id')) is not None:
            raise ValueError('Disabling the character idle animation is saved in the event editor; native per-instance idle-animation control is not yet verified for export')
    trigger = page.get("trigger", graph.get("trigger"))
    class_id = page.get("class_id", graph.get("class_id"))
    for other in pages:
        if other.get("trigger", graph.get("trigger")) != trigger:
            raise ValueError("Native pages currently share one trigger; per-page trigger changes are not compiled")
        if other.get("class_id", graph.get("class_id")) != class_id:
            raise ValueError("Native pages currently share one graphic class; conditional appearance changes are not compiled")
    placement = graph.get("native_placement", {})
    if not isinstance(placement, dict):
        raise ValueError("Native placement settings must be an object")
    if placement.get('act_as_npc'):
        raise ValueError("Act as NPC is saved in the event editor, but the game build cannot export it yet: an idle, harmless enemy with an NPC hitbox needs a new native controller that has not been built and tested. Untick Act as NPC to build this event")
    _presence_condition(graph)
    passive = len(pages) == 1 and not page.get("commands") and (not page.get("conditions") or _presence_condition(graph) is not None)
    if passive:
        pass  # Empty Contents does not install a synthetic interaction callback.
    elif trigger == 'activate' and not recovered_activation:
        raise ValueError('On activate actions need a verified object-specific state-change hook; touch/interact/deactivation are not equivalent')
    elif trigger == "death" and not recovered_death:
        raise ValueError("On death needs a verified death-only native hook; E also runs on deactivation and cannot be substituted")
    elif class_id is None:
        if trigger not in ("touch", "autorun", "parallel", "interact"):
            raise ValueError("Events without an actor currently use Player touch; choose an NPC/object for interaction")
    elif trigger not in ("interact", "touch") and not (trigger == 'activate' and recovered_activation) and not (trigger=='death' and recovered_death):
        raise ValueError("New actor events support interaction or touch")
    region = graph.get("region")
    if not isinstance(region, list) or len(region) != 4:
        raise ValueError("Event needs a map tile rectangle")
    x, y, w, h = region
    if not all(type(v) is int for v in region) or not 0 <= x <= 127 or not 0 <= y <= 127 or not 1 <= w <= 128 or not 1 <= h <= 128 or x + w > 128 or y + h > 128:
        raise ValueError("Native event region must fit the map's128-tile coordinate range")
    if (x, y, w, h) == (0, 0, 1, 1) and class_id is None:
        raise ValueError("A one-tile trigger at0,0 is the native terminator; enlarge or move the event")
    if class_id is not None and (w, h) != (1, 1):
        raise ValueError("Actor events use their native collision/interaction size; expanded rectangles currently require a separate Player touch event")
    return page, trigger, class_id, placement


def _destroys(graph):
    """An Erase Event command on any page or trigger tab (taken out by _take_erase)."""
    return bool(graph.get('_erase'))


def _take_erase(graph):
    """Remove Erase Event commands; the event then gets the destroy latch (gone for good)."""
    def strip(rows):
        found = False
        for r in rows or []:
            for key in ('then', 'else', 'commands'):
                if isinstance(r, dict) and isinstance(r.get(key), list):
                    kept = [c for c in r[key] if not (isinstance(c, dict) and c.get('type') == 'erase_event')]
                    found = strip(kept) or found or len(kept) != len(r[key])
                    r[key] = kept
        return found
    pages = graph.get('pages', [])
    if strip(list(pages) + [h for p in pages for h in p.get('trigger_actions', [])]):
        graph['_erase'] = True


def _walk(commands):
    for command in commands:
        yield command
        if command.get("type") == "if":
            yield from _walk(command.get("then", []))
            yield from _walk(command.get("else", []))
        elif command.get("type") == "repeat":
            yield from _walk(command.get("commands", []))


# Map-reset (temporary) game flags no original map script uses: one per
# dropped item, so a dropped item is there for the rest of this visit only.
FREE_DROP_FLAGS = tuple(0x87FE - i for i in range(31))


def _expand_item_pages(graphs, is_item_page, state_registry):
    """A page whose object is an item (2026-10-23): the game's own ground pickup,
    there while the page is in force. Picking it up is once only: the presence
    watcher latches it as collected when it is gone (as Destroy after for
    enemies), so it never comes back, room reloads included. The page's actions
    then run from a classless controller on the same map, after the pickup."""
    out = []
    for g in graphs:
        pages = g.get('pages') or []
        if len(pages) != 1 or not is_item_page(g, pages[0]):
            out.append(g); continue
        page = pages[0]
        handlers = [h for h in page.get('trigger_actions') or [] if h.get('commands')]
        commands = list(page.get('commands') or (handlers[0].get('commands') if handlers else []))
        trigger = page.get('trigger', g.get('trigger'))
        if trigger in ('death', 'activate'):
            commands = []   # 2026-10-23 (user): an item never dies or activates; these actions are ignored
        if not commands and not page.get('conditions') and not g.get('_blockers'):
            if trigger in ('death', 'activate'):
                g = deepcopy(g); g['pages'][0].update(commands=[], trigger_actions=[])
            out.append(g); continue   # a plain placed item: the game's own pickup, nothing else
        if trigger not in ('interact', 'touch', 'autorun', 'parallel', 'hit', 'death', 'activate', None):
            raise ValueError(f"{g.get('name') or 'Event'}: an item page's actions run when it is picked up or hit; "
                             f"the {trigger} trigger does not apply to an item (choose Player Touch, Interact or Hit)")
        hit_elements = None
        if trigger == 'hit' and commands:
            hit_elements = _hit_elements(g, page)
        for row in _walk(commands):
            if row.get('type') in ('change_animation', 'move_actor', 'face_actor'):   # these only act on This event
                raise ValueError(f"{g.get('name') or 'Event'}: the item is gone once picked up, so its actions cannot move, turn or animate This event")
        name = g.get('name') or 'Item'
        collected = state_registry.create('switches', f"{name} collected")['id']
        spawned = state_registry.create('switches', f"{name} spawned this visit")['id']
        item = deepcopy(g)
        item_page = item['pages'][0]
        item_page['conditions'] = list(item_page.get('conditions') or []) + [
            {'type': 'switch', 'switch_scope': 'project', 'switch_id': collected, 'value': False, 'operator': '=='}]
        item_page['commands'] = []; item_page['trigger_actions'] = []
        item['_once'] = {'killed': collected, 'spawned': spawned}
        out.append(item)
        if hit_elements is not None:
            # Hit: the item's own D (touched) program sets a request when the attack type matches
            # (native 87, as the game's lamps / torches / hit markers); a classless controller runs
            # the Hit actions once per request. The item stays a pickup.
            out.extend(_hit_area(g, item_page['conditions'], commands, hit_elements, state_registry))
        elif commands:
            done = state_registry.create('switches', f"{name} pickup actions done")['id']
            after = {k: deepcopy(v) for k, v in g.items() if k not in ('pages', '_blockers', '_once', '_once_visit')}
            after.update(id=f"{g['id']}/picked_up", name=f"{name} picked up", class_id=None,
                         trigger='autorun' if trigger == 'autorun' else 'parallel')
            after['pages'] = [{'id': f"{page.get('id', 'page')}:picked_up", 'name': 'Picked up', 'class_id': None,
                               'trigger': after['trigger'],
                               'conditions': [{'type': 'switch', 'switch_scope': 'project', 'switch_id': collected, 'value': True, 'operator': '=='},
                                              {'type': 'switch', 'switch_scope': 'project', 'switch_id': done, 'value': False, 'operator': '=='}],
                               'commands': [{'type': 'set_switch', 'switch_scope': 'project', 'switch_id': done, 'value': True}] + deepcopy(commands),
                               'trigger_actions': []}]
            out.append(after)
    return out


# Command 87 80 n: this entity touched by an attack of type table[n] (0x8009B80C = [1,2,3,4,5,5,6,7],
# docs/2026-10-21-sanctuary-wind-scroll.txt). Stock uses: lamps 0 = swords, map-10 markers 1 = flails,
# Bombable Rock 3 = bombs, torches 6 = fire wand / 7 = ice wand; 2 = arrows (type 3, lamp balance
# record notes). The Spring Bean has no known attack type.
HIT_ELEMENTS = {'sword': 0, 'flail': 1, 'bow': 2, 'bomb': 3, 'fire_wand': 6, 'ice_wand': 7}


def _hit_elements(g, page):
    handler = next((h for h in page.get('trigger_actions') or [] if h.get('trigger') == 'hit'), None)
    sources = (handler or {}).get('hit_sources') or []
    if not sources:
        raise ValueError(f"{g.get('name') or 'Event'}: choose at least one weapon or magic type for the Hit trigger")
    if 'spring_bean' in sources:
        raise ValueError(f"{g.get('name') or 'Event'}: a Spring Bean hit has no known native attack type; choose the other weapons or magic")
    return [HIT_ELEMENTS[source] for source in sources]


# The game's own invisible hit spot: map 10 entity 1 (global sprite 25, 8x7 transparent frame,
# hitbox 24x16x32), whose D programs test 87 (docs/2026-10-21-sanctuary-wind-scroll.txt).
# Ground items cannot be hit themselves: the attack scan 0x80039C10 skips actors whose
# +B4 (animation flags, 0x80039458) has 0x40, which the item pickups' animations have.
HIT_MARKER_SOURCE = (10, 1, bytes.fromhex('0000333b0140193656028200c981000000000000'))
HIT_MARKER_CLASS = '_hit_marker'


def _hit_area(g, conditions, commands, elements, state_registry, spots=True, request=None):
    """Hit actions (2026-10-23): one stock hit spot per tile of the area, there while the page is
    in force; its D (touched) program sets a request on a chosen attack type, and a classless
    controller runs the Hit actions once per request. spots=False: only the controller (the
    object itself sets `request`, _expand_hit_pages)."""
    x, y, rw, rh = g['region']
    if spots and rw * rh > 9:
        raise ValueError(f"{g.get('name') or 'Event'}: a Hit area can cover at most 9 tiles (each tile is one native hit spot)")
    name = g.get('name') or 'Event'
    if request is None:
        request = state_registry.create('switches', f"{name} hit")['id']
    base = {k: deepcopy(v) for k, v in g.items() if k not in ('pages', '_once', '_once_visit', 'region', 'class_id', 'trigger', '_hit_on_object')}
    out = []
    for dy in range(rh if spots else 0):
        for dx in range(rw):
            spot = deepcopy(base)
            spot.update(id=f"{g['id']}/hit_spot{len(out) + 1}", name=f"{name} hit spot", region=[x + dx, y + dy, 1, 1],
                        class_id=HIT_MARKER_CLASS, trigger='touch', _hit_marker={'request': request, 'elements': list(elements)})
            spot['pages'] = [{'id': f"hit_spot{len(out) + 1}", 'name': 'Hit spot', 'class_id': HIT_MARKER_CLASS, 'trigger': 'touch',
                              'conditions': deepcopy(conditions or []), 'commands': [], 'trigger_actions': []}]
            out.append(spot)
    after = {k: deepcopy(v) for k, v in g.items() if k not in ('pages', '_blockers', '_once', '_once_visit', '_hit_on_object')}
    after.update(id=f"{g['id']}/hit", name=f"{name} hit", class_id=None, trigger='parallel')
    after['pages'] = [{'id': 'hit', 'name': 'Hit', 'class_id': None, 'trigger': 'parallel',
                       'conditions': [{'type': 'switch', 'switch_scope': 'project', 'switch_id': request, 'value': True, 'operator': '=='}],
                       'commands': [{'type': 'set_switch', 'switch_scope': 'project', 'switch_id': request, 'value': False}] + deepcopy(commands)
                                   + HIT_SETTLE(request),
                       'trigger_actions': []}]
    return out + [after]


# Objects that move (lift / throw / push) and take the hit on themselves: stock records with no
# A-F hooks (DATAS: Barrel 290 map 22 ent 21, Wooden Crate 292 map 61 ent 15, Rock 293), and the
# Stool (Pushable) (A 1A 03 FF from map 137 entity 2, kept after the 2A).
HIT_ON_OBJECT_CLASSES = {290, 292, 293}


# 2026-10-24 (BizHawk, hit-objects a2 / x1): the Square press that closes a Hit text also swings
# the weapon at the object again (shot x1 s13), which set the request again, so the actions ran
# twice. The controller waits out that swing and clears the request once more.
HIT_SETTLE_FRAMES = 30
HIT_SETTLE = lambda request: [{'type': 'wait', 'frames': HIT_SETTLE_FRAMES},
                              {'type': 'set_switch', 'switch_scope': 'project', 'switch_id': request, 'value': False}]


def _expand_hit_pages(graphs, state_registry, is_hit_object=lambda g, p: False, moves=lambda g, p: False):
    """A Hit page with no object or graphic: native hit spots on its tile area.
    2026-10-24: a Hit page on a placed object (crate, barrel, statue, chest ...; is_hit_object):
    the object is placed as the game's own (no authored hooks, so its stock reaction stays) and
    the hit spot goes on its tile, there while the page is in force.
    Objects that can be lifted, thrown, pushed or rolled (moves): the spot's C copies the object's
    position every frame and leaves when the object is gone (native_hit_follow)."""
    out = []
    for g in graphs:
        pages = g.get('pages') or []
        page = pages[0] if len(pages) == 1 else {}
        if page.get('trigger', g.get('trigger')) != 'hit':
            out.append(g); continue
        on_object = page.get('class_id', g.get('class_id')) is not None
        if on_object and not is_hit_object(g, page):
            out.append(g); continue
        handlers = [h for h in page.get('trigger_actions') or [] if h.get('commands')]
        commands = list(page.get('commands') or (handlers[0].get('commands') if handlers else []))
        if on_object:
            obj = deepcopy(g)
            obj['trigger'] = 'interact'
            obj['pages'][0].update(trigger='interact', commands=[], trigger_actions=[   # its Activate / Deactivate tabs stay (Nirude Face Statue)
                h for h in page.get('trigger_actions') or [] if h.get('trigger') in ('activate', 'deactivate') and h.get('commands')])
            out.append(obj)
        if not commands:
            continue   # nothing happens on a hit
        area = _hit_area(g, page.get('conditions'), commands, _hit_elements(g, page), state_registry)
        if on_object and moves(g, page):
            for spot in area:
                if spot.get('_hit_marker'):spot['_hit_marker']['follow'] = g['id']   # follows the object, goes with it
        out.extend(area)
    return out


def _hit_marker_record(data, original, map_id, x, y, height):
    m, index, raw = HIT_MARKER_SOURCE
    from native_class_placement import record_cluster
    if original is not None and record_cluster(original, m)['entities'][index] != raw:
        raise ValueError('The game\'s own hit spot (map 10 entity 1) differs in this game data')
    from native_class_placement import global_sprite_available
    if not global_sprite_available(data, raw[6]):
        raise ValueError('The game\'s own hit spot graphic (global sprite 25) is missing')
    row = bytearray(raw)
    row[7:10] = bytes((x * 2, y * 2, height * 2))
    row[10:16] = bytes(6)   # its own programs are set by the caller
    return row


def _hit_touched_program(elements, set_request):
    """D (touched): set the hit request when the attack is one of the chosen types."""
    from event_logic_compile import _Assembler
    d = _Assembler()
    for element in elements:
        d.data.extend(bytes((0x87, 0x80, element))); d.branch(3, 'hit')
    d.branch(2, 'end')
    d.label('hit'); d.data.extend(set_request)
    d.label('end'); d.data.append(0xFF)
    return d.finish()


# What the switches' rebuilt (recovered) activation controllers compile themselves.
RECOVERED_SWITCH_COMMANDS = {'change_money', 'wait', 'set_switch', 'set_variable', 'if', 'deactivate_switch'}


def _hit_switch_requests(graphs, definitions, hit_switches, state_registry):
    """2026-10-24: a switch the game itself hits (lever, wall, ignition, toggle, lamp) whose Hit
    actions hold more than its rebuilt controller compiles (text, items ...): the switch's own
    Activate sets a "<event> hit" request and a classless controller runs the actions, once per
    request. The switch keeps its native reaction."""
    out = []
    for g in graphs:
        pages = g.get('pages') or []
        for n, p in enumerate(pages):
            d = definitions.get(p.get('class_id', g.get('class_id')), {})
            if d.get('kind') != 'object' or d.get('source', {}).get('catalogue_index') not in hit_switches or d.get('source', {}).get('variant'):
                continue
            handlers = [h for h in p.get('trigger_actions') or [] if h.get('trigger') == 'activate' and h.get('commands')]
            commands = list(p.get('commands') or (handlers[0].get('commands') if handlers else []))
            if not commands or all(row.get('type') in RECOVERED_SWITCH_COMMANDS for row in _walk(commands)):
                continue
            name = g.get('name') or 'Switch'
            request = state_registry.create('switches', f"{name} hit")['id']
            ask = [{'type': 'set_switch', 'switch_scope': 'project', 'switch_id': request, 'value': True}]
            p['commands'] = deepcopy(ask)
            for h in p.get('trigger_actions') or []:
                if h.get('trigger') == 'activate':h['commands'] = deepcopy(ask)
            after = {k: deepcopy(v) for k, v in g.items() if k not in ('pages', '_blockers', '_once', '_once_visit', '_release_commands')}
            after.update(id=f"{g['id']}/hit{n + 1}", name=f"{name} hit", class_id=None, trigger='parallel')
            after['pages'] = [{'id': 'hit', 'name': 'Hit', 'class_id': None, 'trigger': 'parallel',
                               'conditions': [{'type': 'switch', 'switch_scope': 'project', 'switch_id': request, 'value': True, 'operator': '=='}],
                               'commands': [{'type': 'set_switch', 'switch_scope': 'project', 'switch_id': request, 'value': False}] + deepcopy(commands),
                               'trigger_actions': []}]
            out.append(after)
    return out


# Weapons that flip a placed Switch (Lever) 305 natively (BizHawk hit-objects b4, 2026-10-24:
# sword yes; flail, bow, ice wand, fire wand no).
LEVER_NATIVE_SOURCES = {'sword'}


def _lever_other_weapons(graphs, definitions, state_registry):
    """2026-10-24: a lever's Hit actions run on its native flip (Activate, sword). The other weapons
    ticked on its Hit tab do not flip it; they get the stock hit spot on its tile, so their hits run
    the Hit actions too (the lever does not move, as in the game)."""
    out = []
    for g in graphs:
        pages = g.get('pages') or []
        if len(pages) != 1:
            continue
        p = pages[0]
        d = definitions.get(p.get('class_id', g.get('class_id')), {})
        if d.get('kind') != 'object' or d.get('source', {}).get('catalogue_index') != 305 or d.get('source', {}).get('variant'):
            continue
        handler = next((h for h in p.get('trigger_actions') or [] if h.get('trigger') == 'hit'), None)
        if handler is None and p.get('trigger') != 'hit':
            continue
        commands = list((handler or {}).get('commands') or p.get('commands') or [])
        extra = [s for s in (handler or {}).get('hit_sources') or [] if s not in LEVER_NATIVE_SOURCES and s in HIT_ELEMENTS]
        if commands and extra:
            out.extend(_hit_area(dict(g, id=f"{g['id']}/weapons"), p.get('conditions'), commands,
                                 [HIT_ELEMENTS[s] for s in extra], state_registry))
    return out


def _nirude_faces(graphs, definitions, state_registry, face_states):
    """Nirude Face Statue (user 2026-10-24, native_nirude_face): it cannot be destroyed until it
    is activated (Active By Default, or Activate Switch from another event); then it breaks the
    stock way (15 hits) and stays broken. Breaking runs the Deactivate actions once; becoming
    active runs the Activate actions once. Both run from classless controllers on its map."""
    from native_nirude_face import is_face
    out = []
    for g in graphs:
        pages = g.get('pages') or []
        if not pages or not is_face(definitions.get(pages[0].get('class_id', g.get('class_id')))):
            continue
        if len(pages) != 1:
            raise ValueError(f"{g.get('name')}: a Nirude Face Statue takes one page (its Activate and Deactivate actions)")
        page = pages[0]; name = g.get('name') or 'Nirude Face Statue'
        tabs = {h.get('trigger'): list(h.get('commands') or []) for h in page.get('trigger_actions') or []}
        if page.get('trigger') in ('activate', 'deactivate') and not tabs.get(page['trigger']):
            tabs[page['trigger']] = list(page.get('commands') or [])
        state = state_registry.create('switches', f"{name} object state",
                                      initial_value=bool((g.get('native_placement') or {}).get('active_by_default')))['id']
        broken = state_registry.create('switches', f"{name} broken")['id']
        g['_face'] = {'state': state, 'broken': broken}
        face_states[g['id']] = state
        page.update(trigger='interact', commands=[], trigger_actions=[])
        g['trigger'] = 'interact'
        for trigger, flag, label in (('activate', state, 'activated'), ('deactivate', broken, 'broken')):
            commands = tabs.get(trigger)
            if not commands:
                continue
            done = state_registry.create('switches', f"{name} {label} actions done")['id']
            after = {k: deepcopy(v) for k, v in g.items() if k not in ('pages', '_blockers', '_once', '_once_visit', '_face', '_release_commands')}
            after.update(id=f"{g['id']}/{label}", name=f"{name} {label}", class_id=None, trigger='parallel')
            after['pages'] = [{'id': label, 'name': label.title(), 'class_id': None, 'trigger': 'parallel',
                               'conditions': [{'type': 'switch', 'switch_scope': 'project', 'switch_id': flag, 'value': True, 'operator': '=='},
                                              {'type': 'switch', 'switch_scope': 'project', 'switch_id': done, 'value': False, 'operator': '=='}],
                               'commands': [{'type': 'set_switch', 'switch_scope': 'project', 'switch_id': done, 'value': True}] + deepcopy(commands),
                               'trigger_actions': []}]
            out.append(after)
    return out


def _nirude_statue_variants(graphs, definitions, state_registry, face_states):
    """Shooting Nirude Face Statues (Fire / Homing Fire / Laser, native_nirude_statue_variants,
    user 2026-10-24): the plain face's activation (_nirude_faces) for these entries: dormant until
    activated, Activate actions once on becoming active, Deactivate actions once when broken.
    Their object state joins face_states, so Activate / Deactivate Switch reaches them."""
    from native_nirude_statue_variants import variant_of
    out = []
    for g in graphs:
        pages = g.get('pages') or []
        if not pages or not variant_of(definitions.get(pages[0].get('class_id', g.get('class_id')))):
            continue
        if len(pages) != 1:
            raise ValueError(f"{g.get('name')}: a shooting Nirude Face Statue takes one page (its Activate and Deactivate actions)")
        page = pages[0]; name = g.get('name') or 'Nirude Face Statue'
        tabs = {h.get('trigger'): list(h.get('commands') or []) for h in page.get('trigger_actions') or []}
        if page.get('trigger') in ('activate', 'deactivate') and not tabs.get(page['trigger']):
            tabs[page['trigger']] = list(page.get('commands') or [])
        state = state_registry.create('switches', f"{name} object state",
                                      initial_value=bool((g.get('native_placement') or {}).get('active_by_default', True)))['id']   # missing: on (user 2026-10-24)
        broken = state_registry.create('switches', f"{name} broken")['id']
        g['_statue'] = {'state': state, 'broken': broken}
        face_states[g['id']] = state
        page.update(trigger='interact', commands=[], trigger_actions=[])
        g['trigger'] = 'interact'
        for trigger, flag, label in (('activate', state, 'activated'), ('deactivate', broken, 'broken')):
            commands = tabs.get(trigger)
            if not commands:
                continue
            done = state_registry.create('switches', f"{name} {label} actions done")['id']
            after = {k: deepcopy(v) for k, v in g.items() if k not in ('pages', '_blockers', '_once', '_once_visit', '_statue', '_release_commands')}
            after.update(id=f"{g['id']}/{label}", name=f"{name} {label}", class_id=None, trigger='parallel')
            after['pages'] = [{'id': label, 'name': label.title(), 'class_id': None, 'trigger': 'parallel',
                               'conditions': [{'type': 'switch', 'switch_scope': 'project', 'switch_id': flag, 'value': True, 'operator': '=='},
                                              {'type': 'switch', 'switch_scope': 'project', 'switch_id': done, 'value': False, 'operator': '=='}],
                               'commands': [{'type': 'set_switch', 'switch_scope': 'project', 'switch_id': done, 'value': True}] + deepcopy(commands),
                               'trigger_actions': []}]
            out.append(after)
    return out


def _drop_unfired_pages(graphs):
    """2026-10-23 (user): Death / Activate pages with no object or graphic never fire; they are
    ignored and the build goes on."""
    out = []
    for g in graphs:
        pages = g.get('pages') or []
        unfired = lambda p: p.get('class_id', g.get('class_id')) is None and p.get('trigger', g.get('trigger')) in ('death', 'activate')
        if pages and all(unfired(p) for p in pages):
            continue
        out.append(g)
    return out


def _expand_item_drops(graphs):
    """Give Item with Drop Item On Map: instead of adding the item straight to
    the inventory, the item appears on the map where the event is, as the
    game's own ground pickup (walk over it to collect it, with the game's own
    message). Built as a hidden placed item that shows once its flag is set."""
    out = list(graphs); used = {}
    for graph in graphs:
        n = 0
        pages = graph.get("pages", [])
        rows = [c for p in pages for c in _walk(list(p.get("commands", [])) + [x for t in p.get("trigger_actions", []) for x in t.get("commands", [])])]
        for command in rows:
            if command.get("type") != "give_item" or not command.get("drop_on_map"):
                continue
            map_id = graph.get("map_id"); taken = used.setdefault(map_id, set())
            free = [f for f in FREE_DROP_FLAGS if f not in taken]
            if not free:
                raise ValueError("Too many Drop Item On Map commands on this map")
            if len(free) < 2:
                raise ValueError("Too many Drop Item On Map commands on this map")
            flag, collected = free[0], free[1]; taken.update((flag, collected)); n += 1
            x, y = graph.get("region", [0, 0])[:2]
            item_class = command.get("item_class_id")
            out.append({"id": f"{graph['id']}/drop{n}", "name": f"{graph.get('name','Event')} dropped item {n}",
                        "map_id": map_id, "region": [x, y, 1, 1], "class_id": None, "trigger": "interact",
                        "switch_id": None, "native_placement": {},
                        "pages": [{"id": "page:0001", "name": "Dropped", "trigger": "interact", "class_id": item_class,
                                   "conditions": [{"type": "switch", "native_flag_operand": flag, "value": True},
                                                  {"type": "switch", "native_flag_operand": collected, "value": False}],
                                   "commands": [], "trigger_actions": []}]})
            # Stepping onto the dropped item (which picks it up) latches it as
            # collected, so it never comes back on later visits (user 2026-10-18).
            out.append({"id": f"{graph['id']}/drop{n}/taken", "name": f"{graph.get('name','Event')} dropped item {n} taken",
                        "map_id": map_id, "region": [x, y, 1, 1], "class_id": None, "trigger": "touch",
                        "switch_id": None, "native_placement": {},
                        "pages": [{"id": "page:0001", "name": "Taken", "trigger": "touch", "class_id": None,
                                   "conditions": [{"type": "switch", "native_flag_operand": flag, "value": True},
                                                  {"type": "switch", "native_flag_operand": collected, "value": False}],
                                   "commands": [],
                                   "trigger_actions": [{"trigger": "touch", "hit_sources": [], "destroy_after": False,
                                       "commands": [{"type": "set_switch", "native_flag_operand": collected, "value": True}]}]}]})
            command.clear()
            command.update({"type": "set_switch", "native_flag_operand": flag, "value": True})
    return out


def _expand_spawn_templates(graphs, definitions):
    """Each placed actor whose custom AI has spawned attacks gets one hidden
    template per spawned class on its map (not created at map load); the
    attack spawns it at its own position with native 8B."""
    out = list(graphs)
    for graph in graphs:
        chosen = (graph.get("native_placement") or {}).get("spawned_class")
        if chosen:
            # Generator "Spawns" option (2026-10-22): the chosen class becomes a dormant
            # template on the generator's tile; its copied program spawns that instead.
            if chosen not in definitions:
                raise ValueError(f"{graph.get('name')}: the class it spawns no longer exists")
            x, y = graph.get("region", [0, 0])[:2]
            out.append({"id": f"{graph['id']}/spawn/{chosen}", "name": f"{graph.get('name')} spawn", "map_id": graph["map_id"],
                        "region": [x, y, 1, 1], "class_id": None, "trigger": "interact", "switch_id": None,
                        "native_placement": {"spawn_of": graph["id"], "spawn_class": chosen, "generator_spawn": True},
                        "pages": [{"id": "page:0001", "name": "Spawn", "trigger": "interact", "class_id": chosen,
                                   "conditions": [], "commands": [], "trigger_actions": []}]})
        for page in graph.get("pages", [])[:1]:
            d = definitions.get(page.get("class_id") or graph.get("class_id"), {})
            ai = (d.get("data") or {}).get("custom_ai") or {}
            if ai.get("mode") != "custom":
                continue
            for cls in {a.get("spawn_class") for a in ai.get("attacks") or [] if a.get("type") == "spawned" and a.get("spawn_class")}:
                if cls not in definitions:
                    raise ValueError(f"{d.get('name')}: its spawned attack class no longer exists")
                x, y = graph.get("region", [0, 0])[:2]
                out.append({"id": f"{graph['id']}/spawn/{cls}", "name": f"{graph.get('name')} spawn", "map_id": graph["map_id"],
                            "region": [x, y, 1, 1], "class_id": None, "trigger": "interact", "switch_id": None,
                            "native_placement": {"spawn_of": graph["id"], "spawn_class": cls},
                            "pages": [{"id": "page:0001", "name": "Spawn", "trigger": "interact", "class_id": cls,
                                       "conditions": [], "commands": [], "trigger_actions": []}]})
    # Database spawn attacks (native_animation_spawns) whose spawned class has custom behaviour
    # (custom AI, lifetime): one dormant template per class on each map where an owner of the
    # attack is placed, or is a part of a placed boss; the attack spawns it (user 2026-10-26).
    from content_database import ContentDatabase
    by_catalogue = {}
    for d in definitions.values():
        c = (d.get("source") or {}).get("catalogue_index")
        for row in (d.get("data") or {}).get("spawn_attacks") or []:
            target = definitions.get(row.get("class_id")) or {}
            if type(c) is int and ((target.get("data") or {}).get("custom_ai") or {}).get("mode") == "custom":
                by_catalogue.setdefault(c, set()).add(row["class_id"])
    done = {(g["map_id"], (g.get("native_placement") or {}).get("spawn_class")) for g in out
            if (g.get("native_placement") or {}).get("spawn_class")}
    for graph in graphs:
        page = (graph.get("pages") or [{}])[0]
        c = (definitions.get(page.get("class_id") or graph.get("class_id")) or {}).get("source", {}).get("catalogue_index")
        if type(c) is not int:
            continue
        for owner in (c,) + tuple(ContentDatabase.BOSS_PARTS.get(c, ())):
            for cls in sorted(by_catalogue.get(owner, ())):
                if (graph["map_id"], cls) in done:
                    continue
                done.add((graph["map_id"], cls))
                x, y = graph.get("region", [0, 0])[:2]
                out.append({"id": f"{graph['id']}/spawn/{cls}", "name": f"{graph.get('name')} spawn", "map_id": graph["map_id"],
                            "region": [x, y, 1, 1], "class_id": None, "trigger": "interact", "switch_id": None,
                            "native_placement": {"spawn_of": graph["id"], "spawn_class": cls},
                            "pages": [{"id": "page:0001", "name": "Spawn", "trigger": "interact", "class_id": cls,
                                       "conditions": [], "commands": [], "trigger_actions": []}]})
    return out


_AI_SPAWNS = None


def _player_box(graph, record):
    """Launcher / Four-Way Turret trigger options (native_placement): always_fire, or
    trigger_range tiles around the placed record (behavior_transplant.program_span)."""
    from native_freezable_flame import FREEZABLE_CATALOGUES
    placement = graph.get("native_placement") or {}
    if record[6] + (256 if record[5] & 128 else 0) not in FREEZABLE_CATALOGUES:
        return None
    if placement.get("always_fire"):
        return "always"
    r = placement.get("trigger_range")
    if r is None:
        return None
    if type(r) is not int or not 1 <= r <= 64:
        raise ValueError("Trigger range must be 1..64 tiles")
    return (record[7] // 2, record[8] // 2, r)


def ai_spawned_slots(data, home, catalogue):
    """Map-local sprite slots the class's own game code creates (spawn_warp_entity
    with a map sprite number, research/us_decomp/ai), followed through what those
    create in turn. Zorgia (C44) creates 0xD5 Zorgia Magic, 0xFE Magic Circle, 0xFF
    Projectiles."""
    global _AI_SPAWNS
    import re
    from pathlib import Path
    from event_vm_compatibility import sprite_callbacks
    if _AI_SPAWNS is None:
        _AI_SPAWNS = {}
        folder = Path(__file__).resolve().parents[1] / 'research/us_decomp/ai'
        for f in folder.glob('*_*.c'):
            m = re.match(r'[0-9A-F]+_([A-F])(\d+)\.c$', f.name)
            if not m:
                continue
            found = {int(x, 0) for x in re.findall(r'spawn_warp_entity\([^,]+,\s*1,\s*(0x[0-9A-Fa-f]+|\d+)\s*,', f.read_text(errors='ignore'))}
            _AI_SPAWNS[(m.group(1), int(m.group(2)))] = found
    seen, todo = set(), [catalogue]
    while todo:
        cat = todo.pop()
        try:
            callbacks = sprite_callbacks(data, home, cat)
        except Exception:
            continue
        for bank_hook in callbacks:
            for slot in _AI_SPAWNS.get(tuple(bank_hook), ()):
                if slot not in seen and slot != catalogue - 256:
                    seen.add(slot); todo.append(256 + slot)
    return sorted(seen)


_AI_EFFECTS = None


def ai_local_effects(data, home, catalogue):
    """Map-local effect sprites (bank 1) the class's own game code shows, by their fixed
    index in the map's effect bank (spawn_effect(1, n, ...), research/us_decomp/ai), for the
    class and the parts it creates. Melzas (C55) waits on local effect 0 before he fights."""
    global _AI_EFFECTS
    import re
    from pathlib import Path
    from event_vm_compatibility import sprite_callbacks
    if _AI_EFFECTS is None:
        _AI_EFFECTS = {}
        folder = Path(__file__).resolve().parents[1] / 'research/us_decomp/ai'
        for f in folder.glob('*_*.c'):
            m = re.match(r'[0-9A-F]+_([A-F])(\d+)\.c$', f.name)
            if m:
                found = {int(x, 0) for x in re.findall(r'spawn_effect(?:_on)?\(\s*1\s*,\s*(0x[0-9A-Fa-f]+|\d+)\s*,', f.read_text(errors='ignore'))}
                _AI_EFFECTS[(m.group(1), int(m.group(2)))] = found
    found = set()
    for cat in [catalogue] + [256 + s for s in ai_spawned_slots(data, home, catalogue)]:
        try:
            callbacks = sprite_callbacks(data, home, cat)
        except Exception:
            continue
        for bank_hook in callbacks:
            found |= _AI_EFFECTS.get(tuple(bank_hook), set())
    return sorted(found)


def _import_boss_effects(data, target, home, catalogue, name, cache):
    """Copy the home map's local effect sprites the boss's code uses, each at the SAME index
    of the target's effect bank (the native code names them by number): effects 0..n of the
    home map are copied in order. An index the target already uses for another sprite is an
    error, since the boss would show the wrong effect."""
    from block_switch import effect_assets, import_local_effect
    needed = ai_local_effects(data, home, catalogue)
    if not needed:
        return data, []
    reports = []
    for index in range(max(needed) + 1):
        if cache.get((target, index)) == home:
            continue
        try:
            present = len(effect_assets(data, target, 0)['table'])
        except ValueError:
            present = 0
        if index < present:
            if cache.get((target, index)) is None and _effect_bytes(data, target, index) == _effect_bytes(data, home, index):
                cache[(target, index)] = home; continue
            raise ValueError(f"{name}: its fight shows effect sprite {index} of map {home}, but this map already "
                             f"uses effect sprite {index} for something else; place {name} on a map without its own effects")
        if index > present:
            raise ValueError(f"{name}: its effect sprites must keep their numbers; this map's effect bank has a gap")
        try:
            data, slot = import_local_effect(data, target, home, index)
        except ValueError as exc:
            raise ValueError(f"{name}: could not bring its effect sprite {index} onto map {target} ({exc})")
        if slot != index:
            raise ValueError(f"{name}: effect sprite {index} landed at {slot}")
        cache[(target, index)] = home
        reports.append(dict(effect_sprite=index, from_map=home, used_by_ai=index in needed))
    return data, reports


def _effect_bytes(data, map_id, index):
    from block_switch import effect_assets
    try:
        a = effect_assets(data, map_id, index)
    except ValueError:
        return None
    return bytes(data[a['record']:a['end']])


def boss_companion_slots(data, home, catalogue):
    """Local sprite slots of map `home` that no placed character there uses
    (besides the boss itself): what the boss's own code spawns."""
    import struct as _st
    from local_sprite_import import layout
    from native_class_placement import record_cluster
    b, h, s, e, sh = layout(data, home)
    placed = {raw[6] for raw in record_cluster(data, home)['entities'] if raw[5] & 128}
    slots = []
    for i in range((sh[4] - sh[3]) // 4):
        pointer = _st.unpack_from('<i', data, s + sh[3] + 4 * i)[0]
        if pointer not in (0, -1) and i not in placed and i != catalogue - 256:
            slots.append(i)
    present = {i for i in range((sh[4] - sh[3]) // 4) if _st.unpack_from('<i', data, s + sh[3] + 4 * i)[0] not in (0, -1)}
    return sorted(set(slots) | (set(ai_spawned_slots(data, home, catalogue)) & present))


def _import_boss_companions(data, target, home, catalogue, local_slots, name, slots=None):
    from local_sprite_import import import_local_sprite, layout
    import struct as _st
    reports = []
    for slot in (boss_companion_slots(data, home, catalogue) if slots is None else slots):
        if slot in local_slots:
            raise ValueError(f"{name}: its fight uses sprite slot {slot + 256}, which another character on this map uses")
        try:
            data, report = import_local_sprite(data, target, home, slot, keep=local_slots | {catalogue - 256})
        except ValueError as exc:
            raise ValueError(f"{name}: could not bring its part / projectile sprite {slot + 256} onto map {target} ({exc})")
        reports.append(dict(report, catalogue_index=slot + 256))
    return data, reports


def _self_switches(graphs, registry):
    """Self Switches A-D (each event's own private switches, never story flags):
    Control Self Switch and the Self Switch page condition become project
    switches "<event> Self Switch A" (one per event and letter)."""
    ids = {}
    names = {g.get('id'): g.get('name') or 'Event' for g in graphs}
    def sid(gid, letter):
        if letter not in ('A', 'B', 'C', 'D'):
            raise ValueError('Self Switch must be A, B, C or D')
        if (gid, letter) not in ids:
            ids[(gid, letter)] = registry.create('switches', f"{names.get(gid, 'Event')} Self Switch {letter}")['id']
        return ids[(gid, letter)]
    def fix_condition(c, g):
        if isinstance(c, dict) and c.get('type') == 'self_switch':
            target = g['id'] if c.get('event_id') in (None, 'this_event') else c['event_id']
            letter, value = c.get('letter', 'A'), bool(c.get('value', True))
            c.clear(); c.update(type='switch', switch_scope='project', switch_id=sid(target, letter), value=value, operator='==')
    def fix_commands(rows, g):
        for r in rows or []:
            if not isinstance(r, dict):
                continue
            if r.get('type') == 'set_self_switch':
                target = g['id'] if r.get('event_id') in (None, 'this_event') else r['event_id']
                letter, value = r.get('letter', 'A'), bool(r.get('value', True))
                r.clear(); r.update(type='set_switch', switch_scope='project', switch_id=sid(target, letter), value=value)
            if r.get('type') == 'if':
                fix_condition(r.get('condition'), g)
            for key in ('then', 'else', 'commands'):
                fix_commands(r.get(key), g)
    for g in graphs:
        for p in g.get('pages') or []:
            for c in p.get('conditions') or []:
                fix_condition(c, g)
            fix_commands(p.get('commands'), g)
            for h in p.get('trigger_actions') or []:
                fix_commands(h.get('commands'), g)
        fix_commands(g.get('_release_commands'), g)
    return ids


def _visibility_and_graphics(graphs, registry):
    """Show / Hide Event and Change Event Graphic had no native compiler (stress test
    2026-10-21). Both become what already runs in the game: a project switch and page
    conditions. Show / Hide: switch "<event> shown" (ON at start); the command sets it and every
    page of the target needs it ON. Change Graphic: switch "<event> graphic <class>"; the command
    turns it ON and the target gets a later page (a copy of its last page) with that graphic,
    shown while the switch is ON (the highest page whose conditions hold is in force)."""
    by_id = {g.get('id'): g for g in graphs}
    shown, graphic, made = {}, {}, []   # made: Create Database Object instances

    def target(row, g):
        t = row.get('event_id') or row.get('target')
        return g if t in (None, 'this_event') else by_id.get(t)

    def walk(rows, g):
        for r in rows or []:
            if not isinstance(r, dict):
                continue
            if r.get('type') == 'set_event_active' and target(r, g) is not None:
                t = target(r, g)
                if t['id'] not in shown:
                    shown[t['id']] = registry.create('switches', f"{t.get('name') or 'Event'} shown", initial_value=True)['id']
                active = bool(r.get('active'))
                r.clear(); r.update(type='set_switch', switch_scope='project', switch_id=shown[t['id']], value=active)
            elif r.get('type') == 'spawn_class' and r.get('class_id') and isinstance(r.get('position'), list):
                # Create Database Object: one hidden instance at that tile, shown from then on
                x, y = r['position'][:2]; sid = registry.create('switches', f"{g.get('name') or 'Event'} created {r['class_id']} {x},{y}")['id']
                made.append(dict(id=f"{g['id']}#spawn{len(made) + 1}", name=f"Created by {g.get('name') or 'event'}",
                                 map_id=g['map_id'], region=[x, y, 1, 1], class_id=r['class_id'], trigger='interact',
                                 native_placement={'facing': 'down'},
                                 pages=[{'id': f"page:spawn{len(made) + 1}", 'name': 'Created', 'trigger': 'interact',
                                         'class_id': r['class_id'], 'commands': [], 'trigger_actions': [],
                                         'conditions': [{'type': 'switch', 'switch_scope': 'project', 'switch_id': sid,
                                                         'value': True, 'operator': '=='}]}]))
                r.clear(); r.update(type='set_switch', switch_scope='project', switch_id=sid, value=True)
            elif r.get('type') == 'change_graphic' and target(r, g) is not None:
                t = target(r, g); key = (t['id'], r.get('graphic'))
                if key not in graphic:
                    graphic[key] = registry.create('switches', f"{t.get('name') or 'Event'} graphic {r.get('graphic')}")['id']
                r.clear(); r.update(type='set_switch', switch_scope='project', switch_id=graphic[key], value=True)
            for k in ('then', 'else', 'commands'):
                walk(r.get(k), g)
    for g in graphs:
        for p in g.get('pages') or []:
            walk(p.get('commands'), g)
            for h in p.get('trigger_actions') or []:
                walk(h.get('commands'), g)
    for (gid, cls), sid in graphic.items():
        g = by_id[gid]; page = deepcopy(g['pages'][-1])
        page['class_id'] = cls
        page['conditions'] = [c for c in page.get('conditions') or [] if c.get('switch_id') != sid] + [
            {'type': 'switch', 'switch_scope': 'project', 'switch_id': sid, 'value': True, 'operator': '=='}]
        page['id'] = f"{page.get('id', 'page')}:graphic"
        g['pages'].append(page)
    for gid, sid in shown.items():
        for p in by_id[gid].get('pages') or []:
            p['conditions'] = list(p.get('conditions') or []) + [
                {'type': 'switch', 'switch_scope': 'project', 'switch_id': sid, 'value': True, 'operator': '=='}]
    graphs.extend(made)


def _npc_page(g):
    """Act As NPC: the page's actions run when Alundra talks to it."""
    g['trigger'] = 'interact'
    for p in g.get('pages') or []:
        handlers = [h for h in p.get('trigger_actions') or [] if h.get('commands')]
        commands = list(p.get('commands') or (handlers[0].get('commands') if handlers else []))
        p['trigger'] = 'interact'; p['commands'] = commands
        p['trigger_actions'] = [{'trigger': 'interact', 'commands': deepcopy(commands), 'hit_sources': [], 'destroy_after': False}]


def _split_pages(graphs, must_split=lambda g: False):
    """An event whose pages show different characters (another database entry,
    or Act As NPC on one page) is built as one placed actor per page, each there
    while its page is the one in force (the highest page whose conditions hold):
    page n shows while its own conditions hold and no later page's do. Pages
    after it may have one switch condition each (Self Switch included)."""
    out = []
    for g in graphs:
        pages = g.get('pages') or []
        classes = {p.get('class_id', g.get('class_id')) for p in pages}
        triggers = {p.get('trigger', g.get('trigger')) for p in pages}
        # 2026-10-23: pages with different triggers, and item pages (each page's
        # item is its own pickup), are split the same way.
        if len(pages) < 2 or (len(classes) < 2 and len(triggers) < 2 and not must_split(g)
                              and not any(p.get('act_as_npc') for p in pages)):
            if pages and pages[0].get('act_as_npc'):
                g['_act_as_npc'] = True; _npc_page(g)
            out.append(g)
            continue
        for i, p in enumerate(pages):
            conditions = deepcopy(p.get('conditions') or [])
            shown = True; blockers = []
            for later in pages[i + 1:]:
                tests = later.get('conditions') or []
                if not tests:
                    shown = False   # a later page with no conditions is always in force
                    break
                if len(tests) == 1 and tests[0].get('type') == 'switch':
                    flipped = dict(tests[0]); flipped['value'] = not tests[0].get('value', True)
                    conditions.append(flipped)
                else:   # several conditions, variables ...: the watcher checks the later page first
                    blockers.append(deepcopy(tests))
            if not shown:
                continue
            if p.get('class_id', g.get('class_id')) is None and not p.get('commands') and \
                    not any(h.get('commands') for h in p.get('trigger_actions') or []):
                continue   # an empty page with no character: nothing is there while it is in force (2026-10-18)
            sub = deepcopy(g)
            sub['id'] = f"{g['id']}#page{i + 1}"
            sub['pages'] = [dict(deepcopy(p), conditions=conditions)]
            sub['class_id'] = p.get('class_id', g.get('class_id'))
            sub['trigger'] = p.get('trigger', g.get('trigger'))
            sub['_act_as_npc'] = bool(p.get('act_as_npc'))
            if sub['_act_as_npc']:_npc_page(sub)
            sub['_page_of'] = g['id']
            if blockers:sub['_blockers'] = blockers
            out.append(sub)
    return out


import threading as _threading
COMPILE_LOCK = _threading.RLock()   # one compile at a time (module-level per-map settings)


def compile_new_events(session, graphs):
    """compile_events_on_data, with every game object read from the original
    game's maps, whatever the project did to them (stock_donors). One compile
    runs at a time: the editor's background warm-up and a build take turns
    map by map (COMPILE_LOCK)."""
    with COMPILE_LOCK:
        return _compile_new_events(session, _expand_text_questions(graphs))


def _expand_text_questions(graphs):
    """Ask A Question becomes Show Text followed by a Yes / No branch (the
    form tested in game on 2026-10-22)."""
    from copy import deepcopy
    def expand(rows):
        out = []
        for row in rows or []:
            if not isinstance(row, dict):out.append(row);continue
            row = dict(row)
            for key in ("then", "else", "commands"):
                if key in row:row[key] = expand(row[key])
            if row.get("type") == "ask_question":
                then, other = row.pop("then", []), row.pop("else", [])
                row.update(type="show_dialogue", speaker=row.get("speaker"))
                out += [row, {"type": "if", "condition": {"type": "yes_no", "value": True}, "then": then, "else": other}];continue
            out.append(row)
        return out
    graphs = deepcopy(graphs)
    for graph in graphs:
        for page in graph.get("pages", []):page["commands"] = expand(page.get("commands", []))
    return graphs


def _compile_new_events(session, graphs):
    import stock_donors
    from copy import copy as _copy
    definitions = {row["id"]: row for row in (getattr(session, "content_database", None) or {}).get("definitions", [])}
    from class_instance import resolve_graphs
    graphs = resolve_graphs(graphs, definitions)
    prepared = stock_donors.prepare(session, graphs, definitions)
    if prepared is None:
        return compile_events_on_data(session, graphs)
    data, graphs, plan = prepared
    view = _copy(session)
    view.data = data
    if plan.slots:
        db = dict(getattr(session, "content_database", None) or {})
        created = list(db.get("created_maps") or [])
        created += [slot for m, slot in plan.slots if m in created]
        db["created_maps"] = created
        view.content_database = db
    exported = compile_events_on_data(view, graphs)
    exported.data = stock_donors.finish(exported.data, plan, stock_donors.original_of(session))
    if plan.slots:
        exported.content_database = dict(exported.content_database or {})
        exported.content_database["created_maps"] = (getattr(session, "content_database", None) or {}).get("created_maps", [])
        back = {slot: m for m, slot in plan.slots}
        for row in getattr(exported, "native_event_export_report", None) or []:
            if isinstance(row, dict) and row.get("map_id") in back:row["map_id"] = back[row["map_id"]]
    return exported


from copy import deepcopy


def compile_events_on_data(session, graphs):
    """Return isolated session with added bytecode, native records and text.

    Current-map donors guarantee sprite records/assets already exist. Class
    records are authoring metadata: unknown class IDs or mismatched donor
    catalogue identities are never silently installed as another character.
    """
    graphs = _expand_text_questions(graphs)
    from class_instance import resolve_graphs   # events are class instances: unset values come from the class now
    graphs = resolve_graphs(graphs, (getattr(session, "content_database", None) or {}).get("definitions", []))
    import local_sprite_import as _lsi   # maps the project blanked over unused originals act as new maps
    _db = getattr(session, "content_database", None) or {}
    _lsi.PROJECT_BLANK_MAPS = {m for m in (_db.get("created_maps") or []) if type(m) is int} if isinstance(_db, dict) else set()

    exported = copy(session)
    from map_block_repack import owned as _owned, own_session_data, release_session_data
    exported.data = session.data
    own_session_data(exported)   # this compile's own copy: allocations edit it in place (fast)
    definitions = {row["id"]: row for row in getattr(session, "content_database", {}).get("definitions", [])}
    # New enemies of their own (enemy_clone): build them in their own class slot,
    # with the original's art copied into it on each map (clone_art_catalogue).
    for _id, _row in list(definitions.items()):
        _slot = _row.get("source", {}).get("own_slot")
        if type(_slot) is int:
            _row = dict(_row, source=dict(_row["source"], catalogue_index=_slot, clone_art_catalogue=_row["source"]["catalogue_index"]))
            definitions[_id] = _row
    from project_state_registry import ProjectStateRegistry
    from project_state_runtime import compile_project_command, compile_project_condition, layout as state_layout
    from event_edit_draft import event_copy   # definitions/instances are only read here
    state_registry = ProjectStateRegistry(event_copy(getattr(session, "content_database", {}) or {}))
    recovered_objects = {}
    recovered_deaths = {}
    recovered_default_routes = {}
    decorative_interactions = set()
    sign_interactions = set()   # Signboards (254) whose Interact actions the user wrote
    stool_activations = set()   # Stool (Pushable) with Activate actions (native_pushable_stool)
    stool_states = {}           # its on-target project switch
    route_resume_slots = 0
    graphs = [deepcopy(event_copy(g)) for g in graphs]   # destroy-after adds a build-only condition; the build changes only its own copies
    _self_switches(graphs, state_registry)   # Self Switches A-D -> each event's own project switches
    _visibility_and_graphics(graphs, state_registry)   # Show / Hide Event, Change Event Graphic -> switches + pages
    _is_item_page = lambda g, p: definitions.get(p.get('class_id', g.get('class_id')), {}).get('kind') in ('item', 'weapon', 'armor')
    graphs = _split_pages(graphs, lambda g: any(_is_item_page(g, p) or p.get('trigger', g.get('trigger')) == 'hit' for p in g.get('pages') or []))   # pages with different characters (Act As NPC): one actor per page
    graphs = _expand_item_pages(graphs, _is_item_page, state_registry)   # item pages: conditions, once-only pickup, actions after it
    graphs = _drop_unfired_pages(graphs)      # Death / Activate with no object: never fire
    from object_activation import HIT_SWITCHES as _HIT_SWITCHES
    def _is_hit_object(g, p):   # placed objects other than the switches the game itself hits (their Activate)
        d = definitions.get(p.get('class_id', g.get('class_id')), {})
        return d.get('kind') == 'object' and not (d.get('source', {}).get('catalogue_index') in _HIT_SWITCHES and not d.get('source', {}).get('variant'))
    def _hit_moves(g, p):   # lifted / thrown / pushed objects: the hit is taken on the object itself
        d = definitions.get(p.get('class_id', g.get('class_id')), {})
        s = d.get('source', {})
        return s.get('variant') == 'push_stool' or (s.get('catalogue_index') in HIT_ON_OBJECT_CLASSES and not s.get('variant'))
    graphs = _expand_hit_pages(graphs, state_registry, _is_hit_object, _hit_moves)   # Hit: native hit spots on its tiles (objects stay stock)
    graphs = _expand_item_drops(graphs)   # Give Item > Drop Item On Map
    graphs = _expand_spawn_templates(graphs, definitions)   # Edit AI > Spawned attack
    # Healing Tile (Life / Magic) objects: the save rooms' floor plates, built
    # on their own at the end (heal_tile.install_tiles), not as actors.
    import native_event_authoring as _nea
    from heal_tile import kind_of as _heal_kind, ensure_sparkles as _ensure_sparkles
    _nea.HEAL_EFFECTS = None
    _nea.SHOW_EFFECTS = None
    heal_graphs = [(g, _heal_kind(definitions.get((g.get('pages') or [{}])[0].get('class_id', g.get('class_id')))))
                   for g in graphs]
    heal_graphs = [(g, k) for g, k in heal_graphs if k]
    graphs = [g for g in graphs if not any(g is h for h, _ in heal_graphs)]
    # Block Switch Orb (Giles' nightmare): orb sprite + map-event program, built
    # at the end (block_switch.install_switches), not as an actor.
    from block_switch import kind_of as _orb_kind
    orb_graphs = [(g, _orb_kind(definitions.get((g.get('pages') or [{}])[0].get('class_id', g.get('class_id'))))) for g in graphs]
    orb_graphs = [(g, k) for g, k in orb_graphs if k]
    graphs = [g for g in graphs if not any(g is o for o, _ in orb_graphs)]
    # Sages (Lars...): their map's effect sprite, standing on the tile, built at the
    # end (sage_npc.install); walking up to them runs the event's actions (Player
    # touch on that tile; an event with no actions is only the picture).
    from sage_npc import sage_of as _sage_of, HELPER as _SAGE_HELPER
    sage_graphs = []
    _helper_id = next((d['id'] for d in definitions.values() if d.get('source', {}).get('catalogue_index') == _SAGE_HELPER
                       and not d.get('clone_of') and not d.get('source', {}).get('variant')), None)
    _kept = []
    for g in graphs:
        donor = _sage_of(definitions.get((g.get('pages') or [{}])[0].get('class_id', g.get('class_id'))))
        if donor is None:
            _kept.append(g);continue
        sage_graphs.append((g, donor))
        talks = any(p.get('commands') or any(h.get('commands') for h in p.get('trigger_actions') or []) for p in g.get('pages') or [])
        if talks:   # walking up to the sage (Player touch on its tile) runs the event, as in the game
            g = deepcopy(g);g['class_id'] = None;g['trigger'] = 'touch'
            for p in g.get('pages') or []:
                p['class_id'] = None;p['trigger'] = 'touch'
                for h in p.get('trigger_actions') or []:h['trigger'] = 'touch'
            _kept.append(g)
    graphs = _kept
    # Warp Panel objects: the save rooms' panel drawn over the floor (its event
    # tile is the panel's bottom-left corner) and a warp on its four tiles.
    from heal_tile import warp_panel_of as _warp_panel_of
    panel_graphs = [g for g in graphs if _warp_panel_of(definitions.get((g.get('pages') or [{}])[0].get('class_id', g.get('class_id'))))]
    graphs = [g for g in graphs if not any(g is p for p in panel_graphs)]
    # Save Room Portal objects: panel + swirl + warp back (tools/save_portal.py).
    from save_portal import portal_of as _portal_of
    portal_graphs = [g for g in graphs if _portal_of(definitions.get((g.get('pages') or [{}])[0].get('class_id', g.get('class_id'))))]
    graphs = [g for g in graphs if not any(g is p for p in portal_graphs)]
    for g in portal_graphs:
        for p in g.get('pages') or []:
            if p.get('commands') or any(h.get('commands') for h in p.get('trigger_actions') or []):
                raise ValueError(f"{g.get('name')}: a Save Room Portal only warps; it takes no actions")
    for g in panel_graphs:
        to = (g.get('native_placement') or {}).get('warp_to')
        if not isinstance(to, dict) or type(to.get('map')) is not int:
            raise ValueError(f"{g.get('name')}: choose where the Warp Panel leads (Warp Destination in the event editor)")
        for p in g.get('pages') or []:
            if p.get('commands') or any(h.get('commands') for h in p.get('trigger_actions') or []):
                raise ValueError(f"{g.get('name')}: a Warp Panel only warps; it takes no actions")
    # Step On Switch (Floor): the step-on switch's top drawn as a floor tile; it is
    # built as a Player Touch event on that tile (its Activate actions run each
    # time Alundra steps on it) and the picture is drawn at the end.
    from heal_tile import floor_switch_of as _floor_switch_of
    floor_switch_tiles = []
    floor_switch_lit = []
    floor_switch_unlit = []
    for g in graphs:
        if not _floor_switch_of(definitions.get((g.get('pages') or [{}])[0].get('class_id', g.get('class_id')))):
            continue
        x, y, rw, rh = g['region']
        if (rw, rh) != (1, 1):
            raise ValueError(f"{g.get('name')}: a Step On Switch (Floor) covers one tile")
        floor_switch_tiles.append((g['map_id'], x, y))
        # turns green when stepped on: a lit copy of its square waits on a spare
        # square and is copied over it (heal_tile.install_lit_copies)
        from heal_tile import spare_squares as _spare
        _taken = [s for (_m, _xy, s) in floor_switch_lit + floor_switch_unlit if _m == g['map_id']]
        _spot = _spare(bytes(session.data), g['map_id'], 2, _taken)
        lit_command = []; unlit_command = []
        if _spot:
            floor_switch_lit.append((g['map_id'], (x, y), _spot[0]))
            lit_command = [{'type': 'copy_map_tiles', 'from_x': _spot[0][0], 'from_y': _spot[0][1], 'width': 1, 'height': 1, 'to_x': x, 'to_y': y}]
        if len(_spot) > 1:   # an unlit copy, put back when it comes up again (Deactivate)
            floor_switch_unlit.append((g['map_id'], (x, y), _spot[1]))
            unlit_command = [{'type': 'copy_map_tiles', 'from_x': _spot[1][0], 'from_y': _spot[1][1], 'width': 1, 'height': 1, 'to_x': x, 'to_y': y}]
        # 2026-10-25: a whole-map controller (B) tests the tile itself, so nothing solid stands on
        # the floor (Alundra walks on from squares of the same height) and it is pressed by
        # Alundra (3B) or anything solid resting on the square (3C: blocks, statues, pots...),
        # with the step-on switch's options (While Pressed, Ignore Spring Bean, Active By Default,
        # Keep State Upon Leaving Room, Can Deactivate, Activate / Deactivate Switch commands).
        _pl = g.get('native_placement') or {}
        _pressed = bool(_pl.get('while_pressured'))
        _off = []
        g['class_id'] = None; g['trigger'] = 'parallel'
        for p in g.get('pages') or []:
            handlers = p.get('trigger_actions') or []
            # the step-on switch's press click (the game's BD3C; Play Sound's 75 3C is StopSound, 2026-10-23), then its Activate actions
            on = [h for h in handlers if h.get('trigger') != 'deactivate']
            if not on:on = [{'trigger': 'activate', 'commands': [], 'hit_sources': [], 'destroy_after': False}]
            on = [dict(h, trigger='parallel', commands=[{'type': 'native_play_sound', 'sound_id': 0x3C}] + lit_command + list(h.get('commands') or [])) for h in on[:1]]
            if not _off:_off = [h for h in handlers if h.get('trigger') == 'deactivate']
            p['trigger_actions'] = on
            p['commands'] = list(on[0].get('commands', []))
            p['class_id'] = None; p['trigger'] = 'parallel'
        if any(h.get('commands') for h in _off) and not _pressed:
            _pl = g.setdefault('native_placement', {}); _pl['can_deactivate'] = True
        g['_floor_switch'] = {
            'tile': (x, y), 'lit': lit_command, 'unlit': unlit_command,
            'release': unlit_command + list((_off[0].get('commands') if _off else None) or []),
            'while_pressed': _pressed, 'ignore_spring_bean': bool(_pl.get('ignore_spring_bean')),
            'can_deactivate': bool(_pl.get('can_deactivate')), 'keep_state': bool(_pl.get('keep_state')),
            'active_by_default': bool(_pl.get('active_by_default')) and not _pressed,
            'state_id': state_registry.create('switches', (g.get('name') or 'Step On Switch (Floor)') + ' object state',
                initial_value=bool(_pl.get('active_by_default')) and not _pressed)['id']}
    # Switches you hit start their actions on Hit in the event editor (user 2026-10-14);
    # their rebuilt controllers run them where the game's switch reacts (Activate).
    from object_activation import HIT_SWITCHES as _HIT
    graphs = graphs + _lever_other_weapons(graphs, definitions, state_registry)
    for g in graphs:
        for p in g.get('pages') or []:
            d = definitions.get(p.get('class_id', g.get('class_id')), {})
            if d.get('kind') != 'object' or d.get('source', {}).get('catalogue_index') not in _HIT or d.get('source', {}).get('variant'):
                continue
            for h in p.get('trigger_actions') or []:
                if h.get('trigger') == 'hit':h['trigger'] = 'activate'
            if p.get('trigger') == 'hit':p['trigger'] = 'activate'
        if g.get('trigger') == 'hit' and all(p.get('trigger') == 'activate' for p in g.get('pages') or []):g['trigger'] = 'activate'
    graphs = graphs + _hit_switch_requests(graphs, definitions, _HIT, state_registry)
    face_states = {}   # Nirude Face Statue: its object state (Activate / Deactivate Switch reaches it)
    graphs = graphs + _nirude_faces(graphs, definitions, state_registry, face_states)
    graphs = graphs + _nirude_statue_variants(graphs, definitions, state_registry, face_states)   # shooting statues: the same activation
    # Recover All Life And Magic shows the game's healing sparkles: their map
    # effect entries are added before anything else of the map is built.
    heal_sparkles = {}
    show_effects = {}      # map: {(global effect, animation): effect index} for Show Effect
    plate_rotations = {}   # map: directions whose pattern plate cycle starts on another symbol
    plate_pictures = {}   # map: [(plate top-left square, {spare block: plate frame}, frame shown first)] (Flush With Floor)
    # Entries tied to one game copy (Red / Blue Block: a box of that colour on
    # map 41) run that copy's scripts unless the event picked another behaviour.
    for g in graphs:
        fixed = definitions.get((g.get('pages') or [{}])[0].get('class_id', g.get('class_id')), {}).get('source', {}).get('fixed_donor')
        placement = g.setdefault('native_placement', {})
        if isinstance(fixed, list) and len(fixed) == 2 and type(placement.get('donor_entity_index')) is not int:
            placement.update(donor_map_id=fixed[0], donor_entity_index=fixed[1], behaviour_variant=True)
    for g in graphs:
        lists = [g.get('_release_commands') or []]
        for p in g.get('pages') or []:
            lists.append(p.get('commands') or [])
            lists.extend(h.get('commands') or [] for h in p.get('trigger_actions') or [])
        wanted = [(int(r.get('effect', 0)), int(r.get('animation', 0))) for rows in lists for r in _walk(rows) if r.get('type') == 'show_effect']
        if wanted:
            from heal_tile import ensure_effects as _ensure_effects
            exported.data, found = _ensure_effects(exported.data, g['map_id'], wanted)
            exported.data = _owned(exported.data)
            show_effects.setdefault(g['map_id'], {}).update(found)
        if g['map_id'] not in heal_sparkles and any(r.get('type') == 'restore_life' for rows in lists for r in _walk(rows)):
            exported.data, heal_sparkles[g['map_id']] = _ensure_sparkles(exported.data, g['map_id'])
            exported.data = bytearray(exported.data)
    # Spring Bean pots (user 2026-10-11): both are the game's magic pot (409).
    #  Spring Bean Pot (No Event) [340]: left like the game's own pots, so it waits for the Spring Bean.
    #  Spring Bean Pot (Boing)    [409]: starts already bouncing (the earlier behaviour).
    _by_index = {}
    for _d in definitions.values():
        _i = _d.get('source', {}).get('catalogue_index')
        if _i in (340, 409) and not _d.get('clone_of'):_by_index.setdefault(_i, _d['id'])
    for _g in graphs:   # While Pressured step-on switch: Deactivate tab = actions when stepped off
        for _p in _g.get('pages', []):
            _handlers = _p.get('trigger_actions') or []
            _off = [h for h in _handlers if h.get('trigger') == 'deactivate']
            if not _off:continue
            _d = definitions.get(_p.get('class_id', _g.get('class_id')), {})
            if not _off[0].get('commands'):   # empty Deactivate tab (every switch has one): nothing to build
                _p['trigger_actions'] = [h for h in _handlers if h.get('trigger') != 'deactivate'] or [{'trigger':'activate','commands':[],'hit_sources':[],'destroy_after':False}]
                _p['trigger'] = _p['trigger_actions'][0].get('trigger', 'activate');_p['commands'] = list(_p['trigger_actions'][0].get('commands', []))
                continue
            _ci = _d.get('source', {}).get('catalogue_index')
            _pl = _g.get('native_placement') or {}
            if _d.get('source', {}).get('variant') == 'push_stool':   # Stool (Pushable): off its target tile
                _pl = dict(_pl, can_deactivate=True)
            elif _ci not in (301, 305, 306, 307, 398) or _d.get('source', {}).get('variant'):
                raise ValueError(f"{_g.get('name')}: Deactivate actions build only for switches")
            if not (_pl.get('can_deactivate') or (_ci == 301 and (_pl.get('while_pressured') or _d.get('data', {}).get('while_pressured')))):
                # Deactivate actions written: the switch can deactivate (user 2026-10-25: never refuse)
                _g.setdefault('native_placement', {})['can_deactivate'] = True
            _g['_release_commands'] = list(_off[0].get('commands', []))
            _on = [h for h in _handlers if h.get('trigger') != 'deactivate']
            _p['trigger_actions'] = _on
            if _on:_p['trigger'] = _on[0].get('trigger', 'activate');_p['commands'] = list(_on[0].get('commands', []))
            else:_p['trigger'] = 'activate';_p['commands'] = []
    for _g in graphs:
        for _p in _g.get('pages', []):
            _cid = _p.get('class_id', _g.get('class_id'))
            _i = definitions.get(_cid, {}).get('source', {}).get('catalogue_index')
            if _i == 340 and 409 in _by_index:
                _p['class_id'] = _by_index[409];_g.setdefault('native_placement', {})['magicpot_sprouted'] = False
            elif _i == 409:
                _g.setdefault('native_placement', {})['magicpot_sprouted'] = True
    for graph in graphs:
        _take_erase(graph)
    # Erase Event on one page erases the whole event: every page's actor of a split event
    # shares one latch (2026-10-22 QA: page 2's character still appeared after page 1 erased).
    erased_families = {g.get('_page_of', g['id']) for g in graphs if _destroys(g)}
    family_latch = {}
    def _latch_for(g):
        key = g.get('_page_of', g['id'])
        if key not in family_latch:
            family_latch[key] = state_registry.create('switches', (g['name'] if key == g['id'] else g['name'].split('#')[0]) + ' destroyed')['id']
        return family_latch[key]
    for graph in graphs:
        page_class = (graph.get('pages') or [{}])[0].get('class_id',graph.get('class_id'))
        definition = definitions.get(page_class, {})
        if definition.get('kind')=='object' and any(definition.get('data',{}).get(field,False)
                for field in ('active_by_default','activation_one_way','remember_state_until_area_exit')):
            # the class's Database options apply to each placed copy that does not set its own
            # (user 2026-10-25: the same options on every switch, never a refusal)
            _cd = definition.get('data', {}); _np = graph.setdefault('native_placement', {})
            if _cd.get('active_by_default'):_np.setdefault('active_by_default', True)
            if _cd.get('remember_state_until_area_exit'):_np.setdefault('keep_state', True)
            if _cd.get('activation_one_way'):_np['can_deactivate'] = False
        catalogue = definition.get('source', {}).get('catalogue_index')
        if any(page.get('default_move_route') for page in graph.get('pages', [])):
            from native_default_route_profile import require_proven_default_route
            command=require_proven_default_route(graph, definition,allow_interaction=True)
            entry={'command':command}
            if graph['pages'][0].get('commands') and command.get('_native_animation_route'):
                if route_resume_slots>=16:raise ValueError('Default movement route interaction supports at most16 independent snapshot instances per game')
                entry.update(slot=route_resume_slots,busy_id=state_registry.create('switches',graph['name']+' route interaction active')['id'])
                route_resume_slots+=1
            recovered_default_routes[graph['id']]=entry
        if (graph.get('pages') or [{}])[0].get('trigger')=='death' and (any(p.get('commands') for p in graph.get('pages',[])) or _destroys(graph)):   # conditions alone only decide when it appears
            from native_enemy_death import DEATH_ACTIONS
            if definition.get('kind') not in ('enemy','boss'):
                raise ValueError('Death actions need an enemy or boss')
            if len(graph['pages'])!=1:
                raise ValueError('Death actions use one event page (its conditions decide when the enemy appears)')
            unsupported=sorted({c.get('type') for c in _walk(graph['pages'][0].get('commands',[]))}-DEATH_ACTIONS)
            if unsupported:
                raise ValueError('Death actions cannot include '+', '.join(unsupported)+' yet (money, items, dialogue, switches, variables, waits, branches, sound and music work)')
            recovered_deaths[graph['id']]=state_registry.create('switches',graph['name']+' death completed')['id']
            if _destroys(graph):
                # Destroy after action: once killed it stays gone (the latch
                # the death script sets keeps it out on every later visit).
                killed=state_registry.create('switches',graph['name']+' killed')['id']
                spawned=state_registry.create('switches',graph['name']+' spawned this visit')['id']
                graph['_once']={'killed':killed,'spawned':spawned}
                graph['pages'][0].setdefault('conditions',[]).append({'type':'switch','switch_scope':'project','switch_id':killed,'value':False})
        if _destroys(graph) and graph['id'] not in recovered_deaths and not (
                definition.get('kind') in ('item','weapon','armor') or catalogue == 30):   # pickups and chests remove themselves
            latch=_latch_for(graph)
            for current in graph['pages']:
                done={'type':'set_switch','switch_scope':'project','switch_id':latch,'value':True}
                current['commands']=list(current.get('commands',[]))+[done]
                for handler in current.get('trigger_actions',[]):
                    handler['commands']=list(handler.get('commands',[]))+[dict(done)]
            for current in graph['pages']:
                current['conditions']=list(current.get('conditions',[]))+[{'type':'switch','switch_scope':'project','switch_id':latch,'value':False}]
        elif graph.get('_page_of') in erased_families and not _destroys(graph):
            latch=_latch_for(graph)
            for current in graph['pages']:
                current['conditions']=list(current.get('conditions',[]))+[{'type':'switch','switch_scope':'project','switch_id':latch,'value':False}]
        explicit_rolling_target = catalogue == 314 and 'finish_tile' in graph.get('native_placement',{})
        if explicit_rolling_target:
            from native_small_rolling_rock_profile import compile_controller
            compile_controller(state_registry,graph['native_placement']['finish_tile'],facing=graph['native_placement'].get('facing','down'))
        bound_gate = catalogue in (325,326) and 'open_switch_id' in graph.get('native_placement', {})
        rotation = graph.get('native_placement', {}).get('rotation_controller',False)
        if type(rotation) is not bool:raise ValueError('Rotation controller must be explicitly checked or unchecked')
        explicit_rotation = catalogue == 308 and rotation
        carryable_continuation = catalogue == 291 and any(page.get('commands') for page in graph.get('pages',[]))
        book_interaction = definition.get('kind')=='object' and catalogue==303 and any(page.get('commands') for page in graph.get('pages',[]))
        sign_interaction = definition.get('kind')=='object' and catalogue==254 and any(page.get('commands') for page in graph.get('pages',[]))
        if sign_interaction:
            # A signboard does what the game's own signs that do more than show a text do
            # (map 27 entity 49, map 62 entity 0): reading it (F) sets a room flag, and its C
            # program waits for that flag, clears it, then runs the actions (text, warp ...).
            if any(page.get('trigger','interact')!='interact' for page in graph.get('pages',[])):
                raise ValueError(f"{graph.get('name')}: a signboard's actions run when it is read (Interact)")
            sign_interactions.add(graph['id'])
        if book_interaction:
            from native_book_interaction import require_graph
            require_graph(graph,session.data)
            decorative_interactions.add(graph['id'])
        if carryable_continuation:
            placement=graph.get('native_placement',{})
            if any(key in placement for key in ('donor_map_id','donor_entity_index')) and (placement.get('donor_map_id'),placement.get('donor_entity_index'))!=(21,1):
                raise ValueError('Recovered jar291 custom donor selection supports the verified source21/1 only')
        if explicit_rotation and not graph['pages'][0].get('commands'):
            raise ValueError('Rotation controller needs authored Activate contents to replace its original map target')
        if bound_gate:
            state_registry.get('switches', graph['native_placement']['open_switch_id'])
        from native_pushable_stool import is_stool as _is_stool_def
        if _is_stool_def(definition) and (any(page.get('commands') for page in graph.get('pages',[])) or graph.get('_release_commands')):
            # Stool (Pushable): Activate / Deactivate actions run in its own C program when it
            # ends a move on / off its target tile (native_pushable_stool)
            from native_pushable_stool import target_of as _stool_target
            if len(graph.get('pages',[])) != 1 or graph['pages'][0].get('trigger','activate') != 'activate':
                raise ValueError(f"{graph.get('name')}: a pushable stool's actions run on Activate / Deactivate (one page)")
            if _stool_target(graph.get('native_placement')) is None:
                raise ValueError(f"{graph.get('name')}: choose the stool's Target tile for its Activate / Deactivate actions")
            stool_activations.add(graph['id'])
            stool_states[graph['id']] = state_registry.create('switches', graph['name'] + ' target state')['id']
        if definition.get('kind') == 'object' and catalogue not in (298,301,305,306,307,312,313,315,316,321,322,323,324,364,398) and not bound_gate and not explicit_rotation and not explicit_rolling_target and not carryable_continuation and not book_interaction and not sign_interaction and graph['id'] not in stool_activations:
            if any(page.get('commands') or (page.get('conditions') and _presence_condition(graph) is None) for page in graph.get('pages', [])):
                raise ValueError('Assigned object events need a verified retained native controller; replacing the interaction hook can stop pickup, throwing or activation. Passive object placement remains available; authored object actions currently support recovered floor, lever and hit switches on Activate')
        if definition.get('kind') == 'object' and (catalogue in (298,301,305,306,307,312,313,315,316,321,322,323,324,364,398) or bound_gate or explicit_rotation or explicit_rolling_target or carryable_continuation):
            if catalogue == 291:
                from native_carryable_continuation import verify_jar_source as verify_source
            elif catalogue == 308:
                from native_rotation_switch_profile import verify_source
            elif catalogue == 326:
                from native_large_gate_profile import verify_source
            elif catalogue == 324:
                from native_key_door_profile import verify_source, require_synchronous_continuation
                for door_page in graph.get('pages', []):
                    require_synchronous_continuation(door_page.get('commands', []))
            elif catalogue == 323:
                from native_small_key_door_profile import verify_source
                door_placement=graph.get('native_placement',{})
                if any(key in door_placement for key in ('donor_map_id','donor_entity_index')) and (door_placement.get('donor_map_id'),door_placement.get('donor_entity_index'))!=(41,24):
                    raise ValueError('Small key door323 supports the verified source41/24 only')
            elif catalogue == 316:
                from native_flame_pillar_profile import verify_source
                if any(page.get('commands') for page in graph.get('pages',[])):
                    raise ValueError('Flame pillar316 currently supports its native passive cycle only; authored Contents need retained cycle-completion testing')
                hazard_placement=graph.get('native_placement',{})
                if any(key in hazard_placement for key in ('donor_map_id','donor_entity_index')) and (hazard_placement.get('donor_map_id'),hazard_placement.get('donor_entity_index'))!=(52,28):
                    raise ValueError('Flame pillar316 supports the verified source52/28 only')
            elif catalogue == 325:
                from native_gate_profile import verify_source
            elif catalogue == 298:
                from native_statue_profile import verify_source
            elif catalogue == 305:
                from native_lever_profile import verify_source
            elif catalogue == 306:
                from native_wall_switch_profile import verify_source
            elif catalogue == 314:
                from native_small_rolling_rock_profile import verify_source
            elif catalogue == 315:
                from native_rolling_rock_profile import verify_source
            elif catalogue == 322:
                from native_large_breakable_platform_profile import verify_source
            elif catalogue == 321:
                from native_breakable_platform_profile import verify_source
            elif catalogue == 313:
                from native_platform_shuttle_profile import verify_source
            elif catalogue == 312:
                from native_platform_lift_profile import verify_source
            elif catalogue == 307:
                from native_ignition_switch_profile import verify_source
            elif catalogue == 398:
                from native_lamp_switch_profile import verify_source
            elif catalogue == 364:
                from native_pattern_plate_profile import verify_source
            else:
                from native_floor_switch_profile import verify_source
            verify_source(session.data)
            if len(graph.get('pages', [])) != 1 or graph['pages'][0].get('conditions'):
                raise ValueError('Recovered object currently supports one unconditional activation page')
            if graph['pages'][0].get('commands') and graph['pages'][0].get('trigger') != 'activate':
                raise ValueError('Recovered object actions run on Activate, after the native activation animation')
            recovered_objects[graph['id']] = {
                'catalogue':catalogue,
                'state_id':None if catalogue in (291,308,312,313,314,315,316,321,322,325,326) else state_registry.create('switches', graph['name']+' object state',
                    # Active By Default (switches): the switch starts already on
                    initial_value=bool(catalogue in (301,305,306,307,398) and (graph.get('native_placement') or {}).get('active_by_default')
                                       and not (graph.get('native_placement') or {}).get('while_pressured')))['id']}
            if catalogue in (325,326):
                recovered_objects[graph['id']]['open_switch_id'] = graph['native_placement']['open_switch_id']
            if catalogue in (298,305,306,307,308,398):
                recovered_objects[graph['id']]['request_id'] = state_registry.create('switches', graph['name']+' activation request')['id']
            if catalogue == 307 and (graph.get('native_placement') or {}).get('can_deactivate'):   # Can Deactivate: the ice wand puts it out again
                recovered_objects[graph['id']]['off_request_id'] = state_registry.create('switches', graph['name']+' put-out request')['id']
    exported.content_database = state_registry.document
    exported.actor_route_resume_slots = route_resume_slots
    def validate(graph):
        return validate_new_event(graph, recovered_activation=graph['id'] in recovered_objects or graph['id'] in stool_activations,recovered_death=graph['id'] in recovered_deaths, recovered_default_route=graph['id'] in recovered_default_routes)
    # Block Switch with Keep State Upon Leaving Room: its own private switch
    orb_states = {g['id']: state_registry.create('switches', g['name'] + ' object state',
                      initial_value=bool((g.get('native_placement') or {}).get('active_by_default')))['id']
                  for g, _ in orb_graphs if (g.get('native_placement') or {}).get('keep_state')}
    # Conditional enemies/bosses: their once-per-visit latch needs its switch before the
    # slots are laid out (made later, it had no slot: KeyError on export, 2026-10-21)
    for g in graphs:
        page_class = (g.get('pages') or [{}])[0].get('class_id', g.get('class_id'))
        if g.get('_once') is None and definitions.get(page_class, {}).get('kind') in ('enemy', 'boss') \
                and not (g.get('native_placement') or {}).get('instant_respawn') and _presence_condition(g) is not None:
            g['_once_visit'] = g.get('_once_visit') or {
                'killed': None, 'spawned': state_registry.create('switches', g['name'] + ' spawned this visit')['id']}
    state_slots = state_layout(state_registry)
    project_condition = lambda row: compile_project_condition(row, state_registry, state_slots)
    def switch_state_command(command, _graph_box=[None]):
        graph = _graph_box[0]
        target = graph["id"] if command.get("event_id") in (None, "this_event") else command.get("event_id")
        entry = recovered_objects.get(target)
        other = next((g for g in graphs if g["id"] == target), None)
        if other is not None and other.get("_floor_switch"):   # Step On Switch (Floor): its own latch
            if other.get("map_id") != graph.get("map_id"):
                raise ValueError(f"{graph['name']}: Activate / Deactivate Switch can only reach a switch on the same map")
            return compile_project_command({"type": "set_switch", "switch_scope": "project",
                "switch_id": other["_floor_switch"]["state_id"], "value": bool(command.get("active", False))}, state_registry, state_slots)
        if target in face_states and other is not None:   # Nirude Face Statue: activated -> destructible
            if other.get("map_id") != graph.get("map_id"):
                raise ValueError(f"{graph['name']}: Activate / Deactivate Switch can only reach a statue on the same map")
            return compile_project_command({"type": "set_switch", "switch_scope": "project",
                "switch_id": face_states[target], "value": bool(command.get("active", False))}, state_registry, state_slots)
        if entry is None or entry.get("state_id") is None or other is None or \
                definitions.get((other.get("pages") or [{}])[0].get("class_id", other.get("class_id")), {}).get("source", {}).get("catalogue_index") != 301:
            raise ValueError(f"{graph['name']}: Activate / Deactivate Switch needs a Switch (Step On) event on this map")
        if other.get("map_id") != graph.get("map_id"):
            raise ValueError(f"{graph['name']}: Activate / Deactivate Switch can only reach a switch on the same map")
        return compile_project_command({"type": "set_switch", "switch_scope": "project",
            "switch_id": entry["state_id"], "value": bool(command.get("active", False))}, state_registry, state_slots)
    _switch_graph = switch_state_command.__defaults__[0]
    reports = []
    grouped = {}
    for graph in graphs:
        grouped.setdefault(graph["map_id"], []).append(graph)
    behaviour_cache = {}
    for map_id, group in grouped.items():
        _nea.HEAL_EFFECTS = heal_sparkles.get(map_id)
        _nea.SHOW_EFFECTS = show_effects.get(map_id)
        pending = []
        room_guards = []   # switches whose private state resets on entering this room
        victory_bosses = []   # bosses with Play Victory: (template index, home map, name)
        victory_after = []   # their death actions: run by the victory watcher once the text is closed
        victory_text_slots = []   # their texts' slots (the watcher is added last, so nothing in the map shows them yet)
        victory_hook = None
        victory_homes = {}
        tracking_hooks = []   # Track Player watchers (B, whole map)
        sign_guards = []   # signboards with actions: the room flag reading one sets
        imported_placements = {}
        imported_assets = {}
        # Map-local sprite slots every event of this map places: an import must
        # not reuse their texture pages, even before their records are written.
        local_slots = set()
        portrait_cells = set()   # texture cells of portraits F2 placed on this map
        for graph in group:
            for page in graph.get('pages') or [{}]:
                cat = definitions.get(page.get('class_id') or graph.get('class_id'), {}).get('source', {}).get('catalogue_index')
                if type(cat) is int and 256 <= cat < 512:
                    local_slots.add(cat - 256)
        # Sprite assets must be installed before capturing/repacking bytecode.
        # Find real donor records, never infer native identity from a name.
        for graph in group:
            _, _, class_id, placement = validate(graph)
            definition = definitions.get(class_id, {})
            catalogue = definition.get("source", {}).get("catalogue_index")
            if type(catalogue) is not int or catalogue < 256:
                continue
            art = definition.get("source", {}).get("clone_art_catalogue")
            if type(art) is int:
                # copy the original's sprite into this enemy's own slot on this map
                from native_class_placement import class_donors
                from local_sprite_import import import_local_sprite
                donor_map = donor_index = None
                for candidate in [map_id] + [m for m in range(483) if m != map_id]:
                    donors = class_donors(exported.data, candidate, art)
                    if donors:
                        donor_map, donor_index = candidate, donors[0]["entity_index"]; break
                if donor_map is None:
                    raise ValueError(f"{definition.get('name')}: its original has no placed copy to take art from")
                key = ("own", catalogue)
                if key not in imported_assets:
                    exported.data, imported_assets[key] = import_local_sprite(exported.data, map_id, donor_map, art - 256,
                                                                              keep=local_slots, target_slot=catalogue - 256)
                imported_placements[graph["id"]] = (imported_assets[key], donor_index)
                continue
            if definition.get('kind')=='enemy' and catalogue==347 and map_id==153:
                raise ValueError('Murgg claws in map153 needs its native parent/controller contract')
            resolved = resolve_class_donor(exported.data, map_id, catalogue)
            if resolved is not None:
                continue
            from native_class_placement import class_donors
            donor_map = placement.get("donor_map_id")
            donor_index = placement.get("donor_entity_index")
            if type(donor_map) is not int or type(donor_index) is not int:
                donor_map = donor_index = None
                if graph['id'] in recovered_objects and catalogue == 291:
                    donor_map,donor_index=21,1
                elif graph['id'] in recovered_objects and catalogue == 308:
                    donor_map, donor_index = 126, 0
                elif graph['id'] in recovered_objects and catalogue == 326:
                    donor_map, donor_index = 55, 11
                elif graph['id'] in recovered_objects and catalogue == 324:
                    donor_map, donor_index = 42, 16
                elif graph['id'] in recovered_objects and catalogue == 323:
                    donor_map, donor_index = 41, 24
                elif graph['id'] in recovered_objects and catalogue == 316:
                    donor_map, donor_index = 52, 28
                elif graph['id'] in recovered_objects and catalogue == 325:
                    donor_map, donor_index = 39, 2
                elif graph['id'] in recovered_objects and catalogue == 298:
                    donor_map, donor_index = 37, 0
                elif graph['id'] in recovered_objects and catalogue == 306:
                    donor_map, donor_index = 40, 9
                elif graph['id'] in recovered_objects and catalogue == 314:
                    donor_map, donor_index = 126, 3
                elif graph['id'] in recovered_objects and catalogue == 315:
                    donor_map, donor_index = 67, 29
                elif graph['id'] in recovered_objects and catalogue == 322:
                    donor_map, donor_index = 69, 28
                elif graph['id'] in recovered_objects and catalogue == 321:
                    donor_map, donor_index = 306, 15
                elif graph['id'] in recovered_objects and catalogue == 313:
                    donor_map, donor_index = 52, 7
                elif graph['id'] in recovered_objects and catalogue == 312:
                    donor_map, donor_index = 29, 28
                elif graph['id'] in recovered_objects and catalogue == 307:
                    donor_map, donor_index = 58, 1
                elif graph['id'] in recovered_objects and catalogue == 398:
                    donor_map, donor_index = 24, 0
                elif graph['id'] in recovered_objects and catalogue == 364:
                    from native_pattern_plate_profile import STATIC_SOURCE, CHANGING_SOURCE
                    donor_map, donor_index = CHANGING_SOURCE if definition.get('source', {}).get('variant') == 'pattern_cycle' else STATIC_SOURCE
                elif definition.get('kind') == 'object' and catalogue == 409:
                    from native_magicpot_donor import donor
                    preferred = donor(exported.data)
                    donor_map, donor_index = preferred['map_id'], preferred['entity_index']
                elif definition.get('kind') == 'object' and graph['id'] not in recovered_objects:
                    from object_donor_selection import preferred_hook_free_donor
                    try:
                        preferred = preferred_hook_free_donor(exported.data,catalogue)
                        donor_map, donor_index = preferred['map_id'], preferred['entity_index']
                    except ValueError:
                        donor_map = donor_index = None   # no map places it; synthesized below
                elif definition.get('kind') == 'enemy' and catalogue in (347,350,356):
                    from native_murgg_bundle import verified_donor
                    preferred = verified_donor(exported.data,catalogue)
                    donor_map, donor_index = preferred['map_id'], preferred['entity_index']
                elif definition.get('kind') == 'boss' and catalogue == 452:
                    from native_sara1_donor import donor
                    preferred = donor(exported.data)
                    donor_map, donor_index = preferred['map_id'], preferred['entity_index']
                elif definition.get('kind') == 'boss' and catalogue == 482:
                    from native_werewolf_donor import donor
                    preferred = donor(exported.data)
                    donor_map, donor_index = preferred['map_id'], preferred['entity_index']
                else:
                    first = None
                    for candidate in range(483):
                        donors = class_donors(exported.data, candidate, catalogue)
                        if donors and first is None:
                            first = (candidate, donors[0]["entity_index"])
                            if definition.get('kind') != 'enemy':
                                break
                        # An enemy prefers an instance the room's own scripts do not drive: the
                        # first Shrine Mummy (map 340) is a statue its room's C program wakes,
                        # placed elsewhere it never moved (2026-10-21)
                        free = [d for d in donors if not any(d['programs'].values())]
                        if definition.get('kind') == 'enemy' and free:
                            first = (candidate, free[0]["entity_index"])
                            break
                    if first is not None:
                        donor_map, donor_index = first
            if donor_map is None:
                # No map places this class: import its art from the map that
                # holds it and build a fresh record (behaviour_transplant).
                from behavior_transplant import local_sprite_home
                from local_sprite_import import import_local_sprite
                home = local_sprite_home(exported.data, catalogue - 256)
                if home is None:
                    raise ValueError("This class has no graphics anywhere in the game data")
                key = (home, catalogue)
                if key not in imported_assets:
                    exported.data, imported_assets[key] = import_local_sprite(exported.data, map_id, home, catalogue - 256, keep=local_slots)
                imported_placements[graph["id"]] = (imported_assets[key], None)
                continue
            if graph['id'] in recovered_objects and catalogue==291 and (donor_map,donor_index)!=(21,1):
                raise ValueError('Recovered jar291 needs the exact hook-free native donor21/1')
            if definition.get('kind') == 'boss' and catalogue == 482:
                from native_werewolf_donor import donor
                preferred = donor(exported.data)
                if (donor_map,donor_index)!=(preferred['map_id'],preferred['entity_index']):
                    raise ValueError('Standalone Werewolf placement requires its exact recovered donor')
            if definition.get('kind') == 'object' and catalogue == 409:
                from native_magicpot_donor import donor
                preferred = donor(exported.data)
                if (donor_map,donor_index)!=(preferred['map_id'],preferred['entity_index']):
                    raise ValueError('Magicpot placement requires its exact recovered donor')
            from local_sprite_import import import_local_sprite
            key = (donor_map, catalogue)
            if key not in imported_assets:
                if definition.get('kind') == 'enemy' and catalogue in (347,350,356):
                    from native_murgg_bundle import verified_donor,import_bundle
                    preferred = verified_donor(exported.data,catalogue)
                    if (donor_map,donor_index)!=(preferred['map_id'],preferred['entity_index']):
                        raise ValueError('Foreign Murgg placement requires its recovered donor and projectile bundle')
                    exported.data, bundle_report = import_bundle(exported.data,map_id,catalogue)
                    art_report = dict(bundle_report['asset_imports'][0],native_dependency_bundle=bundle_report)
                else:
                    exported.data, art_report = import_local_sprite(exported.data, map_id, donor_map, catalogue - 256, keep=local_slots)
                if definition.get('kind') == 'enemy' and donor_map != map_id:
                    # an enemy brings the sprites its own code creates (projectiles...)
                    from local_sprite_import import layout as _lay
                    import struct as _st2
                    _b, _h, _s, _e, _sh = _lay(exported.data, donor_map)
                    _spawned = [i for i in ai_spawned_slots(exported.data, donor_map, catalogue)
                                if _st2.unpack_from('<i', exported.data, _s + _sh[3] + 4 * i)[0] not in (0, -1)
                                and i not in local_slots]
                    if _spawned:
                        exported.data, companions = _import_boss_companions(exported.data, map_id, donor_map, catalogue, local_slots, definition.get('name'), _spawned)
                        art_report = dict(art_report, ai_companions=companions)
                if definition.get('kind') == 'boss' and donor_map != map_id:
                    # A boss carries what its fight needs: every sprite of its home map that no
                    # placed character there uses (its other parts, projectiles, effects), in the
                    # same slots, since the boss's own code creates them by slot number.
                    exported.data, companions = _import_boss_companions(exported.data, map_id, donor_map, catalogue, local_slots, definition.get('name'))
                    # ... and the home map's effect sprites its code shows by number (Melzas: effect 0)
                    exported.data, effects = _import_boss_effects(exported.data, map_id, donor_map, catalogue,
                                                                  definition.get('name'), behaviour_cache.setdefault('_boss_effects', {}))
                    art_report = dict(art_report, boss_companions=companions, boss_effects=effects)
                imported_assets[key] = art_report
            imported_placements[graph["id"]] = (imported_assets[key], donor_index)
        palette_requests = {}
        palette_forks = {}
        for graph in group:
            _, _, class_id, _ = validate(graph)
            definition = definitions.get(class_id, {})
            catalogue = definition.get("source", {}).get("catalogue_index")
            palette = definition.get("data", {}).get("palette_shift", {})
            if not isinstance(palette, dict):
                raise ValueError("Class palette settings must be an object")
            hue = (palette.get("hue_degrees", 0), palette.get("saturation_percent", 100))
            if type(catalogue) is not int:
                continue
            if catalogue in palette_requests and palette_requests[catalogue] != hue:
                raise ValueError("Two classes request different hues for one native sprite ID on this map; independent palette clones are not installed")
            palette_requests[catalogue] = hue
        # A recoloured boss/enemy recolours the look-alike sprites of its fight too (its parts,
        # the sprites its code spawns) unless they ask for their own colours (2026-10-21)
        from local_sprite_import import sprite_assets as _assets
        part_requests = {}
        for graph in group:
            _, _, class_id, _ = validate(graph)
            definition = definitions.get(class_id, {})
            hue = palette_requests.get(definition.get("source", {}).get("catalogue_index"))
            if hue in (None, (0, 100)):
                continue
            art = (imported_placements.get(graph["id"]) or ({},))[0] or {}
            parts = list(definition.get("source", {}).get("boss_parts") or [])
            parts += [row.get("catalogue_index") for key in ("boss_companions", "ai_companions") for row in art.get(key) or []]
            for part in parts:
                if type(part) is int and 256 <= part < 512 and part not in palette_requests:
                    try:_assets(exported.data, map_id, part - 256)
                    except Exception:continue   # not on this map
                    part_requests.setdefault(part, hue)
        palette_requests.update(part_requests)
        by_hue = {}
        for catalogue, hue in palette_requests.items():
            if hue != (0, 100):
                if catalogue < 256:
                    raise ValueError("Hue forks currently support map-local classes; global class recolors are not compiled")
                by_hue.setdefault(hue, []).append(catalogue)
        for hue, catalogues in by_hue.items():
            from local_sprite_recolor import recolor_local_classes
            exported.data, fork = recolor_local_classes(exported.data, map_id, catalogues, *hue)
            for catalogue in catalogues:palette_forks[catalogue] = fork
        initial_entities = len(record_cluster(exported.data, map_id)["entities"])
        total_gifts = sum(command.get("type") == "give_item" for graph in group
            for current in graph["pages"] for command in _walk(current.get("commands", [])))
        # Direct82 grant creates no InitData rows; old8B pickup is not a grant.
        total_gifts = 0
        actor_indices = {}
        for graph in group:
            if validate(graph)[2] is not None:
                actor_indices[graph["id"]] = initial_entities + total_gifts + len(actor_indices)
        # Spawn templates a placed boss brings (behavior_transplant.copy_template) go after
        # these actors, so the actors keep the indices their watchers name.
        behaviour_cache[("template_base", map_id)] = initial_entities + total_gifts + len(actor_indices)
        behaviour_cache[("templates", map_id)] = []
        def speaker_selector(command):
            speaker = command.get("speaker")
            explicit = command.get("native_speaker_entity_index")
            if speaker in (None, "self") and explicit is None:
                return None
            if speaker == "player" and explicit is None:
                return 0x81
            if explicit is not None:
                if type(explicit) is not int or not 0 <= explicit < initial_entities or explicit >= 127:
                    raise ValueError("Dialogue speaker needs an existing native entity index on this map")
                return explicit
            if isinstance(speaker, str) and speaker.startswith("database:") and speaker not in actor_indices:
                # A database NPC as the speaker (user 2026-10-26): its character on this map speaks when
                # there is exactly one; otherwise the text shows without a portrait (it was skipped).
                cid = speaker[len("database:"):]
                here = [row["entity_index"] for row in getattr(session, "content_database", {}).get("instances", [])
                        if row.get("class_id") == cid and row.get("map_id") == map_id]
                here += [actor_indices[g["id"]] for g in group if g["id"] in actor_indices
                         and ((g.get("pages") or [{}])[0].get("class_id", g.get("class_id")) == cid)]
                if len(here) == 1 and type(here[0]) is int and 0 <= here[0] < 127:
                    return here[0]
                return None
            if speaker in actor_indices:
                index = actor_indices[speaker]
            else:
                candidates = [row["entity_index"] for row in getattr(session, "content_database", {}).get("instances", [])
                    if row.get("id") == speaker and row.get("map_id") == map_id]
                if len(candidates) != 1:
                    raise ValueError("Choose a dialogue speaker instance on this map, self or player")
                index = candidates[0]
                if type(index) is not int or not 0 <= index < initial_entities:
                    raise ValueError("Dialogue speaker instance is stale or missing from this map")
            if not 0 <= index < 127:
                raise ValueError("Dialogue speaker exceeds native InitData selector range")
            return index
        def voiced(command, text):
            # the speaker's dialogue voice (npc_voices: the game's default per class, or the class's
            # own setting) as the text's first control code (user 2026-10-26)
            import npc_voices
            speaker = command.get("speaker")
            cid = None
            if isinstance(speaker, str) and speaker.startswith("database:"):
                cid = speaker[len("database:"):]
            elif speaker in (None, "self"):
                cid = (graph.get("pages") or [{}])[0].get("class_id") or graph.get("class_id")
            elif speaker != "player":
                other = next((g for g in group if g.get("id") == speaker), None)
                if other is not None:
                    cid = (other.get("pages") or [{}])[0].get("class_id") or other.get("class_id")
                else:
                    row = next((r for r in getattr(session, "content_database", {}).get("instances", []) if r.get("id") == speaker), None)
                    cid = (row or {}).get("class_id")
            return npc_voices.apply(text, npc_voices.voice_of(definitions.get(cid))) if cid else text
        def portrait_for(command):
            # A database NPC speaker with no character here: F2 shows its portrait and name
            # (native_portrait_speaker); its art is put on the map without an entity. b'' if impossible.
            speaker = command.get("speaker")
            if not (isinstance(speaker, str) and speaker.startswith("database:")) or speaker in actor_indices:
                return b''
            catalogue = definitions.get(speaker[len("database:"):], {}).get("source", {}).get("catalogue_index")
            from native_portrait_speaker import compile_portrait
            exported.data, code = compile_portrait(exported.data, map_id, catalogue, keep=local_slots, taken=portrait_cells)
            if code:
                local_slots.add(catalogue - 256)
            return code or b''
        gift_templates = []
        def item_id_for(row):
            definition = definitions.get(row.get("item_class_id"))
            if definition is None or definition.get("kind") not in ("item", "weapon", "armor"):
                raise ValueError("Choose a native inventory item class")
            require_native_class_definition(session, definition)
            source = definition.get("source", {})
            item_id = source.get("item_id")
            if type(item_id) is not int or not 1 <= item_id <= 89 or source.get("catalogue_index") != item_id + 30:
                raise ValueError("Item class has no verified native inventory/catalogue identity")
            return item_id
        for graph in group:
            from compile_yield import step as _step;_step()   # the build warm-up steps aside between events (user 2026-10-27)
            position_route_info=None
            page, trigger, class_id, placement = validate(graph)
            recovered_object = graph['id'] in recovered_objects
            book_interaction = graph['id'] in decorative_interactions
            sign_interaction = graph['id'] in sign_interactions
            stool_activation = graph['id'] in stool_activations
            retained_context = (class_id is None and trigger in ("touch", "autorun", "parallel", "interact")) or recovered_object or sign_interaction or stool_activation
            walking = [row for current in graph["pages"] for row in _walk(current.get("commands", []))
                       if row.get("type") == "move_actor" and row.get("mode") in ("route", "walk_tiles")]
            npc_route_continuation = bool(walking)
            if npc_route_continuation:
                from native_actor_route_profile import VERIFIED_FIXED_NPC_ROUTE_CLASSES
                route_definition = definitions.get(class_id, {})
                if (route_definition.get("kind") != "npc"
                        or route_definition.get("source", {}).get("catalogue_index") not in VERIFIED_FIXED_NPC_ROUTE_CLASSES
                        or trigger != "interact" or len(graph["pages"]) != 1
                        or page.get("conditions") or len(walking) != 1
                        or walking[0] not in page.get("commands", [])
                        or (any(row.get("type") == "show_dialogue" for row in page.get("commands", []))
                            and route_definition.get("source", {}).get("catalogue_index") not in (256,260))
                        or (any(row.get("type") in ("set_switch", "set_variable") for row in page.get("commands", []))
                            and route_definition.get("source", {}).get("catalogue_index") != 260)
                        or any(row.get("type") in ("set_switch", "set_variable")
                               and row.get("switch_scope" if row.get("type") == "set_switch" else "variable_scope") != "project"
                               for row in page.get("commands", []))
                        or any(row.get("type") not in ("move_actor", "change_money", "wait", "show_dialogue", "set_switch", "set_variable")
                               for row in page.get("commands", []))
                        or walking[0].get("movement_speed", 100) != 100
                        or walking[0].get("moving_animation") != 1
                        or walking[0].get("idle_animation") != 0
                        or walking[0].get("blocked_behavior", "wait") != "wait"):
                    raise ValueError("Walking currently needs one unconditional Interact page on a tested new fixed NPC class, one self route, native speed100 and wait when blocked; other actor controllers need a verified retained movement continuation")
                retained_context = True
            if any(row.get("type") == "repeat" for current in graph["pages"] for row in _walk(current.get("commands", []))) and not retained_context:
                raise ValueError("Repeat actions currently require a graphic-free Player Touch event with retained native B context")
            needs_ordered_continuation = (any(any(row.get("type") == "show_dialogue" for row in list(_walk(current.get("commands", [])))[:-1]) for current in graph["pages"])
                or any(row.get("type") == "play_victory" for current in graph["pages"] for row in _walk(current.get("commands", [])))) and not retained_context \
                and (graph.get("pages") or [{}])[0].get("trigger") != "death"   # death actions run in the death script
            npc_continuation = False
            presence = _presence_condition(graph)
            # Bounds must be the actual map shape, not only byte width.
            from area_map import grid
            w, h, cells = grid(exported, map_id)
            if graph.get("_floor_switch") and "z" not in graph["_floor_switch"]:
                _fx, _fy = graph["_floor_switch"]["tile"]
                graph["_floor_switch"]["z"] = cells[_fy * w + _fx]["values"][3]
            if class_id is None and trigger == "interact":   # 2026-10-23: its tile area is tested by 3B
                graph["_interact_area"] = list(graph["region"])
            if class_id is None and trigger in ("autorun", "parallel", "interact"):
                graph["region"] = [0, 0, w, h]   # a whole-map controller (as the Play Victory watcher)
            x, y, rw, rh = graph["region"]
            if x + rw > w or y + rh > h:
                raise ValueError(f"{graph['name']}: event region is outside this map")
            if graph.get("_hit_marker"):
                import stock_donors as _sd
                marker = graph["_hit_marker"]
                row = _hit_marker_record(exported.data, _sd.original_of(session), map_id, x, y,
                                         graph.get("native_placement", {}).get("height", cells[y*w+x]["values"][3]))
                hit_code = _hit_touched_program(marker["elements"], compile_project_command(
                    {"type": "set_switch", "switch_scope": "project", "switch_id": marker["request"], "value": True},
                    state_registry, state_slots))
                # A: native 2A, the attack scan's target bit (+6C bit0, 0x8003E6D4), and 63 80 0080 (clears
                # +6C 0x80, 0x80040060), the stock freezable Flame's "solid off" (map 443), so the spot does
                # not block walking (onto the item it is on); D: touched
                exported.data, a_alloc = append_native_process(exported.data, map_id, "A", bytes((0x2A, 0x63, 0x80, 0x80, 0x00, 0xFF)))
                exported.data, d_alloc = append_native_process(exported.data, map_id, "D", hit_code)
                follow_alloc = None
                if marker.get("follow"):   # a lifted / thrown / pushed / rolled object: the spot follows it (native_hit_follow)
                    from native_hit_follow import follow_program, OPCODE as _FOLLOW
                    if marker["follow"] not in actor_indices:
                        raise ValueError(f"{graph['name']}: its object is not placed on this map")
                    # D first drops a hit by the object itself (EF clears it), then tests the attack type
                    exported.data, d_alloc = append_native_process(exported.data, map_id, "D",
                        bytes((_FOLLOW, actor_indices[marker["follow"]])) + hit_code)
                row[10], row[13] = a_alloc["hook_value"], d_alloc["hook_value"]
                if marker.get("follow"):
                    exported.data, follow_alloc = append_native_process(exported.data, map_id, "C", follow_program(actor_indices[marker["follow"]]))
                    row[12] = follow_alloc["hook_value"]
                template = bytes(row)
                marker_report = {"map_id": map_id, "bank": None, "native_passive": True, "hit_spot": {
                    "source": "map 10 entity 1 (global sprite 25)", "A": a_alloc, "D": d_alloc,
                    "attack_elements": marker["elements"], "request_switch": marker["request"]},
                    "opcodes": sorted(set(_generated_opcodes(hit_code) + [0x2A, 0x63] + ([0xEF, 0x17, 0x2E] if follow_alloc else []))), "gameplay_verified": False}
                if follow_alloc:
                    marker_report["hit_spot"].update(C=follow_alloc, follows=marker["follow"], owner_record=actor_indices[marker["follow"]])
                if presence:
                    exported.data, watcher = _presence_watcher(exported.data, map_id, presence, template,
                        actor_indices[graph["id"]], project_condition, w, h, None, item_resolver=item_id_for)
                    marker_report["presence_controller"] = watcher
                    marker_report["opcodes"] = sorted(set(marker_report["opcodes"] + watcher["opcodes"]))
                pending.append((graph, template, marker_report))
                continue
            template = None
            initial_pose = None; float_code = None
            portable_werewolf = None
            portable_magicpot = None
            builtins = []
            native_chest = False
            cleared_npc_hooks = {}
            synthesized = False
            transplant_from = None
            victory_home = None
            behaviour_report = None
            if class_id is not None:
                definition = definitions.get(class_id)
                if definition is None or definition.get("kind") not in ("npc", "object", "enemy", "boss", "item", "weapon", "armor"):
                    raise ValueError("Choose an existing placeable database class")
                source = definition.get("source", {})
                catalogue = source.get("catalogue_index")
                if catalogue is None:
                    catalogue = source.get("balance_index")
                if type(catalogue) is not int:
                    raise ValueError("Class has no proven native catalogue identity for donor placement")
                require_native_class_definition(session, definition, allow_map_class_hue=catalogue in palette_forks)
                if definition.get('kind') == 'object' and catalogue == 409 and graph.get('native_placement', {}).get('magicpot_sprouted'):
                    # Only on request: start already sprouted (bouncing). By default a placed
                    # Magic Pot (Boing) is left exactly like the game's own (no program of its
                    # own), so its native routine waits for the Spring Bean as in the stock game.
                    from native_magicpot_donor import donor, CALLBACKS
                    from event_vm_compatibility import sprite_callbacks
                    portable_magicpot = donor(exported.data)
                    if sprite_callbacks(exported.data,map_id,catalogue)!=CALLBACKS:
                        raise ValueError('Magicpot target native bounce callbacks differ')
                if definition.get('kind') == 'boss' and catalogue == 482:
                    from native_werewolf_donor import donor, CALLBACKS
                    from event_vm_compatibility import sprite_callbacks
                    portable_werewolf = donor(exported.data)
                    if sprite_callbacks(exported.data,map_id,catalogue)!=CALLBACKS:
                        raise ValueError('Standalone Werewolf target native AI callbacks differ')
                inventory_pickup = definition.get("kind") in ("item", "weapon", "armor")
                imported = imported_placements.get(graph["id"])
                if inventory_pickup:
                    # _expand_item_pages leaves each item page as one page whose actions run from
                    # its own controller after the pickup; anything else here is a build error.
                    if len(graph["pages"]) != 1 or page.get("commands") or (page.get("conditions") and presence is None):
                        raise ValueError(f"{graph.get('name')}: internal: item page was not prepared for its pickup")
                    item_id = item_id_for({"item_class_id": class_id})
                    template = verified_item_pickup_template(exported.data, item_id)
                    if template is None:
                        raise ValueError("Item has no verified native ground pickup asset")
                    row = bytearray(template)
                    row[7:10] = bytes((x*2, y*2, graph.get("native_placement", {}).get("height", cells[y*w+x]["values"][3])*2))
                    template = bytes(row)
                elif imported is not None and imported[1] is None:
                    from behavior_transplant import synthetic_record
                    template = synthetic_record(exported.data, map_id, catalogue, x, y,
                        graph.get("native_placement", {}).get("height", cells[y*w+x]["values"][3]))
                    synthesized = True
                elif imported is not None:
                    from local_sprite_import import imported_actor_record
                    template = imported_actor_record(exported.data, imported[0], imported[1], x, y,
                        graph.get("native_placement", {}).get("height", cells[y*w+x]["values"][3]))
                elif type(placement.get("donor_entity_index")) is not int:
                    resolved = resolve_class_donor(exported.data, map_id, catalogue)
                    if resolved is None:
                        from native_class_placement import global_sprite_available
                        if catalogue >= 256 or not global_sprite_available(exported.data, catalogue):
                            raise ValueError("This class has no graphics anywhere in the game data")
                        # No map places this shared-bank class: a fresh record.
                        from behavior_transplant import synthetic_record
                        template = synthetic_record(exported.data, map_id, catalogue, x, y,
                            graph.get("native_placement", {}).get("height", cells[y*w+x]["values"][3]))
                        synthesized = True
                    else:
                        placement = resolved
                if definition.get("kind") in ("enemy", "boss", "object") and not synthesized:
                    if imported is not None:
                        donor_map = imported[0]["donor_map"]
                        donor_index = imported[1]
                    else:
                        donor_map = placement.get("donor_map_id", map_id)
                        donor_index = placement.get("donor_entity_index")
                    if portable_werewolf is not None:
                        if (donor_map,donor_index)!=(portable_werewolf['map_id'],portable_werewolf['entity_index']):
                            raise ValueError('Standalone Werewolf source instance differs')
                        donor_raw = record_cluster(exported.data,donor_map)['entities'][donor_index]
                        if donor_raw.hex()!=portable_werewolf['record_hex']:
                            raise ValueError('Standalone Werewolf source instance differs')
                    victory_home = donor_map; victory_homes[graph['id']] = donor_map
                    if donor_map != map_id and type(donor_index) is int:
                        donor_raw = record_cluster(exported.data, donor_map)["entities"][donor_index]
                        if not recovered_object and portable_werewolf is None:
                            # Keep its behaviour: the donor's own map scripts are
                            # copied onto this map below (behavior_transplant).
                            transplant_from = (donor_map, bytes(donor_raw[10:16]), bytes(donor_raw[7:10]))
                        elif portable_werewolf is not None and (donor_map,donor_index,donor_raw.hex()) != (portable_werewolf['map_id'],portable_werewolf['entity_index'],portable_werewolf['record_hex']):
                            raise ValueError('Standalone Werewolf source instance differs')
                if imported is None and not inventory_pickup and not synthesized:
                    template = donor_record_for_map(exported.data, map_id, placement.get("donor_map_id", map_id), placement["donor_entity_index"], x, y, graph.get("native_placement", {}).get("height", cells[y*w+x]["values"][3]))
                donor_catalogue = template[6] + (256 if template[5] & 128 else 0)
                if donor_catalogue != catalogue:
                    raise ValueError("Selected donor belongs to another native class")
                # Authored instances are independent of the donor's collection
                # state. Native SetGameOrTemporaryFlag treats0 as a no-flag
                # sentinel; stock records remain byte-identical.
                template = bytearray(template)
                # A donor can be a dormant stock actor. Authored placements must
                # start enabled independently; opt-in watcher clears this below.
                template[5] |= 0x40
                requested = graph.get("native_placement", {})
                direction_index = requested.get("direction")
                if direction_index is not None:
                    if type(direction_index) is not int or not 0 <= direction_index <= 3:
                        raise ValueError("Direction must be0..3")
                    template[5] = (template[5] & 0xFC) | direction_index
                facing = requested.get("facing")
                if facing is not None:
                    direction = {"down": 0, "up": 1, "left": 2, "right": 3}
                    if facing not in direction:
                        raise ValueError("Facing must be up, down, left or right")
                    template[5] = (template[5] & 0xFC) | direction[facing]
                initial_animation = requested.get("initial_animation", requested.get("animation_id"))
                initial_pose = None
                if initial_animation is not None:
                    if definition.get("kind") != "npc" or (template[10] and not template[10] & 0x80):
                        raise ValueError("Initial pose currently needs a new NPC without an inherited load process")
                    from event_movement_compile import animation_profile
                    poses = animation_profile(exported.data, catalogue, map_id)
                    if type(initial_animation) is not int or not 0 <= initial_animation < len(poses) or not poses[initial_animation]["directions_valid"][(0,2,1,3)[template[5] & 3]]:
                        raise ValueError("Choose an existing NPC pose with a valid selected direction")
                    initial_pose = bytes((0x1A, initial_animation, 0xFF))
                float_code = None
                if page.get("float"):
                    # Float: the load process (A) turns this character's gravity off (0x17)
                    # and zeroes its vertical speed (0x5E), so it stays at its record Z,
                    # raised by Float height (8 pixels per raw Z unit).
                    lift = page.get("float_height", 0)
                    if type(lift) is not int or not 0 <= lift <= 512:
                        raise ValueError("Float height must be 0..512 pixels")
                    template[9] = min(255, template[9] + (lift + 4) // 8)
                    float_code = bytes((0x17,)) + struct.pack("<BBh", 0x5E, 0x80, 0)
                if graph.get("native_placement", {}).get("frame_index") is not None:
                    raise ValueError("Initial frame selection has no verified native placement compiler")
                template[16:18] = bytes(2)
                from native_pushable_stool import is_stool as _is_stool
                if _is_stool(definition) and transplant_from is not None:   # its talk / tick programs are made below
                    transplant_from = (transplant_from[0], transplant_from[1][:2] + bytes(1) + transplant_from[1][3:5] + bytes(1), transplant_from[2])
                if graph.get('_face') and transplant_from is not None:   # Nirude Face Statue: its C / D are made below
                    transplant_from = (transplant_from[0], transplant_from[1][:2] + bytes(2) + transplant_from[1][4:6], transplant_from[2])
                from native_nirude_statue_variants import variant_of as _statue_variant_of
                _statue_variant = _statue_variant_of(definition)
                if _statue_variant and transplant_from is not None:   # shooting Nirude Face Statue: C / D / emitter made below
                    _statue_from = transplant_from
                    transplant_from = (transplant_from[0], transplant_from[1][:2] + bytes(2) + transplant_from[1][4:6], transplant_from[2])
                if transplant_from is not None and any(transplant_from[1]) and not sign_interaction:   # a sign with actions gets its own F / C
                    from behavior_transplant import transplant_hooks, placement_shift
                    is_boss = definition.get('kind') == 'boss'
                    _moved = placement_shift(transplant_from[2], template[7:10])
                    _chosen = (graph.get('native_placement') or {}).get('spawned_class')
                    _chosen = next((actor_indices[sp['id']] for sp in group if (sp.get('native_placement') or {}).get('spawn_of') == graph['id']
                                    and (sp.get('native_placement') or {}).get('generator_spawn')), None) if _chosen else None
                    behaviour_cache['_freezable_flames'] = bool((graph.get('native_placement') or {}).get('fireballs_freezable'))
                    exported.data, hooks, behaviour_report = transplant_hooks(
                        exported.data, map_id, transplant_from[0], transplant_from[1], behaviour_cache,
                        start_now=is_boss,   # bosses start as in the game, without their room's intro
                        # ... and act on the tile they are placed on, not the donor room's tiles
                        shift=_moved if is_boss else None,
                        # objects keep what they spawn (Launcher Flames, Generator Mud Men), 2026-10-22
                        spawns=None if is_boss else _moved, spawn_target=_chosen,
                        player_box=_player_box(graph, template))
                    behaviour_cache.pop('_freezable_flames', None)
                    template[10:16] = hooks
                    if is_boss and template[6] + (256 if template[5] & 128 else 0) == 418 and map_id != transplant_from[0]:
                        # Melzas's native AI teleports to his room's points: move them with him (native_melzas_points)
                        places = getattr(exported, 'melzas_places', None) or {}
                        offset = ((template[7] - transplant_from[2][0]) * 12, (template[8] - transplant_from[2][1]) * 8,
                                  (template[9] - transplant_from[2][2]) * 8)
                        if places.get(map_id, offset) != offset:
                            raise ValueError(f'Map {map_id}: two Melzas placements need one position (his points follow one of them)')
                        places[map_id] = offset; exported.melzas_places = places
                if graph.get('_face'):   # Nirude Face Statue: destructible once activated (native_nirude_face)
                    from native_nirude_face import install as _face_install
                    _fcounts = getattr(exported, 'face_counts', None)
                    if _fcounts is None: _fcounts = {}; exported.face_counts = _fcounts
                    _on = lambda sid: project_condition({'type': 'switch', 'switch_scope': 'project', 'switch_id': sid, 'value': True, 'operator': '=='})
                    exported.data, _hooks, _face_report = _face_install(
                        exported.data, map_id, bytes(template[10:16]), _fcounts, _on(graph['_face']['state']), _on(graph['_face']['broken']),
                        compile_project_command({'type': 'set_switch', 'switch_scope': 'project', 'switch_id': graph['_face']['broken'], 'value': True}, state_registry, state_slots))
                    template[10:16] = _hooks
                    exported.face_reports = getattr(exported, 'face_reports', []) + [dict(_face_report, event=graph['id'])]
                if _statue_variant and transplant_from is not None and graph.get('_statue'):   # Nirude Face Statue (Fire / Homing Fire / Laser)
                    from native_nirude_statue_variants import install as _statue_install
                    from behavior_transplant import placement_shift as _pshift
                    _scounts = getattr(exported, 'statue_counts', None)
                    if _scounts is None: _scounts = {}; exported.statue_counts = _scounts
                    exported.data, (_c, _d), _emitter, _statue_report = _statue_install(
                        exported.data, map_id, _statue_variant, behaviour_cache, _pshift(_statue_from[2], template[7:10]), _scounts,
                        *(project_condition({'type': 'switch', 'switch_scope': 'project', 'switch_id': graph['_statue'][k], 'value': True, 'operator': '=='}) for k in ('state', 'broken')),
                        compile_project_command({'type': 'set_switch', 'switch_scope': 'project', 'switch_id': graph['_statue']['broken'], 'value': True}, state_registry, state_slots))
                    template[12] = _c; template[13] = _d
                    tracking_hooks.append(_emitter)   # its room loop runs as a whole-map B process
                    exported.statue_reports = getattr(exported, 'statue_reports', []) + [dict(_statue_report, event=graph['id'])]
                if _is_stool(definition) and not stool_activation:   # Stool (Pushable): one tile in any allowed direction (native_pushable_stool)
                    from native_pushable_stool import install as _stool_install
                    _counts = getattr(exported, 'stool_counts', None)
                    if _counts is None: _counts = {}; exported.stool_counts = _counts
                    from native_pushable_stool import switch_templates as _stool_switches
                    exported.data, _hooks, _stool_report = _stool_install(exported.data, map_id, bytes(template[10:16]), graph, _counts,
                        switches=_stool_switches(exported.data, map_id, group, definitions, actor_indices))
                    template[10:16] = _hooks; exported.stool_reports = getattr(exported, 'stool_reports', []) + [dict(_stool_report, event=graph['id'])]
                from native_boss_points import SITES as _BOSS_SITES
                _cls = template[6] + (256 if template[5] & 128 else 0)
                if transplant_from is not None and definition.get('kind') == 'boss' and _cls in _BOSS_SITES and map_id != transplant_from[0]:
                    # its native AI's fixed room positions/heights follow the placement (native_boss_points)
                    _all = dict(getattr(exported, 'boss_places', None) or {})
                    _rows = dict(_all.get(_cls, {}))
                    _off = ((template[7] - transplant_from[2][0]) * 12, (template[8] - transplant_from[2][1]) * 8,
                            (template[9] - transplant_from[2][2]) * 8)
                    if _rows.get(map_id, _off) != _off:
                        raise ValueError(f'Map {map_id}: two placements of boss {_cls} need one position')
                    _rows[map_id] = _off; _all[_cls] = _rows; exported.boss_places = _all
                if portable_werewolf is not None:
                    from native_werewolf_donor import INITIALIZER
                    # Source-room arena/camera/story hooks are excluded only
                    # from this newly authored actor; native C37/D11/E1 stay.
                    template[10:16] = bytes(6)
                    initial_pose = INITIALIZER
                if definition.get("kind") == "npc":
                    # Instance high80 chooses current-map event roots; these are
                    # donor story logic, not sprite-header/native class callbacks.
                    # Preserve low shared-bank hooks and every original record.
                    for index, value in enumerate(template[10:16]):
                        if value & 0x80:
                            cleared_npc_hooks["ABCDEF"[index]] = value
                            template[10 + index] = 0
                template = bytes(template)
                if npc_route_continuation:
                    if (any(template[10:15]) or template[18:20] != bytes(2)
                            or presence or initial_pose is not None):
                        raise ValueError("Retained walking needs a tested new fixed NPC without inherited load/tick/touch/deactivation hooks, contents or conditional presence")
                    npc_continuation = True
                if book_interaction:
                    from native_book_interaction import require_placed_template
                    require_placed_template(exported.data,map_id,template)
                    npc_continuation = True
                    retained_context = True
                if graph.get('_act_as_npc'):
                    template = bytearray(template); template[10:16] = bytes(6); template = bytes(template)   # its own programs are replaced (below)
                if needs_ordered_continuation and not book_interaction:
                    if ((definition.get("kind") != "npc" and not graph.get('_act_as_npc')) or trigger != "interact"
                            or any(template[10:15]) or template[18:20] != bytes(2)
                            or any(row.get("type") in ("move_actor", "warp_player", "spawn_class", "set_event_active") for current in graph["pages"] for row in _walk(current.get("commands", [])))):
                        raise ValueError("Ordered NPC dialogue currently needs a newly placed fixed NPC with no inherited load/tick/touch/deactivation hooks, movement or transition commands")
                    npc_continuation = True
                    retained_context = True
                if presence:
                    if class_id is None or w == h == 1:
                        raise ValueError("Condition-based presence needs a placed actor and a nonempty full-map controller region")
                    from native_actor_lifecycle import conditional_template
                    template = conditional_template(template)
                from event_graph import chest_item_for_page
                contained = chest_item_for_page(page, definition)
                if catalogue == 30 and not contained:
                    raise ValueError("Choose an item for the placed Chest before building the game")
                if contained:
                    if catalogue != 30 or template[5] & 128:
                        raise ValueError("Assign chest items to the native Chest class30; chest-looking class227 has no chest callbacks")
                    if trigger != "interact" or page.get("commands") or len(graph["pages"]) != 1 or (page.get("conditions") and presence is None):
                        raise ValueError("Native chest opening uses its built-in interaction; leave Contents commands empty")
                    item_id = item_id_for({"item_class_id": contained})
                    if verified_chest_template(exported.data, item_id) is None:
                        raise ValueError("Chest or item has no verified native callbacks/pickup asset")
                    template = bytearray(template)
                    template[10:16] = bytes(6)
                    struct.pack_into("<H", template, 18, item_id)
                    # Its own saved game flag: once opened it stays open (and
                    # empty) on every later visit, like the game's own chests.
                    struct.pack_into("<H", template, 16, chest_flag_for(getattr(session, "content_database", None) or {}, graph["id"]))
                    template = bytes(template)
                    native_chest = True
            initial_pose_report = None
            if template is not None and float_code is not None and template[10] and initial_pose is None:
                raise ValueError(f"{graph.get('name')}: Float needs a character without its own load process (A); choose another source character")
            if template is not None and (initial_pose is not None or float_code is not None):
                exported.data, initial_pose_report = append_native_process(exported.data, map_id, "A", (a_code := (float_code or b"") + (initial_pose or bytes((0xFF,)))))
                row = bytearray(template); row[10] = initial_pose_report["hook_value"]; template = bytes(row)
            chosen_animation = (graph.get("native_placement") or {}).get("animation")
            if chosen_animation is None and definition.get("kind") == "npc" and (definition.get("data") or {}).get("ai_movement") == "stand":
                chosen_animation = int((definition.get("data") or {}).get("ai_idle_animation") or 0)   # Edit AI: Stand still
            if template is not None and chosen_animation is not None:
                # Event menu "Animation": the NPC's tick program sets this animation once
                # when the map loads; the native animation player loops it until an event
                # command changes it. It replaces the class's own tick program (wandering).
                if definition.get("kind") != "npc":
                    raise ValueError("Choosing an on-map animation is for NPCs")
                from event_movement_compile import animation_profile
                poses = animation_profile(exported.data, catalogue, map_id)
                if type(chosen_animation) is not int or not 0 <= chosen_animation < len(poses):
                    raise ValueError("Choose one of this NPC's animations")
                program = bytes((0x1A, chosen_animation, 0xFF))
                exported.data, loop_report = append_native_process(exported.data, map_id, "C", program)
                row = bytearray(template); row[12] = loop_report["hook_value"]; template = bytes(row)
            passive = len(graph["pages"]) == 1 and not page.get("commands") and (not page.get("conditions") or presence is not None) and not stool_activation
            if portable_magicpot is not None:
                from native_magicpot_donor import INITIALIZER
                if not passive or template is None or any(template[10:16]) or initial_pose is not None:
                    raise ValueError('Magicpot initializer needs a newly authored passive object without inherited programs')
                exported.data, allocation = append_native_process(exported.data,map_id,'C',INITIALIZER)
                row=bytearray(template);row[12]=allocation['hook_value'];template=bytes(row)
                pending.append((graph,template,{'map_id':map_id,'bank':'C','opcodes':[0x1A,0x40,0xFF],
                    'hook_value':allocation['hook_value'],'native_passive':True,
                    'native_magicpot':{**portable_magicpot,'allocation':allocation},
                    'sprite_callbacks':sprite_callbacks(exported.data,map_id,catalogue),'gameplay_verified':False}))
                continue
            custom_ai = (definition.get("data") or {}).get("custom_ai") or {}
            if custom_ai.get("mode") == "custom" and template is not None and definition.get("kind") in ("enemy", "boss", "object"):
                # Edit AI > Custom: this enemy's tick program (C) is our compiled behaviour.
                from native_custom_ai import compile_custom_ai
                from animation_preview import available_animations
                from animation_names import auto_names
                choices = available_animations(exported, map_id, catalogue)
                names = auto_names(exported, definition, choices)
                walk = next((i for i, n in names.items() if n.startswith('Walking')), 1)
                idle = next((i for i, n in names.items() if n.startswith('Idle')), 0)
                from event_vm_compatibility import sprite_callbacks
                spawn_templates = {(sp.get('native_placement') or {}).get('spawn_class'): actor_indices[sp['id']] for sp in group
                                   if (sp.get('native_placement') or {}).get('spawn_of') == graph['id']}
                from native_custom_ai import swing_frames
                from animation_preview import load_animation
                swings = {}
                for att in custom_ai.get('attacks') or []:   # default lunge window: the attack-box frames
                    if att.get('animation') is not None and att['animation'] not in swings:
                        try: swings[att['animation']] = swing_frames(load_animation(exported, map_id, catalogue, att['animation'], 0).frames)
                        except Exception: swings[att['animation']] = None
                from native_custom_ai import stock_death_animation
                death_anim = custom_ai['death_animation'] if 'death_animation' in custom_ai else stock_death_animation(definition)
                lengths = {}
                for anim in {att.get('animation') for att in custom_ai.get('attacks') or []} - {None}:   # whole-animation waits, checked for death
                    try: lengths[anim] = sum(f.ticks for f in load_animation(exported, map_id, catalogue, anim, 0).frames)
                    except Exception: pass
                anim_sounds = {}
                try:
                    from anim_tails import tails
                    anim_sounds = {i: r['sfx'] for i, r in enumerate(tails(exported, map_id, catalogue))}
                except Exception: pass
                # the class's native D (template, else its sprite's callback): its hurt animation is kept
                # when a dart trigger replaces D (native_custom_ai.hit_program)
                from native_custom_ai import STUN_ANIMATIONS
                native_d = template[10 + 'ABCDEF'.index('D')]
                if not native_d:
                    try: native_d = dict(sprite_callbacks(exported.data, map_id, catalogue)).get('D', 0)
                    except Exception: native_d = 0
                stun_anim = STUN_ANIMATIONS.get(native_d)
                code = compile_custom_ai(custom_ai, walk_animation=walk, idle_animation=idle, class_bits=None, spawn_templates=spawn_templates, swings=swings, owner=definition.get('name') or definition.get('id'), death_animation=death_anim, lengths=lengths, anim_sounds=anim_sounds, stun_animation=stun_anim)
                exported.data, ai_alloc = append_native_process(exported.data, map_id, "C", code + b"\xff")
                row = bytearray(template); row[10 + 'ABCDEF'.index('C')] = ai_alloc['hook_value']; template = bytes(row)
                # objects only (for enemies E is their death handling); on unless unticked
                if definition.get("kind") == "object" and custom_ai.get("destroy_on_wall", True):
                    # Destroy when it hits a wall: projectile classes (header flag 0x10, e.g. Zorgia's
                    # blades) get status 3 from the engine at a wall; status 3 runs E every frame and
                    # never C again. E = remove this character (docs/2026-10-20-zorgia-projectile-lifecycle.txt).
                    exported.data, wall_alloc = append_native_process(exported.data, map_id, "E", bytes((0x2E, 0x80, 0xFF)))
                    row = bytearray(template); row[10 + 'ABCDEF'.index('E')] = wall_alloc['hook_value']; template = bytes(row)
                from native_custom_ai import hit_program
                hit_code = hit_program(custom_ai, stun_anim)
                if hit_code is not None and definition.get("kind") in ("enemy", "boss"):
                    # No hit stun / dart counters: D (hit reaction) = our program instead of the class's
                    # native D (stock D 8 = damage + hurt animation 4 + face away + knockback, 0x80080640)
                    exported.data, hit_alloc = append_native_process(exported.data, map_id, "D", hit_code + bytes((0xFF,)))
                    row = bytearray(template); row[10 + 'ABCDEF'.index('D')] = hit_alloc['hook_value']; template = bytes(row)
                reports.append({"event_id": graph["id"] + "/custom_ai", "map_id": map_id, "bank": "C",
                                "hook_value": ai_alloc['hook_value'], "opcodes": _generated_opcodes((hit_code or b"") + code + b"\xff"),
                                "custom_ai": {"walk_animation": walk, "idle_animation": idle, "attacks": len(custom_ai.get("attacks") or []),
                                              "route_steps": len(custom_ai.get("route") or [])}, "gameplay_verified": False})
            if graph['id'] in recovered_default_routes:
                from event_vm_compatibility import sprite_callbacks
                route_entry=recovered_default_routes[graph['id']]
                native_animation_route=route_entry['command'].get('_native_animation_route') is True
                if template is None or initial_pose is not None:
                    raise ValueError('Default movement needs a placed character, enemy, item or object without an initial pose override')
                if native_animation_route and (any(template[11 if float_code else 10:16]) or template[18:20] != bytes(2)):
                    raise ValueError('The tested animation route needs an instance without inherited callbacks or contents')
                from native_default_route_profile import compile_default_route
                if 'slot' in route_entry:
                    from native_default_route_interaction import compile_immediate_interaction
                    from native_event_commands import encode_insert
                    dialogue,reward=page['commands']
                    exported.data,text_report=append_local_text(exported.data,map_id,dialogue.get('text'),auto_wrap=dialogue.get('auto_wrap',True))
                    programs,profile=compile_immediate_interaction(exported.data,catalogue,route_entry['command'],state_registry,
                        route_entry['busy_id'],text_report['dialogue_reference'],map_id=map_id,reward=encode_insert(reward),slot=route_entry['slot'])
                    profile.update(optional_runtime_feature='actor_route_resume',text=text_report,
                        evidence='data/2026-10-06-two-default-route-interaction-runtime.json',cold_boot_profile_verified=True)
                else:
                    programs, profile = compile_default_route(exported.data, catalogue, route_entry['command'], map_id=map_id)
                allocations = {}
                row = bytearray(template)
                for route_bank, route_code in programs.items():
                    exported.data, allocations[route_bank] = append_native_process(exported.data, map_id, route_bank, route_code)
                    row[10 + 'ABCDEF'.index(route_bank)] = allocations[route_bank]['hook_value']
                if not native_animation_route and 'slot' not in route_entry:
                    template=bytes(row)
                    position_route_info={'profile':profile,'allocations':allocations,
                        'opcodes':sorted(set(op for body in programs.values() for op in _generated_opcodes(body)))}
                else:
                    profile.update(kind='owned-default-route', cold_boot_profile_verified=True)
                    if 'slot' not in route_entry:
                        profile['evidence']='data/2026-10-06-default-route-jess-runtime.json' if catalogue == 260 else 'data/2026-10-06-default-route-beaumont-runtime.json'
                    pending.append((graph, bytes(row), {'map_id':map_id, 'bank':'C',
                        'hook_value':allocations['C']['hook_value'],
                        'opcodes':sorted(set(op for body in programs.values() for op in _generated_opcodes(body))), 'native_default_route':profile,
                        'native_chest':native_chest,
                        'contained_item_id':item_id if native_chest else None,
                        'sprite_callbacks':sprite_callbacks(exported.data,map_id,catalogue) if native_chest else None,
                        'allocations':allocations, 'gameplay_verified':False}))
                    continue
            if passive and template is None:
                # A blank classless event is an editor placeholder, not a
                # running region with a fabricated FF-only callback.
                reports.append({"event_id": graph["id"], "map_id": map_id,
                    "bank": None, "opcodes": [], "native_passive": True,
                    "placement": "no actor or authored action"})
                continue
            if (passive or native_chest) and not recovered_object:
                from event_vm_compatibility import sprite_callbacks
                passive_report={"map_id": map_id, "bank": "C" if position_route_info else None,
                    "opcodes": sorted(set((_generated_opcodes(a_code) if initial_pose_report else []) + (position_route_info or {}).get('opcodes',[]))), "initial_pose": initial_pose_report, "native_chest": native_chest, "native_passive": passive,
                    "native_pickup": definition.get("kind") in ("item", "weapon", "armor"),
                    "collection_persistence": ("once: project switch %d set when picked up" % graph["_once"]["killed"]
                        if definition.get("kind") in ("item", "weapon", "armor") and graph.get("_once") else "none; respawns on room reload"),
                    "standalone_werewolf": portable_werewolf,
                    "sprite_callbacks": sprite_callbacks(exported.data, map_id, catalogue) + (sprite_callbacks(exported.data, map_id, item_id + 30) if native_chest else []),
                    "gameplay_verified": False}
                if position_route_info:
                    passive_report['native_default_route']=position_route_info['profile']
                    passive_report['allocations']=position_route_info['allocations']
                if behaviour_report is not None:
                    passive_report['behaviour_transplant'] = behaviour_report
                if presence:
                    exported.data, watcher = _presence_watcher(exported.data, map_id, presence, template,
                                                               actor_indices[graph["id"]], project_condition, w, h,
                                                           _once_per_visit(graph, definition, state_registry, state_slots, project_condition), item_resolver=item_id_for)
                    passive_report["presence_controller"] = watcher
                    passive_report["opcodes"] = sorted(set(passive_report["opcodes"] + watcher["opcodes"]))
                if synthesized:
                    passive_report['synthesized_record'] = {"reason": "no map places this class", "hooks": "none (class AI only)"}
                pending.append((graph, template, passive_report))
                continue
            text_commands = {}
            if graph['id'] in recovered_deaths:
                from native_enemy_death import compile_death_E, TESTED_DEATH_CALLBACKS
                from event_vm_compatibility import sprite_callbacks
                callbacks=sprite_callbacks(exported.data,map_id,catalogue)
                # A boss with Play Victory: its death actions wait until the victory text is fully
                # dismissed (user 2026-10-27), so they run in the victory watcher, after the routine;
                # its death script keeps only the latch and the hand-back to the game's own death.
                # The watcher sees the boss die by itself, so a boss without the standard death
                # routine (Nightmare Melzas, E 11) keeps its own death script (user 2026-10-27).
                victory_death=(definition.get('kind')=='boss' and not graph.get('_act_as_npc')
                    and (graph.get('native_placement') or {}).get('play_victory', True) is not False)
                own_death=victory_death and ('E',1) not in callbacks
                if ('E',1) not in callbacks and not own_death:
                    raise ValueError(f"{graph['name']}: this enemy does not use the game's standard death routine, so death actions cannot be attached")
                if template[14] and not own_death:
                    raise ValueError(f"{graph['name']}: the enemy copied from another map brings its own death script; choose Automatic behaviour or another enemy")
                death_texts={}
                for command in _walk(page['commands']):
                    if command.get('type')=='show_dialogue':
                        exported.data,text_report=append_local_text(exported.data,map_id,command.get('text'),auto_wrap=command.get('auto_wrap',True))
                        death_texts[id(command)]=bytes([0x0D,text_report['dialogue_reference'],0])
                        if victory_death:victory_text_slots.append(text_report['text_index'])
                        if victory_death:   # the watcher (B) waits for it to close, so a following ending does not cut it off (BizHawk 2026-10-27)
                            from native_dialogue_wait import compile_dialogue_wait
                            death_texts[id(command)]+=compile_dialogue_wait()
                def death_leaf(command):
                    if command.get('type')=='deactivate_switch':
                        _switch_graph[0]=graph;return switch_state_command(command)
                    if command.get('switch_scope')=='project' or command.get('variable_scope')=='project':
                        return compile_project_command(command,state_registry,state_slots)
                    if command.get('type')=='give_item':
                        from native_item_grant import compile_item_grant
                        return compile_item_grant(item_id_for(command),command.get('quantity',1),command.get('obtained_message'))
                    if command.get('type')=='show_dialogue':
                        return death_texts[id(command)]
                    if command.get('type')=='change_music':
                        from music_database import encode_music
                        return encode_music(command.get('music_id'))
                    if command.get('type')=='lock_movement':return bytes((0x10,0x59,0x81,0x00))   # lock, and Alundra stands still
                    if command.get('type')=='unlock_movement':return bytes((0x11,))
                    if command.get('type') in ('back_to_title','play_ending','play_movie'):
                        from native_event_authoring import compile_command as _native
                        return _native(command)
                    raise ValueError(f"{command.get('type')} is not available in death actions")
                if victory_death:
                    from event_logic_compile import compile_logic as _compile_logic
                    victory_after.append(_compile_logic(page['commands'],leaf_emitter=death_leaf,project_condition_emitter=project_condition))
                if own_death:
                    report={'bank':None,'opcodes':[],'sprite_callbacks':callbacks,'death_actions':'victory watcher (own death script kept)','gameplay_verified':False}
                else:
                  code=compile_death_E(state_registry,recovered_deaths[graph['id']],[] if victory_death else page['commands'],clear_latch_before_handoff=True,
                    leaf_emitter=death_leaf,project_condition_emitter=project_condition)
                  exported.data,report=append_native_process(exported.data,map_id,'E',code)
                  report.update(opcodes=_generated_opcodes(code),sprite_callbacks=callbacks,
                    native_enemy_death={'catalogue_index':catalogue,'native_HP_width':32,'HP_field_offset':20,
                        'private_latch_id':recovered_deaths[graph['id']], 'native_E_handoff':[0x40,4,0],
                        'optional_runtime_feature':'enemy_hp_zero','native_AI_retained':True,
                        'native_contents_retained':True,'memory_card_persistent':False,
                        'continuation_lifetime':'native actor lifetime','clear_latch_before_native_handoff':True,
                        'evidence':'data/2026-10-06-eight-enemy-death-per-lifetime-controls.json',
                        'tested_profile':callbacks==TESTED_DEATH_CALLBACKS.get(catalogue)})
                if presence:   # conditions: the enemy is only there while they hold
                    exported.data, watcher = _presence_watcher(exported.data, map_id, presence, template,
                                                               actor_indices[graph["id"]], project_condition, w, h,
                                                           _once_per_visit(graph, definition, state_registry, state_slots, project_condition), item_resolver=item_id_for)
                    report["presence_controller"] = watcher
                    report["opcodes"] = sorted(set(report["opcodes"] + watcher["opcodes"]))
                pending.append((graph,template,report));continue
            gift_commands = {}
            page_commands = [command for current in graph["pages"] for command in current.get("commands", [])]
            # A message right before a Yes / No branch is its question: the
            # choice appears beside it when the text reaches its end (game style).
            prompts = set()
            def _mark_prompts(rows):
                for i, r in enumerate(rows or []):
                    if not isinstance(r, dict):continue
                    nxt = rows[i + 1] if i + 1 < len(rows) else None
                    if (r.get("type") == "show_dialogue" and isinstance(nxt, dict) and nxt.get("type") == "if"
                            and isinstance(nxt.get("condition"), dict) and nxt["condition"].get("type") == "yes_no"):
                        prompts.add(id(r)); nxt["condition"]["_after_prompt"] = True
                    for key in ("then", "else", "commands"):
                        if isinstance(r.get(key), list):_mark_prompts(r[key])
            for current in graph["pages"]:_mark_prompts(current.get("commands", []))
            for command in _walk(page_commands + graph.get('_release_commands', [])):
                if command.get("type") == "show_dialogue":
                    selector = speaker_selector(command)
                    if id(command) in prompts:
                        from dialogue_layout import format_dialogue
                        prompt_text = voiced(command, command.get("text") or "")
                        if command.get("auto_wrap", True):prompt_text = format_dialogue(prompt_text)
                        exported.data, text_report = append_local_text(exported.data, map_id, prompt_text)
                        # randomizer door pattern: plain mode-0 text, then 39 44 in the branch
                        text_commands[id(command)] = (portrait_for(command) + bytes([0x0D, text_report["dialogue_reference"], 0]) if selector is None
                            else compile_speaker_dialogue(selector, text_report["dialogue_reference"]))
                        continue
                    exported.data, text_report = append_local_text(exported.data, map_id, voiced(command, command.get("text")),
                        auto_wrap=command.get("auto_wrap", True))
                    text_commands[id(command)] = (portrait_for(command) + bytes([0x0D, text_report["dialogue_reference"], 0]) if selector is None
                        else compile_speaker_dialogue(selector, text_report["dialogue_reference"]))
                    if retained_context:
                        from native_dialogue_wait import compile_dialogue_wait
                        text_commands[id(command)] += compile_dialogue_wait()
                elif command.get("type") == "play_victory":
                    from boss_victory import markup, sequence
                    exported.data, text_report = append_local_text(exported.data, map_id, markup(command.get("text")))
                    text_commands[id(command)] = sequence(text_report["dialogue_reference"], delay=False)
                elif command.get("type") == "give_item":
                    from native_item_grant import compile_item_grant
                    item_id = item_id_for(command)
                    gift_commands[id(command)] = compile_item_grant(item_id, command.get("quantity", 1), command.get("obtained_message"))
                    if command.get("show_obtained_text", True):
                        # the game's own wording, shown after the item is added
                        item_name = definitions.get(command.get("item_class_id"), {}).get("name") or "Item"
                        exported.data, obtained_report = append_local_text(exported.data, map_id, f"{item_name} obtained!", auto_wrap=True)
                        gift_commands[id(command)] += bytes([0x0D, obtained_report["dialogue_reference"], 0])
                        if retained_context:
                            from native_dialogue_wait import compile_dialogue_wait
                            gift_commands[id(command)] += compile_dialogue_wait()
            commands = page_commands
            if recovered_object:
                supported = {'change_money', 'wait', 'set_switch', 'set_variable', 'if', 'deactivate_switch'}
                if catalogue == 291:
                    supported={'change_money'}
                if catalogue in (301, 364):
                    supported.update(('show_dialogue','give_item'))
                if graph.get('_floor_hidden'):   # Step On Switch (Floor): its picture turns lit / unlit (opcode 85)
                    supported.add('copy_map_tiles')
                if any(row.get('type') not in supported for row in _walk(commands + graph.get('_release_commands', []))):
                    raise ValueError('Recovered object currently supports money, waits, switches, variables and branches; other activation commands need retained-controller testing')
            if needs_ordered_continuation and not npc_continuation:
                raise ValueError("NPC/object dialogue followed by actions needs a verified retained F/D continuation; use a graphic-free Player Touch event and choose this actor as speaker")
            all_commands = list(_walk(commands))
            warps = [command for command in all_commands if command.get("type") == "warp_player"]
            if warps and (len(warps) != 1 or not commands or commands[-1] is not warps[0]):
                raise ValueError("Change map must be the final top-level command")
            if warps and len(graph["pages"]) != 1:
                raise ValueError("Change map on an event with several pages is not compiled; give the Change map page its own event")
            if warps and page.get("conditions") and not (class_id is None and trigger == "touch"):
                # 2026-10-23: a conditional Player Touch region (no character) was tested in game;
                # other triggers / characters with conditions still need their own test
                raise ValueError("Change map on a conditional page is compiled for Player Touch events without a character")
            def leaf(command):
                if command.get("switch_scope") == "project" or command.get("variable_scope") == "project":
                    return compile_project_command(command, state_registry, state_slots)
                if command.get("type") in ("show_dialogue", "play_victory"):
                    return text_commands[id(command)]
                if command.get("type") == "give_item":
                    return gift_commands[id(command)]
                if command.get("type") == "change_music":
                    from music_database import encode_music
                    return encode_music(command.get("music_id"))
                if command.get("type") == "deactivate_switch":
                    _switch_graph[0] = graph
                    return switch_state_command(command)
                if command.get("type") == "change_animation":
                    if class_id is None:raise ValueError("Change Animation needs an event with a graphic")
                    return bytes((0x1A, int(command.get("animation_id", 0))))   # native: this actor plays that animation
                if command.get("type") == "lock_movement":
                    return bytes((0x10, 0x59, 0x81, 0x00))   # native: player loses control and stands still (as the game's scripts do)
                if command.get("type") == "unlock_movement":
                    return bytes((0x11,))      # native: player regains control
                if command.get("type") == "face_actor":
                    from event_movement_compile import compile_facing_command
                    return compile_facing_command(command,has_actor=class_id is not None)
                if command.get("type") == "move_actor":
                    from event_movement_compile import compile_movement_command
                    return compile_movement_command(exported.data,
                        catalogue if class_id is not None else None,command,map_id=map_id)
                if command.get("type") == "warp_player":
                    values = [command.get(k) for k in ("map_id", "x", "y", "z")]
                    if not all(type(v) is int for v in values) or not 0 <= values[0] < 2547 or not all(0 <= v <= 255 for v in values[1:]):
                        raise ValueError("Change map needs native destination map/X/Y/Z")
                    plain = struct.pack("<BH5B", 0x53, *values, 0, 0)
                    # Aligned arrival (user 2026-10-25): from a Player Touch area of several tiles,
                    # Alundra lands at the destination plus his offset inside the area, as the
                    # game's own doors do (use_portal 0x80031898): enter on x+1, land on dest x+1.
                    rx, ry, rw, rh = graph.get("region") or (0, 0, 1, 1)
                    if class_id is None and trigger == "touch" and (rw, rh) != (1, 1) and rw * rh <= 64 \
                            and command.get("align", True) is not False:
                        chunks = []
                        for oy in range(rh):
                            for ox in range(rw):
                                tx, ty = values[1] + ox, values[2] + oy
                                if 0 <= tx <= 255 and 0 <= ty <= 255:
                                    chunks.append((rx + ox, ry + oy, tx, ty))
                        size = 7 + 3 + 8 + 3
                        out = bytearray()
                        for n, (ex, ey, tx, ty) in enumerate(chunks):
                            out += bytes((0x3B, ex, ex, ey, ey, 0, 127))
                            out += struct.pack("<Bh", 0x04, 3 + 8 + 3)      # not on this tile: next test
                            out += struct.pack("<BH5B", 0x53, values[0], tx, ty, values[3], 0, 0)
                            end = (len(chunks) - n - 1) * size + len(plain)   # bytes left after this jump
                            out += struct.pack("<Bh", 0x02, 3 + end)        # warped: skip the rest
                        return bytes(out) + plain
                    return plain
                raise ValueError(f"{command.get('type')} has no verified native compiler yet")
            if len(graph["pages"]) > 1 or page.get("conditions"):
                from event_logic_compile import compile_page_dispatch
                code = compile_page_dispatch(graph["pages"], leaf, item_resolver=item_id_for,
                    continuation_proven=retained_context, project_condition_emitter=project_condition) + b"\xff"
            else:
                code = compile_logic(commands, leaf, item_resolver=item_id_for,
                    continuation_proven=retained_context, project_condition_emitter=project_condition) + b"\xff"
            if graph.get("_floor_switch"):
                fs = graph["_floor_switch"]
                release = compile_logic(fs["release"], leaf, item_resolver=item_id_for,
                    continuation_proven=retained_context, project_condition_emitter=project_condition)
                lit = compile_logic(fs["lit"], leaf, item_resolver=item_id_for,
                    continuation_proven=retained_context, project_condition_emitter=project_condition)
                guard = None
                if not fs["keep_state"] and not fs["while_pressed"]:
                    if len(room_guards) >= 32:
                        raise ValueError(f'Map {map_id}: at most 32 switches reset on entering the room')
                    guard = 0x87A0 + len(room_guards); room_guards.append(graph['id'])
                from native_floor_switch_profile import compile_tile_floor_switch
                code = compile_tile_floor_switch(state_registry, state_slots, fs, code[:-1], lit, release, guard)
            elif class_id is None and trigger in ("autorun", "parallel"):
                code = _run_controller(graph, code[:-1], trigger == "autorun", project_condition, item_id_for)
            elif class_id is None and trigger == "interact":
                code = _run_controller(graph, code[:-1], False, project_condition, item_id_for,
                                       interact_area=graph["_interact_area"])
            bank = "B" if class_id is None else ("F" if trigger == "interact" else "D")
            if (bank == "F" and not recovered_object and definition.get("kind") == "npc"
                    and catalogue not in NOT_HUMAN and not (graph.get("native_placement") or {}).get("direction_fix")):
                # People turn to face Alundra when he talks to them (native 27 Face
                # player) unless the event menu's Direction fix is ticked.
                code = bytes((0x27,)) + code
            if recovered_object:
                # Use the already compiled authored bytes, including branch
                # conditions. Native controller performs the animation first.
                from native_object_controller import rebind_controller
                from native_lever_profile import CONTROLLER, CONTACT
                recovered = recovered_objects[graph['id']]
                state_id = recovered['state_id']
                if catalogue == 291:
                    from native_carryable_continuation import compile_jar
                    from event_vm_compatibility import sprite_callbacks
                    if any(template[10:16]) or sprite_callbacks(exported.data,map_id,catalogue)!=[('A',0),('C',23),('D',0),('E',2),('F',0)]:
                        raise ValueError('Jar continuation requires retained native C23/E2 without inherited instance hooks')
                    programs,profile=compile_jar(code[:-1])
                elif catalogue == 308:
                    from native_rotation_switch_profile import compile_rotation_switch
                    programs,profile = compile_rotation_switch(state_registry,recovered['request_id'],commands,leaf_emitter=leaf,initial_direction=(0,16,8,24)[template[5]&3])
                elif catalogue == 326:
                    from native_large_gate_profile import compile_gate
                    programs,profile = compile_gate(state_registry,recovered['open_switch_id'],commands,leaf_emitter=leaf)
                elif catalogue == 324:
                    from native_key_door_profile import compile_key_door
                    exported.data, failure_text = append_local_text(exported.data,map_id,"\\BIt's locked.")
                    programs,profile = compile_key_door(state_registry,state_id,
                        failure_text['dialogue_reference'],code[:-1])
                elif catalogue == 323:
                    from native_small_key_door_profile import compile_portable_small_key_door
                    exported.data, failure_text = append_local_text(exported.data,map_id,"\\BIt's locked.")
                    programs,profile = compile_portable_small_key_door(state_registry,state_id,
                        failure_text['dialogue_reference'],code[:-1])
                elif catalogue == 316:
                    from native_flame_pillar_profile import compile_passive_pillar
                    programs,profile=compile_passive_pillar()
                elif catalogue == 325:
                    from native_gate_profile import compile_gate
                    programs,profile = compile_gate(state_registry,recovered['open_switch_id'],commands,leaf_emitter=leaf)
                elif catalogue == 298:
                    from native_statue_profile import compile_statue
                    programs,profile = compile_statue(state_registry,state_id,
                        recovered['request_id'],x,y,template[9]//2,code[:-1])
                elif catalogue == 305:
                    bindings = {0x8001:state_id, 0x8002:recovered['request_id']}
                    programs = {}
                    _rel = graph.get('_release_commands', [])
                    _release = compile_logic(_rel, leaf, item_resolver=item_id_for, project_condition_emitter=project_condition) if _rel else b''
                    # offset 22: the lever goes back (off: Deactivate actions); 34: pulled (on: Activate actions)
                    # pulled: only the Activate actions the user placed (2026-10-23: the editor's own
                    # BD 02 "OK" sound here was removed; the donor lever controller has no sound)
                    programs['C'], profile = rebind_controller(CONTROLLER, bindings, state_registry,
                        insert_before={22:_release, 34:code[:-1]})
                    _contact, _ = rebind_controller(CONTACT, bindings, state_registry)
                    _contact = bytes.fromhex('bd3c00') + _contact   # the lever's click when hit (map 36 copies)
                    if not (graph.get('native_placement') or {}).get('can_deactivate'):   # pulled: it stays pulled
                        from event_logic_compile import _Assembler as _A2
                        _g2 = _A2(); _g2.data.extend(project_condition({'type': 'switch', 'switch_scope': 'project', 'switch_id': state_id, 'value': True}))
                        # hit again once pulled: the game's "Error" (sound 0x03) instead of nothing
                        _g2.branch(3, 'end'); _g2.data.extend(_contact[:-1]); _g2.data.append(0xFF)
                        _g2.label('end'); _g2.data.extend(bytes.fromhex('bd0300')); _g2.data.append(0xFF); _contact = _g2.finish()
                    programs['D'] = _contact
                elif catalogue == 314:
                    from native_small_rolling_rock_profile import compile_controller
                    if template[9]//2!=1:raise ValueError('Small rolling314 currently needs starting tile height1')
                    programs,profile = compile_controller(state_registry,graph['native_placement']['finish_tile'],commands,leaf_emitter=leaf,facing=graph['native_placement'].get('facing','down'))
                elif catalogue == 315:
                    from native_rolling_rock_profile import compile_platform
                    programs,profile = compile_platform(state_registry,commands,leaf_emitter=leaf)
                elif catalogue == 322:
                    from native_large_breakable_platform_profile import compile_platform
                    programs,profile = compile_platform(state_registry,commands,leaf_emitter=leaf)
                elif catalogue == 321:
                    from native_breakable_platform_profile import compile_platform
                    programs,profile = compile_platform(state_registry,commands,leaf_emitter=leaf)
                elif catalogue == 313:
                    from native_platform_shuttle_profile import compile_platform
                    programs,profile = compile_platform(state_registry,commands,leaf_emitter=leaf,
                        direction=(0,16,8,24)[template[5]&3])
                elif catalogue == 312:
                    from native_platform_lift_profile import compile_platform
                    programs,profile = compile_platform(state_registry,commands,leaf_emitter=leaf)
                elif catalogue == 307:
                    from native_ignition_switch_profile import compile_ignition_switch
                    programs,profile = compile_ignition_switch(state_registry,state_id,
                        recovered['request_id'],commands,leaf_emitter=leaf,off_request_id=recovered.get('off_request_id'),
                        allow_bomb=bool(graph.get('native_placement',{}).get('bomb_activation') or definition.get('data',{}).get('bomb_activation')),
                        release_commands=graph.get('_release_commands', []))
                elif catalogue == 364:
                    from native_pattern_plate_profile import compile_pattern_plate, symbol_templates
                    plate_templates = symbol_templates(record_cluster(exported.data, map_id)['entities'][:initial_entities],
                                                       actor_indices, group, definitions)
                    plate_changing = definition.get('source',{}).get('variant')=='pattern_cycle'
                    plate_symbol = definition.get('source',{}).get('plate_symbol', template[5]&3) if not plate_changing else template[5]&3
                    plate_start = int((graph.get('native_placement') or {}).get('start_symbol', 0) or 0) & 3 if plate_changing else plate_symbol
                    plate_flush = None
                    if (graph.get('native_placement') or {}).get('plate_flush', True) is not False:
                        # Flush With Floor: drawn in the floor squares, every frame of the game's plate
                        # animations on a spare 2x2 (heal_tile.install_plate_pictures)
                        from heal_tile import spare_blocks, plate_frames
                        from native_pattern_plate_profile import flush_animations
                        from area_map import grid as _grid
                        from heal_tile import _View as _TileView
                        _px, _py = graph['region'][:2]
                        _w, _h, _cells = _grid(_TileView(exported.data), map_id)
                        if _py < 1 or _px + 1 >= _w:
                            raise ValueError(f"{graph['name']}: a Flush With Floor plate covers its square, the one to its right and the two above")
                        _anims = {name: plate_frames(_TileView(exported.data), *key)
                                  for name, key in flush_animations(plate_symbol, plate_changing).items()}
                        _pictures = list(dict.fromkeys(f for seq in _anims.values() for f, _ in seq))   # (animation, direction, frame) per picture
                        _taken = [b for (_t, _b, _s) in plate_pictures.get(map_id, []) for b in _b] + \
                                 [s for (_m, _xy, s) in floor_switch_lit if _m == map_id]
                        _spots = spare_blocks(exported.data, map_id, len(_pictures), _taken)
                        if len(_spots) < len(_pictures):
                            raise ValueError(f"{graph['name']}: map {map_id} has no empty dark space left for the Flush With Floor plate pictures "
                                             f"({len(_pictures)} spare 2x2 squares needed, {len(_spots)} found)")
                        _at = dict(zip(_pictures, _spots))
                        _first = _anims['cycle'][len(_anims['cycle']) // 4 * plate_start] if plate_changing else _anims['unlit'][0]
                        plate_flush = {'tiles': (_px, _py - 1), 'height': _cells[_py * _w + _px]['values'][3],
                                       'frames': {name: [(_at[f], n) for f, n in seq] for name, seq in _anims.items()}}
                        plate_pictures.setdefault(map_id, []).append(((_px, _py - 1), {xy: f for f, xy in _at.items()}, _first[0]))
                    programs,profile = compile_pattern_plate(state_registry,state_id,commands,leaf_emitter=leaf,
                        symbol=plate_symbol,templates=plate_templates,changing=plate_changing,start=plate_start,
                        fail_stops_others=(graph.get('native_placement') or {}).get('fail_stops_others',True) is not False,
                        flush=plate_flush, keep_state=bool((graph.get('native_placement') or {}).get('keep_state')))
                    # the record faces the symbol it shows first: a static plate its own,
                    # a changing plate the one it starts on (its animation is turned to start there)
                    template = bytes(template[:5]) + bytes(((template[5] & 0xFC) | plate_start,)) + bytes(template[6:])
                    if plate_changing and plate_start and not plate_flush:
                        plate_rotations.setdefault(map_id, set()).add(plate_start)
                elif catalogue == 398:
                    from native_lamp_switch_profile import compile_lamp_switch
                    programs,profile = compile_lamp_switch(state_registry,state_id,recovered['request_id'],commands,leaf_emitter=leaf,
                        sword_only=bool(graph.get('native_placement',{}).get('sword_only') or definition.get('data',{}).get('sword_only')),
                        can_deactivate=bool(graph.get('native_placement',{}).get('can_deactivate')), release_commands=graph.get('_release_commands', []))
                elif catalogue == 306:
                    from native_wall_switch_profile import compile_wall_switch
                    programs,profile = compile_wall_switch(state_registry,state_id,
                        recovered['request_id'],commands,leaf_emitter=leaf,
                        can_deactivate=bool(graph.get('native_placement',{}).get('can_deactivate')), release_commands=graph.get('_release_commands', []))
                else:
                    from native_floor_switch_profile import compile_floor_switch
                    pressured = bool(definition.get('data', {}).get('while_pressured') or graph.get('native_placement', {}).get('while_pressured'))
                    programs,profile = compile_floor_switch(state_registry,state_id,commands,leaf_emitter=leaf,
                        while_pressured=pressured,release_commands=graph.get('_release_commands', []),
                        can_deactivate=bool(graph.get('native_placement',{}).get('can_deactivate')),
                        ignore_spring_bean=bool(graph.get('native_placement',{}).get('ignore_spring_bean')))
                if (graph.get('native_placement') or {}).get('active_by_default') and catalogue in (305, 306) and 'C' in programs:
                    # Active by default: a lever / wall switch already switched shows its on position
                    from event_logic_compile import _Assembler as _A
                    _pre = _A(); _pre.data.extend(project_condition({'type': 'switch', 'switch_scope': 'project', 'switch_id': state_id, 'value': True}))
                    _pre.branch(4, 'rest'); _pre.data.extend(bytes((0x1A, 1))); _pre.label('rest')
                    programs = dict(programs, C=_pre.finish() + programs['C'])
                _placement = graph.get('native_placement') or {}
                if (catalogue in (301, 305, 306, 307, 398) and state_id is not None and not _placement.get('keep_state')
                        and not (catalogue == 301 and pressured)):
                    # The switch's own private state goes back to its start (Active By Default)
                    # each time you enter the room, unless Keep State Upon Leaving Room is ticked.
                    # A room flag (cleared by every map load) makes it happen once per visit.
                    if len(room_guards) >= 32:
                        raise ValueError(f'Map {map_id}: at most 32 switches reset on entering the room')
                    _guard = 0x87A0 + len(room_guards); room_guards.append(graph['id'])
                    _set = compile_project_command({'type': 'set_switch', 'switch_scope': 'project', 'switch_id': state_id,
                                                    'value': bool(_placement.get('active_by_default'))}, state_registry, state_slots)
                    _body = _set + struct.pack('<BH', 0x05, _guard)
                    _reset = struct.pack('<BHh', 0x30, _guard, 5 + len(_body)) + _body
                    _bank = 'A' if catalogue == 301 and 'A' in programs else 'C'
                    programs = dict(programs, **{_bank: _reset + programs[_bank]})
                row = bytearray(template); row[10:16] = bytes(6); allocations = {}
                for native_bank, native_code in programs.items():
                    exported.data, allocation = append_native_process(exported.data, map_id, native_bank, native_code)
                    allocations[native_bank] = allocation
                    row[10+'ABCDEF'.index(native_bank)] = allocation['hook_value']
                from event_vm_compatibility import sprite_callbacks
                pending.append((graph,bytes(row),{'map_id':map_id,'bank':None,
                    'opcodes':sorted({op for raw in programs.values() for op in _generated_opcodes(raw)}),
                    'recovered_object':{**recovered,'controller':profile,'allocations':allocations,
                        'activation_after_native_animation':catalogue not in (314,315,316,323,324),
                        'activation_after_native_movement':catalogue in (314,315),
                        'activation_after_key_consumption':catalogue in (323,324),
                        'memory_card_persistent':False,'gameplay_verified':False},
                    'native_passive':passive,'sprite_callbacks':sprite_callbacks(exported.data,map_id,catalogue)}))
                continue
            route_load_report = None
            book_load_report = None
            if npc_continuation:
                from native_npc_continuation import compile_fixed_npc_handoff, idle_tick_process
                code = compile_fixed_npc_handoff(code)
                if book_interaction:
                    from native_book_interaction import button_load_process
                    book_load_code=button_load_process()
                    exported.data,book_load_report=append_native_process(exported.data,map_id,'A',book_load_code)
                    row=bytearray(template);row[10]=book_load_report['hook_value'];template=bytes(row)
                if npc_route_continuation:
                    from native_actor_route_profile import fixed_route_load_process
                    load_code = fixed_route_load_process(catalogue)
                    if load_code is not None:
                        exported.data, route_load_report = append_native_process(exported.data, map_id, "A", load_code)
                        row = bytearray(template)
                        row[10] = route_load_report["hook_value"]
                        template = bytes(row)
                exported.data, tick_report = append_native_process(exported.data, map_id, "C", idle_tick_process())
                row = bytearray(template)
                row[12] = tick_report["hook_value"]
                template = bytes(row)
            sign_report = None
            if stool_activation and template is not None:   # Stool (Pushable): pushes run the Activate actions
                from native_pushable_stool import install as _stool_install, switch_templates as _stool_switches2
                _counts = getattr(exported, 'stool_counts', None)
                if _counts is None: _counts = {}; exported.stool_counts = _counts
                _sid = stool_states[graph['id']]
                _test = project_condition({'type': 'switch', 'switch_scope': 'project', 'switch_id': _sid, 'value': True})
                _set = lambda v: compile_project_command({'type': 'set_switch', 'switch_scope': 'project', 'switch_id': _sid, 'value': v}, state_registry, state_slots)
                _rel = graph.get('_release_commands', [])
                _off = compile_logic(_rel, leaf, item_resolver=item_id_for, continuation_proven=True, project_condition_emitter=project_condition) if _rel else b''
                exported.data, _hooks, _stool_report = _stool_install(exported.data, map_id, bytes(template[10:16]), graph, _counts,
                    on=code[:-1], off=_off, state=(_test, _set(True), _set(False)), append_f=False,
                    switches=_stool_switches2(exported.data, map_id, group, definitions, actor_indices))
                row = bytearray(template); row[10:16] = _hooks; template = bytes(row)
                code = _stool_report.pop('F_code'); bank = 'F'
                exported.stool_reports = getattr(exported, 'stool_reports', []) + [dict(_stool_report, event=graph['id'])]
            if sign_interaction and template is not None:
                if len(sign_guards) >= 31:
                    raise ValueError(f'Map {map_id}: at most 31 signboards with actions')
                _flag = struct.pack('<H', 0x87C0 + len(sign_guards)); sign_guards.append(graph['id'])
                _c = bytes((0x36,)) + _flag + bytes((0x06,)) + _flag + code[:-1] + bytes((0x49, 0xFF))
                exported.data, sign_report = append_native_process(exported.data, map_id, 'C', _c)
                row = bytearray(template); row[10:16] = bytes(6); row[12] = sign_report['hook_value']; template = bytes(row)
                code = bytes((0x05,)) + _flag + bytes((0xFF,)); bank = 'F'
            exported.data, report = append_native_process(exported.data, map_id, bank, code)
            if sign_report:
                report['signboard'] = {'room_flag': hex(0x87C0 + len(sign_guards) - 1), 'C': sign_report,
                                       'pattern': 'F sets the flag; C waits, clears it, runs the actions (map 27 / 62 signs)'}
            report["opcodes"] = sorted(set(_generated_opcodes(code) + ([0x1A,0xFF] if initial_pose_report else [])))
            if book_load_report:
                report['opcodes']=sorted(set(report['opcodes']+_generated_opcodes(book_load_code)))
            if book_interaction:
                report['book_interaction']={'catalogue':303,'native_callbacks_retained':True,
                    'retained_F_to_C':True,'native_dialogue_wait':True,'native_opcode_extension':False,
                    'button_load_process':book_load_report,'instance_flags_OR':'00008000',
                    'manual_F_restore':False,
                    'evidence':['data/2026-10-06-Book-button-repeat-production-runtime.json',
                                'data/2026-10-06-Book-303-editor-build-ui-audit-v2.json',
                                'data/2026-10-06-Book-actual-editor-module-runtime.json'],
                    'scope':'New hook-free Book only; unconditional Interact text and money',
                    'instance_gameplay_verified':False,'stock_events_unchanged':True}
            if route_load_report:
                report["opcodes"] = sorted(set(report["opcodes"] + _generated_opcodes(load_code)))
            if initial_pose_report:
                report["initial_pose"] = initial_pose_report
            if gift_commands:
                report["item_grants"] = {"opcode": "82", "native_item_id": 36,
                    "quantity_per_command": 1, "condition": "1 only when native quantity increases; 0 at capacity",
                    "stock_cap": 9, "cap_address": "800BBFBE", "automatic_obtained_message": False,
                    "gameplay_verified": False, "limits": ["Herb36 only", "Native cap applies", "No pickup or progressive normalization"]}
            if npc_continuation:
                report["npc_continuation"] = {"tick_process": tick_report,
                    "handoff_opcode": "66", "opcode_relative_target": 4,
                    "fixed_npc_only": True, "gameplay_verified": False,
                    "limits": ["New NPC instance uses authored C tick instead of native autonomous AI", "Physical touch may select D and interrupt continuation; runtime verification required"]}
            if npc_route_continuation:
                report["retained_route"] = {"catalogue_index": catalogue,
                    "handoff_opcode": "66", "idle_tick": "FF",
                    "blocked_behavior": "wait", "speed_percent": 100,
                    "evidence": "data/2026-10-06-retained-actor-route-runtime.json" if catalogue == 260 else "data/2026-10-06-additional-npc-route-runtime.json",
                    "cold_boot_profile_verified": True,
                    "instance_gameplay_verified": False,
                    "limits": ["Explicitly tested new fixed NPC class only", "Animation1 walking/animation0 idle at native speed", "One self route on one unconditional Interact page", "Default autonomous routes and per-instance speed remain guarded"]}
                if catalogue == 289:
                    report["retained_route"]["load_process"] = route_load_report
                    report["retained_route"]["instance_collidable_flag"] = "80, native62 self selector80; stock sprite header unchanged"
            if presence:
                exported.data, watcher = _presence_watcher(exported.data, map_id, presence, template,
                                                           actor_indices[graph["id"]], project_condition, w, h,
                                                           _once_per_visit(graph, definition, state_registry, state_slots, project_condition), item_resolver=item_id_for)
                report["presence_controller"] = watcher
                report["opcodes"] = sorted(set(report["opcodes"] + watcher["opcodes"]))
            if any(command.get('type')=='move_actor' for command in all_commands):
                report['movement_limits']=['Self fixed tile route only',
                    'Collision, overshoot and donor AI competition require gameplay validation']
            if template is not None:
                from event_vm_compatibility import sprite_callbacks
                builtins.extend(sprite_callbacks(exported.data, map_id, catalogue))
            report["sprite_callbacks"] = sorted(set(builtins))
            if cleared_npc_hooks:
                report["npc_donor_map_hooks_cleared"] = cleared_npc_hooks
            if behaviour_report is not None:
                report["behaviour_transplant"] = behaviour_report
            if synthesized:
                report["synthesized_record"] = {"reason": "no map places this class", "hooks": "none (class AI only)"}
            if template is not None and catalogue in palette_forks:
                report["palette_fork"] = palette_forks[catalogue]
            if graph["id"] in imported_placements:
                report["imported_sprite"] = imported_placements[graph["id"]][0]
            if len(graph["pages"]) > 1 or page.get("conditions"):
                report["page_dispatch"] = {"pages": len(graph["pages"]), "priority": "highest matching page",
                    "appearance_changes": False, "evaluated_on": trigger}
            if graph.get('_act_as_npc') and template is not None:
                # Act As NPC: the character stands still and only talks (its Interact actions);
                # its own start-up, AI, touch and death programs are replaced by empty ones.
                template = bytearray(template)
                for bank, code_bytes in (('A', b'\xff'), ('C', b'\x00\x49\xff'), ('D', b'\xff'), ('E', b'\xff')):
                    if template[10 + 'ABCDEF'.index(bank)]:
                        continue   # already the NPC talk machinery's own program
                    exported.data, allocation = append_native_process(exported.data, map_id, bank, code_bytes)
                    template[10 + 'ABCDEF'.index(bank)] = allocation['hook_value']
                template = bytes(template)
                report['act_as_npc'] = {'hooks': bytes(template[10:16]).hex(), 'talk': 'F (Interact actions)', 'gameplay_verified': False}
            pending.append((graph, template, report))
        for _g, _template, _report in pending:
            _def = definitions.get((_g.get('pages') or [{}])[0].get('class_id', _g.get('class_id')), {})
            if (_template is not None and _def.get('kind') == 'boss' and not _g.get('_act_as_npc') and _g['id'] in actor_indices
                    and (_g.get('native_placement') or {}).get('play_victory', True) is not False):
                _home = victory_homes.get(_g['id'])
                if type(_home) is not int or _home >= 483:
                    _src = _def.get('source', {})
                    _home = (_src.get('fixed_donor') or [None])[0] or (_src.get('observed_maps') or [None])[0]
                victory_bosses.append((actor_indices[_g['id']], _home, _def.get('name') or 'the boss'))
                _report['play_victory'] = {'home_map': _home}
        for _g, _template, _report in pending:
            # Track Player: while the player is 3+ tiles away, keep the character turned toward
            # him, so its own wandering walks it his way and its sight check finds him (Sara)
            _def = definitions.get((_g.get('pages') or [{}])[0].get('class_id', _g.get('class_id')), {})
            if _template is None or _def.get('kind') not in ('enemy', 'boss') or _g.get('_act_as_npc') or _g['id'] not in actor_indices:
                continue
            _default = _def.get('source', {}).get('catalogue_index') == 452 and _def.get('kind') == 'boss'
            if not (_g.get('native_placement') or {}).get('track_player', _default):
                continue
            from player_tracking import tracker
            if actor_indices[_g['id']] >= 0x80:
                raise ValueError(f"{_g.get('name')}: Track Player needs it among the first 128 characters of the map")
            _code = tracker(actor_indices[_g['id']])
            exported.data, _tw = append_native_process(exported.data, map_id, 'B', _code)
            tracking_hooks.append(_tw['hook_value'])
            _report['track_player'] = {'watcher_hook': _tw['hook_value']}
            _report['opcodes'] = sorted(set(_report.get('opcodes', []) + _generated_opcodes(_code)))
        from native_boss_points import START_FLAGS as _START_FLAGS, start_program as _start_program
        _flags = []
        for _g, _template, _report in pending:
            _def = definitions.get((_g.get('pages') or [{}])[0].get('class_id', _g.get('class_id')), {})
            _cls = _def.get('source', {}).get('catalogue_index')
            if _template is not None and _def.get('kind') == 'boss' and not _g.get('_act_as_npc') and _cls in _START_FLAGS:
                _flags += [f for f in _START_FLAGS[_cls] if f not in _flags]
                _report['start_flags'] = [hex(f) for f in _START_FLAGS[_cls]]
        if _flags:
            # the room flags these bosses wait for (their home room's intro set them): set as the map starts
            exported.data, _sw = append_native_process(exported.data, map_id, 'B', _start_program(_flags))
            tracking_hooks.append(_sw['hook_value'])
        if victory_bosses:
            # Play Victory (bosses): the game's own boss-room routine, once every boss here is beaten
            from boss_victory import home_victory, markup, watcher as victory_watcher
            _bosses, _text = [], None
            for _index, _home, _name in victory_bosses:
                if _index >= 0x80:
                    raise ValueError(f'{_name}: Play Victory needs the boss among the first 128 characters of the map')
                _t, _flag = home_victory(_home, getattr(session, 'original', None))
                _bosses.append((_index, _flag)); _text = _text or _t or f'Defeated {_name}.'
            exported.data, _vt = append_local_text(exported.data, map_id, markup(_text), taken=victory_text_slots)
            exported.data, _vw = append_native_process(exported.data, map_id, 'B', victory_watcher(_bosses, _vt['dialogue_reference'], after=b''.join(victory_after)))
            victory_hook = _vw['hook_value']
        # All script allocations precede the final record relocation so bytecode
        # capture does not include a previously appended record-only cluster.
        if not pending:
            continue
        # Flush step-on switches: their own sprite (the switch cut to its lit top,
        # level with the floor) goes into a free slot of this map; the placed
        # records are the step-on switch's, moved to that slot below.
        flush_slot = None
        flush_ids = {graph['id'] for graph, _, _ in pending
                     if definitions.get((graph.get('pages') or [{}])[0].get('class_id', graph.get('class_id')), {}).get('source', {}).get('variant') == 'flush_top'}
        if flush_ids:
            from flush_switch import install_flush_switch
            taken = set(local_slots) | {t[6] for _, t, _ in pending if t is not None and t[5] & 0x80}
            exported.data, flush_slot = install_flush_switch(exported.data, map_id, keep=taken)
            exported.data = _owned(exported.data)
        # Placed pattern plates with Flush With Floor (on unless unticked): a hidden, not solid copy of the plate
        # sprite in a free slot (flush_switch.hide_plate) runs the plate; its picture is in the floor squares.
        # Unticked plates and the game's own keep the original sprite.
        floor_hidden_slot = None
        floor_hidden_ids = {graph['id'] for graph, _, _ in pending if graph.get('_floor_hidden')}
        if floor_hidden_ids:   # Step On Switch (Floor): the real switch, not drawn (its picture is in the floor)
            from flush_switch import install_hidden_switch
            taken = set(local_slots) | {t[6] for _, t, _ in pending if t is not None and t[5] & 0x80} | {flush_slot}
            exported.data, floor_hidden_slot = install_hidden_switch(exported.data, map_id, keep=taken)
            exported.data = _owned(exported.data)
        plate_flush_slot = None
        plate_flush_ids = {graph['id'] for graph, t, _ in pending
                           if t is not None and t[5] & 0x80 and t[6] == 364 - 256
                           and (graph.get('native_placement') or {}).get('plate_flush', True) is not False}
        if plate_flush_ids:
            from flush_switch import install_flush_plate
            taken = set(local_slots) | {t[6] for _, t, _ in pending if t is not None and t[5] & 0x80} | {flush_slot, floor_hidden_slot}
            exported.data, plate_flush_slot = install_flush_plate(exported.data, map_id, keep=taken)
            exported.data = _owned(exported.data)
        cluster = record_cluster(exported.data, map_id)
        entities, events = cluster["entities"] + gift_templates, cluster["events"]
        for graph, template, report in pending:
            x, y, rw, rh = graph["region"]
            if template is None:
                events.append(bytes([x, y, x + rw - 1, y + rh - 1, report["hook_value"], 0, 0, 0]))
            else:
                row = bytearray(template)
                if (graph.get('native_placement') or {}).get('spawn_of'):row[5] &= ~0x40   # created only when its owner spawns it
                if graph['id'] in flush_ids:
                    if row[6] + (256 if row[5] & 0x80 else 0) != 301:
                        raise ValueError(f"{graph['name']}: flush switch record is not a step-on switch")
                    row[6] = flush_slot
                if graph['id'] in plate_flush_ids:
                    row[6] = plate_flush_slot
                if graph['id'] in floor_hidden_ids:
                    if row[6] + (256 if row[5] & 0x80 else 0) != 301:
                        raise ValueError(f"{graph['name']}: floor switch record is not a step-on switch")
                    row[6] = floor_hidden_slot
                placement_offsets = graph.get("native_placement", {})
                if False and placement_offsets.get('lower_one'):   # Sink Into Floor removed
                    if row[9] < 2:
                        raise ValueError(f"{graph['name']}: Sink Into Floor needs the object to stand at height 1 or more")
                    row[9] -= 2   # one height = two half-tile z units
                wide = 0
                try:   # a wide (2-tile) sprite starts at the left of its tile, as the editor shows it
                    from project_event_preview import event_world_image, wide_shift
                    page_class = (graph.get('pages') or [{}])[0].get('class_id', graph.get('class_id'))
                    if page_class in definitions:
                        wide = wide_shift(event_world_image(session, definitions[page_class], map_id, placement_offsets.get('facing')))
                except Exception:
                    wide = 0
                for index, key in ((7, "offset_x"), (8, "offset_y")):   # half-tile steps
                    shift = placement_offsets.get(key, 0) + (wide if index == 7 else 0)
                    if shift:
                        if type(shift) is not int or not 0 <= row[index] + shift <= 255:
                            raise ValueError(f"{graph['name']}: Offset {'X' if index == 7 else 'Y'} moves it off the map")
                        row[index] += shift
                if report["bank"] is not None and "hook_value" in report:
                    # Position routes already wrote their hook into the template.
                    row[10 + "ABCDEF".index(report["bank"])] = report["hook_value"]
                # Deliberately full-map activation, so moving the donor beyond
                # its source rectangle does not silently deactivate the copy.
                row[:4] = bytes([0, 0, w - 1, h - 1])
                entities.append(bytes(row))
            if report.get("play_victory") and victory_hook is not None:
                report["play_victory"]["watcher_hook"] = victory_hook
            if report.get("presence_controller"):
                watcher = report["presence_controller"]
                events.append(bytes(watcher["region"] + [watcher["hook_value"], 0, 0, 0]))
                if len(entities) - 1 != watcher["template_index"]:
                    raise ValueError("Conditional controller identity differs from its final actor InitData index")
            report["event_id"] = graph.get("_page_of", graph["id"])
            if graph.get("_page_of"):report["page"] = graph["id"].rsplit("#page", 1)[1]
            reports.append(report)
        boss_templates = behaviour_cache.get(("templates", map_id)) or []
        if boss_templates:
            if len(entities) != behaviour_cache[("template_base", map_id)]:
                raise ValueError("Boss spawn templates: placed characters differ from their reserved indices")
            entities.extend(boss_templates)   # the spawn templates placed bosses brought, at the indices their programs use
        if victory_hook is not None:
            events.append(bytes([0, 0, w - 1, h - 1, victory_hook, 0, 0, 0]))   # Play Victory watcher, whole map
        for _hook in tracking_hooks:
            events.append(bytes([0, 0, w - 1, h - 1, _hook, 0, 0, 0]))   # Track Player watchers, whole map
        exported.data, _ = append_record_cluster(exported.data, map_id, entities=entities, map_events=events)
    _nea.HEAL_EFFECTS = None
    _nea.SHOW_EFFECTS = None
    for m, directions in plate_rotations.items():
        from native_pattern_plate_profile import rotate_cycle
        stock = record_cluster(session.data, m)['entities'] if m < 483 else []
        if any(raw[5] & 0x80 and raw[6] == 364 - 256 and (raw[5] & 3) in directions for raw in stock):
            raise ValueError(f"Map {m} has the game's own changing pattern plates facing that way; choose Star as the starting symbol here")
        exported.data = _owned(rotate_cycle(exported.data, m, directions))
    if panel_graphs:
        from heal_tile import install_plates, panel_tiles, add_warp_data
        by_map = {}
        for g in panel_graphs:by_map.setdefault(g['map_id'], []).append(g)
        for m, rows in by_map.items():
            tiles = [t for g in rows for t in panel_tiles(*g['region'][:2])]
            exported.data = _owned(install_plates(exported.data, m, tiles))
            for g in rows:
                x, y = g['region'][:2]
                index = add_warp_data(exported.data, m, (x, y - 1, x + 1, y), g['native_placement']['warp_to'])
                reports.append({'event_id': g['id'], 'map_id': m, 'name': g.get('name'), 'warp_panel': True,
                                'warp_index': index, 'warp_to': g['native_placement']['warp_to'], 'gameplay_verified': False})
    if portal_graphs:
        from save_portal import install as _install_portals
        _data, _reports = _install_portals(exported.data, portal_graphs)
        exported.data = _owned(_data)
        reports.extend(_reports)
    if floor_switch_tiles:
        from heal_tile import install_plates
        by_map = {}
        for m, x, y in floor_switch_tiles:by_map.setdefault(m, []).append((x, y, 'switch'))
        if floor_switch_lit:   # the lit copies first, from the squares as they are under the switch
            from heal_tile import install_lit_copies
            lit_by_map = {}
            for m, xy, spot in floor_switch_lit:lit_by_map.setdefault(m, []).append((xy, spot))
            for m, pairs in lit_by_map.items():
                exported.data = install_lit_copies(exported.data, m, pairs)
        if floor_switch_unlit:   # unlit copies (put back on Deactivate), from the squares as they are
            from heal_tile import install_square_copies
            unlit_by_map = {}
            for m, xy, spot in floor_switch_unlit:unlit_by_map.setdefault(m, []).append((xy, spot))
            for m, pairs in unlit_by_map.items():
                exported.data = install_square_copies(exported.data, m, pairs, 'switch')
        for m, tiles in by_map.items():
            exported.data = install_plates(exported.data, m, tiles)
    for m, plates in plate_pictures.items():
        from heal_tile import install_plate_pictures
        exported.data = _owned(install_plate_pictures(exported.data, m, plates))
    if sage_graphs:
        from sage_npc import install as _install_sages
        exported.data, sage_reports = _install_sages(exported.data, sage_graphs)
        reports.extend(sage_reports)
    if heal_graphs:
        from heal_tile import install_tiles
        exported.data, heal_reports = install_tiles(exported.data, heal_graphs)
        reports.extend(heal_reports)
    if orb_graphs:
        from block_switch import install_switches
        _sw = lambda sid, v, cond: (compile_project_condition if cond else compile_project_command)(
            {'type': 'switch' if cond else 'set_switch', 'switch_scope': 'project', 'switch_id': sid, 'value': v}, state_registry, state_slots)
        keep = {gid: (_sw(sid, True, True), _sw(sid, True, False), _sw(sid, False, False)) for gid, sid in orb_states.items()}
        exported.data, orb_reports = install_switches(exported.data, orb_graphs, keep)
        reports.extend(orb_reports)
    exported.native_event_export_report = reports
    release_session_data(exported)   # hand back a plain session with plain data
    return exported
