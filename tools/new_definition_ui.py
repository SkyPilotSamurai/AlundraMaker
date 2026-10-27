"""Create blank definitions or select an optional same-kind template."""
import tkinter as tk
from tkinter import ttk

class NewDefinitionWindow:
 def __init__(self,editor,kind):
  self.editor=editor;self.kind=kind;self.database=editor.database
  self.window=tk.Toplevel(editor.db_window or editor.root)
  self.window.title('New '+kind.title());self.window.geometry('520x250')
  host=ttk.Frame(self.window,padding=16);host.pack(fill='both',expand=True)
  ttk.Label(host,text='Name').pack(anchor='w')
  self.name=tk.StringVar(value='New '+kind.title())
  ttk.Entry(host,textvariable=self.name).pack(fill='x',pady=5)
  ttk.Label(host,text='Start from' if kind in ('enemy','boss','npc') else 'Template (optional)').pack(anchor='w')
  self.own=kind in ('enemy','boss','npc')
  if self.own:
   # A new enemy / boss / NPC always starts from an existing one (its art,
   # animations, hit boxes and AI), as its own separate class.
   self.templates={f"{r['name']} — {r['id']}":r['id'] for r in self.database.definitions if r['kind']==kind and not r.get('clone_of')
                   and type(r.get('source',{}).get('catalogue_index')) is int and r['source']['catalogue_index']>=256 and type(r['source'].get('balance_entry')) is int}
   self.template=tk.StringVar(value=next(iter(self.templates),''))
  else:
   self.templates={'Blank definition':None}
   self.templates.update({f"{r['name']} — {r['id']}":r['id'] for r in self.database.definitions if r['kind']==kind})
   self.template=tk.StringVar(value='Blank definition')
  ttk.Combobox(host,textvariable=self.template,values=list(self.templates),state='readonly').pack(fill='x',pady=5)
  ttk.Label(host,text=('Your new '+kind+' starts as a copy of the one you pick (look, animations, hit boxes, AI) but has its own HP, attacks and AI settings.') if self.own else 'A blank definition starts without game graphics or behavior. A template copies its settings.',wraplength=480).pack(anchor='w',pady=5)
  footer=ttk.Frame(host);footer.pack(fill='x')
  ttk.Button(footer,text='Create',command=lambda:editor.guard(self.create)).pack(side='right')
  ttk.Button(footer,text='Cancel',command=self.window.destroy).pack(side='right',padx=6)
 def create(self):
  if self.editor.database is not self.database:raise ValueError('The mod changed. Reopen New entry.')
  name=self.name.get().strip()
  if not name:raise ValueError('Give this entry a name')
  if self.own:
   from enemy_clone import create_clone
   template=self.templates.get(self.template.get())
   if not template:raise ValueError('Pick what it starts from')
   row=create_clone(self.editor,self.database.get(template));row['name']=name
  else:row=self.database.new(self.kind,name,template_id=self.templates[self.template.get()])
  self.editor.db_refresh(row['id']);self.editor.db_tabs.select(self.editor.db_frames[self.kind])
  tree=self.editor.db_trees[self.kind];tree.selection_set(row['id']);self.editor.db_select(self.kind)
  self.editor.dirty=True;self.window.destroy()
