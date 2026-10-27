"""Prefer concrete hook-free object instances with the first donor's callbacks.

This is structural donor selection, not gameplay certification. Native callback
selectors remain intact. No instance program is transplanted into another map.
Without an eligible alternative, the original first donor is returned so the
compiler's existing behavior-dependency guard can reject it normally.
"""
import struct
from database_catalogue import entity_names, classify
from native_class_placement import record_cluster
from event_vm_compatibility import sprite_callbacks

# Actual cold-boot test found that the hook-free statue variant is stationary.
# Its first donor's map controller supplies movement. Keep that guarded donor
# until a portable controller is recovered; identical zero callbacks are not
# evidence that the two instances behave the same.
#312/313 platform vertical motion,324 keyed door destruction,325/326 gate
# opening are supplied by first-donor map programs; hook-free scenery omits
# these behaviors. Exact stock programs: dated passive-controller audit.
#345 selected hook-free426 instance stayed dormant in actual gameplay;
# source40 provides the C2/F2 press/rearm animation programs.
MAP_CONTROLLER_REQUIRED=frozenset({298,312,313,315,324,325,326,345})


# Hook-free315 is scenery in two actual cold tests. Keep an actual native
# rolling-controller donor guarded, rather than returning the first static row.
CONTROLLER_GUARDED_DONORS={315:(67,29,'10251f3b01c33b2d51269e009e00000000000000')}

def preferred_hook_free_donor(datas, catalogue_index):
    if type(catalogue_index) is not int or not 0<=catalogue_index<=511:
        raise ValueError('Object catalogue ID outside two native banks')
    names=entity_names()
    if catalogue_index>=len(names) or classify(catalogue_index,names[catalogue_index]['text_en'])!='object':
        raise ValueError('Preferred hook-free donor selection is only for object classes')
    first=None; selected=None; guarded=None; count=0; free_count=0; profile_mismatches=0
    for map_id in range(483):
        cluster=record_cluster(datas,map_id)
        for entity_index,raw in enumerate(cluster['entities']):
            if raw[6]+(256 if raw[5]&128 else 0)!=catalogue_index: continue
            callbacks=sprite_callbacks(datas,map_id,catalogue_index)
            row={'map_id':map_id,'entity_index':entity_index,'record_hex':raw.hex(),
                 'native_callbacks':callbacks,'hook_free':not any(raw[10:16]),
                 'flag_raw':struct.unpack_from('<H',raw,16)[0],
                 'contents_raw':struct.unpack_from('<H',raw,18)[0]}
            count+=1
            if first is None: first=row
            required=CONTROLLER_GUARDED_DONORS.get(catalogue_index)
            if required and (map_id,entity_index)==required[:2]:
                if raw.hex()!=required[2]:raise ValueError('Known rolling-controller source record differs')
                if callbacks!=first['native_callbacks']:raise ValueError('Known rolling-controller native callbacks differ')
                guarded=row
            if row['hook_free']:
                free_count+=1
                if callbacks!=first['native_callbacks']:
                    profile_mismatches+=1;continue
                if selected is None: selected=row
    if first is None:
        raise ValueError('Object class has no concrete native donor')
    if catalogue_index in MAP_CONTROLLER_REQUIRED:
        selected=None
    if catalogue_index in CONTROLLER_GUARDED_DONORS and guarded is None:
        raise ValueError('Known rolling-controller donor is absent; scenery is not a substitute')
    choice=guarded or selected or first
    return {**choice,'catalogue_index':catalogue_index,'first_donor':first,
            'selection':'guarded_native_controller_donor' if guarded else 'hook_free_same_native_callbacks' if selected else 'first_donor_fallback',
            'donor_count':count,'hook_free_count':free_count,
            'hook_free_callback_mismatches':profile_mismatches,
            'instance_callbacks_transplanted':False,'gameplay_verified':False,
            'known_map_controller_dependency':catalogue_index in MAP_CONTROLLER_REQUIRED,
            'limitations':['Hook-free does not prove full behavior',
                           'Sprite callback selectors do not decode entire native callees',
                           'Original hooked fallback still requires behavior preflight']}
