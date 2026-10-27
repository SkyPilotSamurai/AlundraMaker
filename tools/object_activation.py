"""State-changing object authoring defaults; native hooks remain type-specific."""
# Switches you hit (lever, wall, ignition, toggle, lamp). Their actions start on Activate (user 2026-10-14;
# a Hit tab still builds as Activate).
HIT_SWITCHES={305,306,307,308,398}
ACTIVATION_OBJECTS={291,298,301,305,306,307,308,312,313,314,315,321,322,323,324,325,326,337,346,383,393}   # 346 Nirude Face Statue (2026-10-24)

def default_event_trigger(definition):
    if not definition:return 'interact'
    if definition.get('kind') in ('enemy','boss'):return 'death'   # enemies and bosses start on Death
    data=definition.get('data',{})
    index=definition.get('source',{}).get('catalogue_index')
    if definition.get('kind')=='object' and (index in ACTIVATION_OBJECTS or
            any(r.get('activate') for r in data.get('reactions',{}).values() if isinstance(r,dict))):
        return 'activate'
    return 'interact'
