"""Database: what an armour does once Alundra has it.

Native rule (ALUN_CD.EXE 0x800307E8 UpdateItemEffectState / 0x80030904, via the
MIT xcasadio PlayerManager.cs): the best body armour Alundra owns replaces his
own incoming-damage table with the armour's balance record, so for every attack
type damage taken = attack power x value / 16 (16 = 100%). Cloth 16 (100%),
Leather 12 (75%), Ancient 8 (50%), Silver 4 (25%). Boots carry 64 (flag 0x40),
which the rule skips: they do not change damage taken (their effects are built
into the game: e.g. the gravity / speed checks on item 0x1A-0x1C).
"""
import tkinter as tk
from tkinter import ttk

from attack_attributes import ATTACK_TYPES


def responses(row):
    data = row.get('data', {})
    raw = data.get('damage_responses_raw')
    if raw is None and data.get('balance_tiers'):
        raw = data['balance_tiers'][0].get('damage_responses_raw')
    return list(raw) if isinstance(raw, list) and len(raw) == 11 else None


class ArmorDamagePanel:
    def __init__(self, parent, editor):
        self.editor = editor
        self.frame = ttk.LabelFrame(parent, text='Damage taken while Alundra has this armour', padding=8)
        self.frame.pack(fill='x', pady=6)
        self.host = ttk.Frame(self.frame); self.host.pack(fill='x')
        self.vars = []; self.raw = None

    def load(self, row):
        for child in self.host.winfo_children(): child.destroy()
        self.vars = []; self.raw = responses(row)
        if self.raw is None:
            ttk.Label(self.host, text='No balance record for this armour.').pack(anchor='w'); return
        if all(v & 0xC0 for v in self.raw):
            ttk.Label(self.host, wraplength=560, text="Doesn't change the damage Alundra takes. "
                      "Its effect (for example faster walking or no slipping) is built into the game.").pack(anchor='w')
            return
        for i, value in enumerate(self.raw):
            name = ATTACK_TYPES.get(i + 1, f'Type {i + 1}')
            r, c = 1 + i // 2, (i % 2) * 2
            ttk.Label(self.host, text=name).grid(row=r, column=c, sticky='w', padx=(0, 6), pady=1)
            var = tk.StringVar(value=f'{(value & 0x3F) * 100 / 16:g}%' if not value & 0xC0 else 'unchanged')
            box = ttk.Spinbox(self.host, values=[f'{n * 6.25:g}%' for n in range(0, 64)], textvariable=var, width=9)
            if value & 0xC0: box.configure(state='disabled')
            box.grid(row=r, column=c + 1, sticky='w', padx=(0, 18), pady=1)
            self.vars.append(var)

    def apply(self, row):
        if self.raw is None or not self.vars:
            return row
        out = []
        for value, var in zip(self.raw, self.vars):
            if value & 0xC0: out.append(value); continue
            text = var.get().strip().rstrip('%')
            try: percent = float(text)
            except ValueError: raise ValueError('Damage taken must be a percentage, e.g. 75%')
            n = round(percent * 16 / 100)
            if not 0 <= n <= 63 or abs(n * 100 / 16 - percent) > 0.01:
                raise ValueError('Damage taken is 0-393.75% in 6.25% steps (for example 75% or 50%)')
            out.append(n)
        row['data']['damage_responses_raw'] = out
        return row


# Silver Armlet (item 53) and Nava's Charm (item 54) (user 2026-10-26). Static, stock US 1.1:
# Alundra's damage table is the working copy 0x801E70B8 (used for him at 0x8003ACDC), rebuilt
# every frame (0x80030CA4, called at 0x8003302C) from the body armour's record (0x801E9E68), the
# equipped weapon's (0x801E9E70, 0x80030E10) and the selected item's (0x801E9E78, 0x80030E64, only an
# item of type 3 such as these two): so they work while selected as his item. Per attack type
# (0x80031018..0x80031108): any 128 (0x80) -> no damage; otherwise armour value + (item value - 16)
# for each item, kept within 0..31. So an item value adds (value - 16) x 6.25% to the damage taken.
ACCESSORY_ITEMS = (53, 54)


class AccessoryDamagePanel:
    def __init__(self, parent, editor):
        self.editor = editor
        self.frame = ttk.LabelFrame(parent, text="Damage taken while this is Alundra's selected item", padding=8)
        self.host = ttk.Frame(self.frame); self.host.pack(fill='x')
        self.vars = []; self.raw = None

    def load(self, row):
        for child in self.host.winfo_children(): child.destroy()
        self.vars = []; self.raw = None; self.custom = False
        own = (row.get('source') or {}).get('item_id')
        if own in range(31, 51):
            # any item Circle can use, given the Accessory category: its own defence values
            # (custom_accessory; 16 = unchanged) (user 2026-10-27)
            self.custom = True
            self.raw = list(((row.get('data') or {}).get('accessory') or {}).get('defence') or [16] * 11)
        elif own not in ACCESSORY_ITEMS:
            self.frame.pack_forget(); return
        else:
            self.raw = responses(row)
        if self.raw is None:
            self.frame.pack_forget(); return
        self.frame.pack(fill='x', pady=6)
        choices = ['No damage'] + [f'{(n - 16) * 6.25:+g}%' for n in range(0, 32)]
        for i, value in enumerate(self.raw):
            r, c = i // 2, (i % 2) * 2
            ttk.Label(self.host, text=ATTACK_TYPES.get(i + 1, f'Type {i + 1}')).grid(row=r, column=c, sticky='w', padx=(0, 6), pady=1)
            var = tk.StringVar(value='No damage' if value & 0x80 else f'{((value & 0x3F) - 16) * 6.25:+g}%')
            ttk.Combobox(self.host, values=choices, textvariable=var, state='readonly', width=10).grid(row=r, column=c + 1, sticky='w', padx=(0, 18), pady=1)
            var.trace_add('write', lambda *_: self.editor.db_schedule_autosave())
            self.vars.append(var)

    def apply(self, row):
        if self.raw is None or not self.vars:
            return row
        out = []
        for var in self.vars:
            text = var.get()
            if text == 'No damage': out.append(0x80); continue
            out.append(16 + round(float(text.rstrip('%')) / 6.25))
        if self.custom:
            acc = dict(row['data'].get('accessory') or {})
            if out == [16] * 11 and not acc.get('recovery'):
                row['data'].pop('accessory', None)
            else:
                acc['defence'] = out; row['data']['accessory'] = acc
            return row
        row['data']['damage_responses_raw'] = out
        return row
