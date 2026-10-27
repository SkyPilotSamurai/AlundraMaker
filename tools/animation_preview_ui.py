"""Actual native animation playback and bounded existing-frame edits."""
import tkinter as tk
from tkinter import ttk
from PIL import Image,ImageTk
from animation_preview import available_animations,load_animation,animation_reader,preview_delay_ms
from entity_animation import prepare_animation_edit

class AnimationPreviewWindow:
 def __init__(self,editor,row):
  self.editor=editor;self.session=editor.session;self.row=row;self.index=row.get('source',{}).get('catalogue_index')
  if self.index is None:raise ValueError('Choose a class with a native sprite before editing animation')
  maps=row.get('source',{}).get('observed_maps',[]) or [editor.current_map]
  self.map_id=editor.current_map if editor.current_map in maps else maps[0]
  self.window=tk.Toplevel(editor.db_window);self.window.title(row['name']+' — Native animations');self.window.geometry('1080x760+25+0')
  self.playing=False;self.timer=None;self.selected=None;self.edits={}
  controls=ttk.Frame(self.window,padding=8);controls.pack(fill='x')
  self.animation=tk.StringVar(value='0');self.direction=tk.StringVar(value='0');self.rate=tk.StringVar(value='60')
  choices=available_animations(self.session,self.map_id,self.index)
  ttk.Button(controls,text='Play / stop',command=lambda:editor.guard(self.toggle)).pack(side='left',padx=(0,10))   # animations are picked in the list on the left
  # Direction: four arrows (native order down 0, up 1, left 2, right 3)
  ttk.Label(controls,text='Direction').pack(side='left',padx=(6,2))
  for arrow,value in (('\u2191','1'),('\u2193','0'),('\u2190','2'),('\u2192','3')):
   ttk.Radiobutton(controls,text=arrow,value=value,variable=self.direction,style='Toolbutton',width=3,
                   command=lambda:editor.guard(self.load)).pack(side='left',padx=1)
  ttk.Label(controls,text='Preview ticks / second').pack(side='left');ttk.Spinbox(controls,textvariable=self.rate,from_=1,to=120,width=6).pack(side='left',padx=5)
  # Sprite sheet of this animation: export, edit in any paint program, import (applied at build).
  sheet=ttk.Frame(self.window,padding=(8,0,8,4));sheet.pack(fill='x')
  for label,action in [('Export Sheet...',self.export_sheet),('Import Sheet...',self.import_sheet),('Remove Import',self.remove_import)]:
   ttk.Button(sheet,text=label,command=lambda a=action:editor.guard(a)).pack(side='left',padx=(0,5))
  self.import_note=tk.StringVar();ttk.Label(sheet,textvariable=self.import_note).pack(side='left',padx=8)
  body=ttk.Panedwindow(self.window,orient='horizontal');body.pack(fill='both',expand=True,padx=10)
  # Every animation listed on the left: click one to show it.
  anim_side=ttk.Frame(body);body.add(anim_side,weight=1)
  ttk.Label(anim_side,text='Animations').pack(anchor='w')
  self.anim_list=ttk.Treeview(anim_side,show='tree',selectmode='browse',height=22)
  bar=ttk.Scrollbar(anim_side,orient='vertical',command=self.anim_list.yview);self.anim_list.configure(yscrollcommand=bar.set)
  bar.pack(side='right',fill='y');self.anim_list.pack(fill='both',expand=True)
  from animation_names import auto_names,display_name,class_names
  try:balance=bytes(editor.native_balance_session().data)
  except Exception:balance=None
  self.auto_names=auto_names(self.session,row,choices,balance)
  doc=editor.database.document
  for r in choices:
   self.anim_list.insert('','end',iid=str(r['index']),text=display_name(doc,row,self.auto_names,r['index']))
  def rename(event):
   item=self.anim_list.identify_row(event.y)
   if not item:return
   from tkinter import simpledialog
   names=class_names(doc,row['id'])
   current=names.get(item) or self.auto_names.get(int(item),'')
   new=simpledialog.askstring('Name animation',f'Name for animation {item} (empty = automatic):',initialvalue=current,parent=self.window)
   if new is None:return
   if new.strip():names[item]=new.strip()
   else:names.pop(item,None)
   editor.dirty=True
   self.anim_list.item(item,text=display_name(doc,row,self.auto_names,int(item)))
  self.anim_list.bind('<Double-Button-1>',rename)
  ttk.Label(anim_side,text='Double-click to rename').pack(anchor='w')
  def pick(_=None):
   chosen=self.anim_list.selection()
   if chosen and chosen[0]!=self.animation.get():self.animation.set(chosen[0]);editor.guard(self.load)
  self.anim_list.bind('<<TreeviewSelect>>',pick)
  left=ttk.Frame(body);body.add(left,weight=1)
  self.tree=ttk.Treeview(left,columns=('ticks','image'),show='tree headings',height=22)
  for key,label,width in [('#0','Frame',60),('ticks','Ticks',50),('image','Image reference',95)]:self.tree.heading(key,text=label);self.tree.column(key,width=width)
  self.tree.pack(fill='both',expand=True);self.tree.bind('<<TreeviewSelect>>',lambda _:editor.guard(self.select))
  right=ttk.Frame(body);body.add(right,weight=3)
  self.canvas=tk.Canvas(right,background='#171b22',height=440,highlightthickness=0);self.canvas.pack(fill='both',expand=True)
  fields=ttk.Frame(right,padding=10);fields.pack(fill='x');self.ticks=tk.StringVar();self.speed=tk.StringVar()
  ttk.Label(fields,text='Selected frame ticks').pack(side='left');ttk.Spinbox(fields,textvariable=self.ticks,from_=0,to=127,width=7).pack(side='left',padx=5)
  ttk.Label(fields,text='Native movement speed').pack(side='left',padx=(20,0));ttk.Spinbox(fields,textvariable=self.speed,from_=0,to=65535,width=8).pack(side='left',padx=5)
  buttons=ttk.Frame(right);buttons.pack(fill='x')
  for label,action in [('Move up',lambda:self.move(-1)),('Move down',lambda:self.move(1)),('Undo',self.undo)]:ttk.Button(buttons,text=label,command=lambda a=action:editor.guard(a)).pack(side='left',padx=3)
  # Frame ticks and movement speed are saved automatically (no Apply button).
  self.quiet=False;self.commit_job=None
  for var in (self.ticks,self.speed):var.trace_add('write',lambda *_:self.schedule_commit())
  self.info=tk.StringVar()  # kept for internal status; not shown
  self.window.protocol('WM_DELETE_WINDOW',self.close);self.load()
 def stop(self):
  self.playing=False
  if self.timer is not None:self.window.after_cancel(self.timer);self.timer=None
 def schedule_commit(self):
  if getattr(self,'quiet',True):return
  if self.commit_job is not None:self.window.after_cancel(self.commit_job)
  self.commit_job=self.window.after(500,self.commit)
 def pending(self):
  if self.selected is not None:
   try:ticks=int(self.ticks.get())
   except ValueError:ticks=None
   if ticks is not None and 0<=ticks<=127 and ticks!=(self.clip.frames[self.selected].delay_raw&127):return True
  if any(v.get('delay_raw')!=self.clip.frames[i].delay_raw for i,v in self.edits.items()):return True
  try:speed=int(self.speed.get())
  except ValueError:return False
  return speed!=self.clip.native_speed_raw or self.order!=list(range(len(self.clip.frames)))
 def commit(self):
  self.commit_job=None
  try:
   if not self.pending():return
   keep=self.order.index(self.selected) if self.selected in self.order else None;self.apply()
   if keep is not None and keep<len(self.clip.frames):self.quiet=True;self.refresh(keep);self.quiet=False
  except (ValueError,TypeError) as exc:self.editor.status.set(f'Animation not saved yet: {exc}')
 def load(self):
  self.quiet=True
  try:self._load()
  finally:self.quiet=False
 def _load(self):
  self.stop();self.selected=None;self.edits={}
  self.clip=load_animation(self.session,self.map_id,self.index,int(self.animation.get()),int(self.direction.get()))
  self.speed.set(str(self.clip.native_speed_raw));self.order=list(range(len(self.clip.frames)));self.refresh(0)
  lst=getattr(self,'anim_list',None)
  if lst is not None and lst.exists(self.animation.get()) and lst.selection()!=(self.animation.get(),):
   lst.selection_set(self.animation.get());lst.see(self.animation.get())
  if hasattr(self,'import_note'):self.update_import_note()
  self.info.set(f'Source map {self.map_id} · bank {"global" if self.index<256 else "local"} · {len(self.clip.frames)} frames · transition: {self.clip.terminal_kind} ({self.clip.terminator.hex()}) · next animation: {self.clip.next_animation}')
 def refresh(self,index):
  self.tree.delete(*self.tree.get_children())
  for pos,i in enumerate(self.order):
   frame=self.clip.frames[i];ticks=self.edits.get(i,{}).get('delay_raw',frame.delay_raw)&127
   self.tree.insert('','end',iid=str(i),text=str(pos+1),values=(ticks,frame.image_set_index))
  self.tree.selection_set(str(index));self.select()
 def select(self):
  selected=self.tree.selection()
  if not selected:return
  if not getattr(self,'quiet',True) and self.selected is not None and self.commit_job is not None:
   self.window.after_cancel(self.commit_job);self.commit()
  self.selected=int(selected[0]);frame=self.clip.frames[self.selected]
  previous=getattr(self,'quiet',True);self.quiet=True
  try:self.ticks.set(str(self.edits.get(self.selected,{}).get('delay_raw',frame.delay_raw)&127));self.draw(frame)
  finally:self.quiet=previous
 def draw(self,frame):
  self.canvas.delete('all');w=max(600,self.canvas.winfo_width());h=max(350,self.canvas.winfo_height())
  if frame.image is None:self.canvas.create_text(w/2,h/2,text=frame.unsupported_reason or 'Unsupported frame',fill='#ccd7e5');return
  image=self.clip.canvas_image(frame);scale=max(1,min(6,int(min((w-20)/image.width,(h-20)/image.height))))
  photo=ImageTk.PhotoImage(image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST));self.canvas.create_image(w/2,h/2,image=photo);self.canvas.image=photo
 def stage(self):
  if self.selected is None:return
  ticks=int(self.ticks.get())
  if not 0<=ticks<=127:raise ValueError('Frame delay must fit native 7-bit ticks')
  self.edits[self.selected]={'delay_raw':128|ticks};self.tree.set(str(self.selected),'ticks',ticks)
 def move(self,step):
  self.stage();i=self.order.index(self.selected);other=i+step
  if 0<=other<len(self.order):
   self.order[i],self.order[other]=self.order[other],self.order[i];self.refresh(self.selected);self.commit()
 def toggle(self):
  if self.playing:self.stop();return
  self.stage();self.playing=True;self.play_position=0;self.advance()
 def advance(self):
  self.timer=None
  if not self.playing:return
  index=self.order[self.play_position];frame=self.clip.frames[index];self.draw(frame)
  ticks=max(1,self.edits.get(index,{}).get('delay_raw',frame.delay_raw)&127)
  delay=preview_delay_ms(ticks,int(self.rate.get()))
  self.play_position+=1
  if self.play_position>=len(self.order):
   if self.clip.terminal_kind=='loop':self.play_position=0
   else:self.playing=False;return
  self.timer=self.window.after(delay,lambda:self.editor.guard(self.advance))
 def apply(self):
  self.stop();self.stage();_,sets=animation_reader(self.session,self.map_id,self.index)
  animation=sets[int(self.animation.get())];stream=animation.streams[self.clip.selected_direction]
  if animation.speed_raw!=self.clip.native_speed_raw or len(stream.frames)!=len(self.clip.frames) or any((old.offset,old.delay_raw,old.collision_raw,old.image_set_index)!=(new.offset,new.delay_raw,new.collision_raw,new.image_set_index) for old,new in zip(self.clip.frames,stream.frames)):
   raise ValueError('Animation changed since opening; reload it before applying')
  edits={i:v for i,v in self.edits.items()}
  changes=prepare_animation_edit(self.session.data,animation,stream,int(self.speed.get()),self.order,edits)
  for offset,data,label in changes:self.session.replace(offset,data,label)
  if changes:self.editor.dirty=True
  self.load();self.editor.status.set('Native animation frames edited. Save mod or Build game includes them; shared references share changes.')
 def undo(self):self.stop();self.session.undo();self.load();self.editor.dirty=True
 def document(self):
  return self.editor.database.document
 def sheet_folder(self):
  from pathlib import Path
  folder=Path(__file__).resolve().parents[1]/'game'/'sprite-sheets'/'edits';folder.mkdir(parents=True,exist_ok=True);return folder
 def update_import_note(self):
  from sprite_sheet_import import imported_animations
  done=imported_animations(self.document(),self.index)
  self.import_note.set(('Imported (applied at build): animation '+', '.join(str(a) for a in done)) if done else '')
 def export_sheet(self):
  from tkinter import filedialog
  import re
  from sprite_sheet_import import export_sheet
  name=re.sub(r'[^A-Za-z0-9 ()_-]','',self.row.get('name','class'))
  path=filedialog.asksaveasfilename(parent=self.window,title='Export animation sheet',initialdir=str(self.sheet_folder()),
   initialfile=f"{name} animation {int(self.animation.get()):02d}.png",defaultextension='.png',filetypes=[('PNG image','*.png')])
  if not path:return
  entry=export_sheet(self.session,self.document(),self.map_id,self.index,int(self.animation.get()),path)
  self.editor.status.set(f"Sheet saved: {path} ({len(entry['cells'])} frames). Edit the pictures inside the cells, keep the size, then Import Sheet.")
 def import_sheet(self):
  from tkinter import filedialog
  from sprite_sheet_import import import_sheet
  path=filedialog.askopenfilename(parent=self.window,title='Import edited animation sheet',initialdir=str(self.sheet_folder()),filetypes=[('PNG image','*.png')])
  if not path:return
  result=import_sheet(self.session,self.document(),self.map_id,self.index,int(self.animation.get()),path)
  if result['changed']:self.editor.dirty=True
  extra=(' '+'; '.join(result['notes'])) if result['notes'] else ''
  self.editor.status.set(f"Imported {result['changed']} changed frame picture{'s' if result['changed']!=1 else ''}; they are drawn into the game when you build.{extra}" if result['changed'] else 'No frames changed in that sheet.'+extra)
  self.update_import_note()
 def remove_import(self):
  from sprite_sheet_import import remove_import
  n=remove_import(self.document(),self.index,int(self.animation.get()))
  if n:self.editor.dirty=True
  self.editor.status.set(f'Removed {n} imported frame picture'+('s' if n!=1 else '')+' from this animation.' if n else 'This animation has no imported sheet.')
  self.update_import_note()
 def close(self):
  if getattr(self,'commit_job',None) is not None:self.window.after_cancel(self.commit_job);self.commit()
  self.stop();self.window.destroy()
