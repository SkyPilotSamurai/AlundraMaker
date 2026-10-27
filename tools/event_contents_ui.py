"""Shared RPG-style Contents list for authored and existing game events."""
from tkinter import ttk


def contents_tree(parent, height=11):
    frame=ttk.LabelFrame(parent,text='Contents',padding=6)
    frame.pack(fill='both',expand=True,pady=(5,3))
    tree=ttk.Treeview(frame,columns=('type','summary'),show='headings',height=height)
    tree.heading('type',text='Command');tree.heading('summary',text='Settings')
    tree.column('type',width=230,minwidth=160);tree.column('summary',width=650,minwidth=180)
    scroll=ttk.Scrollbar(frame,orient='vertical',command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y');tree.pack(side='left',fill='both',expand=True)
    return tree
