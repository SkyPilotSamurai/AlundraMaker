"""Pattern Plate (catalogue 364), two versions, with Activate contents.

The game's plates (Star / Moon / Water / Sun) go with the carryable symbol
objects 363 / 367 / 368 / 369. The plate's direction is its symbol:
down = Star, up = Moon, left = Water, right = Sun (animation directions
00 / 10 / 08 / 18).

* Static (map 29 entity 16, C17): shows its symbol (animation 0). When its own
  symbol object is put on it (60 template: stands on this), the object can no
  longer be picked up (63 template 0200), sound FE, the plate lights
  (animation 1) and stays lit.
* Changing (map 400 entity 0, A1/C1): animation 2 shows Star, Moon, Water,
  Sun for 24 steps each, over and over. Its own object put on it while its own
  symbol shows lights it; any symbol object put on it at another moment (or a
  wrong one) fails: the plate stops on the symbol shown (animation 0), sound 3,
  and every changing plate on the map stops too (shared map flag; the map's
  plates start again when the map is entered again).

Here the solved state is a private project switch (stays solved), and the
event's Activate contents run once when the plate lights.
"""
from event_logic_compile import _Assembler, compile_logic
from project_state_runtime import compile_project_command, compile_project_condition

SYMBOLS = (363, 367, 368, 369)          # by plate direction 0..3
SYMBOL_NAMES = ('Star', 'Moon', 'Water', 'Sun')
DIRECTIONS = (0x00, 0x10, 0x08, 0x18)
FAIL_FLAG = 0x87DF                      # map (temporary) flag no stock map script uses
STATIC_SOURCE = (29, 16)
CHANGING_SOURCE = (400, 0)
PHASE_STEPS = 24


def verify_source(datas):
    from native_class_placement import record_cluster
    for m, i in (STATIC_SOURCE, CHANGING_SOURCE):
        raw = record_cluster(datas, m)['entities'][i]
        if not raw[5] & 0x80 or raw[6] != 364 - 256:
            raise ValueError('Pattern plate364 source record differs')
    return True


def symbol_templates(entities, actor_indices, graphs, definitions):
    """{symbol index: [template indices]} of the symbol objects on the map:
    stock records first, then the map's placed events."""
    found = {k: [] for k in range(4)}
    for index, raw in enumerate(entities):
        cat = raw[6] + (256 if raw[5] & 0x80 else 0)
        if cat in SYMBOLS:
            found[SYMBOLS.index(cat)].append(index)
    for graph in graphs:
        cid = (graph.get('pages') or [{}])[0].get('class_id', graph.get('class_id'))
        cat = definitions.get(cid, {}).get('source', {}).get('catalogue_index')
        if cat in SYMBOLS and graph['id'] in actor_indices:
            found[SYMBOLS.index(cat)].append(actor_indices[graph['id']])
    return found


def compile_pattern_plate(registry, latch_id, commands=None, *, leaf_emitter=None, symbol=0,
                          templates=None, changing=False, start=0, fail_stops_others=True, flush=None, keep_state=False):
    """start: the symbol a changing plate shows first (its record faces that
    way; rotate_cycle() turns that direction's animation 2 to start there).
    fail_stops_others: its failure sets the shared map flag every changing
    plate on the map watches (else only this plate stops).
    A symbol object put on the plate stays stuck there (63 template 0200), lit
    or failed: a static plate takes its own symbol, a changing plate the symbol
    it shows at that moment; anything else fails (sound 3, the plate stops).
    keep_state: a lit plate stays lit after leaving the room (else it starts
    again, like the game's). flush: Flush With Floor (_flush_steps)."""
    registry.get('switches', latch_id)
    templates = templates or {k: [] for k in range(4)}
    own = templates.get(symbol) or []
    if not changing and not own:
        raise ValueError(f'Put a {SYMBOL_NAMES[symbol]} Object (carryable) on this map for this pattern plate '
                         f'(the plate faces {("down", "up", "left", "right")[symbol]}, so its symbol is the {SYMBOL_NAMES[symbol]})')
    if changing and not any(templates.get(k) for k in range(4)):
        raise ValueError('Put a Star, Moon, Water or Sun Object (carryable) on this map for this pattern plate')
    if any(t > 126 for k in templates for t in templates[k]):
        raise ValueError('Symbol object template number out of range')

    def state(value, condition=False):
        row = {'type': 'switch' if condition else 'set_switch', 'switch_scope': 'project', 'switch_id': latch_id, 'value': value}
        return (compile_project_condition if condition else compile_project_command)(row, registry)

    def emit(row):
        if row.get('switch_scope') == 'project' or row.get('variable_scope') == 'project':
            return compile_project_command(row, registry)
        if leaf_emitter: return leaf_emitter(row)
        raise ValueError('Unverified pattern plate continuation leaf')

    continuation = compile_logic(commands or [], leaf_emitter=emit,
                                 project_condition_emitter=lambda row: compile_project_condition(row, registry))
    steps = _flush_steps(flush) if flush else _sprite_steps()
    everyone = [t for k in range(4) for t in templates.get(k) or []]
    glue = lambda t: bytes((0x63, t, 0x00, 0x02))
    c = _Assembler(); steps.c = c
    if keep_state:
        c.data.extend(state(True, True)); c.branch(3, 'kept')
    if not changing:
        steps.unlit_poll(symbol, lambda: [(t, ('hit', symbol, t) if t in own else ('wrong', t)) for t in everyone])
        for t in everyone:
            if t in own: continue
            c.label(('wrong', t)); c.data.extend(glue(t) + bytes((0xBD, 0x03, 0x00)))   # a wrong symbol: stuck, the plate stops
            steps.stopped_static(symbol)
    else:
        c.label('round')
        for k in [(start + i) % 4 for i in range(4)]:
            steps.phase(k, lambda k=k: [(t, ('hit', k, t) if t in (templates.get(k) or []) else ('fail', k, t)) for t in everyone],
                        ('stop', k))
        c.branch(2, 'round')
        for k in range(4):
            for t in [None] + everyone:
                c.label(('fail', k, t) if t is not None else ('stop', k))
                if t is not None:
                    c.data.extend(glue(t))
                if fail_stops_others:
                    c.data.extend(bytes((0x05,)) + FAIL_FLAG.to_bytes(2, 'little'))
                c.branch(2, ('failed', k))
            c.label(('failed', k))
            steps.failed(k)
    lit_symbols = range(4) if changing else (symbol,)
    for k in lit_symbols:
        for t in (templates.get(k) or []):
            c.label(('hit', k, t))
            c.data.extend(bytes((0x00, 0xBD, 0xFE, 0x00)) if changing else bytes((0xBD, 0xFE, 0x00)))   # the game's: sound FE
            steps.light(k)
            c.data.extend(glue(t)); c.branch(2, ('solved', k))
        c.label(('solved', k))
        c.data.extend(state(True))
        c.data.extend(continuation)
        steps.lit(k)
    if keep_state:
        c.label('kept')
        steps.lit_again(symbol)
    return {'C': c.finish()}, {
        'class_id': 364, 'version': 'changing' if changing else 'static',
        'donor': CHANGING_SOURCE if changing else STATIC_SOURCE, 'symbol': SYMBOL_NAMES[symbol],
        'symbol_templates': {SYMBOL_NAMES[k]: v for k, v in templates.items()},
        'latch_id': latch_id, 'fail_flag': FAIL_FLAG if changing else None, 'keep_state': bool(keep_state),
        'start_symbol': SYMBOL_NAMES[start] if changing else None, 'failure_stops_others': bool(fail_stops_others) if changing else None,
        'flush_with_floor': flush, 'continuation_length': len(continuation), 'gameplay_verified': False}


class _sprite_steps:
    """The plate drawn by its own sprite: the game's animations."""
    c = None

    def _poll(self, targets, label):
        self.c.label(label); self.c.data.append(0)
        for t, to in targets():
            self.c.data.extend(bytes((0x60, t))); self.c.branch(3, to)

    def unlit_poll(self, symbol, targets):
        self.c.data.extend(bytes((0x1A, 0x00)))                 # its symbol, unlit
        self._poll(targets, 'poll'); self.c.branch(2, 'poll')

    def stopped_static(self, symbol):
        self.c.data.extend(bytes((0x00, 0xFF)))

    def phase(self, k, targets, stop):
        if not getattr(self, 'started', False):
            self.c.data.extend(bytes((0x1A, 0x02))); self.started = True   # the four symbols in turn
        self.c.data.extend(bytes((0x73, PHASE_STEPS)))
        self.c.label(('phase', k)); self.c.data.append(0)
        self.c.branch(0x30, stop, FAIL_FLAG)                    # another plate failed
        for t, to in targets():
            self.c.data.extend(bytes((0x60, t))); self.c.branch(3, to)
        self.c.branch(0x74, ('phase', k))

    def failed(self, k):
        self.c.data.extend(bytes((0x5B, 0x80, 0x00, DIRECTIONS[k], 0xBD, 0x03, 0x00, 0x37, 0x28,
                                  0x5B, 0x80, 0x00, DIRECTIONS[k], 0x00, 0xFF)))

    def light(self, k):
        self.c.data.extend(bytes((0x5B, 0x80, 0x01, DIRECTIONS[k])))

    def lit(self, k):
        self.c.data.extend(bytes((0x00, 0xFF)))

    def lit_again(self, k):
        self.c.data.extend(bytes((0x5B, 0x80, 0x01, DIRECTIONS[k], 0xFF)))


def flush_animations(symbol, changing):
    """The game's plate animations a Flush With Floor plate copies into its squares, as
    {name: (animation, direction)}: unlit (static) or cycle (changing), lit0..3 (lit on
    that symbol; a static plate only its own) and fail0..3 (changing: it stops on that symbol)."""
    if changing:
        names = {'cycle': (2, 0)}
        names.update({f'fail{k}': (0, k) for k in range(4)})
        names.update({f'lit{k}': (1, k) for k in range(4)})
    else:
        names = {'unlit': (0, symbol), f'lit{symbol}': (1, symbol)}
    return names


FAIL_RESTART = 41   # frames: after a failure the game sets animation 0 again 41 frames later (37 28)


class _flush_steps:
    """The plate drawn in its floor squares (Flush With Floor). flush = {'tiles': (x, y) top-left
    square, 'height': floor height, 'frames': {name: [((x, y) spare 2x2 squares with that frame's
    picture, frames shown)]}} (flush_animations). A symbol object resting on the squares at floor
    height (07) stands for 'stands on this' (60); each animation frame is copied in (85) for as many
    frames as the game shows it."""
    c = None

    def __init__(self, flush):
        self.tx, self.ty = flush['tiles']; self.z = flush['height']; self.frames = flush['frames']

    def copy(self, xy):
        return bytes((0x85, xy[0], xy[1], 2, 2, self.tx, self.ty))

    def on_plate(self, t):
        return bytes((0x07, t, self.tx, self.tx + 1, self.ty, self.ty + 1, self.z, self.z))

    def wait(self, n):                              # 37 n lasts n+1 frames
        while n > 0:
            step = min(n, 256); self.c.data.extend(bytes((0x37, step - 1))); n -= step

    def show(self, seq, total):                     # the animation from its start for `total` frames
        shown = 0
        while shown < total:
            for xy, n in seq:
                n = min(n, total - shown)
                if n <= 0: break
                self.c.data.extend(self.copy(xy)); self.wait(n); shown += n

    def loop(self, name):                           # the animation for ever
        if ('loop', name) in self.c.labels:
            self.c.branch(2, ('loop', name)); return
        self.c.label(('loop', name))
        for xy, n in self.frames[name]:
            self.c.data.extend(self.copy(xy)); self.wait(n)
        self.c.branch(2, ('loop', name))

    def unlit_poll(self, symbol, targets):
        self.c.label('round')
        for j, (xy, n) in enumerate(self.frames['unlit']):
            self.c.data.extend(self.copy(xy) + bytes((0x73, n)))
            self.c.label(('frame', j)); self.c.data.append(0)
            for t, to in targets():
                self.c.data.extend(self.on_plate(t)); self.c.branch(3, to)
            self.c.branch(0x74, ('frame', j))
        self.c.branch(2, 'round')

    def stopped_static(self, symbol):
        self.loop('unlit')

    def phase(self, k, targets, stop):
        cycle = self.frames['cycle']; per = len(cycle) // 4
        for j, (xy, n) in enumerate(cycle[per * k:per * (k + 1)]):
            self.c.data.extend(self.copy(xy) + bytes((0x73, n)))
            self.c.label(('step', k, j)); self.c.data.append(0)
            self.c.branch(0x30, stop, FAIL_FLAG)            # another plate failed
            for t, to in targets():
                self.c.data.extend(self.on_plate(t)); self.c.branch(3, to)
            self.c.branch(0x74, ('step', k, j))

    def failed(self, k):
        # the game: animation 0 of symbol k, sound 3, 41 frames later animation 0 again (it restarts)
        self.c.data.extend(bytes((0xBD, 0x03, 0x00)))
        self.show(self.frames[f'fail{k}'], FAIL_RESTART)
        self.loop(f'fail{k}')

    def light(self, k):
        self.c.data.extend(self.copy(self.frames[f'lit{k}'][0][0]))

    def lit(self, k):
        self.loop(f'lit{k}')

    def lit_again(self, k):
        self.loop(f'lit{k}')


def rotate_cycle(data, map_id, directions):
    """Animation 2 of the pattern plate on map_id (local slot 364-256) shows
    Star, Moon, Water, Sun, 10 frames (24 steps) each, in all four direction
    streams. For each direction d in `directions`, turn that stream so it
    starts on symbol d (same frames, same length, rewritten in place)."""
    from entity_animation import parse_map_sprite_animations
    data = bytearray(data)
    anims = parse_map_sprite_animations(bytes(data), map_id, 364 - 256)
    if len(anims) < 3:
        raise ValueError('Pattern plate sprite has no changing animation on this map')
    for d in sorted(set(directions)):
        if not d:
            continue
        stream = anims[2].streams[d]
        if stream is None or len(stream.frames) != 40:
            raise ValueError('Pattern plate changing animation is not the game\'s 40-frame cycle')
        start = stream.offset
        frames = [bytes(data[start + i * 5:start + i * 5 + 5]) for i in range(40)]
        base = [bytes(data[anims[2].streams[0].offset + i * 5:anims[2].streams[0].offset + i * 5 + 5]) for i in range(40)]
        turned = base[10 * d:] + base[:10 * d]
        if frames != base and frames != turned:
            raise ValueError('Pattern plate changing animation differs from the game\'s')
        data[start:start + 200] = b''.join(turned)
    return data
