"""Edit AI (user 2026-10-11): a simple behaviour page per NPC / enemy / boss
class, built only from options the build already supports.

NPC: Movement 'Original' (the game's own routine, e.g. wandering) or 'Stand
still' (plays one chosen animation in place; a placed event's own Animation
setting still wins). Enemies and bosses keep their original AI routine and
get speed controls: animation & attack speed and movement speed (%).
New behaviour types (chase, shoot, patrol...) need new native code and are
not offered yet."""
import tkinter as tk
from tkinter import ttk


TYPES = {'strike': 'Strike (hits with the animation)', 'spawned': 'Spawned attack', 'misc': 'Misc behaviour'}
MOVES_BEFORE = {'none': 'Stay', 'toward': 'Move towards Alundra', 'away': 'Move away from Alundra'}
MOVES_DURING = {'none': 'Stay', 'toward': 'Move towards Alundra', 'away': 'Move away from Alundra',
                'lock': 'Lock trajectory (charge to where Alundra was, and past)'}
TRIGGERS = (('before_attack', 'Before attack'), ('after_attack', 'After attack'),
            ('before_anim', 'Before animation'), ('after_anim', 'After animation'))
DART = {'chance': 0, 'after_hits': 0, 'after_damage': 0, 'tiles': 3, 'speed': 4}   # On hit: dart away (0 = off)
NEW_ATTACK = {'name': 'Attack', 'type': 'strike', 'min_distance': 0, 'max_distance': 3, 'chance': 50, 'interval': 120,
              'animation': None, 'frames': 30, 'prepare_animation': None, 'stall_before': 0,
              'move_before': 'none', 'move_before_tiles': 0, 'move_before_speed': 100,
              'move_during': 'none', 'move_during_tiles': 0, 'move_during_speed': 100,
              'stall_while': False, 'always_first': False, 'whole_animation': False, 'move_from': None, 'move_to': None, 'spawn_class': None, 'spawn_frame': 0, 'spawn_x': 0, 'spawn_y': 0, 'spawn_z': 0, 'spawn_sound': None, 'prepare_sound': None}
INTS = {'min_distance': (0, 40), 'max_distance': (0, 40), 'chance': (1, 100), 'interval': (1, 3600), 'frames': (1, 600),
        'stall_before': (0, 600), 'move_before_tiles': (0, 12), 'move_before_speed': (25, 400),
        'move_during_tiles': (0, 12), 'move_during_speed': (25, 400), 'spawn_frame': (0, 600),
        'spawn_x': (-64, 64), 'spawn_y': (-64, 64), 'spawn_z': (-64, 64)}


STEPS = {'up': 'Move up', 'down': 'Move down', 'left': 'Move left', 'right': 'Move right',
         'toward': 'Move towards Alundra', 'away': 'Move away from Alundra', 'random': 'Move in a random direction',
         'face_player': 'Face Alundra', 'face': 'Face direction', 'wait': 'Wait (frames)', 'animation': 'Change animation',
         'lock_player': 'Lock Alundra movement', 'unlock_player': 'Unlock Alundra movement',
         'invisible': 'Go invisible', 'visible': 'Become visible',
         'hitbox_off': 'Turn hit box off', 'hitbox_on': 'Turn hit box on',
         'gravity_on': 'Gravity on', 'gravity_off': 'Gravity off', 'remove': 'Remove itself (end)'}
STEP_ARG = {'up': ('Tiles', None), 'down': ('Tiles', None), 'left': ('Tiles', None), 'right': ('Tiles', None),
            'toward': ('Tiles', None), 'away': ('Tiles', None), 'random': ('Tiles', None),
            'face': ('Direction', ['down', 'up', 'left', 'right']), 'wait': ('Frames', None), 'animation': ('Animation', 'anims')}


def step_text(st, anim_label=str):
    t = STEPS.get(st['kind'], st['kind'])
    if st['kind'] == 'animation': return f"{t}: {anim_label(st.get('value'))}"
    if 'value' in st: t += f" {st['value']}" + (' tiles' if st['kind'] in ('up', 'down', 'left', 'right', 'toward', 'away', 'random') else '')
    return t


def migrate_ai(ai):
    """Older saves had fixed 'strike' / 'projectile' entries: turn them into attacks."""
    ai = dict(ai or {}); out = {'mode': ai.get('mode', 'original'), 'route': list(ai.get('route') or []), 'routes': list(ai.get('routes') or []), 'on_hit_route': ai.get('on_hit_route'), 'chase': ai.get('chase', False), 'block_when_idle': ai.get('block_when_idle', False),
           'route_before_attack': ai.get('route_before_attack', any(a.get('always_first') for a in ai.get('attacks') or [])),
           'no_hit_stun': ai.get('no_hit_stun', False), 'stop_near_player': ai.get('stop_near_player', False), 'dart': dict(DART, **(ai.get('dart') or {}))}
    if 'death_animation' in ai: out['death_animation'] = ai['death_animation']
    attacks = list(ai.get('attacks') or [])
    for key, kind in (('strike', 'strike'), ('projectile', 'spawned')):
        old = ai.get(key)
        if old and old.get('enabled'):
            attacks.append(dict(NEW_ATTACK, name='Strike' if kind == 'strike' else 'Spawned attack', type=kind,
                                animation=old.get('animation'), frames=old.get('frames', 30),
                                prepare_animation=old.get('prepare_animation'), stall_before=old.get('stall_before', 0),
                                interval=old.get('interval', 120), stall_while=old.get('stall_while', kind == 'spawned'),
                                move_during='lock' if old.get('lock_trajectory') else 'none',
                                move_during_speed=old.get('attack_speed', 100), spawn_class=old.get('projectile_class')))
    out['attacks'] = [dict(NEW_ATTACK, **a) for a in attacks]
    return out


class AIEditorWindow:
    def __init__(self, editor, row):
        if row.get('kind') not in ('enemy', 'boss'):
            raise ValueError('Edit AI is for enemies and bosses')
        self.editor = editor; self.row = row; data = row.setdefault('data', {})
        self.window = tk.Toplevel(editor.db_window); self.window.title(row['name'] + ' — AI')
        self.window.geometry('560x420+60+40')
        body = ttk.Frame(self.window, padding=12); body.pack(fill='both', expand=True)
        ttk.Label(body, text=row['name'], font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        self.vars = {}
        if row['kind'] == 'npc':
            box = ttk.LabelFrame(body, text='Movement', padding=8); box.pack(fill='x', pady=8)
            mode = tk.StringVar(value=data.get('ai_movement', 'original')); self.vars['ai_movement'] = mode
            ttk.Radiobutton(box, text="Original (the game's own routine, e.g. wandering)", value='original', variable=mode).pack(anchor='w')
            ttk.Radiobutton(box, text='Stand still, playing one animation', value='stand', variable=mode).pack(anchor='w')
            row2 = ttk.Frame(box); row2.pack(anchor='w', padx=24, pady=4)
            ttk.Label(row2, text='Animation').pack(side='left')
            choices = self.animation_choices()
            self.idle = tk.StringVar()
            current = int(data.get('ai_idle_animation') or 0)
            self.idle.set(next((c for c in choices if c.split(' ')[0] == str(current)), choices[0] if choices else '0'))
            ttk.Combobox(row2, textvariable=self.idle, values=choices, state='readonly', width=30).pack(side='left', padx=6)
            ttk.Label(box, text='A placed event can still choose its own Animation; that one wins.', wraplength=500).pack(anchor='w', pady=(6, 0))
        else:
            self.window.geometry(f"1000x{min(1000, self.window.winfo_screenheight()-60)}+40+0")
            self.build_custom(body, data)
        buttons = ttk.Frame(body); buttons.pack(fill='x', side='bottom')
        ttk.Button(buttons, text='Done', command=lambda: editor.guard(self.close)).pack(side='right')
        self.window.protocol('WM_DELETE_WINDOW', lambda: editor.guard(self.close))

    def build_custom(self, body, data):
        """Custom enemy behaviour (user 2026-10-11/12), stored as data['custom_ai']:
        mode, block_when_idle, and a list of attacks. Each attack: type (strike /
        spawned / misc), when to use it (player distance range + % chance),
        movement before and during it, animations and timings."""
        ai = migrate_ai(data.get('custom_ai'))
        self.ai = ai; self.attacks = [dict(a) for a in ai['attacks']]; self.current = None
        self.anims = ['(none)'] + self.animation_choices()
        self.classes = ['(none)'] + [f"{r['name']} — {r['id']}" for r in self.editor.database.definitions
                                     if r['kind'] in ('object', 'enemy', 'unclassified') and r.get('source', {}).get('catalogue_index') is not None]
        top = ttk.LabelFrame(body, text='Behaviour', padding=8); top.pack(fill='x', pady=4)
        self.mode = tk.StringVar(value=ai['mode'])
        ttk.Radiobutton(top, text="Original (the game's own AI for this enemy)", value='original', variable=self.mode).pack(anchor='w')
        ttk.Radiobutton(top, text='Custom', value='custom', variable=self.mode).pack(anchor='w')
        self.chase = tk.BooleanVar(value=ai.get('chase', False))
        opts = ttk.Frame(top); opts.pack(anchor='w', pady=(4, 0))
        chase = ttk.Checkbutton(opts, text='Chases like a regular enemy', variable=self.chase); chase.pack(side='left')
        self.stop_near = tk.BooleanVar(value=ai.get('stop_near_player', False))
        ttk.Checkbutton(opts, text='Stop near Alundra', variable=self.stop_near).pack(side='left', padx=(24, 0))
        self.block = tk.BooleanVar(value=ai['block_when_idle'])
        block = ttk.Checkbutton(opts, text='Block attacks when not attacking', variable=self.block); block.pack(side='left', padx=(24, 0))
        # No hit stun: D = take the damage only (no hurt animation, no knockback); BizHawk 2026-10-22
        self.no_stun = tk.BooleanVar(value=ai.get('no_hit_stun', False))
        ttk.Checkbutton(opts, text='No hit stun', variable=self.no_stun).pack(side='left', padx=(24, 0))
        # Death animation (2026-10-24): played when HP reaches 0, before the enemy disappears
        from native_custom_ai import stock_death_animation
        death = ttk.Frame(top); death.pack(anchor='w', pady=(4, 0))
        ttk.Label(death, text='Death animation').pack(side='left')
        self.death = tk.StringVar(value=self.anim_label(ai['death_animation'] if 'death_animation' in ai else stock_death_animation(self.row)))
        ttk.Combobox(death, textvariable=self.death, values=self.anims, state='readonly', width=30).pack(side='left', padx=4)
        dart = ttk.Frame(top); dart.pack(anchor='w', pady=(4, 0)); self.dart = {}
        ttk.Label(dart, text='On hit: dart away').pack(side='left')
        for key, label, hi in (('chance', 'chance per hit %', 100), ('after_hits', 'or after hits', 255), ('after_damage', 'or after damage', 255),
                               ('tiles', 'distance (tiles)', 20), ('speed', 'speed (px/frame)', 6)):
            v = tk.StringVar(value=str(ai['dart'].get(key, DART[key]))); self.dart[key] = (v, hi)
            ttk.Label(dart, text='  ' + label).pack(side='left'); ttk.Spinbox(dart, textvariable=v, from_=0, to=hi, width=4).pack(side='left', padx=2)
        ttk.Label(top, text='(0 = off. Darting implies no hit stun; the triggers are checked between actions and every 10 cool-down frames.)').pack(anchor='w')
        # Attacks and move routes each on their own tab (user 2026-10-22)
        sections = ttk.Notebook(body); sections.pack(fill='both', expand=True, pady=4)
        attacks_tab = ttk.Frame(sections, padding=4); routes_tab = ttk.Frame(sections, padding=4)
        sections.add(attacks_tab, text='Attacks'); sections.add(routes_tab, text='Move routes')
        sections.bind('<<NotebookTabChanged>>', lambda _: hasattr(self, 'trig') and self.load_triggers())
        route_box = ttk.LabelFrame(routes_tab, text='Move routes', padding=8); route_box.pack(fill='both', expand=True, pady=4)
        self.routes = [dict(name=r.get('name') or f'Route {n + 1}', steps=[dict(x) for x in r.get('steps', [])],
                            triggers={k: dict(v) for k, v in (r.get('triggers') or {}).items()})
                       for n, r in enumerate(ai.get('routes') or [])] or [{'name': 'Main route', 'steps': [dict(r) for r in ai.get('route', [])], 'triggers': {}}]
        if ai.get('route_before_attack') and not self.routes[0]['triggers']:   # older 'Always do before attack'
            self.routes[0]['triggers']['before_attack'] = {'on': True, 'target': '(any)', 'chance': 100}
        self.route_tabs = ttk.Notebook(route_box); self.route_tabs.pack(fill='x')
        self.route_lists = []
        for r in self.routes: self.add_route_tab(r)
        self.route_tabs.bind('<<NotebookTabChanged>>', lambda _: self.route_tab_changed())
        tabbar = ttk.Frame(route_box); tabbar.pack(fill='x', pady=(4, 0))
        for label, fn in (('New route', self.new_route), ('Rename route', self.rename_route), ('Delete route', self.delete_route)):
            ttk.Button(tabbar, text=label, command=lambda f=fn: self.editor.guard(f)).pack(side='left', padx=(0, 4))
        ttk.Label(tabbar, text='On being hit:').pack(side='left', padx=(16, 4))
        self.on_hit = tk.StringVar(value=ai.get('on_hit_route') or '(keep going)')
        self.on_hit_combo = ttk.Combobox(tabbar, textvariable=self.on_hit, state='readonly', width=24); self.on_hit_combo.pack(side='left')
        self.refresh_on_hit()
        rf = ttk.Frame(route_box, padding=(0, 6, 0, 0)); rf.pack(fill='x')
        self.step_kind = tk.StringVar(value=list(STEPS.values())[0]); self.step_a = tk.StringVar(value='1')
        ttk.Label(rf, text='Step').grid(row=0, column=0, sticky='w')
        ttk.Combobox(rf, textvariable=self.step_kind, values=list(STEPS.values()), state='readonly', width=36).grid(row=0, column=1, columnspan=3, sticky='w', padx=4)
        self.step_a_label = ttk.Label(rf, text='Tiles'); self.step_a_label.grid(row=1, column=0, sticky='w', pady=2)
        self.step_a_box = ttk.Combobox(rf, textvariable=self.step_a, width=36); self.step_a_box.grid(row=1, column=1, columnspan=3, sticky='w', padx=4)
        bb = ttk.Frame(rf); bb.grid(row=3, column=0, columnspan=4, sticky='w', pady=4)
        for label, fn in (('Add step', self.add_step), ('Replace', self.replace_step), ('Remove', self.remove_step), ('Up', lambda: self.move_step(-1)), ('Down', lambda: self.move_step(1))):
            ttk.Button(bb, text=label, command=lambda f=fn: self.editor.guard(f)).pack(side='left', padx=(0, 4))
        self.step_kind.trace_add('write', lambda *_: self.step_kind_changed())
        self.step_kind_changed()
        # Route triggers (user 2026-10-27): run this route before/after an attack or animation, with a % chance
        tf = ttk.LabelFrame(route_box, text='Run this route', padding=6); tf.pack(fill='x', pady=(6, 0))
        self.trig = {}; self.trig_loading = False
        for r, (key, label) in enumerate(TRIGGERS):
            on, target, chance = tk.BooleanVar(), tk.StringVar(), tk.StringVar(value='100')
            ttk.Checkbutton(tf, text=label, variable=on).grid(row=r, column=0, sticky='w')
            box = ttk.Combobox(tf, textvariable=target, state='readonly', width=30); box.grid(row=r, column=1, padx=4, sticky='w')
            ttk.Label(tf, text='chance %').grid(row=r, column=2)
            ttk.Spinbox(tf, textvariable=chance, from_=1, to=100, width=4).grid(row=r, column=3, padx=4)
            self.trig[key] = (on, target, chance, box)
            for v in (on, target, chance): v.trace_add('write', lambda *_: self.store_triggers())
        self.route_tab_changed()
        attacks = ttk.LabelFrame(attacks_tab, text='Attacks', padding=8); attacks.pack(fill='both', expand=True, pady=4)
        left = ttk.Frame(attacks); left.pack(side='left', fill='y')
        self.attack_list = tk.Listbox(left, height=12, width=24, exportselection=False,
                                      background='#171b22', foreground='#e6e6e6', selectbackground='#3a4250', highlightthickness=0)
        self.attack_list.pack(fill='y', expand=True)
        self.attack_list.bind('<<ListboxSelect>>', lambda _: self.editor.guard(self.select_attack))
        self.attack_list.bind('<Delete>', lambda _: self.editor.guard(self.remove_attack))
        bar = ttk.Frame(left); bar.pack(fill='x', pady=4)
        ttk.Button(bar, text='Add', command=lambda: self.editor.guard(self.add_attack)).pack(side='left')
        ttk.Button(bar, text='Remove', command=lambda: self.editor.guard(self.remove_attack)).pack(side='left', padx=4)
        self.form = ttk.Frame(attacks, padding=(10, 0)); self.form.pack(side='left', fill='both', expand=True)
        self.f = {}
        def row(r, label, widget):
            ttk.Label(self.form, text=label).grid(row=r, column=0, sticky='w', pady=2)
            widget.grid(row=r, column=1, columnspan=3, sticky='w', padx=4)
        def var(key, kind=tk.StringVar):
            v = kind(); self.f[key] = v; return v
        def spin(key, lo, hi, w=7): return ttk.Spinbox(self.form, textvariable=var(key), from_=lo, to=hi, width=w)
        def combo(key, values, w=40): return ttk.Combobox(self.form, textvariable=var(key), values=values, state='readonly', width=w)
        row(0, 'Name', ttk.Entry(self.form, textvariable=var('name'), width=30))
        row(1, 'Type', combo('type', list(TYPES.values()), 40))
        rng = ttk.Frame(self.form)
        ttk.Spinbox(rng, textvariable=var('min_distance'), from_=0, to=40, width=5).pack(side='left')
        ttk.Label(rng, text=' to ').pack(side='left')
        ttk.Spinbox(rng, textvariable=var('max_distance'), from_=0, to=40, width=5).pack(side='left')
        ttk.Label(rng, text=' tiles from Alundra').pack(side='left')
        row(2, 'Use when', rng)
        row(3, 'Chance in range %', spin('chance', 1, 100))
        row(4, 'Every (frames)', spin('interval', 1, 3600))
        row(5, 'Attack animation', combo('animation', self.anims))
        row(6, 'Attack frames', spin('frames', 1, 600))
        # the stock Reaper plays its whole slash (hit ~117 frames in), BizHawk 2026-10-22
        ttk.Checkbutton(self.form, text='Play the whole animation (ignore frames)', variable=var('whole_animation', tk.BooleanVar)).grid(row=6, column=2, columnspan=2, sticky='w')
        row(7, 'Prepare animation', combo('prepare_animation', self.anims))
        row(8, 'Stall before (frames)', spin('stall_before', 0, 600))
        mb = ttk.Frame(self.form)
        ttk.Combobox(mb, textvariable=var('move_before'), values=list(MOVES_BEFORE.values()), state='readonly', width=30).pack(side='left')
        ttk.Spinbox(mb, textvariable=var('move_before_tiles'), from_=0, to=12, width=4).pack(side='left', padx=4); ttk.Label(mb, text='tiles').pack(side='left')
        row(9, 'Move before', mb)
        md = ttk.Frame(self.form)
        ttk.Combobox(md, textvariable=var('move_during'), values=list(MOVES_DURING.values()), state='readonly', width=48).pack(side='left')
        ttk.Spinbox(md, textvariable=var('move_during_tiles'), from_=0, to=12, width=4).pack(side='left', padx=4); ttk.Label(md, text='tiles').pack(side='left')
        ttk.Label(md, text='  from frame').pack(side='left'); ttk.Spinbox(md, textvariable=var('move_from'), from_=0, to=600, width=4).pack(side='left', padx=2)
        ttk.Label(md, text='to').pack(side='left'); ttk.Spinbox(md, textvariable=var('move_to'), from_=0, to=600, width=4).pack(side='left', padx=2)
        ttk.Label(md, text='(empty: the swing frames with an attack box)').pack(side='left')
        row(10, 'Move during', md)
        ttk.Checkbutton(self.form, text='Stall while attacking', variable=var('stall_while', tk.BooleanVar)).grid(row=11, column=0, columnspan=2, sticky='w', pady=2)
        self.spawn_label = ttk.Label(self.form, text='Spawned attack'); self.spawn_label.grid(row=12, column=0, sticky='w', pady=2)
        self.spawn_combo = combo('spawn_class', self.classes); self.spawn_combo.grid(row=12, column=1, columnspan=3, sticky='w', padx=4)
        sp = ttk.Frame(self.form)
        ttk.Label(sp, text='frame').pack(side='left'); ttk.Spinbox(sp, textvariable=var('spawn_frame'), from_=0, to=600, width=5).pack(side='left', padx=4)
        ttk.Label(sp, text='offset x').pack(side='left'); ttk.Spinbox(sp, textvariable=var('spawn_x'), from_=-64, to=64, width=5).pack(side='left', padx=4)
        ttk.Label(sp, text='y').pack(side='left'); ttk.Spinbox(sp, textvariable=var('spawn_y'), from_=-64, to=64, width=5).pack(side='left', padx=4)
        ttk.Label(sp, text='height').pack(side='left'); ttk.Spinbox(sp, textvariable=var('spawn_z'), from_=-64, to=64, width=5).pack(side='left', padx=4)
        self.spawn_label2 = ttk.Label(self.form, text='Spawn at'); self.spawn_label2.grid(row=13, column=0, sticky='w', pady=2)
        sp.grid(row=13, column=1, columnspan=3, sticky='w', padx=4); self.spawn_point = sp
        # pick the attack animation, the frame and the spawn point by looking at them (user 2026-10-18)
        ttk.Button(sp, text='Choose on the animation…', command=lambda: self.editor.guard(self.pick_spawn)).pack(side='left', padx=(10, 0))
        # sound played when the attack is spawned (user 2026-10-22)
        from sound_database_ui import sound_names
        self.sound_choices = {'(none)': None, **sound_names(self.editor)}
        snd = ttk.Frame(self.form); self.spawn_sound_row = snd
        ttk.Combobox(snd, textvariable=var('spawn_sound'), values=list(self.sound_choices), state='readonly', width=40).pack(side='left')
        def preview():
            sid = self.sound_choices.get(self.f['spawn_sound'].get())
            if sid is not None:
                from sound_database_ui import play_preview
                play_preview(self.editor, sid)
        ttk.Button(snd, text='▶', width=3, command=lambda: self.editor.guard(preview)).pack(side='left', padx=4)
        self.spawn_label3 = ttk.Label(self.form, text='Spawn sound'); self.spawn_label3.grid(row=14, column=0, sticky='w', pady=2)
        snd.grid(row=14, column=1, columnspan=3, sticky='w', padx=4)
        # the prepare animation's sound: its own, none, or a chosen one (user 2026-10-25)
        self.prepare_sound_choices = {"Animation's own": None, '(none)': -1, **{k: v for k, v in self.sound_choices.items() if v is not None}}
        ps = ttk.Frame(self.form)
        ttk.Combobox(ps, textvariable=var('prepare_sound'), values=list(self.prepare_sound_choices), state='readonly', width=40).pack(side='left')
        def preview_prepare():
            sid = self.prepare_sound_choices.get(self.f['prepare_sound'].get())
            if sid is not None and sid >= 0:
                from sound_database_ui import play_preview
                play_preview(self.editor, sid)
        ttk.Button(ps, text='▶', width=3, command=lambda: self.editor.guard(preview_prepare)).pack(side='left', padx=4)
        ttk.Label(self.form, text='Prepare sound').grid(row=7, column=2, sticky='w', padx=(8, 0))
        ps.grid(row=7, column=3, columnspan=2, sticky='w', padx=4)
        ttk.Button(self.form, text='Choose…', command=lambda: self.editor.guard(self.pick_animation)).grid(row=5, column=4, sticky='w')
        self.f['type'].trace_add('write', lambda *_: self.type_changed())
        self.f['name'].trace_add('write', lambda *_: self.rename_current())
        for a in self.attacks: self.attack_list.insert('end', a['name'])
        if self.attacks: self.attack_list.selection_set(0); self.select_attack()
        else: self.load_form(None)
        custom_parts = [block, route_box, attacks]
        def shade(*_):
            state = 'normal' if self.mode.get() == 'custom' else 'disabled'
            def walk(widget):
                for child in widget.winfo_children():
                    try:
                        if isinstance(child, ttk.Combobox): child.configure(state='readonly' if state == 'normal' else 'disabled')
                        elif isinstance(child, ttk.Label): child.configure(foreground='#e6e6e6' if state == 'normal' else '#6b7280')
                        else: child.configure(state=state)
                    except Exception: pass
                    walk(child)
            block.configure(state=state); chase.configure(state=state); walk(attacks); walk(route_box)
            if state == 'normal': self.type_changed()
        self.mode.trace_add('write', shade); shade()

    def _anim_index(self, key='animation'):
        text = self.f[key].get().split(' ')[0]
        return int(text) if text.isdigit() else None

    def pick_animation(self):
        """Attack animation from the animation list with its frames shown."""
        from spawn_attack_picker import AttackPicker
        def done(v):
            self.f['animation'].set(self.anim_label(v['animation']))
            self.f['frames'].set(str(max(1, sum(f.ticks for f in self._clip_frames(v['animation'])))))
        AttackPicker(self.editor, self.window, self.row, dict(animation=self._anim_index() or 0), done)

    def _clip_frames(self, animation):
        try:
            import animation_preview as A
            from native_spawn_attacks import class_maps
            from stock_donors import source_for
            cat = self.row.get('source', {}).get('catalogue_index')
            for m in class_maps(self.row):
                try:return A.load_animation(source_for(self.editor.session, m), m, cat, animation, 0).frames
                except Exception:continue
        except Exception:pass
        return ()

    def pick_spawn(self):
        """Spawn frame and point: click a frame of the attack animation, then the spot."""
        from spawn_attack_picker import AttackPicker
        anim = self._anim_index()
        if anim is None:raise ValueError('Choose the attack animation first')
        frames = self._clip_frames(anim)
        # the stored spawn frame counts game frames from the start of the animation
        ticks = int(self.f['spawn_frame'].get() or 0); index = 0; total = 0
        for i, f in enumerate(frames):
            if total > ticks:break
            index = i; total += f.ticks
        current = dict(animation=anim, frame=index, dx=self.f['spawn_x'].get() or 0, dy=self.f['spawn_y'].get() or 0, dz=self.f['spawn_z'].get() or 0)
        def done(v):
            clamp = lambda n: max(-64, min(64, int(n)))
            self.f['spawn_frame'].set(str(v['ticks']))
            for key, src in (('spawn_x', 'dx'), ('spawn_y', 'dy'), ('spawn_z', 'dz')):self.f[key].set(str(clamp(v[src])))
            if v['animation'] != anim:self.f['animation'].set(self.anim_label(v['animation']))
        AttackPicker(self.editor, self.window, self.row, current, done)

    # -- attack list ------------------------------------------------------
    def anim_label(self, value):
        return next((x for x in self.anims if x.split(' ')[0] == str(value)), '(none)')

    def load_form(self, a):
        self.loading = True
        try:
            a = dict(NEW_ATTACK, **(a or {}))
            for key, v in self.f.items():
                value = a.get(key)
                if key in ('animation', 'prepare_animation'): value = self.anim_label(value)
                elif key == 'type': value = TYPES.get(value, TYPES['strike'])
                elif key == 'move_before': value = MOVES_BEFORE.get(value, MOVES_BEFORE['none'])
                elif key == 'move_during': value = MOVES_DURING.get(value, MOVES_DURING['none'])
                elif key == 'spawn_class': value = next((c for c in self.classes if c.endswith('— ' + str(value))), '(none)')
                elif key == 'spawn_sound': value = next((k for k, s in self.sound_choices.items() if s == value), '(none)')
                elif key == 'prepare_sound': value = next((k for k, s in self.prepare_sound_choices.items() if s == value), "Animation's own")
                elif key in ('move_from', 'move_to'): value = '' if value is None else value
                v.set(value if not isinstance(v, tk.BooleanVar) else bool(value))
        finally:
            self.loading = False
        self.type_changed()

    def read_form(self):
        out = {}
        for key, v in self.f.items():
            value = v.get()
            if key in ('animation', 'prepare_animation'): value = None if value in ('(none)', '') else int(value.split(' ')[0])
            elif key == 'type': value = next(k for k, t in TYPES.items() if t == value)
            elif key == 'move_before': value = next(k for k, t in MOVES_BEFORE.items() if t == value)
            elif key == 'move_during': value = next(k for k, t in MOVES_DURING.items() if t == value)
            elif key == 'spawn_class': value = None if value in ('(none)', '') else value.rsplit('— ', 1)[-1]
            elif key == 'spawn_sound': value = self.sound_choices.get(value)
            elif key == 'prepare_sound': value = self.prepare_sound_choices.get(value)
            elif key in ('move_from', 'move_to'):
                try: value = None if str(value).strip() == '' else int(value)
                except ValueError: raise ValueError('Move during: from/to frame must be a whole number or empty')
                if value is not None and not 0 <= value <= 600: raise ValueError('Move during: from/to frame must be 0-600')
            elif key in INTS:
                lo, hi = INTS[key]
                try: value = int(value)
                except ValueError: raise ValueError(f"{key.replace('_', ' ').title()} must be a whole number")
                if not lo <= value <= hi: raise ValueError(f"{key.replace('_', ' ').title()} must be {lo}-{hi}")
            out[key] = value
        if out['min_distance'] > out['max_distance']: raise ValueError('Use when: the first distance must not be larger than the second')
        return out

    def store_current(self):
        if self.current is not None and self.current < len(self.attacks):
            self.attacks[self.current] = self.read_form()

    def select_attack(self):
        chosen = self.attack_list.curselection()
        if not chosen: return
        if self.current is not None and chosen[0] != self.current: self.store_current()
        self.current = chosen[0]; self.load_form(self.attacks[self.current])

    def add_attack(self):
        self.store_current()
        a = dict(NEW_ATTACK, name=f'Attack {len(self.attacks) + 1}')
        self.attacks.append(a); self.attack_list.insert('end', a['name'])
        self.attack_list.selection_clear(0, 'end'); self.attack_list.selection_set('end')
        self.current = len(self.attacks) - 1; self.load_form(a)

    def remove_attack(self):
        if self.current is None: return
        self.attacks.pop(self.current); self.attack_list.delete(self.current); self.current = None
        if self.attacks: self.attack_list.selection_set(0); self.select_attack()
        else: self.load_form(None)

    def rename_current(self):
        if getattr(self, 'loading', False) or self.current is None: return
        self.attack_list.delete(self.current); self.attack_list.insert(self.current, self.f['name'].get())
        self.attack_list.selection_set(self.current)

    def type_changed(self):
        spawned = self.f['type'].get() == TYPES['spawned']
        state = 'normal' if spawned and self.mode.get() == 'custom' else 'disabled'
        for w in (self.spawn_label, self.spawn_label2, self.spawn_label3): w.configure(foreground='#e6e6e6' if state == 'normal' else '#6b7280')
        self.spawn_combo.configure(state='readonly' if state == 'normal' else 'disabled')
        for child in self.spawn_sound_row.winfo_children():
            child.configure(state=('readonly' if isinstance(child, ttk.Combobox) else 'normal') if state == 'normal' else 'disabled')
        for child in self.spawn_point.winfo_children():
            try: child.configure(foreground='#e6e6e6' if state == 'normal' else '#6b7280') if isinstance(child, ttk.Label) else child.configure(state=state)
            except Exception: pass

    # -- move routes (tabs) ---------------------------------------------------
    def add_route_tab(self, route):
        frame = ttk.Frame(self.route_tabs, padding=4)
        lb = tk.Listbox(frame, height=6, width=60, exportselection=False,
                        background='#171b22', foreground='#e6e6e6', selectbackground='#3a4250', highlightthickness=0)
        lb.pack(fill='x')
        for st in route['steps']: lb.insert('end', step_text(st, self.anim_label))
        lb.bind('<<ListboxSelect>>', lambda _: self.editor.guard(self.pick_step))
        lb.bind('<Delete>', lambda _: self.editor.guard(self.remove_step))
        self.route_tabs.add(frame, text=route['name']); self.route_lists.append(lb)

    def route_tab_changed(self):
        try: i = self.route_tabs.index(self.route_tabs.select())
        except Exception: i = 0
        self.route = self.routes[i]['steps']; self.route_list = self.route_lists[i]
        if hasattr(self, 'trig'): self.load_triggers()

    def trigger_targets(self, key):
        if key.endswith('_anim'): return [a for a in self.anims if a != '(none)']
        return ['(any)'] + [a['name'] for a in self.attacks]

    def load_triggers(self):
        self.trig_loading = True
        try:
            route = self.routes[self.route_tabs.index(self.route_tabs.select())]
            for key, (on, target, chance, box) in self.trig.items():
                t = route.setdefault('triggers', {}).get(key) or {}
                values = self.trigger_targets(key); box.configure(values=values)
                cur = self.anim_label(t['target']) if key.endswith('_anim') and t.get('target') is not None else t.get('target')
                on.set(bool(t.get('on'))); target.set(cur if cur in values else (values[0] if values else ''))
                chance.set(str(t.get('chance', 100)))
        finally: self.trig_loading = False

    def store_triggers(self):
        if self.trig_loading: return
        try: route = self.routes[self.route_tabs.index(self.route_tabs.select())]
        except Exception: return
        out = {}
        for key, (on, target, chance, _) in self.trig.items():
            tv = target.get()
            if key.endswith('_anim'): tv = int(tv.split(' ')[0]) if tv and tv[0].isdigit() else None
            try: c = max(1, min(100, int(chance.get())))
            except ValueError: c = 100
            out[key] = {'on': on.get() and tv is not None, 'target': tv, 'chance': c}
        route['triggers'] = out

    def refresh_on_hit(self):
        names = ['(keep going)'] + [r['name'] for r in self.routes[1:]]
        self.on_hit_combo.configure(values=names)
        if self.on_hit.get() not in names: self.on_hit.set('(keep going)')

    def new_route(self):
        from tkinter import simpledialog
        name = simpledialog.askstring('New route', 'Route name:', parent=self.window, initialvalue=f'Route {len(self.routes) + 1}')
        if not name: return
        if any(r['name'] == name for r in self.routes): raise ValueError('Route names must be different')
        r = {'name': name, 'steps': []}; self.routes.append(r); self.add_route_tab(r)
        self.route_tabs.select(len(self.routes) - 1); self.route_tab_changed(); self.refresh_on_hit()

    def rename_route(self):
        from tkinter import simpledialog
        i = self.route_tabs.index(self.route_tabs.select())
        name = simpledialog.askstring('Rename route', 'Route name:', parent=self.window, initialvalue=self.routes[i]['name'])
        if not name or name == self.routes[i]['name']: return
        if any(r['name'] == name for r in self.routes): raise ValueError('Route names must be different')
        if self.on_hit.get() == self.routes[i]['name']: self.on_hit.set(name)
        self.routes[i]['name'] = name; self.route_tabs.tab(i, text=name); self.refresh_on_hit()

    def delete_route(self):
        i = self.route_tabs.index(self.route_tabs.select())
        if i == 0: raise ValueError('The Main route is always there; clear its steps instead')
        if self.on_hit.get() == self.routes[i]['name']: self.on_hit.set('(keep going)')
        self.route_tabs.forget(i); self.routes.pop(i); self.route_lists.pop(i)
        self.route_tabs.select(0); self.route_tab_changed(); self.refresh_on_hit()

    # -- move route -------------------------------------------------------
    def step_kind_changed(self):
        kind = next(k for k, t in STEPS.items() if t == self.step_kind.get())
        label, values = STEP_ARG.get(kind, (None, None))
        self.step_a_label.configure(text=label or '')
        if label is None: self.step_a_box.grid_remove()
        else:
            self.step_a_box.grid()
            self.step_a_box.configure(values=self.anims[1:] if values == 'anims' else (values or []))
            if values == 'anims' and self.step_a.get() not in self.anims: self.step_a.set(self.anims[1] if len(self.anims) > 1 else '0')
            elif values not in (None, 'anims') and self.step_a.get() not in values: self.step_a.set(values[0])
            elif values is None and not self.step_a.get().lstrip('-').isdigit(): self.step_a.set('1')

    def read_step(self):
        kind = next(k for k, t in STEPS.items() if t == self.step_kind.get())
        step = {'kind': kind}
        label, values = STEP_ARG.get(kind, (None, None))
        if label is not None:
            v = self.step_a.get()
            if values == 'anims': step['value'] = int(v.split(' ')[0])
            elif values: step['value'] = v
            else:
                try: step['value'] = int(v)
                except ValueError: raise ValueError(f'{label} must be a whole number')
                if not 0 <= step['value'] <= 3600: raise ValueError(f'{label} must be 0-3600')
        return step

    def add_step(self):
        st = self.read_step(); self.route.append(st); self.route_list.insert('end', step_text(st, self.anim_label))

    def replace_step(self):
        sel = self.route_list.curselection()
        if not sel: return
        i = sel[0]; st = self.read_step(); self.route[i] = st
        self.route_list.delete(i); self.route_list.insert(i, step_text(st, self.anim_label)); self.route_list.selection_set(i)

    def remove_step(self):
        sel = self.route_list.curselection()
        if not sel: return
        self.route.pop(sel[0]); self.route_list.delete(sel[0])

    def move_step(self, d):
        sel = self.route_list.curselection()
        if not sel: return
        i = sel[0]; j = i + d
        if not 0 <= j < len(self.route): return
        self.route[i], self.route[j] = self.route[j], self.route[i]
        for k in (i, j): self.route_list.delete(k); self.route_list.insert(k, step_text(self.route[k], self.anim_label))
        self.route_list.selection_set(j)

    def pick_step(self):
        sel = self.route_list.curselection()
        if not sel: return
        st = self.route[sel[0]]; self.step_kind.set(STEPS[st['kind']])
        if 'value' in st:
            label, values = STEP_ARG[st['kind']]
            self.step_a.set(self.anim_label(st['value']) if values == 'anims' else str(st['value']))

    def read_custom(self):
        self.store_current()
        for a in self.attacks:
            if a['type'] != 'misc' and a['animation'] is None:
                raise ValueError(f"{a['name']}: choose an attack animation")
            if a['type'] == 'spawned' and not a.get('spawn_class'):
                raise ValueError(f"{a['name']}: choose what the spawned attack creates")
        return {'mode': self.mode.get(), 'chase': self.chase.get(), 'block_when_idle': self.block.get(), 'route': self.routes[0]['steps'], 'routes': self.routes, 'route_before_attack': False,
                'on_hit_route': None if self.on_hit.get() == '(keep going)' else self.on_hit.get(), 'attacks': self.attacks,
                'no_hit_stun': self.no_stun.get(), 'stop_near_player': self.stop_near.get(), 'dart': self.read_dart(),
                'death_animation': None if self.death.get() in ('(none)', '') else int(self.death.get().split(' ')[0])}

    def read_dart(self):
        out = {}
        for key, (v, hi) in self.dart.items():
            try: value = float(v.get()) if key == 'speed' else int(v.get())
            except ValueError: raise ValueError(f"On hit: dart away: {key.replace('_', ' ')} must be a number")
            if not 0 <= value <= hi: raise ValueError(f"On hit: dart away: {key.replace('_', ' ')} must be 0-{hi}")
            out[key] = value
        if (out['chance'] or out['after_hits'] or out['after_damage']) and not (out['tiles'] and out['speed']):
            raise ValueError('On hit: dart away needs a distance and a speed')
        return out

    def animation_choices(self):
        try:
            from animation_preview import available_animations
            from animation_names import auto_names, display_name
            source = self.row.get('source', {}); maps = source.get('observed_maps') or [self.editor.current_map]
            choices = available_animations(self.editor.session, maps[0], source['catalogue_index'])
            auto = auto_names(self.editor.session, self.row, choices)
            return [display_name(self.editor.database.document, self.row, auto, r['index']) for r in choices]
        except Exception:
            return [str(i) for i in range(8)]

    def close(self):
        # The Database autosave (db_apply) replaces the stored class with a copy
        # while this window is open, so write into the current stored row.
        try:
            current = self.editor.database.get(self.row['id'])
        except Exception:
            current = None
        if current is not None:
            self.row = current
        data = self.row.setdefault('data', {})
        for key, var in self.vars.items():
            value = var.get()
            if key != 'ai_movement':
                value = int(value)
                if not 25 <= value <= 400:
                    raise ValueError('Speed must be 25-400 %')
            data[key] = value
        if hasattr(self, 'attack_list'):
            data['custom_ai'] = self.read_custom()
        if hasattr(self, 'idle'):
            data['ai_idle_animation'] = int(self.idle.get().split(' ')[0] or 0)
        self.editor.dirty = True
        try:
            self.editor.db_refresh(self.row['id'])
        except Exception:
            pass
        self.editor.status.set(f"AI settings for {self.row['name']} saved in the mod; used when you build.")
        self.window.destroy()
