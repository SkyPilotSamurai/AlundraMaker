"""Experimental single-owner native C context snapshot/restore injection.

These E6/E7 opcodes are newly authored MIPS, not vanilla recovery. Never
enable in production before actual interrupted-route proof and native guards.
"""
import hashlib
import struct
from project_state_runtime import _Mips, DISPATCH
from native_injection_stack import protect

CONTRACT_SITES={
    0x80042E30:(0x02402821,0x02603021), # a1 owner, a2 current cursor address
    0x80042E5C:(0x0060F809,0x02803821), # indirect handler call; a3 context
    0x80042E98:(0x10800007,0,0xAE800008,0x8E620000,0,0x00441021,0x08010B7B,0xAE620000),
    # return0 branches to80042EB8 before scratch/cursor advancement above.
}

def verify_contract(exe):
    load=struct.unpack_from('<I',exe,0x18)[0]
    off=0x80040264-load+0x800
    if (struct.unpack_from('<I',exe,DISPATCH+0x66*4-load+0x800)[0]!=0x80040264
            or hashlib.sha256(exe[off:off+0x98]).hexdigest()!='e27566a7a7f0478a29008ed86b98ca56948ce52b4493528f5884666e2c569954'):
        raise ValueError('Native route resume66 context-copy contract differs')
    for address,words in CONTRACT_SITES.items():
        off=address-load+0x800
        if exe[off:off+len(words)*4]!=struct.pack('<'+'I'*len(words),*words):
            raise ValueError('Native route resume VM handler contract differs')
    return {'module':'ALUN_CD.EXE','handler_owner_argument':'a1','context_argument':'a3',
        'native66_context_copy':'80040264..800402FB','native66_bytes_sha256':'e27566a7a7f0478a29008ed86b98ca56948ce52b4493528f5884666e2c569954',
        'cursor_argument':'a2','return0_no_cursor_advance_branch':'80042E98→80042EB8',
        'sites':{f'{a:08X}':[f'{w:08X}' for w in words] for a,words in CONTRACT_SITES.items()}}

def emit(opcode,storage):
    if opcode not in (0xE6,0xE7):raise ValueError('Experimental route opcode')
    m=_Mips();m.li(8,storage)
    if opcode==0xE6:
        m.i(43,8,5,72)
    else:
        m.load(9,8,72);m.branch(5,9,5,'invalid')
    # Native66 copies56 bytes; saved animation/direction occupy the next8.
    for offset in range(0,64,4):
        m.load(9,5 if opcode==0xE6 else 8,0x234+offset if opcode==0xE6 else offset)
        m.i(43,8 if opcode==0xE6 else 5,9,offset if opcode==0xE6 else 0x234+offset)
    for offset,field in ((64,0x88),(68,0x8C)):
        m.load(9,5 if opcode==0xE6 else 8,field if opcode==0xE6 else offset)
        m.i(43,8 if opcode==0xE6 else 5,9,offset if opcode==0xE6 else field)
    m.i(9,0,2,1 if opcode==0xE6 else 0);m.words.extend((0x03E00008,0))
    if opcode==0xE7:
        m.label('invalid');m.i(9,0,2,1);m.words.extend((0x03E00008,0))
    return m.finish()

def emit_indexed(opcode,storage,slots):
    if opcode not in (0xE6,0xE7) or type(slots) is not int or not 1<=slots<=16:
        raise ValueError('Indexed route resume needs1..16 declared snapshots')
    m=_Mips();m.li(8,storage)
    m.load(9,6,0);m.load(10,9,1,36)
    m.i(11,10,11,slots);m.branch(4,11,0,'invalid')
    m.r(0,10,11,0,4);m.r(0,10,10,0,6);m.r(10,11,10,0x21);m.r(8,10,8,0x21)
    m.li(10,0x801AC6F8);m.r(5,10,11,0x2B);m.branch(5,11,0,'invalid')
    m.li(10,0x801B6BF8);m.r(5,10,11,0x2B);m.branch(4,11,0,'invalid')
    m.load(9,5,0x10);m.branch(4,9,0,'invalid')
    m.load(9,8,76)
    if opcode==0xE6:m.branch(5,9,0,'invalid');m.i(43,8,5,72)
    else:
        m.branch(4,9,0,'invalid');m.load(9,8,72);m.branch(5,9,5,'invalid')
    for offset in range(0,64,4):
        m.load(9,5 if opcode==0xE6 else 8,0x234+offset if opcode==0xE6 else offset)
        m.i(43,8 if opcode==0xE6 else 5,9,offset if opcode==0xE6 else 0x234+offset)
    for offset,field in ((64,0x88),(68,0x8C)):
        m.load(9,5 if opcode==0xE6 else 8,field if opcode==0xE6 else offset)
        m.i(43,8 if opcode==0xE6 else 5,9,offset if opcode==0xE6 else field)
    if opcode==0xE6:m.i(9,0,9,1);m.i(43,8,9,76)
    else:m.i(43,8,0,76)
    m.i(9,0,2,2 if opcode==0xE6 else 0);m.words.extend((0x03E00008,0))
    m.label('invalid');m.i(9,0,2,0);m.words.extend((0x03E00008,0))
    return m.finish()

def inject(exe):
    contract=verify_contract(exe)
    load,size=struct.unpack_from('<II',exe,0x18)
    if not 0x80018000<load<=0x80020000 or len(exe)!=size+0x800:raise ValueError('Unexpected executable load')
    new_load=load-0x800;storage=new_load;prefix=bytearray(0x800)
    output=bytearray(exe);handlers={};position=80
    for opcode in (0xE6,0xE7):
        site=DISPATCH+opcode*4-load+0x800
        if struct.unpack_from('<I',exe,site)[0]!=0x8003DBD0:raise ValueError('Experimental opcode fallback differs')
        code=emit(opcode,storage);address=new_load+position
        prefix[position:position+len(code)]=code;position+=len(code)
        struct.pack_into('<I',output,site,address)
        handlers[opcode]={'address':address,'bytes':len(code),'sha256':hashlib.sha256(code).hexdigest()}
    output[0x800:0x800]=prefix;struct.pack_into('<II',output,0x18,new_load,size+0x800)
    output,stack=protect(output)
    return output,{'experimental':True,'opcodes':handlers,'storage_address':storage,'storage_size':80,
        'native_contract':contract,
        'native_context_bytes':64,'saved_live_pose_bytes':8,'owner_identity_bytes':4,
        'single_owner_only':True,'native_stack':stack,'runtime_verified':False}
