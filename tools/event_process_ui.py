"""Legacy implementation retained below; live entry uses the unified event editor."""

import struct,tkinter as tk

from tkinter import ttk

from map_inspector import inspect_map

from map_text import dialogue_reference,dialogue_entry,edit_text,edit_dialogue

from event_editor import EDITABLE,reachable_instructions as instructions,script_roots,edit_instruction,assign_entity_hook

from native_event_presentation import present,operand_choices,parse_operand,BRANCHES,help_for,group_for



class LegacyEventProcess:

 def __init__(self,editor,kind,index):

  self.editor=editor;self.session=editor.session;self.map=editor.current_map;self.kind=kind;self.index=index

  self.window=tk.Toplevel(editor.root);self.window.title(f"Game event editor - {kind} {index}");self.window.geometry("1180x800")

  top=ttk.Frame(self.window,padding=10);top.pack(fill="x")

  ttk.Label(top,text=f"Game event {index}",font=("Segoe UI",16,"bold")).pack(side="left")

  ttk.Button(top,text="Find dialogue",command=self.find_dialogue).pack(side="right",padx=6)

  ttk.Button(top,text="Properties / position",command=lambda:editor.area.open_record(kind,index)).pack(side="right")

  ttk.Button(top,text="Delete event",command=lambda:editor.guard(self.delete_event)).pack(side="right",padx=6)

  body=ttk.Panedwindow(self.window,orient='horizontal');body.pack(fill='both',expand=True,padx=8,pady=6)
  left=ttk.Frame(body,width=260,padding=8);body.add(left,weight=1)
  right=ttk.Frame(body,padding=8);body.add(right,weight=4)
  from native_event_view import event_graphic
  from PIL import Image,ImageTk
  image,basis,entity=event_graphic(self.session,self.map,kind,index)
  graphic=tk.Canvas(left,height=180,background='#171b22',highlightthickness=0);graphic.pack(fill='x')
  if image is not None:
   scale=max(1,min(4,int(min(220/image.width,145/image.height))))
   graphic.image=ImageTk.PhotoImage(image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST),master=self.window)
   graphic.create_image(125,80,image=graphic.image)
  else:graphic.create_text(125,80,text='E',fill='#ffe0a5',font=('Segoe UI',28,'bold'))
  ttk.Label(left,text=basis,wraplength=245).pack(anchor='w',pady=4)
  if entity is not None:ttk.Label(left,text=f'Map actor {entity}').pack(anchor='w')

  self.key=tk.StringVar();self.keys={}

  row=inspect_map(self.session.data,self.map)[kind][index];o=int(row["offset"],16);roots=script_roots(self.session,self.map)

  hooks=[("A","On load"),("B","Map trigger"),("C","On update"),("D","On touch"),("E","On deactivate"),("F","On interact")] if kind=="entities" else [("B","Map trigger")]

  self.hook_vars={};self.hook_choices={}

  if kind=="entities":

   assignment=ttk.LabelFrame(left,text="Existing event hooks",padding=6)
   advanced=tk.BooleanVar(value=False)
   ttk.Checkbutton(left,text='Edit process assignments',variable=advanced,command=lambda:assignment.pack(fill='x',pady=6) if advanced.get() else assignment.pack_forget()).pack(anchor='w',pady=6)

   for row_index,(bank,label) in enumerate(hooks):

    hook_value=self.session.data[o+10+ord(bank)-65]

    bank_roots=[key for key in roots if key.startswith(bank+" ")]

    choices={"Inactive":None}

    choices.update({f"{label} · {key}":key for key in bank_roots})

    current=f"{label} · {bank} {hook_value&127}"

    if not hook_value&128 or current not in choices:current="Inactive"

    var=tk.StringVar(value=current);self.hook_vars[bank]=var;self.hook_choices[bank]=choices

    ttk.Label(assignment,text=f"{bank} / {label}").grid(row=row_index*3,column=0,sticky="w",pady=1)

    combo=ttk.Combobox(assignment,textvariable=var,values=list(choices),state="readonly",width=34)

    combo.grid(row=row_index*3+1,column=0,sticky="ew",pady=1)

    ttk.Button(assignment,text="Assign process",command=lambda b=bank:self.assign_hook(b)).grid(row=row_index*3+2,column=0,sticky="w",pady=1)

   assignment.columnconfigure(0,weight=1)

  for bank,label in hooks:

   value=self.session.data[o+(10+ord(bank)-65 if kind=="entities" else 4)]

   key=f"{bank} {value&127}";display=f"{label} ({key})"

   self.keys[display]=key if value&128 and key in roots else None

  ttk.Label(right,text='Event behavior / trigger').pack(anchor='w')
  combo=ttk.Combobox(right,textvariable=self.key,values=list(self.keys),state="readonly",width=45);combo.pack(anchor="w",pady=5)

  combo.bind("<<ComboboxSelected>>",lambda _:self.populate())

  from event_contents_ui import contents_tree
  self.tree=contents_tree(right,height=18)
  self.tree.bind("<<TreeviewSelect>>",lambda _:self.select())

  self.tree.bind("<Double-1>",lambda _:self.select())

  self.form=ttk.LabelFrame(right,text="Command settings",padding=10);self.form.pack(fill="x")

  self.message=tk.StringVar();ttk.Label(self.window,textvariable=self.message,padding=10,wraplength=950).pack(fill="x")

  available=[k for k,v in self.keys.items() if v]

  default=next(iter([k for k in available if k.startswith("On interact")] or available),next(iter(self.keys)))

  self.key.set(default);self.populate()

 def delete_event(self):

  if self.editor.session is not self.session or self.editor.current_map!=self.map:

   raise ValueError('Reopen this event after changing the map or game data')

  from event_deletion import delete_record

  message=delete_record(self.session,self.editor.database,self.map,self.kind,self.index)

  self.editor.status.set(message);self.editor.area.selected_record=None

  self.editor.area.refresh(reload_textures=False);self.window.destroy()

 def assign_hook(self,bank):

  if self.editor.session is not self.session:raise ValueError("Reopen this character after changing game data")

  display=self.hook_vars[bank].get();key=self.hook_choices[bank].get(display,"invalid")

  if key=="invalid":raise ValueError("Choose an existing process for this hook")

  assign_entity_hook(self.session,self.map,self.index,bank,key)

  self.message.set(f"{bank} hook updated. The edit is undoable; save the mod and test the interaction in an emulator.")

  self.window.destroy();EventProcess(self.editor,"entities",self.index)

 def populate(self):

  self._selected_command=None

  self.tree.delete(*self.tree.get_children())

  for child in self.form.winfo_children():child.destroy()

  key=self.keys[self.key.get()]

  if key is None:
   self.tree.insert('','end',iid='unknown-hook',values=('◆ Unknown event','Shared/default behavior — no decoded map-local process for this trigger'))
   self.message.set("Shared/default behavior is preserved. This hook has no decoded map-local command list.");return

  self.rows=instructions(self.session,self.map,key);self.line_by_offset={o:i+1 for i,(o,op,size) in enumerate(self.rows)}

  for i,(o,op,size) in enumerate(self.rows):

   shown=present(self.session,self.map,o,op,size,self.line_by_offset)

   self.tree.insert("","end",iid=str(o),values=(f"{i+1:03d} ◆ {shown['action']}",shown['settings']))

  self.message.set("Commands retain their original order and branch destinations. Double-click a row to edit its known settings; Misc / Unknown bytes are preserved.")

 def select(self):

  selection=self.tree.selection()

  if not selection:return

  if selection[0]=='unknown-hook':
   for child in self.form.winfo_children():child.destroy()
   ttk.Label(self.form,text='Unknown event: shared/default native behavior is not yet decoded.').pack(anchor='w')
   return

  if getattr(self,'_selected_command',None)==selection[0]:return
  self._selected_command=selection[0]
  for child in self.form.winfo_children():child.destroy()

  o=int(selection[0]);op=self.session.data[o]

  if dialogue_reference(self.session.data,o):

   self.show_dialogue(o);return

  if op not in EDITABLE or next((size for pos,code,size in self.rows if pos==o),0)!=1+struct.calcsize("<"+EDITABLE[op][1]):
   size=next((size for pos,code,size in self.rows if pos==o),0)
   shown=present(self.session,self.map,o,op,size,self.line_by_offset)
   ttk.Label(self.form,text=shown['action'],font=('Segoe UI',11,'bold')).pack(anchor='w')
   ttk.Label(self.form,text=shown['settings'],wraplength=850).pack(anchor='w',pady=4)
   ttk.Label(self.form,text='Unknown event — original bytes preserved.' if shown['action'].startswith('Unknown event') else 'Decoded description; editing this command is not yet supported.').pack(anchor='w')
   return

  name,fmt,labels=EDITABLE[op];values=struct.unpack_from("<"+fmt,self.session.data,o+1);self.vars=[];self.branch=None;self.operand_options=[]

  ttk.Label(self.form,text=f"{group_for(op)} · {name}",font=("Segoe UI",11,"bold")).grid(row=0,column=0,columnspan=6,sticky="w",pady=(0,6))

  for i,(label,value) in enumerate(zip(labels,values)):

   var=tk.StringVar(value=str(value));self.vars.append(var)

   choices=operand_choices(op,i);self.operand_options.append(choices)

   if op in BRANCHES and i==len(values)-1:

    label="Continue at line";choices={str(n):offset for offset,n in self.line_by_offset.items() if offset!=o};self.branch=choices

    var.set(str(self.line_by_offset.get(o+value,"")))

    entry=ttk.Combobox(self.form,textvariable=var,values=list(choices),state="readonly",width=18)

   elif choices:

    var.set(next((k for k,v in choices.items() if v==value),str(value)))

    entry=ttk.Combobox(self.form,textvariable=var,values=list(choices),width=30)

   else:entry=ttk.Entry(self.form,textvariable=var,width=14)

   ttk.Label(self.form,text=label).grid(row=1,column=i,padx=4);entry.grid(row=2,column=i,padx=4)

  if op in (0x98,0x99,0x9A):

   help_text={0x98:"Adds money; the game caps the resulting balance at 9999.",0x99:"Pays only when there is enough money. Sets the condition true on payment, false otherwise; use the existing following conditional branch.",0x9A:"Checks money >= this amount without spending. Sets the condition for the existing following branch."}[op]

   ttk.Label(self.form,text=help_text,wraplength=900).grid(row=3,column=0,columnspan=6,sticky="w",pady=6)

  if op in (0x9B,0x9C):
   pass


  self.variant=tk.StringVar(value=str(op))

  if op in (3,4,5,6,0x30,0x31,0x9B,0x9C):

   options={"If condition is true":3,"If condition is false":4} if op in (3,4) else {"Switch ON":5,"Switch OFF":6}

   if op in (0x30,0x31):options={"If switch is ON":0x30,"If switch is OFF":0x31}

   if op in (0x9B,0x9C):options={"Warp lock ON":0x9B,"Warp lock OFF":0x9C}

   self.variants=options;self.variant.set(next(k for k,v in options.items() if v==op))

   ttk.Combobox(self.form,textvariable=self.variant,values=list(options),state="readonly").grid(row=4,column=0,pady=5)

  else:self.variants=None

  ttk.Label(self.form,text=help_for(op),wraplength=930).grid(row=5,column=0,columnspan=6,sticky="w",pady=5)

  ttk.Button(self.form,text="Apply command",command=lambda:self.editor.guard(lambda:self.apply(o,op))).grid(row=6,column=0,pady=8)

 def apply(self,o,op):

  if self.editor.session is not self.session:raise ValueError("Reopen this event after changing game data")

  values=[parse_operand(v.get(),options) if not (self.branch and i==len(self.vars)-1) else 0 for i,(v,options) in enumerate(zip(self.vars,self.operand_options))]

  if self.branch:

   target=self.branch.get(self.vars[-1].get())

   if target is None:raise ValueError("Choose a destination line")

   values[-1]=target-o

  key=self.keys[self.key.get()]

  newop=self.variants[self.variant.get()] if self.variants else op

  edit_instruction(self.session,self.map,key,o,values,newop)

  self.populate();self.tree.selection_set(str(o));self.message.set("Command applied. Save your mod or build a modded game to export it.")



 def show_dialogue(self,offset):

  row=dialogue_entry(self.session,self.map,offset)

  if row is None:

   ttk.Label(self.form,text="This Show Text reference cannot be resolved safely; its bytes remain unchanged.").pack(anchor="w");return

  index,_,raw=row

  ttk.Label(self.form,text="Show Text",font=("Segoe UI",12,"bold")).pack(anchor="w")

  self.text_box=tk.Text(self.form,wrap="word",height=5,font=("Segoe UI",11))

  self.text_box.pack(fill="x",pady=6);self.text_box.insert("1.0",raw.decode("latin-1"))

  ttk.Label(self.form,text=f"{'Map text' if dialogue_reference(self.session.data,offset)[0] else 'Shared text (affects every map using it)'} {index} - up to {len(raw)} bytes. Preserve game formatting codes. Other commands using this text share the edit.",wraplength=930).pack(anchor="w")

  ttk.Button(self.form,text="Apply text",command=lambda:self.editor.guard(lambda:self.apply_text(offset))).pack(anchor="w",pady=6)

 def apply_text(self,offset):

  if self.editor.session is not self.session:raise ValueError("Reopen this event after changing game data")

  row=dialogue_entry(self.session,self.map,offset)

  if row is None:raise ValueError("Dialogue reference is no longer editable")

  edit_dialogue(self.session,self.map,offset,self.text_box.get("1.0","end-1c"))

  self.populate();self.tree.selection_set(str(offset));self.tree.see(str(offset));self.select()

  self.message.set("Show Text updated in the event sequence. Save your mod to keep the edit.")



 def find_dialogue(self):

  from map_text import entries

  window=tk.Toplevel(self.window);window.title("Find map dialogue");window.geometry("850x550")


  rows={str(i):(offset,text) for i,offset,text in entries(self.session,self.map) if text.strip()}

  tree=ttk.Treeview(window,columns=("text",),show="headings",height=10);tree.heading("text",text="Dialogue");tree.pack(fill="both",expand=True,padx=10)

  for i,(offset,text) in rows.items():tree.insert("","end",iid=i,values=(text.decode("latin-1"),))

  box=tk.Text(window,height=6,wrap="word");box.pack(fill="x",padx=10,pady=8)

  message=tk.StringVar();ttk.Label(window,textvariable=message,padding=5).pack()

  def select(_=None):

   if tree.selection():

    i=tree.selection()[0];box.delete("1.0","end");box.insert("1.0",rows[i][1].decode("latin-1"));message.set(f"Text {i}; preserve formatting codes; existing space only.")

  tree.bind("<<TreeviewSelect>>",select)

  def apply():

   if self.editor.session is not self.session:raise ValueError("Reopen after changing game data")

   if not tree.selection():return

   i=tree.selection()[0];edit_text(self.session,self.map,int(i),box.get("1.0","end-1c"))

   updated=next(text for n,o,text in entries(self.session,self.map) if n==int(i));rows[i]=(rows[i][0],updated);tree.item(i,values=(updated.decode("latin-1"),));self.populate();message.set("Dialogue applied. Save mod to keep this edit.")

  ttk.Button(window,text="Apply dialogue",command=lambda:self.editor.guard(apply)).pack(pady=6)

  if rows:tree.selection_set(next(iter(rows)));select()


# Existing events now open the same layout and command forms as custom events.
from native_event_graph_ui import NativeEventGraphWindow as EventProcess
