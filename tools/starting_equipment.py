"""Native new-game item ownership metadata, preserving all other properties."""
import struct
from alundra_memory import parse_exe, runtime_to_offset

TABLE_BYTE = 0x800C7DEA
SUPPORTED_IDS = range(1,90)
INIT_ADDRESS = 0x80031E40
INIT_WORDS = (0x3c01800c,0x00310821,0x90227dea,0,0x30420080,
    0x10400003,0,0x0c013ef9,0x02002021,0x26100001,0x2a020062,
    0x1440fff4,0x26310008)
WEAPON_INIT=0x80031E74
SETTER_ADDRESS=0x8004FB28
SETTER_WORDS=(0x27BDFFE8,0x00802821,0x2402FFFF,0x10A20005,0xAFBF0010,
              0x24A2FFFF,0x2C420006,0x10400005,0,0x3C028012,0x8C429AE8,
              0x08013EDB,0xA445000A)
GETTER_ADDRESS=0x8004F6C0
GETTER_WORDS=(0x3C028012,0x8C429AE8,0x27BDFFE0,0xAFBF0018,
              0x8443000A,0x2402FFFF,0x10620026,0x00602021)
GETTER_NONE_ADDRESS=0x8004F774
GETTER_NONE_WORDS=(0x8FBF0018,0x27BD0020,0x03E00008,0)


DEFAULT_START=(0x01,0x11)   # Dagger, Cloth Armor: Alundra's and Meia's default start (user 2026-10-18)


def native_start(exe):
    from alundra_memory import parse_exe,runtime_to_offset
    info=parse_exe(exe)
    return [i for i in SUPPORTED_IDS if exe[runtime_to_offset(info,TABLE_BYTE+i*8)]&128]


def patch_starting_equipment(exe,item_ids):
    """Select native starting-owned IDs, or None to preserve the imported game.

    Native initialization tries one grant per flagged item. It does not set an
    arbitrary quantity or equip a particular tier: the selected native category
    resolves its highest owned tier. Sword is preferred when selected; otherwise
    the first supported category is selected. No weapons uses native signed-1.
    The unmodelled entries90..97 and each metadata byte's low7 bits stay intact.
    """
    if item_ids is None:
        return bytes(exe),dict(mode='preserve_imported_starting_items',changes=[])
    ids=set(item_ids)
    if any(type(i) is not int or i not in SUPPORTED_IDS for i in ids):
        raise ValueError('Starting item IDs must be supported native IDs1..89')
    info=parse_exe(exe);offset=runtime_to_offset(info,INIT_ADDRESS)
    if offset+4*len(INIT_WORDS)>0x800+info['load_size'] or struct.unpack_from('<13I',exe,offset)!=INIT_WORDS:
        raise ValueError('Native starting-ownership initializer signature changed')
    for address,words in ((SETTER_ADDRESS,SETTER_WORDS),(GETTER_ADDRESS,GETTER_WORDS),
                          (GETTER_NONE_ADDRESS,GETTER_NONE_WORDS)):
        off=runtime_to_offset(info,address)
        if struct.unpack_from('<'+'I'*len(words),exe,off)!=words:
            raise ValueError('Native starting-weapon setter/None getter signature changed')
    weapon_offset=runtime_to_offset(info,WEAPON_INIT)
    call,argument=struct.unpack_from('<II',exe,weapon_offset)
    if call!=0x0C013ECA or argument not in tuple(0x24040000+i for i in range(1,7))+(0x2404FFFF,):
        raise ValueError('Native starting-weapon category initializer changed')
    groups={struct.unpack_from('<h',exe,runtime_to_offset(info,0x800BBE50+i*10))[0] for i in ids}
    weapon_groups=groups.intersection(range(1,7));family=min(weapon_groups) if weapon_groups else -1
    changes=[];data=bytearray(exe)
    for item_id in SUPPORTED_IDS:
        address=TABLE_BYTE+item_id*8;off=runtime_to_offset(info,address)
        old=data[off];new=(old&127)|(128 if item_id in ids else 0)
        if old!=new:
            changes.append(dict(item_id=item_id,native_address=hex(address),
                file_offset=hex(off),before=old,after=new))
            data[off]=new
    new_argument=0x24040000|(family&65535)
    struct.pack_into('<I',data,weapon_offset+4,new_argument)
    return bytes(data),dict(mode='native_starting_owned',selected_item_ids=sorted(ids),
        changes=changes,initializer_address=hex(INIT_ADDRESS),
        initial_equipped_weapon_slot=family,grant_attempts_per_selected_item=1,
        selected_category_address=hex(WEAPON_INIT+4),selected_category_word=f'{new_argument:08x}',
        unmodelled_ids_preserved=list(range(90,98)),gameplay_verified=False,
        limitation='Native capacity/unlock rules still apply; quantity and current tier are not overridden; None path statically accepted, not gameplay-tested')


# ---- New-game HP / MP / Gilder -------------------------------------------------------
# Normal new game (ALUN_CD.EXE US1.1, path after the intro-spawn immediates at
# 0x80031D4C) calls the native setters with immediate arguments:
#   0x80031D8C jal 0x8004F2DC (set max HP, clamps 0..50)   arg at 0x80031D90 = 10
#   0x80031D94 jal 0x8004F3A8 (set HP, clamps 0..max HP)   arg at 0x80031D98 = 10
#   0x80031D9C jal 0x8004F474 (set max MP, clamps 0..4)    arg at 0x80031DA0 = 0
#   0x80031DA4 jal 0x8004F540 (set MP, clamps 0..max MP)   arg at 0x80031DA8 = 0
#   0x80031DAC jal 0x8004F60C (set Gilder, clamps 0..9999) arg at 0x80031DB0 = 0
# Only the argument words change; the calls and native clamps stay intact.
STAT_SITES=(('max_hp',0x80031D8C,0x0C013CB7,50),('hp',0x80031D94,0x0C013CEA,50),
            ('max_mp',0x80031D9C,0x0C013D1D,4),('mp',0x80031DA4,0x0C013D50,4),
            ('gilder',0x80031DAC,0x0C013D83,9999))
STAT_LABELS={'max_hp':'Max HP','hp':'HP','max_mp':'Max MP','mp':'MP','keys':'Keys','gilder':'Gilder'}

# ---- New-game generic Key count (item 0x3D "Key", not Small Key 0x4B) -----------------
# Static, stock ALUN_CD.EXE US1.1: 0x8004FBE4 grants one of item a0 (LH/SH quantity at
# *(0x80119AEC)+id*4+2, capped at the LH at 0x800BBE56+id*10; Key61 cap reads 99).
# The new-game path calls 0x80083E34 at 0x80031E7C (delay slot nop) after the ownership
# loop. A prepended stub replaces that JAL: it grants Key N times, then tail-jumps to
# 0x80083E34 with the original RA. 0 keeps the stock call (no stub).
KEY_ITEM=0x3D;KEY_LIMIT=99;KEY_GIVE=0x8004FBE4
KEY_HOOK=0x80031E7C;KEY_HOOK_WORDS=(0x0C020F8D,0)   # jal 0x80083E34; nop
KEY_TAIL=0x80083E34
STAT_ORDER=('max_hp','hp','max_mp','mp','keys','gilder')
STAT_LIMITS=dict({k:l for k,_,_,l in STAT_SITES},keys=KEY_LIMIT)


def emit_key_stub(count):
    if type(count) is not int or not 1<=count<=KEY_LIMIT:raise ValueError('Key stub count must be 1..99')
    words=(0x27BDFFE8,0xAFBF0014,0xAFB00010,0x24100000|count,
           0x0C000000|(KEY_GIVE>>2&0x3FFFFFF),0x24040000|KEY_ITEM,0x2610FFFF,0x1E00FFFC,0,
           0x8FB00010,0x8FBF0014,0x08000000|(KEY_TAIL>>2&0x3FFFFFF),0x27BD0018)
    return struct.pack('<13I',*words)


def verify_key_hook(exe):
    info=parse_exe(exe)
    if struct.unpack_from('<II',exe,runtime_to_offset(info,KEY_HOOK))!=KEY_HOOK_WORDS:
        raise ValueError('Native new-game key hook site changed')
    cap=struct.unpack_from('<h',exe,runtime_to_offset(info,0x800BBE56+KEY_ITEM*10))[0]
    if cap!=KEY_LIMIT:raise ValueError('Native Key quantity cap differs')


def patch_key_hook(exe,address):
    info=parse_exe(exe);data=bytearray(exe)
    struct.pack_into('<I',data,runtime_to_offset(info,KEY_HOOK),0x0C000000|(address>>2&0x3FFFFFF))
    return bytes(data)


def _stat_argument(word):
    """Decode 'move a0,zero' or 'addiu a0,zero,N'; reject anything else."""
    if word==0x00002021:return 0
    if word>>16==0x2404 and not word&0x8000:return word&0xFFFF
    raise ValueError('Native new-game stat argument changed')


def read_starting_stats(exe):
    info=parse_exe(exe);values={}
    for key,address,call,limit in STAT_SITES:
        off=runtime_to_offset(info,address)
        jal,argument=struct.unpack_from('<II',exe,off)
        if jal!=call:raise ValueError('Native new-game stat call signature changed')
        values[key]=_stat_argument(argument)
    values['keys']=0   # stock new game grants no Key; a prepended stub is not read back
    return values


def validate_starting_stats(stats):
    clean={}
    for key,_,_,limit in STAT_SITES:
        value=stats.get(key)
        if type(value) is not int or not 0<=value<=limit:
            raise ValueError(f'{STAT_LABELS[key]} must be a whole number 0..{limit}')
        clean[key]=value
    keys=stats.get('keys',0)
    if type(keys) is not int or not 0<=keys<=KEY_LIMIT:raise ValueError(f'Keys must be a whole number 0..{KEY_LIMIT}')
    clean['keys']=keys
    if clean['max_hp']<1:raise ValueError('Max HP must be at least 1')
    if clean['hp']>clean['max_hp']:raise ValueError('HP cannot exceed Max HP')
    if clean['mp']>clean['max_mp']:raise ValueError('MP cannot exceed Max MP')
    return clean


def patch_starting_stats(exe,stats):
    """Return (exe, report); None preserves the imported game's values."""
    if stats is None:return bytes(exe),dict(mode='preserve_imported_starting_stats',changes=[])
    stats=validate_starting_stats(stats);before=read_starting_stats(exe)
    info=parse_exe(exe);data=bytearray(exe);changes=[]
    for key,address,_,_ in STAT_SITES:
        if stats[key]==before[key]:continue   # keys: see emit_key_stub (editor_qol block)
        off=runtime_to_offset(info,address+4)
        word=0x00002021 if stats[key]==0 else 0x24040000|stats[key]
        struct.pack_into('<I',data,off,word)
        changes.append(dict(stat=key,native_address=hex(address+4),file_offset=hex(off),before=before[key],after=stats[key]))
    return bytes(data),dict(mode='native_new_game_stats',values=stats,changes=changes,
        gameplay_verified=False,limitation='Normal new game only; native setter clamps still apply. Story scripts that later change HP/MP/Gilder still run.')
