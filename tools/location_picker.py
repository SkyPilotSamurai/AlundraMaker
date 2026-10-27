"""Searchable location picker for the area editor."""
import tkinter as tk
from tkinter import ttk
from map_names import map_label,map_is_reported_unused,NAMES

# Randomizer PatchNewGame native variant mappings and map241 portal table.
from editor_open_world import KEPT_INOA_MAPS
OPEN_WORLD_INOA=frozenset(KEPT_INOA_MAPS)

def initial_map(open_world=False):
 # Randomizer map_codes.hpp MAP_INOA_RANDOMIZER; stock post-ship Jess arrival.
 return 241 if open_world else 163

def location_ids(open_world=False):
 if not open_world:return list(range(483))
 return [n for n in range(483) if n in OPEN_WORLD_INOA or
         (not NAMES.get(str(n),{}).get('name','').casefold().startswith('inoa') and n!=242)]

class LocationPicker:
 def __init__(self,editor,on_choose=None,title=None,button=None):
  self.editor=editor;self.on_choose=on_choose
  self.window=tk.Toplevel(editor.root)
  self.window.title(title or ("Add Map Tiles: Choose Map" if on_choose else "Choose Map"))
  self.window.geometry("580x560")
  self.window.minsize(400,300)
  self.window.transient(editor.root)
  frame=ttk.Frame(self.window,padding=12);frame.pack(fill="both",expand=True)
  ttk.Label(frame,text="Search by location name or map ID").pack(anchor="w")
  self.query=tk.StringVar()
  search=ttk.Entry(frame,textvariable=self.query);search.pack(fill="x",pady=(6,10))
  body=ttk.Frame(frame);body.pack(fill="both",expand=True)
  self.list=ttk.Treeview(body,columns=("location",),show="headings",selectmode="browse")
  self.list.heading("location",text="Location")
  self.list.column("location",width=490)
  scroll=ttk.Scrollbar(body,orient="vertical",command=self.list.yview)
  self.list.configure(yscrollcommand=scroll.set)
  scroll.pack(side="right",fill="y");self.list.pack(side="left",fill="both",expand=True)
  footer=ttk.Frame(frame);footer.pack(fill="x",pady=(10,0))
  self.count=tk.StringVar();ttk.Label(footer,textvariable=self.count).pack(side="left")
  ttk.Button(footer,text=button or ("Add tiles" if on_choose else "Open map"),command=lambda:editor.guard(self.choose)).pack(side="right")
  if not on_choose:
   ttk.Button(footer,text="New Map…",command=lambda:editor.guard(self.new_map)).pack(side="right",padx=6)
   ttk.Button(footer,text="Rename…",command=lambda:editor.guard(self.rename)).pack(side="right")
  ttk.Button(footer,text="Cancel",command=self.window.destroy).pack(side="right",padx=6)
  self.query.trace_add("write",self.refresh)
  self.list.bind("<Double-1>",lambda event:editor.guard(self.choose))
  self.window.bind("<Return>",lambda event:editor.guard(self.choose))
  self.window.bind("<Escape>",lambda event:self.window.destroy())
  self.refresh();search.focus_set()
 def refresh(self,*_):
  query=self.query.get().strip().casefold()
  current=str(getattr(self.editor,"current_map",initial_map()))
  previous=self.list.selection()
  wanted=previous[0] if previous else current
  self.list.delete(*self.list.get_children())
  open_world=False if self.on_choose else self.editor.database.document.get('mod_options',{}).get('open_world',False)
  from map_slots import map_count
  ids=location_ids(open_world)+list(range(483,map_count(self.editor.session.data) if self.editor.session is not None else 483))
  rows=[(n,map_label(n)) for n in ids if query in map_label(n).casefold()]
  rows.sort(key=lambda row:row[0])  # every map in number order, unused and new maps included
  for number,label in rows:self.list.insert("","end",iid=str(number),values=(label,))
  self.count.set(f"{len(rows)} locations"+(' · Open-world Inoa' if open_world else ''))
  if rows:
   default=str(initial_map(open_world))
   chosen=wanted if self.list.exists(wanted) else default if self.list.exists(default) else str(rows[0][0])
   self.list.selection_set(chosen);self.list.focus(chosen);self.list.see(chosen)
 def rename(self):
  selection=self.list.selection()
  if not selection:raise ValueError('Choose a map to rename')
  self.editor.rename_map(int(selection[0]))
 def new_map(self):
  self.window.destroy();self.editor.new_map()
 def choose(self):
  selection=self.list.selection()
  if not selection:return
  self.editor.need()
  selected=int(selection[0])
  if self.on_choose:
   self.on_choose(selected);self.window.destroy();return
  self.editor.map_id.set(str(selected))
  try:self.editor.load_map()
  finally:
   if getattr(self.editor,"current_map",None)!=selected:
    self.editor.map_id.set(str(self.editor.current_map))
  if self.editor.current_map==selected:self.window.destroy()
