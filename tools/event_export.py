"""Best-effort game export for project-authored event pages.

Event features are attempted independently. An unsupported page must not stop
the rest of a disc build or erase the saved authoring project: the exporter
falls back to the safest useful placement it can compile and records every
setting it could not install.
"""
import struct


class EventExportError(ValueError):
    """A saved authoring project contains events not emitted to the game."""


def generated_sprite_callbacks(session, exported=None):
    """Concrete native class/pickup callback selectors from compilation."""
    exported = prepare_native_event_export(session) if exported is None else exported
    return sorted({tuple(row) for report in getattr(exported, 'native_event_export_report', [])
                   for row in report.get('sprite_callbacks', [])})


def project_event_export_issues(session, event_ids=None):
    """Return an actionable issue for each authored event; do not mutate data.

    A metadata claim such as ``compiled=True`` is deliberately insufficient.
    Compilation verifies emitted records against the current data.
    """
    database = getattr(session, "content_database", None)
    if database is None:
        return []
    if not isinstance(database, dict):
        raise EventExportError("The project database is invalid; save a separate copy and reopen it before building.")
    graphs = database.get("event_graphs", [])
    if not isinstance(graphs, list):
        raise EventExportError("The project's event list is invalid; it cannot be exported to the game.")
    issues = []
    selected = None if event_ids is None else set(event_ids)
    for graph in graphs:
        if not isinstance(graph, dict):
            raise EventExportError("The project contains an invalid event record; it cannot be exported to the game.")
        if selected is not None and graph.get("id") not in selected:
            continue
        # Even an empty Contents list needs placement/trigger validation.
        if graph.get("native_binding") is not None:
            from event_native_compile import compile_bound_event
            try:
                compile_bound_event(session, graph)
                continue
            except (ValueError, KeyError, IndexError, TypeError) as error:
                reason = str(error)
        else:
            from new_event_compile import compile_new_events
            try:
                # Speaker references to other authored actors need their native
                # placement context even when checking only the selected event.
                by_id = {row.get("id"): row for row in graphs if isinstance(row, dict)}
                needed = {graph.get("id")}
                pending = [graph]
                def commands(rows):
                    for row in rows:
                        yield row
                        if row.get("type") == "if":
                            yield from commands(row.get("then", []))
                            yield from commands(row.get("else", []))
                        elif row.get("type") == "repeat":
                            yield from commands(row.get("commands", []))
                # a pattern plate needs the symbol objects on its map (its controller tests them)
                defs = {d.get("id"): d for d in database.get("definitions", []) if isinstance(d, dict)}
                def catalogue_of(row):
                    cid = (row.get("pages") or [{}])[0].get("class_id", row.get("class_id"))
                    return defs.get(cid, {}).get("source", {}).get("catalogue_index")
                if catalogue_of(graph) == 364:
                    for other in graphs:
                        if isinstance(other, dict) and other.get("map_id") == graph.get("map_id") and catalogue_of(other) in (363, 367, 368, 369):
                            needed.add(other.get("id"))
                while pending:
                    current = pending.pop()
                    for page in current.get("pages", []):
                        command_lists=[page.get("commands", [])]+[handler.get('commands',[]) for handler in page.get('trigger_actions',[])]
                        for rows in command_lists:
                            for command in commands(rows):
                                # events a command points at (Activate / Deactivate Switch,
                                # Show / Hide Event) are checked together with it, as in a build
                                if command.get("type") in ("deactivate_switch", "set_event_active"):
                                    target = by_id.get(command.get("event_id"))
                                    if target is not None and target.get("id") not in needed and target.get("map_id") == graph.get("map_id"):
                                        needed.add(target["id"]); pending.append(target)
                                dependency = by_id.get(command.get("speaker"))
                                if dependency is not None and dependency.get("id") not in needed:
                                    if dependency.get("map_id") != graph.get("map_id") or dependency.get("native_binding"):
                                        raise ValueError("Dialogue speaker must be a newly placed actor on this map")
                                    needed.add(dependency["id"]); pending.append(dependency)
                compile_new_events(session, [row for row in graphs if isinstance(row, dict) and row.get("id") in needed])
                continue
            except (ValueError, KeyError, IndexError, TypeError) as error:
                reason = str(error)
        issues.append({
            "event_id": graph.get("id", "unknown"),
            "name": graph.get("name", "Unnamed event"),
            "map_id": graph.get("map_id", "unknown"),
            "reason": reason,
        })
    return issues


def require_native_event_export(session):
    """Strict validation helper for tests and diagnostics, not used by Build game."""
    issues = project_event_export_issues(session)
    if issues:
        labels = [f"{str(row['name'])[:100]} ({row['event_id']}, map {row['map_id']}): {row['reason']}"
                  for row in issues[:5]]
        remaining = len(issues) - len(labels)
        if remaining:labels.append(f"and {remaining} more")
        raise EventExportError("Authored event validation found settings that need a compiler update: " + "; ".join(labels))
    return []


def _event_without_custom_actions(graph, *, keep_actor=True):
    """Return a conservative placement fallback while retaining authored data."""
    from copy import deepcopy
    result = deepcopy(graph)
    if not keep_actor:
        result["class_id"] = None
        result["native_placement"] = {}
    result["trigger"] = "interact" if keep_actor and result.get("class_id") else "touch"
    for page in result.get("pages", []):
        if not keep_actor:
            page["class_id"] = None
        page["trigger"] = result["trigger"]
        page["conditions"] = []
        page["commands"] = []
        page.pop("default_move_route", None)
        page.pop("idle_animation_enabled", None)
        page["trigger_actions"] = [{"trigger": result["trigger"], "commands": [],
                                    "hit_sources": [], "destroy_after": False}]
    return result


def _with_chest_item(graph, item):
    from copy import deepcopy
    result = deepcopy(graph)
    for page in result.get("pages", []):
        page.setdefault("contained_item_class_id", item)
        if not page.get("contained_item_class_id"):
            page["contained_item_class_id"] = item
    return result


def _default_chest_item(exported, graph):
    """First inventory item, for a native Chest whose contents were never chosen."""
    database = getattr(exported, "content_database", None) or {}
    definitions = {row.get("id"): row for row in database.get("definitions", []) if isinstance(row, dict)}
    for page in graph.get("pages", []):
        class_id = page.get("class_id", graph.get("class_id"))
        row = definitions.get(class_id) or {}
        if row.get("kind") == "object" and row.get("source", {}).get("catalogue_index") == 30:
            if not page.get("contained_item_class_id") and not row.get("data", {}).get("contained_item_class_id"):
                return next((key for key, item in definitions.items() if item.get("kind") == "item"), None)
    return None


def _compile_new_best_effort(exported, graph):
    """Try the exact page, then less destructive fallbacks for this event only."""
    from copy import copy, deepcopy
    from new_event_compile import compile_new_events

    attempts = [(deepcopy(graph), [])]
    no_route = deepcopy(graph)
    removed = []
    for page in no_route.get("pages", []):
        if page.pop("default_move_route", None) is not None:
            removed.append("default movement route")
    if removed:
        attempts.append((no_route, removed.copy()))
    # Keep the page conditions (an actor shown only while its switch is on
    # must not appear just because one of its actions is not exportable yet).
    keep_conditions = deepcopy(graph)
    for page in keep_conditions.get("pages", []):
        page["commands"] = []
        page.pop("default_move_route", None)
        for handler in page.get("trigger_actions", []):
            handler["commands"] = []
    attempts.append((keep_conditions, ["custom actions/movement (conditions kept)"]))
    placed = _event_without_custom_actions(graph, keep_actor=True)
    attempts.append((placed, ["custom conditions/actions/movement" ]))
    # A chest placed without contents still appears: it gets a default item.
    item = _default_chest_item(exported, graph)
    if item is not None:
        attempts.insert(1, (_with_chest_item(graph, item), ["chest contents (default item used)"]))
        attempts.append((_with_chest_item(placed, item), ["custom conditions/actions/movement", "chest contents (default item used)"]))
    region_only = _event_without_custom_actions(graph, keep_actor=False)
    attempts.append((region_only, ["graphic and custom conditions/actions/movement"]))

    last_error = "Event could not be compiled"
    for candidate, omitted in attempts:
        trial = copy(exported)
        trial.data = bytearray(exported.data)
        try:
            compiled = compile_new_events(trial, [candidate])
        except Exception as error:
            last_error = str(error)
            continue
        reports = list(getattr(compiled, "native_event_export_report", []))
        for report in reports:
            if omitted:
                report["export_fallback"] = {"omitted_settings": omitted,
                                             "reason": last_error}
        previous = list(getattr(exported, "native_event_export_report", []))
        compiled.native_event_export_report = previous + reports
        skipped = list(getattr(exported, "native_event_export_skipped", []))
        if omitted:
            skipped.append({"event_id": graph.get("id"), "name": graph.get("name"),
                            "map_id": graph.get("map_id"), "reason": last_error,
                            "omitted_settings": omitted, "placement_exported": True})
        compiled.native_event_export_skipped = skipped
        ids = set(getattr(exported, "native_event_export_ids", set()))
        ids.update(row.get("event_id") for row in reports if row.get("event_id"))
        compiled.native_event_export_ids = ids
        return compiled
    skipped = list(getattr(exported, "native_event_export_skipped", []))
    skipped.append({"event_id": graph.get("id"), "name": graph.get("name"),
                    "map_id": graph.get("map_id"), "reason": last_error,
                    "omitted_settings": ["event placement and custom actions"],
                    "placement_exported": False})
    exported.native_event_export_skipped = skipped
    return exported


def prepare_native_event_export(session, *, best_effort=False):
    """Compile event settings, then install class colour/speed settings (class_looks)."""
    exported = _prepare_native_event_export(session, best_effort=best_effort)
    document = getattr(session, "content_database", None)
    if not isinstance(document, dict):
        return exported
    if (document.get("mod_options") or {}).get("start_as_meia"):
        # Mod option Start as Meia: redraw Alundra's non-attack frames (player_costume).
        if exported is session:
            from copy import copy
            exported = copy(session); exported.data = bytearray(session.data)
        from player_costume import apply_costume, _global_bank, MEIA_MAP
        from sprite_sheet_import import costume_options
        from build_cache import cached_step
        from meia_final_frames import art_digest
        options = costume_options(document)
        # The costume reads the global sprite bank (start of the game data) and
        # Meia's map: while those and the options are unchanged, the redrawn
        # frames of an earlier build are reused (the step takes a minute+).
        _, _, bank_end, _ = _global_bank(exported.data)
        base, layout = exported.layout(MEIA_MAP)   # Meia's own pictures come from her map
        exported.meia_costume_report = cached_step(
            'meia-costume', exported, [(0, bank_end), (base, base + layout[6])], sorted(options.items()) + [('meia_final_art', art_digest())],
            ('player_costume', 'meia_actions', 'meia_final_frames', 'sprite_frame_replace', 'texture_codec', 'entity_animation',
             'animation_preview', 'entity_preview'),
            lambda: apply_costume(exported, **options))
    if document.get("sprite_imports"):
        # Database > Animations > Import sheet: edited pictures, drawn after the costume
        # and before class colours (so they are recoloured with their class).
        if exported is session:
            from copy import copy
            exported = copy(session); exported.data = bytearray(session.data)
        from sprite_sheet_import import apply_sprite_imports
        exported.sprite_import_report = apply_sprite_imports(exported, document)
    from class_looks import apply_class_looks, class_settings, apply_static_frames
    if any((g.get("native_placement") or {}).get("animation_static") for g in document.get("event_graphs", []) if isinstance(g, dict)):
        if exported is session:
            from copy import copy
            exported = copy(session); exported.data = bytearray(session.data)
        exported.static_frames_report = apply_static_frames(exported, document)
    if not any(class_settings(d) != (0, 100, 100, 100) or d.get("data", {}).get("spawn_attacks")
               for d in document.get("definitions", []) if isinstance(d, dict)):
        return exported
    if exported is session:
        from copy import copy
        exported = copy(session); exported.data = bytearray(session.data)
    handled = {(row["palette_fork"].get("map_id"), catalogue)
               for row in getattr(exported, "native_event_export_report", []) or []
               if isinstance(row, dict) and isinstance(row.get("palette_fork"), dict)
               for catalogue in row["palette_fork"].get("catalogues") or [row["palette_fork"].get("catalogue_index")]}
    exported.class_looks_report = apply_class_looks(exported, document, handled)
    return exported


def _prepare_native_event_export(session, *, best_effort=False, pause=None):
    """Compile event settings; Build opts into per-event best-effort fallbacks."""
    import stock_donors as _sd
    _sd.set_known_changed(None)   # never a hint left over from an interrupted build
    if not best_effort:
        require_native_event_export(session)
        graphs = (getattr(session, "content_database", None) or {}).get("event_graphs", [])
        if not graphs:return session
        from copy import copy
        from event_native_compile import bound_event_replacements
        bound = [graph for graph in graphs if graph.get("native_binding") is not None]
        new = [graph for graph in graphs if graph.get("native_binding") is None]
        replacements = [replacement for graph in bound for replacement in bound_event_replacements(session, graph)]
        spans = sorted((offset, offset + len(raw)) for offset, raw in replacements)
        if any(a[1] > b[0] for a, b in zip(spans, spans[1:])):
            raise EventExportError("Two authored events replace the same process; choose one replacement before building.")
        exported = copy(session);exported.data = bytearray(session.data)
        for offset, raw in replacements:exported.data[offset:offset + len(raw)] = raw
        if new:
            from new_event_compile import compile_new_events
            exported = compile_new_events(exported, new)
        exported.native_event_export_ids = {graph.get("id") for graph in graphs}
        exported.native_event_export_skipped = []
        return exported

    """Best effort avoids discarding compatible events because one page fails."""
    database = getattr(session, "content_database", None) or {}
    graphs = database.get("event_graphs", []) if isinstance(database, dict) else []
    if not isinstance(graphs, list):
        graphs = []
    if not graphs:
        return session
    from copy import copy, deepcopy
    from event_native_compile import bound_event_replacements
    exported = copy(session)
    exported.data = bytearray(session.data)
    exported.native_event_export_report = []
    exported.native_event_export_skipped = []
    exported.native_event_export_ids = set()
    occupied = []
    for graph in graphs:
        if not isinstance(graph, dict) or graph.get("native_binding") is None:
            continue
        try:
            replacements = bound_event_replacements(exported, graph)
            spans = [(offset, offset + len(raw)) for offset, raw in replacements]
            if any(a < end and start < b for start, end in occupied for a, b in spans):
                raise ValueError("another authored event already edits these native bytes")
            trial = bytearray(exported.data)
            for offset, raw in replacements:
                trial[offset:offset + len(raw)] = raw
            exported.data = trial
            occupied.extend(spans)
            exported.native_event_export_ids.add(graph.get("id"))
            exported.native_event_export_report.append({"event_id": graph.get("id"),
                "map_id": graph.get("map_id"), "name": graph.get("name"),
                "native_binding": True, "gameplay_verified": False})
        except Exception as error:
            exported.native_event_export_skipped.append({"event_id": graph.get("id"),
                "map_id": graph.get("map_id"), "name": graph.get("name"),
                "reason": str(error), "omitted_settings": ["bound native edit"],
                "placement_exported": False})
    for graph in graphs:
        if not isinstance(graph, dict):
            exported.native_event_export_skipped.append({"event_id":"unknown", "name":"Invalid event",
                "map_id":"unknown", "reason":"Event record is malformed", "omitted_settings":["event record"],
                "placement_exported":False})
    new = [graph for graph in graphs if isinstance(graph, dict) and graph.get("native_binding") is None]
    grouped = {}
    for graph in new:
        grouped.setdefault(graph.get("map_id"), []).append(graph)
    import stock_donors
    _stock = getattr(session, "original", None)
    _known = None
    if _stock:
        stock_donors.set_known_changed(None)
        try:
            _known = stock_donors.changed_stock_maps(exported.data, _stock)   # once per build
        except Exception:
            _known = None   # not full game data: prepare() works it out (or skips) itself
    import event_group_cache as _egc
    _static = _egc.static_hash(getattr(session, "content_database", None), getattr(session, "original", b"") or b"")
    pending = {}   # map -> finished block from the cache, written into the data in one go

    def flush(current):
        if not pending:
            return current
        from stock_donors import replace_blocks
        current = copy(current); current.data = bytearray(replace_blocks(current.data, dict(pending)))
        pending.clear()
        return current

    for group in grouped.values():
        if pause is not None:
            pause()   # (a background warm-up steps aside between maps)
        stock_donors.set_known_changed(_known)
        _targets = {g.get("map_id") for g in group if type(g.get("map_id")) is int and g.get("map_id") < stock_donors.STOCK_MAPS}
        key = None
        try:
            key = _egc.group_key(exported, group, _static, _known, pending)
        except Exception:
            key = None
        hit = _egc.load(key) if key else None
        if hit is not None and hit.get("map") == key[0]:
            # Same inputs as an earlier build: its finished map block and report.
            pending[key[0]] = hit["block"]
            exported = copy(exported)
            db = dict(getattr(exported, "content_database", None) or {})
            db["project_state"] = deepcopy(hit["project_state"])
            if hit.get("created_maps") is not None:db["created_maps"] = deepcopy(hit["created_maps"])
            exported.content_database = db
            exported.actor_route_resume_slots = hit.get("route_slots", 0)
            if hit.get("boss_places"):
                _all = {c: dict(rows) for c, rows in (getattr(exported, "boss_places", None) or {}).items()}
                for c, rows in hit["boss_places"].items():
                    _all.setdefault(c, {}).update(rows)
                exported.boss_places = _all
            if hit.get("melzas_places"):
                _places = dict(getattr(exported, "melzas_places", None) or {})
                _places.update(hit["melzas_places"])   # map-number keys: dict(**...) raised TypeError (2026-10-21)
                exported.melzas_places = _places
            rows = deepcopy(hit["report"])
            exported.native_event_export_report = list(exported.native_event_export_report) + rows
            exported.native_event_export_ids = set(exported.native_event_export_ids) | {row.get("event_id") for row in rows if row.get("event_id")}
            if _known is not None:
                _known |= _targets
            continue
        exported = flush(exported)
        trial = copy(exported)   # compile_new_events never edits its input's data (it works on its own copy)
        try:
            from new_event_compile import compile_new_events
            compiled = compile_new_events(trial, group)
            if key:
                try:
                    _egc.store(key, trial.data, compiled)
                except Exception:
                    pass
            compiled.native_event_export_report = list(exported.native_event_export_report) + list(getattr(compiled, "native_event_export_report", []))
            compiled.native_event_export_skipped = list(exported.native_event_export_skipped)
            compiled.native_event_export_ids = set(exported.native_event_export_ids) | {
                row.get("event_id") for row in getattr(compiled, "native_event_export_report", []) if row.get("event_id")}
            exported = compiled
            if _known is not None:
                _known |= _targets   # this group may have changed its own stock maps
        except Exception:
            if _known is not None:
                _known |= _targets
            # One troublesome event must not discard its neighbours. Retry each
            # on the progressively built module, with safe feature fallbacks.
            for graph in group:
                exported = _compile_new_best_effort(exported, graph)
    exported = flush(exported)
    _egc.prune()
    stock_donors.set_known_changed(None)
    session.native_event_export_report = list(exported.native_event_export_report)
    session.native_event_export_skipped = list(exported.native_event_export_skipped)
    session.native_event_export_ids = set(exported.native_event_export_ids)
    exported.content_database = getattr(exported, "content_database", getattr(session, "content_database", None))
    return exported


def generated_event_opcodes(session, exported=None):
    """Collect the actual generated operations for target EXE ABI validation."""
    exported = exported if exported is not None else prepare_native_event_export(session)
    opcodes = set()
    for report in getattr(exported, "native_event_export_report", []):
        opcodes.update(report.get("opcodes", []))
    from event_native_compile import compile_bound_event
    from event_editor import SIZES
    included = getattr(exported, "native_event_export_ids", None)
    for graph in (getattr(session, "content_database", None) or {}).get("event_graphs", []):
        if graph.get("native_binding") is None:
            continue
        if included is not None and graph.get("id") not in included:
            continue
        _, code = compile_bound_event(session, graph)
        position = 0
        while position < len(code):
            opcode = code[position]; size = SIZES.get(opcode)
            if not size or position + size > len(code):
                raise EventExportError("Generated bound event instruction is truncated")
            opcodes.add(opcode); position += size
            if opcode == 255:
                break
    return sorted(opcodes)
