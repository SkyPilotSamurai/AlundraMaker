"""Visual existing-frame collision editor; no synthetic attack classification."""
import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace
import struct
from PIL import Image,ImageTk
from frame_collision import frame_hitboxes,sprite_context,edit_collision,FrameHitbox
from entity_preview import EntityPreview
from map_names import map_label

class FrameCollisionWindow:
    def __init__(self,editor,row):
        self.editor=editor;self.session=editor.session;self.row=row
        self.index=row.get('source',{}).get('catalogue_index')
        if self.index is None:raise ValueError('Choose a class linked to a native sprite first')
        maps=row.get('source',{}).get('observed_maps',[]) or [editor.current_map]
        self.map_id=editor.current_map if editor.current_map in maps else maps[0]
        self.window=tk.Toplevel(editor.db_window);self.window.title(row['name']+' — Hit boxes')
        self.window.geometry('1080x740+25+0')
        top=ttk.Frame(self.window,padding=(10,0));top.pack(fill='x')
        ttk.Label(top,text='Source graphic').pack(side='left')
        self.map_choices={f'{map_label(m)} ({m})':m for m in maps}
        self.map_var=tk.StringVar(value=next(k for k,v in self.map_choices.items() if v==self.map_id))
        combo=ttk.Combobox(top,textvariable=self.map_var,values=list(self.map_choices),state='readonly',width=50);combo.pack(side='left',padx=5)
        combo.bind('<<ComboboxSelected>>',lambda _:editor.guard(self.change_map))
        ttk.Label(top,text='Global bank — affects all uses' if self.index<256 else 'Local bank — edits this source map').pack(side='left',padx=8)
        body=ttk.Panedwindow(self.window,orient='horizontal');body.pack(fill='both',expand=True,padx=10,pady=10)
        left=ttk.Frame(body);body.add(left,weight=1)
        self.tree=ttk.Treeview(left,columns=('refs',),show='tree headings',height=22)
        self.tree.heading('#0',text='Frame box');self.tree.heading('refs',text='Shared frames');self.tree.column('#0',width=130);self.tree.column('refs',width=80)
        scroll=ttk.Scrollbar(left,command=self.tree.yview);scroll.pack(side='right',fill='y');self.tree.configure(yscrollcommand=scroll.set);self.tree.pack(fill='both',expand=True)
        self.tree.bind('<<TreeviewSelect>>',lambda _:editor.guard(self.select))
        right=ttk.Frame(body);body.add(right,weight=3)
        self.canvas=tk.Canvas(right,background='#171b22',height=400,highlightthickness=0);self.canvas.pack(fill='both',expand=True)
        self.fields={};settings=ttk.LabelFrame(right,text='XYZ offsets and dimensions',padding=8);settings.pack(fill='x',pady=8)
        for i,label in enumerate(('Offset X','Offset Y','Offset Z','Width X','Depth Y','Height Z')):
            var=tk.StringVar();self.fields[label]=var
            ttk.Label(settings,text=label).grid(row=i//3*2,column=i%3,sticky='w',padx=8)
            ttk.Spinbox(settings,textvariable=var,from_=-128 if i<3 else 0,to=127 if i<3 else 255,width=12,command=self.draw).grid(row=i//3*2+1,column=i%3,padx=8,pady=3)
            var.trace_add('write',lambda *_:self.draw())
        controls=ttk.Frame(right);controls.pack(fill='x')
        ttk.Button(controls,text='Apply box',command=lambda:editor.guard(self.apply)).pack(side='left',padx=4)
        ttk.Button(controls,text='Undo',command=lambda:editor.guard(self.undo)).pack(side='left',padx=4)
        self.info=tk.StringVar();ttk.Label(right,textvariable=self.info,wraplength=710).pack(fill='x',pady=5)
        self.selected=None;self.refresh()
    def change_map(self):
        self.map_id=self.map_choices[self.map_var.get()];self.refresh()
    def refresh(self,offset=None):
        self.boxes=frame_hitboxes(self.session.data,self.map_id,self.index)
        self.tree.delete(*self.tree.get_children())
        for i,box in enumerate(self.boxes):self.tree.insert('','end',iid=str(i),text=f'{i+1:04d} · {box.offset:X}',values=(len(box.references),))
        if not self.boxes:self.info.set('No referenced frame collision boxes decoded.');return
        target=next((i for i,b in enumerate(self.boxes) if b.offset==offset),0)
        self.tree.selection_set(str(target));self.select()
    def select(self):
        choices=self.tree.selection()
        if not choices:return
        self.selected=self.boxes[int(choices[0])]
        for var,value in zip(self.fields.values(),self.selected.values):var.set(str(value))
        self.info.set('Animation / direction / frame references: '+', '.join('/'.join(map(str,r)) for r in self.selected.references[:12])+(' …' if len(self.selected.references)>12 else ''))
        self.draw()
    def frame(self):
        start,end,_,_,animations=sprite_context(self.session.data,self.map_id,self.index)
        a,d,f=self.selected.references[0];frame=animations[a].streams[d].frames[f]
        if self.index<256:
            _,sheet=struct.unpack_from('<2I',self.session.data);sheet_end=struct.unpack_from('<I',self.session.data,0x14)[0]
            view=SimpleNamespace(data=self.session.data,layout=lambda _:(0,(0,0,0,start,sheet,sheet_end,0)))
        else:view=self.session
        return EntityPreview(view,self.map_id).image_set(self.index&255,frame.image_set_index)
    def draw(self):
        if self.selected is None:return
        try:values=tuple(int(v.get()) for v in self.fields.values())
        except ValueError:return
        if any(not -128<=v<=127 for v in values[:3]) or any(not 0<=v<=255 for v in values[3:]):return
        self.canvas.delete('all');w=max(self.canvas.winfo_width(),600);h=max(self.canvas.winfo_height(),340);origin=(w/2,h*.65);scale=3
        try:
            image,left,top=self.frame();photo=ImageTk.PhotoImage(image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST))
            self.canvas.create_image(origin[0]+left*scale,origin[1]+top*scale,anchor='nw',image=photo);self.canvas.image=photo
        except (ValueError,IndexError,struct.error):self.canvas.create_text(10,10,anchor='nw',text='Frame art unavailable; box remains editable',fill='#ccd7e5')
        box=FrameHitbox(self.selected.offset,*values,self.selected.raw,self.selected.references)
        points=[(origin[0]+x*scale,origin[1]+y*scale) for x,y in box.projected_corners]
        for a,b in ((0,1),(0,2),(1,3),(2,3),(4,5),(4,6),(5,7),(6,7),(0,4),(1,5),(2,6),(3,7)):
            self.canvas.create_line(*points[a],*points[b],fill='#68bcff',width=2)
        self.canvas.create_line(origin[0]-8,origin[1],origin[0]+8,origin[1],fill='#f6d777');self.canvas.create_line(origin[0],origin[1]-8,origin[0],origin[1]+8,fill='#f6d777')
    def apply(self):
        if self.selected is None:return
        offset=self.selected.offset
        if edit_collision(self.session,self.selected,[int(v.get()) for v in self.fields.values()]):self.editor.dirty=True
        self.refresh(offset);self.editor.status.set('Native frame collision edited. Save mod or Build game includes it; emulator testing required.')
    def undo(self):
        self.session.undo();self.refresh();self.editor.dirty=True
