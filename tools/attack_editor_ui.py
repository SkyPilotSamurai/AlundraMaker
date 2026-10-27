"""Animation preview with native-matched existing BALANCE attack edits."""
from copy import deepcopy
import tkinter as tk
from tkinter import ttk
from animation_preview_ui import AnimationPreviewWindow
from enemy_definition import BalanceTable
from native_attack_balance import selected_attack,attack_edit
from attack_attributes import attribute_choices,attribute_label,parse_attribute

class AttackEditorWindow(AnimationPreviewWindow):
 def __init__(self,editor,row):
  if row.get('kind') not in ('enemy','boss','weapon') or row.get('clone_of'):
   raise ValueError('Choose an existing enemy, boss or weapon source class. Independent cloned attack records are not allocated yet.')
  self.entry=row.get('source',{}).get('balance_entry')
  if type(self.entry) is not int:raise ValueError('This class has no matched native balance entry')
  self.balance=editor.native_balance_session();self.tier=tk.StringVar(value='0')
  BalanceTable(self.balance.data).record(self.entry)
  preview_row=row
  if row['kind']=='weapon':
   preview_row=deepcopy(row);preview_row['source']['catalogue_index']=0
  super().__init__(editor,preview_row)
  self.window.title(row['name']+' — Attacks and animations')
  self.tree.configure(height=12);self.canvas.configure(height=260)
  self.window.geometry(f"1080x{min(900,editor.root.winfo_screenheight()-80)}+25+0")
  host=ttk.LabelFrame(self.window,text='Attack for this animation',padding=8)
  host.pack(fill='x',padx=10,pady=5,before=self.window.winfo_children()[0])
  self.power=tk.StringVar();self.attribute=tk.StringVar();self.loading=False;self.apply_job=None
  ttk.Label(host,text='Damage').grid(row=0,column=0,padx=5,sticky='w')
  ttk.Spinbox(host,textvariable=self.power,from_=0,to=255,width=7).grid(row=0,column=1,padx=5)
  ttk.Label(host,text='Attribute').grid(row=0,column=2,padx=5,sticky='w')
  self.attribute_combo=ttk.Combobox(host,textvariable=self.attribute,values=list(attribute_choices()),state='readonly',width=26)
  self.attribute_combo.grid(row=0,column=3,padx=5)
  for var in (self.power,self.attribute):var.trace_add('write',lambda *_:self.schedule_apply())
  self.attack_info=tk.StringVar();ttk.Label(host,textvariable=self.attack_info,wraplength=1000).grid(row=1,column=0,columnspan=4,sticky='w')
  self.load()
 def load(self):
  super().load()
  if not hasattr(self,'power'):return
  record=BalanceTable(self.balance.data).record(self.entry,int(self.tier.get()))
  self.attack=selected_attack(record,int(self.animation.get()))
  self.selected_record=record
  self.loading=True
  try:
   if self.attack is None:
    self.power.set('');self.attribute.set('');self.attack_info.set('This animation has no attack.');return
   self.power.set(str(self.attack['power']));self.attribute_combo.configure(values=list(attribute_choices(self.attack['attribute'])));self.attribute.set(attribute_label(self.attack['attribute']));self.attack_info.set('')
  finally:self.loading=False
 def schedule_apply(self):
  # Changes are remembered automatically (no Apply button).
  if self.loading or getattr(self,'attack',None) is None:return
  if self.apply_job is not None:self.window.after_cancel(self.apply_job)
  self.apply_job=self.window.after(500,self.auto_apply)
 def auto_apply(self):
  self.apply_job=None
  try:
   if self.power.get().strip()==str(self.attack['power']) and parse_attribute(self.attribute.get())==self.attack['attribute']:return
   self.apply_attack()
  except (ValueError,TypeError) as exc:self.editor.status.set(f'Attack not saved yet: {exc}')
 def apply_attack(self):
  if self.attack is None:raise ValueError('This record has no editable attack pair')
  table=BalanceTable(self.balance.data);record=table.record(self.entry,int(self.tier.get()))
  current=selected_attack(record,int(self.animation.get()))
  if current!=self.attack:raise ValueError('Attack data changed since preview; choose the animation again before applying')
  report=attack_edit(self.balance,self.entry,int(self.tier.get()),int(self.animation.get()),power=int(self.power.get(),0),attribute=parse_attribute(self.attribute.get()),allow_shared_fallback=True)
  self.sync_classes();self.editor.dirty=True;self.load()
  self.editor.status.set(f"Saved attack for {self.row['name']}.")
 def sync_classes(self):
  table=BalanceTable(self.balance.data)
  for row in self.editor.database.definitions:
   entry=row.get('source',{}).get('balance_entry')
   if type(entry) is int and row['kind'] in ('enemy','boss','weapon') and not row.get('clone_of'):
    row['data']['attacks']=deepcopy(table.record(entry,0)['attacks'])
  self.editor.db_refresh(self.row['id']);self.editor.db_select(self.row['kind'])
 def undo_attack(self):
  self.balance.undo();self.sync_classes();self.load();self.editor.dirty=True
 def open_boxes(self):
  from frame_collision_ui import FrameCollisionWindow
  FrameCollisionWindow(self.editor,self.row)
