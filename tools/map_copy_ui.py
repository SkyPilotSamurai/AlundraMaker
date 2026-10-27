"""UI glue for Map > New map: copy of another map (hooked from editor_ui.Editor).

Wire it in from editor_ui.py:
    from map_copy_ui import new_map_copy
    ...
    group("Map",[..., ("New map: copy of another map...",run(lambda:new_map_copy(self)))])
"""
from location_picker import LocationPicker
from map_names import map_label


def ask_keep_events(parent, source):
    """Keep Events / Fresh Map: True, False, or None when the window is closed."""
    import tkinter as tk
    from tkinter import ttk
    win = tk.Toplevel(parent); win.title('New Map: Carry Over Events?'); win.transient(parent); win.resizable(False, False)
    answer = {'keep': None}
    ttk.Label(win, justify='left', wraplength=420, padding=12,
              text=f'Carry over the characters, events and warps of {map_label(source)}?').pack()
    row = ttk.Frame(win, padding=(12, 0, 12, 12)); row.pack(fill='x')

    def pick(value):
        answer['keep'] = value; win.destroy()
    keep = ttk.Button(row, text='Keep Events', command=lambda: pick(True)); keep.pack(side='left')
    ttk.Button(row, text='Fresh Map', command=lambda: pick(False)).pack(side='left', padx=(8, 0))
    ttk.Button(row, text='Cancel', command=win.destroy).pack(side='right')
    win.bind('<Escape>', lambda e: win.destroy())
    keep.focus_set(); win.grab_set(); parent.wait_window(win)
    return answer['keep']


def new_map_copy(editor):
    """New map copying another map as it is now. You choose whether its
    characters, events and warps come along (a boss room keeps its boss)."""
    editor.need()

    def make(source):
        from map_create import create_copy_of_map, record_edits, apply_edits, copy_map_document
        keep = ask_keep_events(editor.root, source)
        if keep is None:
            return
        with editor.session.group(f'New map copied from map {source}'):
            m = create_copy_of_map(editor.session, editor.database.document, source)
            if keep:
                copy_map_document(editor.database.document, source, m)
            else:
                edits = record_edits(editor.session, m)
                if edits:
                    apply_edits(editor.session, edits, f'New map {m}: leave out copied characters/events/warps')
        editor.set_map_name(m, f'{map_label(source).rsplit(" (Map ", 1)[0]} (copy)')
        editor.dirty = True; editor.populate_database_from_game()
        editor.map_id.set(str(m)); editor.load_map()
        note = 'same tiles, heights, characters, events and warps' if keep else 'same tiles and heights, no characters, events or warps'
        editor.status.set(f'Map {m} is a copy of map {source}: {note}.')

    LocationPicker(editor, on_choose=lambda m: editor.guard(lambda: make(m)),
                   title="New Map: Copy Which Map?", button="Copy this map")