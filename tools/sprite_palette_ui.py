"""Shared sprite palette window. Does not clone enemy types or change stats."""
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk,Image
from sprite_palette import palettes,recolor,apply_palette,affected_sprites,PalettePreview

class SpritePaletteWindow:
 def __init__(self,editor):
  self.editor=editor;self.session=editor.session;self.map=editor.current_map
  self.window=tk.Toplevel(editor.root);self.window.title('Shared character / enemy colours');self.window.geometry('880x640')
  self.rows=palettes(self.session,self.map);self.photos=[]
  ttk.Label(self.window,text='Shared character / enemy colours',font=('Segoe UI',16,'bold'),padding=10).pack(anchor='w')
  bar=ttk.Frame(self.window,padding=10);bar.pack(fill='x')
  self.index=tk.StringVar(value='0');self.source=tk.StringVar(value='Blue');self.target=tk.StringVar(value='Red')
  for label,var,values in [('Palette',self.index,[str(r[0]) for r in self.rows]),('Change dominant',self.source,['Red','Green','Blue']),('to',self.target,['Red','Green','Blue'])]:
   ttk.Label(bar,text=label).pack(side='left',padx=4)
   combo=ttk.Combobox(bar,textvariable=var,values=values,state='readonly',width=10);combo.pack(side='left');combo.bind('<<ComboboxSelected>>',lambda _:editor.guard(self.preview))
  ttk.Button(bar,text='Apply shared colours',command=lambda:editor.guard(self.apply)).pack(side='right')
  self.swatches=tk.Canvas(self.window,height=60,background='#20252d',highlightthickness=0);self.swatches.pack(fill='x',padx=10)
  frame=ttk.Frame(self.window);frame.pack(fill='both',expand=True,padx=10)
  self.canvas=tk.Canvas(frame,background='#20252d',highlightthickness=0);self.canvas.pack(side='left',fill='both',expand=True)
  scroll=ttk.Scrollbar(frame,orient='vertical',command=self.canvas.yview);scroll.pack(side='right',fill='y');self.canvas.configure(yscrollcommand=scroll.set)
  self.message=tk.StringVar();ttk.Label(self.window,textvariable=self.message,padding=10,wraplength=840).pack(fill='x')
  self.preview()
 def current(self):
  if self.editor.session is not self.session:raise ValueError('Reopen colours after changing game data')
  index=int(self.index.get());row=palettes(self.session,self.map)[index]
  return index,row,recolor(row[2],self.source.get(),self.target.get())
 def preview(self):
  if not self.rows:self.message.set('No map-local sprite palettes found.');return
  self.canvas.delete('all');self.swatches.delete('all');self.photos=[]
  if self.source.get()==self.target.get():self.message.set('Choose different source and target colours.');return
  index,row,new=self.current()
  for line,words in enumerate((row[2],new)):
   self.swatches.create_text(5,line*28+14,text='Before' if line==0 else 'After',fill='white',anchor='w')
   for i,w in enumerate(words):
    color='#%02x%02x%02x'%((w&31)*255//31,((w>>5)&31)*255//31,((w>>10)&31)*255//31)
    self.swatches.create_rectangle(65+i*35,line*28+3,98+i*35,line*28+26,fill=color,outline='#555b65')
  affected,raw=affected_sprites(self.session,self.map,index)
  after=PalettePreview(self.session,self.map,{row[1]:new});after.raw=raw
  y=10
  for entity,key,before in affected:
   changed=after.frame(*key)
   if not changed:continue
   self.canvas.create_text(10,y+10,text=f'Event {entity} / sprite {key[0]}',fill='white',anchor='w')
   height=max(before[0].height,changed[0].height)*2
   for x,frame in ((220,before),(460,changed)):
    image=frame[0].resize((frame[0].width*2,frame[0].height*2),Image.Resampling.NEAREST)
    photo=ImageTk.PhotoImage(image,master=self.window);self.photos.append(photo)
    self.canvas.create_image(x,y,image=photo,anchor='nw')
   y+=max(height+15,65)
  self.canvas.configure(scrollregion=(0,0,800,max(y,300)))
  count=sum(a!=b for a,b in zip(row[2],new))
  self.message.set(f'{count} palette colours change; {len(affected)} map entities use it in their preview frame. Other animation frames may also share it. Left: before; right: after. Originals keep their colours until you apply.')
 def apply(self):
  index,row,new=self.current();apply_palette(self.session,self.map,index,new)
  if self.editor.current_map==self.map:self.editor.area.refresh()
  self.preview();self.message.set('Shared colours applied. Undo in the main editor reverses this edit. Save mod or Build game to export.')
