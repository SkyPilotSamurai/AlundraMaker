"""Bounded randomizer-style world access recipes, without dream dungeon mode.

Stock-relative sites are resolved through current script roots/entity lists,
including DATAS whose maps and native process clusters have been repacked.

World recipes derive from Dinopony's MIT randomizer, copyright2022Dinopony.
Full permission/copyright notice: docs/OPEN_WORLD_RANDOMIZER_LICENSE.txt.
"""
import json
import struct
from pathlib import Path
from alundra_memory import parse_exe
from event_editor import script_roots
from map_inspector import inspect_map

ROOT=Path(__file__).resolve().parents[1]
RECIPE=ROOT/'data/2026-10-05-editor-open-world-recipe.json'
KEPT_INOA_MAPS=(241,243,244,245,246,247,258,260)
OPEN_WORLD_SPAWN=dict(map_id=242,x=38,y=12,z=2,house_variant=260)


def _find_all(data,needle):
    hits=[];cursor=0
    while True:
        found=data.find(needle,cursor)
        if found<0:return hits
        hits.append(found);cursor=found+1


def _process_recipe_offset(data,start,end,relative,before,after,map_id,key,source_path,source_line,valid_starts=None,compatible=()):
    """Resolve stock sites after edits shifted commands within their own process."""
    original=start+relative
    current=bytes(data[original:original+len(before)])
    accepted=(before,after,*compatible)
    if current in accepted:return original,False
    code=bytes(data[start:end])
    signatures=set()
    for signature in accepted:signatures.update(_find_all(code,signature))
    if valid_starts is not None:signatures.intersection_update(valid_starts)
    if len(signatures)==1:
        return start+next(iter(signatures)),True
    expected='; '.join((before.hex(' '),after.hex(' '),*(x.hex(' ') for x in compatible)))
    location=f'native process {key}+0x{relative:X}'
    candidate_note=('no unique copy of the supported route command remains'
                    if not signatures else f'{len(signatures)} possible route commands remain')
    raise ValueError(
        f'Open World cannot safely patch map{map_id} ({location}). '
        f'Expected bytes {expected}, but found {current.hex(" ")} at the original location; '
        f'{candidate_note}. The route code changed ({source_path}:{source_line}). '
        'The editor will not overwrite it. Turn off Open World to build these edits, '
        'or restore the matching source route.')


def patch_open_world_spawn(exe):
    """Select the canonical Jess room; preserve every unrelated instruction."""
    from intro_skip import EXE_FIELDS
    # The randomizer's PatchNewGame uses map242, X=0x26, Y=0x0C.
    # Open-world initialization separately selects Jess variant260.
    immediates=(38,12,2,242,38,12,None)
    info=parse_exe(exe);data=bytearray(exe);sites=[]
    for (address,stock,intro,label),value in zip(EXE_FIELDS,immediates):
        offset=0x800+address-info['load_address']
        if not 0x800<=offset<=0x800+info['load_size']-4:
            raise ValueError('Open-world spawn outside executable payload')
        wanted=(intro&0xffff0000)|value if value is not None else intro
        found=struct.unpack_from('<I',data,offset)[0]
        if found not in (stock,intro,wanted):raise ValueError('Open-world spawn instruction changed: '+label)
        sites.append(dict(native_address=hex(address),file_offset=hex(offset),before_word=f'{found:08x}',after_word=f'{wanted:08x}',field=label))
    for row in sites:struct.pack_into('<I',data,int(row['file_offset'],16),int(row['after_word'],16))
    return bytes(data),dict(spawn=OPEN_WORLD_SPAWN.copy(),sites=sites,
        house_variant=260,
        entry_evidence='Pinned randomizer new-game constants: Jess map242, X=0x26, Y=0x0C. Map242 and its initialized house variant260 both report walkability0,height2 at tile38,12.',gameplay_verified=False)


def open_world_starting_state():
    """Exact selected source flags/variant stores for a new-game init wrapper."""
    recipe=json.loads(RECIPE.read_text(encoding='utf-8'))
    return recipe['starting_flags'],recipe['map_variant_stores']


def world_access_plan(session,select=None):
    recipe=json.loads(RECIPE.read_text(encoding='utf-8'))
    plans=[];roots={};entities={}
    for row in recipe['patches']:
        if select is not None and not select(row):continue
        m=row['map_id'];anchor=row['anchor']
        if anchor['kind']=='process':
            if m not in roots:roots[m]=script_roots(session,m)
            if anchor['key'] not in roots[m]:raise ValueError(f'World access native process missing: map{m} {anchor["key"]}')
            start,end,_=roots[m][anchor['key']];offset=start+anchor['relative_offset']
        elif anchor['kind']=='entity':
            if m not in entities:entities[m]=inspect_map(session.data,m)['entities']
            if anchor['index']>=len(entities[m]):raise ValueError('World access source entity removed')
            offset=int(entities[m][anchor['index']]['offset'],16)+anchor['relative_offset']
        else:
            base,h=session.layout(m);offset=base+h[anchor['section']]+anchor['relative_offset']
        before=bytes.fromhex(row['before']);after=bytes.fromhex(row['after'])
        compatible=()
        if anchor['kind']=='process' and row['source_path'].endswith('patch_neutralize_map_variant_changes.hpp'):
            # The pinned randomizer's source writes C5 as byte0 and leaves
            # the original operands in place; its EXE supplies that opcode.
            # Convert only this exact signature to the editor's native skip.
            compatible=(bytes((0xC5,))+before[1:],)
        moved=False
        if anchor['kind']=='process':
            from event_editor import instructions
            valid_starts={op_offset for op_offset,_,_ in instructions(session,m,anchor['key'])}
            offset,moved=_process_recipe_offset(session.data,start,end,anchor['relative_offset'],before,after,
                m,anchor['key'],row['source_path'],row['source_line'],valid_starts,compatible)
        found=bytes(session.data[offset:offset+len(before)])
        if found not in (before,after,*compatible):
            location=(f'native process {anchor["key"]}+0x{anchor["relative_offset"]:X}'
                      if anchor['kind']=='process' else f'entity {anchor.get("index", "?")}')
            raise ValueError(f'Open World source changed on map{m} ({location}): {found.hex(" ")}')
        resolved=dict(row)
        if moved:resolved['resolved_relative_offset']=offset-start
        plans.append((offset,found,after,resolved))
    return plans,recipe


def apply_world_access(session):
    """Apply preimage-guarded DATAS recipes; state injection is separate."""
    plans,recipe=world_access_plan(session)
    changes=[]
    for offset,before,after,row in plans:
        if before!=after:
            session.replace(offset,after,'Open-world route: '+row['source_path'].rsplit('/',1)[-1])
            changes.append(dict(map_id=row['map_id'],file_offset=hex(offset),
                before=before.hex(),after=after.hex(),source_path=row['source_path'],source_line=row['source_line']))
            if 'resolved_relative_offset' in row:
                changes[-1]['resolved_relative_offset']=hex(row['resolved_relative_offset'])
    return dict(format='alundra-editor-open-world-access-v1',changes=changes,
        source_commit=recipe['source_commit'],kept_inoa_maps=list(KEPT_INOA_MAPS),
        starting_state_requires_native_wrapper=True,dream_dungeon_mode=False,
        item_shuffle=False,gameplay_verified=False,hardware_verified=False,
        limitation='Source-matched route/cutscene recipes; independent playthrough and save checks not performed')
