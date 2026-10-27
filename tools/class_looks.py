"""Class colour and speed settings from the database, installed per map.

* Colour (palette_shift: hue_degrees, saturation_percent) - new_event_compile
  forks the palette for classes placed as events. This pass also recolours
  classes that sit natively on maps you made (483+, e.g. a boss on a copied
  map), which no event placement touches.
* Speed (speed_percent, 100 = game speed) - "Animation and attack speed".
  Every drawable frame of the class's map-local sprite keeps its delay/control
  high bit and gets its countdown (low 7 bits) scaled by 100/speed (minimum 1
  tick). Attacks are played as animations, so they speed up with them.
* Movement speed (move_speed_percent) - each animation set's speed word, which
  the engine uses as step distance / movement force (pinned source
  EntityGameplayManager.cs268, PhysicsEngine.cs1581-1594), scaled by
  percent/100 (0 stays 0). In place, no sizes change.

Scope: all instances of that class on that map (the sprite record is shared).
Only map-local classes (256-511); global sprites are shared by every map.
Gameplay timing effects are not verified in game.
"""
import struct


def class_settings(definition):
    data = (definition or {}).get('data', {})
    palette = data.get('palette_shift') or {}
    hue = palette.get('hue_degrees', 0) or 0
    saturation = palette.get('saturation_percent', 100)
    speed = data.get('speed_percent', 100)
    return hue, saturation, speed, data.get('move_speed_percent', 100)


def _sprite_bounds(data, map_id):
    from map_block_repack import pointers, sections
    table = pointers(data)
    base = table[map_id]
    h = sections(data[base:table[map_id + 1]])
    start, end = base + h[3], base + h[4]
    sh = struct.unpack_from('<12I', data, start)
    return start, end, sh


def scale_animation_speed(data, map_id, catalogue, percent):
    """Scale frame delays of a map-local class sprite; returns (data, frames changed)."""
    if type(catalogue) is not int or not 256 <= catalogue < 512:
        raise ValueError('Animation speed can be changed for map-local classes only')
    if type(percent) is not int or not 25 <= percent <= 500:
        raise ValueError('Speed must be 25..500 percent')
    from entity_animation import parse_sprite_animation_record
    start, end, sh = _sprite_bounds(data, map_id)
    sets = parse_sprite_animation_record(data, start, end, catalogue & 255, sh[3], sh[4])
    data = bytearray(data); done = set(); changed = 0
    for animation in sets:
        for stream in animation.streams:
            if stream is None:
                continue
            for frame in stream.frames:
                if frame.offset in done:
                    continue
                done.add(frame.offset)
                ticks = frame.delay_raw & 0x7F
                if not ticks:
                    continue
                new = max(1, min(127, round(ticks * 100 / percent)))
                if new != ticks:
                    data[frame.offset] = 0x80 | new; changed += 1
    return data, changed


def scale_movement_speed(data, map_id, catalogue, percent):
    """Scale every animation set's movement speed word; returns (data, sets changed)."""
    if type(catalogue) is not int or not 256 <= catalogue < 512:
        raise ValueError('Movement speed can be changed for map-local classes only')
    if type(percent) is not int or not 25 <= percent <= 500:
        raise ValueError('Movement speed must be 25..500 percent')
    from entity_animation import parse_sprite_animation_record
    start, end, sh = _sprite_bounds(data, map_id)
    sets = parse_sprite_animation_record(data, start, end, catalogue & 255, sh[3], sh[4])
    data = bytearray(data); changed = 0
    for animation in sets:
        if animation.speed_raw:
            new = max(1, min(0xFFFF, round(animation.speed_raw * percent / 100)))
            if new != animation.speed_raw:
                struct.pack_into('<H', data, animation.offset + 8, new); changed += 1
    return data, changed


def _import_from_original(exported, data, m, home, sprite_id):
    """import_local_sprite from the ORIGINAL game's map home (self-contained classes,
    2026-10-23): when the project changed that stock map, its original block stands in
    for the import and the project's block goes back afterwards."""
    from local_sprite_import import import_local_sprite
    import stock_donors
    stock = stock_donors.original_of(exported) if home != m and 0 <= home < 483 else None
    if stock is None:
        return import_local_sprite(data, m, home, sprite_id)
    own = stock_donors.map_block(data, home)
    original = stock_donors.stock_block(stock, home)
    if own == original:   # unchanged: as before
        return import_local_sprite(data, m, home, sprite_id)
    swapped = stock_donors.replace_blocks(data, {home: original})
    swapped, report = import_local_sprite(bytearray(swapped), m, home, sprite_id)
    return bytearray(stock_donors.replace_blocks(swapped, {home: own})), report


def apply_class_looks(exported, document, handled_palettes=()):
    """Install database colour/speed settings on the built data. Returns a report list."""
    from native_class_placement import record_cluster
    from map_slots import map_count
    from local_sprite_recolor import recolor_local_classes
    from local_sprite_import import sprite_assets, import_local_sprite
    last = ''
    definitions = [d for d in (document or {}).get('definitions', []) if isinstance(d, dict)]
    by_id = {d.get('id'): d for d in definitions}
    base_class = {}
    for d in definitions:
        cat = d.get('source', {}).get('catalogue_index')
        if type(cat) is int and not d.get('clone_of') and d.get('kind') in ('npc', 'enemy', 'boss', 'object'):
            base_class.setdefault(cat, d)
    placed = {}
    for graph in (document or {}).get('event_graphs', []):
        if isinstance(graph, dict):
            for page in graph.get('pages', []) or [{}]:
                d = by_id.get(page.get('class_id') or graph.get('class_id'))
                cat = (d or {}).get('source', {}).get('catalogue_index')
                if type(cat) is int and type(graph.get('map_id')) is int:
                    placed.setdefault(graph['map_id'], {})[cat] = d
    # Owners of new attacks: also every original map they appear on (art import only).
    from native_spawn_attacks import class_maps as _maps
    art_only = {}
    for d in definitions:
        cat = d.get('source', {}).get('catalogue_index')
        if d.get('data', {}).get('spawn_attacks') and type(cat) is int and not d.get('clone_of'):
            for m in _maps(d):
                art_only.setdefault(m, {})[cat] = d
    handled = set(handled_palettes)
    report = []
    data = exported.data
    count = map_count(data)
    maps = sorted(set(range(483, count)) | {m for m in list(placed) + list(art_only) if 0 <= m < count})
    for m in maps:
        try:
            entities = record_cluster(data, m)['entities']
        except Exception:
            continue
        present = {raw[6] + (256 if raw[5] & 128 else 0) for raw in entities}
        # a boss's parts (Melzas's doubles...) are spawned by its code, not placed: they are here too
        from content_database import ContentDatabase
        present |= {p for c in list(present) for p in ContentDatabase.BOSS_PARTS.get(c, ())}
        looks = dict(placed.get(m, {}))
        if m >= 483:
            for cat in present:
                if cat in base_class:
                    looks.setdefault(cat, base_class[cat])
        wanted = dict(art_only.get(m, {})); wanted.update(looks)
        for cat, definition in sorted(wanted.items()):
            if cat not in present:
                continue
            # New attacks (spawn_attacks): the spawned class's art must be on this map.
            for spawn in definition.get('data', {}).get('spawn_attacks', []) or []:
                target = by_id.get(spawn.get('class_id'), {})
                tcat = target.get('source', {}).get('catalogue_index')
                if type(tcat) is not int or not 256 <= tcat < 512:
                    continue
                try:
                    sprite_assets(data, m, tcat - 256)
                    continue          # already here
                except Exception:
                    pass
                from native_spawn_attacks import class_maps
                for home in class_maps(target):
                    try:
                        data, _ = _import_from_original(exported, data, m, home, tcat - 256)
                        report.append(dict(map_id=m, catalogue_index=tcat, imported_for_new_attack_of=cat, from_map=home))
                        break
                    except Exception as error:
                        last = str(error)
                else:
                    report.append(dict(map_id=m, catalogue_index=tcat, skipped='art not imported: ' + (last if class_maps(target) else 'no home map')))
            if not 256 <= cat < 512 or cat not in looks:
                continue
            hue, saturation, speed, move = class_settings(definition)
            try:
                if (hue, saturation) != (0, 100) and (m, cat) not in handled and m >= 483:
                    # a boss's parts (Melzas: his look-alike copies, orbs ...) take its colours with it,
                    # unless they have their own (user 2026-10-21); recoloured together, the palettes
                    # only they use change in place (no 41-palette overflow)
                    def on_map(p):   # parts are not placed: the boss's code spawns them from their sprites
                        try:
                            sprite_assets(data, m, p - 256); return True
                        except Exception:
                            return False
                    parts = [p for p in definition.get('source', {}).get('boss_parts') or []
                             if 256 <= p < 512 and (m, p) not in handled and on_map(p)
                             and class_settings(looks.get(p) or {})[:2] in ((0, 100),)]
                    data, info = recolor_local_classes(data, m, [cat] + parts, hue, saturation)
                    for c in [cat] + parts:
                        handled.add((m, c))
                    report.append(dict(map_id=m, catalogue_index=cat, parts=parts, colour=dict(hue_degrees=hue, saturation_percent=saturation)))
            except Exception as error:
                report.append(dict(map_id=m, catalogue_index=cat, skipped=str(error)))
            # speed settings do not depend on the colour change (2026-10-26: Melzas on map 495
            # lost his speed when his recolour hit the 41-palette bound)
            try:
                if speed != 100:
                    data, frames = scale_animation_speed(data, m, cat, speed)
                    report.append(dict(map_id=m, catalogue_index=cat, speed_percent=speed, frames_changed=frames))
                    # Melzas's doubles (424) run with him (user 2026-10-26), unless they have their own speed
                    if cat == 418 and (m, 424) not in handled and class_settings(looks.get(424) or {})[2] == 100:
                        try:
                            sprite_assets(data, m, 424 - 256)
                            data, frames = scale_animation_speed(data, m, 424, speed)
                            handled.add((m, 424))
                            report.append(dict(map_id=m, catalogue_index=424, speed_percent=speed, frames_changed=frames, with_class=418))
                        except Exception as error:
                            report.append(dict(map_id=m, catalogue_index=424, skipped=str(error)))
                if move != 100:
                    data, sets = scale_movement_speed(data, m, cat, move)
                    report.append(dict(map_id=m, catalogue_index=cat, move_speed_percent=move, sets_changed=sets))
            except Exception as error:
                report.append(dict(map_id=m, catalogue_index=cat, skipped=str(error)))
    exported.data = bytearray(data)
    return report


def apply_static_frames(exported, document):
    """Event menu "Static": the chosen animation shows only the chosen frame.

    Every frame of that animation (each direction) of the class's map-local
    sprite on that map is pointed at the picture of the selected frame (frame
    pictures are 5-byte entries; the picture id is the halfword at +3; sizes do
    not change). Scope: that animation of that class on that map, so another
    event on the same map using the same class and animation is static too.
    Global classes (0-255, shared by every map) are skipped."""
    from entity_animation import parse_sprite_animation_record
    definitions = {d.get('id'): d for d in (document or {}).get('definitions', []) if isinstance(d, dict)}
    report = []; done = set()
    data = exported.data
    for graph in (document or {}).get('event_graphs', []):
        if not isinstance(graph, dict):
            continue
        placement = graph.get('native_placement') or {}
        if not placement.get('animation_static') or placement.get('animation') is None:
            continue
        pages = graph.get('pages') or [{}]
        definition = definitions.get(pages[0].get('class_id') or graph.get('class_id'), {})
        cat = definition.get('source', {}).get('catalogue_index')
        m, anim, frame = graph.get('map_id'), placement['animation'], int(placement.get('static_frame', 0) or 0)
        key = (m, cat, anim)
        if key in done:
            continue
        done.add(key)
        if type(cat) is not int or not 256 <= cat < 512:
            report.append(dict(event_id=graph.get('id'), skipped='Static frames need a map-local class')); continue
        try:
            start, end, sh = _sprite_bounds(data, m)
            sets = parse_sprite_animation_record(data, start, end, cat & 255, sh[3], sh[4])
            if not 0 <= anim < len(sets):
                raise ValueError('Animation outside this sprite')
            data = bytearray(data)
            for stream in sets[anim].streams:
                if stream is None:
                    continue
                picture = stream.frames[min(frame, len(stream.frames) - 1)].image_set_index
                for f in stream.frames:
                    struct.pack_into('<H', data, f.offset + 3, picture)
            report.append(dict(event_id=graph.get('id'), map_id=m, catalogue_index=cat, animation=anim, frame=frame))
        except Exception as error:
            report.append(dict(event_id=graph.get('id'), skipped=str(error)))
    exported.data = bytearray(data)
    return report
