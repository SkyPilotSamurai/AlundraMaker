"""Database: everything an enemy/boss spawns, as attacks, plus new attacks.

* Spawned attacks - what the class's own AI spawns (native_spawn_attacks), with
  when it happens and the spawned class's damage (stored on that class).
* New attacks - spawn any class on a chosen frame of an animation of this
  class (data['spawn_attacks']: animation, frame; frame 0 = the animation
  starts, installed by native_animation_spawns; later frames by
  native_frame_spawns).
"""
import tkinter as tk
from tkinter import ttk


class SpawnAttacksPanel:
    def __init__(self, parent, editor):
        self.editor = editor
        self.frame = ttk.LabelFrame(parent, text='Spawned attacks', padding=(6, 2, 6, 4)); self.frame.pack(fill='x', pady=3)
        self.native_host = ttk.Frame(self.frame); self.native_host.pack(fill='x')
        self.ai_host = ttk.Frame(self.frame); self.ai_host.pack(fill='x')   # Edit AI spawned attacks
        self.new_host = ttk.Frame(self.frame); self.new_host.pack(fill='x')
        bottom = ttk.Frame(self.frame); bottom.pack(fill='x'); self.bottom = bottom   # Add new attack: below every attack (user 2026-10-18)
        ttk.Button(bottom, text='Add new attack', command=self.add_row).pack(side='right')
        self.rows = []; self.damage = {}; self.attributes = {}; self.row_id = None; self.ai_rows = []

    # -- helpers -------------------------------------------------------------
    def memo(self, kind, row, work):
        """Remember per-class results for this game data (user 2026-10-27)."""
        session = getattr(self.editor, 'session', None)
        cache = self.editor.__dict__.setdefault('spawn_panel_cache', {})
        key = (kind, id(session), getattr(session, 'data_version', None), repr(row.get('source')), repr(row.get('data', {}).get('custom_ai')))
        if key not in cache: cache[key] = work()
        return cache[key]

    def classes(self):
        out = []
        for d in self.editor.database.definitions:
            cat = d.get('source', {}).get('catalogue_index')
            if d.get('kind') in ('enemy', 'boss', 'object', 'unclassified') and type(cat) is int and not d.get('clone_of') and not d.get('name', '').startswith('Unused source definition'):   # Misc too: boss parts such as Melzas Double (user 2026-10-27)
                out.append((f"{d['name']} (class {cat})", d['id']))
        return sorted(out)

    def source_choices(self, row):
        """Spawn from: only what this boss's own fight creates (its parts, such as Melzas's
        doubles; ContentDatabase.BOSS_PARTS) (user 2026-10-27)."""
        from content_database import ContentDatabase
        parts = ContentDatabase.BOSS_PARTS.get(row.get('source', {}).get('catalogue_index'), ())
        by_id = {d['id']: d for d in self.editor.database.definitions}
        return [(label, key) for label, key in self.choices
                if by_id.get(key, {}).get('source', {}).get('catalogue_index') in parts]

    def animation_count(self, row):
        try:
            from class_looks import _sprite_bounds
            from entity_animation import parse_sprite_animation_record
            from native_spawn_attacks import class_maps
            cat = row.get('source', {}).get('catalogue_index')
            data = self.editor.session.data
            for m in class_maps(row):
                try:
                    start, end, sh = _sprite_bounds(data, m)
                    return len(parse_sprite_animation_record(data, start, end, cat & 255, sh[3], sh[4]))
                except Exception:
                    continue
        except Exception:
            pass
        return 64

    def frame_counts(self, row):
        """Frames of each animation of the class (most of its four directions)."""
        try:
            import animation_preview as A
            from native_spawn_attacks import class_maps
            from stock_donors import source_for
            cat = row.get('source', {}).get('catalogue_index')
            for m in class_maps(row):
                try:
                    found = A.available_animations(source_for(self.editor.session, m), m, cat)
                except Exception:
                    continue
                if found:
                    return {a['index']: max(1, max(a['direction_frames'])) for a in found}
        except Exception:
            pass
        return {}

    def set_icon(self, body, klass):
        """Mini picture of the spawned class left of the attack (user 2026-10-27)."""
        # decoded on the editor's shared icon thread, shown on the Tk thread (laggy before, user 2026-10-27)
        label = body.outer.summary
        if hasattr(self.editor, 'db_icon_async'):
            self.editor.db_icon_async(label, klass)

    def attack_line(self, host, text, open_=False, remove=None):
        """One attack: its summary with an Edit button; Edit shows its options
        below (user 2026-10-18). Returns the options frame (hidden until Edit)."""
        outer = ttk.Frame(host); outer.pack(fill='x', pady=(1, 1))
        line = ttk.Frame(outer); line.pack(fill='x')
        # a blank icon-sized picture from the start, so the line keeps its size when
        # the class icon arrives (no flicker, user 2026-10-27)
        if getattr(self, '_blank', None) is None:
            self._blank = tk.PhotoImage(master=host, width=24, height=24)
        label = ttk.Label(line, text=text, image=self._blank, compound='left'); label.pack(side='left')
        label.placeholder = self._blank
        body = ttk.Frame(outer, padding=(16, 2, 0, 4))
        def toggle():
            if body.winfo_ismapped():body.pack_forget();button.configure(text='Edit')
            else:body.pack(fill='x');button.configure(text='Close')
        if remove is not None:
            ttk.Button(line, text='Remove', command=remove).pack(side='right', padx=(4, 0))
        button = ttk.Button(line, text='Edit', command=toggle); button.pack(side='right')
        if open_:toggle()
        outer.summary = label; outer.body = body
        body.outer = outer
        return body

    def name_box(self, body, value, summary):
        """Name entry at the top of an attack's options; the summary follows it."""
        line = ttk.Frame(body); line.pack(fill='x', pady=(0, 2))
        ttk.Label(line, text='Name').pack(side='left')
        var = tk.StringVar(value=value or '')
        ttk.Entry(line, textvariable=var, width=30).pack(side='left', padx=4)
        var.trace_add('write', lambda *_: summary())
        return var

    # -- load / apply ----------------------------------------------------------
    def load(self, row):
        self.row_id = row.get('id')
        # build out of view, then show once: one layout pass instead of one per line (less flicker)
        for host in (self.native_host, self.ai_host, self.new_host):
            host.pack_forget()
        try:
            self._load(row)
        finally:
            for host in (self.native_host, self.ai_host, self.new_host):
                host.pack(fill='x', before=self.bottom)

    def _load(self, row):
        for host in (self.native_host, self.new_host, self.ai_host):
            for child in host.winfo_children():
                child.destroy()
            # Tk keeps an emptied frame at its old size: shrink it, children regrow it (user 2026-10-27)
            host.configure(width=1, height=1)
        self.rows = []; self.damage = {}; self.attributes = {}; self.native_names = {}
        saved_names = row.get('data', {}).get('spawn_attack_names') or {}
        spawns = []
        session = getattr(self.editor, 'session', None)
        if session is not None:
            from native_spawn_attacks import class_spawns
            try:
                spawns = self.memo('spawns', row, lambda: class_spawns(session.data, row))
            except Exception:
                spawns = []
        by_catalogue = {}
        for d in self.editor.database.definitions:
            cat = d.get('source', {}).get('catalogue_index')
            if type(cat) is int and not d.get('clone_of'):
                by_catalogue.setdefault(cat, d)
        for i, spawn in enumerate(spawns):
            target = by_catalogue.get(spawn['catalogue'])
            name = target['name'] if target else f"Class {spawn['catalogue']}"
            default = f"{spawn['when'].capitalize()}: {name} (class {spawn['catalogue']})"
            body = self.attack_line(self.native_host, default)
            self.set_icon(body, target)
            holder = {}
            def summary(body=body, default=default, holder=holder):
                given = holder['var'].get().strip() if 'var' in holder else ''
                body.outer.summary.configure(text=f'{given} · {default}' if given else default)
            holder['var'] = self.native_names[str(i)] = self.name_box(body, saved_names.get(str(i)), summary)
            summary()
            body = ttk.Frame(body); body.pack(fill='x')
            attacks = (target or {}).get('data', {}).get('attacks') or []
            if attacks and target['id'] not in self.damage:
                from attack_attributes import attribute_box
                var = tk.StringVar(value=str(attacks[0]['power'])); self.damage[target['id']] = var
                attribute = tk.StringVar(); self.attributes[target['id']] = attribute
                ttk.Label(body, text='Damage').pack(side='left')
                ttk.Spinbox(body, from_=0, to=255, textvariable=var, width=6).pack(side='left', padx=4)
                attribute_box(body, attribute, attacks[0].get('attribute', 0), width=22).pack(side='left', padx=4)
                if len(attacks) > 1:
                    ttk.Label(body, text=f'(+{len(attacks) - 1} more on its own class)', foreground='#8c99ab').pack(side='left', padx=4)
            elif not attacks:
                ttk.Label(body, text='No damage of its own.', foreground='#8c99ab').pack(side='left')
            ttk.Label(body, text='When it happens and what it spawns are part of the game\'s own AI; '
                      'add a new attack below for one you can time and place.', foreground='#8c99ab').pack(side='left', padx=8)
        self.load_ai_spawns(row, by_catalogue)
        self.choices = self.classes(); self.sources = self.source_choices(row); self.max_animation = max(1, self.memo('anims', row, lambda: self.animation_count(row))) - 1
        self.frames = self.memo('frames', row, lambda: self.frame_counts(row))
        for spawn in row.get('data', {}).get('spawn_attacks', []) or []:
            self.add_row(spawn)

    def load_ai_spawns(self, row, by_catalogue):
        """Every spawned attack of the class's Edit AI: what it shoots, on which
        frame of the attack and where (pixels from the enemy), plus its damage."""
        self.ai_rows = []
        ai = row.get('data', {}).get('custom_ai') or {}
        if ai.get('mode', 'original') != 'custom':
            return
        by_id = {d['id']: d for d in self.editor.database.definitions}
        for i, attack in enumerate(ai.get('attacks') or []):
            if attack.get('type') != 'spawned' or not attack.get('spawn_class'):
                continue
            target = by_id.get(attack['spawn_class'])
            shoots = target['name'] if target else attack['spawn_class']
            body = self.attack_line(self.ai_host, '')
            self.set_icon(body, target)
            holder = {}
            def summary(body=body, shoots=shoots, holder=holder, attack=attack):
                given = holder['var'].get().strip() if 'var' in holder else attack.get('name')
                body.outer.summary.configure(text=f"Edit AI · {given or 'Spawned attack'}: {shoots}")
            holder['var'] = self.name_box(body, attack.get('name'), summary)
            summary()
            second = ttk.Frame(body); second.pack(fill='x')
            vars_ = {}
            for label, key, lo, hi in (('Frame', 'spawn_frame', 0, 600), ('X', 'spawn_x', -64, 64), ('Y', 'spawn_y', -64, 64), ('Height', 'spawn_z', -64, 64)):
                ttk.Label(second, text=label).pack(side='left', padx=(8 if key != 'spawn_frame' else 0, 2))
                v = tk.StringVar(value=str(attack.get(key, 0))); vars_[key] = v
                ttk.Spinbox(second, from_=lo, to=hi, increment=1 if key == 'spawn_frame' else 4, textvariable=v, width=5).pack(side='left')
            def pick_ai(attack=attack, vars_=vars_):
                from spawn_attack_picker import AttackPicker
                anim = attack.get('animation')
                if anim is None:raise ValueError('Give this attack an animation in Edit AI first')
                def done(v):
                    vars_['spawn_frame'].set(str(v['ticks']))
                    for key, src in (('spawn_x', 'dx'), ('spawn_y', 'dy'), ('spawn_z', 'dz')):vars_[key].set(str(max(-64, min(64, v[src]))))
                AttackPicker(self.editor, self.frame.winfo_toplevel(), self.editor.database.get(self.row_id),
                             dict(animation=anim, frame=0, dx=vars_['spawn_x'].get(), dy=vars_['spawn_y'].get(), dz=vars_['spawn_z'].get()), done)
            ttk.Button(second, text='Choose on the animation…', command=lambda f=pick_ai: self.editor.guard(f)).pack(side='left', padx=8)
            attacks = (target or {}).get('data', {}).get('attacks') or []
            if attacks and target['id'] not in self.damage:
                from attack_attributes import attribute_box
                dv = tk.StringVar(value=str(attacks[0]['power'])); self.damage[target['id']] = dv
                av = tk.StringVar(); self.attributes[target['id']] = av
                third = ttk.Frame(body); third.pack(fill='x', pady=(2, 0))
                ttk.Label(third, text='Damage').pack(side='left')
                ttk.Spinbox(third, from_=0, to=255, textvariable=dv, width=6).pack(side='left', padx=4)
                attribute_box(third, av, attacks[0].get('attribute', 0), width=22).pack(side='left', padx=4)
            self.ai_rows.append((i, vars_, holder['var']))

    def add_row(self, spawn=None):
        spawn = spawn or {}
        holder = {}
        body = self.attack_line(self.new_host, 'New attack', open_=not spawn, remove=lambda: holder['remove']())
        frame = body.outer
        name = self.name_box(body, spawn.get('name'), lambda: summary())
        # Layout (user 2026-10-27): where it comes from first, then that actor's animation and
        # frame (the picker shows the chosen actor's own animations), then what it spawns.
        ATTACKER = 'This attacker'
        sources = list(getattr(self, 'sources', []))
        saved = next(((label, key) for label, key in self.choices if key == spawn.get('from_class_id')), None)
        if saved and saved not in sources: sources.append(saved)   # never drop a saved choice
        source = tk.StringVar(value=saved[0] if saved else ATTACKER)
        from_random = tk.BooleanVar(value=bool(spawn.get('from_random')))
        chance = tk.StringVar(value=str(spawn.get('chance', 100)))   # % of the animation starts that spawn
        cooldown = tk.StringVar(value=str(spawn.get('cooldown', 0)))
        animation = tk.StringVar(value=str(spawn.get('animation', 0)))
        frame_var = tk.StringVar(value=str(spawn.get('frame', 0)))
        names = [label for label, _ in self.choices]
        current = next((label for label, key in self.choices if key == spawn.get('class_id')), names[0] if names else '')
        klass = tk.StringVar(value=current)
        offsets = [tk.StringVar(value=str(spawn.get(k, 0))) for k in ('dx', 'dy', 'dz')]

        origin = ttk.Frame(body); origin.pack(fill='x', pady=(2, 0))
        ttk.Label(origin, text='Spawn from').pack(side='left')
        ttk.Combobox(origin, textvariable=source, values=[ATTACKER] + [label for label, _ in sources], state='readonly', width=30).pack(side='left', padx=(2, 8))
        ttk.Checkbutton(origin, text='Random', variable=from_random).pack(side='left')
        ttk.Label(origin, text='Chance').pack(side='left', padx=(12, 2))
        chance_box = ttk.Spinbox(origin, from_=1, to=100, textvariable=chance, width=4); chance_box.pack(side='left')
        def chance_state(*_):   # Chance is part of Random: greyed until it is ticked (user 2026-10-27)
            chance_box.configure(state='normal' if from_random.get() else 'disabled')
        from_random.trace_add('write', chance_state); chance_state()
        ttk.Label(origin, text='%').pack(side='left', padx=(1, 0))

        timing = ttk.Frame(body); timing.pack(fill='x', pady=(2, 0))
        ttk.Label(timing, text='Animation').pack(side='left')
        animation_box = ttk.Spinbox(timing, from_=0, to=63, textvariable=animation, width=4); animation_box.pack(side='left', padx=(2, 8))
        ttk.Label(timing, text='frame').pack(side='left')
        frame_box = ttk.Spinbox(timing, from_=0, to=255, textvariable=frame_var, width=4); frame_box.pack(side='left', padx=(2, 2))
        frame_note = ttk.Label(timing, foreground='#8c99ab'); frame_note.pack(side='left', padx=(0, 8))

        def source_row():
            # the actor whose animation starts the attack: this attacker, or the chosen part
            key = dict(sources).get(source.get())
            return self.editor.database.get(key) if key else self.editor.database.get(self.row_id)
        def source_frames():
            row = source_row()
            return self.memo('frames', row, lambda: self.frame_counts(row)) if row else {}
        def frame_range(*_):
            # the frame list follows the chosen actor and animation (0 = when it starts)
            frames = source_frames()
            animation_box.configure(to=max(frames) if frames else 63)
            try: count = frames.get(int(animation.get()))
            except ValueError: count = None
            frame_box.configure(to=(count - 1) if count else 255)
            frame_note.configure(text=f'of 0-{count - 1}' if count else '')
            try:
                if count and int(frame_var.get()) > count - 1: frame_var.set(str(count - 1))
            except ValueError: pass
        animation.trace_add('write', frame_range); source.trace_add('write', frame_range); frame_range()

        def pick():
            from spawn_attack_picker import AttackPicker
            current = dict(animation=animation.get() or 0, frame=frame_var.get() or 0,
                           dx=offsets[0].get() or 0, dy=offsets[1].get() or 0, dz=offsets[2].get() or 0)
            def done(v):
                animation.set(str(v['animation'])); frame_var.set(str(v['frame']))
                for var, key in zip(offsets, ('dx', 'dy', 'dz')): var.set(str(v[key]))
                self.editor.db_schedule_autosave()
            AttackPicker(self.editor, frame.winfo_toplevel(), source_row(), current, done)
        pick_button = ttk.Button(timing, command=lambda: self.editor.guard(pick)); pick_button.pack(side='right')
        def pick_label(*_):   # names whose animations it opens: this attacker's or the chosen part's (user 2026-10-27)
            row = source_row()
            pick_button.configure(text=f"Choose {(row or {}).get('name', 'its')} animation, frame and spawn point…")
        source.trace_add('write', pick_label); pick_label()
        def source_changed(*_):   # another actor: its own animations, so start from its first
            animation.set('0'); frame_var.set('0')
        source.trace_add('write', source_changed)

        what = ttk.Frame(body); what.pack(fill='x', pady=(2, 0))
        ttk.Label(what, text='Spawns').pack(side='left')
        ttk.Combobox(what, textvariable=klass, values=names, state='readonly', width=28).pack(side='left', padx=(2, 8))
        def show_icon(*_):
            key = dict(self.choices).get(klass.get())
            self.set_icon(body, next((d for d in self.editor.database.definitions if d['id'] == key), None))
        klass.trace_add('write', show_icon); show_icon()
        ttk.Label(what, text='Offset').pack(side='left', padx=(4, 0))
        for label, var in zip(('X', 'Y', 'Height'), offsets):
            ttk.Label(what, text=label).pack(side='left', padx=(8, 2))
            ttk.Spinbox(what, from_=-512, to=512, increment=4, textvariable=var, width=5).pack(side='left')

        fourth = ttk.Frame(body); fourth.pack(fill='x', pady=(2, 0))
        ttk.Label(fourth, text='Wait between spawns (frames)').pack(side='left')
        ttk.Spinbox(fourth, from_=0, to=3600, textvariable=cooldown, width=5).pack(side='left', padx=(2, 0))
        limit_on = tk.BooleanVar(value=bool(spawn.get('max_alive')))
        limit = tk.StringVar(value=str(spawn.get('max_alive') or 1))
        ttk.Checkbutton(fourth, text='Max at once', variable=limit_on).pack(side='left', padx=(12, 2))
        limit_box = ttk.Spinbox(fourth, from_=1, to=16, textvariable=limit, width=4); limit_box.pack(side='left')
        def limit_state(*_): limit_box.configure(state='normal' if limit_on.get() else 'disabled')
        limit_on.trace_add('write', limit_state); limit_state()
        despawn_on = tk.BooleanVar(value=bool(spawn.get('despawn')))
        despawn = tk.StringVar(value=str(spawn.get('despawn') or 60))
        fifth = ttk.Frame(body); fifth.pack(fill='x', pady=(2, 0))
        ttk.Checkbutton(fifth, text='Despawn after (frames)', variable=despawn_on).pack(side='left', padx=(0, 2))
        despawn_box = ttk.Spinbox(fifth, from_=1, to=36000, textvariable=despawn, width=6); despawn_box.pack(side='left')
        def despawn_state(*_): despawn_box.configure(state='normal' if despawn_on.get() else 'disabled')
        despawn_on.trace_add('write', despawn_state); despawn_state()
        hp_on = tk.BooleanVar(value=bool(spawn.get('hp')))
        hp = tk.StringVar(value=str(spawn.get('hp') or ''))
        ttk.Checkbutton(fifth, text='Spawn HP', variable=hp_on).pack(side='left', padx=(12, 2))
        hp_box = ttk.Spinbox(fifth, from_=1, to=9999, textvariable=hp, width=5); hp_box.pack(side='left')
        def class_hp():
            target = self.editor.database.get(dict(self.choices).get(klass.get())) if dict(self.choices).get(klass.get()) else None
            return ((target or {}).get('source', {}).get('native_data_baseline') or {}).get('max_hp')
        def hp_state(*_):
            hp_box.configure(state='normal' if hp_on.get() else 'disabled')
            if not hp_on.get() or not hp.get():
                hp.set(str(class_hp() or ''))
        hp_on.trace_add('write', hp_state); klass.trace_add('write', hp_state); hp_state()
        for v in (from_random, chance, cooldown, source, limit_on, limit, despawn_on, despawn, hp_on, hp): v.trace_add('write', lambda *_: self.editor.db_schedule_autosave())
        entry = (frame, animation, klass, offsets, frame_var, name, from_random, chance, cooldown, source, limit_on, limit, despawn_on, despawn, hp_on, hp)
        def remove():
            frame.destroy(); self.rows.remove(entry); self.new_host.configure(width=1, height=1); self.editor.db_schedule_autosave()
        holder['remove'] = remove
        def summary(*_):
            try:f = int(frame_var.get() or 0)
            except ValueError:f = 0
            who = '' if source.get() == 'This attacker' else f"{source.get().rsplit(' (class', 1)[0]} "
            frame.summary.configure(text=f"{name.get().strip() or 'New attack'} · {who}animation {animation.get()}" + (f", frame {f}" if f else '')
                                    + f" spawns {klass.get() or '—'}")
        for v in (animation, frame_var, klass, source):v.trace_add('write', summary)
        summary()
        self.rows.append(entry)
        if not spawn:
            self.editor.db_schedule_autosave()

    def apply(self, row):
        ai = row.get('data', {}).get('custom_ai')
        names = {k: v.get().strip() for k, v in getattr(self, 'native_names', {}).items() if v.get().strip()}
        if names: row['data']['spawn_attack_names'] = names
        else: row['data'].pop('spawn_attack_names', None)
        for i, vars_, name in self.ai_rows:
            if not ai or i >= len(ai.get('attacks') or []):
                continue
            if name.get().strip(): ai['attacks'][i]['name'] = name.get().strip()
            for key, v in vars_.items():
                try: value = int(v.get())
                except ValueError: raise ValueError('Spawn frame and position must be whole numbers')
                if key == 'spawn_frame' and not 0 <= value <= 600: raise ValueError('Spawn frame must be 0-600')
                if key != 'spawn_frame' and not -512 <= value <= 512: raise ValueError('Spawn position must be within 512 pixels')
                ai['attacks'][i][key] = value
        keys = dict(self.choices)
        rows = []
        for _, animation, klass, offsets, frame_var, name, from_random, chance, cooldown, source, limit_on, limit, despawn_on, despawn, hp_on, hp in self.rows:
            if klass.get() not in keys:
                continue
            values = [int(v.get() or 0) for v in offsets]
            item = dict(animation=int(animation.get() or 0), class_id=keys[klass.get()])
            try: chosen = int(frame_var.get() or 0)
            except ValueError: raise ValueError('Spawn frame must be a whole number')
            if not 0 <= chosen <= 255: raise ValueError('Spawn frame must be 0-255')
            if chosen: item['frame'] = chosen
            if name.get().strip(): item['name'] = name.get().strip()
            try: wait = int(cooldown.get() or 0)
            except ValueError: raise ValueError('Wait between spawns must be a whole number')
            if not 0 <= wait <= 3600: raise ValueError('Wait between spawns must be 0-3600 frames')
            try: odds = int(chance.get() or 100)
            except ValueError: raise ValueError('Chance must be a whole number')
            if not 1 <= odds <= 100: raise ValueError('Chance must be 1-100%')
            if not from_random.get(): odds = 100   # Chance only with Random
            if odds < 100: item['chance'] = odds
            if (from_random.get() or wait or odds < 100) and chosen:
                raise ValueError('Random, Chance and wait work from the start of the animation (frame 0)')
            if limit_on.get():
                try: most = int(limit.get())
                except ValueError: raise ValueError('Max at once must be a whole number')
                if not 1 <= most <= 16: raise ValueError("Max at once must be 1-16")
                if chosen: raise ValueError('Max at once works from the start of the animation (frame 0)')
                item['max_alive'] = most
            if despawn_on.get():
                try: life = int(despawn.get())
                except ValueError: raise ValueError('Despawn after must be a whole number')
                if not 1 <= life <= 36000: raise ValueError('Despawn after must be 1-36000 frames')
                if chosen: raise ValueError('Despawn after works from the start of the animation (frame 0)')
                item['despawn'] = life
            if hp_on.get():
                try: life_hp = int(hp.get())
                except ValueError: raise ValueError('Spawn HP must be a whole number')
                if not 1 <= life_hp <= 9999: raise ValueError('Spawn HP must be 1-9999')
                if chosen: raise ValueError('Spawn HP works from the start of the animation (frame 0)')
                item['hp'] = life_hp
            if from_random.get(): item['from_random'] = True
            if source.get() in keys and keys[source.get()] != row.get('id'):
                # the chosen actor's own animation starts it, and it spawns at that actor (user 2026-10-27)
                item['from_class_id'] = keys[source.get()]; item['source_animation'] = True
            if wait: item['cooldown'] = wait
            item.update({k: v for k, v in zip(('dx', 'dy', 'dz'), values) if v})
            if keys[klass.get()] == row.get('id'):
                raise ValueError('A class cannot spawn itself as a new attack')
            rows.append(item)
        if rows:
            row['data']['spawn_attacks'] = rows
        else:
            row['data'].pop('spawn_attacks', None)
        return row

    def damage_edits(self):
        """{definition id: {'power': n, 'attribute': byte}} for changed spawned attacks
        (the first attack of the spawned class)."""
        from attack_attributes import parse_attribute
        out = {}
        for key, var in self.damage.items():
            try:
                power = int(var.get())
            except ValueError:
                continue
            definition = self.editor.database.get(key)
            attacks = definition.get('data', {}).get('attacks') or []
            if not attacks:
                continue
            if not 0 <= power <= 255:
                raise ValueError('Damage must be 0-255')
            attribute = attacks[0].get('attribute', 0)
            if key in self.attributes and self.attributes[key].get():
                attribute = parse_attribute(self.attributes[key].get())
            if (power, attribute) != (attacks[0]['power'], attacks[0].get('attribute', 0)):
                out[key] = dict(power=power, attribute=attribute)
        return out
