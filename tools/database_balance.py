"""Apply verified existing balance fields; clones remain independent metadata."""
import hashlib
from copy import deepcopy
from enemy_definition import BalanceTable

def apply_definition_balance(session,definition):
    source=definition.get('source',{})
    if definition.get('clone_of') or source.get('balance_entry') is None:return False
    digest=source.get('balance_sha256')
    if digest not in (hashlib.sha256(session.original).hexdigest(),hashlib.sha256(session.data).hexdigest()):
        raise ValueError('Database balance source differs from this opened game')
    entry=source['balance_entry'];current=BalanceTable(session.data).record(entry,0)
    data=definition['data'];fields={}
    if definition['kind'] in ('enemy','boss','player') and data.get('max_hp') is not None:fields['max_hp']=data['max_hp']
    # Objects too: projectiles and effects spawned by enemies carry their own attacks.
    if definition['kind'] in ('enemy','boss','weapon','object','player') and data.get('attacks'):fields['attacks']=data['attacks']
    if definition['kind'] in ('npc',) and data.get('max_hp') is not None:fields['max_hp']=data['max_hp']
    if (definition['kind'] in ('enemy','boss','player','npc','armor') or (definition['kind']=='item' and source.get('item_id') in (53,54))) and data.get('damage_responses_raw') is not None:   # items: Silver Armlet, Nava's Charm (armor_damage_ui)
        fields['damage_responses']=data['damage_responses_raw']
    if not fields:return False
    offset,raw=BalanceTable(session.data).replacement(entry,0,**fields)
    if bytes(session.data[offset:offset+len(raw)])==raw:return False
    session.replace(offset,raw,'Database source balance tier 0');return True


def sync_balance_aliases(database, session, entry):
    """Refresh source classes sharing the edited tier-0 record, preserving names."""
    table=BalanceTable(session.data)
    record=table.record(entry,0)
    # A chain may share this record only at a later tier. The database form
    # represents tier0, so refresh only aliases whose tier0 is this record.
    aliases={i for i in record['alias_entries'] if table.record(i,0)['offset']==record['offset']}
    changed=[]
    for row in database.definitions:
        if row.get('clone_of') or row.get('source',{}).get('balance_entry') not in aliases:
            continue
        kind=row['kind'];data=row['data']
        if kind in ('enemy','boss','player'):data['max_hp']=record['max_hp']
        if kind in ('enemy','boss','weapon') or (kind=='object' and record.get('attacks')):data['attacks']=deepcopy(record['attacks'])
        if kind in ('enemy','boss','armor'):data['damage_responses_raw']=list(record['damage_responses'])
        changed.append(row['id'])
    return changed
