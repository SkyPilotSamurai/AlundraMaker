"""Bounded new Magicpot activation; preserve native load and bounce handlers."""
from native_class_placement import record_cluster
from event_vm_compatibility import sprite_callbacks
MAP=12
ENTITY=4
RECORD='0000333b01c09956520200000000000000000000'
CALLBACKS=[('A',20),('C',74),('D',0),('E',0),('F',0)]
INITIALIZER=bytes.fromhex('1a01400200ff')

def donor(data):
    records=record_cluster(data,MAP)['entities']
    if ENTITY>=len(records) or records[ENTITY].hex()!=RECORD:
        raise ValueError('Recovered Magicpot donor record differs')
    if sprite_callbacks(data,MAP,409)!=CALLBACKS:
        raise ValueError('Recovered Magicpot native callback profile differs')
    return dict(map_id=MAP,entity_index=ENTITY,record_hex=RECORD,
        native_callbacks=CALLBACKS,initializer_bank='C',initializer_hex=INITIALIZER.hex(),
        preserves_native_A20=True,native_C74_handoff=True,
        evidence='data/2026-10-06-Magicpot-native-initializer-prototype.json',
        existing_stock_actors_changed=False,gameplay_verified=False)
