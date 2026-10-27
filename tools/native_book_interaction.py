"""Bounded authored Book303 interaction; no stock event or controller replacement."""
BOOK_RECORD='0000333b01802f401a0200000000000000000000'
ZERO_CALLBACKS=[('A',0),('C',0),('D',0),('E',0),('F',0)]

def verify_source(datas):
 from native_class_placement import record_cluster
 from event_vm_compatibility import sprite_callbacks
 row=record_cluster(datas,136)['entities'][8]
 if row.hex()!=BOOK_RECORD or sprite_callbacks(datas,136,303)!=ZERO_CALLBACKS:
  raise ValueError('Book303 hook-free native source136/8 differs')
 return dict(catalogue=303,donor_map=136,donor_entity=8,record_hex=BOOK_RECORD,native_callbacks=ZERO_CALLBACKS)

def require_graph(graph,datas):
 verify_source(datas)
 pages=graph.get('pages',[])
 if len(pages)!=1 or pages[0].get('trigger')!='interact' or pages[0].get('conditions'):
  raise ValueError('Assigned Book303 supports one unconditional Interact page')
 for command in pages[0].get('commands',[]):
  if command.get('type') not in ('show_dialogue','change_money'):
   raise ValueError('Assigned Book303 currently supports Show text and Change money only')
  if command.get('type')=='show_dialogue' and(command.get('speaker') not in (None,'self') or command.get('native_speaker_entity_index') is not None):
   raise ValueError('Assigned Book303 currently uses its own text speaker only')
 placement=graph.get('native_placement',{})
 if any(k in placement for k in ('donor_map_id','donor_entity_index')) and(placement.get('donor_map_id'),placement.get('donor_entity_index'))!=(136,8):
  raise ValueError('Assigned Book303 explicit donor must be verified source136/8')

def require_placed_template(datas,map_id,row):
 from event_vm_compatibility import sprite_callbacks
 if any(row[10:16]) or row[18:20]!=bytes(2) or sprite_callbacks(datas,map_id,303)!=ZERO_CALLBACKS:
  raise ValueError('Assigned Book303 needs no inherited hooks, contents or native callbacks')

def button_load_process():
 # Native62 byte selector80, little-endian16-bit mask8000. Only this new
 # authored instance gains the native button-interaction flag; class/stock
 # sprite header and retail records remain unchanged.
 return bytes.fromhex('62800080ff')
