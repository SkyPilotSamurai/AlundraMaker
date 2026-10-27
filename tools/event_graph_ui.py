"""RPG-style event authoring; export checks the supported native compiler subset."""
from copy import deepcopy
import json
import tkinter as tk
from tkinter import ttk

from event_graph import is_auto_name, class_event_name, COMMANDS, TRIGGERS, HIT_SOURCES, ensure_trigger_actions, validate_event_graph
from map_names import map_label

SWITCH_CLASSES = {301, 305, 306, 307, 345, 383}   # step-on, lever, wall, ignition, Nirude finger, tri-colour
TRIGGER_LABELS = {value: value for value in TRIGGERS}
TRIGGER_LABELS['death']='Death'
TRIGGER_VALUES = {label: value for value, label in TRIGGER_LABELS.items()}


def command_template(kind):
    return {
        "show_dialogue": {"type": kind, "speaker": None, "text": "","auto_wrap":True},
        "ask_question": {"type": kind, "text": "", "auto_wrap": True, "then": [], "else": []},
        "give_item": {"type": kind, "item_class_id": "item:0001", "quantity": 1,
                      "show_obtained_text": True, "drop_on_map": False},
        "set_switch": {"type": kind, "switch_id": 1, "switch_scope":"project", "value": True},
        "change_money": {"type": kind, "amount": 1},
        "set_variable": {"type": kind, "variable_id": 1, "variable_scope":"project", "operation": "set", "value": 0},
        "face_actor": {"type":kind,"target":"this_event","direction":"player"},
        "move_actor": {"type": kind, "target": "this_event", "mode": "walk_tiles", "tiles":1,"direction":"down","movement_speed":100,"blocked_behavior":"wait"},
        "change_graphic": {"type": kind, "target": "this_event", "graphic": ""},
        "change_player_character": {"type":kind,"character":"Alundra","meia_basic_attack":False,"meia_alundra_fallback":False},
        "set_event_active": {"type": kind, "event_id": "event:0001", "active": True},
        "spawn_class": {"type": kind, "class_id": "object:0001", "position": [0, 0]},
        "warp_player": {"type": kind, "map_id": 0, "x": 0, "y": 0, "z": 0},
        "wait": {"type": kind, "frames": 30},
        "change_animation": {"type": kind, "animation_id": 0},
        "deactivate_switch": {"type": kind, "event_id": "this_event", "active": False},
        "play_sound": {"type": kind, "sound_id": 1},
        "change_music": {"type": kind, "music_id": 1},
        "repeat": {"type":kind,"count":2,"commands":[]},
        "if": {"type": kind, "condition": {"type": "switch", "switch_id": 1, "switch_scope":"project", "value": True}, "then": [], "else": []},
        **{k: dict(v[2], type=k) for k, v in __import__("native_event_authoring").COMMANDS.items()},
    }[kind]



OFFSET_CHOICES=('-1/2 tile','0','+1/2 tile')
def offset_label(value):
    """Offset X/Y drop-down text for a half-tile step (older projects may hold larger steps)."""
    value=int(value or 0)
    return {-1:'-1/2 tile',0:'0',1:'+1/2 tile'}.get(value,str(value))
def offset_value(text):
    text=(text or '').strip()
    return {'-1/2 tile':-1,'0':0,'+1/2 tile':1,'':0}.get(text) if text in ('-1/2 tile','0','+1/2 tile','') else int(text,0)


def spawn_choice_names(db):
    """'Name (catalogue)' -> class id of every enemy / object a Generator can spawn."""
    return {f"{r['name']} ({r['source'].get('catalogue_index')})": r['id'] for r in db.definitions
            if r['kind'] in ('enemy', 'object') and not r.get('clone_of') and type(r.get('source', {}).get('catalogue_index')) is int}

class EventGraphWindow:
    page_clipboard=None;command_clipboard=None
    def is_step_on_switch(self):
        cid=self.class_choices.get(self.placement_class.get()) if hasattr(self,'class_choices') else None
        row=self.db.get(cid) if cid else None
        return bool(row) and (row.get('source',{}).get('catalogue_index')==301 or row.get('source',{}).get('variant')=='floor_switch')   # the floor version too (user 2026-10-25)
    def placement_catalogue(self):
        cid=self.class_choices.get(self.placement_class.get()) if hasattr(self,'class_choices') else None
        row=self.db.get(cid) if cid else None
        return row.get('source',{}).get('catalogue_index') if row else None
    PLATE_SYMBOLS={'down':'Star','up':'Moon','left':'Water','right':'Sun'}
    def placement_definition(self):
        cid=self.class_choices.get(self.placement_class.get()) if hasattr(self,'class_choices') else None
        return self.db.get(cid) if cid else None
    def is_changing_plate(self):
        return ((self.placement_definition() or {}).get('source',{}).get('variant'))=='pattern_cycle'
    def is_static_plate(self):
        row=self.placement_definition()
        return bool(row) and row.get('source',{}).get('catalogue_index')==364 and row.get('source',{}).get('variant')!='pattern_cycle'
    ACTIVE_SWITCHES=(301,305,306,307,398)   # switches that keep an on / off state
    def is_state_switch(self):
        row=self.placement_definition() or {}
        src=row.get('source',{})
        return src.get('variant') in ('block_switch','floor_switch') or (src.get('catalogue_index') in self.ACTIVE_SWITCHES and not src.get('variant'))
    def is_nirude_face(self):   # Nirude Face Statue: activated -> destructible, broken -> Deactivate (2026-10-24)
        from native_nirude_face import is_face
        from native_nirude_statue_variants import variant_of   # the shooting statues: the same activation
        return is_face(self.placement_definition()) or bool(variant_of(self.placement_definition()))
    def is_statue_variant(self):   # Nirude Face Statue (Fire / Homing Fire / Laser)
        from native_nirude_statue_variants import variant_of
        return bool(variant_of(self.placement_definition()))
    def is_deactivatable_switch(self):
        row=self.placement_definition() or {}
        src=row.get('source',{})
        return (src.get('catalogue_index') in (301,305,306,307,398) and not src.get('variant')) or src.get('variant')=='floor_switch'
    def can_deactivate_changed(self):
        """Can Deactivate on: the event gets a Deactivate tab; off: an empty one goes."""
        page=self.current_page()
        if not page:return
        self._save_active_trigger()
        handlers=ensure_trigger_actions(page)
        has=[h for h in handlers if h.get('trigger')=='deactivate']
        if self.can_deactivate.get() and not has:
            handlers.append({'trigger':'deactivate','commands':[],'hit_sources':[],'destroy_after':False})
        elif not self.can_deactivate.get() and not self.while_pressured.get():
            for h in has:
                if not h.get('commands'):handlers.remove(h)
        self.refresh_trigger_tabs(self.active_trigger if any(h['trigger']==self.active_trigger for h in handlers) else handlers[0]['trigger'])
    def is_warp_panel(self):
        cid=self.class_choices.get(self.placement_class.get()) if hasattr(self,'class_choices') else None
        row=self.db.get(cid) if cid else None
        return bool(row) and row.get('source',{}).get('variant')=='warp_panel'
    def is_save_portal(self):
        cid=self.class_choices.get(self.placement_class.get()) if hasattr(self,'class_choices') else None
        row=self.db.get(cid) if cid else None
        return bool(row) and row.get('source',{}).get('variant')=='save_portal'
    WARP_MODES={'previous':'Return To Previous Location','destination':'Chosen Destination'}
    def warp_mode_changed(self):
        """Save Room Portal: back where Alundra came from, or a chosen tile."""
        if not self.working:return
        mode=next((k for k,v in self.WARP_MODES.items() if v==self.warp_mode.get()),'previous')
        self.working.setdefault('native_placement',{})['warp_mode']=mode
        self._commit_selected();self.keep_changes(commit_form=False);self.update_switch_option_boxes()
        if mode=='destination' and not isinstance(self.working['native_placement'].get('warp_to'),dict):self.choose_warp_destination()
    def choose_warp_destination(self):
        """Warp Panel / Save Room Portal: pick the map and tile it leads to."""
        if not self.working:return
        from map_tile_picker import MapTileDialog
        current=(self.working.get('native_placement') or {}).get('warp_to') or {}
        event_id=self.working['id']
        name='Save Room Portal' if self.is_save_portal() else 'Warp Panel'
        def picked(m,x,y,z):
            if not self.working or self.working['id']!=event_id:raise ValueError('Another event is open now; choose the destination again')
            self.working.setdefault('native_placement',{})['warp_to']={'map':int(m),'x':int(x),'y':int(y),'z':int(z or 0)}
            self._commit_selected();self.keep_changes(commit_form=False);self.update_switch_option_boxes()
            self.status.set(f"{name} leads to map {m}, tile {x}, {y}.")
        MapTileDialog(self.editor,self.window,lambda m,x,y,z:self.editor.guard(lambda:picked(m,x,y,z)),
                      map_id=current.get('map',self.editor.current_map),x=current.get('x',0),y=current.get('y',0),
                      title=f'{name}: Choose Where It Leads',confirm='Use This Tile')
    def is_pattern_plate(self):
        return self.placement_catalogue()==364
    def facing_label(self,value):
        if self.is_pattern_plate():return self.PLATE_SYMBOLS.get(value,'Star')
        return (value or 'down').capitalize()
    def facing_value(self,label):
        for value,name in self.PLATE_SYMBOLS.items():
            if label==name:return value
        return (label or 'Down').lower()
    def update_facing_control(self):
        plate=self.is_pattern_plate()
        try:
            self.direction_label.configure(text='Symbol' if plate else 'Direction')
            self.facing_combo.configure(values=list(self.PLATE_SYMBOLS.values()) if plate else ['Down','Up','Left','Right'],
                                        state='disabled' if self.is_static_plate() else 'readonly')
            self.facing_display.set(self.facing_label(self.default_facing.get()))
        except Exception:pass
    def track_player_default(self):
        d=self.placement_definition() or {}
        return d.get('kind')=='boss' and d.get('source',{}).get('catalogue_index')==452   # Sara

    def update_switch_option_boxes(self):
        """Sword Only Activation shows for a Lamp Switch, Bomb Activation for a Switch (Ignition)."""
        cat=self.placement_catalogue()
        if hasattr(self,'direction_label'):self.update_facing_control()
        if hasattr(self,'track_player') and 'track_player' not in (((self.working or {}).get('native_placement')) or {}):
            self.track_player.set(self.track_player_default())   # Sara starts with it on
        if hasattr(self,'active_by_default') and self.is_statue_variant() and 'active_by_default' not in (((self.working or {}).get('native_placement')) or {}):
            self.active_by_default.set(True)   # shooting Nirude statues fire at once, like the originals (user 2026-10-24)
        button=getattr(self,'warp_destination_button',None)
        if button is not None:
            try:
                portal=self.is_save_portal()
                mode_box=getattr(self,'warp_mode_combo',None)
                if mode_box is not None:
                    if portal:
                        self.warp_mode.set(self.WARP_MODES['destination' if ((self.working or {}).get('native_placement') or {}).get('warp_mode')=='destination' else 'previous'])
                        mode_box.grid()
                    else:mode_box.grid_remove()
                if self.is_warp_panel() or (portal and ((self.working or {}).get('native_placement') or {}).get('warp_mode')=='destination'):
                    to=((self.working or {}).get('native_placement') or {}).get('warp_to')
                    self.warp_destination_text.set(f"Warp To: map {to['map']}, {to['x']},{to['y']}" if isinstance(to,dict) and 'map' in to else "Warp Destination…")
                    button.grid()
                else:button.grid_remove()
            except Exception:pass
        changing=self.is_changing_plate()
        for box,show in ((getattr(self,'sword_only_box',None),cat==398),(getattr(self,'bomb_activation_box',None),cat==307),
                         (getattr(self,'start_symbol_frame',None),changing),(getattr(self,'fail_stops_box',None),changing),
                         (getattr(self,'active_default_box',None),self.is_state_switch() or self.is_nirude_face()),
                         (getattr(self,'keep_state_box',None),self.is_state_switch() or self.is_pattern_plate()),
                         (getattr(self,'can_deactivate_box',None),self.is_deactivatable_switch()),
                         (getattr(self,'play_victory_box',None),(self.placement_definition() or {}).get('kind')=='boss'),
                         (getattr(self,'track_player_box',None),(self.placement_definition() or {}).get('kind') in ('enemy','boss')),
                         (getattr(self,'instant_respawn_box',None),(self.placement_definition() or {}).get('kind') in ('enemy','boss'))):
            if box is None:continue
            try:
                if show:box.grid()
                else:box.grid_remove()
            except Exception:pass
    def update_while_pressured_box(self):
        """While Pressured only shows for a Switch (Step On)."""
        for box,show in ((getattr(self,'while_pressured_box',None),self.is_step_on_switch()),(getattr(self,'ignore_spring_bean_box',None),self.is_step_on_switch()),
                         (getattr(self,'plate_flush_box',None),self.is_pattern_plate())):
            if box is None:continue
            try:
                if show:box.grid()
                else:box.grid_remove()
            except Exception:pass
    def update_flush_floor_box(self):
        """Flush With Floor only shows for a Switch (Step On)."""
        box=getattr(self,'flush_floor_box',None)
        if box is None:return
        try:
            if self.is_step_on_switch():box.grid()
            else:box.grid_remove()
        except Exception:pass
    def tile_z(self,map_id,x,y):
        """Height of the tile at x,y on map_id (None when unknown)."""
        try:
            from area_map import grid
            w,h,cells=grid(self.editor.session,map_id)
            return cells[y*w+x]['values'][3] if 0<=x<w and 0<=y<h else None
        except Exception:return None
    def __init__(self, editor):
        from event_edit_draft import EventEditDraft
        self.editor=editor;self.draft=EventEditDraft(editor.database);self.db=self.draft.database;self.window=tk.Toplevel(editor.root)
        self.window._alundra_graph_window=self
        self.window.title("Alundra Event Editor")
        width=max(1080,min(1450,round(editor.root.winfo_screenwidth()*.85)));height=max(760,round(editor.root.winfo_screenheight()*.85))
        self.window.geometry(f'{width}x{height}+20+0');self.window.minsize(940,640)
        self.working=None;self.page_id=None;self.command_index=None
        toolbar=ttk.Frame(self.window,padding=8);toolbar.pack(fill="x")
        for label,command in [("Switches / variables",self.open_project_state),("Delete event",self.delete_event)]:
            ttk.Button(toolbar,text=label,command=lambda c=command:editor.guard(c)).pack(side="left",padx=3)
        body=ttk.Panedwindow(self.window,orient="horizontal");body.pack(fill="both",expand=True,padx=8,pady=6)
        left=ttk.Frame(body,width=220);body.add(left,weight=1)
        self.events=ttk.Treeview(left,columns=("map","trigger","region"),show="tree headings",height=6)
        self.events.heading("#0",text="Event");self.events.heading("map",text="Map");self.events.heading("trigger",text="Trigger");self.events.heading("region",text="Tile region")
        for key,width in [("#0",105),("map",55),("trigger",65),("region",70)]:self.events.column(key,width=width,minwidth=40)
        self.events.pack(fill="both",expand=True);self.events.bind("<<TreeviewSelect>>",lambda _:editor.guard(self.load_selected))
        ttk.Label(left,text='Page object / NPC — click to choose').pack(anchor='w',pady=(8,2))
        self.page_graphic=tk.Canvas(left,height=150,background='#171b22',highlightthickness=0);self.page_graphic.pack(fill='x')
        self.page_graphic.bind('<Button-1>',lambda _:self.choose_page_class())
        self.placement_class=tk.StringVar(value="No database object")
        ttk.Button(left,text='Choose object / NPC...',command=self.choose_page_class).pack(fill='x',pady=(3,6))
        self.placement_combo=ttk.Combobox(left,textvariable=self.placement_class,state='readonly',width=28)
        # Object selection uses the 'Choose object / NPC...' picker; the dropdown stays hidden.
        self.chest_contents_frame=ttk.LabelFrame(left,text='Chest contents',padding=5)
        self.chest_contents_label=tk.StringVar(value='Choose an item')
        ttk.Label(self.chest_contents_frame,textvariable=self.chest_contents_label,wraplength=205).pack(anchor='w')
        ttk.Button(self.chest_contents_frame,text='Choose item from database…',command=lambda:editor.guard(self.choose_chest_item)).pack(fill='x',pady=(4,0))
        self.behaviour_frame=ttk.LabelFrame(left,text='Behaviour',padding=5)
        self.behaviour=tk.StringVar(value='Automatic');self.behaviour_choices={}
        self.behaviour_combo=ttk.Combobox(self.behaviour_frame,textvariable=self.behaviour,state='readonly',width=34)
        self.behaviour_combo.pack(fill='x')
        self.behaviour_combo.bind('<<ComboboxSelected>>',lambda _:editor.guard(self.apply_behaviour))
        self.behaviour_note=tk.StringVar()
        self.gate_binding_frame=ttk.Frame(left)
        self.gate_binding_label=tk.StringVar(value='Choose switch…')
        ttk.Label(self.gate_binding_frame,text='Open when switch is ON').pack(anchor='w')
        ttk.Button(self.gate_binding_frame,textvariable=self.gate_binding_label,command=lambda:editor.guard(self.choose_gate_switch)).pack(fill='x',pady=(2,6))
        self.gate_binding_frame.pack(fill='x')
        self.gate_binding_frame.pack_forget()
        # Enemies and bosses: Act as NPC (idles, harmless, NPC hitbox, Interact instead of Death)
        self.act_as_npc=tk.BooleanVar(value=False)
        self.act_as_npc_frame=ttk.Frame(left)
        ttk.Checkbutton(self.act_as_npc_frame,text='Act As NPC',variable=self.act_as_npc,command=lambda:editor.guard(self.act_as_npc_changed)).pack(anchor='w')
        self.act_as_npc_frame.pack(fill='x');self.act_as_npc_frame.pack_forget()
        self.rotation_control=tk.BooleanVar(value=False)
        self.rotation_frame=ttk.Frame(left)
        ttk.Checkbutton(self.rotation_frame,text='Use rotation switch controller',variable=self.rotation_control,command=lambda:editor.guard(self._commit_selected)).pack(anchor='w')
        self.rotation_frame.pack(fill='x');self.rotation_frame.pack_forget()
        # Generator: which class it spawns (default: its stock Mud Man), 2026-10-22
        self.spawned_class=tk.StringVar(value='(stock)')
        self.spawned_frame=ttk.Frame(left)
        ttk.Label(self.spawned_frame,text='Spawns').pack(side='left')
        self.spawned_combo=ttk.Combobox(self.spawned_frame,textvariable=self.spawned_class,state='readonly',width=28)
        self.spawned_combo.pack(side='left',padx=4);self.spawned_combo.bind('<<ComboboxSelected>>',lambda e:editor.guard(self._commit_selected))
        self.spawned_frame.pack(fill='x');self.spawned_frame.pack_forget()
        # Launcher / Four-Way Turret: Fireballs freezable (Ice Wand), native_freezable_flame (2026-10-22)
        self.fireballs_freezable=tk.BooleanVar(value=False)
        self.freezable_frame=ttk.Frame(left)
        ttk.Checkbutton(self.freezable_frame,text='Fireballs freezable (Ice Wand)',variable=self.fireballs_freezable,command=lambda:editor.guard(self._commit_selected)).pack(anchor='w')
        self.always_fire=tk.BooleanVar(value=False);self.trigger_range=tk.StringVar(value='')
        ttk.Checkbutton(self.freezable_frame,text='Always fire (no player trigger box)',variable=self.always_fire,command=lambda:editor.guard(self._commit_selected)).pack(anchor='w')
        _tr=ttk.Frame(self.freezable_frame);_tr.pack(anchor='w')
        ttk.Label(_tr,text='Trigger range (tiles, blank = stock box)').pack(side='left')
        _sp=ttk.Spinbox(_tr,from_=1,to=64,width=5,textvariable=self.trigger_range,command=lambda:editor.guard(self._commit_selected));_sp.pack(side='left',padx=4)
        _sp.bind('<FocusOut>',lambda e:editor.guard(self._commit_selected))
        self.freezable_frame.pack(fill='x');self.freezable_frame.pack_forget()
        # Stool (Pushable): the directions it may be pushed (native_pushable_stool, 2026-10-23)
        self.stool_dirs={d:tk.BooleanVar(value=True) for d in ('up','down','left','right')}
        self.stool_once=tk.BooleanVar(value=False);self.stool_target=tk.StringVar(value='None')
        self.stool_frame=ttk.Frame(left)
        _line=ttk.Frame(self.stool_frame);_line.pack(fill='x')
        ttk.Label(_line,text='Moves').pack(side='left')
        for d in ('up','down','left','right'):
            ttk.Checkbutton(_line,text=d.title(),variable=self.stool_dirs[d],command=lambda:editor.guard(self._commit_selected)).pack(side='left')
        _line=ttk.Frame(self.stool_frame);_line.pack(fill='x')
        ttk.Label(_line,text='Target tile').pack(side='left');ttk.Label(_line,textvariable=self.stool_target).pack(side='left',padx=4)
        ttk.Button(_line,text='Choose Tile On Map…',command=lambda:editor.guard(self.choose_stool_target)).pack(side='left')
        ttk.Button(_line,text='Clear',command=lambda:editor.guard(lambda:self.choose_stool_target(clear=True))).pack(side='left',padx=2)
        ttk.Checkbutton(self.stool_frame,text='Move Once',variable=self.stool_once,command=lambda:editor.guard(self._commit_selected)).pack(anchor='w')
        self.stool_frame.pack(fill='x');self.stool_frame.pack_forget()
        self.rolling_target_enabled=tk.BooleanVar(value=False)
        self.rolling_target_frame=ttk.Frame(left)
        ttk.Checkbutton(self.rolling_target_frame,text='Finish at tile (Up direction)',variable=self.rolling_target_enabled,command=lambda:editor.guard(self.rolling_target_changed)).pack(anchor='w')
        self.rolling_target_x=tk.StringVar(value='0');self.rolling_target_y=tk.StringVar(value='0')
        line=ttk.Frame(self.rolling_target_frame);line.pack(fill='x')
        for label,var in [('X',self.rolling_target_x),('Y',self.rolling_target_y)]:
            ttk.Label(line,text=label).pack(side='left');ttk.Spinbox(line,from_=0,to=127,textvariable=var,width=4).pack(side='left',padx=2)
        self.rolling_target_frame.pack(fill='x');self.rolling_target_frame.pack_forget()
        options=ttk.LabelFrame(left,text='Default behaviour',padding=6);options.pack(fill='x')
        self.default_facing=tk.StringVar(value='down');self.page_trigger=tk.StringVar(value='interact')
        self.direction_label=ttk.Label(options,text='Direction');self.direction_label.pack(anchor='w')
        # shown capitalised; the stored value stays lower case (down/up/left/right).
        # A Pattern Plate's direction is its symbol, so it shows the symbol names.
        self.facing_display=tk.StringVar(value='Down')
        self.default_facing.trace_add('write',lambda *_:self.facing_display.set(self.facing_label(self.default_facing.get())))
        self.facing_combo=ttk.Combobox(options,textvariable=self.facing_display,values=['Down','Up','Left','Right'],state='readonly',width=18)
        def facing_picked(_=None):
            self.default_facing.set(self.facing_value(self.facing_display.get()));editor.guard(self.change_default_facing)
        self.facing_combo.pack(fill='x',pady=(2,6));self.facing_combo.bind('<<ComboboxSelected>>',facing_picked)
        ttk.Label(options,text='Default move route').pack(anchor='w')
        self.default_route_mode=tk.StringVar(value='Native')
        self.default_route_combo=ttk.Combobox(options,textvariable=self.default_route_mode,values=['Native','Route'],state='readonly',width=18)
        self.default_route_combo.pack(fill='x',pady=2)
        self.default_route_combo.bind('<<ComboboxSelected>>',lambda _:editor.guard(self.default_route_changed))
        self.idle_animation_enabled=tk.BooleanVar(value=True)
        self.idle_animation_check=ttk.Checkbutton(options,text='Use this character’s idle animation',variable=self.idle_animation_enabled,
            command=lambda:editor.guard(self._commit_selected))
        self.idle_animation_check.pack(anchor='w',pady=2);self.idle_animation_check.pack_forget()
        # Float (next to Tile Z): the event stays at its Tile Z instead of dropping to the ground
        self.float_enabled=tk.BooleanVar(value=False)
        self.float_height=tk.StringVar(value='0')   # extra lift; kept for older projects (no box)
        self.default_route_button=ttk.Button(options,text='Edit route...',command=lambda:editor.guard(self.edit_default_route));self.default_route_button.pack(fill='x',pady=(3,6))
        speed_row=ttk.Frame(options);speed_row.pack(fill='x',pady=2)
        ttk.Label(speed_row,text='Route Speed %').pack(side='left')
        self.default_route_speed=tk.StringVar(value='100')
        self.default_speed_spin=ttk.Spinbox(speed_row,from_=1,to=400,textvariable=self.default_route_speed,width=8);self.default_speed_spin.pack(side='left',padx=(6,0))
        flags_row=ttk.Frame(options);flags_row.pack(fill='x',pady=3)
        self.default_route_repeat=tk.BooleanVar(value=True)
        self.default_repeat_button=ttk.Checkbutton(flags_row,text='Repeat route',variable=self.default_route_repeat);self.default_repeat_button.pack(side='left')
        # People turn to face Alundra when he talks to them; Direction fix keeps this one's direction.
        self.direction_fix=tk.BooleanVar(value=False)
        ttk.Checkbutton(flags_row,text='Direction fix',variable=self.direction_fix,command=lambda:editor.guard(self.schedule_apply)).pack(side='left',padx=(12,0))
        # NPC on-map animation: plays (and repeats) the chosen animation; Static shows one frame only.
        self.animation_frame=ttk.Frame(options)
        ttk.Label(self.animation_frame,text='Animation').pack(anchor='w')
        self.npc_animation=tk.StringVar(value='Native')
        self.npc_animation_combo=ttk.Combobox(self.animation_frame,textvariable=self.npc_animation,values=['Native'],state='readonly',width=18)
        self.npc_animation_combo.pack(fill='x',pady=2)
        self.npc_animation_combo.bind('<<ComboboxSelected>>',lambda _:editor.guard(self.animation_choice_changed))
        static_row=ttk.Frame(self.animation_frame);static_row.pack(fill='x')
        self.animation_static=tk.BooleanVar(value=False)
        ttk.Checkbutton(static_row,text='Static',variable=self.animation_static,command=lambda:editor.guard(self.animation_choice_changed)).pack(side='left')
        ttk.Label(static_row,text='Frame').pack(side='left',padx=(8,2))
        self.static_frame=tk.StringVar(value='0')
        self.static_frame_spin=ttk.Spinbox(static_row,from_=0,to=63,textvariable=self.static_frame,width=4,command=lambda:editor.guard(self.schedule_apply))
        self.static_frame_spin.pack(side='left')
        self.animation_frame.pack(fill='x',pady=(4,0));self.animation_frame.pack_forget()

        right=ttk.Frame(body,padding=(10,4));body.add(right,weight=4)
        form=ttk.LabelFrame(right,text="Map event settings",padding=8);form.pack(fill="x")
        self.name=tk.StringVar();self.map_id=tk.StringVar(value=str(editor.current_map if editor.session else 0))
        self.x=tk.StringVar(value="0");self.y=tk.StringVar(value="0");self.w=tk.StringVar(value="1");self.h=tk.StringVar(value="1")
        self.offset_x=tk.StringVar(value=offset_label(0));self.offset_y=tk.StringVar(value=offset_label(0))   # half-tile steps (the game's own position unit)
        self.z_height=tk.StringVar(value="")   # blank: stand on the tile's own height; 0 allowed
        self.lower_one=tk.BooleanVar(value=False)   # placed one height lower (e.g. a step-on switch level with the floor)
        self.while_pressured=tk.BooleanVar(value=False)   # Switch (Step On): on only while stood on
        self.flush_floor=tk.BooleanVar(value=False)   # Switch (Step On) only: remove the piece left on top of it when its tile is lowered
        fields=[("Name",self.name,28),("Map",self.map_id,6),("Tile X",self.x,5),("Tile Y",self.y,5),("Tile Z",self.z_height,5),("Offset X",self.offset_x,5),("Offset Y",self.offset_y,5),("Width",self.w,5),("Height",self.h,5),("Float",None,0)]
        for col,(label,var,width) in enumerate(fields):
            if var is None:   # Float, after the event's coordinates, width and height
                ttk.Checkbutton(form,text='Float',variable=self.float_enabled,command=lambda:editor.guard(self._commit_selected)).grid(row=1,column=col,sticky='w',padx=6)
                continue
            ttk.Label(form,text=label).grid(row=0,column=col,sticky="w",padx=3)
            if var is self.offset_x or var is self.offset_y:
                # the game places events in half-tile steps: up to half a tile either way
                ttk.Combobox(form,textvariable=var,values=OFFSET_CHOICES,width=9,state='readonly').grid(row=1,column=col,sticky="w",padx=3)
            else:
                ttk.Entry(form,textvariable=var,width=width).grid(row=1,column=col,sticky="w",padx=3)
        self.while_pressured_box=ttk.Checkbutton(form,text="While Pressed",variable=self.while_pressured)
        self.while_pressured_box.grid(row=1,column=len(fields),sticky="w",padx=6)
        self.ignore_spring_bean=tk.BooleanVar(value=False)   # Switch (Step On): a thrown Spring Bean does not press it
        self.ignore_spring_bean_box=ttk.Checkbutton(form,text="Ignore Spring Bean",variable=self.ignore_spring_bean)
        self.ignore_spring_bean_box.grid(row=2,column=len(fields),sticky="w",padx=6)
        self.plate_flush=tk.BooleanVar(value=True)   # Pattern Plate: level with the floor so Alundra walks onto it
        self.plate_flush_box=ttk.Checkbutton(form,text="Flush With Floor",variable=self.plate_flush)
        self.plate_flush_box.grid(row=1,column=len(fields)+1,sticky="w",padx=6)
        self.placement_class.trace_add('write',lambda *_:self.update_while_pressured_box())
        self.sword_only=tk.BooleanVar(value=False)        # Lamp Switch: only a sword hit lights it
        self.bomb_activation=tk.BooleanVar(value=False)   # Switch (Ignition): a bomb lights it too
        self.sword_only_box=ttk.Checkbutton(form,text="Sword Only Activation",variable=self.sword_only)
        self.sword_only_box.grid(row=1,column=len(fields)+1,sticky="w",padx=6)
        self.bomb_activation_box=ttk.Checkbutton(form,text="Bomb Activation",variable=self.bomb_activation)
        self.bomb_activation_box.grid(row=1,column=len(fields)+2,sticky="w",padx=6)
        # Pattern Plate (Changing): the symbol it starts on, and whether its failure stops the map's other changing plates
        self.start_symbol=tk.StringVar(value='Star');self.fail_stops_others=tk.BooleanVar(value=True)
        self.start_symbol_frame=ttk.Frame(form)
        ttk.Label(self.start_symbol_frame,text="Starting Symbol").pack(side='left')
        ttk.Combobox(self.start_symbol_frame,textvariable=self.start_symbol,values=['Star','Moon','Water','Sun'],state='readonly',width=7).pack(side='left',padx=(4,0))
        self.start_symbol_frame.grid(row=1,column=len(fields)+4,sticky="w",padx=6)
        self.fail_stops_box=ttk.Checkbutton(form,text="Failure Stops Other Changing Plates",variable=self.fail_stops_others)
        self.fail_stops_box.grid(row=1,column=len(fields)+5,sticky="w",padx=6)
        self.active_by_default=tk.BooleanVar(value=False)   # switches: start already active
        self.active_default_box=ttk.Checkbutton(form,text="Active By Default",variable=self.active_by_default)
        self.active_default_box.grid(row=1,column=len(fields)+6,sticky="w",padx=6)
        self.keep_state=tk.BooleanVar(value=False)   # switches: their private state survives leaving the room
        self.keep_state_box=ttk.Checkbutton(form,text="Keep State Upon Leaving Room",variable=self.keep_state)
        self.keep_state_box.grid(row=1,column=len(fields)+7,sticky="w",padx=6)
        self.can_deactivate=tk.BooleanVar(value=False)   # switches: the same trigger switches it off again (ignition: the Ice Wand)
        self.can_deactivate_box=ttk.Checkbutton(form,text="Can Deactivate",variable=self.can_deactivate,command=lambda:editor.guard(self.can_deactivate_changed))
        self.can_deactivate_box.grid(row=1,column=len(fields)+8,sticky="w",padx=6)
        # Act as NPC: one checkbox only, in the enemy / boss panel (act_as_npc_frame); for a boss it
        # is also saved on the page (stands still and talks, no fighting).
        self.play_victory=tk.BooleanVar(value=True)   # bosses: Alundra's victory pose, fanfare and text when it is beaten (as the game)
        self.play_victory_box=ttk.Checkbutton(form,text="Play Victory",variable=self.play_victory)
        self.play_victory_box.grid(row=1,column=len(fields)+10,sticky="w",padx=6)
        self.track_player=tk.BooleanVar(value=False)   # enemies / bosses: turn toward the player from afar (on by default for Sara)
        self.track_player_box=ttk.Checkbutton(form,text="Track Player",variable=self.track_player)
        self.track_player_box.grid(row=1,column=len(fields)+11,sticky="w",padx=6)
        self.instant_respawn=tk.BooleanVar(value=False)   # enemies / bosses: killed ones come straight back instead of on the next visit
        self.instant_respawn_box=ttk.Checkbutton(form,text="Instant respawn",variable=self.instant_respawn)
        self.instant_respawn_box.grid(row=1,column=len(fields)+12,sticky="w",padx=6)
        self.tile_mask=tk.BooleanVar(value=False)   # tile events: the tile's wall pieces are drawn over the player
        self.tile_mask_box=ttk.Checkbutton(form,text="Use as mask",variable=self.tile_mask,command=lambda:self.editor.guard(self.apply_tile_graphic))
        self.tile_mask_box.grid(row=1,column=len(fields)+13,sticky="w",padx=6);self.tile_mask_box.grid_remove()
        self.warp_destination_text=tk.StringVar(value="Warp Destination…")   # Warp Panel: where it leads
        self.warp_destination_button=ttk.Button(form,textvariable=self.warp_destination_text,command=lambda:editor.guard(self.choose_warp_destination))
        self.warp_destination_button.grid(row=1,column=len(fields)+3,sticky="w",padx=6)
        self.warp_mode=tk.StringVar(value=self.WARP_MODES['previous'])   # Save Room Portal: where it leads
        self.warp_mode_combo=ttk.Combobox(form,textvariable=self.warp_mode,values=list(self.WARP_MODES.values()),state='readonly',width=28)
        self.warp_mode_combo.bind('<<ComboboxSelected>>',lambda _:editor.guard(self.warp_mode_changed))
        self.warp_mode_combo.grid(row=1,column=len(fields)+9,sticky="w",padx=6);self.warp_mode_combo.grid_remove()
        self.placement_class.trace_add('write',lambda *_:self.update_switch_option_boxes())
        pagebar=ttk.Frame(right,padding=(0,8,0,4));pagebar.pack(fill="x")
        ttk.Label(pagebar,text="Event page").pack(side="left")
        self.page=tk.StringVar();self.page_combo=ttk.Combobox(pagebar,textvariable=self.page,state="readonly",width=34);self.page_combo.pack(side="left",padx=5)
        self.page_combo.bind("<<ComboboxSelected>>",lambda _:self.load_page())
        ttk.Button(pagebar,text="Add page",command=lambda:editor.guard(self.add_page)).pack(side="left",padx=3)
        ttk.Button(pagebar,text="Delete page",command=lambda:editor.guard(self.delete_page)).pack(side="left",padx=3)
        # page / command clipboards are shared by every event window, so a copy pastes into another event (user 2026-10-25)
        page_menu=tk.Menu(self.window,tearoff=False)
        for label,command in [('Copy page',self.copy_page),('Paste page',self.paste_page),('Clear page',self.clear_page)]:
            page_menu.add_command(label=label,command=lambda c=command:editor.guard(c))
        more=ttk.Menubutton(pagebar,text='Page options');more.configure(menu=page_menu);more.pack(side='left',padx=3)
        # Hidden store of the page's conditions; no undo of its own (an undo emptied it, user 2026-10-23)
        self.conditions=tk.Text(right,height=4,wrap="none",undo=False)
        self.conditions_label=tk.StringVar(value='Always active (no conditions)')
        condition_bar=ttk.LabelFrame(right,text='Page conditions',padding=6);condition_bar.pack(fill='x',pady=4)
        ttk.Label(condition_bar,textvariable=self.conditions_label,wraplength=650).pack(side='left',fill='x',expand=True)
        ttk.Button(condition_bar,text='Remove condition…',command=lambda:editor.guard(self.remove_condition)).pack(side='right',padx=(4,0))
        ttk.Button(condition_bar,text='Add condition…',command=lambda:editor.guard(self.edit_conditions)).pack(side='right')
        self.conditional_presence=tk.BooleanVar(value=True)   # always on: no checkbox
        triggerbar=ttk.Frame(right);triggerbar.pack(fill='x',pady=(3,0))
        ttk.Label(triggerbar,text='Trigger actions').pack(side='left',padx=(0,6))
        self.trigger_tabs=ttk.Notebook(right)   # packed under the command buttons, right above Contents
        self.trigger_tabs.bind('<<NotebookTabChanged>>',lambda _:self.editor.guard(self.on_trigger_tab_changed))
        self.trigger_tab_ids={};self.trigger_controls={};self.active_trigger=None
        trigger_menu=tk.Menu(self.window,tearoff=False)
        for trigger in TRIGGERS:
            trigger_menu.add_command(label=trigger.replace('_',' ').title(),command=lambda t=trigger:self.editor.guard(lambda:self.add_trigger(t)))
        add_trigger=ttk.Menubutton(triggerbar,text='+ Trigger');add_trigger.configure(menu=trigger_menu);add_trigger.pack(side='left')
        ttk.Button(triggerbar,text='Remove trigger',command=lambda:editor.guard(self.remove_trigger)).pack(side='left',padx=4)
        cmdbar=ttk.Frame(right);cmdbar.pack(fill="x")
        self.command_type=tk.StringVar(value="show_dialogue")
        ttk.Button(cmdbar,text="Add command…",command=lambda:editor.guard(self.choose_command)).pack(side="left",padx=5)
        self.action_class=tk.StringVar()
        self.action_class_combo=ttk.Combobox(cmdbar,textvariable=self.action_class,state="readonly",width=30)
        for label,command in [("Up",lambda:self.move_command(-1)),("Down",lambda:self.move_command(1)),("Delete",self.delete_command)]:
            ttk.Button(cmdbar,text=label,command=lambda c=command:editor.guard(c)).pack(side="left",padx=3)
        self.trigger_tabs.pack(fill='x',pady=(4,0))
        from event_contents_ui import contents_tree
        self.commands=contents_tree(right)
        self.commands.bind("<<TreeviewSelect>>",lambda _:self.load_command())
        self.commands.bind('<Double-Button-1>',lambda e:editor.guard(lambda:self.edit_contents(e)))
        self.commands.bind('<Button-3>',self.contents_menu)
        self.commands.bind('<Control-c>',lambda _:editor.guard(self.copy_command))
        self.commands.bind('<Control-x>',lambda _:editor.guard(lambda:self.copy_command(cut=True)))
        self.commands.bind('<Control-v>',lambda _:editor.guard(self.paste_command))
        self.commands.bind('<Delete>',lambda _:editor.guard(self.delete_command))
        ttk.Label(right,text='Contents — double-click a command to edit it, or the empty row to add one.').pack(anchor='w')
        self.command_data=tk.Text(right,height=7,wrap="none",undo=False)   # hidden store; no undo of its own
        bottombar=ttk.Frame(right);bottombar.pack(fill="x")
        # No Apply button: every edit is applied by itself shortly after it is made.
        for sequence in ('<KeyRelease>','<ButtonRelease-1>','<<ComboboxSelected>>'):
            self.window.bind(sequence,lambda _:self.schedule_apply(),add='+')
        ttk.Button(bottombar,text='Done',command=lambda:editor.guard(self.close)).pack(side='right')
        self.window.protocol('WM_DELETE_WINDOW',lambda:editor.guard(self.close))
        self.status=tk.StringVar(value="Create or select a standalone event.")
        ttk.Label(self.window,textvariable=self.status,padding=8,anchor="w").pack(fill="x")
        self.refresh_class_choices()
        self.refresh_list()

    def refresh_list(self,select=None):
        """List only the events on the map being edited (or on the map of the event being opened)."""
        self.events.delete(*self.events.get_children())
        map_id=getattr(self.editor,'current_map',None)
        chosen=next((e for e in self.db.document["event_graphs"] if e["id"]==select),None) if select else None
        if chosen is not None:map_id=chosen["map_id"]
        self.list_map=map_id
        try:self.window.title("Alundra Event Editor" if map_id is None else f"Alundra Event Editor - Map {map_id} {map_label(map_id)}")
        except tk.TclError:pass
        for event in self.db.document["event_graphs"]:
            if map_id is not None and event["map_id"]!=map_id:continue
            x,y,w,h=event["region"];region=f"{x},{y} {w}×{h}"
            trigger=event.get("pages",[{}])[0].get("trigger",event.get("trigger","interact"))
            self.events.insert("","end",iid=event["id"],text=event["name"],values=(f"{event['map_id']} {map_label(event['map_id'])}",trigger,region))
        if select and self.events.exists(select):self.events.selection_set(select);self.events.see(select);self.load_selected()

    def open_project_state(self):
        from project_state_ui import ProjectStateWindow
        self._commit_selected();ProjectStateWindow(self.editor,self.window,database=self.db)

    def new_event(self):
        self._commit_selected()
        map_id=int(self.editor.current_map if self.editor.session else 0)
        row=self.db.new_event_graph(map_id)
        self.refresh_list(row["id"]);self.status.set("New standalone event added to the mod project. Apply edits, then Save mod.")

    def refresh_class_choices(self):
        rows=[row for row in self.db.definitions if row["kind"] in ("npc","enemy","boss","object","item","weapon","armor","unclassified")]
        self.class_choices={"No database object":None}
        self.class_choices.update({f"{row['name']} [{row['kind']}] — {row['id']}":row["id"] for row in rows})
        self.placement_combo.configure(values=list(self.class_choices))
        self.action_class_combo.configure(values=[label for label,value in self.class_choices.items() if value])
        if self.action_class.get() not in self.action_class_combo.cget("values"):
            self.action_class.set(next(iter(self.action_class_combo.cget("values")),""))

    def create_at(self,map_id,x,y):
        """Create a standalone, one-tile RPG-style event at the double-click."""
        self.cancel_close()
        self._commit_selected()
        if not 0<=x<256 or not 0<=y<256:raise ValueError("Event position is outside the map coordinate range")
        row=self.db.new_event_graph(map_id,x=x,y=y)
        row['pages'][0]['trigger']='interact'
        self.window.deiconify();self.window.lift()
        self.refresh_list(row["id"])
        self.keep_changes()   # the new event is on the map straight away (and can be moved)
        self.status.set(f"Created {row['name']} at tile {x}, {y}. Set its pages and commands, then Save mod.")
        def create_warp():
            # Replace the just-created event with a warp on the same tile.
            self.draft.delete_event(row['id']);self.working=None;self.refresh_list()
            self.keep_changes(commit_form=False)
            self.window.withdraw();self.editor.new_warp((x,y))
        def cancelled():
            # Cancel on the picker: no event is made after all.
            self.draft.delete_event(row['id']);self.working=None;self.refresh_list()
            self.keep_changes(commit_form=False)
            self.window.withdraw()
            if self.editor.area:self.editor.area.draw_records()
            self.editor.status.set('No event created.')
        self.choose_page_class(extra_buttons=(('Create Warp',create_warp),),on_cancel=cancelled)

    def choose_page_class(self,extra_buttons=(),on_cancel=None):
        if not self.working:return
        from database_picker import DatabasePicker
        def choose(class_id):
            old_page=dict(self.current_page() or {})
            self.placement_class.set(next((label for label,value in self.class_choices.items() if value==class_id),'No database object'))
            from object_activation import default_event_trigger
            definition=next((r for r in self.db.definitions if r['id']==class_id),None)
            page=self.current_page()
            if page:
                self._commit_command();self._save_active_trigger()
                handlers=ensure_trigger_actions(page)
                if len(handlers)==1:
                    trigger=default_event_trigger(definition);handlers[0]['trigger']=trigger
                    handlers[0]['destroy_after']=trigger=='death' and (definition or {}).get('kind') in ('enemy','boss')
                    self.working.setdefault('native_placement',{}).pop('act_as_npc',None)
                    page['trigger']=trigger;self.active_trigger=trigger;self.refresh_trigger_tabs(trigger)
                source=(definition or {}).get('source',{})
                # Pushable Pillar (One Tile) starts facing Right: it moves in its Direction (user 2026-10-22)
                facing=source.get('default_facing') or ('right' if source.get('catalogue_index')==298 else None)
                if facing:   # e.g. Bombable Rock (Left / Right Side): the class's own side, inherited (not copied)
                    self.default_facing.set(facing);self.working.setdefault('native_placement',{}).pop('facing',None)
                for key in ('animation','animation_static','static_frame'):   # a new class starts on Native
                    self.working.setdefault('native_placement',{}).pop(key,None)
                self.update_idle_animation_control(definition,page);self.update_animation_control(definition)
                if not self.is_native_chest(definition):page.pop('contained_item_class_id',None)
            self._auto_rename(class_event_name(self.name.get().strip(),definition,self._auto_name_bases(old_page)))   # a fresh event takes its class's name
            placement=self.working.get('native_placement',{})
            if placement.pop('behaviour_variant',None):   # a new class starts on Automatic
                placement.pop('donor_map_id',None);placement.pop('donor_entity_index',None)
            self._commit_selected()
            self.keep_changes(commit_form=False)   # its graphic shows on the map at once
            self._refresh_list_names()   # shows any A/B/C renames
            self.update_chest_contents_control()
            self.update_behaviour_control()
            self.show_page_graphic()
            if self.editor.area:self.editor.area.draw_records()
            if self.is_native_chest(definition):self.choose_chest_item()
            if (definition or {}).get('source',{}).get('variant')=='warp_panel':self.choose_warp_destination()   # it asks where it leads
        DatabasePicker(self.editor,self.window,choose,extra_buttons=extra_buttons,on_cancel=on_cancel,
                       use_tile=lambda:self.choose_tile_graphic(choose))

    def choose_tile_graphic(self,choose_class):
        """Use Tile: a map tile (from any map) becomes this event's graphic, painted at its tile."""
        if not self.working:return
        from map_tile_picker import MapTileDialog
        event_id=self.working['id']
        def picked(m,x,y,z):
            if not self.working or self.working['id']!=event_id:raise ValueError('Another event is open now; choose the tile again')
            choose_class(None)   # an empty event whose graphic is the tile
            self.working.setdefault('native_placement',{})['tile_graphic']={'map':int(m),'x':int(x),'y':int(y)}
            self.apply_tile_graphic()
        MapTileDialog(self.editor,self.window,lambda m,x,y,z:self.editor.guard(lambda:picked(m,x,y,z)),
                      map_id=self.editor.current_map,title='Use Tile: Choose The Event Graphic',confirm='Use This Tile')

    def apply_tile_graphic(self):
        """Use Tile: the tile is this event's graphic. Nothing is painted on the map here;
        the game build puts its picture at the event (floor only, or with its wall pieces
        drawn over the player when Use as mask is ticked). No hitbox: walking is unchanged."""
        placement=(self.working or {}).get('native_placement') or {}
        tile=placement.get('tile_graphic')
        if not tile:return
        placement['tile_mask']=bool(self.tile_mask.get())
        self._commit_selected();self.keep_changes(commit_form=False);self.update_tile_mask_box();self.show_page_graphic()
        if self.editor.area:self.editor.area.draw_records()
        self.status.set(f"Event graphic: tile {tile['x']}, {tile['y']} of map {tile['map']}"+(' (masks the player)' if placement['tile_mask'] else '')+'.')

    def update_tile_mask_box(self):
        if not hasattr(self,'tile_mask_box'):return
        placement=(self.working or {}).get('native_placement') or {}
        self.tile_mask.set(bool(placement.get('tile_mask')))
        if placement.get('tile_graphic'):self.tile_mask_box.grid()
        else:self.tile_mask_box.grid_remove()

    def _auto_name_bases(self,page):
        """Names this event may have been given automatically (class / chest item)."""
        ids=[(page or {}).get('class_id',(self.working or {}).get('class_id')),(page or {}).get('contained_item_class_id')]
        return [row['name'] for row in self.db.definitions if row['id'] in ids]

    def _refresh_list_names(self):
        for event in self.db.document["event_graphs"]:
            if self.events.exists(event["id"]):self.events.item(event["id"],text=event["name"])

    def _auto_rename(self,base):
        if not self.working or base==self.name.get().strip():return
        map_id=self.working['map_id']
        self.name.set(self.db.lettered_event_name(map_id,base,self.working['id']))

    @staticmethod
    def is_native_chest(definition):
        return bool(definition and definition.get('kind')=='object'
                    and definition.get('source',{}).get('catalogue_index')==30)

    def update_behaviour_control(self):
        """Objects, enemies and bosses: pick which original map's scripts they run."""
        page=self.current_page()
        class_id=(page or {}).get('class_id',(self.working or {}).get('class_id'))
        definition=next((row for row in self.db.definitions if row['id']==class_id),None)
        catalogue=(definition or {}).get('source',{}).get('catalogue_index')
        if not definition or definition.get('kind') not in ('object','enemy','boss') or type(catalogue) is not int:
            self.behaviour_frame.pack_forget();return
        from behavior_transplant import behaviour_variants,variant_label
        cache=getattr(self.editor,'behaviour_variant_cache',None)
        if cache is None:cache=self.editor.behaviour_variant_cache={}
        from behavior_transplant import FIXED_DONOR_CLASSES
        from stock_donors import behaviour_variants as stock_variants   # the original game's copies, whatever the maps are now
        variants=[] if catalogue in FIXED_DONOR_CLASSES else stock_variants(self.editor.session,catalogue,cache)
        self.behaviour_choices={'Automatic':None}
        for number,variant in enumerate(variants,1):
            self.behaviour_choices[variant_label(number,variant)]=(variant['donor_map'],variant['entity_index'])
        self.behaviour_combo.configure(values=list(self.behaviour_choices),state='readonly' if len(variants)>1 else 'disabled')
        placement=(self.working or {}).get('native_placement',{})
        chosen=(placement.get('donor_map_id'),placement.get('donor_entity_index'))
        label=next((k for k,v in self.behaviour_choices.items() if v==chosen),'Automatic') if placement.get('behaviour_variant') else 'Automatic'
        self.behaviour.set(label)
        if catalogue in FIXED_DONOR_CLASSES:
            self.behaviour_note.set('Uses its tested behaviour.')
        elif not variants:
            self.behaviour_note.set('No original map places this; it runs its class AI only.')
        elif len(variants)==1:
            self.behaviour_note.set('Every original copy runs the same scripts.')
        else:
            self.behaviour_note.set(f'{len(variants)} different behaviours in the game. Each runs the scripts it has on that map.')
        if not self.behaviour_frame.winfo_manager():
            self.behaviour_frame.pack(fill='x',pady=(2,6))

    def apply_behaviour(self):
        if not self.working:return
        placement=self.working.setdefault('native_placement',{})
        choice=self.behaviour_choices.get(self.behaviour.get())
        if choice is None:
            if placement.pop('behaviour_variant',None):
                placement.pop('donor_map_id',None);placement.pop('donor_entity_index',None)
            self.status.set('Behaviour: Automatic (the editor picks a copy from the game).')
        else:
            placement.update(donor_map_id=choice[0],donor_entity_index=choice[1],behaviour_variant=True)
            self.status.set(f'Behaviour copied from map {choice[0]} (its scripts are installed on this map at Build).')
        self._commit_selected()

    def update_chest_contents_control(self):
        page=self.current_page()
        class_id=(page or {}).get('class_id')
        definition=next((row for row in self.db.definitions if row['id']==class_id),None)
        if not self.is_native_chest(definition):
            self.chest_contents_frame.pack_forget();return
        item_id=page.get('contained_item_class_id',definition.get('data',{}).get('contained_item_class_id'))
        item=next((row for row in self.db.definitions if row['id']==item_id),None)
        self.chest_contents_label.set(f"Item: {item['name']}" if item else 'No item selected yet')
        if not self.chest_contents_frame.winfo_manager():
            self.chest_contents_frame.pack(fill='x',pady=(2,6),after=self.page_graphic)   # right below the event graphic (user 2026-10-22)

    def choose_chest_item(self):
        page=self.current_page()
        if not page:raise ValueError('Choose a chest event page first')
        class_id=page.get('class_id',self.working.get('class_id'))
        definition=next((row for row in self.db.definitions if row['id']==class_id),None)
        if not self.is_native_chest(definition):raise ValueError('Choose the native Chest object first')
        from database_picker import DatabasePicker
        def choose(item_class_id):
            if item_class_id is None:return
            page=self.current_page();old_page=dict(page)
            page['contained_item_class_id']=item_class_id
            item=next((row for row in self.db.definitions if row['id']==item_class_id),None)
            if item and is_auto_name(self.name.get().strip(),self._auto_name_bases(old_page)):
                self._auto_rename(item['name'])   # a chest is named after what it holds
            self._commit_selected();self.update_chest_contents_control()
            self._refresh_list_names()
            if self.editor.area:self.editor.area.draw_records()
        DatabasePicker(self.editor,self.window,choose,kinds=('item',))

    def default_route_changed(self):
        if not self.working:return
        if self.default_route_mode.get()=='Route' and not self.current_page().get('default_move_route'):
            self.edit_default_route()

    def edit_default_route(self):
        if not self.working:raise ValueError('Choose an event first')
        from event_command_dialog import CommandDialog
        page=self.current_page()
        row=deepcopy(page.get('default_move_route') or dict(type='move_actor',target='this_event',mode='route',route=['down'],movement_speed=100,blocked_behavior="wait"))
        row.pop('repeat',None);row['movement_speed']=int(self.default_route_speed.get(),0)
        def save(value):
            page=self.current_page()   # re-found: self.working may have been replaced meanwhile
            value.pop('skip_impossible',None);value['blocked_behavior']='wait';value['repeat']=self.default_route_repeat.get()
            page['default_move_route']=value;self.default_route_mode.set('Route');self.default_route_speed.set(str(value['movement_speed']))
            self.editor.dirty=True
        CommandDialog(self.editor,self.window,row,save,database=self.db)

    def change_default_facing(self):
        if not self.working:return
        self._commit_selected();self.show_page_graphic()
        if self.editor.area:self.editor.area.draw_records()

    def refresh_gate_binding(self,cid):
        row=self.db.get(cid) if cid else None
        if row and row.get('source',{}).get('catalogue_index')==314:
            self.rolling_target_frame.pack(fill='x',before=self.facing_combo.master)
            target=(self.working or {}).get('native_placement',{}).get('finish_tile')
            self.rolling_target_enabled.set(isinstance(target,dict))
            self.rolling_target_x.set(str((target or {}).get('x',(self.working or {}).get('region',[0,0])[0])));self.rolling_target_y.set(str((target or {}).get('y',(self.working or {}).get('region',[0,0])[1])))
        else:
            self.rolling_target_frame.pack_forget();self.rolling_target_enabled.set(False)
            if self.working:self.working.get('native_placement',{}).pop('finish_tile',None)
        if row and row.get('kind') in ('enemy','boss'):
            self.act_as_npc_frame.pack(fill='x',before=self.facing_combo.master)
            self.act_as_npc.set(bool((self.working or {}).get('native_placement',{}).get('act_as_npc')))
        else:
            self.act_as_npc_frame.pack_forget();self.act_as_npc.set(False)
            if self.working:self.working.get('native_placement',{}).pop('act_as_npc',None)
        if row and row.get('source',{}).get('catalogue_index')==308:
            self.rotation_frame.pack(fill='x',before=self.facing_combo.master)
            self.rotation_control.set((self.working or {}).get('native_placement',{}).get('rotation_controller',False))
        else:
            self.rotation_frame.pack_forget();self.rotation_control.set(False)
            if self.working:self.working.get('native_placement',{}).pop('rotation_controller',None)
        from behavior_transplant import SPAWN_CHOICE_CATALOGUES
        if row and row.get('source',{}).get('catalogue_index') in SPAWN_CHOICE_CATALOGUES:
            self.spawned_frame.pack(fill='x',before=self.facing_combo.master)
            names=spawn_choice_names(self.db);self.spawned_combo.configure(values=['(stock)']+list(names))
            current=(self.working or {}).get('native_placement',{}).get('spawned_class')
            self.spawned_class.set(next((n for n,c in names.items() if c==current),'(stock)'))
        else:
            self.spawned_frame.pack_forget();self.spawned_class.set('(stock)')
            if self.working:self.working.get('native_placement',{}).pop('spawned_class',None)
        from native_freezable_flame import FREEZABLE_CATALOGUES
        if row and row.get('source',{}).get('catalogue_index') in FREEZABLE_CATALOGUES:
            self.freezable_frame.pack(fill='x',before=self.facing_combo.master)
            self.fireballs_freezable.set(bool((self.working or {}).get('native_placement',{}).get('fireballs_freezable')))
            self.always_fire.set(bool((self.working or {}).get('native_placement',{}).get('always_fire')))
            _r=(self.working or {}).get('native_placement',{}).get('trigger_range');self.trigger_range.set('' if _r is None else str(_r))
        else:
            self.freezable_frame.pack_forget();self.fireballs_freezable.set(False)
            if self.working:
                for _k in ('fireballs_freezable','always_fire','trigger_range'):self.working.get('native_placement',{}).pop(_k,None)
        if row and row.get('source',{}).get('variant')=='push_stool':
            self.stool_frame.pack(fill='x',before=self.facing_combo.master)
            from native_pushable_stool import allowed as _allowed
            _on=_allowed((self.working or {}).get('native_placement',{}))
            for d,var in self.stool_dirs.items():var.set(d in _on)
            _t=(self.working or {}).get('native_placement',{}).get('target_tile')
            self.stool_target.set(f"{_t['x']}, {_t['y']}" if isinstance(_t,dict) else 'None')
            self.stool_once.set(bool((self.working or {}).get('native_placement',{}).get('move_once')))
        else:
            self.stool_frame.pack_forget()
            if self.working:
                for _k in ('push_directions','target_tile','move_once'):self.working.get('native_placement',{}).pop(_k,None)
        if row and row.get('source',{}).get('catalogue_index') in (325,326):
            self.gate_binding_frame.pack(fill='x',before=self.facing_combo.master)
            identity=(self.working or {}).get('native_placement',{}).get('open_switch_id')
            from project_state_ui import state_label
            self.gate_binding_label.set(state_label(self.db,'switches',identity) if type(identity) is int else 'Choose switch…')
        else:
            self.gate_binding_frame.pack_forget()
            if self.working:self.working.get('native_placement',{}).pop('open_switch_id',None)

    def choose_stool_target(self,clear=False):
        """Stool (Pushable): the tile whose arrival runs the Activate actions (native_pushable_stool)."""
        if not self.working:return
        placement=self.working.setdefault('native_placement',{})
        def picked(_map,x,y,z):
            placement['target_tile']={'x':int(x),'y':int(y)};self.stool_target.set(f'{int(x)}, {int(y)}');self.editor.dirty=True
        if clear:
            placement.pop('target_tile',None);self.stool_target.set('None');self.editor.dirty=True;return
        from map_tile_picker import MapTileDialog
        _t=placement.get('target_tile') or {}
        region=self.working.get('region') or [0,0]
        MapTileDialog(self.editor,self.window,lambda m,x,y,z:self.editor.guard(lambda:picked(m,x,y,z)),map_id=self.working.get('map_id',self.editor.current_map),
                      x=_t.get('x',region[0]),y=_t.get('y',region[1]),title='Choose Tile On This Map',fixed_map=True)

    def rolling_target_changed(self):
        if self.rolling_target_enabled.get():self.default_facing.set('up')
        self._commit_selected();self.show_page_graphic()

    def choose_gate_switch(self):
        if not self.working:return
        from project_state_ui import StateSelector
        win=tk.Toplevel(self.window);win.title('Open when switch is ON');win.transient(self.window);win.grab_set()
        identity=self.working.get('native_placement',{}).get('open_switch_id')
        selector=StateSelector(win,self.db,'switches',{'switch_scope':'project','switch_id':identity},self.editor)
        selector.frame.pack(fill='both',expand=True,padx=8,pady=8)
        # This explicit gate binding is private project state, never a story flag.
        for child in selector.frame.winfo_children():
            if isinstance(child,ttk.Combobox):child.configure(values=('My project',),state='disabled')
        def confirm():
            value=selector.value()
            if value.get('switch_scope')!='project':raise ValueError('Gate opening uses a project switch')
            self.working.setdefault('native_placement',{})['open_switch_id']=value['switch_id']
            self._commit_selected();self.show_page_graphic();win.destroy()
        bar=ttk.Frame(win);bar.pack(fill='x',padx=8,pady=8)
        ttk.Button(bar,text='Cancel',command=win.destroy).pack(side='right')
        ttk.Button(bar,text='OK',command=lambda:self.editor.guard(confirm)).pack(side='right',padx=6)

    def show_page_graphic(self):
        from database_catalogue import reference_image
        from PIL import Image,ImageTk
        canvas=self.page_graphic;canvas.delete('all');width=max(200,canvas.winfo_width())
        cid=self.class_choices.get(self.placement_class.get())
        self.refresh_gate_binding(cid)
        tile=((self.working or {}).get('native_placement') or {}).get('tile_graphic')
        if cid is None and tile:
            from tile_event_graphic import tile_image
            image=tile_image(self.editor.session,tile)
            if image is None:canvas.create_text(width/2,75,text=f"Tile graphic\nMap {tile['map']}, tile {tile['x']}, {tile['y']}",fill='#b8c2d2');return
            scale=max(1,min(6,int(min((width-20)/image.width,130/image.height))))
            self.page_photo=ImageTk.PhotoImage(image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST),master=canvas)
            canvas.create_image(width/2,75,image=self.page_photo,anchor='center');return
        if cid is None:canvas.create_text(width/2,75,text='No graphic\nStandalone map event',fill='#b8c2d2');return
        row=self.db.get(cid)
        from project_event_preview import event_world_image
        image=event_world_image(self.editor.session,row,int(self.map_id.get()),self.default_facing.get())
        if image is None:image=reference_image(self.editor.session,row,database=False)
        if image is not None:
            scale=max(1,min(4,int(min((width-16)/image.width,120/image.height))))
            photo=ImageTk.PhotoImage(image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST));canvas.image=photo
            canvas.create_image(width/2,65,image=photo)
        canvas.create_text(width/2,137,text=row['name'],fill='#e7eaf0')

    def bind_native_process(self):
        if not self.working:raise ValueError('Select an event first')
        from event_native_compile import native_binding,dialogue_binding
        from event_editor import script_roots,instructions
        from map_text import dialogue_entry
        self._commit_form();map_id=self.working['map_id']
        keys=[key for key in script_roots(self.editor.session,map_id) if key.startswith(('F ','D '))]
        win=tk.Toplevel(self.window);win.title('Choose existing Alundra process to replace')
        ttk.Label(win,text='This replaces an existing interaction or touch process. It preserves its actor and uses the existing space.',wraplength=650,padding=8).pack(fill='x')
        tree=ttk.Treeview(win,columns=('instructions',),show='tree headings',height=14);tree.heading('#0',text='Process');tree.heading('instructions',text='Instructions');tree.pack(fill='both',expand=True,padx=8)
        for key in keys:tree.insert('','end',iid=key,text=key,values=(len(instructions(self.editor.session,map_id,key)),))
        def bind():
            if not tree.selection():raise ValueError('Choose a process')
            key=tree.selection()[0];binding=native_binding(self.editor.session,map_id,key)
            page=self.current_page();commands=[]
            for offset,opcode,size in instructions(self.editor.session,map_id,key):
                if opcode in (5,6):
                    import struct
                    operand=struct.unpack_from('<H',self.editor.session.data,offset+1)[0]
                    commands.append({'type':'set_switch','switch_id':operand,'native_flag_operand':operand,'value':opcode==5})
                elif opcode in (0x0d,0x5c):
                    text=dialogue_entry(self.editor.session,map_id,offset)
                    if text:commands.append(dict(type='show_dialogue',speaker=None,text=text[2].decode('latin-1'),**dialogue_binding(self.editor.session,map_id,offset)))
                elif opcode==0xA7 and self.editor.session.data[offset+2]==0:
                    commands.append(dict(type='change_music',music_id=self.editor.session.data[offset+1]))
                elif opcode==0x75:
                    commands.append(dict(type='stop_sound',sound_id=self.editor.session.data[offset+1]))
                elif opcode==0x53:
                    import struct
                    dest,x,y,z,effect,sound=struct.unpack_from('<H5B',self.editor.session.data,offset+1)
                    commands.append(dict(type='warp_player',map_id=dest,x=x,y=y,z=z))
                elif opcode!=255:raise ValueError(f'Process {key} contains an unsupported command ({opcode:02X}); its original behavior was preserved.')
            self._commit_current_page();page=self.current_page()
            trigger='interact' if key.startswith('F ') else 'touch'
            self.working['native_binding']=binding;page['commands']=commands;page['conditions']=[];page['class_id']=None
            page['trigger']=trigger;page['trigger_actions']=[{'trigger':trigger,'commands':deepcopy(commands),'hit_sources':[],'destroy_after':False}]
            self.working['pages']=[page];self.page_trigger.set(trigger);self.placement_class.set('No database object')
            self.page_id=page['id'];self.conditions.delete('1.0','end');self.conditions.insert('1.0','[]');self.command_index=None
            self._commit_selected();self.refresh_pages();win.destroy()
            self.status.set(f'Bound to existing {key}. Supported commands will compile within its original space when you Build game.')
        ttk.Button(win,text='Use this process',command=lambda:self.editor.guard(bind)).pack(padx=8,pady=8)

    def open_event(self,event_id):
        self._commit_selected()
        self.window.deiconify();self.window.lift()
        self.refresh_class_choices();self.refresh_list(event_id)

    def load_selected(self):
        selected=self.events.selection()
        if not selected:return
        if self.working and self.working["id"]!=selected[0]:self._commit_selected()
        if self.working and self.working['id']==selected[0]:return
        self.working=deepcopy(next(e for e in self.db.document["event_graphs"] if e["id"]==selected[0]))
        self.name.set(self.working["name"]);self.map_id.set(str(self.working["map_id"]))
        self.x.set(str(self.working["region"][0]));self.y.set(str(self.working["region"][1]));self.w.set(str(self.working["region"][2]));self.h.set(str(self.working["region"][3]))
        self.conditional_presence.set(self.working.get('native_placement',{}).get('presence_by_page_condition',True) is not False)
        from class_instance import effective_placement,graph_class_id
        self.default_facing.set(effective_placement(self.working,self.db.get(graph_class_id(self.working)) if graph_class_id(self.working) else None).get('facing','down'))
        z=self.working.get('native_placement',{}).get('height')
        self.z_auto=None
        if z is None:z=self.z_auto=self.tile_z(self.working['map_id'],*self.working['region'][:2])
        self.z_height.set('' if z is None else str(z))
        self.lower_one.set(bool(self.working.get('native_placement',{}).get('lower_one')))
        self.flush_floor.set(bool(self.working.get('native_placement',{}).get('flush_with_floor')))
        self.while_pressured.set(bool(self.working.get('native_placement',{}).get('while_pressured')))
        if hasattr(self,'ignore_spring_bean'):self.ignore_spring_bean.set(bool(self.working.get('native_placement',{}).get('ignore_spring_bean')))
        if hasattr(self,'plate_flush'):self.plate_flush.set(self.working.get('native_placement',{}).get('plate_flush',True) is not False)
        self.update_while_pressured_box()
        self.sword_only.set(bool(self.working.get('native_placement',{}).get('sword_only')))
        self.bomb_activation.set(bool(self.working.get('native_placement',{}).get('bomb_activation')))
        self.start_symbol.set(('Star','Moon','Water','Sun')[int(self.working.get('native_placement',{}).get('start_symbol',0) or 0)&3])
        self.fail_stops_others.set(self.working.get('native_placement',{}).get('fail_stops_others',True) is not False)
        self.active_by_default.set(bool(self.working.get('native_placement',{}).get('active_by_default',self.is_statue_variant())))
        self.keep_state.set(bool(self.working.get('native_placement',{}).get('keep_state')))
        self.can_deactivate.set(bool(self.working.get('native_placement',{}).get('can_deactivate')))
        self.play_victory.set(self.working.get('native_placement',{}).get('play_victory',True) is not False)
        self.track_player.set(bool(self.working.get('native_placement',{}).get('track_player',self.track_player_default())))
        self.instant_respawn.set(bool(self.working.get('native_placement',{}).get('instant_respawn',False)))
        self.update_tile_mask_box()
        self.update_switch_option_boxes()
        self.offset_x.set(offset_label(self.working.get('native_placement',{}).get('offset_x',0)));self.offset_y.set(offset_label(self.working.get('native_placement',{}).get('offset_y',0)))
        self.direction_fix.set(bool(self.working.get('native_placement',{}).get('direction_fix')))
        self.refresh_class_choices()
        self.page_id=None;self.refresh_pages()

    def refresh_pages(self,select=None):
        if not self.working:return
        pages=self.working["pages"];self.page_names={f"{i+1}. {p['name']} [{p['id']}]":p["id"] for i,p in enumerate(pages)}
        values=list(self.page_names);chosen=select or self.page_id or (pages[0]["id"] if pages else None)
        self.page_combo.configure(values=values);self.page.set(next((n for n,i in self.page_names.items() if i==chosen),values[0] if values else ""));self.page_id=self.page_names.get(self.page.get())
        self.load_page()

    def current_page(self):
        return next((p for p in self.working["pages"] if p["id"]==self.page_id),None) if self.working else None

    def load_page(self):
        if not self.working:return
        new_page_id=self.page_names.get(self.page.get(),self.page_id)
        if self.page_id and new_page_id!=self.page_id:self._commit_current_page()
        self.page_id=new_page_id
        page=self.current_page()
        if not page:return
        handlers=ensure_trigger_actions(page)
        page['trigger']=handlers[0]['trigger'];page['commands']=deepcopy(handlers[0].get('commands',[]))
        self.page_trigger.set(TRIGGER_LABELS[page['trigger']])
        page_class=page.get("class_id",self.working.get("class_id"))
        self.placement_class.set(next((label for label,value in self.class_choices.items() if value==page_class),"No database object"))
        if hasattr(self,'act_as_npc'):
            self.act_as_npc.set(bool(page.get('act_as_npc') or (self.working or {}).get('native_placement',{}).get('act_as_npc')))
            self.update_switch_option_boxes()
        definition=next((r for r in self.db.definitions if r['id']==page_class),None)
        if hasattr(self,'float_enabled'):
            self.float_enabled.set(bool(page.get('float')));self.float_height.set(str(page.get('float_height',0)))
        from native_nirude_face import is_face as _is_face
        from native_nirude_statue_variants import variant_of as _statue_variant
        if definition and ((definition.get('source',{}).get('catalogue_index') in SWITCH_CLASSES \
                and (((self.working or {}).get('native_placement') or {}).get('can_deactivate') or definition.get('source',{}).get('variant')=='push_stool')) \
                or _is_face(definition) or _statue_variant(definition)) \
                and not any(h.get('trigger')=='deactivate' for h in handlers):
            # Can Deactivate ticked: the switch has a Deactivate tab (user 2026-10-14)
            handlers.append({'trigger':'deactivate','commands':[],'hit_sources':[],'destroy_after':False})
        self.update_idle_animation_control(definition,page);self.update_animation_control(definition)
        self.update_chest_contents_control()
        self.update_behaviour_control()
        route=page.get('default_move_route')
        self.default_route_mode.set('Route' if route else 'Native')
        self.default_route_speed.set(str((route or {}).get('movement_speed',100)))
        self.default_route_repeat.set((route or {}).get('repeat',True))
        self.show_page_graphic()
        self.conditions.delete("1.0","end");self.conditions.insert("1.0",json.dumps(page["conditions"],indent=2))
        self.update_conditions_label()
        self.command_index=None;self.refresh_trigger_tabs(handlers[0]['trigger']);self.refresh_commands()

    def update_animation_control(self,definition):
        """Show the Animation / Static choice for NPCs, listing the class's animations."""
        if not definition or definition.get('kind')!='npc':
            self.animation_frame.pack_forget();return
        values=['Native']
        try:
            from animation_preview import available_animations
            cat=definition.get('source',{}).get('catalogue_index')
            map_id=int(self.map_id.get(),0)
            for a in available_animations(self.editor.session,map_id,cat):
                frames=max(a['direction_frames']) if a['direction_frames'] else 0
                values.append(f"{a['index']} ({frames} frame{'s' if frames!=1 else ''})")
        except Exception:
            values+= [str(i) for i in range(16)]
        self.npc_animation_combo.configure(values=values)
        placement=(self.working or {}).get('native_placement',{})
        chosen=placement.get('animation')
        self.npc_animation.set(next((v for v in values[1:] if v.split()[0]==str(chosen)),'Native') if chosen is not None else 'Native')
        self.animation_static.set(bool(placement.get('animation_static')))
        self.static_frame.set(str(placement.get('static_frame',0)))
        if not self.animation_frame.winfo_manager():self.animation_frame.pack(fill='x',pady=(4,0))

    def animation_choice_changed(self):
        if self.npc_animation.get()=='Native':self.animation_static.set(False)
        self._commit_selected();self.schedule_apply()

    def has_native_idle_animation(self,definition):
        eligible=False
        if definition and (definition.get('kind')=='npc' or definition.get('name','').casefold() in ('dog','chicken','crow')):
            source=definition.get('source',{});catalogue=source.get('catalogue_index')
            if self.editor.session is not None and type(catalogue) is int:
                try:
                    from event_movement_compile import animation_profile
                    maps=source.get('observed_maps') or [self.editor.current_map]
                    profile=animation_profile(self.editor.session.data,catalogue,maps[0] if catalogue>=256 else None)
                    eligible=any(row['speed']==0 and any(row['directions_valid']) for row in profile)
                except (ValueError,IndexError,TypeError):eligible=False
        return eligible

    def update_idle_animation_control(self,definition,page=None):
        eligible=self.has_native_idle_animation(definition)
        if eligible:
            if not self.idle_animation_check.winfo_manager():self.idle_animation_check.pack(anchor='w',pady=2)
            self.idle_animation_enabled.set((page or {}).get('idle_animation_enabled',True))
        else:
            self.idle_animation_check.pack_forget();self.idle_animation_enabled.set(True)

    def refresh_trigger_tabs(self,select_trigger=None):
        for tab in tuple(self.trigger_tabs.tabs()):
            widget=self.trigger_tabs.nametowidget(tab);self.trigger_tabs.forget(tab);widget.destroy()
        self.trigger_tab_ids={};self.trigger_controls={}
        page=self.current_page()
        if not page:return
        for handler in ensure_trigger_actions(page):
            trigger=handler['trigger'];frame=ttk.Frame(self.trigger_tabs,padding=(8,3));self.trigger_tabs.add(frame,text=trigger.replace('_',' ').title())
            self.trigger_tab_ids[str(frame)]=trigger
            destroy=tk.BooleanVar(value=handler.get('destroy_after',False));self.trigger_controls[trigger]={'destroy':destroy,'sources':{}}
            if trigger=='hit':
                ttk.Label(frame,text='Only when hit by:').pack(side='left')
                selected=set(handler.get('hit_sources',[]))
                for source in HIT_SOURCES:
                    var=tk.BooleanVar(value=source in selected);self.trigger_controls[trigger]['sources'][source]=var
                    ttk.Checkbutton(frame,text=source.replace('_',' ').title(),variable=var).pack(side='left',padx=3)
        target=next((str(tab) for tab in self.trigger_tabs.tabs() if self.trigger_tab_ids.get(str(tab))==select_trigger),None)
        if target:self.trigger_tabs.select(target)
        self.active_trigger=select_trigger or (ensure_trigger_actions(page)[0]['trigger'])
        self._load_active_trigger()

    def _save_active_trigger(self):
        page=self.current_page()
        if not page or not self.active_trigger:return
        handlers=ensure_trigger_actions(page);handler=next((r for r in handlers if r['trigger']==self.active_trigger),None)
        if handler is None:return
        handler['commands']=deepcopy(page.get('commands',[]))
        controls=self.trigger_controls.get(self.active_trigger,{})
        if controls:
            handler['destroy_after']=controls['destroy'].get()
            if self.active_trigger=='hit':handler['hit_sources']=[key for key,var in controls['sources'].items() if var.get()]
        if handlers and handlers[0]['trigger']==self.active_trigger:
            page['trigger']=self.active_trigger;self.page_trigger.set(TRIGGER_LABELS[self.active_trigger])

    def _load_active_trigger(self):
        controls=self.trigger_controls.get(self.active_trigger) if hasattr(self,'trigger_controls') else None
        if controls and hasattr(self,'destroy_check'):
            self.destroy_check.configure(variable=controls['destroy'])
            self.destroy_check.state(['!disabled'])   # on by default for enemies/bosses (set when the class is chosen), never forced
        page=self.current_page()
        if not page:return
        handler=next((r for r in ensure_trigger_actions(page) if r['trigger']==self.active_trigger),None)
        if handler is None:return
        page['commands']=deepcopy(handler.get('commands',[]));self.page_trigger.set(TRIGGER_LABELS[self.active_trigger])
        self.command_index=None;self.refresh_commands()

    def page_kind(self):
        page=self.current_page() if self.working else None
        class_id=(page or {}).get('class_id',(self.working or {}).get('class_id'))
        row=self.db.get(class_id) if class_id else None
        return (row or {}).get('kind')

    def act_as_npc_changed(self):
        """Act as NPC: the enemy's first trigger becomes Interact; unticked, Death (destroy on)."""
        if not self.working:return
        page=self.current_page()
        if page:
            self._commit_command();self._save_active_trigger()
            handlers=ensure_trigger_actions(page)
            trigger='interact' if self.act_as_npc.get() else 'death'
            if trigger not in {r['trigger'] for r in handlers[1:]}:
                handlers[0]['trigger']=trigger;handlers[0]['destroy_after']=trigger=='death'
                page['trigger']=trigger;self.active_trigger=trigger;self.refresh_trigger_tabs(trigger)
        self._commit_selected();self.schedule_apply()

    def on_trigger_tab_changed(self):
        if not self.working:return
        selected=str(self.trigger_tabs.select());trigger=self.trigger_tab_ids.get(selected)
        if not trigger or trigger==self.active_trigger:return
        self._commit_command();self._save_active_trigger();self.active_trigger=trigger;self._load_active_trigger()

    def add_trigger(self,trigger):
        if not self.working:raise ValueError('Select an event page first')
        self._commit_command();self._save_active_trigger();page=self.current_page();handlers=ensure_trigger_actions(page)
        if trigger in {row['trigger'] for row in handlers}:raise ValueError('That trigger already has a tab on this page')
        if len(handlers)>=len(TRIGGERS):raise ValueError('This page already has the maximum trigger tabs')
        handlers.append({'trigger':trigger,'commands':[],'hit_sources':[],'destroy_after':trigger=='death' and self.page_kind() in ('enemy','boss')})   # on by default, can be unticked
        validate_event_graph(self.working);self.refresh_trigger_tabs(trigger);self.editor.dirty=True

    def remove_trigger(self):
        if not self.working:raise ValueError('Select an event page first')
        self._commit_command();self._save_active_trigger();page=self.current_page();handlers=ensure_trigger_actions(page)
        if len(handlers)<=1:raise ValueError('An event page must keep at least one trigger tab')
        handlers[:]=[row for row in handlers if row['trigger']!=self.active_trigger]
        self.refresh_trigger_tabs(handlers[0]['trigger']);self.editor.dirty=True

    def schedule_apply(self,delay=600):
        """Apply edits a moment after they are made (no Apply button)."""
        job=getattr(self,'apply_job',None)
        if job is not None:
            try:self.editor.root.after_cancel(job)
            except Exception:pass
        self.apply_job=self.editor.root.after(delay,self.auto_apply)

    def auto_apply(self):
        self.apply_job=None
        if not self.working or self.closing():return
        try:
            if not self.window.winfo_exists():return
            from copy import deepcopy
            before=deepcopy(self.editor.database.document.get('event_graphs'));dirty=self.editor.dirty
            self.keep_changes()
            if self.editor.database.document.get('event_graphs')==before:self.editor.dirty=dirty
        except Exception as exc:
            # Half-typed values (for example an empty number) wait until they are valid.
            self.status.set(f'Not applied yet: {exc}')

    def refresh_commands(self,select=None):
        self.schedule_apply()
        self.commands.delete(*self.commands.get_children());page=self.current_page()
        if not page:return
        from event_command_dialog import LABELS,summary
        # Row ids are paths: "2", "2:then:0", "2:then:0:else:1"; "<path>:<branch>:add" adds to a branch.
        def rows(commands,prefix,indent,label):
            for i,row in enumerate(commands):
                iid=f'{prefix}{i}'
                self.commands.insert('','end',iid=iid,values=(indent+label+LABELS[row['type']],summary(row,self.db)))
                asks=row['type']=='ask_question'
                if asks:row.setdefault('then',[]);row.setdefault('else',[])
                branches=([('then','If Yes'),('else','If No')] if asks else [('then','If true'),('else','Else')] if row['type']=='if'
                          else [('commands','Repeat')] if row['type']=='repeat' else [])
                for branch,name in branches:
                    rows(row.get(branch,[]),f'{iid}:{branch}:',indent+'    ',name+' · ')
                    self.commands.insert('','end',iid=f'{iid}:{branch}:add',values=(indent+'    '+name+' · ◇','Add command…'))
        rows(page["commands"],'','','')
        self.commands.insert('','end',iid='new',values=('◇','Add command…'))
        if select is not None and self.commands.exists(str(select)):
            self.commands.selection_set(str(select));self.commands.see(str(select));self.load_command()

    def load_command(self):
        selected=self.commands.selection();page=self.current_page()
        if not selected or not page:return
        if selected[0]=='new' or ':' in selected[0]:self.command_index=None;return
        self.command_index=int(selected[0]);self.command_data.delete("1.0","end")
        self.command_data.insert("1.0",json.dumps(page["commands"][self.command_index],indent=2,ensure_ascii=False))

    def _commit_command(self):
        if self.command_index is None:return
        try:row=json.loads(self.command_data.get("1.0","end"))
        except json.JSONDecodeError:self.command_index=None;return   # unreadable store: keep the command as it was
        candidate=deepcopy(self.working);page=next(p for p in candidate["pages"] if p["id"]==self.page_id)
        page["commands"][self.command_index]=row;validate_event_graph(candidate)
        self.working=candidate

    def add_command(self):
        if not self.working:raise ValueError("Create or select a standalone event first")
        self._commit_form();page=self.current_page();self._commit_command()
        page=self.current_page();page["commands"].append(command_template(self.command_type.get()))
        validate_event_graph(self.working);self.refresh_commands(len(page["commands"])-1)

    def choose_command(self,where=None):
        """where: a Contents row id; inside an If / Repeat (its rows or its
        'Add command…' row) the new command goes into that branch."""
        if not self.working:raise ValueError('Create or select an event first')
        if where is None:
            sel=self.commands.selection();where=sel[0] if sel else None
        self.insert_target=None
        if where and ':' in str(where):self.insert_target=str(where)
        from event_command_dialog import command_menu
        command_menu(self.window,lambda kind:self.open_command_form(kind=kind))

    def edit_contents(self,event):
        hit=self.commands.identify_row(event.y)
        if hit in ('','new'):self.choose_command(where='new')
        elif hit.endswith(':add'):self.choose_command(where=hit)
        else:self.open_command_form(index=hit)

    def open_command_form(self,kind=None,index=None):
        from event_command_dialog import CommandDialog
        self._commit_command();page=self.current_page()
        branch_at=None;where=None   # where: Contents path, re-found when the dialog saves
        if index is not None and ':' in str(index):
            if str(index).endswith(':add'):return self.choose_command(where=str(index))
            where=str(index);container,target=self._locate(where)
        elif index is None and getattr(self,'insert_target',None):
            where=self.insert_target;container,child=self._locate(where);self.insert_target=None;target=None
            branch_at=child if child is not None else len(container)
        else:container=page['commands'];target=int(index) if index is not None else None
        if target is None and kind in ('lock_movement','unlock_movement'):
            # No settings: added straight away.
            position=branch_at if branch_at is not None else self.command_index if self.command_index is not None else len(container)
            container.insert(position,{'type':kind})
            self.command_index=None;self.refresh_commands();self.editor.dirty=True;self.schedule_apply()
            return
        if target is not None and container[target].get('type') in ('lock_movement','unlock_movement'):return
        row=command_template(kind) if target is None else container[target]
        if kind=='give_item':
            item=next((r for r in self.db.definitions if r['kind']=='item'),None)
            if item:row['item_class_id']=item['id']
        def save(value):
            # The dialog is not modal: auto-apply / _commit_command may have replaced
            # page['commands'] (or self.working) meanwhile, so writing into the list
            # captured at open went nowhere ("dialogue didn't stick", user 2026-10-24).
            container=self._locate(where)[0] if where else self.current_page()['commands']
            if target is None:
                position=branch_at if branch_at is not None else self.command_index if self.command_index is not None else len(container)
                container.insert(position,value)
            else:container[target]=value
            self.command_index=None;self.refresh_commands();self.editor.dirty=True
        CommandDialog(self.editor,self.window,row,save,database=self.db)

    def update_conditions_label(self):
        from event_command_dialog import condition_summary
        rows=self._read_conditions()
        self.conditions_label.set('\n'.join(condition_summary(r,self.db) for r in rows) or 'Always active (no conditions)')

    def _center(self,win):
        """Place a small window in the middle of the event editor window."""
        try:
            win.withdraw();win.update_idletasks()
            parent=self.window;w,h=win.winfo_reqwidth(),win.winfo_reqheight()
            x=parent.winfo_rootx()+(parent.winfo_width()-w)//2;y=parent.winfo_rooty()+(parent.winfo_height()-h)//2
            win.geometry(f'+{max(0,x)}+{max(0,y)}');win.transient(parent);win.deiconify()
        except tk.TclError:pass

    def _store_conditions(self,rows):
        self.conditions.delete('1.0','end');self.conditions.insert('1.0',json.dumps(rows));self.update_conditions_label()

    def edit_conditions(self):
        """Add condition (user 2026-10-18): one condition per window; OK adds it,
        Cancel (or closing the window) adds nothing."""
        from event_command_dialog import ConditionForm
        if not self.working:raise ValueError('Select an event first')
        rows=self._read_conditions();win=tk.Toplevel(self.window);win.title('Add condition')
        form=ConditionForm(win,self.db,editor=self.editor)
        def add():
            row=form.value();candidate=deepcopy(self.working);candidate['pages'][0]['conditions']=[row];validate_event_graph(candidate)
            rows.append(row);self._store_conditions(rows);win.destroy()
        buttons=ttk.Frame(win);buttons.pack(fill='x',padx=8,pady=8)
        ttk.Button(buttons,text='Cancel',command=win.destroy).pack(side='right',padx=4)
        ttk.Button(buttons,text='OK',command=lambda:self.editor.guard(add)).pack(side='right',padx=4)
        win.bind('<Escape>',lambda e:win.destroy());self._center(win)

    def remove_condition(self):
        """Remove condition: with one condition it goes at once; with several,
        pick the one to remove."""
        from event_command_dialog import condition_summary
        if not self.working:raise ValueError('Select an event first')
        rows=self._read_conditions()
        if not rows:raise ValueError('This page has no conditions')
        if len(rows)==1:
            self._store_conditions([]);self.editor.status.set('Condition removed.');return
        win=tk.Toplevel(self.window);win.title('Remove condition')
        tree=ttk.Treeview(win,show='tree',height=min(8,len(rows)));tree.pack(fill='x',padx=8,pady=8)
        for i,row in enumerate(rows):tree.insert('','end',iid=str(i),text=condition_summary(row,self.db))
        tree.selection_set('0')
        def remove():
            if not tree.selection():raise ValueError('Choose the condition to remove')
            rows.pop(int(tree.selection()[0]));self._store_conditions(rows);win.destroy()
        buttons=ttk.Frame(win);buttons.pack(fill='x',padx=8,pady=8)
        ttk.Button(buttons,text='Cancel',command=win.destroy).pack(side='right',padx=4)
        ttk.Button(buttons,text='Remove',command=lambda:self.editor.guard(remove)).pack(side='right',padx=4)
        tree.bind('<Double-1>',lambda e:self.editor.guard(remove))
        win.bind('<Escape>',lambda e:win.destroy());self._center(win)

    def add_class_action(self):
        """Append a database-backed spawn action at this event's map tile."""
        if not self.working:raise ValueError("Create or select a standalone event first")
        class_id=self.class_choices.get(self.action_class.get())
        if class_id is None:raise ValueError("Choose an existing NPC, enemy, boss, or object class")
        self._commit_form();page=self.current_page();self._commit_command()
        x,y=self.working["region"][:2]
        page["commands"].append({"type":"spawn_class","class_id":class_id,"position":[x,y]})
        validate_event_graph(self.working);self.refresh_commands(len(page["commands"])-1)

    def delete_command(self):
        self._commit_command();page=self.current_page()
        if (self.commands.selection() or [''])[0].endswith(':add'):raise ValueError('Select a command first')
        container,index=self.selected_command_location()
        del container[index];self.command_index=None;self.refresh_commands()

    def selected_command_location(self):
        selected=self.commands.selection()
        if not selected or selected[0]=='new':raise ValueError('Select a command first')
        container,index=self._locate(selected[0])
        return container,len(container) if index is None else index   # a branch's 'Add command…' row: its end

    def _locate(self,iid):
        """(list holding the row, its index); index None for an 'Add command…' row."""
        parts=str(iid).split(':');container=self.current_page()['commands']
        while len(parts)>1:
            container=container[int(parts[0])].setdefault(parts[1],[]);parts=parts[2:]
        return container,None if parts[0]=='add' else int(parts[0])

    def move_command(self,delta):
        self._commit_command();page=self.current_page()
        container,index=self.selected_command_location();target=index+delta
        if not 0<=target<len(container):return
        container[index],container[target]=container[target],container[index]
        path=self.commands.selection()[0].split(':');selection=':'.join(path[:-1]+[str(target)])
        self.command_index=None;self.refresh_commands(selection)

    def add_page(self):
        if not self.working:raise ValueError("Create or select a standalone event first")
        self._commit_form();self._commit_current_page();n=max(int(p['id'].split(':')[-1]) for p in self.working['pages'])+1
        page={"id":f"page:{n:04d}","name":f"Page {n}","trigger":"interact","class_id":None,"conditions":[],"commands":[]}
        self.working["pages"].append(page);validate_event_graph(self.working);self.refresh_pages(page["id"])

    def copy_page(self):
        self._commit_current_page()
        if self.current_page():EventGraphWindow.page_clipboard=deepcopy(self.current_page())

    def paste_page(self):
        if not self.working or self.page_clipboard is None:raise ValueError('Copy a page first')
        self._commit_current_page();page=deepcopy(self.page_clipboard)
        n=max(int(p['id'].split(':')[-1]) for p in self.working['pages'])+1;page['id']=f'page:{n:04d}';page['name']+=' copy'
        trial=deepcopy(self.working);trial['pages'].append(page);validate_event_graph(trial);self.working=trial;self.refresh_pages(page['id'])

    def clear_page(self):
        page=self.current_page()
        if not page:return
        page.update(trigger='interact',class_id=None,conditions=[],commands=[],trigger_actions=[{'trigger':'interact','commands':[],'hit_sources':[],'destroy_after':False}]);self.command_index=None;self.active_trigger='interact';self.load_page()

    def contents_menu(self,event):
        hit=self.commands.identify_row(event.y)
        if hit:self.commands.selection_set(hit);self.load_command()
        menu=tk.Menu(self.window,tearoff=False)
        actions=[('Insert command…',self.choose_command),('Edit command…',lambda:self.open_command_form(index=hit)),
                 ('Copy',self.copy_command),('Cut',lambda:self.copy_command(cut=True)),('Paste',self.paste_command),('Delete',self.delete_command)]
        for label,command in actions:menu.add_command(label=label,command=lambda c=command:self.editor.guard(c))
        menu.tk_popup(event.x_root,event.y_root)

    def copy_command(self,cut=False):
        self._commit_command();container,index=self.selected_command_location();EventGraphWindow.command_clipboard=deepcopy(container[index])
        if cut:del container[index];self.command_index=None;self.refresh_commands()

    def paste_command(self):
        if self.command_clipboard is None:raise ValueError('Copy a command first')
        self._commit_command();selection=self.commands.selection()
        if not selection or selection[0]=='new':container=self.current_page()['commands'];index=len(container)
        else:container,index=self.selected_command_location()
        container.insert(index,deepcopy(self.command_clipboard));self.command_index=None;self.refresh_commands()

    def delete_page(self):
        if not self.working or len(self.working["pages"])<=1:raise ValueError("An event must keep at least one page")
        self._commit_current_page();self.working["pages"]=[p for p in self.working["pages"] if p["id"]!=self.page_id]
        self.page_id=None;self.refresh_pages()

    def _commit_form(self):
        if not self.working:return
        try:
            map_id=int(self.map_id.get(),0);region=[int(v.get(),0) for v in (self.x,self.y,self.w,self.h)]
        except ValueError:raise ValueError("Map and region fields must be whole numbers")
        self.working.update(name=self.name.get().strip(),map_id=map_id,region=region)
        placement=self.working.setdefault('native_placement',{})
        from class_instance import set_override
        set_override(placement,'facing',self.default_facing.get(),self.placement_definition())   # the class's own facing is inherited
        for key,var in (('offset_x',self.offset_x),('offset_y',self.offset_y)):
            try:value=offset_value(var.get())
            except ValueError:raise ValueError('Offset X/Y must be whole numbers of half tiles (for example -1, 0, 1)')
            if not -8<=value<=8:raise ValueError('Offset X/Y must be between -8 and 8 half tiles')
            if value:placement[key]=value
            else:placement.pop(key,None)
        raw=self.z_height.get().strip()   # Tile Z: the tile's own height unless changed
        try:tile=self.tile_z(int(self.map_id.get(),0),int(self.x.get(),0),int(self.y.get(),0))
        except ValueError:tile=None
        if raw=='' or (getattr(self,'z_auto',None) is not None and raw==str(self.z_auto)) or (tile is not None and raw.lstrip('-').isdigit() and int(raw)==tile):placement.pop('height',None)
        else:
            try:z=int(raw,0)
            except ValueError:raise ValueError('Tile Z must be a whole number (0 or more)')
            if not 0<=z<=127:raise ValueError('Tile Z must be 0..127')
            placement['height']=z
        placement.pop('lower_one',None)   # Sink Into Floor was removed
        placement.pop('flush_with_floor',None)   # Flush With Floor was removed
        if self.is_step_on_switch() and self.while_pressured.get():placement['while_pressured']=True
        else:placement.pop('while_pressured',None)
        if self.is_step_on_switch() and getattr(self,'ignore_spring_bean',None) is not None and self.ignore_spring_bean.get():placement['ignore_spring_bean']=True
        else:placement.pop('ignore_spring_bean',None)
        if self.is_pattern_plate() and getattr(self,'plate_flush',None) is not None and not self.plate_flush.get():placement['plate_flush']=False
        else:placement.pop('plate_flush',None)
        cat=self.placement_catalogue()
        if cat==398 and self.sword_only.get():placement['sword_only']=True
        else:placement.pop('sword_only',None)
        if cat==307 and self.bomb_activation.get():placement['bomb_activation']=True
        else:placement.pop('bomb_activation',None)
        if self.is_changing_plate():
            placement['start_symbol']=('Star','Moon','Water','Sun').index(self.start_symbol.get()) if self.start_symbol.get() in ('Star','Moon','Water','Sun') else 0
            placement['fail_stops_others']=bool(self.fail_stops_others.get())
        else:
            placement.pop('start_symbol',None);placement.pop('fail_stops_others',None)
        if self.is_statue_variant():set_override(placement,'active_by_default',bool(self.active_by_default.get()),self.placement_definition())   # an explicit off stays off
        elif (self.is_state_switch() or self.is_nirude_face()) and self.active_by_default.get():placement['active_by_default']=True
        else:placement.pop('active_by_default',None)
        if (self.is_state_switch() or self.is_pattern_plate()) and self.keep_state.get():placement['keep_state']=True
        else:placement.pop('keep_state',None)
        if self.is_deactivatable_switch() and self.can_deactivate.get():placement['can_deactivate']=True
        else:placement.pop('can_deactivate',None)
        if (self.placement_definition() or {}).get('kind')=='boss':placement['play_victory']=bool(self.play_victory.get())
        else:placement.pop('play_victory',None)
        if (self.placement_definition() or {}).get('kind') in ('enemy','boss'):set_override(placement,'track_player',bool(self.track_player.get()),self.placement_definition(),fallback=False)
        else:placement.pop('track_player',None)
        if (self.placement_definition() or {}).get('kind') in ('enemy','boss') and self.instant_respawn.get():placement['instant_respawn']=True
        else:placement.pop('instant_respawn',None)
        cid=self.class_choices.get(self.placement_class.get())
        row=self.db.get(cid) if cid else None
        if row and row.get('source',{}).get('catalogue_index')==314 and self.rolling_target_enabled.get():
            try:tx=int(self.rolling_target_x.get(),0);ty=int(self.rolling_target_y.get(),0)
            except ValueError:raise ValueError('Rolling target X/Y must be whole tile numbers')
            from area_map import grid
            width,height,cells=grid(self.editor.session,map_id)
            if not 0<=tx<width or not 0<=ty<height:raise ValueError('Choose a rolling target tile inside this map')
            placement['finish_tile']={'x':tx,'y':ty,'height':cells[ty*width+tx]['values'][3]}
        else:placement.pop('finish_tile',None)
        if row and row.get('kind') in ('enemy','boss') and self.act_as_npc.get():placement['act_as_npc']=True
        else:placement.pop('act_as_npc',None)
        if row and row.get('source',{}).get('catalogue_index')==308:placement['rotation_controller']=self.rotation_control.get()
        else:placement.pop('rotation_controller',None)
        from behavior_transplant import SPAWN_CHOICE_CATALOGUES
        chosen_spawn=spawn_choice_names(self.db).get(self.spawned_class.get())
        if row and row.get('source',{}).get('catalogue_index') in SPAWN_CHOICE_CATALOGUES and chosen_spawn:placement['spawned_class']=chosen_spawn
        else:placement.pop('spawned_class',None)
        if row and row.get('source',{}).get('variant')=='push_stool':
            placement['push_directions']=[d for d in ('up','down','left','right') if self.stool_dirs[d].get()]
            if self.stool_once.get():placement['move_once']=True
            else:placement.pop('move_once',None)
        else:
            for _k in ('push_directions','target_tile','move_once'):placement.pop(_k,None)
        from native_freezable_flame import FREEZABLE_CATALOGUES
        if row and row.get('source',{}).get('catalogue_index') in FREEZABLE_CATALOGUES and self.fireballs_freezable.get():placement['fireballs_freezable']=True
        else:placement.pop('fireballs_freezable',None)
        if row and row.get('source',{}).get('catalogue_index') in FREEZABLE_CATALOGUES and self.always_fire.get():placement['always_fire']=True
        else:placement.pop('always_fire',None)
        _r=self.trigger_range.get().strip() if row and row.get('source',{}).get('catalogue_index') in FREEZABLE_CATALOGUES else ''
        if _r:
            if not _r.isdigit() or not 1<=int(_r)<=64:raise ValueError('Trigger range must be 1..64 tiles')
            placement['trigger_range']=int(_r)
        else:placement.pop('trigger_range',None)
        placement.pop('presence_by_page_condition',None)   # always on: events only appear while a page's conditions hold
        if self.direction_fix.get():placement['direction_fix']=True
        else:placement.pop('direction_fix',None)
        chosen=self.npc_animation.get()
        if self.animation_frame.winfo_manager() and chosen!='Native':
            placement['animation']=int(chosen.split()[0])
            if self.animation_static.get():
                try:placement['static_frame']=max(0,int(self.static_frame.get() or 0))
                except ValueError:raise ValueError('Static frame must be a whole number')
                placement['animation_static']=True
            else:placement.pop('animation_static',None);placement.pop('static_frame',None)
        elif self.animation_frame.winfo_manager():
            for key in ('animation','animation_static','static_frame'):placement.pop(key,None)

    def _commit_current_page(self):
        page=self.current_page()
        if not page:return
        self._commit_command();page=self.current_page()
        if self.default_route_mode.get()=='Native':page.pop('default_move_route',None)
        elif page.get('default_move_route'):
            page['default_move_route'].update(movement_speed=int(self.default_route_speed.get(),0),blocked_behavior="wait",repeat=self.default_route_repeat.get())
        self._save_active_trigger()
        handlers=ensure_trigger_actions(page)
        page["trigger"]=handlers[0]['trigger'];page['commands']=deepcopy(handlers[0].get('commands',[]))
        page["class_id"]=self.class_choices.get(self.placement_class.get())
        definition=next((r for r in self.db.definitions if r['id']==page['class_id']),None)
        if definition and definition.get('kind')=='boss' and self.act_as_npc.get():page['act_as_npc']=True   # this page: the boss only talks
        else:page.pop('act_as_npc',None)
        if definition and (definition.get('kind')=='npc' or definition.get('name','').casefold() in ('dog','chicken','crow')):
            if self.has_native_idle_animation(definition):page['idle_animation_enabled']=self.idle_animation_enabled.get()
            else:page.pop('idle_animation_enabled',None)
        else:page.pop('idle_animation_enabled',None)
        if self.float_enabled.get():
            try:lift=int(self.float_height.get() or 0)
            except ValueError:raise ValueError('Float height must be a whole number of pixels')
            page['float']=True;page['float_height']=lift
        else:page.pop('float',None);page.pop('float_height',None)
        page["conditions"]=self._read_conditions(page)

    def _read_conditions(self,page=None):
        """The page's conditions from the hidden store. Blank or unreadable never
        blocks editing or saving: keep the page's last good conditions instead."""
        text=self.conditions.get('1.0','end').strip()   # always at least '[]'; blank means it was wiped
        try:rows=json.loads(text) if text else None
        except json.JSONDecodeError:rows=None
        if not isinstance(rows,list):
            if page is None:page=self.current_page() or {}
            rows=list(page.get('conditions') or [])
            self.conditions.delete('1.0','end');self.conditions.insert('1.0',json.dumps(rows))
        return rows

    def _commit_selected(self):
        if not self.working:return
        self._commit_form();self._commit_current_page();validate_event_graph(self.working)
        # Store a copy: the saved page keeps the first trigger's commands in
        # page['commands'] (export reads them), while the editor goes on
        # showing the open trigger tab's own commands. Sharing one object made
        # every auto-save copy the first tab's commands into the open tab.
        self.db.replace_event_graph(self.working["id"],deepcopy(self.working))
        page=self.current_page()
        if page and self.active_trigger:
            handler=next((r for r in ensure_trigger_actions(page) if r['trigger']==self.active_trigger),None)
            if handler is not None:page['commands']=deepcopy(handler.get('commands',[]))

    def apply(self):
        self._commit_selected();event_id=self.working['id'] if self.working else None
        self.keep_changes(commit_form=False)
        self.refresh_list(event_id)
        if event_id is None:
            self.status.set('Applied event removals and referenced project switches.');return
        from event_export import project_event_export_issues
        issues=project_event_export_issues(self.editor.session,event_ids=[event_id])
        issue=next((r for r in issues if r['event_id']==event_id),None)
        if issue:
            self.status.set('Saved. Build will still continue; it will try this event, keep the project edit, and use the safest available fallback if needed.')
        else:
            self.status.set('Saved. This event is ready for Build game.')

    def keep_changes(self,commit_form=True):
        if commit_form:self._commit_selected()
        # The map's selection is an index into event_graphs; keep it on the same event
        area=self.editor.area;picked=getattr(area,'selected_record',None) if area else None
        graphs=self.editor.database.document.get('event_graphs',[])
        picked_id=graphs[picked[1]].get('id') if picked and picked[0]=='graphs' and picked[1]<len(graphs) else None
        self.draft.commit(self.editor.session)
        if picked_id is not None:
            graphs=self.editor.database.document.get('event_graphs',[])
            area.selected_record=next((('graphs',i) for i,g in enumerate(graphs) if g.get('id')==picked_id),None)
        self.editor.dirty=True
        if self.editor.session is not None:self.editor.session.content_database=self.editor.database.document
        if self.editor.area:
            try:self.editor.area.clear_in_front_of_switches()   # Flush With Floor applies as soon as it is kept
            except Exception:pass
            self.editor.area.draw_records()

    def close(self):
        """Hide at once; the save runs a little later so editing can go on.
        Map changes and Build lock it in first (finish_close)."""
        self._commit_selected()
        self.window.withdraw()
        job=getattr(self,'close_job',None)
        if job is not None:self.editor.root.after_cancel(job)
        import time
        self.close_started=time.monotonic()
        if not getattr(self.editor,'_input_clock_bound',False):
            # Remember the last key/mouse input so the save waits for a pause.
            self.editor._input_clock_bound=True;self.editor.last_input=time.monotonic()
            for sequence in ('<KeyPress>','<ButtonPress>','<B1-Motion>'):
                self.editor.root.bind_all(sequence,lambda e:setattr(self.editor,'last_input',time.monotonic()),add='+')
        self.close_job=self.editor.root.after(4000,lambda:self.editor.guard(self.passive_finish))
        if self.editor.area:
            try:self.editor.area.clear_in_front_of_switches()
            except Exception:pass
            self.editor.area.draw_records()   # show the finished event right away
        self.editor.status.set('Event changes kept. They are locked in shortly, and before map changes and Build.')

    def classes_changed(self):
        """A Database class changed: show its current values on the open event
        (values the event does not override come from the class)."""
        defs=self.editor.database.document.get('definitions')
        if defs is not None and self.db.document.get('definitions') is not defs:self.db.document['definitions']=defs
        cid=self.class_choices.get(self.placement_class.get()) if hasattr(self,'class_choices') else None
        try:
            self.refresh_class_choices()   # a renamed class keeps its place in the picker
            if cid:self.placement_class.set(next((l for l,v in self.class_choices.items() if v==cid),self.placement_class.get()))
        except Exception:pass
        if not self.working:return
        from class_instance import effective_placement
        placement=self.working.get('native_placement') or {}
        current=effective_placement(self.working,self.placement_definition())
        if 'facing' not in placement:self.default_facing.set(current.get('facing','down'))
        if 'track_player' not in placement:self.track_player.set(bool(current.get('track_player',False)))
        if 'active_by_default' not in placement and self.is_statue_variant():self.active_by_default.set(bool(current.get('active_by_default')))
        try:
            self.update_facing_control();self._refresh_list_names()
            if self.window.winfo_viewable():self.show_page_graphic()
        except Exception:pass

    def resync(self):
        """Undo / Redo changed the project's events: start again from them
        (unapplied form changes are dropped, as Undo asked)."""
        from event_edit_draft import EventEditDraft
        current=self.working.get('id') if self.working else None
        self.draft=EventEditDraft(self.editor.database);self.db=self.draft.database
        self.working=None;self.page_id=None
        exists=any(e.get('id')==current for e in self.db.document.get('event_graphs',[]))
        self.refresh_list(current if exists else None)

    def event_moved(self,event_id,region):
        """The map moved an event: keep this editor's copy in step, so closing
        or saving it does not put the event back where it was."""
        rows=[self.db.document.get('event_graphs',[]),self.draft.baseline.get('event_graphs') or []]
        if self.working and self.working.get('id')==event_id:rows.append([self.working])
        for table in rows:
            for row in table:
                if row.get('id')==event_id:row['region']=list(region)
        if self.working and self.working.get('id')==event_id:
            self.x.set(str(region[0]));self.y.set(str(region[1]))

    def closing(self):
        return getattr(self,'close_job',None) is not None

    def cancel_close(self):
        job=getattr(self,'close_job',None)
        if job is not None:
            self.editor.root.after_cancel(job);self.close_job=None

    def passive_finish(self):
        """Timer: save once the user pauses (at most ~20 s after closing)."""
        import time
        now=time.monotonic()
        if now-getattr(self.editor,'last_input',0)<2 and now-getattr(self,'close_started',now)<20:
            self.close_job=self.editor.root.after(1500,lambda:self.editor.guard(self.passive_finish));return
        self.finish_close()

    def finish_close(self):
        """Lock in the edits of a closed editor (no-op if it was reopened)."""
        if not self.closing():return
        self.close_job=None
        if not self.window.winfo_exists():return
        try:self.keep_changes(commit_form=False)
        except Exception:
            self.window.deiconify();self.window.lift()   # show the problem instead of losing the edit
            raise
        if self.window.state()=='withdrawn':self.window.destroy()

    def save_mod(self):
        self.apply()
        self.editor.save_mod_project()

    def delete_event(self):
        selected=self.events.selection()
        if not selected:raise ValueError("Select a standalone event to delete")
        message=self.draft.delete_event(selected[0])
        self.working=None;self.refresh_list();self.status.set(message)
        self.status.set('Event removed. Closing this editor keeps the change; Save mod writes it to disk.')

    def go_to_map(self):
        if not self.working:raise ValueError("Select a standalone event first")
        self._commit_form();validate_event_graph(self.working);self.editor.map_id.set(str(self.working["map_id"]))
