"""Existing game events in the actual custom-event editor, with lossless editing."""
import struct
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk
from event_graph_ui import EventGraphWindow,command_template
from native_event_view import event_hooks,event_graphic
from native_event_presentation import present,operand_choices,parse_operand,BRANCHES
from native_event_commands import command_form,apply_form,encode_insert,replace_in_place,delete_command
from event_editor import reachable_instructions as instructions,EDITABLE,edit_instruction
from map_inspector import inspect_map


class NativeEventGraphWindow(EventGraphWindow):
    def __init__(self,editor,kind,index):
        self.session=editor.session;self.native_map=editor.current_map
        self.kind=kind;self.index=index
        self.info=inspect_map(self.session.data,self.native_map)
        super().__init__(editor)
        self.db=editor.database
        import native_flag_index;native_flag_index.set_document(editor.database.document)
        # Existing hooks have native scheduling semantics, not arbitrary RPG
        # trigger changes. Keep the selector visible but prevent silent edits.
        for widget in self.window.winfo_children():
            self._configure_native_controls(widget)
        self.default_route_mode.set('Existing game behaviour')
        self.default_route_combo.configure(values=['Existing game behaviour'],state='disabled')
        self.default_route_button.configure(state='disabled')
        self.default_route_speed.set('Native')
        self.default_speed_spin.configure(state='disabled');self.default_repeat_button.configure(state='disabled')
        self.window.title('Alundra Event Editor — existing game event')
        self.events.selection_set(f'{kind}:{index}');self.load_selected()

    def _configure_native_controls(self,parent):
        for child in parent.winfo_children():
            if isinstance(child,ttk.Combobox) and str(child.cget('textvariable'))==str(self.page_trigger):child.configure(state='disabled')
            if isinstance(child,ttk.Checkbutton) and str(child.cget('variable'))==str(self.conditional_presence):child.pack_forget()
            self._configure_native_controls(child)

    def refresh_list(self,select=None):
        self.info=inspect_map(self.session.data,self.native_map)
        self.events.delete(*self.events.get_children())
        from event_deletion import record_deleted
        for kind in ('entities','events'):
            for i,row in enumerate(self.info[kind]):
                if record_deleted(self.editor.database.document,self.native_map,kind,i):continue
                a,b,c,d=row['rectangle']
                self.events.insert('','end',iid=f'{kind}:{i}',text=f'{"Actor" if kind=="entities" else "Event"} {i}',values=(self.native_map,'Game event',f'{a},{b} {c-a+1}×{d-b+1}'))

    def load_selected(self):
        selected=self.events.selection()
        if not selected:return
        if self.working:self._commit_form()
        self.kind,raw=selected[0].split(':');self.index=int(raw)
        record=self.info[self.kind][self.index];a,b,c,d=record['rectangle']
        if self.kind=='entities':
            px,py,pz=record['position_raw'];a,b,c,d=px//2,py//2,px//2,py//2
        hooks=event_hooks(self.session,self.native_map,self.kind,self.index,self.info)
        name=self.editor.database.document.get('native_event_names',{}).get(f'{self.native_map}:{self.kind}:{self.index}',f'Game {"actor" if self.kind=="entities" else "event"} {self.index}')
        self.working={'id':selected[0],'name':name,
                      'map_id':self.native_map,'region':[a,b,c-a+1,d-b+1],
                      'pages':[dict(id=f'page:{i+1:04d}',name=h['label'],native_key=h['key'],bank=h['bank']) for i,h in enumerate(hooks)]}
        self.name.set(self.working['name']);self.map_id.set(str(self.native_map))
        for var,value in zip((self.x,self.y,self.w,self.h),self.working['region']):var.set(str(value))
        if self.kind=='entities':
            offset=int(record['offset'],16);self.default_facing.set(('down','up','left','right')[self.session.data[offset+5]&3])
            self.facing_combo.configure(state='readonly')
        else:self.facing_combo.configure(state='disabled')
        self.page_id=next((p['id'] for p in self.working['pages'] if p['bank']=='F' and p['native_key']),self.working['pages'][0]['id'])
        self.refresh_pages();self.status.set('Existing game event. Double-click Contents to edit; original unknown commands stay intact.')

    def load_page(self):
        if not self.working:return
        self.page_id=self.page_names.get(self.page.get(),self.page_id)
        page=self.current_page()
        self.page_trigger.set(page['name'])
        self.placement_class.set('Existing game graphic')
        self.conditions_label.set('Original conditions and branches are shown in Contents.')
        self.show_page_graphic();self.refresh_commands()

    def show_page_graphic(self):
        if not self.working:return
        image,basis,entity=event_graphic(self.session,self.native_map,self.kind,self.index)
        canvas=self.page_graphic;canvas.delete('all')
        if image is not None:
            canvas.image=ImageTk.PhotoImage(image,master=self.window);canvas.create_image(110,70,image=canvas.image)
        else:canvas.create_text(110,70,text='E',fill='#ffe0a5',font=('Segoe UI',28,'bold'))
        canvas.create_text(110,135,text=basis,fill='#d8e2ee')

    def refresh_commands(self,select=None):
        self.commands.delete(*self.commands.get_children())
        page=self.current_page();key=page['native_key'] if page else None
        self.rows=instructions(self.session,self.native_map,key) if key else []
        self.lines={p:i+1 for i,(p,op,n) in enumerate(self.rows)}
        if not key:self.commands.insert('','end',iid='unknown',values=('Unknown event','Shared/default native behavior — preserved'))
        for p,op,n in self.rows:
            shown=present(self.session,self.native_map,p,op,n,self.lines)
            self.commands.insert('','end',iid=str(p),values=(shown['action'],shown['settings']))
        if key:self.commands.insert('','end',iid='new',values=('◇','Add command…'))
        if select is not None and self.commands.exists(str(select)):self.commands.selection_set(str(select))
        self.place_flag_buttons()

    FLAG_OPS=(0x05,0x06,0x32,0x30,0x31,0x35,0x36,0x7B,0x7C,0x80,0x81)

    def place_flag_buttons(self,_=None):
        """A 'Jump to events' button at the right end of the Settings cell of every
        visible flag command; it lists every event that uses that flag."""
        tree=self.commands
        for b in getattr(self,'flag_buttons',[]):b.destroy()
        self.flag_buttons=[]
        if not getattr(self,'_flag_binds',False):
            self._flag_binds=True
            for ev in ('<Configure>','<MouseWheel>','<ButtonRelease-1>','<KeyRelease>'):
                tree.bind(ev,lambda e:tree.after(15,self.place_flag_buttons),add='+')
            for w in tree.master.winfo_children():
                if isinstance(w,ttk.Scrollbar):
                    for ev in ('<B1-Motion>','<ButtonRelease-1>','<MouseWheel>'):w.bind(ev,lambda e:tree.after(15,self.place_flag_buttons),add='+')
        cols=tree['columns'];col=cols[-1] if cols else '#1'
        for p,op,n in getattr(self,'rows',[]):
            if op not in self.FLAG_OPS or not tree.exists(str(p)):continue
            box=tree.bbox(str(p),col)
            if not box:continue
            x,y,w,h=box
            flag=struct.unpack_from('<H',self.session.data,p+1)[0]
            def go(f=flag):
                from native_flag_index import show_uses
                show_uses(self.editor,self.window,f)
            # Sized to its label (font and row height vary), with no extra padding,
            # so the text is never clipped.
            if not getattr(self,'_jump_style',None):
                import tkinter.font as tkfont
                style=ttk.Style(tree);style.configure('Jump.TButton',padding=(4,0))
                f=tkfont.nametofont(style.lookup('TButton','font') or 'TkDefaultFont')
                self._jump_style=(f.measure('Jump to events')+16,f.metrics('linespace')+4)
            bw,bh=self._jump_style;bh=max(h,bh)
            b=ttk.Button(tree,text='Jump to events',style='Jump.TButton',command=lambda g=go:self.editor.guard(g))
            b.place(x=x+w-bw-2,y=y+(h-bh)//2,width=bw,height=bh);self.flag_buttons.append(b)

    def load_command(self):pass
    def _commit_command(self):pass
    def _commit_current_page(self):pass
    def _commit_selected(self):self._commit_form() if self.working else None

    def _commit_form(self):
        if self.session is not self.editor.session:raise ValueError('Reopen the event after changing game data.')
        if int(self.map_id.get())!=self.native_map:raise ValueError('Use a warp command to change maps; this event belongs to its original map.')
        if not self.working:return
        if self.kind=='entities':
            offset=int(self.info[self.kind][self.index]['offset'],16)
            direction=('down','up','left','right').index(self.default_facing.get())
            old_direction=self.session.data[offset+5];new_direction=(old_direction&0xFC)|direction
            if old_direction!=new_direction:
                self.session.replace(offset+5,bytes([new_direction]),'Change default facing');self.editor.dirty=True
        name=self.name.get().strip()
        if name!=self.working['name']:
            self.editor.database.document.setdefault('native_event_names',{})[f'{self.native_map}:{self.kind}:{self.index}']=name
            self.working['name']=name;self.editor.dirty=True
        wanted=[int(v.get(),0) for v in (self.x,self.y,self.w,self.h)]
        old=self.working['region']
        if wanted!=old:
            x,y,w,h=wanted
            if min(x,y)<0 or min(w,h)<1 or x+w>256 or y+h>256:raise ValueError('Event region must fit native map coordinates.')
            record=self.info[self.kind][self.index];offset=int(record['offset'],16)
            values=list(struct.unpack_from('<16B2H' if self.kind=='entities' else '<8B',self.session.data,offset))
            if self.kind=='entities':
                if (w,h)!=(1,1):raise ValueError('Actor interaction size belongs to its native collision; use a separate region event for a wider trigger.')
                values[7]+=(x-old[0])*2;values[8]+=(y-old[1])*2
            else:values[:4]=[x,y,x+w-1,y+h-1]
            self.session.edit_record(self.native_map,self.kind,self.index,values)
            self.working['region']=wanted;self.info=inspect_map(self.session.data,self.native_map)
            self.editor.dirty=True

    def open_command_form(self,kind=None,index=None):
        from event_command_dialog import CommandDialog,Fields
        if kind is not None:
            if kind=='face_actor' and self.kind!='entities':raise ValueError('Facing needs an actor; select a character or object event.')
            row=command_template(kind)
            if kind=='set_switch':row.pop('switch_scope',None);row['native_flag_operand']=row['switch_id']
            def insert(value):
                selected=self.commands.selection()
                offset=int(selected[0]) if selected and selected[0] not in ('new','unknown') else next((p for p,op,n in self.rows if op==1),None)
                if offset is None:raise ValueError('Delete a known command to free an insertion slot first.')
                replace_in_place(self.session,self.native_map,self.current_page()['native_key'],offset,encode_insert(value))
                self.changed(offset)
            return CommandDialog(self.editor,self.window,row,insert,database=self.editor.database)
        if index in ('unknown','new',None):return
        offset=int(index);opcode=self.session.data[offset];key=self.current_page()['native_key']
        row=command_form(self.session,self.native_map,offset,opcode)
        if row is not None:
            def save(value):apply_form(self.session,self.native_map,key,offset,value);self.changed(offset)
            return CommandDialog(self.editor,self.window,row,save,database=self.editor.database)
        shown=present(self.session,self.native_map,offset,opcode,next(n for p,op,n in self.rows if p==offset),self.lines)
        win=tk.Toplevel(self.window);win.title(shown['action']);frame=ttk.Frame(win,padding=12);frame.pack(fill='both',expand=True)
        if opcode not in EDITABLE:
            ttk.Label(frame,text=shown['settings'] or 'Original bytes preserved.',wraplength=650).pack()
            ttk.Button(frame,text='Done',command=win.destroy).pack(pady=8);return
        name,fmt,labels=EDITABLE[opcode];values=struct.unpack_from('<'+fmt,self.session.data,offset+1)
        fields=Fields(frame,self.editor.database)
        for i,(label,value) in enumerate(zip(labels,values)):
            choices=operand_choices(opcode,i)
            if opcode in BRANCHES and i==len(values)-1:
                choices={f'Line {line}':target-offset for target,line in self.lines.items()}
                choices.setdefault(f'Original relative target {value:+d}',value)
            if choices:choices={**choices,f'Native value {value}':value}
            fields.add(str(i),label,value,mapped_choices=choices or None)
        def save():
            parsed=fields.values();edit_instruction(self.session,self.native_map,key,offset,[parsed[str(i)] for i in range(len(values))]);self.changed(offset);win.destroy()
        ttk.Button(frame,text='OK',command=lambda:self.editor.guard(save)).grid(row=fields.n,column=1,pady=10)

    def changed(self,offset=None):
        self.editor.dirty=True;self.refresh_commands(offset)
        self.status.set('Event edit kept. Save mod or Build game includes it; Undo restores the previous data.')

    def delete_command(self):
        selected=self.commands.selection()
        if not selected or selected[0] in ('new','unknown'):return
        delete_command(self.session,self.native_map,self.current_page()['native_key'],int(selected[0]));self.changed()

    def keep_changes(self,commit_form=True):
        if commit_form:self._commit_form()
        if self.editor.area:self.editor.area.draw_records()
    def apply(self):self.keep_changes();self.status.set('Existing event edits kept.')
    def close(self):self.keep_changes();self.window.destroy()

    def open_project_state(self):
        from project_state_ui import ProjectStateWindow
        self._commit_form();ProjectStateWindow(self.editor,self.window,database=self.editor.database)

    def choose_page_class(self):
        if self.kind!='entities':raise ValueError('This map trigger is invisible. Its spawned objects are defined in Contents.')
        from database_picker import DatabasePicker
        from native_class_placement import class_preview
        def choose(cid):
            definition=self.editor.database.get(cid);catalogue=definition.get('source',{}).get('catalogue_index')
            if type(catalogue) is not int or class_preview(self.session,self.native_map,catalogue) is None:raise ValueError('Choose a graphic available in this map or the shared bank.')
            if definition.get('clone_of'):raise ValueError('A custom cloned class needs native class export; select its existing source graphic here.')
            offset=int(self.info['entities'][self.index]['offset'],16)
            raw=bytearray(self.session.data[offset:offset+20]);raw[6]=catalogue&255;raw[5]=(raw[5]&127)|(128 if catalogue>=256 else 0)
            self.session.replace(offset,raw,'Change existing event graphic');self.editor.dirty=True;self.show_page_graphic()
        DatabasePicker(self.editor,self.window,choose)

    def edit_conditions(self):raise ValueError('Edit the original conditional branches in Contents; new page conditions require a verified native page controller.')
    def add_page(self):raise ValueError('Existing event pages represent native load/update/touch/interact hooks; they are kept separately.')
    paste_page=add_page
    clear_page=add_page
    delete_page=add_page
    def move_command(self,delta):raise ValueError('Native command addresses are referenced by branches. Edit or replace freed slots without moving unknown code.')
    def copy_command(self,cut=False):raise ValueError('Copy/paste of existing native instructions requires preserving their branch references; use typed editing or Add command.')
    def paste_command(self):self.copy_command()
    def delete_event(self):
        from event_deletion import delete_record
        delete_record(self.session,self.editor.database,self.native_map,self.kind,self.index)
        self.editor.dirty=True
        if self.editor.area:self.editor.area.refresh(reload_textures=False)
        self.window.destroy()
