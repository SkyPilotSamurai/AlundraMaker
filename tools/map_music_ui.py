"""Map Music dialog: change the background music of the current map only.

The choice is saved straight into the database (document['map_music']) and
written to ALUN_CD.EXE's map music table when the mod is exported. Choosing the
game's own track removes the override.
"""
import struct
import tkinter as tk
from tkinter import ttk
from music_database import TRACK_COUNT, map_music_values
from game_audio_names import music_name


def label(document, track):
    return f'{track:03d} - {music_name(document, track)}'


def native_track(editor, map_id):
    """The game's own track for this map, or None when the game EXE is not available."""
    try:
        from sound_database import library_for_editor
        library = library_for_editor(editor)
        if library is None:
            return None
        return map_music_values(library.exe)[map_id]
    except (ValueError, OSError, IndexError, StopIteration):
        return None


def current_track(editor, map_id, default=None):
    value = editor.database.document.get('map_music', {}).get(str(map_id))
    return default if value is None else int(value)


def set_map_track(editor, map_id, track, default=None):
    """Store one map's track. Returns True when the database changed."""
    if type(track) is not int or not 0 <= track < TRACK_COUNT:
        raise ValueError(f'Music track must be 0..{TRACK_COUNT - 1}')
    overrides = editor.database.document.setdefault('map_music', {})
    key = str(map_id); before = overrides.get(key)
    if default is not None and track == default:
        overrides.pop(key, None)
    else:
        overrides[key] = track
    if not overrides:
        editor.database.document.pop('map_music', None)
    changed = before != overrides.get(key)
    if changed:
        editor.dirty = True
    return changed


LOOK_OFFSET, LOOK_SIZE = 0x0B, 5   # map-info header bytes that differ between dungeon/dream/overworld looks


def look_bytes(session, map_id):
    base, h = session.layout(map_id)
    o = base + h[0] + LOOK_OFFSET
    return o, bytes(session.data[o:o + LOOK_SIZE])


def look_presets(session):
    """{label: bytes}: every different look used by the game's own maps,
    named after the maps that use it (dream looks are marked)."""
    import re
    from map_names import map_label
    groups = {}
    for m in range(483):
        try: groups.setdefault(look_bytes(session, m)[1], []).append(m)
        except (ValueError, IndexError, struct.error): pass
    presets = {}
    for raw, maps in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        names = []
        for m in maps:
            name = re.sub(r'\s*\d+$', '', map_label(m).rsplit(' (Map', 1)[0]).strip()
            if name not in names: names.append(name)
        dream = sum('Dream' in map_label(m) for m in maps) * 2 > len(maps)   # mostly dream maps
        if dream: names = [n for n in names if 'Dream' in n] or names
        text = ('Dream: ' if dream else '') + ', '.join(names[:3]) + (' …' if len(names) > 3 else '')
        presets[text] = raw
    return presets


class MapMusicDialog:
    def __init__(self, editor):
        map_id = getattr(editor, 'current_map', None)
        if editor.session is None or map_id is None:
            raise ValueError('Open a map first')
        old = getattr(editor, 'map_music_window', None)
        if old is not None:
            try:
                old.window.destroy()
            except tk.TclError:
                pass
        editor.map_music_window = self
        self.editor = editor; self.map_id = map_id
        self.default = native_track(editor, map_id)
        document = editor.database.document
        self.choices = {label(document, i): i for i in range(TRACK_COUNT) if i not in __import__('game_audio_names').HIDDEN_TRACKS}
        self.window = win = tk.Toplevel(editor.root)
        win.title(f'Map Properties - Map {map_id}'); win.transient(editor.root); win.resizable(False, False)
        body = ttk.Frame(win, padding=12); body.pack(fill='both', expand=True)
        ttk.Label(body, text='Music').grid(row=0, column=0, sticky='w')
        start = current_track(editor, map_id, self.default)
        self.track = tk.StringVar(value=label(document, start) if start is not None else '')
        self.combo = ttk.Combobox(body, textvariable=self.track, values=list(self.choices), state='readonly', width=40)
        self.combo.grid(row=0, column=1, padx=(8, 0), sticky='we')
        self.combo.bind('<<ComboboxSelected>>', lambda _: editor.guard(self.save))
        game = label(document, self.default) if self.default is not None else 'Unknown (game EXE not available)'
        ttk.Label(body, text=f'Game default: {game}').grid(row=1, column=0, columnspan=2, sticky='w', pady=(8, 0))
        from audio_preview import PreviewBar
        PreviewBar(body, editor, 'music', lambda: self.choices.get(self.track.get())).frame.grid(row=2, column=0, columnspan=2, sticky='w', pady=(10, 0))
        # Look: background and effects (dream look included), copied from a game map
        ttk.Separator(body).grid(row=3, column=0, columnspan=2, sticky='we', pady=(12, 8))
        ttk.Label(body, text='Background && effects').grid(row=4, column=0, sticky='w')
        self.presets = look_presets(editor.session)
        _, now = look_bytes(editor.session, map_id)
        current = next((k for k, v in self.presets.items() if v == now), None)
        if current is None:
            current = f'Custom ({now.hex(" ")})'; self.presets = {current: now, **self.presets}
        self.look = tk.StringVar(value=current)
        look = ttk.Combobox(body, textvariable=self.look, values=list(self.presets), state='readonly', width=60)
        look.grid(row=4, column=1, padx=(8, 0), sticky='we')
        look.bind('<<ComboboxSelected>>', lambda _: editor.guard(self.save_look))
        ttk.Label(body, text='Uses the same background/effect settings as the named maps (choose a "Dream:" one for a dream look). Shown in game after you build.',
                  wraplength=520, foreground='#a8b6c8').grid(row=5, column=0, columnspan=2, sticky='w', pady=(4, 0))
        buttons = ttk.Frame(body); buttons.grid(row=6, column=0, columnspan=2, sticky='e', pady=(12, 0))
        self.reset_button = ttk.Button(buttons, text='Reset To Default', command=lambda: editor.guard(self.reset))
        self.reset_button.pack(side='left', padx=(0, 6))
        if self.default is None:
            self.reset_button.state(['disabled'])
        ttk.Button(buttons, text='Done', command=win.destroy).pack(side='left')
        win.bind('<Escape>', lambda _: win.destroy())
        self.combo.focus_set()

    def save(self):
        track = self.choices[self.track.get()]
        if set_map_track(self.editor, self.map_id, track, self.default):
            self.after_change(track)

    def save_look(self):
        raw = self.presets[self.look.get()]
        offset, now = look_bytes(self.editor.session, self.map_id)
        if raw == now: return
        self.editor.session.replace(offset, raw, 'Map background/effects')
        self.editor.dirty = True
        status = getattr(self.editor, 'status', None)
        if status is not None: status.set(f'Map {self.map_id} background/effects: {self.look.get()}')

    def reset(self):
        if self.default is None:
            return
        self.track.set(label(self.editor.database.document, self.default))
        self.save()

    def after_change(self, track):
        name = music_name(self.editor.database.document, track)
        status = getattr(self.editor, 'status', None)
        if status is not None:
            status.set(f'Map {self.map_id} music: {track:03d} - {name}')
        tab = getattr(self.editor, 'db_music', None)
        try:
            if tab is not None and tab.frame.winfo_exists():
                tab.refresh()
        except tk.TclError:
            pass
