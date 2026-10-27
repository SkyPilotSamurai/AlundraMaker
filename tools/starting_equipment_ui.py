"""Choose new-game inventory from existing native database item definitions."""
import tkinter as tk
from tkinter import ttk


from starting_equipment import DEFAULT_START


def source_equipment(exe):
    from starting_equipment import TABLE_BYTE, SUPPORTED_IDS, patch_starting_equipment
    from alundra_memory import parse_exe, runtime_to_offset
    info = parse_exe(exe)
    selected = [i for i in SUPPORTED_IDS if exe[runtime_to_offset(info, TABLE_BYTE+i*8)] & 128]
    # Check the same bounded native routines used by export before trusting it.
    patch_starting_equipment(exe, selected)
    return selected


class StartingEquipmentPanel:
    """Staged starting inventory list; only the database Apply button commits it."""
    def __init__(self, parent, editor):
        self.editor=editor
        stats=ttk.LabelFrame(parent,text='Starting stats (new game)',padding=8);stats.pack(fill='x',pady=6)
        from starting_equipment import STAT_ORDER,STAT_LABELS,STAT_LIMITS
        self.stat_vars={}
        for column,key in enumerate(STAT_ORDER):
            limit=STAT_LIMITS[key]
            ttk.Label(stats,text=STAT_LABELS[key]).grid(row=0,column=column,sticky='w',padx=4)
            var=tk.StringVar();self.stat_vars[key]=var
            ttk.Spinbox(stats,from_=0,to=limit,textvariable=var,width=7).grid(row=1,column=column,sticky='w',padx=4)
        self.stat_defaults=None
        frame=ttk.LabelFrame(parent,text='Initial equipment / inventory',padding=8)
        frame.pack(fill='x',pady=6)
        self.tree=ttk.Treeview(frame,columns=('type',),show='tree headings',height=6,selectmode='extended')
        self.tree.heading('#0',text='Item');self.tree.heading('type',text='Type')
        self.tree.pack(fill='x')
        controls=ttk.Frame(frame);controls.pack(fill='x',pady=6)
        ttk.Button(controls,text='Add items...',command=lambda:editor.guard(self.open_item_grid)).pack(side='left')
        ttk.Button(controls,text='Remove',command=self.remove).pack(side='left',padx=4)
        self.tree.bind('<Delete>',lambda _:self.remove())
        ttk.Button(controls,text='Give all items',command=lambda:editor.guard(self.give_all)).pack(side='left',padx=4)
        self.note=tk.StringVar()
        ttk.Label(frame,textvariable=self.note,wraplength=570).pack(anchor='w',pady=4)
        self.selected=[];self.defaults=[];self.custom=False

    def load(self,row=None):
        self.database=self.editor.database
        self.rows=dict(equipment_rows(self.database))
        self.defaults=[];self.stat_defaults=None
        self.source_note='Source defaults retained; open a matching game EXE to preview them.'
        try:
            from editor_ui import ROOT
            from mod_export import read_datas
            source=self.editor.session
            extra=getattr(source,'extra_files',{}).get('ALUN_CD.EXE')
            if extra is not None:exe=bytes(extra.data)
            elif source.source_verified:exe=(ROOT/'private-inputs/disc/ALUN_CD.EXE').read_bytes()
            elif source.path and source.path.suffix.lower()=='.bin':exe=read_datas(source.path,'ALUN_CD.EXE')
            else:raise ValueError('No matched EXE')
            self.defaults=sorted(set(source_equipment(exe))|set(DEFAULT_START))
            self.source_note='Showing the imported game’s starting inventory.'
            from starting_equipment import read_starting_stats
            self.stat_defaults=read_starting_stats(exe)
        except (ValueError,OSError,IndexError) :pass
        self.meia_id=row['id'] if row and row.get('source',{}).get('player_slot')=='meia' else None
        if self.meia_id:
            # Meia's own starting equipment and stats: used by Build game when Start as Meia is on.
            data=row.get('data',{})
            self.custom=True;self.selected=list(data.get('starting_equipment') or DEFAULT_START)
            stats=data.get('starting_stats') or self.stat_defaults or {}
            self.source_note=''
            for key,var in self.stat_vars.items():var.set(str(stats.get(key,0 if key=='keys' and stats else '')))
            self.refresh();return
        options=self.database.document.get('mod_options',{})
        self.custom='starting_equipment' in options
        self.selected=list(options['starting_equipment']) if self.custom else list(self.defaults)
        stats=options.get('starting_stats') or self.stat_defaults or {}
        for key,var in self.stat_vars.items():var.set(str(stats.get(key,0 if key=='keys' and stats else '')))
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i in sorted(set(self.selected)):
            row=self.rows.get(i)
            self.tree.insert('','end',iid=str(i),text=row['name'] if row else f'Item {i:02X}',values=(row['kind'].title() if row else 'Native item',))
        if getattr(self,'meia_id',None):self.note.set(self.source_note);return
        self.note.set('' if self.custom else self.source_note)

    def add(self,i):
        if i is None:return
        self.selected=sorted(set(self.selected+[i]));self.custom=True;self.refresh()

    def item_for_class(self,class_id):
        return next((i for i,row in self.rows.items() if row['id']==class_id),None)

    def open_item_grid(self):
        from database_picker import DatabasePicker
        def choose(class_id):
            number=self.item_for_class(class_id)
            if number is None:raise ValueError('That item is not a native inventory item (IDs 1-89), so it cannot start in the inventory')
            self.add(number)
        DatabasePicker(self.editor,self.tree.winfo_toplevel(),lambda cid:self.editor.guard(lambda:choose(cid)),
                       kinds=('item',),title='Add starting items',confirm='Add selected',allow_empty=False,keep_open=True)

    def give_all(self):
        """Every native inventory entry (weapons, armour, items: IDs 1-89) in the starting list."""
        self.selected=sorted(set(self.selected)|set(self.rows));self.custom=True;self.refresh()
        if hasattr(self.editor,'db_schedule_autosave'):self.editor.db_schedule_autosave()
        self.editor.status.set(f'Starting inventory: all {len(self.selected)} items. Remove any you do not want.')

    def remove(self):
        removed={int(i) for i in self.tree.selection()}
        if not removed:return
        self.selected=[i for i in self.selected if i not in removed];self.custom=True;self.refresh()

    def reset(self):
        self.selected=list(self.defaults);self.custom=False;self.refresh()

    def apply(self):
        if self.editor.database is not self.database:raise ValueError('The mod changed. Select the player again.')
        stats=self.read_stats()
        if getattr(self,'meia_id',None):
            data=self.database.get(self.meia_id)['data']
            data['starting_equipment']=sorted(set(self.selected))
            data['starting_stats']=stats if stats is not None else None
            return
        options=self.database.document.setdefault('mod_options',{})
        if self.custom:options['starting_equipment']=sorted(set(self.selected))
        else:options.pop('starting_equipment',None)
        if stats is not None:options['starting_stats']=stats
        elif hasattr(self,'stat_vars'):options.pop('starting_stats',None)

    def read_stats(self):
        """Return validated stats when they differ from the source game, else None."""
        if not hasattr(self,'stat_vars'):return None
        from starting_equipment import validate_starting_stats
        if all(not var.get().strip() for var in self.stat_vars.values()):return None
        try:values={key:int(var.get(),0) for key,var in self.stat_vars.items()}
        except ValueError:raise ValueError('Starting HP, MP, Keys and Gilder must be whole numbers')
        values=validate_starting_stats(values)
        defaults=dict({'keys':0},**self.stat_defaults) if self.stat_defaults else None
        return None if values==defaults else values


def equipment_rows(database):
    rows={}
    for row in database.definitions:
        number=row.get('source',{}).get('item_id')
        if row['kind'] not in ('weapon','armor','item') or row.get('clone_of'):continue
        if type(number) is int and 1<=number<90:
            rows.setdefault(number,row)
    return sorted(rows.items())


class StartingEquipmentWindow:
    def __init__(self,editor):
        self.editor=editor
        self.window=tk.Toplevel(editor.db_window or editor.root)
        self.window.title('Alundra — Starting equipment');self.window.geometry('580x650')
        self.database=editor.database
        options=self.database.document.get('mod_options',{})
        enabled='starting_equipment' in options
        self.custom=tk.BooleanVar(value=enabled)
        ttk.Checkbutton(self.window,text='Use custom starting equipment / inventory',variable=self.custom).pack(anchor='w',padx=12,pady=12)
        ttk.Label(self.window,text='Select the items Alundra owns when starting a new game. Ctrl-click to select several. Turn this option off to keep the source game’s starting inventory.',wraplength=540).pack(anchor='w',padx=12)
        host=ttk.Frame(self.window,padding=12);host.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(host,columns=('type',),show='tree headings',selectmode='extended')
        self.tree.heading('#0',text='Item');self.tree.heading('type',text='Type');self.tree.column('type',width=100)
        scroll=ttk.Scrollbar(host,command=self.tree.yview);scroll.pack(side='right',fill='y')
        self.tree.configure(yscrollcommand=scroll.set);self.tree.pack(fill='both',expand=True)
        for number,row in equipment_rows(self.database):
            self.tree.insert('','end',iid=str(number),text=row['name'],values=(row['kind'].title(),))
        selected=[str(i) for i in options.get('starting_equipment',[]) if self.tree.exists(str(i))]
        self.tree.selection_set(selected)
        footer=ttk.Frame(self.window,padding=12);footer.pack(fill='x')
        ttk.Button(footer,text='Apply',command=lambda:editor.guard(self.apply)).pack(side='right')
        ttk.Button(footer,text='Cancel',command=self.window.destroy).pack(side='right',padx=8)

    def apply(self):
        if self.editor.database is not self.database:raise ValueError('The mod changed. Reopen starting equipment.')
        options=self.database.document.setdefault('mod_options',{})
        if self.custom.get():options['starting_equipment']=sorted(int(i) for i in self.tree.selection())
        else:options.pop('starting_equipment',None)
        self.editor.dirty=True
        self.editor.status.set('Starting equipment saved in this mod. Build game applies it to new games.')
        self.window.destroy()
