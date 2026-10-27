"""Build-snapshot QoL patches; retail sources are never overwritten.

Low-RAM code also requires relocation of the game's descending native stack.
Individual dated runtime evidence does not certify every composed editor patch
or hardware compatibility.
"""
import hashlib
import json
import struct
from pathlib import Path
from native_lr_swaps import emit_wrapper,validate,offset,manifest,HOOK,MENU_MASK
from project_state_runtime import STOCK_SHA

ROOT=Path(__file__).resolve().parents[1]
# Fast loading (2026-10-12): the map-transition fades are timed in frames by
# the immediate passed to the fade starter 0x80043944 (out: effects 0-3,
# in: 0x80044FB8). The fade-to-black waits are shortened to a quarter; the long
# story fades (100/180/300 frames) are left alone. (address, stock word, new frames)
MEIA_DASH_CHECK=0x8003257C  # MovePlayer: andi v0,v0,0x10 (Triangle held) before PrepareSprint (0x29)
FAST_FADE_SITES=((0x80043CF0,16),(0x80043D54,16),(0x80043F94,80),(0x80044090,30),(0x8004511C,8),(0x80045220,60))
# Text blip played once per glyph (0x80047DB0 jal 0x8004A128). With instant text a
# whole page of blips would be issued in one frame, so it is skipped.
TEXT_BLIP_CALL=(0x80047DB0,0x0C01284A)
INSTANT_BLOCK_SHA256={'gate_words':'c4cca89f003c011d078a3aee394a46ee1d772916f8ce2c3a6572f6ce42d19beb',
 'wrapper_words':'cd50127115865b91d6e8d8737490d88d954437c153fa5d0446965e1c7412fa41'}


def _stock():
    path=ROOT/'private-inputs/disc/ALUN_CD.EXE'
    if not path.exists():raise ValueError('QoL patch verification needs the local original US1.1 executable')
    stock=path.read_bytes()
    if hashlib.sha256(stock).hexdigest()!=STOCK_SHA:raise ValueError('QoL reference executable fingerprint differs from US1.1')
    return stock


def apply_qol(session,source_exe):
    options=(getattr(session,'content_database',None) or {}).get('mod_options',{})
    requested={key:options.get(key,False) for key in ('skip_intro','lr_swaps','instant_text','open_world','remove_cutscenes')}
    starting_equipment=options.get('starting_equipment')
    starting_stats=options.get('starting_stats')
    if options.get('start_as_meia'):
        # Start as Meia: her own Player entry in the database holds her starting
        # equipment and stats (user 2026-10-18); Alundra's are used for what she leaves unset.
        meia=next((d for d in (getattr(session,'content_database',None) or {}).get('definitions',[])
                   if isinstance(d,dict) and d.get('source',{}).get('player_slot')=='meia'),None)
        data=(meia or {}).get('data',{})
        # Meia never takes Alundra's choices (user 2026-10-18): blank means her own defaults.
        from starting_equipment import DEFAULT_START
        starting_equipment=list(data.get('starting_equipment') or DEFAULT_START)
        starting_stats=data.get('starting_stats') or None
    if starting_equipment is None:
        # Default (user 2026-10-18): Alundra and Meia start with the Dagger and Cloth Armor,
        # plus whatever the game itself gives at the start.
        from starting_equipment import native_start, DEFAULT_START
        try:native=native_start(bytes(source_exe))
        except Exception:native=[]
        starting_equipment=sorted(set(native)|set(DEFAULT_START))
    start_point=options.get('start_point')
    if any(type(value) is not bool for value in requested.values()):raise ValueError('Mod options must be checkboxes')
    confirm_report=None
    if options.get('confirm_square') is True:
        # Confirm button: Square (JP) -- menu confirm tests 0x40 -> 0x80 (confirm_button_swap.py)
        from confirm_button_swap import patch_alun
        source_exe,confirm_report=patch_alun(source_exe)
    if requested['open_world'] or requested['remove_cutscenes'] or start_point is not None:requested['skip_intro']=True
    report={'format':'alundra-editor-qol-v1','options':requested,'patches':[],
            'emulator_verified':False,'hardware_verified':False}
    if confirm_report:report['patches'].append({'feature':'confirm_square','sites':confirm_report})
    if start_point is not None:
        from editor_start_point import resolve_start_point
        start_point=resolve_start_point(session,start_point)
        report['start_point']=start_point
    from map_slots import extra_count
    extra_maps=extra_count(getattr(session,'data',b'')) if len(getattr(session,'data',b''))>=0x800 else 0
    from native_animation_spawns import rules_from_database
    spawn_rules=rules_from_database(getattr(session,'content_database',None))
    no_dash=bool(options.get('start_as_meia')) and not options.get('meia_alundra_fallback')
    # A map with a boss uses the boss's home sound set (maps 483+: in the new-map tables below)
    import extra_maps_runtime as _emr
    _music,_sfx=_emr.stock_tables(source_exe,offset)
    boss_banks=_emr.boss_sound_banks(getattr(session,'content_database',None),_sfx)
    if _emr.SOUND_SET_CONFLICTS:report['boss_sound_set_conflicts']=list(_emr.SOUND_SET_CONFLICTS)
    import magic_placement as _mp
    placement=_mp.settings((getattr(session,'content_database',None) or {}).get('definitions',[]))
    import magic_spawns as _ms
    import custom_consume as _cc
    import play_movie as _pm
    _movie_used=_pm.used(getattr(session,'content_database',None))
    consume=_cc.settings((getattr(session,'content_database',None) or {}).get('definitions',[]))
    if not consume and not placement and not _ms.needs_water_stub((getattr(session,'content_database',None) or {}).get('definitions',[])) and not any(requested.values()) and not options.get('instant_boot_plus') and not options.get('fast_loading') and not options.get('fast_loads') and starting_equipment is None and starting_stats is None and start_point is None and not extra_maps and not spawn_rules and not no_dash and not boss_banks and options.get('elemental_bombs') is not True and options.get('magic_weapon_swap') is not True and options.get('regular_item_sounds') is not True and options.get('boss_hp_hud') is not True and not _movie_used:return bytes(source_exe),report
    stock=_stock();exe=bytearray(source_exe);blocks=[]
    if boss_banks and not extra_maps:   # stock maps only: the game's own map -> sound set table
        for m,bank in boss_banks.items():
            if 0<=m<_emr.STOCK_MAPS:struct.pack_into('<i',exe,offset(exe,_emr.SFX_TABLE+4*m,4),bank)
        report['patches'].append({'feature':'boss_sound_sets','maps':{str(m):b for m,b in boss_banks.items()}})
    elif boss_banks:report['boss_sound_sets']={str(m):b for m,b in boss_banks.items()}
    if extra_maps:
        # New map slots 483-499: first block, so its tables are 8-byte aligned.
        import extra_maps_runtime as emr
        map_block=emr.block_for(exe,offset,getattr(session,'content_database',None),session.data)
        blocks.append(('new_map_slots',map_block))
        report['new_map_slots']=extra_maps
        import object_sound_banks as _osb
        if _osb.REPORT:report['object_sound_sets']=list(_osb.REPORT)
    world_flags=world_variants=None
    if requested['open_world']:
        from editor_open_world import open_world_starting_state,world_access_plan
        from native_open_world_state import validate as validate_world,emit_wrapper as emit_world
        world_flags,world_variants=open_world_starting_state()
        validate_world(exe,stock,world_flags,world_variants);world_access_plan(session)
        blocks.append(('open_world_state',emit_world(world_flags,world_variants)))
    elif start_point is not None:
        # A custom start skips Jess's house, whose first-wake process is what
        # sets these flags in a normal new game -- above all "HUD allowed", so
        # without it the health/item UI stays off. Set them at new game.
        from native_open_world_state import validate as validate_world,emit_wrapper as emit_world
        world_flags=[dict(name=name,operand=operand,byte_address=hex(0x801DD334+operand//8),byte_mask=1<<(operand%8))
                     for name,operand in (('FLAG_FIRST_WAKE_DONE',0x0000),('FLAG_INTRO_DONE_C9',0x00C9),('FLAG_HUD_ALLOWED',0x067E))]
        world_variants=[]
        validate_world(exe,stock,world_flags,world_variants)
        blocks.append(('open_world_state',emit_world(world_flags,world_variants)))
        report['start_point_new_game_flags']=world_flags
    if spawn_rules:
        # Database: new attacks that spawn a class when an animation starts.
        import native_animation_spawns as nas
        start_rules=[r for r in spawn_rules if not r.get('frame')]
        frame_rules=[r for r in spawn_rules if r.get('frame')]   # a chosen frame of the animation (native_frame_spawns)
        if start_rules:nas.validate(exe);blocks.append(('animation_spawns',nas.Block(start_rules)))
        if frame_rules:
            import native_frame_spawns as nfs
            nfs.validate(exe);blocks.append(('frame_spawns',nfs.Block(frame_rules)))
        report['animation_spawns']=spawn_rules
    if options.get('instant_boot_plus'):
        # Instant boot +: entry stub that clears the loader hand-over word on a BIOS boot.
        import instant_boot as ib
        original_entry=struct.unpack_from('<I',exe,0x10)[0]
        blocks.append(('instant_boot_entry',type('Block',(),{'length':ib.ENTRY_STUB_SIZE,
            '__call__':lambda self,address:ib.entry_stub(address,original_entry)})()))
        report['instant_boot']={'original_entry':hex(original_entry)}
    start_keys=(starting_stats or {}).get('keys',0)
    if start_keys:
        # Database Player: new-game generic Key count (starting_equipment.emit_key_stub).
        from starting_equipment import verify_key_hook,emit_key_stub
        verify_key_hook(bytes(exe));blocks.append(('starting_keys',emit_key_stub(start_keys)))
    if requested['lr_swaps']:
        validate(exe,stock);blocks.append(('lr_swaps',None))
    if options.get('elemental_bombs') is True:
        # Elemental bomb effects: fire detonation is stock D30; an ice hit halves the fuse speed (elemental_bombs.py)
        import elemental_bombs as _eb
        _eb.validate(bytes(exe));blocks.append(('elemental_bombs',_eb.Block()))
    if options.get('magic_weapon_swap') is True:
        # Magic & weapon swap: Circle in the inventory menu picks a group's weapon / magic (magic_weapon_swap.py)
        import magic_weapon_swap as _mws
        _mws.validate(bytes(exe));blocks.append(('magic_weapon_swap',_mws.Block()))
    if _movie_used:
        # Play Movie event command: remember the movie before END.EXE starts (play_movie.py)
        _pm.validate_alun(bytes(exe));blocks.append(('play_movie',_pm.AlunBlock()))
    if options.get('boss_hp_hud') is True:
        # Boss HP on the HUD: the boss's hit points between the life and Gilder numbers (boss_hp_hud.py)
        import boss_hp_hud as _bhh
        _bhh.validate(bytes(exe));blocks.append(('boss_hp_hud',_bhh.Block(_bhh.boss_classes(getattr(session,'content_database',None)))))
    import magic_spawns as _ms   # an item behaving like Water Scroll: its own tick case (magic_spawns.WaterScrollStub)
    if _ms.needs_water_stub((getattr(session,'content_database',None) or {}).get('definitions',[])):
        blocks.append(('water_scroll_stub',_ms.WaterScrollStub()))
    if consume:   # custom consumable items: HP / MP / Revive (custom_consume.py)
        _cc.validate(bytes(exe));blocks.append(('custom_consume',_cc.Block(consume)))
    if placement:   # magic spawn placement (magic_placement.py), set on the magic item classes
        _mp.validate(bytes(exe));blocks.append(('magic_placement',_mp.Block(placement,bytes(session.data))))
    if no_dash:
        # Meia without "Alundra for missing actions": Triangle never starts a dash.
        at=offset(exe,MEIA_DASH_CHECK);word=struct.unpack_from('<I',exe,at)[0]
        if word!=0x30420010:raise ValueError(f'Meia no-dash: unexpected code at {MEIA_DASH_CHECK:08X}')
        struct.pack_into('<I',exe,at,0x30420000)
        report['meia_no_dash']=hex(MEIA_DASH_CHECK)
    if False:   # fade times stay as in the game (user 2026-10-17: speed up loads only)
        for address,frames in FAST_FADE_SITES:
            at=offset(exe,address);word=struct.unpack_from('<I',exe,at)[0]
            if word!=0x24050000|frames:raise ValueError(f'Fast loading: unexpected fade code at {address:08X}')
            struct.pack_into('<I',exe,at,0x24050000|max(2,frames//4))
        report['fast_loading']=[dict(address=hex(a),frames=f,new=max(2,f//4)) for a,f in FAST_FADE_SITES]
    if options.get('fast_loading') is True or options.get('fast_loads') is True:
        # Fast loading (merged with the old Fast loads, 2026-10-16): room changes stop the old music at once and do not wait for
        # sound effects to end before the room is read (fast_loads.py)
        from fast_loads import EXE_SITES
        for address,old,new in EXE_SITES:
            at=offset(exe,address);word=struct.unpack_from('<I',exe,at)[0]
            if word not in (old,new):raise ValueError(f'Fast loads: unexpected code at {address:08X}')
            struct.pack_into('<I',exe,at,new)
        report['fast_loads']=[hex(a) for a,_,_ in EXE_SITES]
    if requested['instant_text']:
        at=offset(exe,TEXT_BLIP_CALL[0])
        if struct.unpack_from('<I',exe,at)[0]!=TEXT_BLIP_CALL[1]:raise ValueError('Instant text: unexpected text blip call')
        for address,size in ((0x80046FB4,0x80047EC0-0x80046FB4),(0x80048084,8)):
            a=offset(exe,address,size);b=offset(stock,address,size)
            if exe[a:a+size]!=stock[b:b+size]:raise ValueError(f'Instant text conflicts with native interpreter at {address:08X}')
        words=json.loads((ROOT/'extras/game edits/tests/instant_text_words.json').read_text())
        for key in ('gate_words','wrapper_words'):
            raw=struct.pack('<'+'I'*len(words[key]),*words[key])
            if hashlib.sha256(raw).hexdigest()!=INSTANT_BLOCK_SHA256[key]:
                raise ValueError('Instant text emitted code differs from the static-tested portable implementation')
            blocks.append((key,raw))
    if blocks:
        load,size=struct.unpack_from('<II',exe,0x18)
        # Reserve a gap before existing module bytes, including earlier private
        # injections. None of those bytes or their virtual addresses move.
        import extra_maps_runtime as emr
        lengths=[len(emit_wrapper(0x80010000)) if raw is None else raw.length if callable(raw) else len(raw) for _,raw in blocks]
        expansion=(sum(lengths)+0x800+0x7FF)&~0x7FF;new_load=load-expansion
        if new_load<0x80010000:raise ValueError('QoL code exceeds the bounded low-memory prepend allocation')
        prefix=bytearray(expansion);addresses={};cursor=0
        for (name,raw),length in zip(blocks,lengths):
            address=new_load+cursor;raw=emit_wrapper(address) if raw is None else raw(address) if callable(raw) else raw
            prefix[cursor:cursor+length]=raw;addresses[name]=address;cursor+=length
            report['patches'].append(manifest(raw,address) if name=='lr_swaps' else
                {'feature':name,'address':address,'size':length,'sha256':hashlib.sha256(raw).hexdigest()})
        if 'new_map_slots' in addresses:
            report['patches'].append(emr.patch_sites(exe,addresses['new_map_slots'],offset,map_block))
        if requested['lr_swaps']:
            struct.pack_into('<I',exe,offset(exe,HOOK),0x0C000000|((addresses['lr_swaps']>>2)&0x3FFFFFF))
            struct.pack_into('<I',exe,offset(exe,MENU_MASK),0x30420800)
        if requested['instant_text']:
            struct.pack_into('<I',exe,offset(exe,0x800470E8),0x08000000|((addresses['gate_words']>>2)&0x3FFFFFF))
            struct.pack_into('<I',exe,offset(exe,0x80048084),0x0C000000|((addresses['wrapper_words']>>2)&0x3FFFFFF))
            struct.pack_into('<I',exe,offset(exe,TEXT_BLIP_CALL[0]),0)
        if 'instant_boot_entry' in addresses:
            struct.pack_into('<I',exe,0x10,addresses['instant_boot_entry'])   # header PC
            report['instant_boot']['entry']=hex(addresses['instant_boot_entry'])
        if 'animation_spawns' in addresses:
            import native_animation_spawns as nas
            report['patches'].append(nas.patch_hook(exe,addresses['animation_spawns'],lambda e,a:offset(e,a)))
            tick=nas.tick_address(addresses['animation_spawns'],start_rules)   # Despawn after: once-per-frame check
            if tick is not None:nas.patch_tick(exe,tick,lambda e,a:offset(e,a));report['patches'].append(dict(feature='spawn_despawn',hook=hex(nas.TICK_SITE),code=hex(tick)))
        if 'frame_spawns' in addresses:
            import native_frame_spawns as nfs
            report['patches'].append(nfs.patch_hook(exe,addresses['frame_spawns'],lambda e,a:offset(e,a)))
        if 'open_world_state' in addresses:   # open world, or a custom start point's new-game flags
            from native_open_world_state import HOOK as WORLD_HOOK
            struct.pack_into('<I',exe,offset(exe,WORLD_HOOK),0x0C000000|((addresses['open_world_state']>>2)&0x3FFFFFF))
        if 'elemental_bombs' in addresses:
            import elemental_bombs as _eb
            report['patches'].append(_eb.patch_hooks(exe,addresses['elemental_bombs']))
        if 'magic_weapon_swap' in addresses:
            import magic_weapon_swap as _mws
            report['patches'].append(_mws.patch_hooks(exe,addresses['magic_weapon_swap']))
        if 'play_movie' in addresses:
            report['patches'].append(_pm.patch_alun(exe,addresses['play_movie'],lambda e,a:offset(e,a)))
        if 'boss_hp_hud' in addresses:
            import boss_hp_hud as _bhh
            report['patches'].append(_bhh.patch_hook(exe,addresses['boss_hp_hud'],lambda e,a:offset(e,a)))
        if 'custom_consume' in addresses:
            import custom_consume as _cc
            report['patches'].append(_cc.patch_hooks(exe,addresses['custom_consume'],consume))
        if 'water_scroll_stub' in addresses:
            report['patches'].append({'feature':'water_scroll_stub','address':addresses['water_scroll_stub']})
        if 'magic_placement' in addresses:
            import magic_placement as _mp
            report['patches'].append(_mp.patch_hooks(exe,addresses['magic_placement']))
        if 'starting_keys' in addresses:
            from starting_equipment import patch_key_hook
            exe=bytearray(patch_key_hook(bytes(exe),addresses['starting_keys']))
        exe[0x800:0x800]=prefix;struct.pack_into('<II',exe,0x18,new_load,size+expansion)
        from native_injection_stack import protect
        exe,stack_report=protect(exe);exe=bytearray(exe)
        report['allocation']={'old_load':load,'new_load':new_load,'expansion':expansion,
            'gap_at_least':0x800,'native_stack':stack_report,
            'verification':'static only; never restore this prefix into an already booted session'}
    if starting_equipment is not None:
        from starting_equipment import patch_starting_equipment
        exe,equipment_report=patch_starting_equipment(bytes(exe),starting_equipment)
        exe=bytearray(exe);report['patches'].append(equipment_report)
        report['options']['starting_equipment']=list(starting_equipment)
    if starting_stats is not None:
        from starting_equipment import patch_starting_stats
        exe,stats_report=patch_starting_stats(bytes(exe),starting_stats)
        exe=bytearray(exe);report['patches'].append(stats_report)
        report['options']['starting_stats']=dict(starting_stats)
    if requested['skip_intro']:
        from intro_skip import apply_intro_skip
        exe,intro_report=apply_intro_skip(bytes(exe),session,patch_spawn=not requested['open_world'] and start_point is None);exe=bytearray(exe)
        if start_point is not None:
            from editor_start_point import patch_start_point_spawn
            exe,start_report=patch_start_point_spawn(bytes(exe),start_point);exe=bytearray(exe)
            intro_report['spawn']=start_report['spawn']
            intro_report['spawn_fields_patched']=True
            intro_report['spawn_source']='User-authored S start-point tile; height read from current map floor.'
            report['patches'].append(start_report)
        elif requested['open_world']:
            from editor_open_world import patch_open_world_spawn
            exe,spawn_report=patch_open_world_spawn(bytes(exe));exe=bytearray(exe)
            intro_report['spawn']=spawn_report['spawn']
            intro_report['spawn_fields_patched']=True
            intro_report['spawn_source']='Pinned randomizer PatchNewGame: Jess map242, tile38,12; initialized house variant260.'
        report['patches'].append(intro_report)
    if requested['open_world']:
        from editor_open_world import apply_world_access
        world_report=apply_world_access(session)
        world_report['new_game_flag_stores']=world_flags;world_report['new_game_map_variant_stores']=world_variants
        report['patches'].append(world_report)
    if requested['remove_cutscenes']:
        # Remove cutscenes no longer touches item fanfares (user 2026-10-24)
        from cutscene_removal import apply_cutscene_removal
        report['patches'].append(apply_cutscene_removal(session))
    if options.get('regular_item_sounds') is True:
        # Use regular item sounds for rare items (was part of Remove cutscenes until 2026-10-24)
        from cutscene_removal import remove_item_fanfares
        exe,fanfare_report=remove_item_fanfares(bytes(exe));exe=bytearray(exe)
        report['patches'].append(fanfare_report)
    report['source_exe_sha256']=hashlib.sha256(source_exe).hexdigest()
    report['result_exe_sha256']=hashlib.sha256(exe).hexdigest()
    return bytes(exe),report
