"""Exact stock hook-free Murgg donors and fixed native projectile slots.

Structural proof only: gameplay certification is kept in dated runtime reports.
No native AI or instance script is substituted. Imports are transactional and
preserve native local IDs because the AI spawns current-map slots 95/101.
"""
from native_class_placement import record_cluster
from event_vm_compatibility import sprite_callbacks
from local_sprite_import import import_local_sprite

PROFILES = {
    347: dict(map_id=110, entity_index=15,
              record_hex='0000333b01805b28620200000000000000000000',
              callbacks=[('A',0),('C',10),('D',9),('E',1),('F',0)], projectiles={}),
    350: dict(map_id=151, entity_index=23,
              record_hex='0000333b01c05e3b5b0a00000000000000000000',
              callbacks=[('A',0),('C',33),('D',13),('E',1),('F',0)],
              projectiles={351:[('A',0),('C',24),('D',0),('E',3),('F',0)]}),
    356: dict(map_id=111, entity_index=17,
              record_hex='0000333b018064405a0200000000000000000000',
              callbacks=[('A',0),('C',35),('D',6),('E',1),('F',0)],
              projectiles={357:[('A',0),('C',36),('D',0),('E',3),('F',0)]}),
}


def verified_donor(data, catalogue):
    if catalogue not in PROFILES:
        raise ValueError('No recovered Murgg dependency profile for this class')
    profile=PROFILES[catalogue]
    records=record_cluster(data,profile['map_id'])['entities']
    if profile['entity_index']>=len(records) or records[profile['entity_index']].hex()!=profile['record_hex']:
        raise ValueError('Known hook-free Murgg source record differs')
    for identity, expected in [(catalogue,profile['callbacks']), *profile['projectiles'].items()]:
        if sprite_callbacks(data,profile['map_id'],identity)!=expected:
            raise ValueError('Known Murgg or projectile native callback profile differs')
    return dict(profile,catalogue_index=catalogue,gameplay_verified=False)


def import_bundle(data,target_map,catalogue):
    if catalogue==347 and target_map==153:
        raise ValueError('Murgg claws in map153 needs its native parent/controller contract')
    profile=verified_donor(data,catalogue)
    # Work on returned copies: a dependency collision/capacity failure cannot
    # leave the caller with a half-imported parent that spawns missing sprites.
    result=bytes(data);reports=[]
    for identity in [catalogue,*profile['projectiles']]:
        result,report=import_local_sprite(result,target_map,profile['map_id'],identity-256)
        reports.append(dict(report,catalogue_index=identity))
    return result,dict(profile,asset_imports=reports,
                       fixed_projectile_slots=[i-256 for i in profile['projectiles']],
                       native_parent_spawn_retained=True)
