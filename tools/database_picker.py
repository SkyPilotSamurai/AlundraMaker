"""Responsive, scrollable native-graphic cards for map event placement."""
import math
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from database_catalogue import reference_image
from placement_catalogue import placement_rows

TABS=(("npc","NPCs"),("enemy","Enemies"),("boss","Bosses"),
      ("object","Objects"),("item","Items"),("misc","Misc"))
CARD_SIZES={'Compact':(106,114),'Normal':(132,142),'Large':(164,174)}   # Normal = the old Compact (user 2026-10-21)

def grid_geometry(width,count,card_width,card_height):
    columns=max(1,int(width)//card_width)
    return columns, max(1,math.ceil(count/columns))*card_height

def visible_cards(count,columns,top,height,card_height):
    first=max(0,int(top)//card_height)*columns
    last=min(count,(math.ceil((top+height)/card_height)+1)*columns)
    return range(first,last)

_LOADING=object()   # picture being decoded in the background

class DatabasePicker:
    def __init__(self,editor,parent,choose,kinds=None,title='Choose an event graphic / object',
                 confirm='Place selected',allow_empty=True,keep_open=False,extra_buttons=(),on_cancel=None,use_tile=None):
        self.editor=editor;self.choose=choose;self.on_cancel=on_cancel;self.chose=False;self.kinds=kinds;self.keep_open=keep_open
        self.window=tk.Toplevel(parent);self.window.title(title)
        sw,sh=parent.winfo_screenwidth(),parent.winfo_screenheight()
        width,height=round(sw*.85),round(sh*.85)
        self.window.geometry(f'{width}x{height}+{(sw-width)//2}+0')
        self.window.minsize(min(740,width),min(440,height));self.window.transient(parent)
        self.rows={};self.canvases={};self.frames={};self.selected={};self.photos={};self.images={};self.jobs={}
        self.search_job=None;self.search=tk.StringVar();self.card_size=tk.StringVar(value='Normal')   # Normal by default (user 2026-10-21)
        bar=ttk.Frame(self.window,padding=8);bar.pack(fill='x')
        ttk.Label(bar,text='Find a name or number').pack(side='left')
        ttk.Entry(bar,textvariable=self.search).pack(side='left',fill='x',expand=True,padx=8)
        ttk.Label(bar,text='Preview size').pack(side='left')
        size=ttk.Combobox(bar,textvariable=self.card_size,values=list(CARD_SIZES),state='readonly',width=10)
        size.pack(side='left',padx=6);size.bind('<<ComboboxSelected>>',lambda _:self.draw())
        self.count=tk.StringVar();ttk.Label(bar,textvariable=self.count).pack(side='left',padx=8)
        self.notebook=ttk.Notebook(self.window);self.notebook.pack(fill='both',expand=True,padx=8)
        for key,label in TABS:
            if kinds is not None and key not in kinds and not (key=='item' and any(k in kinds for k in ('item','weapon','armor'))):continue
            frame=ttk.Frame(self.notebook);self.notebook.add(frame,text=label);self.frames[str(frame)]=key
            canvas=tk.Canvas(frame,background='#171b22',highlightthickness=0,takefocus=True)
            canvas.pack(side='left',fill='both',expand=True)
            scroll=ttk.Scrollbar(frame,command=lambda *args,c=canvas,k=key:self.scroll(k,c,*args));scroll.pack(side='right',fill='y')
            canvas.configure(yscrollcommand=scroll.set);self.canvases[key]=canvas
            canvas.bind('<Configure>',lambda _,k=key:self.schedule_draw(k))
            canvas.bind('<Button-1>',lambda e,k=key:self.click(k,e))
            canvas.bind('<Double-Button-1>',lambda e,k=key:self.click(k,e,place=True))
            canvas.bind('<MouseWheel>',lambda e,k=key:self.wheel(k,e))
            for key_name,delta in [('Left',-1),('Right',1),('Up','up'),('Down','down')]:
                canvas.bind('<'+key_name+'>',lambda _,k=key,d=delta:self.navigate(k,d))
            canvas.bind('<Return>',lambda _:editor.guard(self.select))
        self.notebook.bind('<<NotebookTabChanged>>',lambda _:self.draw())
        buttons=ttk.Frame(self.window,padding=8);buttons.pack(fill='x')
        self.description=tk.StringVar();ttk.Label(buttons,textvariable=self.description).pack(side='left',fill='x',expand=True)
        # Empty event / Create Warp sit in the tab row, right of the tabs (user 2026-10-18)
        if allow_empty or extra_buttons or use_tile:
            tabrow=ttk.Frame(self.window)
            if use_tile:ttk.Button(tabrow,text='Use Tile',command=lambda:(setattr(self,'chose',True),self.window.destroy(),editor.guard(use_tile))).pack(side='left',padx=(0,6))
            if allow_empty:ttk.Button(tabrow,text='Empty Event / No Graphic',command=lambda:self.finish(None)).pack(side='left',padx=(0,6))
            for label,action in extra_buttons:
                ttk.Button(tabrow,text=label,command=lambda a=action:(setattr(self,'chose',True),self.window.destroy(),editor.guard(a))).pack(side='left',padx=(0,6))
            def beside_tabs(_=None):   # right after the last tab
                try:
                    import tkinter.font as tkfont
                    font=tkfont.Font(family='Segoe UI',size=10)
                    estimate=sum(font.measure(self.notebook.tab(t,'text'))+26 for t in self.notebook.tabs())
                    end=0;w=self.notebook.winfo_width()
                    for y in (6,10,16):
                        for x in range(0,w,4):
                            try:self.notebook.index(f'@{x},{y}');end=max(end,x)
                            except tk.TclError:pass
                    x=max(end,estimate)+10
                    if x+tabrow.winfo_reqwidth()<=w-4 or w<=1:
                        tabrow.place(in_=self.notebook,x=x,y=1,anchor='nw');tabrow.lift()
                    else:   # no room beside the tabs: keep them reachable in the bottom row
                        tabrow.place(in_=buttons,relx=1.0,x=-260,rely=0.5,anchor='e');tabrow.lift()
                except tk.TclError:pass
            self.notebook.bind('<Configure>',beside_tabs,add='+')
            beside_tabs();self.window.after(50,beside_tabs);self.window.after(300,beside_tabs)
        ttk.Button(buttons,text=confirm,command=lambda:editor.guard(self.select)).pack(side='right')
        ttk.Button(buttons,text='Done' if keep_open else 'Cancel',command=self.close).pack(side='right',padx=8)
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.search.trace_add('write',lambda *_:self.schedule_search())
        self.refresh()

    def category(self):return self.frames.get(self.notebook.select())

    def schedule_search(self):
        if self.search_job is not None:self.window.after_cancel(self.search_job)
        self.search_job=self.window.after(120,self.refresh)

    def refresh(self):
        self.search_job=None;query=self.search.get().strip().casefold()
        for category in self.canvases:
            rows=[r for r in placement_rows(self.editor.database,category) if query in (r['name']+' '+r['id']).casefold()]
            self.rows[category]=rows
            if self.selected.get(category) not in {r['id'] for r in rows}:
                self.selected[category]=rows[0]['id'] if rows else None
            self.canvases[category].yview_moveto(0)
        self.draw()

    def schedule_draw(self,category):
        if category in self.jobs:self.window.after_cancel(self.jobs[category])
        self.jobs[category]=self.window.after(40,lambda:self.draw(category))

    def draw(self,category=None):
        category=category or self.category()
        if category not in self.canvases:return
        self.jobs.pop(category,None)
        if category!=self.category():return
        canvas=self.canvases[category];rows=self.rows.get(category,[])
        cw,ch=CARD_SIZES[self.card_size.get()];width=max(1,canvas.winfo_width());height=max(1,canvas.winfo_height())
        columns,total=grid_geometry(width,len(rows),cw,ch)
        canvas.configure(scrollregion=(0,0,width,total));top=max(0,canvas.canvasy(0));canvas.delete('all')
        for i in visible_cards(len(rows),columns,top,height,ch):
            row=rows[i];x=(i%columns)*cw;y=(i//columns)*ch;selected=row['id']==self.selected.get(category)
            canvas.create_rectangle(x+5,y+5,x+cw-5,y+ch-5,fill='#344c68' if selected else '#242c38',outline='#b8d8ff' if selected else '#3b4655',width=2 if selected else 1)
            image_key=(id(self.editor.session),row['id'])
            if image_key not in self.images and hasattr(self.editor,'db_background'):   # decoded off the Tk thread (user 2026-10-27)
                self.images[image_key]=_LOADING;session=self.editor.session
                def store(image,key=image_key,category=category):
                    self.images[key]=image
                    if self.window.winfo_exists():self.schedule_draw(category)
                self.editor.db_background(lambda r=row,s=session:reference_image(s,r),store)
            elif image_key not in self.images:self.images[image_key]=reference_image(self.editor.session,row)
            image=self.images[image_key]
            if image is _LOADING:
                canvas.create_text(x+cw/2,y+(ch-55)/2,text='…',fill='#8c99ab');image=None;loading=True
            else:loading=False
            if image is not None:
                limit=(cw-20,ch-64);scale=min(4,limit[0]/image.width,limit[1]/image.height)
                dimensions=(max(1,round(image.width*scale)),max(1,round(image.height*scale)))
                cache_key=(row['id'],id(image),dimensions)
                if cache_key not in self.photos:
                    self.photos[cache_key]=ImageTk.PhotoImage(image.resize(dimensions,Image.Resampling.NEAREST))
                canvas.create_image(x+cw/2,y+ch-57,image=self.photos[cache_key],anchor='s')
            elif not loading:
                canvas.create_text(x+cw/2,y+(ch-55)/2,text='No graphic',fill='#8c99ab')
            canvas.create_text(x+cw/2,y+ch-48,text=row['name'],width=cw-18,anchor='n',fill='#edf2fa',font=('Segoe UI',10))
            canvas.create_text(x+cw/2,y+15,text=row['id'].split(':')[-1],fill='#aebed1',font=('Segoe UI',8))
        self.count.set(f'{len(rows)} entries')
        row=next((r for r in rows if r['id']==self.selected.get(category)),None)
        self.description.set(row['name'] if row else 'No matching entries')

    def scroll(self,category,canvas,*args):
        canvas.yview(*args);self.schedule_draw(category)

    def wheel(self,category,event):
        self.canvases[category].yview_scroll(-int(event.delta/120),'units');self.schedule_draw(category)
        return 'break'

    def click(self,category,event,place=False):
        canvas=self.canvases[category];canvas.focus_set();cw,ch=CARD_SIZES[self.card_size.get()]
        columns,_=grid_geometry(canvas.winfo_width(),len(self.rows[category]),cw,ch)
        col=int(event.x)//cw
        if col>=columns:return
        index=int(canvas.canvasy(event.y))//ch*columns+col
        if 0<=index<len(self.rows[category]):
            self.selected[category]=self.rows[category][index]['id'];self.draw(category)
            if place:self.editor.guard(self.select)

    def navigate(self,category,delta):
        rows=self.rows[category]
        if not rows:return 'break'
        canvas=self.canvases[category];cw,ch=CARD_SIZES[self.card_size.get()]
        columns,total=grid_geometry(canvas.winfo_width(),len(rows),cw,ch)
        index=next((i for i,r in enumerate(rows) if r['id']==self.selected.get(category)),0)
        delta=-columns if delta=='up' else columns if delta=='down' else delta
        index=max(0,min(len(rows)-1,index+delta));self.selected[category]=rows[index]['id']
        y=index//columns*ch;top=canvas.canvasy(0)
        if y<top:canvas.yview_moveto(y/total)
        elif y+ch>top+canvas.winfo_height():canvas.yview_moveto(max(0,y+ch-canvas.winfo_height())/total)
        self.draw(category);return 'break'

    def select(self):
        chosen=self.selected.get(self.category())
        if not chosen:return
        if getattr(self,'keep_open',False):
            # Multi-add pickers stay open; double-click or the button adds each card.
            self.chose=True;self.choose(chosen)
            name=next((r['name'] for r in self.rows.get(self.category(),[]) if r['id']==chosen),chosen)
            self.description.set(f'Added {name}')
        else:self.finish(chosen)

    def close(self):
        for job in list(self.jobs.values())+[self.search_job]:
            if job is not None:self.window.after_cancel(job)
        self.window.destroy()
        if not self.chose and self.on_cancel is not None:   # cancelled without choosing
            callback,self.on_cancel=self.on_cancel,None;self.editor.guard(callback)

    def finish(self,class_id):self.chose=True;self.choose(class_id);self.close()
