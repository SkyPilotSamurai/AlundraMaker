"""Source-guarded native Sara1 donor; no story scripts removed from stock maps."""
from native_class_placement import record_cluster
from event_vm_compatibility import sprite_callbacks
MAP=54
ENTITY=15
RECORD='2828333b01c0c45b680600000000000000000000'
CALLBACKS=[('A',0),('C',12),('D',10),('E',1),('F',0)]

def donor(data):
    records=record_cluster(data,MAP)['entities']
    if ENTITY>=len(records) or records[ENTITY].hex()!=RECORD:
        raise ValueError('Recovered Sara1 hook-free donor differs')
    if sprite_callbacks(data,MAP,452)!=CALLBACKS:
        raise ValueError('Recovered Sara1 native AI callback profile differs')
    return dict(map_id=MAP,entity_index=ENTITY,native_callbacks=CALLBACKS,
                record_hex=RECORD,instance_hooks_transplanted=False,gameplay_verified=False)
