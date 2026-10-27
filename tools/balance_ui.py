"""Global balance record editor with alias disclosure."""
import csv,tkinter as tk
from tkinter import ttk
from pathlib import Path
from enemy_definition import BalanceTable
ROOT=Path(__file__).resolve().parents[1]
class BalanceWindow:
 def __init__(self,editor):
  from enemy_definition import BalanceSession
  self.editor=editor
  if not hasattr(editor.session,"extra_files"):editor.session.extra_files={}
  extras=editor.session.extra_files
  if "DATA/BALANCE.BIN" not in extras:raise ValueError("Open a verified game build to select its balance table.")
  self.owner=editor.session;self.session=extras["DATA/BALANCE.BIN"]
  self.window=tk.Toplevel(editor.root);self.window.title("Balance - enemies, items and equipment");self.window.geometry("1080x800")
  ttk.Label(self.window,text="Global balance definitions",font=("Segoe UI",16,"bold"),padding=12).pack(anchor="w")
  body=ttk.Frame(self.window);body.pack(fill="both",expand=True)
  self.tree=ttk.Treeview(body,columns=("name",),show="headings",height=20);self.tree.heading("name",text="Definition / tier");self.tree.column("name",width=360);self.tree.pack(side="left",fill="both",expand=True)
  scroll=ttk.Scrollbar(body,command=self.tree.yview);scroll.pack(side="left",fill="y");self.tree.configure(yscrollcommand=scroll.set)
  self.form=ttk.Frame(body,padding=10);self.form.pack(side="left",fill="both",expand=True)
  names={int(r["item_id"],16):r["name"] for r in csv.DictReader((ROOT/"data/item-slots.csv").open())}
  table=BalanceTable(self.session.data)
  for entry,chain in enumerate(table.chains):
   label=names.get(entry-0x1e,f"Definition {entry}") if 0x1e<=entry<0x80 else f"Enemy / sprite {entry}"
   for tier in range(len(chain)):self.tree.insert("","end",iid=f"{entry}:{tier}",values=(f"{label} | tier {tier} [entry {entry}]",))
  self.tree.bind("<<TreeviewSelect>>",lambda _:self.select())
  self.status=tk.StringVar();ttk.Label(self.window,textvariable=self.status,wraplength=1000,padding=8).pack(fill="x")
  buttons=ttk.Frame(self.window);buttons.pack(fill="x")
  ttk.Button(buttons,text="Undo balance edit",command=lambda:editor.guard(self.undo)).pack(side="left",padx=8,pady=8)
  ttk.Button(buttons,text="Save mod",command=lambda:editor.guard(editor.save_mod_project)).pack(side="left")
  self.tree.selection_set("0:0");self.select()
 def select(self):
  if not self.tree.selection():return
  for child in self.form.winfo_children():child.destroy()
  entry,tier=map(int,self.tree.selection()[0].split(":"));record=BalanceTable(self.session.data).record(entry,tier)
  self.values=[]
  fields=[("HP / base response",record["max_hp"])]+[(f"Damage response {i}",v) for i,v in enumerate(record["damage_responses"])]
  for i,a in enumerate(record["attacks"]):fields.extend([(f"Attack {i} attribute",a["attribute"]),(f"Attack {i} power",a["power"])])
  for i,(label,value) in enumerate(fields):
   col=(i//16)*2;row=i%16
   ttk.Label(self.form,text=label).grid(row=row,column=col,sticky="w")
   var=tk.StringVar(value=str(value));self.values.append(var);ttk.Entry(self.form,textvariable=var,width=7).grid(row=row,column=col+1,pady=2)
  ttk.Button(self.form,text="Apply balance",command=lambda:self.editor.guard(self.apply)).grid(row=17,column=0,columnspan=2,pady=10)
  self.status.set("Shared entries: "+", ".join(map(str,record["alias_entries"]))+". Field meanings are source-derived; damage response values are not labelled as simple defence.")
 def apply(self):
  if self.editor.session is not self.owner:raise ValueError("Reopen balance after changing game data")
  entry,tier=map(int,self.tree.selection()[0].split(":"));v=[int(x.get(),0) for x in self.values]
  attacks=[dict(attribute=v[i],power=v[i+1]) for i in range(12,len(v),2)]
  offset,data=BalanceTable(self.session.data).replacement(entry,tier,max_hp=v[0],damage_responses=v[1:12],attacks=attacks)
  self.session.replace(offset,data,"Balance stats");self.status.set("Applied. Save mod or Build game includes balance changes.")
 def undo(self):
  self.session.undo();self.select()
