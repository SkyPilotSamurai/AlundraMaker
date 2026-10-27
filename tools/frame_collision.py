"""Bounded six-byte animation-frame collision editing, global and map-local.

Format and 16.16 conversion are source-reported at xcasadio commit
242b09a20ae1186c90278ba5f15f0f9a84104ef4, DatasBin/FrameCollisionData.cs
and Gameplay/EntityManager.cs322-328. This is not independent native/runtime
verification, nor a claim every frame box is an offensive attack hitbox.
"""
from dataclasses import dataclass
import struct
from entity_animation import parse_sprite_animation_record


@dataclass(frozen=True)
class FrameHitbox:
    offset:int
    offset_x:int
    offset_y:int
    offset_z:int
    width:int
    depth:int
    height:int
    raw:bytes
    references:tuple

    @property
    def values(self):
        return (self.offset_x,self.offset_y,self.offset_z,self.width,self.depth,self.height)

    @property
    def projected_corners(self):
        """Simple entity-origin-relative X/(Y-Z) wireframe, native raw units."""
        x,y,z,w,d,h=self.values
        return tuple((x+dx,y+dy-z-dz) for dz in (0,h) for dy in (0,d) for dx in (0,w))


def sprite_context(data,map_id,catalogue_index):
    if type(catalogue_index) is not int or not 0<=catalogue_index<512:
        raise ValueError('Catalogue index outside native two-bank identity')
    if catalogue_index<256:
        start,end=struct.unpack_from('<2I',data)
    else:
        from local_sprite_import import layout
        _,_,start,end,_=layout(data,map_id)
    if not 0<=start<=start+48<=end<=len(data):raise ValueError('Invalid sprite-info bounds')
    header=struct.unpack_from('<12I',data,start)
    sprite_id=catalogue_index&255
    table,stop=header[3:5]
    if not 48<=table<=stop<=end-start or (stop-table)%4:
        raise ValueError('Invalid sprite table bounds')
    if sprite_id>=(stop-table)//4:raise ValueError('Sprite slot outside native table')
    record=struct.unpack_from('<i',data,start+table+sprite_id*4)[0]
    if not 48<=record<=end-start-32:raise ValueError('Sprite has no native record')
    _,_,collision,images=struct.unpack_from('<4I',data,start+record)
    if not record<=collision<=images<=end-start:
        raise ValueError('Unsupported bounded collision/image table order')
    animations=parse_sprite_animation_record(data,start,end,sprite_id,table,stop)
    return start,end,collision,images,animations


def frame_hitboxes(data,map_id,catalogue_index):
    """Return unique referenced boxes with ALL shared animation-frame aliases."""
    start,end,collision,images,animations=sprite_context(data,map_id,catalogue_index)
    aliases={}
    for anim in animations:
        for direction,stream in enumerate(anim.streams):
            if stream is None:continue
            for frame_index,frame in enumerate(stream.frames):
                relative=frame.collision_raw
                if relative==-1:continue
                at=start+collision+relative
                if relative<0 or not start+collision<=at<=start+images-6:
                    raise ValueError('Frame collision reference outside collision table')
                aliases.setdefault(at,[]).append((anim.index,direction,frame_index))
    result=[]
    for at,references in sorted(aliases.items()):
        raw=bytes(data[at:at+6]);values=struct.unpack('<3b3B',raw)
        result.append(FrameHitbox(at,*values,raw,tuple(references)))
    return result


def prepare_collision_edit(data,box,values):
    """Prepare one in-place edit. Shared aliases deliberately remain shared."""
    if not isinstance(box,FrameHitbox):raise ValueError('Parsed native frame hitbox required')
    if not 0<=box.offset<=len(data)-6 or bytes(data[box.offset:box.offset+6])!=box.raw:
        raise ValueError('Stale hitbox: reload before applying changes')
    if len(values)!=6 or any(type(v) is not int for v in values):
        raise ValueError('Hitbox requires six integer fields')
    if any(not -128<=v<=127 for v in values[:3]):raise ValueError('XYZ offsets use signed byte range-128..127')
    if any(not 0<=v<=255 for v in values[3:]):raise ValueError('XYZ sizes use unsigned byte range0..255')
    replacement=struct.pack('<3b3B',*values)
    if replacement==box.raw:return None
    return box.offset,replacement,'Animation frame collision XYZ (shared native box)'


def edit_collision(session,box,values):
    """Apply through the existing undoable session; no allocation/pointer edits."""
    change=prepare_collision_edit(session.data,box,values)
    if change is not None:session.replace(*change)
    return change is not None
