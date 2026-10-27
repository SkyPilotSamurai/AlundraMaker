"""Alundra project command forms; native support is checked by the exporter."""
from copy import deepcopy
import tkinter as tk
from tkinter import ttk
import csv
from pathlib import Path
from event_graph import COMPARISONS, VARIABLE_OPS, DIRECTIONS, validate_event_graph, new_event_graph

LABELS={"change_music":"Change Music", "play_sound":"Play Sound", "show_dialogue":"Show Text", "ask_question":"Ask A Question","give_item":"Give Item", "change_money":"Give Money", "set_switch":"Control Switch",
        "set_variable":"Control Variable", "if":"Conditional Branch", "move_actor":"Move Character", "face_actor":"Face Character",
        "change_graphic":"Change Event Graphic", "change_player_character":"Change Player Character", "set_event_active":"Show / Hide Event",
        "spawn_class":"Create Database Object", "warp_player":"Transfer Player", "wait":"Wait","repeat":"Repeat Actions",
        "lock_movement":"Lock Player Movement","erase_event":"Erase Event","change_animation":"Change Animation","deactivate_switch":"Activate / Deactivate Switch","unlock_movement":"Unlock Player Movement"}
GRAPHIC_KINDS=('npc','enemy','boss','object')
import native_event_authoring as NATIVE
LABELS.update({k:v[0] for k,v in NATIVE.COMMANDS.items()})

def switch_options():
    path=Path(__file__).resolve().parents[1]/'data/event-flags.csv'
    with path.open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    return {f"{row['event_code']}  {row['name']}":int(row['event_code'],16) for row in rows if row.get('event_code')}

def summary(row, database):
    def name(cid):
        return next((r["name"] for r in database.definitions if r["id"]==cid),str(cid))
    kind=row["type"]
    if kind in NATIVE.COMMANDS and kind!='take_item' and kind!='play_sound_volume':return NATIVE.summary(row)
    if kind=='take_item':return f"{name(row.get('item_class_id'))} − 1"
    if kind=="change_music":
        from game_audio_names import music_name
        return f"{row['music_id']:03d} - {music_name(database.document,row['music_id'])}"
    if kind=="play_sound":
        from game_audio_names import sound_name
        return f"{row['sound_id']:03d} - {sound_name(database.document,row['sound_id'])}"
    if kind=="ask_question":return (row.get('text') or '').replace('\n',' ')[:60]+'  (Yes / No)'
    if kind=="show_dialogue":
        speaker=row.get('speaker');label=speaker or 'This character / native portrait'
        if speaker=='player':label='Alundra'
        elif isinstance(speaker,str) and speaker.startswith('database:'):label=name(speaker[len('database:'):])
        actor=next((r for r in database.document['instances'] if r['id']==speaker),None)
        event=next((r for r in database.document['event_graphs'] if r['id']==speaker),None)
        if actor:label=name(actor.get('class_id'))
        elif event:label=event['name']
        return f"{label}: {row.get('text','')}"
    if kind=='change_player_character':return row['character']
    if kind=='lock_movement':return 'The player cannot move until Unlock Player Movement'
    if kind=='unlock_movement':return 'The player can move again'
    if kind=='erase_event':return 'This event is gone for good once these actions finish'
    if kind=='change_graphic':
        target='This Event' if row.get('target')=='this_event' else str(row.get('target'))
        return f"{target} → {name(row['graphic']) if row.get('graphic') else 'No graphic chosen'}"
    if kind=="give_item":
        extra=['Drop Item On Map' if row.get('drop_on_map') else ('Show Obtained Text' if row.get('show_obtained_text',True) else 'No Obtained Text')]
        return f"{name(row['item_class_id'])} + {row.get('quantity',1)}  ({', '.join(extra)})"
    if kind=="set_switch":
        from project_state_ui import state_label
        label=state_label(database,'switches',row['switch_id']) if row.get('switch_scope')=='project' else f"Game #{row['switch_id']:04d}"
        return f"{label} = {'ON' if row['value'] else 'OFF'}"
    if kind=='change_money':return f"Money + {row['amount']}"
    if kind=="set_variable":
        from project_state_ui import state_label
        return f"{state_label(database,'variables',row['variable_id'])} {row['operation']} {row['value']}"
    if kind=="if":return condition_summary(row['condition'],database)
    if kind=='repeat':return f"{row['count']} times · {len(row.get('commands',[]))} actions"
    if kind=="spawn_class":return f"{name(row['class_id'])} at {row['position']}"
    if kind=="warp_player":
        from map_names import map_label
        return f"{map_label(row['map_id'])} ({row['map_id']}) at {row['x']}, {row['y']}"
    return ", ".join(f"{k.replace('_',' ')}: {v}" for k,v in row.items() if k!='type')

def actor_targets(editor,database,value=None):
    """Characters on the event's map: This Event, then the player, then every other event."""
    active=getattr(editor,'event_graph_window',None)
    working=(getattr(active,'working',None) or {}) if active else {}
    map_id=working.get('map_id',getattr(editor,'current_map',None))
    choices={'This Event':'this_event','Player':'player'}
    definitions={r['id']:r for r in database.definitions}
    for instance in database.document.get('instances',[]):
        if instance.get('map_id')!=map_id:continue
        name=definitions.get(instance.get('class_id'),{}).get('name','Map character')
        choices[f"{name} — event {instance['entity_index']}"]=instance['id']
    for graph in database.document.get('event_graphs',[]):
        if graph.get('map_id')==map_id and graph.get('id')!=working.get('id'):
            choices[f"{graph['name']} — authored event"]=graph['id']
    if value not in choices.values() and value not in (None,''):choices[f"{value} — not on this map"]=value
    return choices

def condition_summary(row,database):
    kind=row['type']
    if kind in NATIVE.CONDITIONS:return NATIVE.condition_summary(row)
    key={'switch':'switch_id','variable':'variable_id','item':'item_class_id'}[kind]
    value=row.get('value',row.get('quantity',1))
    if type(value) is bool:value='ON' if value else 'OFF'
    identity=row[key]
    if row.get(kind+'_scope')=='project':
        from project_state_ui import state_label
        identity=state_label(database,'switches' if kind=='switch' else 'variables',identity)
    return f"{kind.title()} {identity} {row.get('operator','==')} {value}"

class Fields:
    def __init__(self,frame,database):self.frame=frame;self.db=database;self.readers={};self.widgets={};self.n=0
    def add(self,key,label,value,choices=None,class_kinds=None,multiline=False,mapped_choices=None):
        ttk.Label(self.frame,text=label).grid(row=self.n,column=0,sticky='nw',padx=6,pady=5)
        if multiline:
            widget=tk.Text(self.frame,width=48,height=5,wrap='word');widget.insert('1.0',value)
            read=lambda:widget.get('1.0','end-1c')
        elif type(value) is bool:
            var=tk.BooleanVar(value=value);widget=ttk.Checkbutton(self.frame,text='ON / enabled',variable=var);read=var.get
        else:
            var=tk.StringVar(value=str(value));mapping=mapped_choices
            if mapping is not None:
                var.set(next((k for k,v in mapping.items() if v==value),''));choices=list(mapping)
            if class_kinds:
                mapping={f"{r['name']} — {r['id']}":r['id'] for r in self.db.definitions if r['kind'] in class_kinds}
                var.set(next((k for k,v in mapping.items() if v==value),''));choices=list(mapping)
            widget=ttk.Combobox(self.frame,textvariable=var,values=choices,state='readonly',width=45) if choices is not None else ttk.Entry(self.frame,textvariable=var,width=45)
            def read():
                text=var.get()
                if mapping is not None:
                    if text not in mapping:raise ValueError(f"Choose {label.lower()} from the database")
                    return mapping[text]
                return int(text,0) if type(value) is int else text
        widget.grid(row=self.n,column=1,sticky='ew',padx=6,pady=5);self.readers[key]=read;self.widgets[key]=widget;self.n+=1
    def add_search(self,key,label='Find'):
        """Filter for a mapped choice: name or number (user 2026-10-26)."""
        box=self.widgets[key];every=list(box.cget('values'));text=tk.StringVar()
        ttk.Label(self.frame,text=label).grid(row=self.n,column=0,sticky='nw',padx=6,pady=5)
        entry=ttk.Entry(self.frame,textvariable=text,width=45);entry.grid(row=self.n,column=1,sticky='ew',padx=6,pady=5);self.n+=1
        def filter_(*_):
            needle=text.get().strip().casefold()
            shown=[v for v in every if needle in v.casefold()] if needle else every
            box.configure(values=shown)
            if len(shown)==1:box.set(shown[0])
        text.trace_add('write',filter_);self.widgets[key+'_search']=entry
    def add_graphic_picker(self,editor,window,key,label,value,title='Choose Event Graphic',button='Choose Graphic…'):
        """Graphic chosen from the same card grid used for placing events."""
        ttk.Label(self.frame,text=label).grid(row=self.n,column=0,sticky='nw',padx=6,pady=5)
        host=ttk.Frame(self.frame);host.grid(row=self.n,column=1,sticky='ew',padx=6,pady=5)
        chosen={'id':value or None};shown=tk.StringVar()
        def show():
            row=next((r for r in self.db.definitions if r['id']==chosen['id']),None)
            shown.set(row['name'] if row else 'None chosen')
        def pick(class_id):
            if class_id:chosen['id']=class_id;show()
        def open_grid():
            from database_picker import DatabasePicker
            DatabasePicker(editor,window,pick,kinds=GRAPHIC_KINDS,title=title,confirm='Use Selected',allow_empty=False)
        ttk.Label(host,textvariable=shown,width=34).pack(side='left')
        ttk.Button(host,text=button,command=lambda:editor.guard(open_grid)).pack(side='left',padx=(6,0))
        def read():
            if not chosen['id']:raise ValueError(f'Choose a {label.lower()}')
            return chosen['id']
        show();self.readers[key]=read;self.n+=1
    def add_destination_picker(self,editor,window,row):
        """Transfer Player destination: a map and a tile chosen on the rendered map."""
        from map_names import map_label
        ttk.Label(self.frame,text='Destination').grid(row=self.n,column=0,sticky='nw',padx=6,pady=5)
        host=ttk.Frame(self.frame);host.grid(row=self.n,column=1,sticky='ew',padx=6,pady=5)
        state={'map_id':row.get('map_id',0),'x':row.get('x',0),'y':row.get('y',0),'z':row.get('z')}
        shown=tk.StringVar()
        def show():
            z='' if state['z'] is None else f" · height {state['z']}"
            shown.set(f"{state['map_id']:03d} {map_label(state['map_id'])} — tile {state['x']}, {state['y']}{z}")
        def picked(map_id,x,y,z):state.update(map_id=map_id,x=x,y=y,z=z);show()
        def open_picker():
            from map_tile_picker import MapTileDialog
            MapTileDialog(editor,window,picked,map_id=state['map_id'],x=state['x'],y=state['y'],z=state['z'],title='Choose Destination Map And Tile')
        ttk.Label(host,textvariable=shown,width=46).pack(side='left')
        ttk.Button(host,text='Choose Map And Tile…',command=lambda:editor.guard(open_picker)).pack(side='left',padx=(6,0))
        def reader(key):
            def read():
                if key=='z' and state['z'] is None:raise ValueError('Choose the destination tile')
                return int(state[key])
            return read
        for key in ('map_id','x','y','z'):self.readers[key]=reader(key)
        show();self.n+=1
    def add_tile_picker(self,editor,window,value,map_id,label='Tile'):
        """A tile on the event's own map, picked on the rendered map."""
        ttk.Label(self.frame,text=label).grid(row=self.n,column=0,sticky='nw',padx=6,pady=5)
        host=ttk.Frame(self.frame);host.grid(row=self.n,column=1,sticky='ew',padx=6,pady=5)
        state={'x':int(value[0]),'y':int(value[1])}
        shown=tk.StringVar()
        def show():shown.set(f"Map {map_id} — tile {state['x']}, {state['y']}")
        def picked(_map,x,y,z):state.update(x=x,y=y);show()
        def open_picker():
            from map_tile_picker import MapTileDialog
            MapTileDialog(editor,window,picked,map_id=map_id,x=state['x'],y=state['y'],
                          title='Choose Tile On This Map',fixed_map=True)
        ttk.Label(host,textvariable=shown,width=30).pack(side='left')
        ttk.Button(host,text='Choose Tile On Map…',command=lambda:editor.guard(open_picker)).pack(side='left',padx=(6,0))
        self.readers['x']=lambda:int(state['x']);self.readers['y']=lambda:int(state['y'])
        show();self.n+=1
    def values(self):return {k:read() for k,read in self.readers.items()}

class RouteEditor:
    """Ordered cardinal steps, without requiring command syntax."""
    def __init__(self,parent,route):
        self.steps=list(route);self.frame=ttk.LabelFrame(parent,text='Tile route',padding=5)
        self.list=tk.Listbox(self.frame,height=4,background='#171b22',foreground='#d8e2ee',selectbackground='#2d4156',exportselection=False)
        self.list.pack(fill='x');bar=ttk.Frame(self.frame);bar.pack(fill='x',pady=4)
        for direction in DIRECTIONS:ttk.Button(bar,text=direction.title(),width=7,command=lambda d=direction:self.append(d)).pack(side='left',padx=2)
        for label,action in [('↑',lambda:self.move(-1)),('↓',lambda:self.move(1)),('Remove',self.remove)]:ttk.Button(bar,text=label,width=7,command=action).pack(side='left',padx=2)
        self.refresh()
    def refresh(self,selection=None):
        self.list.delete(0,'end')
        for index,direction in enumerate(self.steps):self.list.insert('end',f'{index+1}. {direction.title()} one tile')
        if selection is not None and self.steps:self.list.selection_set(selection);self.list.see(selection)
    def append(self,direction):
        if len(self.steps)>=255:return
        self.steps.append(direction);self.refresh(len(self.steps)-1)
    def remove(self):
        selected=self.list.curselection()
        if selected:self.steps.pop(selected[0]);self.refresh(min(selected[0],len(self.steps)-1))
    def move(self,delta):
        selected=self.list.curselection()
        if not selected:return
        index=selected[0];other=index+delta
        if 0<=other<len(self.steps):self.steps[index],self.steps[other]=self.steps[other],self.steps[index];self.refresh(other)
    def value(self):return list(self.steps)

class ConditionForm:
    def __init__(self,parent,db,condition=None,editor=None):
        self.editor=editor;self.db=db;self.frame=ttk.LabelFrame(parent,text='Condition',padding=5);self.frame.pack(fill='x',pady=5)
        self.kind=tk.StringVar(value=(condition or {}).get('type','switch'))
        self.kind_names={'switch':'Switch','variable':'Variable','item':'Item',**{k:v[0] for k,v in NATIVE.CONDITIONS.items()}}
        self.kind_label=tk.StringVar(value=self.kind_names.get(self.kind.get(),self.kind.get()))
        # Yes / No is asked from Show Text ("Ask Yes / No"); old branches still open.
        offered=[v for k,v in self.kind_names.items() if k!='yes_no' or self.kind.get()=='yes_no']
        combo=ttk.Combobox(self.frame,textvariable=self.kind_label,values=offered,state='readonly',width=44);combo.pack(anchor='w')
        def picked(_=None):
            self.kind.set(next(k for k,v in self.kind_names.items() if v==self.kind_label.get()));self.build()
        combo.bind('<<ComboboxSelected>>',picked)
        self.body=ttk.Frame(self.frame);self.body.pack(fill='x');self.build(condition)
    def build(self,row=None):
        for child in self.body.winfo_children():child.destroy()
        row=row or {};kind=self.kind.get();self.fields=Fields(self.body,self.db)
        self.state_selector=None
        if kind in NATIVE.CONDITIONS:
            label,defaults,fields=NATIVE.CONDITIONS[kind]
            for key,default in defaults.items():
                flabel,choices=fields.get(key,(key,None))
                self.fields.add(key,flabel,row.get(key,default),mapped_choices=choices)
            return
        if kind in ('switch','variable'):
            from project_state_ui import StateSelector
            self.state_selector=StateSelector(self.body,self.db,'switches' if kind=='switch' else 'variables',row,editor=self.editor)
            self.state_selector.frame.grid(row=self.fields.n,column=0,columnspan=2,sticky='ew');self.fields.n+=1
            self.fields.add('value','Switch is' if kind=='switch' else 'Value',row.get('value',True if kind=='switch' else 0))
        else:
            self.fields.add('item_class_id','Item',row.get('item_class_id',''),class_kinds=('item','weapon','armor'));self.fields.add('quantity','Quantity',row.get('quantity',1))
        choices=COMPARISONS if kind=='variable' else ('==','!=') if kind=='switch' else ('==','!=','>=','<')
        self.fields.add('operator','Comparison',row.get('operator','=='),choices=choices)
    def value(self):
        row=dict(type=self.kind.get(),**self.fields.values())
        if self.state_selector is not None:row.update(self.state_selector.value())
        return row

MENU_COLUMNS=[
    [('Messages',['show_dialogue','ask_question','play_victory']),
     ('Game Progression',['set_switch','set_self_switch','set_variable','deactivate_switch','if','repeat']),
     ('Items And Money',['give_item','take_item','change_money','pay_money','restore_life','raise_max_life','raise_max_mp'])],
    [('Movement',['move_actor','face_actor','jump_actor','set_gravity','lock_movement','unlock_movement']),
     ('Characters And Objects',['change_graphic','change_animation','wait_animation','set_event_active','erase_event','show_effect','change_player_character'])],
    [('Map',['warp_player','set_passability','copy_map_tiles']),
     ('Screen And Timing',['camera','fade_screen','wait']),
     ('Audio',['change_music','play_sound_volume','stop_sound']),
     ('Other',['back_to_title','play_movie'])]]
MENU_LABELS={'change_player_character':'Change Player Character','copy_map_tiles':'Open Door / Bridge (Map Tiles)',
             'set_passability':'Tile Passability','raise_max_life':'Raise Max Life','raise_max_mp':'Raise Max MP','restore_life':'Recover Life And Magic',
             'deactivate_switch':'Activate / Deactivate Switch','play_sound_volume':'Play Sound'}

def command_menu(parent,choose):
    win=tk.Toplevel(parent);win.title('Alundra Event Commands');win.transient(parent);win.resizable(False,False)
    listed={k for col in MENU_COLUMNS for _,kinds in col for k in kinds}
    extra=[k for k in LABELS if k not in listed and k not in ('play_sound','play_ending')]              # anything added later still shows up
    columns=[list(col) for col in MENU_COLUMNS]
    if extra:   # into the Other group
        other=next((i for i,(name,_) in enumerate(columns[-1]) if name=='Other'),None)
        if other is None:columns[-1].append(('Other',extra))
        else:columns[-1][other]=('Other',list(columns[-1][other][1])+extra)
    for c,column in enumerate(columns):
        host=ttk.Frame(win);host.grid(row=0,column=c,sticky='n',padx=(10 if c==0 else 4,10 if c==len(columns)-1 else 4),pady=8)
        for name,kinds in column:
            group=ttk.LabelFrame(host,text=name,padding=(8,4,8,6));group.pack(fill='x',pady=(0,8))
            for kind in kinds:
                if kind not in LABELS:continue
                def selected(k=kind):choose(k)                      # the menu stays open for the next command
                ttk.Button(group,text=MENU_LABELS.get(kind,LABELS[kind]),command=selected,width=30).pack(fill='x',pady=2)
    ttk.Button(win,text='Done',command=win.destroy).grid(row=1,column=len(columns)-1,sticky='e',padx=10,pady=(0,10))
    win.update_idletasks()
    try:
        x=parent.winfo_rootx()+max(0,(parent.winfo_width()-win.winfo_width())//2);y=parent.winfo_rooty()+40
        win.geometry(f'+{x}+{y}')
    except Exception:pass

def center_on_app(win):
    """Command windows open centred on the main editor window, 10% above the middle."""
    try:
        win.update_idletasks();app=win.master
        while app.master is not None:app=app.master
        aw,ah=app.winfo_width(),app.winfo_height();ww,wh=win.winfo_reqwidth(),win.winfo_reqheight()
        x=app.winfo_rootx()+(aw-ww)//2;y=app.winfo_rooty()+(ah-wh)//2-round(ah*0.10)
        y=max(app.winfo_rooty(),y)    # no screen clamp on X: it broke centring on a second monitor
        win.update_idletasks();ww=max(ww,win.winfo_width());x=app.winfo_rootx()+(aw-ww)//2
        win.geometry(f'+{x}+{y}')
    except Exception:pass

class CommandDialog:
    def __init__(self,editor,parent,row,save,database=None):
        self.editor=editor;self.db=database if database is not None else editor.database;self.row=deepcopy(row);self.save=save
        self.window=tk.Toplevel(parent);self.window.title(LABELS[row['type']]);self.window.transient(parent)
        frame=ttk.Frame(self.window,padding=10);frame.pack(fill='both',expand=True);self.fields=Fields(frame,self.db)
        kind=row['type'];self.state_selector=None
        if kind in ('set_switch','set_variable'):
            from project_state_ui import StateSelector
            self.state_selector=StateSelector(frame,self.db,'switches' if kind=='set_switch' else 'variables',row,editor=editor)
            self.state_selector.frame.grid(row=self.fields.n,column=0,columnspan=2,sticky='ew');self.fields.n+=1
        if kind=='show_dialogue':
            active=getattr(editor,'event_graph_window',None)
            map_id=(active.working or {}).get('map_id',editor.current_map) if active else editor.current_map
            speakers={'This character — linked native portrait':None,'Player / Alundra':'player'}
            definitions={r['id']:r for r in self.db.definitions}
            # NPCs standing on this map first, each listed once; then the rest.
            on_map=[i for i in self.db.document['instances'] if i['map_id']==map_id]
            npcs=[i for i in on_map if definitions.get(i.get('class_id'),{}).get('kind')=='npc']
            counts={}
            for instance in npcs:counts[instance.get('class_id')]=counts.get(instance.get('class_id'),0)+1
            seen={}
            for instance in npcs:
                cid=instance.get('class_id');seen[cid]=seen.get(cid,0)+1
                name=definitions.get(cid,{}).get('name','Map character')
                label=f"{name} — on this map"+(f" ({seen[cid]})" if counts[cid]>1 else '')
                speakers[label]=instance['id']
            for graph in self.db.document['event_graphs']:
                if graph['map_id']==map_id and any(p.get('class_id') for p in graph['pages']):
                    speakers[f"{graph['name']} — your event on this map"]=graph['id']
            for instance in on_map:
                if instance in npcs:continue
                definition=definitions.get(instance.get('class_id'),{})
                speakers[f"{definition.get('name','Map character')} — map object {instance['entity_index']}"]=instance['id']
            for definition in self.db.definitions:
                if definition['kind']=='npc' and definition['id'] not in counts:
                    speakers[f"{definition['name']} — database NPC"]='database:'+definition['id']
            # Preserve old named authoring values for review; export still checks
            # whether the value identifies an actual native actor on this map.
            value=row.get('speaker')
            if value not in speakers.values():speakers[str(value)+' — needs native actor binding']=value
            self.fields.add('speaker','Speaking character',value,mapped_choices=speakers)
        if kind=='change_player_character':   # Start as Meia's two options, per command
            row.setdefault('meia_basic_attack',False);row.setdefault('meia_alundra_fallback',False)
        for key,value in row.items():
            if key in ('type','condition','then','else','commands'):continue
            if kind=='change_music' and key=='music_id':
                from music_database_ui import music_names
                self.fields.add('music_id','Music track',value,mapped_choices=music_names(editor))
                from audio_preview import PreviewBar
                PreviewBar(frame,editor,'music',lambda:self.fields.readers['music_id']()).frame.grid(row=self.fields.n,column=0,columnspan=2,pady=6);self.fields.n+=1
                continue
            if kind=='play_sound' and key=='sound_id':
                from sound_database_ui import sound_names
                from audio_preview import PreviewBar
                self.fields.add('sound_id','Sound effect',value,mapped_choices=sound_names(editor));self.fields.add_search('sound_id','Find sound')
                PreviewBar(frame,editor,'sound',lambda:self.fields.readers['sound_id']()).frame.grid(row=self.fields.n,column=0,columnspan=2,pady=6);self.fields.n+=1
                continue
            if self.state_selector is not None and key in ('switch_id','switch_scope','native_flag_operand','variable_id','variable_scope'):continue
            if kind=='move_actor' and key in ('moving_animation','idle_animation','movement_speed','skip_impossible','blocked_behavior'):continue
            if kind=='deactivate_switch' and key=='event_id':
                active=getattr(editor,'event_graph_window',None)
                graph=(active.working or {}) if active else {}
                map_id=graph.get('map_id',editor.current_map)
                defs={r['id']:r for r in self.db.definitions}
                choices={'This switch (this event)':'this_event'}
                for g in self.db.document.get('event_graphs',[]):
                    if g.get('map_id')!=map_id or g.get('id')==graph.get('id'):continue
                    cid=(g.get('pages') or [{}])[0].get('class_id',g.get('class_id'))
                    if defs.get(cid,{}).get('source',{}).get('catalogue_index') in (301,346) and not defs.get(cid,{}).get('source',{}).get('variant'):   # 346 Nirude Face Statue
                        choices[f"{g['name']} ({defs[cid]['name']}, tile {g['region'][0]},{g['region'][1]})"]=g['id']
                if value not in choices.values():choices[str(value)+' (not a step-on switch on this map)']=value
                self.fields.add('event_id','Switch',value,mapped_choices=choices)
                self.fields.add('active','Set it to',bool(row.get('active',False)),mapped_choices={'Deactivated (up)':False,'Activated (pressed)':True});continue
            if kind=='deactivate_switch' and key=='active':continue
            if kind=='change_animation' and key=='animation_id':
                active=getattr(editor,'event_graph_window',None)
                graph=(active.working or {}) if active else {}
                page=next((p for p in graph.get('pages',[]) if p['id']==getattr(active,'page_id',None)),{})
                definition=next((r for r in self.db.definitions if r['id']==page.get('class_id')),{})
                source=definition.get('source',{});catalogue=source.get('catalogue_index');profile=[]
                if editor.session is not None and type(catalogue) is int:
                    from event_movement_compile import animation_profile
                    for map_id in [graph.get('map_id',editor.current_map)]+source.get('observed_maps',[]):
                        try:profile=animation_profile(editor.session.data,catalogue,map_id);break
                        except ValueError:continue
                choices={f"Animation {r['animation_id']}"+(' (moving)' if r['speed']>0 else ''):r['animation_id'] for r in profile if any(r['directions_valid'])}
                if value not in choices.values():choices[f'Animation {value}']=value
                self.fields.add('animation_id','Animation',value,mapped_choices=choices);continue
            if kind=='play_sound_volume' and key=='volume':   # a volume bar, 0-127 (user 2026-10-26)
                ttk.Label(frame,text='Volume').grid(row=self.fields.n,column=0,sticky='w',padx=6,pady=5)
                line=ttk.Frame(frame);line.grid(row=self.fields.n,column=1,sticky='ew',padx=6,pady=5);self.fields.n+=1
                vol=tk.IntVar(value=max(0,min(127,int(value))))
                shown=ttk.Label(line,text=str(vol.get()),width=4)
                tk.Scale(line,from_=0,to=127,orient='horizontal',variable=vol,showvalue=False,length=260,
                         command=lambda _v,_s=shown,_x=vol:_s.configure(text=str(_x.get()))).pack(side='left',fill='x',expand=True)
                shown.pack(side='left',padx=(6,0))
                self.fields.readers['volume']=vol.get;continue
            if kind in NATIVE.COMMANDS and key in NATIVE.COMMANDS[kind][3]:
                flabel,choices=NATIVE.COMMANDS[kind][3][key]
                self.fields.add(key,flabel,value,mapped_choices=choices);continue
            if kind in ('play_sound_volume','stop_sound') and key=='sound_id':
                from sound_database_ui import sound_names
                self.fields.add('sound_id','Sound effect',value,mapped_choices=sound_names(editor))
                if kind=='play_sound_volume':self.fields.add_search('sound_id','Find sound')
                continue
            if key in ('native_instruction_offset','native_text_sha256'):continue
            if key=='switch_id' and 'native_flag_operand' in row:continue
            if kind=='set_switch' and key in ('switch_id','native_flag_operand'):
                from native_flag_index import flag_label,flag_name,show_uses,set_document
                set_document(self.db.document)
                flag=row.get('native_flag_operand',value);options=switch_options()
                options={k:v for k,v in options.items() if v!=flag};options={flag_label(flag):flag,**options}
                self.fields.add('native_flag_operand','Game switch',flag,mapped_choices=options)
                self.flag_name=tk.StringVar(value=flag_name(flag) or '')
                ttk.Label(frame,text='Flag name').grid(row=self.fields.n,column=0,sticky='w',padx=6,pady=5)
                line=ttk.Frame(frame);line.grid(row=self.fields.n,column=1,sticky='ew',padx=6,pady=5);self.fields.n+=1
                ttk.Entry(line,textvariable=self.flag_name,width=32).pack(side='left',fill='x',expand=True)
                def uses():
                    current=self.fields.readers['native_flag_operand']()
                    show_uses(editor,self.window,current)
                ttk.Button(line,text='Events using this flag…',command=lambda:editor.guard(uses)).pack(side='left',padx=(6,0))
                continue
            if kind=='show_dialogue' and key=='speaker':continue
            if key=='position' and kind=='spawn_class':
                active=getattr(editor,'event_graph_window',None)
                event_map=(getattr(active,'working',None) or {}).get('map_id',editor.current_map)
                self.fields.add_tile_picker(editor,self.window,value,event_map);continue
            if key=='position':
                self.fields.add('x','Tile X',value[0]);self.fields.add('y','Tile Y',value[1]);continue
            if kind=='move_actor' and key=='route':continue
            if kind in ('move_actor','face_actor') and key=='target':
                self.fields.add(key,'Character',value,mapped_choices=actor_targets(editor,self.db,value));continue
            if kind=='change_graphic':
                if key=='target':self.fields.add(key,'Event',value,mapped_choices={'This Event':'this_event'});continue
                if key=='graphic':self.fields.add_graphic_picker(editor,self.window,key,'Graphic',value);continue
            if kind=='warp_player' and key in ('x','y','z'):continue
            if kind=='warp_player' and key=='map_id':
                self.fields.add_destination_picker(editor,self.window,row);continue
            if kind=='spawn_class' and key=='class_id':
                self.fields.add_graphic_picker(editor,self.window,key,'Database Object',value,title='Choose Database Object',button='Choose Object…');continue
            if kind=='face_actor':
                if key=='direction':
                    self.fields.add(key,'Face',value,mapped_choices={'Player':'player','Away from player':'away_from_player','Up':'up','Down':'down','Left':'left','Right':'right'});continue
            choices=('Alundra','Meia') if kind=='change_player_character' and key=='character' else VARIABLE_OPS if key=='operation' else DIRECTIONS if key=='direction' else ('toward_player','walk_tiles','route') if key=='mode' else None
            kinds=('item','weapon','armor') if key=='item_class_id' else ('npc','enemy','boss','object') if key in ('class_id','graphic') else None
            label='Native switch ID' if key=='native_flag_operand' else key.replace('_',' ').title()
            if key=='auto_wrap':label='Wrap for game text window'
            if key=='meia_basic_attack':label='Meia basic attack'
            if key=='meia_alundra_fallback':label='Alundra for other actions'
            if key=='drop_on_map':label='Drop Item On Map'
            if kind=='give_item' and key=='obtained_message':continue   # replaced by Show Obtained Text
            self.fields.add(key,label,value,choices=choices,class_kinds=kinds,multiline=key in ('text','obtained_message'))
        if kind=='show_dialogue' and 'auto_wrap' not in row:self.fields.add('auto_wrap','Wrap for game text window',True)
        if kind=='give_item' and 'show_obtained_text' not in row:
            self.fields.add('show_obtained_text','Show Obtained Text',True)
        if kind=='give_item' and 'drop_on_map' not in row:
            self.fields.add('drop_on_map','Drop Item On Map',False)
        if kind=='move_actor':
            self.fields.add('movement_speed','Speed (% of this type)',row.get('movement_speed',100))
            self.fields.readers['blocked_behavior']=lambda:'wait'
            if 'tiles' not in row:self.fields.add('tiles','Tile distance',1)
            if 'direction' not in row:self.fields.add('direction','Direction','down',choices=DIRECTIONS)
            self.route_editor=RouteEditor(frame,row.get('route',['down']))
            self.route_editor.frame.grid(row=self.fields.n,column=0,columnspan=2,sticky='ew',padx=6,pady=5)
            self.fields.readers['route']=self.route_editor.value;self.fields.n+=1
            active=getattr(parent,'_alundra_graph_window',getattr(editor,'event_graph_window',None))
            graph=(active.working or {}) if active else {}
            page=next((p for p in graph.get('pages',[]) if p['id']==getattr(active,'page_id',None)),{})
            definition=next((r for r in self.db.definitions if r['id']==page.get('class_id')),{})
            source=definition.get('source',{});catalogue=source.get('catalogue_index')
            profile=[]
            if editor.session is not None and type(catalogue) is int:
                from event_movement_compile import animation_profile
                maps=[graph.get('map_id',editor.current_map)]+source.get('observed_maps',[])
                for map_id in maps:
                    try:profile=animation_profile(editor.session.data,catalogue,map_id);break
                    except ValueError:continue
            for key,label,moving in [('moving_animation','Walking animation',True),('idle_animation','Stopped animation',False)]:
                choices={f"Animation {r['animation_id']} — speed {r['speed']}":r['animation_id']
                    for r in profile if any(r['directions_valid']) and (r['speed']>0 if moving else r['speed']==0)}
                value=row.get(key,next(iter(choices.values())) if len(choices)==1 else None)
                choices={'Keep current graphic':None,**choices}
                self.fields.add(key,label,value,mapped_choices=choices)
            ttk.Label(frame,text="Blocked movement pauses and resumes when clear. Choose this type's moving and stopped animations. Custom speeds and autonomous movement export await native controller validation.",wraplength=480).grid(row=self.fields.n,column=0,columnspan=2,sticky='w',padx=6,pady=6);self.fields.n+=1
        if kind in ('if','repeat'):
            condition_host=ttk.Frame(frame);condition_host.grid(row=self.fields.n,column=0,columnspan=2,sticky='ew');self.fields.n+=1
            if kind=='if':self.condition=ConditionForm(condition_host,self.db,row['condition'],editor=self.editor)
            # Branch commands are edited in the page's command list (If true / Else rows).
            branches=[] if kind=='if' else [('commands','Repeated actions — double-click to add or edit')]
            for branch,label in branches:
                box=ttk.LabelFrame(frame,text=label,padding=5);box.grid(row=self.fields.n,column=0,columnspan=2,sticky='ew');self.fields.n+=1
                tree=ttk.Treeview(box,show='tree',height=5);tree.pack(fill='x')
                self.branch_list(tree,branch)
                tree.bind('<Double-Button-1>',lambda event,t=tree,b=branch:self.branch_edit(t,b,event))
                tree.bind('<Delete>',lambda event,t=tree,b=branch:self.branch_delete(t,b))
        ttk.Button(self.window,text='OK',command=lambda:editor.guard(self.apply)).pack(side='right',padx=10,pady=10)
        # Ctrl+Enter = OK (closes the command page), also inside multi-line text boxes
        def ok(_):
            editor.guard(self.apply);return 'break'   # 'break': no newline in a text box
        def bind(widget):
            if isinstance(widget,tk.Text):
                for key in ('<Control-Return>','<Control-KP_Enter>'):widget.bind(key,ok)
            for child in widget.winfo_children():bind(child)
        for key in ('<Control-Return>','<Control-KP_Enter>'):self.window.bind(key,ok)
        bind(self.window)
        ttk.Button(self.window,text='Cancel',command=self.window.destroy).pack(side='right',pady=10)
        center_on_app(self.window)
    def branch_list(self,tree,branch):
        tree.delete(*tree.get_children())
        for i,command in enumerate(self.row[branch]):tree.insert('','end',iid=str(i),text=LABELS[command['type']]+': '+summary(command,self.db))
        tree.insert('','end',iid='new',text='◇ Add command…')
    def branch_edit(self,tree,branch,event):
        from event_graph_ui import command_template
        hit=tree.identify_row(event.y)
        def edit(kind=None):
            new=hit in ('','new');index=len(self.row[branch]) if new else int(hit)
            row=command_template(kind) if new else self.row[branch][index]
            def save(value):
                if new:self.row[branch].append(value)
                else:self.row[branch][index]=value
                self.branch_list(tree,branch)
        CommandDialog(self.editor,self.window,row,save,database=self.db)
        if hit in ('','new'):command_menu(self.window,edit)
        else:edit()
    def branch_delete(self,tree,branch):
        selected=tree.selection()
        if not selected or selected[0]=='new':return
        del self.row[branch][int(selected[0])];self.branch_list(tree,branch)
    def branch_move(self,tree,branch,step):
        selected=tree.selection()
        if not selected or selected[0]=='new':return
        index=int(selected[0]);other=index+step;commands=self.row[branch]
        if not 0<=other<len(commands):return
        commands[index],commands[other]=commands[other],commands[index]
        self.branch_list(tree,branch);tree.selection_set(str(other))
    def apply(self):
        row=deepcopy(self.row);values=self.fields.values()
        if row['type']=='spawn_class':values['position']=[values.pop('x'),values.pop('y')]
        if row['type']=='move_actor' and isinstance(values['route'],str):values['route']=[s.strip() for s in values['route'].split(',') if s.strip()]
        row.update(values)
        if row['type']=='move_actor':row.pop('skip_impossible',None)
        if self.state_selector is not None:
            for key in ('native_flag_operand','switch_scope','variable_scope'):row.pop(key,None)
            row.update(self.state_selector.value())
        if 'native_flag_operand' in row:row['switch_id']=row['native_flag_operand']
        if getattr(self,'flag_name',None) is not None and 'native_flag_operand' in row:
            from native_flag_index import set_flag_name
            set_flag_name(self.db.document,row['native_flag_operand'],self.flag_name.get());self.editor.dirty=True
        if row['type']=='if':row['condition']=self.condition.value()
        event=new_event_graph('validation',0);event['pages'][0]['commands']=[row];validate_event_graph(event)
        self.save(row);self.window.destroy()


# 2026-10-12: one Play Sound command (the volume one); old play_sound rows still open
LABELS['play_sound_volume'] = 'Play Sound'
try: MENU_LABELS['play_sound_volume'] = 'Play Sound'
except NameError: pass
