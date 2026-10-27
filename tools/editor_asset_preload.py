"""Eager editor asset loading, with progress; missing maps do not abort others."""
import struct
from entity_preview import cached_preview
from database_catalogue import reference_image,portrait_image
from event_editor import script_roots,instructions
from map_text import entries

def preload_plan(session,database):
    """Every preload step as (group, label, action): group is 'global',
    ('map', id) or 'class'. Each action only fills caches; none touches Tk."""
    def bank(map_id,global_bank=False):
        decoder=cached_preview(session,map_id,global_bank)
        from texture_codec import unpack_ez
        if decoder.raw is None:
            decoder.raw=unpack_ez(bytes(session.data[decoder.sheet_start:decoder.sheet_end]),limit=262144)[0]
        table,stop=decoder.header[3:5]
        for sprite in range(min(256,(stop-table)//4)):
            for direction in range(4):decoder.frame(sprite,direction)
            decoder.portrait(sprite)
            from entity_animation import parse_sprite_animation_record
            try:
                sets=parse_sprite_animation_record(session.data,decoder.start,decoder.end,sprite,table,stop)
                if not hasattr(decoder,'animation_sets'):decoder.animation_sets={}
                decoder.animation_sets[sprite]=sets
                frames={frame.image_set_index for aset in sets for stream in aset.streams if stream is not None for frame in stream.frames}
                for frame in frames:
                    try:decoder.image_set(sprite,frame)
                    except (ValueError,IndexError,struct.error):pass
            except (ValueError,IndexError,struct.error):pass
    def scripts(m):
        for key in script_roots(session,m):instructions(session,m,key)
    from bush_catalogue import cached_bush_styles
    plan=[('global','Global sprites',lambda:bank(0,True)),('global','Global dialogue',lambda:entries(session,None))]
    # the project's own maps (483 and up) first: they are the ones being edited
    from map_slots import map_count
    try:count=map_count(session.data)
    except Exception:count=483
    document=getattr(database,'document',None) or {}
    definitions={row.get('id'):row for row in document.get('definitions',[]) if isinstance(row,dict)}
    placed={}
    for graph in document.get('event_graphs',[]) or []:
        if not isinstance(graph,dict):continue
        for page in graph.get('pages',[]) or []:
            klass=definitions.get(page.get('class_id',graph.get('class_id')))
            if klass is not None:
                placed.setdefault(graph.get('map_id'),[]).append((klass,(graph.get('native_placement') or {}).get('facing')))
    def previews(m):
        # pictures of the events placed on map m, as the map view draws them
        from project_event_preview import event_world_image
        for klass,facing in placed.get(m,[]):
            try:event_world_image(session,klass,m,facing)
            except (ValueError,IndexError,KeyError,struct.error):pass
    for map_id in list(range(483,count))+list(range(483)):
        group=('map',map_id)
        plan+=[(group,f'Map {map_id} textures',lambda m=map_id:session.texture(m)),
               (group,f'Map {map_id} sprites',lambda m=map_id:bank(m)),
               (group,f'Map {map_id} scripts',lambda m=map_id:scripts(m)),
               (group,f'Map {map_id} dialogue',lambda m=map_id:entries(session,m))]
        if placed.get(map_id):plan.append((group,f'Map {map_id} events',lambda m=map_id:previews(m)))
    for row in list(database.definitions):
        plan+=[('class',row['name'],lambda r=row:reference_image(session,r)),
               ('class',row['name']+' portrait',lambda r=row:portrait_image(session,r))]
    plan.append(('bushes','Bush pictures',lambda:cached_bush_styles(session)))   # last: tile picker Bushes tab
    return plan

def preload_editor_assets(session,database,progress=lambda done,total,label:None):
    """Load everything now (scripts and tests; the editor loads in the background)."""
    session._full_asset_preload=True
    plan=preload_plan(session,database);errors=[]
    for done,(group,label,action) in enumerate(plan,1):
        try:action()
        except (ValueError,IndexError,KeyError,struct.error) as exc:errors.append({'asset':label,'error':str(exc)})
        progress(done,len(plan),label)
    result={'processed':len(plan),'total':len(plan),'errors':errors}
    session.asset_preload_result=result
    return result
