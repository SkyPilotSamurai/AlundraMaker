"""Two native weapon damage controls with explicit shared-record information."""
import hashlib
import tkinter as tk
from tkinter import ttk


class WeaponDamagePanel:
    def __init__(self, parent, editor):
        self.editor = editor
        self.frame = ttk.LabelFrame(parent, text='Weapon damage', padding=10)
        self.frame.pack(fill='x', pady=6)
        self.values = {}
        self.entries = {}
        for index, (key, label) in enumerate((('normal', 'Attack damage'), ('charge', 'Charge damage'))):
            ttk.Label(self.frame, text=label).grid(row=index, column=0, sticky='w', pady=5)
            var = tk.StringVar()
            self.values[key] = var
            field = ttk.Spinbox(self.frame, textvariable=var, from_=0, to=510, width=12)
            field.grid(row=index, column=1, sticky='w', padx=10, pady=5)
            self.entries[key] = field
        self.note = tk.StringVar()
        ttk.Label(self.frame, textvariable=self.note, wraplength=580, justify='left').grid(
            row=2, column=0, columnspan=2, sticky='w', pady=(8, 0))
        self.profile = None
        self.balance = None

    def load(self, row):
        from weapon_damage_fields import weapon_damage_profile
        self.profile = None
        self.balance = None
        for key in self.values:
            self.values[key].set('')
            self.entries[key].configure(state='disabled')
        if row.get('clone_of'):
            self.note.set('Independent damage records for cloned weapons have not been allocated.')
            return
        item_id = row.get('source', {}).get('item_id')
        if type(item_id) is not int:
            self.note.set('This definition has no matched in-game weapon item.')
            return
        try:
            self.balance = self.editor.native_balance_session()
            from editor_ui import ROOT
            from mod_export import read_datas
            source = self.editor.session
            extra = getattr(source, 'extra_files', {}).get('ALUN_CD.EXE')
            if extra is not None:
                self.exe = bytes(extra.data)
            elif source.source_verified:
                self.exe = (ROOT/'game/disc/ALUN_CD.EXE').read_bytes()
            elif source.path and source.path.suffix.lower() == '.bin':
                self.exe = read_datas(source.path, 'ALUN_CD.EXE')
            else:
                raise ValueError('Open the source disc to verify this weapon’s attack routing.')
            self.profile = weapon_damage_profile(self.balance.data, item_id, self.exe)
        except ValueError as exc:
            self.note.set(str(exc))
            return
        self.loaded_hash = hashlib.sha256(self.balance.data).hexdigest()
        self.item_id = item_id
        for key in self.values:
            field = self.profile[key]
            if field.get('available'):
                self.values[key].set(str(field['power']))
                self.entries[key].configure(state='normal', from_=field.get('minimum', 0), to=field.get('maximum', 510))
        notes = list(self.profile.get('notes', []))
        if not self.profile['charge']['available']:
            notes.append('This weapon has no matched charged attack.')
        notes.append('Values are attack power before the target’s weaknesses and resistances.')
        self.note.set('\n'.join(notes))

    def apply(self):
        from weapon_damage_fields import edit_weapon_damage
        if self.profile is None:
            return None
        if hashlib.sha256(self.balance.data).hexdigest() != self.loaded_hash:
            raise ValueError('Weapon data changed. Select this weapon again before applying.')
        values = {}
        for key in self.values:
            if not self.profile[key].get('available'):
                continue
            try:
                values[key] = int(self.values[key].get().strip(), 0)
            except ValueError:
                raise ValueError('Weapon damage must be a whole number')
        return edit_weapon_damage(self.balance, self.item_id, exe=self.exe, **values)
