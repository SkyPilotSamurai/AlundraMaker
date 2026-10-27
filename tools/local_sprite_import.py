"""Bounded, selective map-local sprite imports; no original assets overwritten.

Pinned format: xcasadio242b09a20ae1186c90278ba5f15f0f9a84104ef4,
DatasBin/SpriteRecord.cs, SiFrame.cs, SiImageSet.cs, SiImage.cs.
Only up to the largest observed five-page native map texture bank is used. Runtime safety
is not certified. Targets with local effects reserve every existing texture
page; only identical pages or appended pages may be used. Foreign entity
scripts are not imported.
"""
import struct
from map_block_repack import pointers,sections,replace_section
from map_loader_constraints import validate_layout
from texture_codec import unpack_ez,pack_ez
from entity_animation import parse_map_sprite_animations

MAX_PAGES=5
MAX_PALETTES=41


def layout(data,map_id):
    pp=pointers(data)
    if type(map_id) is not int or not 0<=map_id<2547:raise ValueError('Map outside native table')
    b=pp[map_id];h=sections(data[b:pp[map_id+1]]);s,e=b+h[3],b+h[4]
    sh=struct.unpack_from('<12I',data,s)
    if any(p<48 or s+p>e for p in sh):raise ValueError('Sprite-info roots outside section')
    return b,h,s,e,sh


def sprite_assets(data,map_id,sprite_id):
    """Enumerate every drawable frame, collision and portrait quad of a sprite."""
    from compile_yield import step; step()   # (the build warm-up steps aside)
    b,h,s,e,sh=layout(data,map_id)
    if type(sprite_id) is not int or not 0<=sprite_id<(sh[4]-sh[3])//4:
        raise ValueError('Sprite outside native local table')
    pointer=struct.unpack_from('<i',data,s+sh[3]+sprite_id*4)[0]
    if not 48<=pointer<=e-s-32:raise ValueError('Local sprite has no asset record')
    record=s+pointer;roots=struct.unpack_from('<4I',data,record)
    if any(p<pointer or p>e-s for p in roots):raise ValueError('Sprite asset root outside contiguous payload')
    animations=parse_map_sprite_animations(data,map_id,sprite_id)
    maximum=record+32;image_sets={0} # portrait lives at frame-table offset0
    for anim in animations:
        maximum=max(maximum,anim.offset+14)
        for stream in anim.streams:
            if stream is None:continue
            maximum=max(maximum,stream.offset+len(stream.frames)*5+len(stream.terminator))
            for frame in stream.frames:
                image_sets.add(frame.image_set_index*2)
                if frame.collision_raw!=-1:
                    at=s+roots[2]+frame.collision_raw
                    if not record<=at<=e-6:raise ValueError('Sprite collision outside payload')
                    maximum=max(maximum,at+6)
    quads=set()
    for relative in image_sets:
        at=s+roots[3]+relative
        if not record<=at<=e-2:raise ValueError('Image-set outside payload')
        count=data[at+1]
        if relative==0:count=max(1,count)
        if count>64 or at+2+count*14>e:raise ValueError('Image-set count outside payload')
        maximum=max(maximum,at+2+count*14)
        quads.update(at+2+i*14 for i in range(count))
    if maximum>e:raise ValueError('Asset payload exceeds section')
    return dict(record=record,relative=pointer,roots=roots,end=maximum,
                quads=sorted(quads),pages={data[q]&7 for q in quads},
                palettes={data[q+1] for q in quads})


# Original game maps the project saved a new blank map over (New Map over an
# unused map): like maps 483+, their old sprite slots/pages are free to reuse.
# Set by the event compiler from the project's created_maps list.
PROJECT_BLANK_MAPS=set()


def slots_in_use(data,map_id,keep=()):
    """Local sprite slots something on the map uses: placed records (templates included),
    `keep`, and the parts a placed boss's code creates (Melzas's doubles, orbs ...)."""
    from native_class_placement import record_cluster
    from content_database import ContentDatabase
    used={raw[6] for raw in record_cluster(data,map_id)['entities'] if raw[5]&128}|set(keep)
    for slot in list(used):
        used|={p-256 for p in ContentDatabase.BOSS_PARTS.get(slot+256,()) if 256<=p<512}
    return used


def spare_palettes(data,map_id,keep=()):
    """On a new map, palettes only the old map's unused sprites use (none elsewhere)."""
    if not (map_id>=483 or map_id in PROJECT_BLANK_MAPS):return []
    b,h,s,e,sh=layout(data,map_id);in_use=slots_in_use(data,map_id,keep);busy=set();idle=set()
    for i in range((sh[4]-sh[3])//4):
        if struct.unpack_from('<i',data,s+sh[3]+i*4)[0] in (0,-1):continue
        (busy if i in in_use else idle).update(sprite_assets(data,map_id,i)['palettes'])
    return sorted(idle-busy)


def import_local_sprite(data,target_map,donor_map,sprite_id,keep=(),target_slot=None):
    """Import one existing local identity without replacing target inhabitants.

    Slot identity is preserved for native balance/portrait lookup. The slot
    must be unused. Page allocation preserves every used target texture page;
    palettes are deduplicated or appended within the largest stock bound.
    """
    from compile_yield import step; step()   # (the build warm-up steps aside)
    slot_id=sprite_id if target_slot is None else target_slot   # a new enemy: the donor's art in its own slot
    if target_map==donor_map and slot_id==sprite_id:raise ValueError('Choose a different donor map')
    tb,th,ts,te,tsh=layout(data,target_map)
    db,dh,ds,de,dsh=layout(data,donor_map)
    if type(slot_id) is not int or not 0<=slot_id<(tsh[4]-tsh[3])//4:
        raise ValueError('Target sprite slot outside table')
    slot=ts+tsh[3]+slot_id*4
    # On the user's own new maps (483+), sprite slots and pages that no
    # character on the map uses are free to reuse (copied maps keep the
    # original map's sprite table even after its characters were removed).
    from native_class_placement import record_cluster as _cluster
    # keep: sprite slots this build still places on the map (events not yet
    # written): their pages must not be reused by a later import.
    in_use=slots_in_use(data,target_map,set(keep)-{slot_id})
    reuse=target_map>=483 or target_map in PROJECT_BLANK_MAPS   # also original maps blanked as new maps
    if struct.unpack_from('<i',data,slot)[0] not in (0,-1) and not (reuse and slot_id not in in_use) and target_slot is None:
        raise ValueError('Target class slot already contains an asset; preserve it')
    # Map-local effect animation formats differ from ordinary sprite records.
    has_effects=False
    for at in range(ts+tsh[4],ts+tsh[5],4):
        value=struct.unpack_from('<i',data,at)[0]
        if value==0:break
        if value!=-1:
            has_effects=True
    used=set()
    for i in range((tsh[4]-tsh[3])//4):
        p=struct.unpack_from('<i',data,ts+tsh[3]+i*4)[0]
        if reuse and i not in in_use:continue
        if p not in (0,-1):used.update(sprite_assets(data,target_map,i)['pages'])
    if reuse and not any(raw for raw in _cluster(data,target_map)['events']):
        has_effects=False   # effects are started by map scripts; none remain here
    donor=sprite_assets(data,donor_map,sprite_id)
    if any(p>=MAX_PAGES for p in used|donor['pages']):
        raise ValueError('Sprite exceeds largest observed five native texture-page bound')
    draw,_=unpack_ez(data[db+dh[4]:db+dh[5]],limit=262144)
    traw,_=unpack_ez(data[tb+th[4]:tb+th[5]],limit=262144)
    # Effects can reference pages absent from ordinary sprite quads. Keeping
    # ALL existing pages avoids guessing the opaque effect animation format.
    if has_effects:used.update(range((len(traw)+32767)//32768))
    if len(traw)>MAX_PAGES*32768 or len(draw)>MAX_PAGES*32768:
        raise ValueError('Texture bank exceeds observed native bound')
    page_map={}
    for old in sorted(donor['pages']):
        chunk=draw[old*32768:(old+1)*32768]
        if len(chunk)!=32768:raise ValueError('Donor texture page missing')
        identical=next((p for p in range(len(traw)//32768)
                        if traw[p*32768:(p+1)*32768]==chunk),None)
        if identical is not None:
            page_map[old]=identical
    available=[p for p in range(MAX_PAGES) if p not in used and p not in page_map.values()]
    for old in sorted(donor['pages']):
        if old in page_map:continue
        if available:page_map[old]=available.pop(0)
        else:raise ValueError('No free native sprite texture pages')
    needed=max([len(traw)]+[(page+1)*32768 for page in page_map.values()])
    traw=bytearray(traw+bytes(needed-len(traw)))
    for old,new in page_map.items():
        chunk=draw[old*32768:(old+1)*32768]
        if len(chunk)!=32768:raise ValueError('Donor texture page missing')
        traw[new*32768:(new+1)*32768]=chunk
    tcount=(tsh[6]-tsh[5])//32;dcount=(dsh[6]-dsh[5])//32
    tpad=bytes(data[ts+tsh[5]+32*tcount:ts+tsh[6]])
    dpad=bytes(data[ds+dsh[5]+32*dcount:ds+dsh[6]])
    if tpad!=bytes(4):
        raise ValueError('Unsupported target palette table terminator')
    if len(dpad)!=4:
        raise ValueError('Unsupported donor palette root bounds')
    # Eight stock donor maps have nonzero trailing four bytes. They are never
    # copied into the target: only explicitly referenced, bounded32-byte
    # palettes are imported, then the target's own zero trailer is retained.
    # This does not establish what a nonzero TARGET trailer means.
    palettes=[bytes(data[q:q+32]) for q in range(ts+tsh[5],ts+tsh[5]+32*tcount,32)]
    # On a new map, palettes only the old map's unused sprites use are free once the
    # 41-palette bound is reached (as their texture pages are, above; user 2026-10-26).
    spare=spare_palettes(data,target_map,set(keep)|{slot_id}) if reuse else []
    mapping={}
    for index in sorted(donor['palettes']):
        start=ds+dsh[5]+index*32
        if index>=dcount:raise ValueError('Donor palette outside native table')
        palette=bytes(data[start:start+32])
        if palette not in palettes:
            if len(palettes)>=MAX_PALETTES and spare:palettes[spare.pop(0)]=palette
            else:palettes.append(palette)
        mapping[index]=palettes.index(palette)
    if len(palettes)>MAX_PALETTES:raise ValueError('Palette count exceeds largest observed native bound')
    section=bytearray(data[ts:te]);section.extend(bytes((-len(section))%4))
    start=len(section);payload=bytearray(data[donor['record']:donor['end']])
    delta=start-donor['relative']
    struct.pack_into('<4I',payload,0,*[p+delta for p in donor['roots']])
    for q in donor['quads']:
        q-=donor['record'];payload[q]=(payload[q]&0xf8)|page_map[payload[q]&7]
        payload[q+1]=mapping[payload[q+1]]
    section.extend(payload);section.extend(bytes((-len(section))%4))
    roots=list(tsh);roots[5]=len(section);section.extend(b''.join(palettes)+tpad)
    # Relocate only the script/record cluster as a whole; its relative code
    # displacements and existing entity callbacks retain their original roots.
    shift=len(section)-tsh[6]
    section.extend(data[ts+tsh[6]:ts+tsh[0]])
    for i in range(6,12):roots[i]=tsh[i]+shift
    from native_class_placement import record_cluster
    cluster=record_cluster(data,target_map)
    roots[0]=len(section);section.extend(b''.join(cluster['entities'])+cluster['entity_terminator'])
    roots[1]=len(section);section.extend(cluster['effects'])
    roots[2]=len(section);section.extend(b''.join(cluster['events'])+bytes(4))
    section.extend(bytes((-len(section))%4));struct.pack_into('<12I',section,0,*roots)
    struct.pack_into('<I',section,tsh[3]+slot_id*4,start)
    page_head=bytes(data[tb+th[4]:tb+th[4]+6])   # read before data may change in place
    result=replace_section(data,target_map,3,section)
    base,h,_,_,_=layout(result,target_map)
    packed=pack_ez(bytes(traw),page_head);packed+=bytes((-len(packed))%4)
    result=replace_section(result,target_map,4,packed);validate_layout(result)
    imported=sprite_assets(result,target_map,slot_id)
    if imported['pages']!=set(page_map.values()):raise ValueError('Imported page remapping failed')
    return result,dict(target_map=target_map,donor_map=donor_map,sprite_id=slot_id,donor_sprite_id=sprite_id,
        page_mapping=page_map,palette_mapping=mapping,asset_bytes=len(payload),
        existing_target_assets_preserved=True,effect_pages_reserved=has_effects,gameplay_verified=False,
        limits=['Foreign entity scripts/story dependencies require authored replacements',
                'Effect pages are reserved without decoding effects','Largest stock five-page/41-palette bounds'])


def imported_actor_record(data,import_report,donor_entity_index,x,y,height=None,*,
                          programs=None,contents=None):
    """Build an authored entity after a successful selective import.

    The report identifies the actual imported class/slot/donor. Clear source
    scripts and collection flags; the imported sprite's own built-in native
    callbacks and portrait identity survive. Call after art imports and process
    allocation, before appending final native record lists.
    """
    if not isinstance(import_report,dict) or not import_report.get('existing_target_assets_preserved'):
        raise ValueError('Successful native sprite import report required')
    target,donor,sid=[import_report[k] for k in ('target_map','donor_map','sprite_id')]
    from native_class_placement import donor_record
    row=bytearray(donor_record(data,donor,donor_entity_index,x,y,height,
                              programs=programs,contents=contents))
    if not row[5]&128 or row[6]!=import_report.get('donor_sprite_id',sid):raise ValueError('Donor entity differs from imported local class')
    row[6]=sid   # a new enemy uses its own slot
    sprite_assets(data,target,sid)
    b,h,s,e,sh=layout(data,target);width,tall=data[b+h[1]:b+h[1]+2]
    if not 0<=x<width or not 0<=y<tall:raise ValueError('Actor outside target tile grid')
    row[:4]=bytes((0,0,width-1,tall-1));row[4]=1;row[5]=(row[5]&3)|0xc0
    row[10:18]=bytes(8)
    if programs:
        for key,value in programs.items():row[10+'ABCDEF'.index(key)]=value
    return bytes(row)
