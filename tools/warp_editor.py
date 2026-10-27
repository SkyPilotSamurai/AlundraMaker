"""Existing map portal edits; fixed 12-byte records, no relocation."""
from dataclasses import replace
import tkinter as tk
from tkinter import ttk
from portal_records import Portal
from map_names import map_label,map_number

def warps(session,m):
 base,h=session.layout(m);start=base+h[0]+0x42c
 if start+64*12>base+h[1]:raise ValueError("Portal table outside map info")
 result=[]
 for i in range(64):
  o=start+i*12;p=Portal.read(session.data,o)
  if (p.x1,p.y1,p.x2,p.y2)==(0,0,255,255) or p.destination_map<0:continue
  result.append((i,o,p))
 return result

def set_warp(session,m,index,values):
 row=next((r for r in warps(session,m) if r[0]==index),None)
 if row is None:raise ValueError("Select an existing warp")
 _write_warp(session,m,row[1],Portal(*values),"Warp point and activation tiles")

def _write_warp(session,m,record_offset,p,label,warp_square=False):
 from map_slots import map_exists
 if not 0<=p.destination_map<2547 or (p.destination_map>=483 and not map_exists(session.data,p.destination_map)):raise ValueError("Destination map must be0-2546 and exist")
 if p.x1>p.x2 or p.y1>p.y2 or (p.x1,p.y1,p.x2,p.y2)==(0,0,255,255):raise ValueError("Invalid warp area")
 encoded=p.encode()
 from area_map import grid
 width,height,cells=grid(session,m)
 edits=[(record_offset,encoded)]
 for y in range(max(0,p.y1),min(height-1,p.y2)+1):
  for x in range(max(0,p.x1),min(width-1,p.x2)+1):
   cell=cells[y*width+x];offset=cell['offset']+1
   # Actual cold-boot evidence: an ordinary floor needs GroundProperty80
   # (native expanded flag8000) to activate a standing, facing portal.
   # Keep other properties and old-area flags: other portals/events can use
   # them. Record and tile changes form one reversible edit.
   edits.append((offset,bytes((session.data[offset]|0x80,))))
   if warp_square:edits.append((offset-1,bytes((session.data[offset-1]|0x04,))))   # ground bit 4: taken at once, any facing (stock save room panels)
 start=min(o for o,raw in edits);stop=max(o+len(raw) for o,raw in edits)
 replacement=bytearray(session.data[start:stop])
 for offset,raw in edits:replacement[offset-start:offset-start+len(raw)]=raw
 session.replace(start,replacement,label)

def free_warp_slot(session,m):
 """First unused portal slot. The game takes the first portal containing the
 player's tile and stops at an unused record (destination map 0), so new
 warps go in the first free slot after the existing ones."""
 base,h=session.layout(m);start=base+h[0]+0x42c
 for i in range(64):
  p=Portal.read(session.data,start+i*12)
  if (p.x1,p.y1,p.x2,p.y2)==(0,0,255,255):return i,start+i*12
 raise ValueError("This map already has 64 warps")

def add_warp(session,m,x,y,destination_map,destination_x,destination_y,z,flags=2,width=1,height=1,warp_square=False):
 """Create a new warp like the game's own (record + floor activation flag). Returns its index."""
 index,offset=free_warp_slot(session,m)
 if not 0<destination_map<2547:raise ValueError("Destination map must be1-2546")
 x1,y1,x2,y2=area_bounds(x,y,width,height)
 _write_warp(session,m,offset,Portal(x1,y1,x2,y2,destination_map,destination_x,destination_y,z,flags),"New warp",warp_square)
 return index

OPPOSITE={0:1,1:0,2:3,3:2}   # Down, Up, Left, Right

def guess_door_facing(session,m,x,y):
 """Which way the player walks through a door on tile x,y: towards the side
 that is wall or empty (0 Down, 1 Up, 2 Left, 3 Right). Up when unclear."""
 from area_map import grid
 width,height,cells=grid(session,m)
 def open_floor(a,b):
  if not (0<=a<width and 0<=b<height):return False
  v=cells[b*width+a]['values'];return v[4]!=0xFFFF and v[0]==0
 for facing,(dx,dy) in ((1,(0,-1)),(0,(0,1)),(2,(-1,0)),(3,(1,0))):
  if not open_floor(x+dx,y+dy):return facing
 return 1

def auto_arrive(session,m,p):
 """Auto arrive facing: the opposite of the way back's entry direction (he faces away from the
 door he comes out of); without a way back, the opposite of this warp's own entry direction."""
 try:
  back=[q for _,_,q in warps(session,p.destination_map) if q.destination_map==m]
  if back:
   q=min(back,key=lambda q:abs(min(max(p.destination_x,q.x1),q.x2)-p.destination_x)+abs(min(max(p.destination_y,q.y1),q.y2)-p.destination_y))
   return OPPOSITE[(q.flags>>14)&3]
 except Exception:pass
 return (p.flags>>14)&3   # one-way warp: the same way he walked in (user 2026-10-26)

def has_way_back(session,m,p):
 try:return any(q.destination_map==m for _,_,q in warps(session,p.destination_map))
 except Exception:return False

def door_flags(facing,arrive_facing,low=0x002):
 """Use the door walking `facing`; arrive facing `arrive_facing`."""
 return (facing<<14)|(arrive_facing<<12)|(low&0x0FFF)

def add_two_way_warp(session,source_map,sx,sy,destination_map,dx,dy,here=None,there=None,way_back=True):
 """A door like the game's: walk through it to arrive at the other tile, and
 a return door there (when that tile has no warp yet). Returns (index, back).
 here/there: the way each door is walked through (0 Down, 1 Up, 2 Left, 3 Right);
 None guesses it from the tiles around it."""
 if there is None:there=guess_door_facing(session,destination_map,dx,dy)
 if here is None:here=guess_door_facing(session,source_map,sx,sy)
 grouped=session.group('New two-way warp') if hasattr(session,'group') else None
 if grouped is not None:
  with grouped:return _two_way(session,source_map,sx,sy,destination_map,dx,dy,here,there,way_back)
 return _two_way(session,source_map,sx,sy,destination_map,dx,dy,here,there,way_back)

def _two_way(session,source_map,sx,sy,destination_map,dx,dy,here,there,way_back=True):
 index=add_warp(session,source_map,sx,sy,destination_map,dx,dy,0,flags=door_flags(here,OPPOSITE[there] if way_back else here))   # Auto: face away from the way back's door (user 2026-10-26)
 back=None
 if way_back and (destination_map!=source_map or (dx,dy)!=(sx,sy)):   # Single warp: no way back (user 2026-10-25)
  taken=any(p.x1<=dx<=p.x2 and p.y1<=dy<=p.y2 for _,_,p in warps(session,destination_map))
  try:back=add_warp(session,destination_map,dx,dy,source_map,sx,sy,0,flags=door_flags(there,OPPOSITE[here]))
  except ValueError:back=None
  if back is not None and taken:
   # the tile already has a warp: the game takes the first warp holding the tile, so the way
   # back goes first in the table (the other warps keep their records, one slot later)
   back=_to_front(session,destination_map,back)
 return index,back

def _to_front(session,m,index):
 base,h=session.layout(m);start=base+h[0]+0x42c
 table=bytearray(session.data[start:start+64*12])
 row=bytes(table[index*12:index*12+12])
 table[12:(index+1)*12]=table[0:index*12];table[0:12]=row
 session.replace(start,table,"Way back first")
 return 0

def delete_warp(session,m,index):
 """Remove a warp record. The game stops at the first unused record, so the
 warps after it move up one slot and the last slot becomes unused (one
 undoable edit). Floor activation flags are left alone: other portals or
 events may use them, and without a portal record they do nothing."""
 base,h=session.layout(m);start=base+h[0]+0x42c
 if not any(r[0]==index for r in warps(session,m)):raise ValueError("Select an existing warp")
 table=bytearray(session.data[start:start+64*12])
 empty=Portal(0,0,255,255,0,0,0,0,0).encode()
 def unused(i):
  p=Portal.read(table,i*12);return (p.x1,p.y1,p.x2,p.y2)==(0,0,255,255)
 end=next((i for i in range(index,64) if unused(i)),64)
 if end<64:empty=bytes(table[end*12:end*12+12])   # keep the map's own unused-record bytes
 table[index*12:end*12]=table[(index+1)*12:end*12]+empty
 session.replace(start,table,f"Delete warp {index}")

def move_warp(session,m,index,dx,dy):
 p=next(r[2] for r in warps(session,m) if r[0]==index)
 p=replace(p,x1=p.x1+dx,x2=p.x2+dx,y1=p.y1+dy,y2=p.y2+dy)
 set_warp(session,m,index,list(p.__dict__.values()))

TILE_WIDTH=24
TILE_HEIGHT=16
DIRECTIONS=('Down','Up','Left','Right')

def projected_warp_boxes(portal,tile_hits):
 """Match portal tile bounds to the renderer's actual floor positions."""
 return [(px,py,px+24,py+16) for px,py,x,y in tile_hits
         if portal.x1<=x<=portal.x2 and portal.y1<=y<=portal.y2]

def warp_at_visual_point(warp_boxes,x,y):
 hits=[(area,index) for area,index,boxes in warp_boxes
       if any(left<=x<right and top<=y<bottom for left,top,right,bottom in boxes)]
 return min(hits)[1] if hits else None

def area_dimensions(portal,pixels=False):
 x,y,w,h=portal.x1,portal.y1,portal.x2-portal.x1+1,portal.y2-portal.y1+1
 return (x*24,y*16,w*24,h*16) if pixels else (x,y,w,h)

def area_bounds(x,y,width,height,pixels=False):
 values=(x,y,width,height)
 if any(type(v) is not int for v in values):raise ValueError('Warp dimensions must be whole numbers')
 if pixels:
  if x%24 or width%24 or y%16 or height%16:
   raise ValueError('Native warps use whole tiles: pixel X/width must be multiples of24, Y/height of16')
  x,y,width,height=x//24,y//16,width//24,height//16
 if width<1 or height<1 or x<0 or y<0 or x+width>256 or y+height>256:
  raise ValueError('Warp must have a positive size and fit the native0–255 tile coordinates')
 return x,y,x+width-1,y+height-1

def ask_door_directions(parent,here,there,way_back=True):
 """New warp: which way each door is walked through (the game only uses a
 door when the player walks into it facing that way). Starts on the guess.
 Returns (here, there) or None when cancelled."""
 win=tk.Toplevel(parent);win.title('New Warp: Door Direction');win.transient(parent);win.resizable(False,False)
 body=ttk.Frame(win,padding=12);body.pack(fill='x')
 choices=[tk.StringVar(value=DIRECTIONS[here]),tk.StringVar(value=DIRECTIONS[there])]
 rows=[('Walk into this door facing',choices[0])]+([('Walk into the way back facing',choices[1])] if way_back else [])
 for row,(label,var) in enumerate(rows):
  ttk.Label(body,text=label).grid(row=row,column=0,sticky='w',padx=(0,8),pady=4)
  ttk.Combobox(body,textvariable=var,values=DIRECTIONS,state='readonly',width=10).grid(row=row,column=1,sticky='w')
 kind=tk.StringVar(value='return' if way_back else 'single')   # Single warp / Return warp (user 2026-10-25)
 kinds=ttk.Frame(body);kinds.grid(row=len(rows),column=0,columnspan=2,sticky='w',pady=(8,0))
 ttk.Radiobutton(kinds,text='Single warp',value='single',variable=kind).pack(side='left')
 r=ttk.Radiobutton(kinds,text='Return warp',value='return',variable=kind);r.pack(side='left',padx=(12,0))
 if not way_back:r.state(['disabled'])
 answer={'value':None}
 def ok():answer['value']=tuple(DIRECTIONS.index(v.get()) for v in choices)+(kind.get()=='return',);win.destroy()
 buttons=ttk.Frame(win,padding=(12,0,12,12));buttons.pack(fill='x')
 create=ttk.Button(buttons,text='Create Warp',command=ok);create.pack(side='left')
 ttk.Button(buttons,text='Cancel',command=win.destroy).pack(side='right')
 win.bind('<Return>',lambda e:ok());win.bind('<Escape>',lambda e:win.destroy())
 create.focus_set();win.grab_set();parent.wait_window(win)
 return answer['value']

class DestinationPicker:
 def __init__(self,owner):
  from area_map import MapRenderer,grid
  from PIL import ImageTk
  self.owner=owner;self.map=map_number(owner.fields[4].get())
  if not 0<=self.map<2547:raise ValueError('Destination map must be0–2546')
  self.width,self.height,self.cells=grid(owner.session,self.map)
  self.window=tk.Toplevel(owner.window);self.window.title('Pick destination — '+map_label(self.map));self.window.geometry('900x680')
  self.window.transient(owner.window)
  header=ttk.Frame(self.window,padding=8);header.pack(fill='x')
  self.point=[int(owner.fields[i].get(),0) for i in (5,6,7)]
  self.label=tk.StringVar();ttk.Label(header,textvariable=self.label).pack(side='left')
  ttk.Label(header,text='Landing height follows the selected tile').pack(side='right')
  body=ttk.Frame(self.window);body.pack(fill='both',expand=True)
  self.canvas=tk.Canvas(body,background='#202630',highlightthickness=0)
  sx=ttk.Scrollbar(body,orient='horizontal',command=self.canvas.xview);sy=ttk.Scrollbar(body,command=self.canvas.yview)
  self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
  body.rowconfigure(0,weight=1);body.columnconfigure(0,weight=1)
  self.canvas.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
  self.renderer=MapRenderer(owner.session,self.map)
  image,_,self.margin=self.renderer.render(elevation=True)
  self.photo=ImageTk.PhotoImage(image,master=self.canvas);self.canvas.create_image(0,0,image=self.photo,anchor='nw')
  self.canvas.configure(scrollregion=(0,0,image.width,image.height))
  for index,_,p in warps(owner.session,self.map):
   for y in range(p.y1,min(p.y2+1,self.height)):
    for x in range(p.x1,min(p.x2+1,self.width)):
     px,py=self.tile_position(x,y)
     self.canvas.create_rectangle(px,py,px+24,py+16,outline='#bf91ff',width=1)
   if p.x1<self.width and p.y1<self.height:
    px,py=self.tile_position(p.x1,p.y1)
    self.canvas.create_text(px+2,py+2,text=f'W{index}',anchor='nw',fill='#d1b0ff')
  self.canvas.bind('<Button-1>',self.pick)
  footer=ttk.Frame(self.window,padding=8);footer.pack(fill='x')
  ttk.Label(footer,text='Click a landing tile. Purple boxes show existing destination warps.').pack(side='left')
  ttk.Button(footer,text='Use point',command=lambda:owner.editor.guard(self.confirm)).pack(side='right')
  ttk.Button(footer,text='Cancel',command=self.window.destroy).pack(side='right',padx=6)
  self.mark()
  self.canvas.xview_moveto(max(0,(self.point[0]*24-350)/image.width))
  _,py=self.tile_position(*self.point[:2])
  self.canvas.yview_moveto(max(0,(py-240)/image.height))
 def tile_position(self,x,y):
  height=self.cells[y*self.width+x]['values'][3] if 0<=x<self.width and 0<=y<self.height else 0
  return x*24,y*16+self.margin-height*16
 def mark(self):
  x,y,z=self.point;self.label.set(f'Current destination: tile {x}, {y} · height {z}')
  self.canvas.delete('landing')
  px,py=self.tile_position(x,y)
  self.canvas.create_rectangle(px,py,px+24,py+16,outline='#62cbff',width=3,tags='landing')
  self.canvas.create_text(px+12,py+8,text='X',fill='white',tags='landing')
 def pick(self,event):
  hit=self.renderer.surface_at(self.canvas.canvasx(event.x),self.canvas.canvasy(event.y))
  if hit is None:return
  x,y=hit[2:4]
  if not 0<=x<self.width or not 0<=y<self.height:return
  self.point[:]=[x,y,self.cells[y*self.width+x]['values'][3]]
  self.mark()
 def confirm(self):
  if self.owner.editor.session is not self.owner.session:raise ValueError('The game data changed; reopen the warp')
  for index,value in zip((5,6,7),self.point):self.owner.fields[index].set(str(value))
  self.owner.update_destination();self.window.destroy()

class WarpWindow:
 def __init__(self,editor,index):
  self.editor=editor;self.session=editor.session;self.map=editor.current_map;self.index=index
  p=next(r[2] for r in warps(self.session,self.map) if r[0]==index)
  self.window=tk.Toplevel(editor.root);self.window.title(f'Warp {index}');self.window.geometry('650x570')
  self.fields=[tk.StringVar(value=map_label(value) if i==4 else str(value)) for i,value in enumerate(p.__dict__.values())]
  area=ttk.LabelFrame(self.window,text='Warp area',padding=8);area.pack(fill='x',padx=12,pady=8)
  self.dimensions=[tk.StringVar(value=str(v)) for v in area_dimensions(p)]
  self.area_labels=[]
  for i,label in enumerate(('X (tile)','Y (tile)','Width (tiles)','Height (tiles)')):
   widget=ttk.Label(area,text=label);widget.grid(row=i//2,column=(i%2)*2,sticky='w',padx=4,pady=5);self.area_labels.append(widget)
   ttk.Entry(area,textvariable=self.dimensions[i],width=12).grid(row=i//2,column=(i%2)*2+1,padx=4)
  dest=ttk.LabelFrame(self.window,text='Destination',padding=8);dest.pack(fill='x',padx=12,pady=8)
  for i,label in enumerate(('Destination map','Arrival X (tile)','Arrival Y (tile)','Arrival height (raw)','Flags (raw)'),4):
   ttk.Label(dest,text=label).grid(row=i-4,column=0,padx=4,pady=5,sticky='w')
   if i==4:
    from location_picker import location_ids
    mode=editor.database.document.get('mod_options',{}).get('open_world',False)
    from map_slots import map_count
    maps=location_ids(mode)+list(range(483,map_count(self.session.data)))  # plus the mod's new maps
    ttk.Combobox(dest,textvariable=self.fields[i],values=[map_label(n) for n in maps],width=42).grid(row=i-4,column=1)
   else:ttk.Entry(dest,textvariable=self.fields[i],width=18).grid(row=i-4,column=1,sticky='w')
  self.destination=tk.StringVar()
  ttk.Label(dest,textvariable=self.destination,wraplength=560).grid(row=5,column=0,columnspan=2,sticky='w',pady=6)
  ttk.Button(dest,text='Pick destination point…',command=lambda:editor.guard(lambda:DestinationPicker(self))).grid(row=6,column=0,columnspan=2,sticky='w')
  for i in (4,5,6,7):self.fields[i].trace_add('write',lambda *_:self.update_destination())
  directions=ttk.Frame(self.window,padding=(12,0));directions.pack(fill='x')
  self.entry_direction=tk.StringVar(value=DIRECTIONS[(p.flags>>14)&3])
  ttk.Label(directions,text='Entry direction').pack(side='left')
  ttk.Combobox(directions,textvariable=self.entry_direction,values=DIRECTIONS,state='readonly',width=12).pack(side='left',padx=8)
  # Arrive facing (user 2026-10-26): Auto faces the opposite of the entry direction
  _entry=(p.flags>>14)&3;_arrive=(p.flags>>12)&3
  # one-way warps have no Auto: they arrive facing the way he walked in unless changed (user 2026-10-26)
  self.has_back=has_way_back(self.session,self.map,p)
  self.arrive_direction=tk.StringVar(value='Auto' if self.has_back and _arrive==auto_arrive(self.session,self.map,p) else DIRECTIONS[_arrive])
  ttk.Label(directions,text='Arrive facing').pack(side='left',padx=(16,0))
  ttk.Combobox(directions,textvariable=self.arrive_direction,values=(('Auto',) if self.has_back else ())+DIRECTIONS,state='readonly',width=12).pack(side='left',padx=8)
  self.fields[8].trace_add('write',lambda *_:self.update_entry_direction())
  self.update_destination()
  # Every change is saved to the warp as you make it (a moment after you stop typing).
  self.apply_job=None
  for var in list(self.fields)+list(self.dimensions)+[self.entry_direction]:
   var.trace_add('write',lambda *_:self.schedule_apply())
  self.arrive_direction.trace_add('write',lambda *_:self.schedule_apply())
  ttk.Button(self.window,text='Done',command=self.close).pack(pady=8)
  self.window.protocol('WM_DELETE_WINDOW',self.close)
 def schedule_apply(self):
  if self.apply_job is not None:
   try:self.window.after_cancel(self.apply_job)
   except tk.TclError:pass
  try:self.apply_job=self.window.after(500,self.auto_apply)
  except tk.TclError:self.apply_job=None
 def auto_apply(self):
  self.apply_job=None
  try:self.apply()
  except (ValueError,IndexError):pass   # half-typed values: saved once they are valid
 def close(self):
  if self.apply_job is not None:
   try:self.window.after_cancel(self.apply_job)
   except tk.TclError:pass
   self.apply_job=None
  try:self.apply()
  except (ValueError,IndexError) as exc:self.editor.status.set(f'Warp not saved: {exc}')
  self.window.destroy()
 def update_destination(self):
  try:self.destination.set(f"{map_label(map_number(self.fields[4].get()))} · landing tile {int(self.fields[5].get(),0)}, {int(self.fields[6].get(),0)} · height {int(self.fields[7].get(),0)}")
  except ValueError:self.destination.set('Enter a valid destination map and point')
 def apply(self):
  if self.editor.session is not self.session:raise ValueError('Reopen warp after changing data')
  bounds=area_bounds(*(int(v.get(),0) for v in self.dimensions))
  values=list(bounds)+[map_number(v.get()) if i==4 else int(v.get(),0) for i,v in enumerate(self.fields) if i>=4]
  entry=DIRECTIONS.index(self.entry_direction.get());a=self.arrive_direction.get()
  arrive=auto_arrive(self.session,self.map,Portal(*values)) if a=='Auto' else DIRECTIONS.index(a)
  values[8]=(values[8]&0x0FFF)|(entry<<14)|(arrive<<12)
  current=next((r[2] for r in warps(self.session,self.map) if r[0]==self.index),None)
  if current is not None and list(current.__dict__.values())==values:return   # nothing changed
  set_warp(self.session,self.map,self.index,values)
  self.editor.dirty=True
  if self.editor.current_map==self.map:self.editor.area.draw_records()
  self.editor.status.set('Warp saved.')
 def update_entry_direction(self):
  try:self.entry_direction.set(DIRECTIONS[(int(self.fields[8].get(),0)>>14)&3])
  except (ValueError,IndexError):pass
