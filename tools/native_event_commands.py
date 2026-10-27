"""Typed forms over existing native instructions; opaque bytes never relocated."""
import struct
from event_editor import EDITABLE, reachable_instructions as instructions, edit_instruction, script_roots
from map_text import dialogue_entry, edit_dialogue


def command_form(session,map_id,offset,opcode):
    if opcode in (0x0D,0x5C):
        text=dialogue_entry(session,map_id,offset)
        if text:return {'type':'show_dialogue','speaker':None,'text':text[2].decode('latin-1')}
    if opcode in (5,6):
        flag=struct.unpack_from('<H',session.data,offset+1)[0]
        return dict(type='set_switch',switch_id=flag,native_flag_operand=flag,value=opcode==5)
    if opcode==0xA7 and session.data[offset+2]==0:return dict(type='change_music',music_id=session.data[offset+1])
    if opcode==0x75:return dict(type='stop_sound',sound_id=session.data[offset+1])
    if opcode==0x37:return dict(type='wait',frames=session.data[offset+1])
    if opcode==0x98:return dict(type='change_money',amount=struct.unpack_from('<H',session.data,offset+1)[0])
    if opcode==0x53:
        m,x,y,z,effect,sound=struct.unpack_from('<H5B',session.data,offset+1)
        return dict(type='warp_player',map_id=m,x=x,y=y,z=z)
    return None


def apply_form(session,map_id,key,offset,command):
    opcode=session.data[offset];kind=command['type']
    if kind=='show_dialogue' and opcode in (0x0D,0x5C):
        if command.get('speaker') is not None:raise ValueError('This text uses its existing native speaker; edit the actor graphic to change its portrait.')
        return edit_dialogue(session,map_id,offset,command['text'])
    if kind=='set_switch' and opcode in (5,6):
        if command.get('switch_scope')=='project':raise ValueError('Choose an existing game switch for this native instruction.')
        flag=command.get('native_flag_operand',command['switch_id'])
        return edit_instruction(session,map_id,key,offset,[flag],5 if command['value'] else 6)
    values={'change_music':['music_id'],'stop_sound':['sound_id'],'wait':['frames'],'change_money':['amount'],'warp_player':['map_id','x','y','z']}
    expected={'change_music':0xA7,'stop_sound':0x75,'wait':0x37,'change_money':0x98,'warp_player':0x53}
    if expected.get(kind)!=opcode:raise ValueError('This command does not match the original instruction.')
    operands=[command[k] for k in values[kind]]
    if opcode==0xA7:
        from music_database import encode_music
        encode_music(command.get('music_id'));operands.append(0)
    if opcode==0x53:operands.extend(session.data[offset+6:offset+8])
    return edit_instruction(session,map_id,key,offset,operands)


def encode_insert(command):
    kind=command['type']
    if kind=='set_switch':
        if command.get('switch_scope')=='project':raise ValueError('Choose a game switch; this existing process uses native game flags.')
        flag=command.get('native_flag_operand',command.get('switch_id'))
        if type(flag) is not int or not (0<=flag<=0x7FF or 0x8000<=flag<=0x87FF):raise ValueError('Invalid native game switch')
        return struct.pack('<BH',5 if command['value'] else 6,flag)
    if kind=='face_actor':
        from event_movement_compile import compile_facing_command
        return compile_facing_command(command,has_actor=True)
    if kind=='change_music':
        from music_database import encode_music
        return encode_music(command.get('music_id'))
    if kind=='play_sound':
        from sound_database import encode_sound
        return encode_sound(command.get('sound_id'))
    if kind=='stop_sound':
        from sound_database import encode_stop_sound
        return encode_stop_sound(command.get('sound_id'))
    if kind=='wait':return struct.pack('<BB',0x37,command['frames'])
    if kind=='change_money':return struct.pack('<BH',0x98,command['amount'])
    if kind=='warp_player':
        if not 0<=command['map_id']<2547:raise ValueError('Invalid destination map')
        return struct.pack('<BH5B',0x53,command['map_id'],command['x'],command['y'],command.get('z',0),0,0)
    raise ValueError('This command needs additional native allocation; currently insert game switches, waits, money or transfers into freed command space.')


def replace_in_place(session,map_id,key,offset,raw):
    """Use explicit no-op slots; original branch/call addresses never move."""
    rows=instructions(session,map_id,key)
    start=next((i for i,r in enumerate(rows) if r[0]==offset),None)
    if start is None:raise ValueError('Choose a command slot')
    capacity=0
    for p,op,n in rows[start:]:
        if op!=1 or n!=1:break
        capacity+=1
    if len(raw)>capacity:raise ValueError(f'This slot has {capacity} freed bytes; the command needs {len(raw)}. Delete adjacent known commands to free space first.')
    stop=offset+len(raw)
    roots=script_roots(session,map_id)
    if any(offset<address<stop for address,end,minimum in roots.values()):
        raise ValueError('Another process starts inside this insertion slot.')
    for root in roots:
        for p,opcode,size in instructions(session,map_id,root):
            if opcode in (0x57,0x58,*range(0x79,0x82)):
                raise ValueError('An indirect/choice branch prevents proving this freed slot is safe to combine.')
            if opcode in (2,3,4,0x30,0x31,0x74,0x78):
                target=p+struct.unpack_from('<h',session.data,p+size-2)[0]
                if offset<target<stop:raise ValueError('A branch targets the middle of this insertion slot; preserve its command boundaries.')
    session.replace(offset,raw,'Insert native event command')


def delete_command(session,map_id,key,offset):
    row=next((r for r in instructions(session,map_id,key) if r[0]==offset),None)
    if row is None or row[1]==255 or row[1] not in EDITABLE and command_form(session,map_id,offset,row[1]) is None:
        raise ValueError('Unknown commands and End process are preserved; select a decoded editable command.')
    session.replace(offset,bytes([1])*row[2],'Delete native command (preserve branch addresses)')
