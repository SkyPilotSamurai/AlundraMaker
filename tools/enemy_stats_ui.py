"""Enemy combat form backed by verified BALANCE bytes, not invented stats."""
from copy import deepcopy
from decimal import Decimal,InvalidOperation
import tkinter as tk
from tkinter import ttk
from attack_attributes import attribute_box,parse_attribute
from enemy_combat_fields import SOURCE_ATTACK_TYPES,ATTACK_LABELS,decode_response,encode_response

MODE_LABELS={'Damage multiplier':'scalar','Set HP to zero':'zero_hp',
             'Special 0x80':'skip_80','Special 0xC0':'skip_c0'}
PRESETS=tuple(f'{n*6.25:g}%' for n in range(64))   # every native factor 0..63 /16


def byte_value(value,label):
    try:result=int(str(value).strip(),0)
    except ValueError:raise ValueError(f'{label} must be a whole number 0..255')
    if not 0<=result<=255:raise ValueError(f'{label} must be 0..255')
    return result


def multiplier_factor(text):
    value=str(text).strip()
    if '(' in value:value=value.rsplit('(',1)[-1].rstrip(')')
    try:factor=Decimal(value.rstrip('%'))*Decimal(16)/Decimal(100)
    except InvalidOperation:raise ValueError('Incoming damage must be a percentage, e.g. 100%')
    if not factor.is_finite() or factor!=factor.to_integral_value() or not 0<=factor<=63:
        raise ValueError('Incoming damage is 0..393.75% in 6.25% steps')
    return int(factor)


def response_values(row):
    data=row.get('data',{});raw=data.get('damage_responses_raw')
    if raw is None and data.get('balance_tiers'):raw=data['balance_tiers'][0].get('damage_responses_raw')
    if raw is None:return None
    if not isinstance(raw,list) or len(raw)!=11:raise ValueError('Exactly 11 native incoming responses required')
    for value in raw:decode_response(value)
    return list(raw)


def apply_combat_form(row,hp,attack_powers,contact_index=None,incoming=None,attributes=None):
    result=deepcopy(row);data=result['data'];attacks=deepcopy(data.get('attacks',[]))
    if len(attack_powers)!=len(attacks):raise ValueError('Attack list changed; reload this class')
    data['max_hp']=None if str(hp).strip()=='' and data.get('max_hp') is None else byte_value(hp,'Max HP')
    for i,power in enumerate(attack_powers):attacks[i]['power']=byte_value(power,f'Attack {i+1} damage')
    if attributes is not None:
        if len(attributes)!=len(attacks):raise ValueError('Attack attribute list changed')
        for i,value in enumerate(attributes):attacks[i]['attribute']=byte_value(value,f'Attack {i+1} attribute')
    data['attacks']=attacks
    source=result.setdefault('source',{})
    if contact_index is None:source.pop('contact_attack_index',None)
    else:
        if type(contact_index) is not int or not 0<=contact_index<len(attacks):raise ValueError('Choose an existing contact attack pair')
        source['contact_attack_index']=contact_index
    if incoming is not None:
        if len(incoming)!=11:raise ValueError('Exactly 11 incoming attack responses required')
        if any(mode not in MODE_LABELS for mode,percent in incoming):raise ValueError('Choose a supported incoming damage mode')
        raw=[encode_response(MODE_LABELS[mode],multiplier_factor(percent)) for mode,percent in incoming]
        data['damage_responses_raw']=raw
    return result


class EnemyCombatPanel:
    def __init__(self,parent,labels=None,show_hp=True,readonly_attacks=False):
        self.readonly_attacks=readonly_attacks   # Alundra: shown only; weapon damage edits change them
        # labels(row,index,attack) -> row text, or None to hide that pair (kept unchanged).
        self.labels=labels
        self.frame=ttk.LabelFrame(parent,text='Combat',padding=6);self.frame.pack(fill='x',pady=3)
        stats=ttk.Frame(self.frame)
        if show_hp:stats.pack(fill='x')   # the Player tab has Max HP under Starting stats already
        self.hp=tk.StringVar();ttk.Label(stats,text='Max HP').grid(row=0,column=0,sticky='w')
        ttk.Spinbox(stats,from_=0,to=255,textvariable=self.hp,width=8).grid(row=0,column=1,padx=6,sticky='w')
        contact=ttk.Frame(self.frame)  # contact row hidden (user request); keeps saved contact links
        ttk.Label(contact,text='Contact attack').pack(side='left');self.contact_choice=tk.StringVar(value='Not assigned')
        self.contact_combo=ttk.Combobox(contact,textvariable=self.contact_choice,state='readonly',width=20);self.contact_combo.pack(side='left',padx=6)
        self.contact_damage=tk.StringVar();self.contact_entry=ttk.Spinbox(contact,from_=0,to=255,textvariable=self.contact_damage,width=7,state='disabled');self.contact_entry.pack(side='left')
        self.contact_combo.bind('<<ComboboxSelected>>',lambda _:self.select_contact())
        self.contact_damage.trace_add('write',lambda *_:self.sync_contact_to_attack())
        self.attack_host=ttk.Frame(self.frame,padding=(5,2));self.attack_host.pack(fill='x',pady=2)
        self.response_host=ttk.LabelFrame(self.frame,text='Incoming damage / weaknesses and resistances',padding=4);self.response_host.pack(fill='x',pady=(2,0))
        self.boss_note=tk.StringVar()
        self.alias_note=tk.StringVar();self.alias_label=ttk.Label(self.frame,textvariable=self.alias_note,wraplength=570)   # shown only when there is a note
        self.raw_host=ttk.Frame(self.frame)   # attributes now sit beside each attack; kept empty for older callers
        self.loading=False;self.attack_vars=[];self.attribute_vars=[];self.response_vars=[]
    def load(self,row):
        self.loading=True
        for host in (self.attack_host,self.response_host,self.raw_host):
            for child in host.winfo_children():child.destroy()
        self.hp.set('' if row['data'].get('max_hp') is None else str(row['data']['max_hp']))
        self.attack_vars=[];self.attribute_vars=[];self.response_vars=[]
        attacks=row['data'].get('attacks',[])
        for i,attack in enumerate(attacks):
            var=tk.StringVar(value=str(attack['power']));self.attack_vars.append(var)
            text=self.labels(row,i,attack) if self.labels else ('Contact Damage' if i==0 else f'Attack {i+1} damage')
            attribute=tk.StringVar();self.attribute_vars.append(attribute)
            if text is None:
                attribute.set(str(attack['attribute']));continue   # hidden pair: kept as it is
            ttk.Label(self.attack_host,text=text).grid(row=i,column=0,sticky='w')
            if self.readonly_attacks:
                ttk.Label(self.attack_host,textvariable=var,width=8).grid(row=i,column=1,padx=8)
                attribute.set(str(attack['attribute']))
                from attack_attributes import attribute_label
                ttk.Label(self.attack_host,text=attribute_label(attack['attribute'])).grid(row=i,column=2,sticky='w')
                continue
            ttk.Spinbox(self.attack_host,from_=0,to=255,textvariable=var,width=8).grid(row=i,column=1,padx=8)
            var.trace_add('write',lambda *_,index=i:self.sync_attack_to_contact(index))
            # Each attack's attribute sits right after its damage.
            attribute_box(self.attack_host,attribute,attack['attribute'],width=22).grid(row=i,column=2,sticky='w')
        if not attacks:ttk.Label(self.attack_host,text='No decoded attack pairs for this class').pack(anchor='w')
        choices=['Not assigned']+[f'Attack {i+1}' for i in range(len(attacks))];self.contact_combo.configure(values=choices)
        index=row.get('source',{}).get('contact_attack_index')
        self.contact_choice.set(f'Attack {index+1}' if type(index) is int and 0<=index<len(attacks) else 'Not assigned')
        from boss_damage_profiles import BOSSES
        entry=row.get('source',{}).get('catalogue_index',row.get('source',{}).get('balance_entry'))
        self.boss_note.set('Boss damage formula: max(1, floor(combined incoming power × response /16)) for scalar responses. The controls below edit its native parameters; vulnerability windows and AI timing are not simulated.' if entry in BOSSES else '')
        raw=response_values(row)
        if raw is None:ttk.Label(self.response_host,text='No decoded incoming responses; import this game’s balance data first.').pack(anchor='w')
        else:
            for i,value in enumerate(raw):
                decoded=decode_response(value);mode=tk.StringVar(value=next(label for label,key in MODE_LABELS.items() if key==decoded['mode']))
                percent=tk.StringVar(value=f"{decoded['factor_numerator']*6.25:g}%")
                self.response_vars.append((mode,percent))
                ttk.Label(self.response_host,text=ATTACK_LABELS[i]).grid(row=i,column=0,sticky='w',padx=3,pady=1)
                ttk.Combobox(self.response_host,textvariable=mode,values=list(MODE_LABELS),state='readonly',width=20).grid(row=i,column=1,padx=3)
                ttk.Combobox(self.response_host,textvariable=percent,values=PRESETS,width=19).grid(row=i,column=2,padx=3)
        aliases=(row['data'].get('balance_tiers') or [{}])[0].get('alias_entries',[])
        self.alias_note.set(f"Shared native balance record: {len(aliases)} entries. Source edits affect all aliases." if len(aliases)>1 else '')
        if self.alias_note.get():self.alias_label.pack(anchor='w',pady=(2,0))
        else:self.alias_label.pack_forget()
        self.loading=False;self.select_contact()
    def contact_index(self):
        value=self.contact_choice.get()
        return None if value=='Not assigned' else int(value.removeprefix('Attack '))-1
    def select_contact(self):
        index=self.contact_index();self.loading=True
        self.contact_entry.configure(state='disabled' if index is None else 'normal')
        self.contact_damage.set('' if index is None else self.attack_vars[index].get());self.loading=False
    def sync_attack_to_contact(self,index):
        if self.loading or self.contact_index()!=index:return
        self.loading=True;self.contact_damage.set(self.attack_vars[index].get());self.loading=False
    def sync_contact_to_attack(self):
        if self.loading:return
        index=self.contact_index()
        if index is not None:self.loading=True;self.attack_vars[index].set(self.contact_damage.get());self.loading=False
    def apply(self,row):
        if self.readonly_attacks:   # never written from here: keep whatever the weapons set
            attacks=row['data'].get('attacks',[])
            return apply_combat_form(row,self.hp.get(),[str(x['power']) for x in attacks],self.contact_index(),
                [(mode.get(),percent.get()) for mode,percent in self.response_vars] if self.response_vars else None,
                [x['attribute'] for x in attacks])
        return apply_combat_form(row,self.hp.get(),[v.get() for v in self.attack_vars],self.contact_index(),
            [(mode.get(),percent.get()) for mode,percent in self.response_vars] if self.response_vars else None,
            [parse_attribute(v.get()) for v in self.attribute_vars])
