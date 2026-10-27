"""What an enemy or boss spawns, shown as its attacks in the database.

Facts come from data/2026-10-08-native-ai-spawns.json (made by
tools/extract_native_ai_spawns.py from the pinned xcasadio source review): for
each native callback (bank A/C/D/E/F + index) the classes its AI spawns and,
when known, the animation during which it spawns them. A class's callbacks are
read from its sprite record (event_vm_compatibility.sprite_callbacks) on a map
that has it. Map-local spawns are catalogue 256 + index (SpawnWarpEntity
current-map mapping, as in docs/2026-10-04-melzas-private-cooldown.txt).

Each spawned class has its own balance record, so its damage is edited on that
class (the database stores it there and the build writes it). Source-derived,
not verified in game.
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / 'data' / '2026-10-08-native-ai-spawns.json'
WHEN = {'A': 'when it appears', 'C': 'during its AI', 'D': 'when touched', 'E': 'when defeated', 'F': 'when talked to'}
_cache = {}


def spawn_table():
    if 'table' not in _cache:
        try:
            _cache['table'] = json.loads(DATA.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            _cache['table'] = {}
    return _cache['table']


def class_maps(definition):
    source = definition.get('source', {})
    maps = [source.get('observed_map')] + list(source.get('observed_maps', [])) + list(source.get('graphic_maps', []))
    return [m for m in dict.fromkeys(maps) if type(m) is int]


def class_spawns(data, definition):
    """[{catalogue, bank, animation, when}] for one class (empty if unknown)."""
    from event_vm_compatibility import sprite_callbacks
    catalogue = definition.get('source', {}).get('catalogue_index')
    if type(catalogue) is not int:
        return []
    callbacks = None
    for m in class_maps(definition) or [0]:
        try:
            callbacks = sprite_callbacks(data, m, catalogue); break
        except Exception:
            continue
    if not callbacks:
        return []
    table = spawn_table(); rows = {}
    for bank, value in callbacks:
        for spawn in table.get(f'{bank}{value}', {}).get('spawns', []):
            for index in spawn.get('ids', []):
                target = (256 if spawn.get('local') else 0) + index
                if not 0 <= target < 512:
                    continue
                animation = spawn.get('animation') if bank == 'C' else None
                key = (target, bank, animation)
                if key not in rows:
                    when = f'during animation {animation}' if animation is not None else WHEN.get(bank, bank)
                    rows[key] = dict(catalogue=target, bank=bank, animation=animation, when=when)
    return sorted(rows.values(), key=lambda r: (r['animation'] is None, r['animation'] or 0, r['catalogue']))
