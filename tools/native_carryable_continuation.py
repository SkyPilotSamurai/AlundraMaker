"""Experimental retained native E2 animation; never an enemy HP query."""
import hashlib,struct
from event_vm_compatibility import STOCK_EXE_SHA256,_read_virtual,DISPATCH_TABLE_ADDRESS
from project_state_runtime import _Mips
from native_injection_stack import protect
E2=0x800815E8
JAR_RECORD='2018333b01c0235e520200000000000000000000'
WORDS=(0x27BDFFE8,0xAFBF0010,0x8C820088,0x24050002,0x14450005,0x24020001,
       0x8C8300AC,0,0x10620006,0,0x8C820184,0,0x30420004,0x10400005,
       0x2403FFCF,0x0C00EBB9,0x2405FFFF,0x08020592,0,0x8C82006C,
       0xAC850088,0x34420040,0x00431024,0xAC82006C,0x8FBF0010,
       0x27BD0018,0x03E00008,0)

def verify_source(exe):
 if hashlib.sha256(exe).hexdigest()!=STOCK_EXE_SHA256:raise ValueError('Exact retail carryable controller required')
 raw=struct.pack('<28I',*WORDS)
 if _read_virtual(exe,E2,len(raw))!=raw:raise ValueError('Native E2 controller differs')
 return {'module':'ALUN_CD.EXE','source_sha256':STOCK_EXE_SHA256,'native_E2_address':E2,
         'native_E2_length':len(raw),'native_E2_sha256':hashlib.sha256(raw).hexdigest(),
         'native_destroy_address':0x8003AEE4,'native_fields':{'animation':{'offset':0x88,'width':32},'animation_complete':{'offset':0xAC,'width':32},'terrain_flags_184':{'offset':0x184,'width':32,'mask':4,'name_basis':'Source-reported CombinedVramFlagsAND; exact bit meaning remains unnamed'},'flags':{'offset':0x6C,'width':32}},
         'hypothesis':'Retain native E2 until animation is complete; then authored continuation and native E handback. Raw terrain184 bit4 has no animation wait. Requires actual positive and negative evidence.'}

def verify_jar_source(datas):
 from native_class_placement import record_cluster
 from event_vm_compatibility import sprite_callbacks
 row=record_cluster(datas,21)['entities'][1]
 callbacks=sprite_callbacks(datas,21,291)
 if row.hex()!=JAR_RECORD or callbacks!=[('A',0),('C',23),('D',0),('E',2),('F',0)]:
  raise ValueError('Recovered jar291 native source differs')
 return {'catalogue':291,'donor_map':21,'donor_entity':1,'record_hex':JAR_RECORD,'sprite_callbacks':callbacks}

def compile_jar(continuation):
 return {'E':bytes((0xE8,))+bytes(continuation)+bytes((0x40,4,0,0xff))},{
  'catalogue':291,'native_E2_retained':True,'native_C_retained':True,'native_F_retained':True,
  'optional_runtime_feature':'carryable_e2','native_E_handoff':[0x40,4,0],
  'continuation_lifetime':'native actor lifetime','native_contents_retained':True,
  'evidence':['data/2026-10-06-jar-native-E-production-runtime.json','data/2026-10-06-jar-native-E-production-unload-runtime.json','data/2026-10-06-jar-291-editor-build-ui-audit.json'],
  'limitations':['Other attack families and terrain184 bit4 branch need independent gameplay evidence'],
  'gameplay_verified':False}

def emit():
 m=_Mips()
 m.li(8,0x801AC6F8);m.r(5,8,9,0x2B);m.branch(5,9,0,'invalid')
 m.li(8,0x801B6BF8);m.r(5,8,9,0x2B);m.branch(4,9,0,'invalid')
 m.load(8,5,0x10);m.i(9,0,9,3);m.branch(5,8,9,'invalid')
 # Finish only when native E2 would destroy immediately. Otherwise invoke
 # its real callback, preserving the interpreter argument registers and RA.
 m.load(8,5,0x184);m.i(12,8,8,4);m.branch(5,8,0,'ready')
 m.load(8,5,0x88);m.i(9,0,9,2);m.branch(5,8,9,'native')
 m.load(8,5,0xAC);m.i(9,0,9,1);m.branch(4,8,9,'ready')
 m.label('native');m.i(9,29,29,-24)
 for reg,off in ((31,20),(4,16),(5,12),(6,8),(7,4)):m.i(43,29,reg,off)
 m.r(5,0,4,0x21);m.words.extend((0x0C000000|(E2>>2&0x3ffffff),0))
 for reg,off in ((31,20),(4,16),(5,12),(6,8),(7,4)):m.load(reg,29,off)
 m.i(9,29,29,24);m.i(9,0,2,0);m.words.extend((0x03E00008,0))
 m.label('ready');m.i(9,0,2,1);m.words.extend((0x03E00008,0))
 m.label('invalid');m.i(9,0,2,0);m.words.extend((0x03E00008,0))
 return m.finish()

def inject(exe):
 contract=verify_source(exe);load,size=struct.unpack_from('<II',exe,0x18)
 if load!=0x80020000 or len(exe)!=size+0x800:raise ValueError('Experimental load differs')
 output=bytearray(exe);site=DISPATCH_TABLE_ADDRESS+0xE8*4-load+0x800
 if struct.unpack_from('<I',exe,site)[0]!=0x8003DBD0:raise ValueError('E8 unused fallback differs')
 code=emit();new_load=load-0x800;prefix=bytearray(0x800);prefix[:len(code)]=code
 struct.pack_into('<I',output,site,new_load);output[0x800:0x800]=prefix
 struct.pack_into('<II',output,0x18,new_load,size+0x800);output,stack=protect(output)
 return output,{'experimental':True,'opcode':0xE8,'width':1,'handler_address':new_load,'handler_bytes':len(code),'handler_sha256':hashlib.sha256(code).hexdigest(),'native_source':contract,'native_stack':stack,'runtime_verified':False}
