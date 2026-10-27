"""Local compiled dungeon projects: fingerprinted, compressed variable-size deltas."""
import base64,hashlib,json,zlib
from pathlib import Path
from editor_session import EditSession
from map_block_repack import pointers,sections
from map_loader_constraints import validate_layout
ROOT=Path(__file__).resolve().parents[1]
LIMIT=200*1024*1024

def fingerprint(data):return hashlib.sha256(data).hexdigest()
def encode_delta(original,data):
 # Chunk boundaries keep this linear for large DATAS without a costly sequence matcher.
 a=0;end=min(len(original),len(data))
 while a+4096<=end and original[a:a+4096]==data[a:a+4096]:a+=4096
 b=0
 while b+4096<=end-a and original[len(original)-b-4096:len(original)-b]==data[len(data)-b-4096:len(data)-b]:b+=4096
 payload=bytes(data[a:len(data)-b if b else len(data)])
 return dict(base_sha256=fingerprint(original),result_sha256=fingerprint(data),result_size=len(data),start=a,remove=len(original)-a-b,payload=base64.b64encode(zlib.compress(payload)).decode('ascii'))
def decode_delta(original,p):
 if p['base_sha256']!=fingerprint(original):raise ValueError('Compiled mod base mismatch')
 a,n,size=p['start'],p['remove'],p['result_size']
 if any(type(v) is not int for v in (a,n,size)) or not 0<=a<=len(original) or not 0<=n<=len(original)-a or not 0<size<=LIMIT:raise ValueError('Invalid compiled mod bounds')
 expected=size-len(original)+n
 if not 0<=expected<=LIMIT:raise ValueError('Invalid compiled payload size')
 obj=zlib.decompressobj();raw=obj.decompress(base64.b64decode(p['payload'],validate=True),expected+1)
 if len(raw)!=expected or not obj.eof or obj.unused_data or obj.unconsumed_tail:raise ValueError('Invalid compiled payload')
 result=bytes(original[:a])+raw+bytes(original[a+n:])
 if fingerprint(result)!=p['result_sha256']:raise ValueError('Compiled mod result mismatch')
 return result

def compiled_session(original,data,path=None):
 # Stock provenance is mandatory; the imported structure may be larger than stock.
 EditSession(original)
 validate_layout(data);table=pointers(data)
 for m in range(483):sections(data[table[m]:table[m+1]])
 session=EditSession(data,path,verify=False);session.export_original=bytes(original)
 session.compiled_project=True;session.extra_files={}
 return session

def open_citadel(path):
 from mod_export import read_datas
 path=Path(path);manifest_path=path.with_suffix('.build.json')
 if not manifest_path.is_file():raise ValueError('Choose a compiled Citadel BIN with its .build.json manifest')
 manifest=json.loads(manifest_path.read_text());data=read_datas(path);exe=read_datas(path,'ALUN_CD.EXE')
 if fingerprint(data)!=manifest.get('result_datas_sha256') or fingerprint(exe)!=manifest.get('result_exe_sha256'):raise ValueError('Citadel build differs from its manifest')
 folder=ROOT/'private-inputs/disc';original=(folder/'DATA/DATAS.BIN').read_bytes()
 session=compiled_session(original,data,path)
 extra=EditSession((folder/'ALUN_CD.EXE').read_bytes(),verify=False);extra.data=bytearray(exe)
 session.extra_files['ALUN_CD.EXE']=extra
 balance=read_datas(path,'DATA/BALANCE.BIN');stock=(folder/'DATA/BALANCE.BIN').read_bytes()
 if balance!=stock:
  from enemy_definition import BalanceSession
  extra=BalanceSession(stock);extra.data=bytearray(balance);session.extra_files['DATA/BALANCE.BIN']=extra
 return session

def project_document(session,name,map_id):
 return dict(format='alundra-mod-v3',name=name,map_id=map_id,patch=encode_delta(session.export_original,session.data),extra_files={key:encode_delta(extra.original,extra.data) for key,extra in session.extra_files.items()})
def restore_project(original,doc,path=None):
 session=compiled_session(original,decode_delta(original,doc['patch']),path)
 for name,p in doc.get('extra_files',{}).items():
  if name not in ('ALUN_CD.EXE','DATA/BALANCE.BIN'):raise ValueError('Unsupported compiled mod file')
  stock=(ROOT/'private-inputs/disc'/name).read_bytes();data=decode_delta(stock,p)
  if name=='DATA/BALANCE.BIN':
   from enemy_definition import BalanceSession
   extra=BalanceSession(stock)
  else:extra=EditSession(stock,verify=False)
  extra.data=bytearray(data);session.extra_files[name]=extra
 if 'ALUN_CD.EXE' not in session.extra_files:raise ValueError('Compiled dungeon mod lacks its executable')
 return session
