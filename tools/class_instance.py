"""Placed events are instances of their Database class (user 2026-10-24).

An event's native_placement stores only what the user set on that event.
A missing key means "use the class's current value"; class_placement_defaults
gives those values, effective_placement merges them for previews and Build.
"""
from copy import deepcopy

STATUE_ON = True        # shooting Nirude statues fire at once unless switched off
SARA_CATALOGUE = 452    # Sara starts with Track Player on
PILLAR_CATALOGUE = 298  # Pushable Pillar (One Tile) starts facing Right


def graph_class_id(graph):
    pages = (graph or {}).get('pages') or [{}]
    return pages[0].get('class_id', (graph or {}).get('class_id'))


def class_placement_defaults(definition):
    """Placement values an event inherits from its class while not overridden."""
    if not definition:return {}
    source = definition.get('source', {}) or {}
    out = {}
    facing = source.get('default_facing') or ('right' if source.get('catalogue_index') == PILLAR_CATALOGUE else None)
    if facing:out['facing'] = facing
    if source.get('variant') == 'nirude_statue' and source.get('statue_variant'):
        try:
            from native_nirude_statue_variants import variant_of
            if variant_of(definition):out['active_by_default'] = STATUE_ON
        except ImportError:pass
    if definition.get('kind') == 'boss' and source.get('catalogue_index') == SARA_CATALOGUE:
        out['track_player'] = True
    return out


def effective_placement(graph, definition):
    """The event's placement with the class's current values filled in."""
    out = class_placement_defaults(definition)
    out.update((graph or {}).get('native_placement') or {})
    return out


def resolve_graphs(graphs, definitions):
    """Copies of graphs whose placements carry the classes' current values (Build)."""
    if not isinstance(definitions, dict):
        definitions = {row.get('id'): row for row in definitions or [] if isinstance(row, dict)}
    out = []
    for graph in graphs:
        defaults = class_placement_defaults(definitions.get(graph_class_id(graph)))
        missing = {k: v for k, v in defaults.items() if k not in (graph.get('native_placement') or {})}
        if missing:
            graph = dict(graph)
            graph['native_placement'] = dict(missing, **(graph.get('native_placement') or {}))
        out.append(graph)
    return out


def set_override(placement, key, value, definition, fallback=None):
    """Store value only when it differs from what the class (or fallback) gives."""
    default = class_placement_defaults(definition).get(key, fallback)
    if value == default:placement.pop(key, None)
    else:placement[key] = value


def strip_class_defaults(document):
    """Migration: drop stored placement values equal to the class's current
    default (stale copies made when the class was chosen). Returns a list of
    (event id, key, value) removed. Values that differ stay as overrides."""
    definitions = {row.get('id'): row for row in document.get('definitions', []) if isinstance(row, dict)}
    removed = []
    for graph in document.get('event_graphs', []):
        placement = graph.get('native_placement')
        if not isinstance(placement, dict):continue
        for key, value in class_placement_defaults(definitions.get(graph_class_id(graph))).items():
            if key in placement and placement[key] == value:
                del placement[key];removed.append((graph.get('id'), key, value))
    return removed
