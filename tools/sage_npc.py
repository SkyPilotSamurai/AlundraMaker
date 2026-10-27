"""The sages as NPCs (user 2026-10-18).

In the game a sage is not a character but each crest map's own effect sprite 0:
the swirling pool, the light and the sage's figure (map 25 Lars Crypt 5, 95
Magyscar 10, 84 Reptile Lair 5, 432 Nava's Keep 5, 76 Coastal Cave 8). The map's
effect table has it hidden (flags 80, type 0) and a program shows it.
Animations of that effect: 0 appears (111 frames), 1 stands (16, loops),
2 a short sequence, 3 leaves.

A placed sage: the donor map's effect 0 is copied into the map's effect bank
(block_switch.import_local_effect) and an effect entry shows it standing
(flags C0: own sprite, shown from the start; animation 1) on the event's tile.
Its actions run when Alundra walks up to the sage (Player touch on that tile;
objects cannot take authored Interact actions yet), as the game's sages speak
when you reach them.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# names from each sage's own dialogue on that map ("I am Uma, Queen of Life and Death..." etc.)
SAGES = (('lars', 'Lars', 25), ('magyscar', 'Uma', 95), ('reptile_lair', 'Jeal', 84),
         ('navas_keep', 'Nava (Guardian)', 432), ('coastal_cave', 'Vul', 76))
OLD_NAMES = {'Lars (Sage)', 'Sage (Magyscar)', 'Sage (Reptile Lair)', "Sage (Nava's Keep)", 'Sage (Coastal Cave)'}
EFFECT = 0
STAND = 1
HELPER = 25   # Transparent Block (1x1x2): invisible, solid, talkable


def sage_of(definition):
    source = (definition or {}).get('source', {})
    return source.get('sage_map') if source.get('variant') == 'sage' else None


def preview(map_id):
    """First standing frame of the sage (base layer + additive glow)."""
    from PIL import Image
    folder = ROOT / f'assets/engine/maps/{map_id:03d}/effects/{EFFECT:03d}'
    try:
        anim = json.loads((folder / 'animations.json').read_text())['animations'][STAND]
        frames = anim.get('frames', anim) if isinstance(anim, dict) else anim
        image = frames[0]['image']
        base = folder / f'{image}.png'
        add = folder / f'{image}_add.png'
        out = None
        for p in (base, add):
            if p.exists():
                with Image.open(p) as im:
                    im = im.convert('RGBA')
                    out = im if out is None else Image.alpha_composite(out.resize(im.size) if out.size != im.size else out, im)
        if out is not None and out.getbbox():
            return out.crop(out.getbbox())
    except Exception:
        return None
    return None


def install(data, placed):
    """placed: [(graph, donor map)]. Copies each sage effect onto its map and
    shows it standing on the event's tile. Returns (data, reports)."""
    from area_map import grid
    from heal_tile import _View, _entries, MAX_EFFECTS
    from block_switch import import_local_effect
    from native_class_placement import record_cluster, append_record_cluster
    reports = []
    by_map = {}
    for graph, donor in placed:
        by_map.setdefault(graph['map_id'], []).append((graph, donor))
    for map_id, rows in by_map.items():
        slots = {}
        for _, donor in rows:
            if donor not in slots:
                data, slots[donor] = import_local_effect(data, map_id, donor, EFFECT)
        w, h, cells = grid(_View(data), map_id)
        effects = _entries(record_cluster(data, map_id)['effects'])
        for graph, donor in rows:
            x, y = graph['region'][:2]
            z = (graph.get('native_placement') or {}).get('height')
            if z is None:
                z = cells[y * w + x]['values'][3]
            if len(effects) >= MAX_EFFECTS:
                raise ValueError(f'Map {map_id} has no room for another effect')
            effects.append(bytes((0, 0, w - 1, h - 1, 0xC0, slots[donor], 2 * x + 1, 2 * y + 1, 2 * z, STAND, 0, 0)))
            reports.append({'event_id': graph['id'], 'map_id': map_id, 'name': graph.get('name'), 'sage_from_map': donor,
                            'effect_sprite': slots[donor], 'effect_entry': len(effects) - 1, 'tile': [x, y, z],
                            'gameplay_verified': False})
        data, _ = append_record_cluster(data, map_id, effects=b''.join(effects) + bytes(4))
        data = bytearray(data)
    return data, reports
