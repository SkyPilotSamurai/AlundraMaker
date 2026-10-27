"""Private session state in a guarded stock-EXE prepend; no stock flags reused.

Injected E0..E4 handlers are original MIPS code, not recovered vanilla opcodes.
The array is initialized by executable loading and survives ordinary map changes.
EXE reload resets it. Since 2026-10-22 a companion card file keeps it per save slot
(native_save_persistence); the native save block itself is unchanged.
"""
import hashlib
import struct
from copy import deepcopy
from project_state_registry import ProjectStateRegistry,LIFETIME

STOCK_SHA='12f12eafa3e34dac6aca40b52f4f85f95811d40de7e48db77c52a35aa18833a3'
DISPATCH=0x8009B814
OPCODES={0xE0:4,0xE1:4,0xE2:7,0xE3:7,0xE4:8}
COMPARISONS={'==':0,'!=':1,'<':2,'<=':3,'>':4,'>=':5}


def layout(registry):
    return {kind:{row['id']:slot for slot,row in enumerate(registry.options(kind))}
            for kind in ('switches','variables')}


def _signed(value):
    if type(value) is not int or not -2147483648<=value<=2147483647:
        raise ValueError('Project variable operands must be signed32')
    return value


def compile_project_command(command,registry,slots=None):
    slots=slots or layout(registry);kind=command.get('type')
    if kind=='set_switch':
        row=registry.resolve('switches',command);value=command.get('value')
        if type(value) is not bool:raise ValueError('Project switch value must be ON/OFF')
        return struct.pack('<BHB',0xE0,slots['switches'][row['id']],value)
    if kind=='set_variable':
        row=registry.resolve('variables',command);value=_signed(command.get('value'))
        operation=command.get('operation','set')
        if operation not in ('set','add','subtract'):
            raise ValueError('Private variables currently support set/add/subtract only')
        if operation=='subtract':
            value=(-value)&0xFFFFFFFF
            if value>=0x80000000:value-=0x100000000
        return struct.pack('<BHi',0xE2 if operation=='set' else 0xE3,slots['variables'][row['id']],value)
    raise ValueError('No private-state compiler for this command')


def compile_project_condition(condition,registry,slots=None):
    slots=slots or layout(registry);kind=condition.get('type')
    if kind=='switch':
        row=registry.resolve('switches',condition);value=condition.get('value',True)
        comparison=condition.get('operator','==')
        if type(value) is not bool or comparison not in ('==','!='):
            raise ValueError('Project switch condition needs ON/OFF and ==/!=')
        return struct.pack('<BHB',0xE1,slots['switches'][row['id']],value if comparison=='==' else not value)
    if kind=='variable':
        row=registry.resolve('variables',condition);op=condition.get('operator','==')
        if op not in COMPARISONS:raise ValueError('Project variable comparison must be == != < <= > >=')
        return struct.pack('<BHB i',0xE4,slots['variables'][row['id']],COMPARISONS[op],_signed(condition.get('value')))
    raise ValueError('No private-state compiler for this condition')


class _Mips:
    def __init__(self):self.words=[];self.labels={};self.branches=[]
    def i(self,op,rs,rt,im):self.words.append(op<<26|rs<<21|rt<<16|(im&65535))
    def r(self,rs,rt,rd,funct,shift=0):self.words.append(rs<<21|rt<<16|rd<<11|shift<<6|funct)
    def li(self,rt,value):self.i(15,0,rt,(value+0x8000)>>16);self.i(9,rt,rt,value)
    def load(self,rt,rs,offset,op=35):self.i(op,rs,rt,offset);self.words.append(0)
    def branch(self,op,rs,rt,label):self.branches.append((len(self.words),label));self.i(op,rs,rt,0);self.words.append(0)
    def label(self,label):self.labels[label]=len(self.words)
    def finish(self):
        for index,label in self.branches:
            delta=self.labels[label]-index-1
            if not -32768<=delta<=32767:raise ValueError('Injected branch exceeds signed16')
            self.words[index]|=delta&65535
        return struct.pack('<'+'I'*len(self.words),*self.words)


def emit_handler(opcode,state_address,switch_count,variable_count):
    if (type(opcode) is not int or opcode not in OPCODES
            or type(state_address) is not int or not 0x80010000<=state_address<=0x8001F400 or state_address%4
            or any(type(n) is not int or not 0<=n<=128 for n in (switch_count,variable_count))):
        raise ValueError('Invalid private-state handler layout')
    m=_Mips();variable=opcode>=0xE2;count=variable_count if variable else switch_count
    # Native a2 points to a current-opcode pointer, a3 to process scratch.
    m.load(8,6,0);m.load(9,8,1,36);m.load(13,8,2,36)
    m.r(0,13,13,0,8);m.r(9,13,9,0x25)
    m.i(11,9,13,count);m.branch(4,13,0,'invalid')
    m.r(0,9,9,0,2);m.li(10,state_address+(512 if variable else 0));m.r(10,9,10,0x21)
    if opcode in (0xE0,0xE1):
        m.load(12,8,3,36);m.i(12,12,12,1)
    else:
        value_offset=4 if opcode==0xE4 else 3
        m.load(12,8,value_offset,36)
        for byte in range(1,4):
            m.load(13,8,value_offset+byte,36);m.r(0,13,13,0,8*byte);m.r(12,13,12,0x25)
    if opcode in (0xE0,0xE2):m.i(43,10,12,0)
    elif opcode==0xE3:
        m.load(11,10,0);m.r(11,12,12,0x21);m.i(43,10,12,0)
    elif opcode==0xE1:
        m.load(11,10,0);m.r(11,12,15,0x26);m.i(11,15,15,1);m.i(43,7,15,0x2C)
    else:
        m.load(11,10,0);m.load(14,8,3,36)
        for op in range(6):
            m.i(9,0,13,op);m.branch(4,14,13,'compare'+str(op))
        m.branch(4,0,0,'invalid')
        for op in range(6):
            m.label('compare'+str(op))
            if op in (0,1):
                m.r(11,12,15,0x26)
                if op==0:m.i(11,15,15,1)
                else:m.r(0,15,15,0x2B)
            elif op in (2,5):m.r(11,12,15,0x2A)
            else:m.r(12,11,15,0x2A)
            if op in (3,5):m.i(14,15,15,1)
            m.i(43,7,15,0x2C);m.branch(4,0,0,'return')
    m.branch(4,0,0,'return');m.label('invalid')
    if opcode in (0xE1,0xE4):m.i(43,7,0,0x2C)
    m.label('return');m.i(9,0,2,OPCODES[opcode]);m.words.extend([0x03E00008,0])
    return m.finish()


RAISE_MAX_MP=0xEA   # EA nn: raise max MP by nn (native setter clamps 0..4)


def emit_raise_max_mp():
    jal=lambda a:0x0C000000|((a>>2)&0x3FFFFFF)
    words=[0x27BDFFE8,0xAFBF0010,0xAFA60014,          # addiu sp,-24; sw ra,16; sw a2,20
           jal(0x8004F45C),0,                          # v0 = max MP
           0x8FA60014,0,0x8CC80000,0,0x91090001,0,     # t0=[a2]; t1=byte[t0+1]
           0x00492021,0x28880005,0x15000002,0,0x24040004,   # a0=v0+t1; if a0>=5 a0=4
           jal(0x8004F474),0,                          # set max MP
           jal(0x8004CA2C),0,                          # refresh the status display
           0x8FBF0010,0x24020002,0x03E00008,0x27BD0018]
    return struct.pack('<%dI'%len(words),*words)


def inject_private_state(exe,document,*,optional_features=(),route_resume_slots=0,melzas_places=None,boss_places=None,player_swap=None):
    if hashlib.sha256(exe).hexdigest()!=STOCK_SHA:
        raise ValueError('New private-state injection requires exact stock ALUN_CD.EXE; modified executables need a composable allocator audit')
    registry=ProjectStateRegistry(deepcopy(document));registry.validate_references();slots=layout(registry)
    load,size=struct.unpack_from('<II',exe,0x18)
    if load!=0x80020000 or len(exe)!=size+0x800:raise ValueError('Unexpected stock executable layout')
    prefix=bytearray(0x800);state=bytearray(1024)
    for kind,base in (('switches',0),('variables',512)):
        for row in registry.options(kind):struct.pack_into('<i',state,base+slots[kind][row['id']]*4,int(row['initial_value']))
    prefix[:0]=state;state_address=load-len(prefix);handlers={}
    output=bytearray(exe)
    optional_features=tuple(optional_features)
    if any(feature not in ('enemy_hp_zero','actor_route_resume','carryable_e2','custom_ai','hit_follow') for feature in optional_features) or len(set(optional_features))!=len(optional_features):
        raise ValueError('Unknown or duplicated optional private-runtime feature')
    resume_report=None
    if 'actor_route_resume' in optional_features:
        from native_route_resume_runtime import verify_contract
        if type(route_resume_slots) is not int or not 1<=route_resume_slots<=16:raise ValueError('Route resume requires1..16 declared instance slots')
        contract=verify_contract(exe);resume_state=bytes(route_resume_slots*80)
        prefix[:0]=resume_state;resume_address=load-len(prefix)
        resume_report={'slot_count':route_resume_slots,'slot_stride':80,'storage_address':resume_address,
            'storage_size':len(resume_state),'initial_sha256':hashlib.sha256(resume_state).hexdigest(),
            'opcodes':{'230':2,'231':2},'native_contract':contract,'instance_identity_guard':True,'runtime_verified':False}
    elif route_resume_slots!=0:raise ValueError('Route snapshot slots require the explicit optional feature')
    selected=list(OPCODES)
    if 'enemy_hp_zero' in optional_features:selected.append(0xE5)
    if resume_report:selected.extend((0xE6,0xE7))
    carry_report=None
    if 'carryable_e2' in optional_features:
        from native_carryable_continuation import verify_source
        carry_report=verify_source(exe);selected.append(0xE8)
    if 'custom_ai' in optional_features:
        selected.extend((0xE9,0xEC,0xED,0xEE));prefix[:0]=bytes(256);hit_address=load-len(prefix)   # per-slot hit counters (native_custom_ai)
    if 'hit_follow' in optional_features:selected.append(0xEF)   # EF sel: hit spot follows its object (native_hit_follow)
    selected.append(RAISE_MAX_MP)
    selected.extend((0xF0,0xF1))   # step-on switch press filters (native_press_filter, user 2026-10-26)
    selected.append(0xF2)   # portrait of a database NPC not on the map (native_portrait_speaker)
    for op in selected:
        offset=DISPATCH+op*4-load+0x800
        if struct.unpack_from('<I',exe,offset)[0]!=0x8003DBD0:
            raise ValueError('Private opcode slot is not the verified stock fallback')
        if op==0xE5:
            from native_enemy_death import verify_native_contract,emit_hp_zero_query
            verify_native_contract(exe);code=emit_hp_zero_query()
        elif op in (0xE6,0xE7):
            from native_route_resume_runtime import emit_indexed
            code=emit_indexed(op,resume_address,route_resume_slots)
        elif op==0xE8:
            from native_carryable_continuation import emit
            code=emit()
        elif op==RAISE_MAX_MP:code=emit_raise_max_mp()
        elif op in (0xF0,0xF1):
            from native_press_filter import emit_ride,emit_box
            code=emit_ride() if op==0xF0 else emit_box()
        elif op==0xF2:
            from native_portrait_speaker import verify as verify_portrait,emit as emit_portrait
            verify_portrait(exe,load);code=emit_portrait()
        elif op==0xEF:
            from native_hit_follow import emit as emit_follow
            code=emit_follow()
        elif op==0xE9:
            from native_custom_ai import emit_range
            code=emit_range()
        elif op==0xEC:
            from native_custom_ai import emit_speed
            code=emit_speed()
        elif op in (0xED,0xEE):
            from native_custom_ai import emit_hits,emit_hit
            code=(emit_hits if op==0xED else emit_hit)(hit_address)
        else:code=emit_handler(op,state_address,len(slots['switches']),len(slots['variables']))
        prefix[:0]=code;address=load-len(prefix)
        struct.pack_into('<I',output,offset,address)
        handlers[op]={'address':address,'size':len(code),'sha256':hashlib.sha256(code).hexdigest()}
    swap_report=None
    if player_swap is not None:
        # EB nn: Change Player Character (native_player_swap; XOR of the game data and the Meia costume)
        from native_player_swap import OPCODE,blocks,NO_DASH,verify_exe
        verify_exe(exe)
        if player_swap[2] and struct.unpack_from('<I',exe,NO_DASH-load+0x800)[0]!=0x30420010:raise ValueError('Meia no-dash: unexpected stock code')
        offset=DISPATCH+OPCODE*4-load+0x800
        if struct.unpack_from('<I',exe,offset)[0]!=0x8003DBD0:raise ValueError('Private opcode slot is not the verified stock fallback')
        # its 4 KB read buffer shares the save companion buffer (native_save_persistence, 4736 bytes):
        # one is used only while saving/loading, the other only during the swap (user 2026-10-26)
        import native_save_persistence as nsp
        prefix[:0]=nsp.data_block();shared_buffer=load-len(prefix)
        def place(block):
            if len(block)==CHUNK and not placed:
                placed.append(1);return shared_buffer
            prefix[:0]=block;return load-len(prefix)
        from native_player_swap import CHUNK
        placed=[]
        if CHUNK>nsp.SIZE:raise ValueError('Player swap buffer is larger than the shared save buffer')
        address,swap_report=blocks(player_swap[0],player_swap[1],place,player_swap[2])
        struct.pack_into('<I',output,offset,address)
        handlers[OPCODE]={'address':address,'size':swap_report['code_size'],'sha256':swap_report['code_sha256']}
    melzas_report=None
    if melzas_places:
        # Melzas placed by events: his teleport points follow the placement (native_melzas_points)
        from native_melzas_points import verify as verify_melzas,data_block,emit as emit_melzas,patch_sites
        verify_melzas(exe)
        block=data_block(melzas_places);prefix[:0]=block;list_address=load-len(prefix)
        scratch_address=list_address+len(block)-32
        code,_=emit_melzas(list_address,scratch_address);prefix[:0]=code;code_address=load-len(prefix)
        patch_sites(output,code_address,load)
        from native_melzas_points import emit_centre,patch_centre
        centre_size=len(emit_centre(list_address,0,exe)[0]);centre_address=load-len(prefix)-centre_size
        centre,stubs=emit_centre(list_address,centre_address,exe);prefix[:0]=centre
        if load-len(prefix)!=centre_address:raise ValueError('Melzas centre code moved while placing it')
        patch_centre(output,stubs,load)
        melzas_report={'maps':{str(m):list(v) for m,v in sorted(melzas_places.items())},'code_address':code_address,'centre_address':centre_address,
                       'list_address':list_address,'runtime_verified':False}
    boss_report=None
    if boss_places:
        # other event-placed bosses: their native fixed positions follow the placement (native_boss_points)
        import native_boss_points as nbp
        nbp.verify(exe,boss_places)
        block,where=nbp.data_block(boss_places);prefix[:0]=block;block_address=load-len(prefix)
        lists={c:block_address+o for c,o in where.items()}
        boss_size=len(nbp.emit(lists,0,exe)[0]);boss_address=load-len(prefix)-boss_size
        code,stubs=nbp.emit(lists,boss_address,exe);prefix[:0]=code
        nbp.patch(output,exe,lists,stubs,load)
        boss_report={'classes':{str(c):{str(m):list(v) for m,v in sorted(rows.items())} for c,rows in sorted(boss_places.items())},
                     'code_address':boss_address,'sites':[row[0] for c in boss_places for row in nbp.SITES[c]],
                     'runtime_verified':False}
    # Project state in the memory-card save (native_save_persistence, 2026-10-22): a companion
    # card file per save block; the native block itself is unchanged.
    import native_save_persistence as nsp
    nsp.verify(exe,load)
    initial_address=None   # ALUN_CD.EXE is loaded fresh for every game start: the state starts initial
    if player_swap is not None:buffer_address=shared_buffer   # placed with the player swap above
    else:prefix[:0]=nsp.data_block();buffer_address=load-len(prefix)
    save_code,load_code=nsp.emit(state_address,initial_address,buffer_address,buffer_address+nsp.SIZE)
    prefix[:0]=save_code;save_hook=load-len(prefix);prefix[:0]=load_code;load_hook=load-len(prefix)
    nsp.patch(output,load,save_hook,load_hook)
    # Death retry puts the project state back too (native_retry_state, user 2026-10-26): a snapshot that
    # starts initial, takes a loaded save's state, and is copied back when the game retries.
    import native_retry_state as nrs
    nrs.verify(exe,load)
    prefix[:0]=bytes(state);snapshot_address=load-len(prefix)
    code=nrs.emit_call_then_copy(load_hook,state_address,snapshot_address);prefix[:0]=code;loaded_hook=load-len(prefix)
    code=nrs.emit_call_then_copy(nrs.RESTORE,snapshot_address,state_address);prefix[:0]=code;retry_hook=load-len(prefix)
    struct.pack_into('<I',output,nsp.LOAD_SITE-load+0x800,nrs.jal(loaded_hook))
    struct.pack_into('<I',output,nrs.RETRY_SITE-load+0x800,nrs.jal(retry_hook))
    persistence={'companion_file':nsp.NAME.decode(),'buffer_address':buffer_address,'initial_address':initial_address,
        'save_hook':save_hook,'load_hook':load_hook,'sites':[nsp.SAVE_SITE,nsp.LOAD_SITE],'retry_site':nrs.RETRY_SITE,'retry_hook':retry_hook,'loaded_hook':loaded_hook,'snapshot_address':snapshot_address,'entry_bytes':nsp.ENTRY,'file_bytes':nsp.SIZE}
    expansion=(len(prefix)+0x7FF)&~0x7FF;new_load=load-expansion
    if new_load<0x80010000:raise ValueError('Private-state code exceeds reserved low-memory allocation bound')
    prefix[:0]=bytes([255])*(expansion-len(prefix));output[0x800:0x800]=prefix
    struct.pack_into('<II',output,0x18,new_load,size+expansion)
    from native_injection_stack import protect
    output,stack_report=protect(output)
    manifest={'format':'alundra-private-state-injection-v1','stock_sha256':STOCK_SHA,
        'result_sha256':hashlib.sha256(output).hexdigest(),'state_address':state_address,
        'state_size':1024,'state_initial_sha256':hashlib.sha256(state).hexdigest(),
        'slots':slots,'handlers':{str(op):row for op,row in handlers.items()},
        'new_load':new_load,'expansion':expansion,'lifetime':LIFETIME,
        'allocator':'guarded prepend; native descending stack relocated below load; minimum80018000',
        'memory_card_persistent':True,'save_persistence':persistence,'gameplay_verified':False}
    manifest['native_stack']=stack_report
    if optional_features:manifest['optional_features']=list(optional_features)
    if resume_report:manifest['route_resume']=resume_report
    if carry_report:manifest['carryable_e2']=carry_report
    if melzas_report:manifest['melzas_points']=melzas_report
    if boss_report:manifest['boss_points']=boss_report
    if swap_report:manifest['player_swap']=swap_report
    return bytes(output),manifest


def verify_private_state_injection(exe,manifest):
    if manifest.get('format')!='alundra-private-state-injection-v1' or hashlib.sha256(exe).hexdigest()!=manifest.get('result_sha256'):
        raise ValueError('Private-state injected module differs from its exact export manifest')
    load,size=struct.unpack_from('<II',exe,0x18)
    if load!=manifest['new_load'] or size+0x800!=len(exe):raise ValueError('Private-state module load layout changed')
    if 'carryable_e2' in manifest.get('optional_features',[]):
        from native_carryable_continuation import E2,WORDS
        expected=struct.pack('<28I',*WORDS);offset=E2-load+0x800
        if exe[offset:offset+len(expected)]!=expected:raise ValueError('Retained native carryable E2 controller changed')
    if 'actor_route_resume' in manifest.get('optional_features',[]):
        resume=manifest.get('route_resume',{})
        count=resume.get('slot_count');address=resume.get('storage_address');length=resume.get('storage_size')
        if type(count) is not int or not 1<=count<=16 or length!=count*80 or type(address) is not int or not load<=address<=load+size-length:
            raise ValueError('Private route snapshot layout differs')
        initial=exe[address-load+0x800:address-load+0x800+length]
        if initial!=bytes(length) or hashlib.sha256(initial).hexdigest()!=resume.get('initial_sha256'):
            raise ValueError('Private route snapshots must start empty')
    for op,row in manifest['handlers'].items():
        op=int(op);address=row['address'];offset=address-load+0x800
        if struct.unpack_from('<I',exe,DISPATCH+op*4-load+0x800)[0]!=address:
            raise ValueError('Private-state dispatch target changed')
        if hashlib.sha256(exe[offset:offset+row['size']]).hexdigest()!=row['sha256']:
            raise ValueError('Private-state handler code changed')
    return {'private_state_handlers_compatible':True,'opcodes':sorted(int(op) for op in manifest['handlers']),
            'lifetime':LIFETIME,'memory_card_persistent':bool(manifest.get('memory_card_persistent')),'gameplay_verified':False}
