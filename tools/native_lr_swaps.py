"""Original native quick-swap code for the fingerprinted US1.1 main module.

L1/R1 cycle owned weapon families; L2/R2 cycle usable item groups. Native
getters select the highest owned progressive tier, and native setters retain
the game's signed-halfword equipment ABI. This is static-tested injected code,
not a recovered vanilla feature or a claim of hardware/emulator verification.
"""
import hashlib
import struct
from project_state_runtime import _Mips

HOOK=0x8002BD94
MENU_MASK=0x8002BE00
# Cycle orders of the item-swap Lua script (Alundra Crowd Control): R goes
# forward, L back, wrapping; unowned entries are skipped.
# Weapons (native categories): sword, flail, bow, ice wand, fire wand, spirit wand.
WEAPON_ORDER=(1,3,2,4,5,6)
# Item groups: herbs, strength tonic, strength elixir, magic elixir, wonder
# essence, mining bomb, earth, water, fire, wind magic, sand cape, aqua cape,
# Nava's charm, power glove, spring bean, Olga's/Oak's ring, silver armlet,
# recovery ring/refresher. Native getters still pick the best owned tier.
ITEM_GROUPS=(12,14,13,15,30,11,16,17,18,19,26,27,31,23,29,20,21,22)
DEPENDENCIES=((0x8002BD94,0x8002BE50),(0x8004F6C0,0x8004F784),
              (0x8004F810,0x8004F904),(0x8004F904,0x8004F9C4),
              (0x8004FB28,0x8004FBE4),(0x800265D4,0x800265EC))


def offset(exe,address,size=4):
    if exe[:8]!=b'PS-X EXE':raise ValueError('QoL requires a PS-X executable')
    load,length=struct.unpack_from('<II',exe,0x18)
    result=address-load+0x800
    if length+0x800!=len(exe) or result<0x800 or result+size>len(exe):
        raise ValueError('QoL address is outside this executable module')
    return result


def validate(exe,stock):
    for start,end in DEPENDENCIES:
        a=offset(exe,start,end-start);b=offset(stock,start,end-start)
        if exe[a:a+end-start]!=stock[b:b+end-start]:
            raise ValueError(f'LR swaps conflict with modified native code at {start:08X}')
    # Group/priority/flags influence native ownership resolution. Caps/icons may
    # be balanced without invalidating this patch.
    for index in range(128):
        address=0x800BBE50+10*index
        a=offset(exe,address,6);b=offset(stock,address,6)
        if exe[a:a+6]!=stock[b:b+6]:
            raise ValueError('LR swaps conflict with modified item group/priority metadata')


def emit_wrapper(address):
    m=_Mips()
    def call(target):m.words.extend([0x0C000000|((target>>2)&0x3FFFFFF),0])
    def move(target,source):m.r(source,0,target,0x21)
    def read_absolute(target,where,op=35):m.li(8,where);m.load(target,8,0,op)
    m.i(9,29,29,-64)
    # Reserve the caller's four O32 argument-home words. Native callees may
    # spill A0..A3 there; saved S registers must not overlap those words.
    for register in range(16,23):m.i(43,29,register,16+(register-16)*4)
    m.i(43,29,31,44)
    call(0x8002E3B4) # Keep the intercepted stock UpdateWorld call.
    m.i(43,29,2,48) # Preserve its return value across subsequent native setters.
    for where in (0x801F0060,0x801AC718,0x801F121C,0x801EFBF8):
        read_absolute(9,where);m.branch(5,9,0,'return')
    read_absolute(9,0x801DDA48,37);m.i(12,9,9,0x100);m.branch(5,9,0,'return')
    read_absolute(16,0x801DDA4A,37)
    # Opposing buttons cancel rather than choosing an arbitrary direction.
    m.i(12,16,9,12);m.branch(4,9,0,'items');m.i(9,0,10,12);m.branch(4,9,10,'items')
    m.i(9,0,17,1);m.i(12,16,9,4);m.branch(4,9,0,'weapon_start');m.i(9,0,17,-1)
    m.label('weapon_start');read_absolute(8,0x80119AE8);m.load(10,8,10,37)   # t2 = current weapon category
    weapon_li=len(m.words);m.li(21,0)                                          # s5 = WEAPON_ORDER (fixed below)
    m.i(9,0,20,0)
    m.label('find_weapon');m.r(21,20,8,0x21);m.load(9,8,0,36);m.branch(4,9,10,'weapon_ready')
    m.i(9,20,20,1);m.i(11,20,9,len(WEAPON_ORDER));m.branch(5,9,0,'find_weapon')
    m.i(9,0,20,0);m.i(9,0,9,1);m.branch(5,17,9,'weapon_ready');m.i(9,0,20,-1)   # none: R starts at the first
    m.label('weapon_ready');m.i(9,0,19,len(WEAPON_ORDER))
    m.label('weapon_loop');m.r(20,17,20,0x21)
    m.i(10,20,9,0);m.branch(4,9,0,'weapon_upper');m.i(9,0,20,len(WEAPON_ORDER)-1)
    m.label('weapon_upper');m.i(11,20,9,len(WEAPON_ORDER));m.branch(5,9,0,'weapon_check');m.i(9,0,20,0)
    m.label('weapon_check');m.r(21,20,8,0x21);m.load(18,8,0,36)
    move(4,18);call(0x8004F810);m.i(9,0,9,-1);m.branch(5,2,9,'weapon_set')
    m.i(9,19,19,-1);m.branch(5,19,0,'weapon_loop');m.branch(4,0,0,'items')
    m.label('weapon_set');move(4,18);call(0x8004FB28)
    m.label('items');m.i(12,16,9,3);m.branch(4,9,0,'return');m.i(9,0,10,3);m.branch(4,9,10,'return')
    m.i(9,0,17,1);m.i(12,16,9,1);m.branch(4,9,0,'item_start');m.i(9,0,17,-1)
    m.label('item_start');read_absolute(8,0x80119AE8);m.load(9,8,12,37)
    m.i(11,9,10,128);m.branch(4,10,0,'unknown_group')
    m.r(0,9,10,0,2);m.r(10,9,10,0x21);m.r(0,10,10,0,1)
    m.li(8,0x800BBE50);m.r(8,10,8,0x21);m.load(10,8,0,37)
    # Fix table address after assembly. All branches are position-independent.
    table_li=len(m.words);m.li(21,0)
    m.i(9,0,20,0);m.i(9,0,22,len(ITEM_GROUPS))
    m.label('find_group');m.r(21,20,8,0x21);m.load(9,8,0,36);m.branch(4,9,10,'item_ready')
    m.i(9,20,20,1);m.i(11,20,9,len(ITEM_GROUPS));m.branch(5,9,0,'find_group')
    m.label('unknown_group');m.i(9,0,20,0);m.branch(4,17,0,'item_ready')
    m.i(9,0,9,1);m.branch(5,17,9,'item_ready');m.i(9,0,20,-1)
    m.label('item_ready');m.li(21,0);second_li=len(m.words)-2;m.i(9,0,19,len(ITEM_GROUPS))
    m.label('item_loop');m.r(20,17,20,0x21);m.i(10,20,9,0);m.branch(4,9,0,'item_upper');m.i(9,0,20,len(ITEM_GROUPS)-1)
    m.label('item_upper');m.i(11,20,9,len(ITEM_GROUPS));m.branch(5,9,0,'item_check');m.i(9,0,20,0)
    m.label('item_check');m.r(21,20,8,0x21);m.load(4,8,0,36);call(0x8004F810)
    m.i(9,0,9,-1);m.branch(5,2,9,'item_set');m.i(9,19,19,-1);m.branch(5,19,0,'item_loop');m.branch(4,0,0,'return')
    m.label('item_set');move(4,2);call(0x8004FB84)
    m.label('return')
    for register in range(16,23):m.load(register,29,16+(register-16)*4)
    m.load(2,29,48);m.load(31,29,44);m.i(9,29,29,64);m.words.extend([0x03E00008,0])
    table_address=address+len(m.words)*4
    weapon_address=table_address+len(ITEM_GROUPS)
    for index,where in ((table_li,table_address),(second_li,table_address),(weapon_li,weapon_address)):
        m.words[index]=15<<26|21<<16|((where+0x8000)>>16&0xFFFF)
        m.words[index+1]=9<<26|21<<21|21<<16|(where&0xFFFF)
    tables=bytes(ITEM_GROUPS)+bytes(WEAPON_ORDER)
    return m.finish()+tables+bytes((-len(tables))%4)


def manifest(code,address):
    return {'feature':'lr_swaps','address':address,'size':len(code),
            'sha256':hashlib.sha256(code).hexdigest(),'native_gameplay_verified':False,
            'controls':'L1 previous/R1 next weapon; L2 previous/R2 next item (script order); none while a menu or event runs; Start menu',
            'weapon_order':list(WEAPON_ORDER),
            'item_groups':list(ITEM_GROUPS),'limitations':['Only verified stock item groups; custom grouping conflicts rejected',
            'Native ownership/progressive priority retained; no Lua or inventory writes',
            'Cold boot and emulator/hardware play remain unverified']}
