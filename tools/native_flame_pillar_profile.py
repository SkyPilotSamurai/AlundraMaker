"""Source-guarded316 passive C28 cycle; authored continuations remain experimental."""
SOURCE_MAP=52
SOURCE_ENTITY=28
SOURCE_RECORD=bytes.fromhex('1624213901c33c306a0600009c00000000000000')
CONTROLLER=bytes.fromhex('bd61011a021c011a013778001a031c011a00be6101373c00bd61011a021c011a01373c001a031c011a00be6101377849ff')

def audit_native_handlers(exe):
 import hashlib,struct
 from alundra_memory import parse_exe
 if hashlib.sha256(exe).hexdigest()!='12f12eafa3e34dac6aca40b52f4f85f95811d40de7e48db77c52a35aa18833a3':raise ValueError('Exact USA1.1 native EXE required')
 load=parse_exe(exe)['load_address'];table=0x8009B814-load+0x800;rows=[]
 for opcode in (0x1A,0x1C,0x37,0x49,0xBD,0xBE):
  address=struct.unpack_from('<I',exe,table+opcode*4)[0];offset=address-load+0x800
  count=4 if opcode==0x49 else 12
  rows.append({'opcode':f'{opcode:02X}','native_virtual_address':f'{address:08X}','exe_file_offset':offset,'instruction_slice_words':[f'{w:08X}' for w in struct.unpack_from('<'+str(count)+'I',exe,offset)]})
 return {'module':'Retail USA1.1 ALUN_CD.EXE','sha256':hashlib.sha256(exe).hexdigest(),'dispatch_table':'8009B814','bounded_slices':rows,
  'derived_contracts':{'49':'LW context(a3)+0 and+4; returns SUBU(+0,+4) in v0. No operand read. Runtime cycle restart is separately observed.',
   'BD':'LBU bytes1/2, combines little-endian16 operand and calls8004A128; returns3.',
   'BE':'LBU bytes1/2, combines little-endian16 operand and calls8004A7B4; returns3.'},
  'scope':'Bounded dispatcher instruction slices and arithmetic derivations; no complete render/audio function claim'}

def verify_source(data):
 from native_class_placement import record_cluster
 from editor_session import EditSession
 from event_editor import instructions
 from event_vm_compatibility import sprite_callbacks
 if record_cluster(data,52)['entities'][28]!=SOURCE_RECORD:raise ValueError('Flame pillar316 source record differs')
 actual=b''.join(bytes(data[p:p+n]) for p,_,n in instructions(EditSession.readonly(data),52,'C 28'))
 if actual!=CONTROLLER:raise ValueError('Flame pillar316 C28 source differs')
 if sprite_callbacks(data,52,316)!=[('A',0),('C',0),('D',0),('E',0),('F',0)]:raise ValueError('Flame pillar316 native callbacks differ')
 return True

def compile_pillar(after=b''):
 return {'C':CONTROLLER[:-2]+after+CONTROLLER[-2:]},{'catalogue':316,'source_map':52,'source_entity':28,'source_program':'C 28','source_room_dependencies':[],
  'source_controller_hex':CONTROLLER.hex(),'native_callback_selectors':[0,0,0,0,0],
  'authored_continuation_position':'After complete alternating native animation/wait cycle, before native49 restart',
  'production_enabled':False,'gameplay_verified':False,
  'uncertainties':['Native contact damage and Ice Rod reaction require actual controls','Native49 restart semantics require runtime verification','No hardware/save/audio claim']}

def compile_passive_pillar():
 programs,report=compile_pillar()
 report.update(production_enabled=True,authored_contents_supported=False,
               uncertainties=['Ice projectile collision/impact not proven; no immunity claim','No hardware/save/audio claim'])
 return programs,report
