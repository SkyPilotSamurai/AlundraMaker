"""Same-native-ID palette forks: one map's class changes, shared art preserved.

This does not separate two instances of the same native class. No AI/balance
ID changes, no global palette edits and no texture-page allocation.
"""
import colorsys
import hashlib
import struct
from local_sprite_import import layout,sprite_assets,MAX_PALETTES,MAX_PAGES
from map_block_repack import replace_section
from map_loader_constraints import validate_layout
from native_class_placement import record_cluster


def shift_hue(words,degrees,saturation=100):
    """Hue rotation (degrees) and saturation (percent, 100 = unchanged) for
    RGB555 colours, preserving transparency/STP."""
    if not isinstance(degrees,(int,float)) or isinstance(degrees,bool):
        raise ValueError('Hue rotation must be numeric degrees')
    if not -360<=degrees<=360:raise ValueError('Hue rotation must be-360..360 degrees')
    if not isinstance(saturation,(int,float)) or isinstance(saturation,bool) or not 0<=saturation<=200:
        raise ValueError('Saturation must be 0..200 percent')
    if len(words)!=16 or any(type(w) is not int or not 0<=w<=65535 for w in words):
        raise ValueError('Native palette requires16 unsigned halfwords')
    result=[]
    for word in words:
        rgb=((word&31)/31,((word>>5)&31)/31,((word>>10)&31)/31)
        h,s,v=colorsys.rgb_to_hsv(*rgb)
        rr,gg,bb=colorsys.hsv_to_rgb((h+degrees/360)%1,min(1.0,s*saturation/100),v)
        result.append((word&0x8000)|round(rr*31)|(round(gg*31)<<5)|(round(bb*31)<<10))
    return tuple(result)


def recolor_local_class(data,map_id,catalogue_index,degrees,saturation=100):
    """Return a palette-forked DATAS plus explicit native scope report."""
    return recolor_local_classes(data,map_id,[catalogue_index],degrees,saturation)


def _other_palettes(data,map_id,sids):
    """Palette indices used by every other sprite of this map's table, or None when one
    of them cannot be read (then nothing is changed in place)."""
    b,h,s,e,sh=layout(data,map_id);used=set()
    for i in range((sh[4]-sh[3])//4):
        if i in sids or struct.unpack_from('<i',data,s+sh[3]+4*i)[0] in (0,-1):continue
        try:used|=sprite_assets(data,map_id,i)['palettes']
        except Exception:return None
    return used


def recolor_local_classes(data,map_id,catalogues,degrees,saturation=100):
    """Recolour several classes of one map together (a boss and the parts of its fight
    that look like it). A palette only these classes use is changed in place; one
    another sprite also uses is forked, so that sprite keeps its colours (2026-10-21:
    forking every palette ran past the 41-palette bound for Melzas)."""
    from compile_yield import step; step()   # (the build warm-up steps aside)
    catalogues=list(dict.fromkeys(catalogues))
    if not catalogues or any(type(c) is not int or not 256<=c<512 for c in catalogues):
        raise ValueError('Palette forks currently support map-local classes256..511')
    b,h,s,e,sh=layout(data,map_id)
    assets=[(c,sprite_assets(data,map_id,c&255)) for c in catalogues]
    from texture_codec import unpack_ez
    raw,_=unpack_ez(data[b+h[4]:b+h[5]],limit=262144)
    if len(raw)>MAX_PAGES*32768 or any(page>=MAX_PAGES for _,asset in assets for page in asset['pages']):
        raise ValueError('Sprite exceeds largest stock five texture-page bound')
    count=(sh[6]-sh[5])//32
    pad=bytes(data[s+sh[5]+count*32:s+sh[6]])
    if pad!=bytes(4):raise ValueError('Unsupported native palette table terminator')
    palettes=[bytes(data[s+sh[5]+i*32:s+sh[5]+(i+1)*32]) for i in range(count)]
    shared=_other_palettes(data,map_id,{c&255 for c in catalogues})
    from local_sprite_import import spare_palettes
    spare=[i for i in spare_palettes(data,map_id,{c&255 for c in catalogues}) if i not in set().union(*(a['palettes'] for _,a in assets))]
    mapping={}
    for index in sorted(set().union(*(asset['palettes'] for _,asset in assets))):
        if index>=count:raise ValueError('Class palette reference outside native table')
        words=struct.unpack('<16H',palettes[index]);changed=struct.pack('<16H',*shift_hue(words,degrees,saturation))
        if shared is not None and index not in shared:
            palettes[index]=changed;mapping[index]=index   # only these classes use it
            continue
        if changed not in palettes:
            if len(palettes)>=MAX_PALETTES and spare:palettes[spare.pop(0)]=changed   # new map: a leftover sprite's palette
            else:palettes.append(changed)
        mapping[index]=palettes.index(changed)
    if len(palettes)>MAX_PALETTES:raise ValueError('Palette fork exceeds largest stock41 palette bound')
    section=bytearray(data[s:e]);section.extend(bytes((-len(section))%4))
    targets=[]
    for catalogue,asset in assets:
        target=len(section);payload=bytearray(data[asset['record']:asset['end']])
        delta=target-asset['relative']
        struct.pack_into('<4I',payload,0,*[root+delta for root in asset['roots']])
        for quad in asset['quads']:
            pos=quad-asset['record'];payload[pos+1]=mapping[payload[pos+1]]
        section.extend(payload);section.extend(bytes((-len(section))%4));targets.append((catalogue,target))
    roots=list(sh);roots[5]=len(section);section.extend(b''.join(palettes)+pad)
    shift=len(section)-sh[6]
    section.extend(data[s+sh[6]:s+sh[0]])
    for i in range(6,12):roots[i]=sh[i]+shift
    cluster=record_cluster(data,map_id)
    roots[0]=len(section);section.extend(b''.join(cluster['entities'])+cluster['entity_terminator'])
    roots[1]=len(section);section.extend(cluster['effects'])
    roots[2]=len(section);section.extend(b''.join(cluster['events'])+bytes(4))
    section.extend(bytes((-len(section))%4));struct.pack_into('<12I',section,0,*roots)
    for catalogue,target in targets:struct.pack_into('<I',section,sh[3]+(catalogue&255)*4,target)
    result=replace_section(data,map_id,3,section);validate_layout(result)
    return result,dict(map_id=map_id,catalogue_index=catalogues[0],catalogues=catalogues,hue_degrees=degrees,saturation_percent=saturation,
        palette_mapping=mapping,native_identity_preserved=True,texture_bytes_unchanged=True,
        scope='All instances of these native classes on this map',
        independent_instance_clone=False,gameplay_verified=False,
        base_sha256=hashlib.sha256(data).hexdigest(),result_sha256=hashlib.sha256(result).hexdigest())
