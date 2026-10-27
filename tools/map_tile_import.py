"""Exact-colour, fixed-capacity native tile imports; no guessed asset relocation."""
from copy import deepcopy
import struct
from area_map import grid
from texture_codec import pack_ez,pack_ez_fit,unpack_ez

def tile_bytes(raw,index):
    if not 0<=index<960:raise ValueError('Unsupported native tile index')
    x=index%10*12;y=index//10*16
    if (y+15)*128+x+12>len(raw):raise ValueError('Tile outside texture')
    return bytes(b for row in range(16) for b in raw[(y+row)*128+x:(y+row)*128+x+12])

def write_tile(raw,index,pixels):
    x=index%10*12;y=index//10*16
    for row in range(16):raw[(y+row)*128+x:(y+row)*128+x+12]=pixels[row*12:row*12+12]

def convert_pixels(pixels,source_words,target_words):
    used={b&15 for b in pixels}|{b>>4 for b in pixels}
    if any(source_words[i] not in target_words for i in used):return None
    mapping={i:target_words.index(source_words[i]) for i in used}
    return bytes(mapping[b&15]|mapping[b>>4]<<4 for b in pixels)

def _rgb(word):
    return (word&31,(word>>5)&31,(word>>10)&31)

def nearest_conversion(pixels,source_words,palettes):
    """When no palette holds the exact colours and none is free: recolour the
    tile into the existing palette that matches it best (closest colour per
    index; transparent stays transparent). Returns (palette, pixels)."""
    used={b&15 for b in pixels}|{b>>4 for b in pixels}
    best=None
    for p,target_words in enumerate(palettes):
        mapping={};cost=0
        for i in used:
            word=source_words[i]
            if word==0:   # transparent
                candidates=[j for j,w in enumerate(target_words) if w==0] or [0]
                mapping[i]=candidates[0];continue
            r,g,b=_rgb(word)
            j=min((j for j,w in enumerate(target_words) if w!=0),default=0,
                  key=lambda j:sum((x-y)**2 for x,y in zip((r,g,b),_rgb(target_words[j]))))
            mapping[i]=j;cost+=sum((x-y)**2 for x,y in zip((r,g,b),_rgb(target_words[j])))
        if best is None or cost<best[0]:best=(cost,p,mapping)
    _,p,mapping=best
    return p,bytes(mapping[b&15]|mapping[b>>4]<<4 for b in pixels)

def import_tiles(session,database,target,source,codes,erase_unused=False,defer=False,original=False,keep_codes=()):
    """Import a selected brush batch atomically, or fail without changing data.
    defer: the new tile pixels wait in session.defer_texture (drawn at once,
    compressed into the game data later by flush_texture); compressing a map
    texture takes seconds, so the editor does it in the background."""
    codes=list(dict.fromkeys(codes))
    if target==source:return {code:code for code in codes}
    # original: a picture of the original game (bushes, water, map objects): read
    # from the original map, whatever the project did to that map
    from stock_donors import source_for
    src=source_for(session,source) if original else session
    source_raw=src.texture(source)[0];target_raw,start,end=session.texture(target)
    raw=bytearray(target_raw);palettes=[session.palette(target,p)[0] for p in range(16)]
    _,_,cells=grid(session,target)
    # keep_codes: tiles painted but not written into the map yet - their art is in use
    existing=[c['values'][4] for c in cells]+[w[1] for c in cells for w in c['walls']]+list(keep_codes)
    used_tiles={code&1023 for code in existing if code!=65535}
    used_palettes={(code>>12)&15 for code in existing if code!=65535}
    tiles=[tile_bytes(raw,i) for i in range(960)]
    # Preserve every nonblank native texture, including ones not used by a cell.
    animated=animated_pages(session,target)   # water/lava pages: their unused slots are animation frames
    free_tiles=[i for i,tile in enumerate(tiles) if i not in used_tiles and not any(tile) and i//160 not in animated]
    erased_doc=database.document.setdefault('erased_tile_art',{}).setdefault(str(target),{}) if database is not None else {}
    free_tiles.sort(key=lambda i:str(i) in erased_doc)   # slots whose old picture can still be put back: last
    if erase_unused:
        # User-approved: erase tile art this map never places, to make room.
        # Some may be swapped in by in-game map changes (not decoded).
        for i,tile in enumerate(tiles):
            if i not in used_tiles and any(tile) and i//160 not in animated:
                erased_doc[str(i)]=tile.hex()   # kept in the mod: the picker still shows it, using it puts it back
                tiles[i]=bytes(len(tile));write_tile(raw,i,tiles[i]);free_tiles.append(i)
        free_tiles.sort(key=lambda i:(str(i) in erased_doc,i))
    # Palette slots unused by all current floor/wall records can be assigned to
    # imported artwork. Dynamic native map-copy/animation usage is not decoded.
    free_palettes=[p for p in range(16) if p not in used_palettes]
    changes={};result={}
    for code in codes:
        if code==65535:result[code]=code;continue
        pixels=tile_bytes(source_raw,code&1023);words=src.palette(source,(code>>12)&15)[0]
        converted=None
        for p,target_words in enumerate(palettes):
            converted=convert_pixels(pixels,words,target_words)
            if converted is not None:break
        if converted is None:
            if free_palettes:
                p=free_palettes.pop(0);palettes[p]=words;converted=pixels
                changes[session.palette(target,p)[1]]=struct.pack('<16H',*words)
            else:
                # All 16 palettes are in use: closest colours from the best palette.
                p,converted=nearest_conversion(pixels,words,palettes)
        try:tile=tiles.index(converted)
        except ValueError:
            if not free_tiles:raise ValueError('No unused blank native tile slots remain on this map.')
            tile=free_tiles.pop(0);tiles[tile]=converted;write_tile(raw,tile,converted)
            erased_doc.pop(str(tile),None)   # its old picture is gone for good now
        if tile in free_tiles:free_tiles.remove(tile)
        if p in free_palettes:free_palettes.remove(p)
        result[code]=(code&0x0C00)|tile|(p<<12)
    if raw!=target_raw and defer:
        for offset,payload in changes.items():session.defer_palette(offset,payload)   # written with the texture
        session.defer_texture(target,bytes(raw))
        return result
    if raw!=target_raw:
        store_texture(session,database,target,bytes(raw),changes)
    elif changes:
        session.replace_document(database.document,dict(database.document),'Import foreign map tiles',tuple(changes.items()))
    return result


def store_texture(session,database,target,raw,changes=None,packed=None):
    """Compress texture `raw` into map `target` (one undo step), reusing zero
    padding of the same map block when it is larger than the old texture.
    changes: other byte changes (palettes) stored in the same step."""
    changes=dict(changes or {})
    _,start,end=session.texture(target)
    if packed is None:
        packed=pack_ez_fit(bytes(raw),bytes(session.data[start:start+6]),end-start)
    if unpack_ez(packed)[0]!=raw:raise ValueError('Imported tile texture failed round-trip validation')
    if len(packed)>end-start:
        # Reuse verified zero tail padding inside this SAME map block.
        # Neither the outer map offsets nor its loader allocation grow.
        from map_block_repack import pointers,sections
        pp=pointers(session.data);base,limit=pp[target:target+2]
        block=bytes(session.data[base:limit]);h=sections(block)
        replacement=packed+bytes((-len(packed))%4);delta=len(replacement)-(h[3]-h[2])
        if delta>len(block)-h[6]-16 or any(block[-(delta+16):]):
            raise ValueError(f'This map has insufficient texture/padding space ({len(packed)} bytes needed; {end-start} texture bytes available). No tiles were imported.')
        changed=bytearray(block[:h[2]]+replacement+block[h[3]:len(block)-delta])
        shifted=[v+(delta if i>2 else 0) for i,v in enumerate(h)]
        struct.pack_into('<7I',changed,0,*shifted);changed.extend(bytes(len(block)-len(changed)))
        sections(changed)
        # Palette positions are in section0, before the relocated texture.
        for offset,payload in changes.items():changed[offset-base:offset-base+len(payload)]=payload
        changes={base:bytes(changed)}
    else:changes[start]=packed+bytes(end-start-len(packed))
    # (a shallow copy: the database document itself does not change)
    session.replace_document(database.document,dict(database.document),'Import foreign map tiles',tuple(changes.items()))


def animated_pages(session,m):
    """Tile pages (160 tiles each) the game animates on map m (map info +0x420, 6 pairs
    {frames log2, ticks}; remake_tile_anims.py). Their unused-looking tiles are frames."""
    try:
        base,h=session.layout(m);i=base+h[0]+0x420;d=session.data
        return {p for p in range(6) if d[i+2*p] and d[i+2*p+1]}
    except Exception:
        return set(range(6))   # unknown: protect every page


def make_room(session,m,raw,keep=()):
    """raw (a waiting texture of map m) with the art of every tile the map never places
    erased (blank tiles compress to almost nothing). Animated pages and `keep` (tiles
    just put back for painting) are kept. Returns (raw, {tile index: art hex})."""
    _,_,cells=grid(session,m)
    used={code&1023 for c in cells for code in [c['values'][4]]+[w[1] for w in c['walls']] if code!=65535}|set(keep)
    animated=animated_pages(session,m);raw=bytearray(raw);erased={}
    for i in range(960):
        if i in used or i//160 in animated:continue
        t=tile_bytes(raw,i)
        if any(t):erased[str(i)]=t.hex();write_tile(raw,i,bytes(len(t)))
    return bytes(raw),erased


def flush_texture(session,database,m,packed=None):
    """Write map m's waiting imported texture into the game data (one undo step)."""
    pending=getattr(session,'_pending_textures',{})
    raw=pending.get(m)
    if raw is None:return False
    del pending[m]
    base,h=session.layout(m);first,last=base+h[0],base+h[0]+16+32*32
    palettes={o:p for o,p in getattr(session,'_pending_palettes',{}).items() if first<=o<last}
    for o in palettes:session._pending_palettes.pop(o,None)
    try:store_texture(session,database,m,raw,changes=palettes,packed=packed)
    except ValueError as error:
        if 'padding space' not in str(error):
            pending[m]=raw;getattr(session,'_pending_palettes',{}).update(palettes);raise
        # Too big: make room by erasing tile art the map never places, then once more
        # (user 2026-10-25: always make the room, never stop the editor).
        roomy,erased=make_room(session,m,raw,keep=getattr(session,'restored_tiles',{}).get(m,()))
        try:store_texture(session,database,m,roomy,changes=palettes)
        except Exception:
            pending[m]=raw;getattr(session,'_pending_palettes',{}).update(palettes);raise
        # the erased pictures are kept in the mod: the tile picker still shows them and
        # using one puts it back (user 2026-10-25: 'adjust after the fact')
        if database is not None and erased:
            database.document.setdefault('erased_tile_art',{}).setdefault(str(m),{}).update(erased)
        session.made_room=getattr(session,'made_room',0)+len(erased)
    except Exception:
        pending[m]=raw;getattr(session,'_pending_palettes',{}).update(palettes);raise
    return True


def flush_textures(session,database):
    for m in list(getattr(session,'_pending_textures',{})):flush_texture(session,database,m)
