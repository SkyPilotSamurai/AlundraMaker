"""Database Sounds tab and reusable event sound picker."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
from sound_database import library_for_editor
from game_audio_names import sound_name

# 0-255 shared sounds; 256-501 room sounds (each in its home room's sound set; the export
# copies a used one into the set of the map that plays it). 502-511 are spare/unused records.
SOUND_IDS=range(502)

def sound_names(editor):
 return {f"{i:03d} - {sound_name(editor.database.document,i)}":i for i in SOUND_IDS}

def play_preview(editor,sound_id):
 from audio_preview import play_sound
 play_sound(editor,sound_id)

def stop_preview(editor=None):
 from audio_preview import stop
 stop(editor)

class SoundsTab:
 def __init__(self,editor,parent):
  self.editor=editor;self.frame=ttk.Frame(parent);parent.add(self.frame,text='Sounds')
  toolbar=ttk.Frame(self.frame,padding=8);toolbar.pack(fill='x')
  self.search=tk.StringVar();ttk.Label(toolbar,text='Find sound').pack(side='left');entry=ttk.Entry(toolbar,textvariable=self.search);entry.pack(side='left',padx=6)
  from audio_preview import PreviewBar
  PreviewBar(toolbar,editor,'sound',self.selected).frame.pack(side='left',padx=6)
  ttk.Button(toolbar,text='Add to event...',command=lambda:editor.guard(self.add_to_event)).pack(side='left',padx=3)
  self.tree=ttk.Treeview(self.frame,columns=('name','bank'),show='tree headings',selectmode='browse')
  for column,label,width in [('#0','ID',65),('name','Name',330),('bank','Bank',150)]:self.tree.heading(column,text=label);self.tree.column(column,width=width)
  scroll=ttk.Scrollbar(self.frame,command=self.tree.yview);scroll.pack(side='right',fill='y');self.tree.configure(yscrollcommand=scroll.set);self.tree.pack(fill='both',expand=True,padx=8,pady=6)
  self.tree.bind('<Double-Button-1>',lambda _:editor.guard(self.play))
  bottom=ttk.Frame(self.frame,padding=8);bottom.pack(fill='x');self.name=tk.StringVar()
  ttk.Label(bottom,text='Name').pack(side='left');ttk.Entry(bottom,textvariable=self.name,width=42).pack(side='left',padx=6);ttk.Button(bottom,text='Rename',command=self.rename).pack(side='left')
  self.note=tk.StringVar(value='')
  ttk.Label(self.frame,textvariable=self.note,wraplength=1000,padding=8).pack(fill='x')
  self.tree.bind('<<TreeviewSelect>>',lambda _:self.selected_changed());self.search.trace_add('write',lambda *_:self.refresh())
  self.rows=None;self.source_session=editor.session;self.refresh()
 def refresh(self):
  if self.source_session is not self.editor.session:self.rows=None;self.source_session=self.editor.session
  if self.rows is None:
   try:
    lib=library_for_editor(self.editor);self.rows=lib.rows() if lib else []
   except (ValueError,OSError,StopIteration) as exc:self.rows=[];self.note.set(str(exc))
  metadata={row['id']:row for row in self.rows};names=self.editor.database.document.get('sound_names',{});needle=self.search.get().casefold();self.tree.delete(*self.tree.get_children())
  for i in SOUND_IDS:
   name=sound_name(self.editor.database.document,i);row=metadata.get(i,{})
   if needle and needle not in f'{i:03d} {name}'.casefold():continue
   bank='Global' if row.get('bank')==-1 else f"Map bank {row['bank']}" if row else 'Unknown'
   self.tree.insert('','end',iid=str(i),text=f'{i:03d}',values=(name,bank))
 def selected(self):
  selected=self.tree.selection()
  if not selected:raise ValueError('Choose a sound')
  return int(selected[0])
 def selected_changed(self):
  if self.tree.selection():self.name.set(sound_name(self.editor.database.document,self.selected()))
 def rename(self):
  def change():
   i=self.selected();name=self.name.get().strip()
   if not name:raise ValueError('Give the sound a name')
   self.editor.database.document.setdefault('sound_names',{})[str(i)]=name;self.editor.dirty=True;self.refresh();self.tree.selection_set(str(i))
  self.editor.guard(change)
 def play(self):play_preview(self.editor,self.selected())
 def add_to_event(self):
  sound_id=self.selected();events=self.editor.database.document.get('event_graphs',[])
  if not events:raise ValueError('Create an event by double-clicking the map first, then add a Play sound command')
  win=tk.Toplevel(self.frame);win.title('Add sound to event');win.transient(self.editor.db_window)
  choices={f"{row['name']} - Map {row['map_id']} [{row['id']}]":row['id'] for row in events};selected=tk.StringVar(value=next(iter(choices)))
  ttk.Combobox(win,textvariable=selected,values=list(choices),state='readonly',width=65).pack(padx=12,pady=12)
  def add():
   self.editor.open_event_builder(choices[selected.get()]);active=self.editor.event_graph_window
   from event_command_dialog import CommandDialog
   def save(row):
    active.current_page()['commands'].append(row);active.command_index=None;active.refresh_commands();self.editor.dirty=True
   CommandDialog(self.editor,active.window,{'type':'play_sound','sound_id':sound_id},save,database=active.db);win.destroy()
  ttk.Button(win,text='Choose event page and sound',command=lambda:self.editor.guard(add)).pack(padx=12,pady=8)
