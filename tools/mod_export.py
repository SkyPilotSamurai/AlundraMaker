"""Named edit projects and isolated disc rebuilds using bundled mkpsxiso tools."""
import hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
from disc_inventory import Disc
from editor_session import EditSession
ROOT=Path(__file__).resolve().parents[1]

def build_snapshot(session,content_database=None):
 """Freeze the complete authoring state for a background disc build.

 Preserve session layout methods and compiled-project source identity. Dropping
 the database here would silently omit authored events from the GUI build.
 """
 from copy import copy,deepcopy
 result=copy(session);result.original=bytes(session.original);result.data=bytes(session.data)
 result.content_database=deepcopy(content_database if content_database is not None else getattr(session,'content_database',None))
 result.extra_files={}
 for name,extra in getattr(session,'extra_files',{}).items():
  frozen=copy(extra);frozen.original=bytes(extra.original);frozen.data=bytes(extra.data)
  result.extra_files[name]=frozen
 return result

def save_mod(session,path,name,map_id,overwrite=False):
 if getattr(session,'compiled_project',False):
  from compiled_mod import project_document
  document=project_document(session,name,map_id)
  if getattr(session,'content_database',None) is not None:document['content_database']=session.content_database
  _write_json_project(Path(path),document,overwrite)
  return
 document=dict(format="alundra-mod-v1",name=name,map_id=map_id,patch=session.patch())
 extras=getattr(session,"extra_files",{})
 if extras:
  document["format"]="alundra-mod-v2";document["extra_files"]={name:extra.patch() for name,extra in extras.items()}
 if getattr(session,'content_database',None) is not None:document["content_database"]=session.content_database
 path=Path(path)
 _write_json_project(path,document,overwrite,indent=2)

def _write_json_project(path,document,overwrite,indent=None):
 path=Path(path)
 if not overwrite:
  with path.open('x',encoding='utf-8') as stream:json.dump(document,stream,indent=indent)
  return
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,temp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as stream:
   json.dump(document,stream,indent=indent);stream.flush();os.fsync(stream.fileno())
  os.replace(temp,path)
 except Exception:
  try:os.unlink(temp)
  except OSError:pass
  raise

def load_mod(original,path,base_extra_files=None,progress=None):
 """progress(done,total,text), optional: the editor's loading bar (called from
 the thread that loads; it never touches Tk itself)."""
 step=(lambda done,text:progress(done,4,text)) if progress else (lambda done,text:None)
 base_extra_files=base_extra_files or {}
 step(0,'Reading the mod file…')
 document=json.loads(Path(path).read_text(encoding="utf-8"))
 step(1,'Putting the mod\'s edits on the game…')
 if document.get("format") not in ("alundra-mod-v1","alundra-mod-v2","alundra-mod-v3"):raise ValueError("Not an Alundra mod project")
 m=document.get("map_id",244)
 if not isinstance(m,int) or not 0<=m<2547:raise ValueError("Invalid project map")
 if document['format']=='alundra-mod-v3':
  from compiled_mod import restore_project
  session=restore_project(original,document,path)
  session.content_database=document.get('content_database',{"format":"alundra-content-database-v1","definitions":[]})
  return session,m
 try:session=EditSession(original)
 except ValueError:session=EditSession(original,allow_compatible=True)
 session.apply_patch(document["patch"])
 # Loading is not an edit: Undo must never take the project's own changes back
 # (undoing "Imported new maps" cut the added map blocks off while the map
 # table still pointed at them, so the next map load read past the data end).
 # The imported bytes stay in the saved patch through _extra_spans (patch() reads them).
 limit=len(session.original);spans=session.__dict__.setdefault('_extra_spans',[])
 for change in session.undo_stack:
  rows=change.byte_changes if hasattr(change,'byte_changes') else [change[:3]]
  spans.extend((o,min(o+len(a),limit)) for o,b,a in rows if o<limit)
 session.undo_stack.clear();session.redo_stack.clear();session.__dict__.pop('_parts',None)
 step(3,'Loading the Database…')
 session.content_database=document.get('content_database',{"format":"alundra-content-database-v1","definitions":[]})
 session.extra_files={}
 for name,patch in document.get("extra_files",{}).items():
  if name!="DATA/BALANCE.BIN":raise ValueError("Unsupported mod file")
  from enemy_definition import BalanceSession
  stock=(ROOT/"private-inputs/disc"/name).read_bytes()
  source=bytes(base_extra_files.get(name,stock))
  from jp_balance import balance_mode,balance_bytes,make_session
  mode=balance_mode((document.get('content_database') or {}).get('mod_options'))
  if mode is not None and balance_bytes(mode,source)!=source:
   extra=make_session(balance_bytes(mode,source),source)
  else:extra=BalanceSession(source,verify=(source==stock))
  extra.apply_patch(patch);session.extra_files[name]=extra
 return session,m

def read_datas(path,name="DATA/DATAS.BIN"):
 disc=Disc(path)
 try:
  _,rows=disc.inventory();entry=next(r for r in rows if r["path"].upper()==name)
  return disc.read(entry["lba"],entry["size"])
 finally:disc.handle.close()

def _player_swap_pictures(session):
 """(game data, game data with the Meia costume) for Change Player Character (native_player_swap)."""
 document=getattr(session,'content_database',None) or {}
 if (document.get('mod_options') or {}).get('start_as_meia'):
  raise ValueError('Change Player Character cannot be combined with Start as Meia (the game already starts as Meia)')
 def rows(value):
  if isinstance(value,dict):
   if value.get('type')=='change_player_character' and value.get('character')=='Meia':yield value
   for v in value.values():yield from rows(v)
  elif isinstance(value,list):
   for v in value:yield from rows(v)
 # Each command carries Start as Meia's two options; one swap picture per game, so they must agree.
 flags={(bool(r.get('meia_basic_attack')),bool(r.get('meia_alundra_fallback'))) for r in rows(document.get('event_graphs',[]))} or {(False,False)}
 if len(flags)>1:raise ValueError('Every Change Player Character to Meia needs the same Meia basic attack / Alundra for other actions settings')
 basic,fallback=flags.pop();fallback=fallback and basic   # (as the mod: the fallback needs basic attack)
 from copy import copy
 from player_costume import apply_costume
 meia=copy(session);meia.data=bytearray(session.data)
 apply_costume(meia,basic_attack=basic,alundra_fallback=fallback)
 return bytes(session.data),bytes(meia.data),not fallback


def prepare_project_state_executable(session, source_exe, opcodes):
 """Attach a fresh generated private-state EXE to the isolated export session."""
 from project_state_runtime import OPCODES,inject_private_state
 from types import SimpleNamespace
 melzas=getattr(session,'melzas_places',None) or None
 bosses=getattr(session,'boss_places',None) or None
 if not melzas and not bosses and not any(op in OPCODES or op in (0xE5,0xE6,0xE7,0xE8,0xE9,0xEC,0xED,0xEE,0xEA,0xEB,0xEF,0xF0,0xF1,0xF2) for op in opcodes):return None
 extras=dict(getattr(session,'extra_files',{}))
 candidate=extras.get('ALUN_CD.EXE')
 if candidate is not None and bytes(candidate.original)!=bytes(source_exe):raise ValueError('Source executable does not match the mod project')
 candidate=bytes(candidate.data) if candidate is not None else bytes(source_exe)
 features=['enemy_hp_zero'] if 0xE5 in opcodes else []
 if 0xE8 in opcodes:features.append('carryable_e2')
 if 0xE9 in opcodes or 0xEC in opcodes or 0xEE in opcodes:features.append('custom_ai')
 if 0xEF in opcodes:features.append('hit_follow')   # hit spots that follow their object (native_hit_follow)
 if 0xE6 in opcodes or 0xE7 in opcodes:
  if not (0xE6 in opcodes and 0xE7 in opcodes):raise ValueError('Route snapshot and restore must be exported together')
  features.append('actor_route_resume')
 patched,manifest=inject_private_state(candidate,getattr(session,'content_database',None) or {},
    optional_features=tuple(features),route_resume_slots=getattr(session,'actor_route_resume_slots',0),melzas_places=melzas,boss_places=bosses,
    player_swap=_player_swap_pictures(session) if 0xEB in opcodes else None)
 swap=manifest.get('player_swap')
 if swap:
  # Change Player Character: its XOR data goes at the end of DATAS.BIN, where the handler reads it
  blob=swap.pop('file');data=bytearray(session.data)
  if len(data)>swap['file_offset']:raise ValueError('Player swap file offset moved')
  data+=bytes(swap['file_offset']-len(data))+blob;session.data=data
 extras['ALUN_CD.EXE']=SimpleNamespace(original=bytes(source_exe),data=bytearray(patched))
 session.extra_files=extras;session.private_state_manifest=manifest
 return manifest


def prepare_item_metadata_executable(session,source_exe):
 """Compose verified item metadata with an already-generated/QoL executable."""
 from item_categories import patch_native_properties
 from types import SimpleNamespace
 extras=dict(getattr(session,'extra_files',{}));candidate=extras.get('ALUN_CD.EXE')
 if candidate is not None and bytes(candidate.original)!=bytes(source_exe):
  raise ValueError('Source executable does not match item metadata mod')
 current=bytes(candidate.data) if candidate is not None else bytes(source_exe)
 definitions=(getattr(session,'content_database',None) or {}).get('definitions',[])
 patched,report=patch_native_properties(current,definitions)
 if patched!=current:
  extras['ALUN_CD.EXE']=SimpleNamespace(original=bytes(source_exe),data=patched)
  session.extra_files=extras
 session.item_metadata_report=report
 return report

_SOURCE_OK={}

def _source_matches(source,original):
 """The source disc's DATAS.BIN is the mod's original data (checked once per
 disc file and editor session: the same unchanged file is not read again)."""
 import hashlib
 try:
  st=Path(source).stat();key=(str(Path(source).resolve()),st.st_size,st.st_mtime_ns,len(original),hashlib.sha1(original).hexdigest())
 except OSError:
  return read_datas(source)==original
 if _SOURCE_OK.get(key):return True
 ok=read_datas(source)==original
 if ok:_SOURCE_OK[key]=True
 return ok

def _slus_options(options):
 """Boot program (SLUS_005.53) changes: no opening movies (Instant boot and
 Instant boot +), shorter title exit fades (Fast loading)."""
 wanted=[]
 if options.get('instant_boot') or options.get('instant_boot_plus'):wanted.append('movies')
 if options.get('fast_loading') or options.get('fast_loads'):wanted.append('fast')
 if options.get('confirm_square') is True:wanted.append('confirm')
 return wanted

def _patch_slus(slus,which):
 if 'movies' in which:
  from instant_boot import patch_slus_movies
  slus=patch_slus_movies(slus)
 if 'fast' in which:
  from fast_loads import patch_slus
  slus=patch_slus(slus)
 if 'confirm' in which:
  from confirm_button_swap import patch_slus as confirm_slus
  slus=confirm_slus(slus)
 return slus

def build_game(session,source,destination,progress=lambda text:None,overwrite=False):
 from disc_build_queue import build_slot
 with build_slot(ROOT/'private-inputs/disc-build.lock',progress):
  return _build_game(session,source,destination,progress,overwrite)

def check_build_space(source,destination,temp_root,session):
 """Budget extraction, rebuilt image and exclusive output copy per volume."""
 source=Path(source);destination=Path(destination);temp_root=Path(temp_root)
 growth=max(0,len(session.data)-len(getattr(session,'export_original',session.original)))
 for extra in getattr(session,'extra_files',{}).values():
  growth+=max(0,len(extra.data)-len(extra.original))
 image=source.stat().st_size+growth
 reserve=128*1024*1024
 budgets={}
 for path,needed in ((temp_root,2*image+reserve),(destination.parent,image+reserve)):
  ancestor=path
  while not ancestor.exists():ancestor=ancestor.parent
  volume=ancestor.stat().st_dev
  if volume not in budgets:budgets[volume]=[ancestor,0]
  budgets[volume][1]+=needed
 for path,needed in budgets.values():
  free=shutil.disk_usage(path).free
  if free<needed:
   raise ValueError('Not enough free space to build this game. The drive containing '+
    str(path)+' needs about '+f'{needed/1024**3:.1f} GB free ('+f'{free/1024**3:.1f} GB available). '+
    'Free space before building; no output game has been created.')
 return [{'path':str(path),'required_bytes':needed} for path,needed in budgets.values()]

PAD_DIR=(0x4000,0x1000,0x8000,0x2000)   # ALUN_CD.EXE 0x80022778: pad bit per door side (Down, Up, Left, Right)

def _custom_warps(session,m):
 """[(index, record)] of map m's warps that the project changed or added."""
 from warp_editor import warps
 from portal_records import Portal
 stock={}
 try:
  base,h=EditSession.layout(_View(bytes(session.original),session),m);start=base+h[0]+0x42c
  stock={i:Portal.read(session.original,start+i*12) for i in range(64)}
 except Exception:pass
 return [(i,p) for i,_,p in warps(session,m) if stock.get(i)!=p]

def partner_size(session,src_map,p):
 """(width, height) of the warp on the destination map that leads back to src_map, nearest
 to where p lands; None when there is none."""
 from warp_editor import warps
 try:rows=warps(session,p.destination_map)
 except Exception:return None
 back=[q for _,_,q in rows if q.destination_map==src_map]
 if not back:return None
 def dist(q):
  cx=min(max(p.destination_x,q.x1),q.x2);cy=min(max(p.destination_y,q.y1),q.y2)
  return abs(cx-p.destination_x)+abs(cy-p.destination_y)
 q=min(back,key=dist);return (q.x2-q.x1+1,q.y2-q.y1+1)

def build_clamp_warps(session):
 """Custom warps whose way back has fewer tiles or another shape: each tile gets a one-tile record;
 tile n (reading order) lands on the way back's tile n, or its last tile when it has fewer
 (1 to 2: both go to the one; 4 to 6: 5 and 6 go to the 4th). Returns [(map, warp, tiles)]."""
 from dataclasses import replace
 from portal_records import Portal
 from height_view_blocking import project_maps
 done=[];maps=list(project_maps(session));plan={}
 for m in maps:   # every way back is measured before any warp is split
  try:plan[m]={i:partner_size(session,m,p) for i,p in _custom_warps(session,m)}
  except Exception:plan[m]={}
 for m in maps:
  custom=plan.get(m) or {}
  if not custom:continue
  base,h=session.layout(m);start=base+h[0]+0x42c
  table=[Portal.read(session.data,start+i*12) for i in range(64)]
  used=[i for i,p in enumerate(table) if (p.x1,p.y1,p.x2,p.y2)!=(0,0,255,255)]
  end=next((i for i in range(64) if (table[i].x1,table[i].y1,table[i].x2,table[i].y2)==(0,0,255,255)),64)
  rows=table[:end];spare=table[end:];out=[];changed=False
  for i,p in enumerate(rows):
   size=custom.get(i)
   W,H=p.x2-p.x1+1,p.y2-p.y1+1
   if size is None:out.append(p);continue
   pw,ph=size;tiles=[(ox,oy) for oy in range(H) for ox in range(W)]
   # tile n (in reading order) lands on the way back's tile n, the last one when it has fewer
   land=[((k:=min(n,pw*ph-1))%pw,k//pw) for n in range(len(tiles))]
   if all(t==l for t,l in zip(tiles,land)):out.append(p);continue
   for (ox,oy),(kx,ky) in zip(tiles,land):
    tx,ty=p.x1+ox,p.y1+oy
    out.append(replace(p,x1=tx,y1=ty,x2=tx,y2=ty,destination_x=p.destination_x+kx,destination_y=p.destination_y+ky))
   done.append((m,i,len(tiles)));changed=True
  if not changed:continue
  if len(out)>64:raise ValueError(f'map {m}: too many warps after clamping')
  empty=spare[0] if spare else Portal(0,0,255,255,0,0,0,0,0)
  raw=b''.join(q.encode() for q in out)+b''.join(empty.encode() for _ in range(64-len(out)))
  session.replace(start,raw,f'Warp clamp map {m}')
 return done

def slope_warp_program(p,dest_map):
 """B program (whole map) for warp record p: Alundra on its tiles (3B) pushing toward the
 door's side (2F, held) is sent to the destination plus his place inside the warp (as the
 game's doors, use_portal 0x80031898). Works on slopes: the game's own door test needs all
 four of his support tiles at his exact height, which a slope never gives. Arriving on it
 he has to step off or let go first."""
 import struct
 box=bytes((0x3B,p.x1,p.x2,p.y1,p.y2,0,127));pad=struct.pack('<BHB',0x2F,PAD_DIR[(p.flags>>14)&3],0)
 arm=bytearray()
 arm+=b'\x00'+box+struct.pack('<Bh',0x04,3+len(pad)+3+3)+pad+struct.pack('<Bh',0x04,3+3)+struct.pack('<Bh',0x02,-(1+len(box)+3+len(pad)+3))
 poll=bytearray()
 poll+=b'\x00'+box+struct.pack('<Bh',0x04,-(1+len(box)))
 at=len(poll);poll+=pad;poll+=struct.pack('<Bh',0x04,-(at+len(pad)))
 tiles=[(p.x1+ox,p.y1+oy) for oy in range(p.y2-p.y1+1) for ox in range(p.x2-p.x1+1)]
 face=bytes((0x5A,0x81,(0,16,8,24)[(p.flags>>12)&3]))   # Arrive facing: a script warp keeps his facing, so turn him first
 size=7+3+3+8+3;plain=face+struct.pack('<BH5B',0x53,dest_map,p.destination_x,p.destination_y,p.z,0,0)
 for n,(tx,ty) in enumerate(tiles):
  dx=p.destination_x+tx-p.x1;dy=p.destination_y+ty-p.y1
  if not(0<=dx<=255 and 0<=dy<=255):dx,dy=p.destination_x,p.destination_y
  poll+=bytes((0x3B,tx,tx,ty,ty,0,127))+struct.pack('<Bh',0x04,3+3+8+3)
  poll+=face+struct.pack('<BH5B',0x53,dest_map,dx,dy,p.z,0,0)
  poll+=struct.pack('<Bh',0x02,3+(len(tiles)-n-1)*size+len(plain))
 return bytes(arm+poll+plain)+b'\xff'

def build_slope_warps(session):
 """Custom warps (changed or added in the project) whose tiles, or a tile next to them, are a
 slope get a tile-tested script too (slope_warp_program). Returns (session, [(map, warp)])."""
 from copy import copy
 from warp_editor import warps
 from area_map import grid
 from height_view_blocking import project_maps
 from native_script_allocation import append_native_process
 from native_class_placement import record_cluster,append_record_cluster
 from portal_records import Portal
 done=[];data=None
 for m in list(project_maps(session)):
  try:rows=warps(session if data is None else _View(data,session),m)
  except Exception:continue
  view=session if data is None else _View(data,session)
  w,hh,cells=grid(view,m)
  stock={}
  try:
   base,h=EditSession.layout(_View(bytes(session.original),session),m);start=base+h[0]+0x42c
   stock={i:Portal.read(session.original,start+i*12) for i in range(64)}
  except Exception:pass
  events=[]
  for i,o,p in rows:
   if stock.get(i)==p:continue   # the game's own warp: left alone
   near=[(x,y) for y in range(p.y1-1,p.y2+2) for x in range(p.x1-1,p.x2+2) if 0<=x<w and 0<=y<hh]
   if not any(cells[y*w+x]['values'][2]&3 for x,y in near):continue
   cur=bytes(view.data);dm=p.destination_map
   cur,alloc=append_native_process(cur,m,'B',slope_warp_program(p,dm))
   data=bytearray(cur);events.append(bytes((0,0,w-1,hh-1,alloc['hook_value'],0,0,0)));done.append((m,i))
  if events:
   cluster=record_cluster(bytes(data),m)
   data,_=append_record_cluster(bytes(data),m,map_events=cluster['events']+events);data=bytearray(data)
 if data is None:return session,done
 result=copy(session);result.data=bytearray(data)
 result.undo_stack=list(getattr(session,'undo_stack',[]));result.redo_stack=[]
 for k in ('_texture_cache','_parts'):result.__dict__.pop(k,None)
 return result,done

class _View:
 """Session-like view of rebuilt data (layout / texture readers of EditSession)."""
 def __init__(self,data,session):self.data=data;self.original=session.original
 layout=EditSession.layout

def build_draw_behind(session,m):
 """The Draw all behind Alundra button run without the editor window on map m."""
 from area_map import MapRenderer
 from map_area_copy import cells_of,rebuild_grid
 from no_mask import draw_all_behind,blank_code,masked_tiles
 w,hh,cells=cells_of(session,m);r=MapRenderer(session,m)
 margin=max((c['values'][3] for c in cells),default=0)*16
 n=draw_all_behind(r,cells,w,hh,margin,blank_code(r,cells),masked=masked_tiles(getattr(session,'content_database',None),m))
 if n:rebuild_grid(session,m,cells,f'Draw all behind Alundra ({n})')
 return n

def build_fix_masks(session,m):
 """The Fix Masks button (area_ui.AreaPanel.fix_masks) run without the editor window on map m of
 session; the result is written into the session. Returns the number of pieces fixed."""
 from types import SimpleNamespace,MethodType
 from area_ui import AreaPanel
 from area_map import grid,MapRenderer
 from map_area_copy import rebuild_grid
 w,hh,cells=grid(session,m)
 doc=getattr(session,'content_database',None) or {}
 v=SimpleNamespace(grid_cells=cells,grid_width=w,grid_height=hh,margin=max((c['values'][3] for c in cells),default=0)*16+16,
  pending_heights={},pending_stack_grid=None,pending_stack_tiles=set(),renderer=MapRenderer(session,m),
  editor=SimpleNamespace(session=session,current_map=m,dirty=False,database=SimpleNamespace(document=doc)))
 v.elevation_enabled=lambda:True
 for name in ('original_pieces','record_pieces','column_picture','rebased_walls','tile_rows','set_cell_walls','stack_grid'):
  setattr(v,name,MethodType(getattr(AreaPanel,name),v))
 n=AreaPanel.fix_masks(v,redraw=False)
 if n:rebuild_grid(session,m,v.stack_grid()[2],f'Fix Masks ({n} pieces)')
 return n

def _build_game(session,source,destination,progress=lambda text:None,overwrite=False):
 from event_export import prepare_native_event_export,generated_event_opcodes,generated_sprite_callbacks
 progress("Compiling map events…")
 import native_custom_ai;native_custom_ai.BUILD_WARNINGS.clear()
 authored_session=session;session=prepare_native_event_export(session,best_effort=True)
 for w in native_custom_ai.BUILD_WARNINGS:progress('Warning: '+w)
 from height_view_blocking import apply_height_view_blocking
 session,_=apply_height_view_blocking(session,progress)   # Edit heights (Lowest tiles) is how the map plays (user 2026-10-25)
 try:   # a bigger warp leading to a smaller one: its extra tiles land on the nearest tile (user 2026-10-26)
  _c=build_clamp_warps(session)
  for _m,_i,_n in _c:progress(f'Warp clamp: map {_m}, warp {_i} ({_n} extra tile(s))')
 except Exception as exc:
  progress(f'Warning: warp clamp skipped ({exc})')
 try:   # custom warps on or next to slopes also work as a tile-tested script (user 2026-10-26)
  session,_sw=build_slope_warps(session)
  for _m,_i in _sw:progress(f'Slope warp: map {_m}, warp {_i}')
 except Exception as exc:
  progress(f'Warning: slope warps skipped ({exc})')
 # Fix Masks (the Edit heights button, AreaPanel.fix_masks) on every project map at build (user 2026-10-25);
 # a map that fails is reported and skipped.
 try:
  from height_view_blocking import project_maps
  _maps=list(project_maps(session))
 except Exception as exc:
  _maps=[]
 if _maps:progress('Compiling map data…')   # masks / drawing over Alundra: one quiet step (user 2026-10-26)
 for _m in _maps:
  try:   # Draw all behind Alundra first (user 2026-10-25), then Fix Masks
   build_draw_behind(session,_m)
  except Exception as exc:
   pass
  try:
   build_fix_masks(session,_m)
  except Exception as exc:
   pass
 source=Path(source).resolve();destination=Path(destination).resolve()
 if destination.suffix.lower()!=".bin":raise ValueError("Choose a .bin output filename")
 if source==destination:raise ValueError("Choose a separate output BIN; the original game image is never overwritten")
 cue=destination.with_suffix(".cue")
 if any(p.exists() for p in (destination,cue)) and not overwrite:raise ValueError("Output BIN or CUE already exists; choose a new name")
 if '"' in destination.name or '\n' in destination.name or '\r' in destination.name:raise ValueError("Invalid output filename")
 progress("Checking original disc…")
 original=getattr(session,'export_original',session.original)
 if not _source_matches(source,original):raise ValueError("This disc does not match the original data used by your mod")
 extras=getattr(session,"extra_files",{})
 if getattr(session,'native_event_export_ids',set()):
  from event_vm_compatibility import verify_event_vm_abi,verify_sprite_callback_abi
  stock_exe=(ROOT/'private-inputs/disc/ALUN_CD.EXE').read_bytes()
  opcodes=generated_event_opcodes(authored_session,session)
  manifest=prepare_project_state_executable(session,read_datas(source,'ALUN_CD.EXE'),opcodes)
  extras=getattr(session,'extra_files',{})
  candidate=extras.get('ALUN_CD.EXE')
  candidate=bytes(candidate.data) if candidate is not None else read_datas(source,'ALUN_CD.EXE')
  verify_event_vm_abi(candidate,stock_exe,opcodes,private_state_manifest=manifest)
  verify_sprite_callback_abi(candidate,stock_exe,generated_sprite_callbacks(authored_session,session),patched=((getattr(session,'private_state_manifest',None) or {}).get('boss_points') or {}).get('sites',()))
 options=(getattr(session,'content_database',None) or {}).get('mod_options',{})
 from map_slots import extra_count
 _doc=getattr(session,'content_database',None) or {}
 _bosses={r.get('id') for r in _doc.get('definitions') or [] if r.get('kind')=='boss'}
 _has_boss=any(p.get('class_id',g.get('class_id')) in _bosses for g in _doc.get('event_graphs') or [] for p in g.get('pages') or [])
 _heal_edits=any(k in (r.get('data') or {}) for r in (getattr(session,'content_database',None) or {}).get('definitions',[]) for k in ('heal_divisor','heal_at_least','heal_amount','magic_spawns'))
 import play_movie as _pm
 _movie=_pm.used(_doc)
 if options or extra_count(session.data) or _has_boss or _heal_edits or _movie:   # (a boss brings its home sound set)
  from editor_qol import apply_qol
  from types import SimpleNamespace
  from copy import copy
  session=copy(session);session.data=bytearray(session.data)
  session.undo_stack=list(getattr(session,'undo_stack',[]));session.redo_stack=[]
  original_exe=read_datas(source,'ALUN_CD.EXE')
  candidate=extras.get('ALUN_CD.EXE')
  if candidate is not None and bytes(candidate.original)!=original_exe:
   raise ValueError('Source executable does not match the mod project')
  candidate=bytes(candidate.data) if candidate is not None else original_exe
  patched,qol_report=apply_qol(session,candidate)
  # healing items' edited heal values (item_heals; patched in place, no new code)
  import item_heals
  patched,heal_report=item_heals.patch(patched,(getattr(session,'content_database',None) or {}).get('definitions',[]))
  if heal_report:qol_report=dict(qol_report,item_heals=heal_report)
  import magic_spawns   # what each magic spawns (patched in place)
  patched,magic_report=magic_spawns.patch(patched,(getattr(session,'content_database',None) or {}).get('definitions',[]),bytes(session.data))
  if magic_report:qol_report=dict(qol_report,magic_spawns=magic_report)
  water_stub=next((x['address'] for x in qol_report.get('patches',[]) if isinstance(x,dict) and x.get('feature')=='water_scroll_stub'),None)
  patched,behaviour_report=magic_spawns.patch_behaviour(patched,(getattr(session,'content_database',None) or {}).get('definitions',[]),water_stub)
  if behaviour_report:qol_report=dict(qol_report,magic_behaviour=behaviour_report)
  if patched!=candidate:
   if getattr(session,'native_event_export_ids',set()):
    if manifest is not None:
     # The original generated module was verified above. A composed patch may
     # relocate its file bytes, but its virtual handlers must remain identical.
     from copy import deepcopy
     import struct
     manifest=deepcopy(manifest)
     manifest['result_sha256']=hashlib.sha256(patched).hexdigest()
     manifest['new_load']=struct.unpack_from('<I',patched,0x18)[0]
     state_offset=manifest['state_address']-manifest['new_load']+0x800
     initial_state=patched[state_offset:state_offset+manifest['state_size']]
     if hashlib.sha256(initial_state).hexdigest()!=manifest['state_initial_sha256']:
      raise ValueError('Game options conflict with project switch/variable initialization')
    verify_event_vm_abi(patched,stock_exe,opcodes,private_state_manifest=manifest)
    verify_sprite_callback_abi(patched,stock_exe,generated_sprite_callbacks(authored_session,session),patched=((getattr(session,'private_state_manifest',None) or {}).get('boss_points') or {}).get('sites',()))
   extras=dict(extras);extras['ALUN_CD.EXE']=SimpleNamespace(original=original_exe,data=patched)
   session.extra_files=extras
  session.qol_report=qol_report
 definitions=(getattr(session,'content_database',None) or {}).get('definitions',[])
 if any(row.get('data',{}).get('item_native_properties') for row in definitions):
  prepare_item_metadata_executable(session,read_datas(source,'ALUN_CD.EXE'))
  extras=getattr(session,'extra_files',{})
  if getattr(session,'native_event_export_ids',set()):
   candidate=bytes(extras['ALUN_CD.EXE'].data)
   if manifest is not None:
    from copy import deepcopy
    manifest=deepcopy(manifest);manifest['result_sha256']=hashlib.sha256(candidate).hexdigest()
   verify_event_vm_abi(candidate,stock_exe,opcodes,private_state_manifest=manifest)
   verify_sprite_callback_abi(candidate,stock_exe,generated_sprite_callbacks(authored_session,session),patched=((getattr(session,'private_state_manifest',None) or {}).get('boss_points') or {}).get('sites',()))
 # New map slots (483+) get their music from the relocated table (editor_qol/extra_maps_runtime).
 selections={k:v for k,v in ((getattr(session,'content_database',None) or {}).get('map_music',{})).items() if int(k)<483}
 if selections:
  from music_database import patch_map_music
  from types import SimpleNamespace
  original_exe=read_datas(source,'ALUN_CD.EXE');candidate=extras.get('ALUN_CD.EXE')
  if candidate is not None and bytes(candidate.original)!=original_exe:raise ValueError('Source executable differs from map music project')
  current=bytes(candidate.data) if candidate is not None else original_exe
  patched,session.map_music_report=patch_map_music(current,selections)
  extras=dict(extras);extras['ALUN_CD.EXE']=SimpleNamespace(original=original_exe,data=patched);session.extra_files=extras
 # Map-only sounds the project plays where the map's sound set lacks them (map_sound_sets);
 # nothing changes unless such a sound is used.
 if getattr(session,'native_event_export_ids',set()):
  import map_sound_sets
  from types import SimpleNamespace
  from editor_session import EditSession
  original_exe=read_datas(source,'ALUN_CD.EXE');candidate=extras.get('ALUN_CD.EXE')
  current=bytes(candidate.data) if candidate is not None else original_exe
  # Melzas's speed setting also shortens his own waits on the maps he is placed on (native_ai_speed)
  _defs={d.get('id'):d for d in (getattr(session,'content_database',None) or {}).get('definitions',[])}
  map_sound_sets.AI_SPEED.clear()
  for _g in (getattr(session,'content_database',None) or {}).get('event_graphs',[]):
   for _p in _g.get('pages') or []:
    _d=_defs.get(_p.get('class_id',_g.get('class_id'))) or {}
    _f=round((_d.get('data',{}).get('speed_percent') or 100)/100)
    if _d.get('source',{}).get('catalogue_index')==418 and _f>1 and type(_g.get('map_id')) is int:map_sound_sets.AI_SPEED[_g['map_id']]=min(_f,16)
  wants=map_sound_sets.project_wants(session,EditSession.readonly(bytes(original)),original_exe)
  own=map_sound_sets.own_wants(session,current)   # project maps: their own sound sets
  all_wants=wants;wants={m:v for m,v in wants.items() if m not in own}
  if map_sound_sets.needed(current,wants) or own:
   original_sound=read_datas(source,'DATA/SOUND.BIN')
   try:
    from game_audio_names import sound_name
    names={n:sound_name(getattr(session,'content_database',None) or {},n) for ids in list(wants.values())+list(own.values()) for n in ids}
   except Exception:names={}
   try:
    patched,sound,session.sound_set_report,warnings=map_sound_sets.apply(current,original_sound,wants,names,extended=bool(options.get('more_sound_room',True)),record_gap=0 if options.get('more_sound_room',True) else 0x800,vh_limit=map_sound_sets.VH_BUFFER if options.get('more_sound_room',True) else None,multi_tone=bool(options.get('more_sound_room',True)),own=own)
   except map_sound_sets.SoundSetError as err:
    if not own:raise
    # no room for every project map's own set: as many maps as fit keep one (those whose
    # placed classes / events play the most sounds first, 2026-10-23); the others keep
    # their template sets plus what fits there, and the warning names them
    order=sorted(own,key=lambda m:(-sum(1 for v in own[m].values() if v[0]<=2),m))
    result=None
    while len(order)>1 and result is None:
     dropped=order.pop()
     part={m:own[m] for m in order};rest={m:v for m,v in all_wants.items() if m not in part}
     try:result=map_sound_sets.apply(current,original_sound,rest,names,extended=bool(options.get('more_sound_room',True)),record_gap=0 if options.get('more_sound_room',True) else 0x800,vh_limit=map_sound_sets.VH_BUFFER if options.get('more_sound_room',True) else None,multi_tone=bool(options.get('more_sound_room',True)),own=part)
     except map_sound_sets.SoundSetError:result=None
    if result is not None:
     patched,sound,session.sound_set_report,warnings=result
     left=sorted(m for m in own if m not in part)
     warnings=[f"Own sound sets not built for map{'s' if len(left)>1 else ''} {', '.join(map(str,left))} ({err}); built for {', '.join(map(str,sorted(part)))}"]+warnings
    else:
     patched,sound,session.sound_set_report,warnings=map_sound_sets.apply(current,original_sound,all_wants,names,extended=bool(options.get('more_sound_room',True)),record_gap=0 if options.get('more_sound_room',True) else 0x800,vh_limit=map_sound_sets.VH_BUFFER if options.get('more_sound_room',True) else None,multi_tone=bool(options.get('more_sound_room',True)))
     warnings=[f"Own sound sets for the project's maps not built: {err}"]+warnings
   if map_sound_sets.MAP_TABLES:   # own-set records go into each map's own data (native_map_sound_table)
    _data,_warn=map_sound_sets.install_map_tables(bytes(session.data));session.data=bytearray(_data);warnings=list(warnings)+_warn
   for line in session.sound_set_report:progress(line)
   for line in warnings:progress("Warning: "+line)
   session.sound_set_warnings=warnings
   if sound!=original_sound:
    extras=dict(extras);extras['ALUN_CD.EXE']=SimpleNamespace(original=original_exe,data=patched)
    extras['DATA/SOUND.BIN']=SimpleNamespace(original=original_sound,data=sound);session.extra_files=extras
 # in-game item / weapon / armor text (item_text): ETC_USA.R rebuilt at the same size
 import item_text
 original_etc=read_datas(source,item_text.NAME)
 etc,text_report=item_text.patch(original_etc,(getattr(session,'content_database',None) or {}).get('definitions',[]))
 if text_report:extras=dict(extras);extras[item_text.NAME]=SimpleNamespace(original=original_etc,data=etc)
 for name,extra in extras.items():
  if name not in ("DATA/BALANCE.BIN","ALUN_CD.EXE","DATA/SOUND.BIN",item_text.NAME):raise ValueError("Unsupported extra mod file")
  if read_datas(source,name)!=getattr(extra,"disc_original",extra.original):raise ValueError("Disc balance data does not match this mod")
 # Fast rebuild: the files this build writes (DATAS.BIN, executable, balance,
 # SYSTEM.CNF). When they keep their sizes, only their changed sectors are
 # rewritten in the previous build (seconds instead of rebuilding the image).
 if _movie:
  # Play Movie event command: END.EXE picks the movie and what follows (play_movie.py); build copy only
  from types import SimpleNamespace
  _end=read_datas(source,'END.EXE');extras=dict(extras)
  extras['END.EXE']=SimpleNamespace(original=_end,data=bytearray(_pm.patch_end(_end)))
 wanted={"DATA/DATAS.BIN":bytes(session.data)}
 # global-bank class colours (global_sprite_recolor): applied to the built copy only, every map
 shifts={}
 for row in (getattr(session,'content_database',None) or {}).get('definitions',[]):
  g=(row.get('data') or {}).get('global_palette_shift');n=(row.get('source') or {}).get('catalogue_index')
  if g and type(n) is int and 0<=n<256 and not row.get('clone_of'):shifts[n]=(g.get('hue_degrees',0),g.get('saturation_percent',100))
 if shifts:
  import global_sprite_recolor
  wanted["DATA/DATAS.BIN"],colour_report=global_sprite_recolor.recolor(wanted["DATA/DATAS.BIN"],shifts)
  for line in colour_report:progress(f"Global class {line['sprite']}: palette {line['palette']} recoloured")
 for name,extra in extras.items():wanted[name]=bytes(extra.data)
 # custom accessories (custom_accessory): item type 3 in the executable, defence / recovery in its
 # own BALANCE.BIN record; applied to the built copies only
 import custom_accessory
 accessories=custom_accessory.settings((getattr(session,'content_database',None) or {}).get('definitions',[]))
 if accessories:
  if 'ALUN_CD.EXE' not in wanted:wanted['ALUN_CD.EXE']=read_datas(source,'ALUN_CD.EXE')
  wanted['ALUN_CD.EXE']=custom_accessory.patch_exe(wanted['ALUN_CD.EXE'],accessories)
  if 'DATA/BALANCE.BIN' not in wanted:wanted['DATA/BALANCE.BIN']=read_datas(source,'DATA/BALANCE.BIN')
  wanted['DATA/BALANCE.BIN']=custom_accessory.patch_balance(wanted['DATA/BALANCE.BIN'],accessories)
 if options.get('instant_boot_plus'):
  from instant_boot import patch_system_cnf,CNF_NAME
  wanted[CNF_NAME]=patch_system_cnf(read_datas(source,CNF_NAME))
 slus_options=_slus_options(options)
 if slus_options:
  from instant_boot import SLUS_NAME
  wanted[SLUS_NAME]=_patch_slus(read_datas(source,SLUS_NAME),slus_options)
 fast=_patch_previous_build(source,destination,cue,wanted,progress)
 if fast is not None:return fast
 tools=ROOT/"tools" if (ROOT/"tools/mkpsxiso.exe").is_file() else ROOT/"Randomizer/tools"   # (AlundraMaker keeps them in tools)
 for name in ("dumpsxiso.exe","mkpsxiso.exe"):
  if not (tools/name).is_file():raise ValueError(f"Missing bundled build tool: {name}")
 private=ROOT/"private-inputs";private.mkdir(exist_ok=True)
 check_build_space(source,destination,private,session)
 with tempfile.TemporaryDirectory(prefix="editor-build-",dir=private) as folder:
  work=Path(folder);dump=work/"dump";dump.mkdir();xml=work/"build.xml"
  def run(args):
   result=subprocess.run([str(x) for x in args],cwd=work,capture_output=True,text=True,errors="replace",creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
   if result.returncode:raise ValueError("Disc tool failed: "+(result.stderr+result.stdout)[-2000:])
  progress("Extracting a temporary disc copy…")
  run([tools/"dumpsxiso.exe",source,"-x",dump,"-s",xml])
  target=next((p for p in dump.rglob("*") if p.is_file() and p.relative_to(dump).as_posix().upper()=="DATA/DATAS.BIN"),None)
  if target is None or target.read_bytes()!=original:raise ValueError("Extracted game data differs from source")
  target.write_bytes(_reserved(session.data))
  for name,extra in extras.items():
   target=next((p for p in dump.rglob("*") if p.is_file() and p.relative_to(dump).as_posix().upper()==name),None)
   if target is None or target.read_bytes()!=getattr(extra,"disc_original",extra.original):raise ValueError("Extracted balance differs from source")
   target.write_bytes(extra.data)
  boot_config=None
  if options.get('instant_boot_plus'):
   # Mod option Instant boot +: the BIOS boots ALUN_CD.EXE directly (instant_boot.py).
   from instant_boot import patch_system_cnf,CNF_NAME
   target=next((p for p in dump.rglob("*") if p.is_file() and p.relative_to(dump).as_posix().upper()==CNF_NAME),None)
   if target is None:raise ValueError("Instant boot: the disc has no "+CNF_NAME)
   boot_config=patch_system_cnf(target.read_bytes())
   target.write_bytes(boot_config)
  slus_patch=None
  if slus_options:
   from instant_boot import SLUS_NAME
   target=next((p for p in dump.rglob("*") if p.is_file() and p.relative_to(dump).as_posix().upper()==SLUS_NAME),None)
   if target is None:raise ValueError("The disc has no "+SLUS_NAME)
   slus_patch=_patch_slus(target.read_bytes(),slus_options)
   target.write_bytes(slus_patch)
  progress("Building the edited game…")
  built=work/"result.bin";builtcue=work/"result.cue"
  run([tools/"mkpsxiso.exe",xml,"-o",built,"-c",builtcue])
  progress("Verifying exported edits…")
  got=read_datas(built)
  if got[:len(session.data)]!=bytes(session.data) or any(got[len(session.data):]):raise ValueError("Rebuilt game does not contain the requested edits")
  for name,extra in extras.items():
   if read_datas(built,name)!=extra.data:raise ValueError("Rebuilt balance data mismatch")
  if boot_config is not None and read_datas(built,'SYSTEM.CNF')!=boot_config:raise ValueError("Rebuilt SYSTEM.CNF mismatch")
  if slus_patch is not None and read_datas(built,'SLUS_005.53')!=slus_patch:raise ValueError("Rebuilt SLUS_005.53 mismatch")
  text=builtcue.read_text();lines=text.splitlines();file_lines=[i for i,line in enumerate(lines) if line.strip().upper().startswith("FILE ")]
  if len(file_lines)!=1:raise ValueError("Only single-file CUE output is supported")
  lines[file_lines[0]]=f'FILE "{destination.name}" BINARY'
  _commit_build_pair(built,"\n".join(lines)+"\n",destination,cue,overwrite)
 wanted['DATA/DATAS.BIN']=_reserved(session.data)
 _write_build_manifest(source,destination,wanted)
 return destination,cue

# -- fast rebuild: patch the changed sectors of the previous build ------------
RESERVE = 8 * 1024 * 1024   # spare room after DATAS.BIN in a full build

def _reserved(data):
 """DATAS.BIN as written to a fully rebuilt disc: the game data plus zero
 padding (the game only reads it through its map table), so later builds
 that grow the data still fit and patch the disc in place - no temporary
 disc copy and rebuild."""
 size=len(data)+RESERVE;size+=(-size)%(1024*1024)
 return bytes(data)+bytes(size-len(data))

def _manifest_path(destination):
 return Path(destination).with_suffix('.build.json')

def _stat(path):
 st=Path(path).stat();return {'path':str(Path(path).resolve()),'size':st.st_size,'mtime_ns':st.st_mtime_ns}

def _write_build_manifest(source,destination,files):
 """What the build at `destination` was made from, so the next build can
 patch it: the source disc, the output's size/time, and the files it wrote."""
 try:
  _manifest_path(destination).write_text(json.dumps({'version':1,'source':_stat(source),'destination':_stat(destination),
   'files':sorted(files)},indent=1),encoding='utf-8')
 except OSError:pass

def _patch_previous_build(source,destination,cue,files,progress=lambda text:None):
 """Rewrite only the sectors that differ in the previous build of the same
 source; None when that is not possible (no or changed previous build, a file
 changed size) and the image must be rebuilt."""
 from cd_sector import mode2_form1_many
 manifest_path=_manifest_path(destination)
 try:manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
 except (OSError,ValueError):return None
 try:
  if manifest.get('version')!=1 or not Path(cue).is_file():return None
  if manifest['source']!=_stat(source) or manifest['destination']!=_stat(destination):return None
 except (OSError,KeyError,TypeError):return None
 files=dict(files)
 for name in manifest.get('files',[]):
  if name not in files:files[name]=read_datas(source,name)   # an edit was removed: back to the original
 disc=Disc(destination)
 try:
  _,rows=disc.inventory();where={row['path'].upper():row for row in rows}
  plan=[]
  for name,content in files.items():
   row=where.get(name.upper())
   if row is not None and name.upper()=='DATA/DATAS.BIN' and len(content)<=row['size']:
    content=bytes(content)+bytes(row['size']-len(content));files[name]=content   # fits the reserved room
   if row is None or row['size']!=len(content):return None   # size changed: the image must be rebuilt
   old=disc.read(row['lba'],row['size'])
   for i in range(0,len(content),2048):
    if content[i:i+2048]!=old[i:i+2048]:plan.append((row['lba']+i//2048,content[i:i+2048]))
 finally:disc.handle.close()
 progress(f"Updating {len(plan)} changed sector(s) of the last build…")
 manifest_path.unlink()   # until the patch is complete, the next build rebuilds
 with open(destination,'r+b') as stream:
  # error codes of many sectors at once (numpy; ~20x faster than one by one)
  for first in range(0,len(plan),4096):
   batch=plan[first:first+4096];sectors=[]
   for lba,chunk in batch:
    stream.seek(lba*2352);sector=bytearray(stream.read(2352))
    sector[24:24+len(chunk)]=chunk;sectors.append(sector)
   mode2_form1_many(sectors)
   for (lba,_),sector in zip(batch,sectors):
    stream.seek(lba*2352);stream.write(sector)
   progress(f"Writing changed sectors {min(first+4096,len(plan))}/{len(plan)}…")
 progress("Verifying exported edits…")
 for name,content in files.items():
  if read_datas(destination,name)!=content:raise ValueError(f"Patched game does not contain the requested edits ({name})")
 _write_build_manifest(source,destination,files)
 return destination,cue

def _commit_build_pair(built,cue_text,destination,cue,overwrite):
 """Stage a verified BIN/CUE pair, then replace existing outputs with rollback."""
 destination=Path(destination);cue=Path(cue)
 destination.parent.mkdir(parents=True,exist_ok=True)
 stages=[];backups=[];installed=[]
 try:
  fd,bin_stage=tempfile.mkstemp(prefix=destination.name+'.',suffix='.tmp',dir=destination.parent);os.close(fd)
  stages.append(Path(bin_stage));shutil.copyfile(built,bin_stage)
  fd,cue_stage=tempfile.mkstemp(prefix=cue.name+'.',suffix='.tmp',dir=cue.parent);os.close(fd)
  stages.append(Path(cue_stage));Path(cue_stage).write_text(cue_text,encoding='utf-8')
  for target in (destination,cue):
   if target.exists():
    if not overwrite:raise ValueError('Output BIN or CUE already exists; choose a new name')
    fd,name=tempfile.mkstemp(prefix=target.name+'.backup.',suffix='.tmp',dir=target.parent);os.close(fd);Path(name).unlink()
    backup=Path(name);os.replace(target,backup);backups.append((target,backup))
  for stage,target in zip(stages,(destination,cue)):
   os.replace(stage,target);installed.append(target)
 except Exception:
  for target in installed:
   try:target.unlink()
   except OSError:pass
  for target,backup in reversed(backups):
   try:os.replace(backup,target)
   except OSError:pass
  raise
 finally:
  for stage in stages:
   try:stage.unlink()
   except OSError:pass
 for _,backup in backups:
  try:backup.unlink()
  except OSError:pass
