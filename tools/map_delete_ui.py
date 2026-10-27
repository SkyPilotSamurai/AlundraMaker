"""UI glue for Map > Delete this map (hooked from editor_ui.Editor).

Wire it in from editor_ui.py:
    from map_delete_ui import delete_current_map
    ...
    group("Map",[..., ("Delete this map...",run(lambda:delete_current_map(self)))])
"""
from tkinter import messagebox
from map_names import map_label


def delete_current_map(editor):
    """Remove a map this project added. Maps above it move down one number."""
    editor.need(); editor.lock_in_closed_events()
    m = editor.current_map
    if m is None:
        raise ValueError('Open the map you want to delete first')
    from map_delete import can_delete, references, delete_map
    can_delete(editor.session, m)
    report = references(editor.session, editor.database.document, m)
    lines = [f'Delete {map_label(m)}?', '',
             'Its tiles, characters, events and warps go, and every map above it moves down one number.']
    if report['doors']:
        lines.append(f"{len(report['doors'])} door(s) on other maps lead here and will be emptied.")
    if report['events']:
        lines.append(f"{len(report['events'])} event(s) you placed on this map are deleted.")
    if report['warp_commands']:
        lines.append(f"{len(report['warp_commands'])} event command(s) elsewhere warp to this map and are removed.")
    lines += ['', 'Undo takes the whole deletion back.']
    if not messagebox.askyesno('Delete map', '\n'.join(lines), parent=editor.root):
        return
    delete_map(editor.session, editor.database.document, m)
    editor.dirty = True
    from map_slots import map_count
    target = max(0, min(m, map_count(editor.session.data) - 1))
    editor.populate_database_from_game(); editor.db_refresh()
    editor.current_map = None; editor.map_id.set(str(target)); editor.load_map()
    editor.status.set(f'Map {m} deleted. Maps above it moved down one number.')