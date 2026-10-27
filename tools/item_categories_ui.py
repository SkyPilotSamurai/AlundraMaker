"""Category-aware item panel; native use behavior is not silently invented."""
import tkinter as tk
from tkinter import ttk
from item_categories import CATEGORIES,CONSUMED_IDS,category_for,item_id,native_properties,apply


class ItemCategoryPanel:
    def __init__(self,parent,exe_provider=None):
        self.exe_provider=exe_provider;self.frame=ttk.LabelFrame(parent,text='Item category and menu properties',padding=8)
        self.category=tk.StringVar(value='Key item');self.menu_group=tk.StringVar()
        self.priority=tk.StringVar();self.maximum=tk.StringVar();self.highest=tk.BooleanVar()
        self.note=tk.StringVar();self.native_enabled=False;self.loaded=None;self.native_baseline={}
        ttk.Label(self.frame,text='Category').grid(row=0,column=0,sticky='w')
        box=ttk.Combobox(self.frame,textvariable=self.category,values=CATEGORIES,state='readonly',width=22)
        self.box=box;box.grid(row=0,column=1,sticky='ew');box.bind('<<ComboboxSelected>>',lambda _:self.update_note())
        self.widgets=[]
        def row(n,label,var):
            text=ttk.Label(self.frame,text=label);text.grid(row=n,column=0,sticky='w',pady=3)
            entry=ttk.Entry(self.frame,textvariable=var,width=12);entry.grid(row=n,column=1,sticky='w');self.widgets.append(entry)
            return text,entry
        row(1,'Menu group (0–31)',self.menu_group)
        # Selection priority only matters for L/R item swapping: shown when ticked.
        self.swap=tk.BooleanVar(value=False)
        swap=ttk.Checkbutton(self.frame,text='Swap Priority (LR Swaps)',variable=self.swap,command=self.show_swap)
        swap.grid(row=2,column=0,columnspan=2,sticky='w',pady=(3,0));self.widgets.append(swap)
        swap.grid_remove()   # hidden with its fields (user 2026-10-26); values still load and save
        self.swap_rows=list(row(3,'Selection priority',self.priority))
        flag=ttk.Checkbutton(self.frame,text='Select highest owned priority in this menu group',variable=self.highest)
        flag.grid(row=4,column=0,columnspan=2,sticky='w');self.widgets.append(flag);self.swap_rows.append(flag)
        row(5,'Maximum quantity',self.maximum)
        self.show_swap()
        # The explanatory note under these fields was removed (user request); self.note is kept for tests.
        self.frame.columnconfigure(1,weight=1)
    def exe(self):return self.exe_provider() if self.exe_provider else None
    def load(self,row):
        self.loaded=row;self.category.set(category_for(row));self.native_enabled=False;self.native_baseline={}
        for var in (self.menu_group,self.priority,self.maximum):var.set('')
        self.highest.set(False)
        exe=self.exe()
        if exe is not None and not row.get('clone_of'):
            try:
                properties=native_properties(exe,item_id(row))
                self.native_baseline={key:properties[key] for key in ('menu_group','priority','max_quantity','highest_priority')}
                properties.update(row.get('data',{}).get('item_native_properties',{}))
                self.menu_group.set(str(properties['menu_group']));self.priority.set(str(properties['priority']))
                self.maximum.set(str(properties['max_quantity']));self.highest.set(properties['highest_priority']);self.native_enabled=True
            except ValueError:pass
        for widget in self.widgets:widget.configure(state='normal' if self.native_enabled else 'disabled')
        try:self.swap.set(bool(int(self.priority.get() or 0)) or bool(self.highest.get()))
        except ValueError:self.swap.set(True)
        self.show_swap()
        self.update_note()
    def show_swap(self):
        for widget in self.swap_rows:widget.grid_remove()   # hidden (user 2026-10-26)
    def update_note(self):
        try:identity=item_id(self.loaded or {})
        except ValueError:identity=None
        category=self.category.get()
        details={'Consume':'Maximum quantity changes the pickup limit. Stock use consumption remains tied to the native item.',
            'Magic':'Spawns its magic when used.',
            'Accessory':'Menu group and priority change selection, not the accessory’s passive effect.',
            'Key item':'Menu group and quantity can change; stock story checks remain tied to the native item.'}[category]
        consumption='Stock use removes one item.' if identity in CONSUMED_IDS else 'No generic consume-on-use toggle is recovered for this type.'
        self.note.set(details+' '+consumption+' Category is editor grouping.'+
            ('' if self.native_enabled else ' Load a native executable-linked item to edit menu properties.'))
    def apply(self,row):
        fields={}
        if self.native_enabled:
            try:fields=dict(menu_group=int(self.menu_group.get(),0),priority=int(self.priority.get(),0),
                max_quantity=int(self.maximum.get(),0),highest_priority=self.highest.get())
            except ValueError:raise ValueError('Menu group, priority and quantity need whole numbers')
            fields={key:value for key,value in fields.items() if value!=self.native_baseline.get(key)}
        return apply(row,self.category.get(),exe=self.exe(),**fields)
