"""Music catalogue and native export-backed map/event selection."""
import tkinter as tk
from tkinter import ttk
from music_database import TRACK_COUNT,map_music_values,music_rows
from game_audio_names import music_name

def music_names(editor):
    return {f"{i:03d} - {music_name(editor.database.document,i)}":i for i in range(TRACK_COUNT) if i not in __import__('game_audio_names').HIDDEN_TRACKS}

class MusicTab:
    def __init__(self,editor,parent):
        self.editor=editor;self.frame=ttk.Frame(parent);parent.add(self.frame,text='Music')
        bar=ttk.Frame(self.frame,padding=8);bar.pack(fill='x')
        self.search=tk.StringVar();ttk.Label(bar,text='Find music').pack(side='left')
        ttk.Entry(bar,textvariable=self.search).pack(side='left',padx=6)
        ttk.Button(bar,text='Use for current map',command=lambda:editor.guard(self.assign_map)).pack(side='left',padx=4)
        ttk.Button(bar,text='Add to event…',command=lambda:editor.guard(self.add_event)).pack(side='left',padx=4)
        from audio_preview import PreviewBar
        PreviewBar(bar,editor,'music',self.selected).frame.pack(side='left',padx=8)
        self.tree=ttk.Treeview(self.frame,columns=('name','maps'),show='tree headings',selectmode='browse')
        for key,label,width in [('#0','ID',70),('name','Name',350),('maps','Maps using this track',480)]:
            self.tree.heading(key,text=label);self.tree.column(key,width=width)
        scrollbar=ttk.Scrollbar(self.frame,command=self.tree.yview);scrollbar.pack(side='right',fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set);self.tree.pack(fill='both',expand=True,padx=8,pady=8)
        bottom=ttk.Frame(self.frame,padding=8);bottom.pack(fill='x');self.name=tk.StringVar()
        ttk.Label(bottom,text='Name').pack(side='left');ttk.Entry(bottom,textvariable=self.name,width=45).pack(side='left',padx=6)
        ttk.Button(bottom,text='Rename',command=lambda:editor.guard(self.rename)).pack(side='left')
        self.note=tk.StringVar(value='')
        ttk.Label(self.frame,textvariable=self.note,padding=8).pack(fill='x')
        self.tree.bind('<Double-Button-1>',lambda _:editor.guard(lambda:__import__('audio_preview').play_music(editor,self.selected())))
        self.tree.bind('<<TreeviewSelect>>',lambda _:self.selection_changed());self.search.trace_add('write',lambda *_:self.refresh())
        self.refresh()
    def selected(self):
        selection=self.tree.selection()
        if not selection:raise ValueError('Choose a music track')
        return int(selection[0])
    def refresh(self):
        names=self.editor.database.document.get('music_names',{});needle=self.search.get().casefold();usage={}
        try:
            from sound_database import library_for_editor
            lib=library_for_editor(self.editor)
            if lib:
                music_rows(lib.exe,lib.sound)
                overrides=self.editor.database.document.get('map_music',{})
                for map_id,default in enumerate(map_music_values(lib.exe)):
                    track=overrides.get(str(map_id),default);usage.setdefault(track,[]).append(map_id)
        except (ValueError,OSError) as error:self.note.set(str(error))
        self.tree.delete(*self.tree.get_children())
        for i in range(TRACK_COUNT):
            if i in __import__('game_audio_names').HIDDEN_TRACKS:continue
            name=music_name(self.editor.database.document,i)
            if needle and needle not in f'{i:03d} {name}'.casefold():continue
            maps=usage.get(i,[]);label=', '.join(map(str,maps[:24]))+(' …' if len(maps)>24 else '')
            self.tree.insert('','end',iid=str(i),text=f'{i:03d}',values=(name,label))
    def selection_changed(self):
        if self.tree.selection():self.name.set(music_name(self.editor.database.document,self.selected()))
    def rename(self):
        i=self.selected();name=self.name.get().strip()
        if not name:raise ValueError('Give the track a name')
        self.editor.database.document.setdefault('music_names',{})[str(i)]=name;self.editor.dirty=True;self.refresh();self.tree.selection_set(str(i))
    def assign_map(self):
        map_id=self.editor.current_map
        if self.editor.session is None or map_id is None:raise ValueError('Choose a map first')
        i=self.selected();self.editor.database.document.setdefault('map_music',{})[str(map_id)]=i
        self.editor.dirty=True;self.note.set(f'Map {map_id} will use music {i:03d} when exported. Story events may change music afterwards.')
        self.refresh();self.tree.selection_set(str(i))
    def add_event(self):
        music_id=self.selected();events=self.editor.database.document.get('event_graphs',[])
        if not events:raise ValueError('Create an event by double-clicking the map first')
        win=tk.Toplevel(self.frame);win.title('Add music to event');win.transient(self.editor.db_window)
        choices={f"{g['name']} — Map {g['map_id']} [{g['id']}]":g['id'] for g in events};selected=tk.StringVar(value=next(iter(choices)))
        ttk.Combobox(win,textvariable=selected,values=list(choices),state='readonly',width=65).pack(padx=12,pady=12)
        def add():
            self.editor.open_event_builder(choices[selected.get()]);active=self.editor.event_graph_window
            active.current_page()['commands'].append(dict(type='change_music',music_id=music_id))
            active.refresh_commands();self.editor.dirty=True;win.destroy()
        ttk.Button(win,text='Add Change music',command=lambda:self.editor.guard(add)).pack(padx=12,pady=8)
