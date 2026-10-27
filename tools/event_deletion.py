"""Undoable event removal with native record indices retained as tombstones."""
from copy import deepcopy
from map_inspector import inspect_map


def _references(value,event_id):
    if isinstance(value,dict):return any(_references(v,event_id) for v in value.values())
    if isinstance(value,list):return any(_references(v,event_id) for v in value)
    return value==event_id


def delete_graph(session,database,event_id):
    document=database.document;graphs=document.get('event_graphs',[])
    row=next((row for row in graphs if row['id']==event_id),None)
    if row is None:raise ValueError('Select an event that still exists')
    for other in graphs:
        if other is not row and _references(other,event_id):
            raise ValueError(f'Event is referenced by {other.get("name",other["id"])}; remove that reference first')
    replacement=deepcopy(document);replacement['event_graphs']=[r for r in replacement['event_graphs'] if r['id']!=event_id]
    replacement.setdefault('deleted_event_ids',[]).append(event_id)
    session.replace_document(document,replacement,'Delete event '+row.get('name',event_id))
    return ('Event override removed; its original game process remains.' if row.get('native_binding')
            else 'Event deleted from this mod. Undo restores it.')


def record_deleted(document,map_id,kind,index):
    return any(row=={'map_id':map_id,'kind':kind,'index':index} for row in document.get('deleted_native_records',[]))


def delete_record(session,database,map_id,kind,index):
    if kind not in ('entities','events'):raise ValueError('Select a character or map event to delete')
    rows=inspect_map(session.data,map_id)[kind]
    if type(index) is not int or not 0<=index<len(rows):raise ValueError('Selected event no longer exists')
    document=database.document
    if record_deleted(document,map_id,kind,index):raise ValueError('This event is already deleted; Undo restores it')
    offset=int(rows[index]['offset'],16)+4
    # Entity GetEntityRecord returns null for IsEnabled==0. Map-event updater
    # skips low7-bit program index0. Never compact tables or erase terminators.
    replacement=deepcopy(document);replacement.setdefault('deleted_native_records',[]).append(
        {'map_id':map_id,'kind':kind,'index':index})
    session.replace_document(document,replacement,f'Delete {kind} {index}',[(offset,b'\0')])
    return 'Event deleted. Its native slot is retained to preserve other event references; Undo restores it.'
