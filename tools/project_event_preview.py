"""Native-size world graphics for newly authored events; never a dialogue face."""
from database_catalogue import preview_hue
from stock_donors import source_for, stock_view

def event_world_image(session,definition,map_id,facing=None):
    if session is None or definition is None:return None
    from native_class_placement import class_preview
    source=definition.get('source',{});catalogue=source.get('catalogue_index')
    if source.get('variant')=='warp_panel':   # Warp Panel: the 2x2 panel, its event tile the bottom-left
        from heal_tile import preview
        return preview(stock_view(session),'panel')
    if source.get('variant')=='save_portal':   # Save Room Portal: panel + swirl, its event tile the bottom-left
        from save_portal import preview
        return preview(stock_view(session))
    if source.get('variant')=='block_switch':   # Block Switch: the orb
        from block_switch import preview
        return preview(session)
    if source.get('variant')=='floor_switch':   # Step On Switch (Floor): the switch's top on the tile
        from heal_tile import preview
        return preview(stock_view(session),'switch')
    if source.get('variant')=='heal_tile':   # Healing Tile: the save room's floor plate
        from heal_tile import preview
        return preview(stock_view(session),source.get('heal_tile'))
    if type(catalogue) is not int:return None
    if source.get('variant')=='pattern_static' or source.get('fixed_donor'):facing=source.get('default_facing',facing)   # symbol / colour of the entry
    elif facing is None and source.get('default_facing'):facing=source['default_facing']
    maps=list(dict.fromkeys([map_id]+source.get('observed_maps',[])))
    for candidate in maps:
        try:
            src=session if candidate==map_id else source_for(session,candidate)   # other maps: the original game's copy
            preview=class_preview(src,candidate,catalogue) if facing is None else class_preview(src,candidate,catalogue,{"down":0,"up":1,"left":2,"right":3}[facing])
        except (ValueError,IndexError,KeyError):continue
        if preview is None:continue
        image=preview[0].convert('RGBA');bounds=image.getbbox()
        if bounds is None:continue
        if source.get('variant')=='flush_top':   # flush switch: only the lit top, on the tile
            image=image.crop(bounds);image=image.crop((0,0,image.width,min(16,image.height)));bounds=image.getbbox() or (0,0,1,1)
        return preview_hue(image.crop(bounds),definition)
    return None

WIDE = 40   # sprites at least this wide (about 2 tiles) start at the tile's left edge


def wide_shift(image):
    """Half-tile steps a wide sprite is moved right so it starts at the left of its tile."""
    return 1 if image is not None and image.width >= WIDE else 0


def anchor_world_image(image,x,y,margin=0,offset_x=0,offset_y=0):
    """Centre over the placement tile (a wide sprite starts at its left edge),
    with the sprite bottom at tile bottom; offsets are half-tile steps."""
    shift=wide_shift(image)+offset_x
    return x*24+12+shift*12-image.width/2,(y+1)*16+margin-image.height+offset_y*8
