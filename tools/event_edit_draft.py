"""Atomic event/private-state editing draft, discarded unless Apply succeeds."""
from copy import deepcopy
from content_database import ContentDatabase
from project_state_registry import ProjectStateRegistry


EVENT_KEYS=('event_graphs','project_state','deleted_event_ids')

def event_copy(document):
    """Share the big read-only parts (definitions, instances); copy only what
    the event editor changes. Opening and saving events stays fast."""
    result=dict(document)
    for key in EVENT_KEYS:
        if key in result:result[key]=deepcopy(result[key])
    return result

class EventEditDraft:
    def __init__(self,database):
        self.global_database=database
        self.database=ContentDatabase(event_copy(database.document),copy=False)
        # Normalize only the draft; absent global registry stays absent until Apply.
        ProjectStateRegistry(self.database.document)
        self.baseline={key:deepcopy(database.document.get(key)) for key in ('event_graphs','project_state','deleted_event_ids')}

    def commit(self,session=None):
        original=self.global_database.document
        draft=self.database.document
        candidate=event_copy(original)
        if all(original.get(key)==value for key,value in self.baseline.items()):
            candidate['event_graphs']=deepcopy(draft['event_graphs'])
            candidate['project_state']=deepcopy(draft['project_state'])
            if 'deleted_event_ids' in draft:candidate['deleted_event_ids']=deepcopy(draft['deleted_event_ids'])
        else:
            # The project changed elsewhere (map view, Undo, another window) since this
            # editor opened (user 2026-10-23: reopening looped on the old refusal).
            # Merge: apply the events this editor changed onto the current ones. When the
            # same event changed in both places, this editor's edit wins (user 2026-10-23).
            base={g['id']:g for g in self.baseline.get('event_graphs') or []}
            mine={g['id']:g for g in draft.get('event_graphs') or []}
            now={g['id']:g for g in original.get('event_graphs') or []}
            touched={i for i in set(base)|set(mine) if base.get(i)!=mine.get(i)}
            order=[g['id'] for g in original.get('event_graphs') or []]+[i for i in mine if i not in now]
            merged=[]
            for i in order:
                row=mine.get(i) if i in touched else now.get(i)
                if row is not None:merged.append(deepcopy(row))
            candidate['event_graphs']=merged
            state_base=self.baseline.get('project_state')
            if draft.get('project_state')!=state_base and original.get('project_state') not in (None,state_base):
                state=deepcopy(original['project_state'])
                for kind in ('switches','variables'):   # add this editor's new rows to the current ones
                    have={r['id'] for r in state.get(kind,[])}
                    state.setdefault(kind,[]).extend(deepcopy(r) for r in draft['project_state'].get(kind,[]) if r['id'] not in have)
                candidate['project_state']=state
            else:
                candidate['project_state']=deepcopy(draft['project_state'] if draft.get('project_state')!=state_base else original.get('project_state') or draft['project_state'])
            deleted=set(original.get('deleted_event_ids') or [])|set(draft.get('deleted_event_ids') or [])
            if deleted:candidate['deleted_event_ids']=sorted(deleted)
        registry=ProjectStateRegistry(candidate)
        previous=ProjectStateRegistry(event_copy(original))
        # Canceled nested forms can create provisional rows; publish only new
        # state actually referenced by confirmed event contents/conditions.
        for kind in ('switches','variables'):
            previous_ids={r['id'] for r in previous.state[kind]}
            candidate['project_state'][kind]=[r for r in registry.state[kind]
                if r['id'] in previous_ids or registry.references(kind,r['id'])]
        checked=ContentDatabase(candidate,copy=False)
        ProjectStateRegistry(checked.document).validate_references()
        # All validation and conflict checks occur before either global mutation.
        if checked.document==original:
            pass
        elif session is not None:
            session.replace_document(original,checked.document,'Apply event and project switches')
        else:
            original.clear();original.update(deepcopy(checked.document))
        self.baseline={key:deepcopy(original.get(key)) for key in self.baseline}
        draft_state=self.database.document['project_state']
        draft_state.clear();draft_state.update(deepcopy(original['project_state']))
        return self.global_database

    def delete_event(self,event_id):
        from event_deletion import delete_graph
        class DraftSession:
            def replace_document(self,target,replacement,label):
                target.clear();target.update(deepcopy(replacement))
        return delete_graph(DraftSession(),self.database,event_id)
