"""Named project switches/variables and selectors for typed event forms."""
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from project_state_registry import ProjectStateRegistry

LIFETIME_NOTE='Project switches and variables are saved with the game (a second memory-card file, 1 block, next to the Alundra save).'
NEW_SWITCH='New switch…'
NEW_VARIABLE='New variable…'

def state_label(database,kind,identity):
    try:row=ProjectStateRegistry(database.document).get(kind,identity);return f"{identity:04d}: {row['name']}"
    except ValueError:return f'{identity:04d}: missing definition'

def guarded(editor,parent,action):
    if editor is not None:return editor.guard(action)
    try:return action()
    except ValueError as error:pass   # no pop-ups; the editor reports problems in its status line

class ProjectStateWindow:
    def __init__(self,editor,parent=None,on_change=None,database=None):
        self.editor=editor;self.database=database if database is not None else editor.database;self.registry=ProjectStateRegistry(self.database.document);self.on_change=on_change
        self.window=tk.Toplevel(parent or editor.root);self.window.title('Project switches and variables');self.window.geometry('720x480')
        self.notebook=ttk.Notebook(self.window);self.notebook.pack(fill='both',expand=True,padx=10)
        self.trees={};self.frames={}
        for kind,title in [('switches','Switches — ON / OFF'),('variables','Variables — numbers')]:
            frame=ttk.Frame(self.notebook);self.notebook.add(frame,text=title);self.frames[str(frame)]=kind
            tree=ttk.Treeview(frame,columns=('initial',),show='tree headings',selectmode='browse');tree.heading('#0',text='Number / name');tree.heading('initial',text='Initial value')
            tree.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(frame,command=tree.yview);scroll.pack(side='right',fill='y');tree.configure(yscrollcommand=scroll.set)
            tree.bind('<Double-Button-1>',lambda _:editor.guard(self.edit));self.trees[kind]=tree
        bar=ttk.Frame(self.window,padding=10);bar.pack(fill='x')
        for title,action in [('New…',self.new),('Rename / initial value…',self.edit),('Delete',self.delete)]:ttk.Button(bar,text=title,command=lambda a=action:editor.guard(a)).pack(side='left',padx=3)
        ttk.Button(bar,text='Done',command=self.window.destroy).pack(side='right');self.refresh()
    def current(self):return self.frames[self.notebook.select()]
    def refresh(self,select=None):
        for kind,tree in self.trees.items():
            tree.delete(*tree.get_children())
            for row in self.registry.options(kind):
                value=('ON' if row['initial_value'] else 'OFF') if kind=='switches' else row['initial_value']
                tree.insert('','end',iid=str(row['id']),text=f"{row['id']:04d}: {row['name']}",values=(value,))
            if select is not None and tree.exists(str(select)):tree.selection_set(str(select))
        if self.on_change:self.on_change()
    def change_form(self,identity=None):
        kind=self.current();row=self.registry.get(kind,identity) if identity else {'name':'','initial_value':False if kind=='switches' else 0}
        win=tk.Toplevel(self.window);win.title('New '+kind[:-2] if kind=='switches' else 'Variable');win.transient(self.window)
        ttk.Label(win,text='Name',padding=8).grid(row=0,column=0);name=tk.StringVar(value=row['name']);ttk.Entry(win,textvariable=name,width=40).grid(row=0,column=1,padx=8,pady=8)
        initial=tk.BooleanVar(value=row['initial_value']) if kind=='switches' else tk.StringVar(value=str(row['initial_value']))
        ttk.Label(win,text='Initial value',padding=8).grid(row=1,column=0)
        (ttk.Checkbutton(win,text='ON',variable=initial) if kind=='switches' else ttk.Entry(win,textvariable=initial)).grid(row=1,column=1,sticky='w',padx=8)
        def save():
            value=initial.get() if kind=='switches' else int(initial.get(),0)
            updated=self.registry.update(kind,identity,name=name.get(),initial_value=value) if identity else self.registry.create(kind,name.get(),value)
            if self.database is self.editor.database:self.editor.dirty=True
            self.refresh(updated['id']);win.destroy()
        ttk.Button(win,text='Save',command=lambda:self.editor.guard(save)).grid(row=2,column=1,sticky='e',padx=8,pady=10)
    def new(self):self.change_form()
    def edit(self):
        selected=self.trees[self.current()].selection()
        if selected:self.change_form(int(selected[0]))
    def delete(self):
        kind=self.current();selected=self.trees[kind].selection()
        if selected:
            self.registry.delete(kind,int(selected[0]))
            if self.database is self.editor.database:self.editor.dirty=True
            self.refresh()

class StateSelector:
    def __init__(self,parent,database,kind,row=None,editor=None):
        self.database=database;self.kind=kind;self.editor=editor;self.registry=ProjectStateRegistry(database.document)
        row=row or {};self.scope_key='switch_scope' if kind=='switches' else 'variable_scope';self.id_key='switch_id' if kind=='switches' else 'variable_id'
        project=row.get(self.scope_key)=='project' or (not row and kind=='switches') or kind=='variables'
        self.frame=ttk.LabelFrame(parent,text='Switch' if kind=='switches' else 'Variable',padding=6)
        self.scope=tk.StringVar(value='My project' if project else 'Existing game switch');self.selected=tk.StringVar();self.mapping={}
        if kind=='switches':
            box=ttk.Combobox(self.frame,textvariable=self.scope,values=('My project','Existing game switch'),state='readonly',width=24);box.pack(anchor='w');box.bind('<<ComboboxSelected>>',lambda _:self.refresh())
        line=ttk.Frame(self.frame);line.pack(fill='x',pady=5)
        self.combo=ttk.Combobox(line,textvariable=self.selected,state='readonly',width=43);self.combo.pack(side='left',fill='x',expand=True)
        self.combo.bind('<<ComboboxSelected>>',lambda _:guarded(editor,self.frame,self.on_selected))
        ttk.Button(line,text='New…',command=lambda:guarded(editor,self.frame,self.new)).pack(side='left',padx=5)
        self.rename_button=ttk.Button(line,text='Rename…',command=lambda:guarded(editor,self.frame,self.rename));self.rename_button.pack(side='left')
        self.uses_button=None
        if kind=='switches' and editor is not None:
            self.uses_button=ttk.Button(line,text='Jump to events…',command=lambda:guarded(editor,self.frame,self.jump));self.uses_button.pack(side='left',padx=(5,0))
        self.refresh(row.get('native_flag_operand',row.get(self.id_key)))
    def refresh(self,identity=None):
        if identity is None:identity=self.mapping.get(self.selected.get())
        if self.scope.get()=='Existing game switch':
            from event_command_dialog import switch_options
            from native_flag_index import flag_label,set_document
            set_document(self.database.document)
            options=switch_options()
            if identity is not None:options={flag_label(identity,getattr(self.editor,'current_map',None)):identity,**{k:v for k,v in options.items() if v!=identity}}
            self.mapping=options
        else:self.mapping={f"{row['id']:04d}: {row['name']}":row['id'] for row in self.registry.options(self.kind)}
        new_label=NEW_SWITCH if self.kind=='switches' else NEW_VARIABLE
        self.combo.configure(values=list(self.mapping)+[new_label]);self.selected.set(next((label for label,value in self.mapping.items() if value==identity),next(iter(self.mapping),'')))
        self.update_rename_state()
    def update_rename_state(self):
        self.rename_button.configure(state='normal' if self.selected.get() in self.mapping else 'disabled')
        if self.uses_button is not None:
            self.uses_button.configure(state='normal' if self.scope.get()=='Existing game switch' and self.selected.get() in self.mapping else 'disabled')
    def jump(self):
        if self.scope.get()!='Existing game switch' or self.selected.get() not in self.mapping:return
        from native_flag_index import show_uses
        show_uses(self.editor,self.frame.winfo_toplevel(),self.mapping[self.selected.get()])
    def on_selected(self):
        if self.selected.get() in (NEW_SWITCH,NEW_VARIABLE):self.new()
        else:self.update_rename_state()
    def new(self):
        row=self.registry.create_auto(self.kind);self.scope.set('My project');self.refresh(row['id'])
        if self.editor is not None and self.database is getattr(self.editor,'database',self.database):self.editor.dirty=True
        return row
    def rename(self):
        if self.selected.get() not in self.mapping:return
        if self.scope.get()=='Existing game switch':
            from native_flag_index import flag_name,set_flag_name
            identity=self.mapping[self.selected.get()]
            name=simpledialog.askstring('Name game switch','Name',initialvalue=flag_name(identity) or '',parent=self.frame)
            if name is None:return
            set_flag_name(self.database.document,identity,name);self.refresh(identity)
            if self.editor is not None:self.editor.dirty=True
            return
        identity=self.mapping[self.selected.get()];row=self.registry.get(self.kind,identity)
        name=simpledialog.askstring('Rename switch' if self.kind=='switches' else 'Rename variable',
            'Name',initialvalue=row['name'],parent=self.frame)
        if name is None:return
        self.registry.update(self.kind,identity,name=name);self.refresh(identity)
        if self.editor is not None and self.database is getattr(self.editor,'database',self.database):self.editor.dirty=True
    def value(self):
        if self.selected.get() not in self.mapping:raise ValueError('Create or choose a named project '+('switch' if self.kind=='switches' else 'variable'))
        identity=self.mapping[self.selected.get()]
        if self.scope.get()=='Existing game switch':return {'switch_id':identity,'native_flag_operand':identity}
        self.registry.get(self.kind,identity)
        return {self.id_key:identity,self.scope_key:'project'}
