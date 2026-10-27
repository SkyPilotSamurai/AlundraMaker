"""Experimental owned C default routes; no shared sprite speed changes."""
from event_logic_compile import _Assembler
from event_movement_compile import compile_movement_command
import math


def require_proven_default_route(graph, definition, *, allow_interaction=False):
    pages = graph.get('pages', [])
    page = pages[0] if pages else {}
    command = dict(page.get('default_move_route') or {})
    catalogue=definition.get('source', {}).get('catalogue_index')
    position_only = (type(catalogue) is int and 0 <= catalogue <= 511
                     and definition.get('kind') not in ('map','event','switch','variable'))
    fixed_npc = (definition.get('kind') == 'npc' and catalogue in (256, 260))
    route=command.get('route')
    common=(not pages or (page.get('commands') and not allow_interaction)
            or graph.get('native_placement', {}).get('presence_by_page_condition')
            or command.get('mode') != 'route'
            or command.get('target') not in ('self', 'this_event')
            or type(command.get('repeat', True)) is not bool
            or type(command.get('movement_speed', 100)) is not int
            or not 1 <= command.get('movement_speed', 100) <= 400
            or command.get('blocked_behavior', 'wait') not in ('wait','skip')
            or not isinstance(route,list) or not route
            or any(direction not in ('up','down','left','right') for direction in route))
    if position_only and not common:
        if (fixed_npc and command.get('route') == ['right','left']
                and command.get('repeat') is True and command.get('movement_speed',100) == 100
                and command.get('blocked_behavior','wait') == 'wait'
                and command.get('moving_animation') == 1 and command.get('idle_animation') == 0):
            command['_native_animation_route'] = True
        else:
            command['_native_animation_route'] = False
        return command
    raise ValueError('Choose a placed character, enemy, item or object, then enter a cardinal movement route')


def compile_default_route(data,catalogue,command,*,map_id):
    if type(command.get('repeat',True)) is not bool:
        raise ValueError('Default route repeat must be true or false')
    if command.get('blocked_behavior','wait') not in ('wait','skip'):
        raise ValueError('Choose whether blocked route steps wait or skip')
    native_animation_route = command.get('_native_animation_route') is True
    if not native_animation_route:
        route=command.get('route')
        if not isinstance(route,list) or not route or any(step not in ('up','down','left','right') for step in route):
            raise ValueError('Choose one or more cardinal directions for the Chest route')
        # Opcode65 moves the owning entity by a signed pixel offset while its
        # current animation stays selected. Alundra tile pitch is24x16.
        import struct
        pitch={'left':(-1,0,24),'right':(1,0,24),'up':(0,-1,16),'down':(0,1,16)}
        body=bytearray()
        speed=command.get('movement_speed',100)
        pixels_per_tick=max(1,round(speed/100))
        wait_frames=max(0,math.ceil(100/speed)-1)
        wait_frames=min(255,wait_frames)
        for direction in route:
            dx,dy,count=pitch[direction]
            left=count
            while left:
                step=min(left,pixels_per_tick)
                body.extend((0x65,0x80))
                body.extend(struct.pack('<hhh',dx*step,dy*step,0))
                body.extend((0x37,wait_frames))
                left-=step
        body=bytes(body)
    else:
        body=compile_movement_command(data,catalogue,command,map_id=map_id)
    # A repeated route stays in walking animation across its wrap. Repeated
    # idle→walking transitions can add native acceleration drift each cycle.
    if command.get('repeat',True) and native_animation_route:
        if body[-3:]!=bytes((0x1A,command.get('idle_animation'),0)):
            raise ValueError('Expected verified native idle route suffix')
        body=body[:-3]
    asm=_Assembler();asm.label('start');asm.data.extend(body)
    if command.get('repeat',True):asm.branch(2,'start')
    asm.data.append(255)
    return {'C':asm.finish(),'F':b'\xff'}, {
        'kind':'experimental-owned-default-route','catalogue':catalogue,
        'repeat':command.get('repeat',True),'speed_percent':100,
        'blocked_behavior':'native distance wait' if native_animation_route else command.get('blocked_behavior','wait'),
        'movement_model':'native animation-driven walking' if native_animation_route else 'position-only native offsets',
        'appearance_animation_preserved':not native_animation_route,
        'interaction_contents':'none',
        'runtime_verified':False,
        'limits':(['Per-instance position route retains its current animation'] if not native_animation_route else ['New NPC instance only','Native animation speed only',
                  'Interaction interruption and resumption not established'])}
