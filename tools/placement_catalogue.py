"""Placement tabs and related native actor parts without removing definitions.

These are editor/source groupings, not proof that a boss can run in any map.
Parts remain accessible in Misc; primary actors retain native identity/hooks.
"""
from functools import lru_cache
from database_catalogue import entity_names,COMMIT

CATEGORIES=('npc','enemy','boss','object','item','misc')
LABELS={'npc':'NPCs','enemy':'Enemies','boss':'Bosses','object':'Objects','item':'Items','misc':'Misc'}
ALIASES={**{v.lower():k for k,v in LABELS.items()},**{k:k for k in CATEGORIES}}
# Explicit catalogue relationships, source labels or adjacent indented entries.
# None means component association is unresolved rather than guessed.
OWNERS={330:329,351:350,357:356,366:365,372:371,411:410,
    413:412,414:412,415:412,419:418,420:418,423:418,424:418,
    432:431,444:443,447:446,448:446,450:446,462:461,
    464:463,465:463,468:467,469:509,470:500,472:471,
    474:473,475:473,477:476,478:None,480:479,481:479,483:None,
    484:485,486:485,487:485,489:488,490:488,491:488,492:488,
    496:495,498:497,499:497,501:500,502:495,503:495,504:488,
    505:488,507:506,508:506,510:509,511:509}
PLAYER_SPAWNS=set(range(1,25))|{27,28,29,150,151,152,153}
# Source-labelled collision-only/invisible helpers and object effect components.
# Grouping is an editor convention, not a recovered spawn call or parent pointer.
INVISIBLE_OBJECTS={25,228,231,233,235,244,246,248,249}
OBJECT_COMPONENTS={343,374,376,391}
# Recognizable primary boss forms. Source-only category; runtime prerequisites
# still require donor/AI verification. Avoid calling an indented part a boss.
PRIMARY_BOSSES={412,418,446,459,460,463,471,476,479,482,485,488,493,494,495,497,500,506,509}


@lru_cache(maxsize=1)
def _names():return entity_names()


@lru_cache(maxsize=8)
def _relation_ids(signature):
    primary={};related={}
    for cid,index,clone in signature:
        primary.setdefault(index,[]).append((cid,clone))
        if index in OWNERS:related.setdefault(OWNERS[index],[]).append(cid)
    return primary,related


def _relations(database):
    definitions=database.definitions if hasattr(database,'definitions') else database.get('definitions',[]) if isinstance(database,dict) else []
    signature=tuple((r['id'],r.get('source',{}).get('catalogue_index'),bool(r.get('clone_of'))) for r in definitions)
    return _relation_ids(signature)


def placement_info(row,database=None,_index=None):
    source=row.get('source',{});index=source.get('catalogue_index')
    names=_names();native=names[index] if type(index) is int and 0<=index<len(names) else None
    component=bool(native and native['text_jp'].startswith(('◆−','◆-')))
    if index==500:component=False   # Twin Demons (its second half, 501, has no entry)
    player_spawn=index in PLAYER_SPAWNS if type(index) is int else False
    invisible=index in INVISIBLE_OBJECTS or source.get('invisible') is True
    spawned=bool(source.get('spawned_by_class_id') or source.get('spawned_by_catalogue_index') is not None)
    object_component=index in OBJECT_COMPONENTS or spawned
    role='invisible_helper' if invisible else 'object_effect' if object_component else 'component' if component else 'player_effect' if player_spawn else 'primary'
    kind=row.get('kind')
    category='misc' if component or player_spawn or invisible or object_component or kind in ('unclassified','player') else 'item' if kind in ('item','weapon','armor') else kind
    if category not in CATEGORIES:category='misc'
    if role=='primary' and index in PRIMARY_BOSSES and kind!='npc':category='boss'   # NPC versions (Melzas (NPC)...) stay NPCs
    primary=OWNERS.get(index) if component else index
    primary_ids,related_ids=_index if _index is not None else _relations(database)
    matches=primary_ids.get(primary,[])
    primary_id=next((cid for cid,clone in matches if not clone),matches[0][0] if matches else None)
    related=[cid for cid in related_ids.get(index,[]) if cid!=row['id']]
    return dict(category=category,label=LABELS[category],role=role,
        native_catalogue_index=index,primary_catalogue_index=primary,
        primary_class_id=primary_id,
        related_class_ids=related,source_commit=COMMIT if native else None,
        source_line=index+2 if native else None,
        grouping_basis='Explicit spawned-by source metadata' if spawned else 'Source-labelled invisible helper' if invisible else 'Source-labelled object effect/component' if object_component else 'Pinned catalogue indentation/labels; conservative editor grouping' if native else 'Project definition kind',
        standalone_supported=False if component else None,
        placement_default='map_pickup' if category=='item' else 'existing_native_behavior',
        limitation='Parts may require a live parent, sibling slots or native spawn setup' if component else
                   'Native donor/assets and map-specific AI prerequisites checked separately at export')


def placement_rows(database,category,include_components=False):
    """Return original definitions for a tab; IDs, names and data are unchanged."""
    category=ALIASES.get(str(category).lower())
    if category is None:raise ValueError('Choose NPCs, Enemies, Bosses, Objects, Items or Misc')
    definitions=database.definitions if hasattr(database,'definitions') else database.get('definitions',[])
    result=[];relations=_relations(database)
    for row in definitions:
        info=placement_info(row,database,relations)
        match=info['category']==category
        if category=='misc' and (row.get('kind')=='player' or row.get('name','').strip().casefold()=='alundra'):
            continue   # the player is not placeable from Misc
        if include_components and info['role']=='component' and info['primary_class_id']:
            parent=next(r for r in definitions if r['id']==info['primary_class_id'])
            match=match or placement_info(parent,database,relations)['category']==category
        if match:result.append(row)
    if category=='enemy':   # by ID (the number shown on each entry), new and duplicated enemies included (user 2026-10-18)
        def number(r):
            tail=r['id'].split(':')[-1]
            return (int(tail) if tail.isdigit() else 10**6,r['id'])
        return sorted(result,key=number)
    return sorted(result,key=lambda r:(r.get('source',{}).get('catalogue_index',10000),r['name'].casefold(),r['id']))


def annotate_placement_sources(database):
    """Record grouping alongside source metadata, preserving schema and IDs."""
    for row in database.definitions:
        info=placement_info(row,database)
        if row.get('source',{}).get('catalogue_index') is not None:
            row['source']['placement_grouping']={k:info[k] for k in
                ('category','role','primary_catalogue_index','grouping_basis','source_commit','source_line')}
    return database.definitions


def database_rows(database,kind):
    """Database actor lists use the same component split as map placement.

    Keep native definition kinds and data intact, including referenced parts.
    Misc exposes all source-derived parts and spawned effects independently.
    """
    if kind=='boss':
        # a boss's parts (Melzas Double...) also listed here, for their combat and spawned attacks
        rows=placement_rows(database,'boss');ids={r['id'] for r in rows}
        return rows+[r for r in placement_rows(database,'misc') if r.get('kind')=='boss' and r['id'] not in ids]
    if kind in ('enemy','object','misc','unclassified'):
        return placement_rows(database,'misc' if kind=='unclassified' else kind)
    return [row for row in database.definitions if row['kind']==kind]
