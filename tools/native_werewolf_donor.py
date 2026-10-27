"""Exact standalone authored Werewolf profile, retaining native class AI.

Only the new actor drops the source room cinematic. Stock actors remain bytes.
The source A animation0 initializer is reproduced by the normal A allocator;
source D/F yield/end stubs have no authored action. Runtime evidence is separate.
"""
import hashlib
from native_class_placement import record_cluster
from event_vm_compatibility import sprite_callbacks
from editor_session import EditSession
from event_editor import reachable_instructions
MAP=226
ENTITY=10
RECORD='0000333b0180e25b680481008182008400000000'
CALLBACKS=[('A',0),('C',37),('D',11),('E',1),('F',0)]
PROGRAM_SIGNATURES={
    'A 1':(3,'dbbd756cc0cc82957cdec77d980c49ce7a49a142b1ebc1e1c2dd0c562fcf39e3'),
    'C 1':(133,'31c5b3092769125a7e07be09aa0617a632fc64de3e57f9cbda3f8f85b7045e4c'),
    'D 2':(2,'06eb7d6a69ee19e5fbdf749018d3d2abfa04bcbd1365db312eb86dc7169389b8'),
    'F 4':(2,'06eb7d6a69ee19e5fbdf749018d3d2abfa04bcbd1365db312eb86dc7169389b8'),
}
INITIALIZER=bytes.fromhex('1a00ff')

def donor(data):
    records=record_cluster(data,MAP)['entities']
    if ENTITY>=len(records) or records[ENTITY].hex()!=RECORD:
        raise ValueError('Recovered standalone Werewolf donor record differs')
    if sprite_callbacks(data,MAP,482)!=CALLBACKS:
        raise ValueError('Recovered Werewolf native AI callback profile differs')
    session=EditSession.readonly(data)
    for key,(length,digest) in PROGRAM_SIGNATURES.items():
        rows=reachable_instructions(session,MAP,key)
        raw=b''.join(bytes(session.data[o:o+n]) for o,op,n in rows)
        if len(raw)!=length or hashlib.sha256(raw).hexdigest()!=digest:
            raise ValueError('Recovered Werewolf source '+key+' program differs')
    return dict(map_id=MAP,entity_index=ENTITY,record_hex=RECORD,
                native_callbacks=CALLBACKS,source_program_signatures=PROGRAM_SIGNATURES,
                reproduced_initializer_hex=INITIALIZER.hex(),
                excluded_map_cinematic='C1: arena tiles, scripted movement/jump, actor13, camera/music/dialogue',
                omitted_no_action_hooks=['D2 yield/end','F4 yield/end'],
                existing_stock_actors_changed=False,gameplay_verified=False)
