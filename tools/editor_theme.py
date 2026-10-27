"""Shared dark desktop theme."""
from tkinter import ttk

def apply_dark(root):
 root.configure(background="#181c24")
 root.option_add("*Background","#202632")
 root.option_add("*Foreground","#e6edf5")
 root.option_add("*Entry.insertBackground","#ffffff")
 root.option_add("*Text.insertBackground","#ffffff")
 root.option_add("*selectBackground","#375a83")
 root.option_add("*selectForeground","#ffffff")
 style=ttk.Style(root);style.theme_use("clam")
 style.configure(".",background="#202632",foreground="#e6edf5",font=("Segoe UI",10),bordercolor="#394354",lightcolor="#394354",darkcolor="#181c24")
 style.configure("TButton",padding=(10,6))
 style.map("TButton",background=[("active","#36465d")])
 style.configure("TEntry",fieldbackground="#151a22",foreground="#e6edf5",insertcolor="white")
 style.configure("TCombobox",fieldbackground="#151a22",arrowcolor="#e6edf5")
 style.map("TCombobox",fieldbackground=[("readonly","#151a22")],foreground=[("readonly","#e6edf5")])
 style.configure("TSpinbox",fieldbackground="#151a22",arrowcolor="#e6edf5")
 style.configure("Treeview",background="#151a22",fieldbackground="#151a22",foreground="#e6edf5",rowheight=27)
 style.map("Treeview",background=[("selected","#345579")],foreground=[("selected","white")])
 style.configure("Treeview.Heading",background="#293445",foreground="#dce8fa",padding=6)
 style.layout("Workspace.TNotebook",[("Notebook.client",{"sticky":"nswe"})])
 style.configure("TNotebook",tabmargins=(0,0,0,0))
 style.configure("TNotebook.Tab",padding=(12,7),expand=(0,0,0,0))
 style.map("TNotebook.Tab",background=[("selected","#345579")],foreground=[("selected","white")],padding=[("selected",(12,7)),("!selected",(12,7))],expand=[("selected",(0,0,0,0)),("!selected",(0,0,0,0))])
 style.map("TRadiobutton",background=[("active","#36465d")])

 # Override clam's pale hover/pressed/indicator defaults on every control.
 for name in ('TButton','TMenubutton','TCheckbutton','TRadiobutton','TScrollbar','Horizontal.TScrollbar','Vertical.TScrollbar','Treeview.Heading'):
  style.map(name,background=[('pressed','#293445'),('active','#2b3545'),('selected','#2d4156')],
   lightcolor=[('active','#394354'),('pressed','#394354')],bordercolor=[('focus','#526783'),('active','#394354')])
 for name in ('TCheckbutton','TRadiobutton'):
  style.map(name,indicatorbackground=[('selected','#2d4156'),('active','#293445'),('!selected','#151a22')],indicatorforeground=[('selected','#a8b6c8'),('!selected','#a8b6c8')])
 for name in ('TEntry','TCombobox','TSpinbox'):
  style.map(name,fieldbackground=[('disabled','#202632'),('readonly','#151a22'),('focus','#151a22')],
   background=[('pressed','#293445'),('active','#2b3545')],selectbackground=[('focus','#2d4156'),('!focus','#2d4156')],bordercolor=[('focus','#526783'),('active','#394354')])
 style.map('TNotebook.Tab',background=[('selected','#2d4156'),('active','#2b3545')])
 style.map('Treeview',background=[('selected','#2d4156')])
 style.configure('TScrollbar',troughcolor='#151a22',arrowcolor='#c0cbd9')
 root.option_add('*Menu.activeBackground','#2d4156')
 root.option_add('*Menu.activeForeground','#e6edf5')
 root.option_add('*Menu.background','#202632')
 root.option_add('*TCombobox*Listbox.background','#151a22')
 root.option_add('*TCombobox*Listbox.selectBackground','#2d4156')
 root.option_add('*selectBackground','#2d4156')
