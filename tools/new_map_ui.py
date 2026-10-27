"""Ask which existing map to save a new map over, once all 17 new slots are used."""
import tkinter as tk
from tkinter import ttk, messagebox
from map_names import map_label


class OverwriteMapDialog:
    """Two tabs: Unused Maps (never visited by the game) and Game Maps, plus
    Expand Maps (new maps 500 and up, see map_slots)."""

    def __init__(self, editor, on_choose, on_expand=None):
        from map_create import overwrite_choices
        unused, game, free = overwrite_choices(editor.session, editor.database.document)
        created = set(editor.database.document.get('created_maps', []))
        self.editor = editor; self.on_choose = on_choose
        self.window = win = tk.Toplevel(editor.root); win.title('New Map: Choose A Map To Save Over')
        win.transient(editor.root); win.geometry('560x560')
        ttk.Label(win, text='All 17 new map slots are in use. Expand Maps to keep adding maps (500 and up), '
                  'or choose a map to replace with the new blank map.',
                  wraplength=520, padding=(10, 10, 10, 4)).pack(anchor='w')
        if on_expand is not None:
            expand = ttk.Frame(win, padding=(10, 0, 10, 6)); expand.pack(fill='x')
            ttk.Button(expand, text='Expand Maps', command=lambda: editor.guard(self.expand)).pack(side='left')
            ttk.Label(expand, text='Adds map 500, 501, ... New Map keeps adding them from then on.',
                      wraplength=380).pack(side='left', padx=8)
        self.on_expand = on_expand
        self.query = tk.StringVar(); search = ttk.Entry(win, textvariable=self.query); search.pack(fill='x', padx=10, pady=4)
        self.tabs = ttk.Notebook(win); self.tabs.pack(fill='both', expand=True, padx=10, pady=4)
        self.lists = {}
        for key, title, maps in (('unused', 'Unused Maps', unused), ('game', 'Game Maps', game)):
            frame = ttk.Frame(self.tabs); self.tabs.add(frame, text=title)
            tree = ttk.Treeview(frame, columns=('map',), show='headings', selectmode='browse')
            tree.heading('map', text='Map'); tree.column('map', width=480)
            scroll = ttk.Scrollbar(frame, command=tree.yview); tree.configure(yscrollcommand=scroll.set)
            scroll.pack(side='right', fill='y'); tree.pack(fill='both', expand=True)
            tree.bind('<Double-1>', lambda _: editor.guard(self.choose))
            self.lists[key] = (tree, maps)
        self.marks = dict(free=free, created=created)
        footer = ttk.Frame(win, padding=10); footer.pack(fill='x')
        ttk.Button(footer, text='Save New Map Over It', command=lambda: editor.guard(self.choose)).pack(side='right')
        ttk.Button(footer, text='Cancel', command=win.destroy).pack(side='right', padx=6)
        self.query.trace_add('write', lambda *_: self.refresh()); self.refresh(); search.focus_set()

    def label(self, m):
        note = ' — already one of your new maps' if m in self.marks['created'] else (' — free' if m in self.marks['free'] else '')
        return map_label(m) + note

    def refresh(self):
        needle = self.query.get().casefold()
        for tree, maps in self.lists.values():
            tree.delete(*tree.get_children())
            for m in maps:
                text = self.label(m)
                if needle in text.casefold():
                    tree.insert('', 'end', iid=str(m), values=(text,))

    def expand(self):
        self.window.destroy(); self.on_expand()

    def choose(self):
        key = 'unused' if self.tabs.index(self.tabs.select()) == 0 else 'game'
        tree, _ = self.lists[key]; selection = tree.selection()
        if not selection:
            raise ValueError('Choose a map first')
        m = int(selection[0])
        warning = (f'Replace {map_label(m)} with a new blank map?\n\nIts tiles, characters, events and warps are removed. Undo restores it.'
                   if key == 'unused' else
                   f'{map_label(m)} is used by the game. Replacing it can break the story or leave doors leading to an empty map.\n\nReplace it with a new blank map anyway? Undo restores it.')
        self.window.destroy(); self.on_choose(m)
