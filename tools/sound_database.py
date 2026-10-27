"""Local PS1 sound-effect browser. No third-party implementation is copied.
Pinned source structure leads are recorded in the dated project report.
Preview is dry PCM (no SPU envelope/reverb), not an emulator playback claim.
"""
import io,math,struct,wave
from pathlib import Path

SIGNATURE=struct.pack('<11h',-1,0,0,0,0,-1,0,-1,0,0,0)+struct.pack('<11h',-1,0,0,60,0,-1,0,-1,2,0,1)
FILTERS=((0,0),(60,0),(115,-52),(98,-55),(122,-60))

def encode_sound(sound_id):
 # Play Sound: BD lo hi -> handler 0x8004278C -> PlaySound 0x8004A128 (US ALUN_CD.EXE, 2026-10-23).
 if type(sound_id) is not int or not 0<=sound_id<=255:raise ValueError('Sound effect ID must be0..255')
 return bytes((0xBD,sound_id,0))

def encode_stop_sound(sound_id):
 # Stop Sound: 75 nn -> handler 0x80040578 -> StopSound 0x8004A7B4 (US ALUN_CD.EXE, 2026-10-23).
 if type(sound_id) is not int or not 0<=sound_id<=255:raise ValueError('Sound effect ID must be0..255')
 return bytes((0x75,sound_id))

def decode_adpcm(data):
 if len(data)%16:raise ValueError('Truncated16-byte ADPCM block')
 result=[];last=previous=0
 for offset in range(0,len(data),16):
  control,flags=data[offset:offset+2];filter_id=control>>4;shift=control&15
  if filter_id>=len(FILTERS) or shift>12:raise ValueError('Invalid PS1 ADPCM filter/shift')
  a,b=FILTERS[filter_id]
  for packed in data[offset+2:offset+16]:
   for nibble in (packed&15,packed>>4):
    signed=nibble if nibble<8 else nibble-16
    value=((signed<<12)>>shift)+((last*a+previous*b+32)>>6)
    value=max(-32768,min(32767,value));previous,last=last,value;result.append(value)
  if flags&1:break
 return result

class SoundLibrary:
 def __init__(self,sound,exe):
  self.sound=bytes(sound);self.exe=bytes(exe);self.cache={}
  if self.exe[:8]!=b'PS-X EXE':raise ValueError('Sound browser requires the selected game EXE')
  offset=self.exe.find(SIGNATURE)
  if offset<0 or self.exe.find(SIGNATURE,offset+1)>=0 or offset+256*22>len(self.exe):raise ValueError('Sound-effect table signature is not uniquely recognized')
  self.table_offset=offset;self.records=[struct.unpack_from('<11h',self.exe,offset+i*22) for i in range(256)]
  if self.sound[0x800:0x804]!=b'pBAV':raise ValueError('Global VAB bank header not recognized')
  self.program_count=struct.unpack_from('<H',self.sound,0x812)[0]
  self.sample_count=struct.unpack_from('<H',self.sound,0x816)[0]
  if not 1<=self.program_count<=128 or not 1<=self.sample_count<=255:raise ValueError('Invalid VAB counts')
  table=0x800+32+128*16+self.program_count*16*32
  if table+512>0x3000:raise ValueError('VAB header exceeds validated global bank space')
  self.lengths=struct.unpack_from('<256H',self.sound,table)
 def rows(self):
  return [dict(id=i,bank=r[0],program=r[1],tone=r[2],note=r[3],tones=r[10],preview=r[0]==-1 and r[5]==-1 and r[10]>0) for i,r in enumerate(self.records)]
 def pcm(self,sound_id):
  encode_sound(sound_id)
  if sound_id in self.cache:return self.cache[sound_id]
  bank,program,tone,note,flags,sequence,reference,_,voices,_,count=self.records[sound_id]
  if bank!=-1 or sequence!=-1:raise ValueError('This sound needs a map-specific bank or sequence; a global preview is unavailable')
  if not 0<=program<self.program_count or not 0<=tone<16 or not 1<=count<=16-tone:raise ValueError('This sound has no playable global tones')
  layers=[]
  for index in range(tone,tone+count):
   attr=0x800+32+128*16+(program*16+index)*32
   center=self.sound[attr+4];fine=self.sound[attr+5];sample=struct.unpack_from('<h',self.sound,attr+22)[0]
   sample=max(0,sample-1)
   if sample>=self.sample_count:raise ValueError('Tone sample outside bank')
   start=0x3000+sum(self.lengths[:sample+1])*8;length=self.lengths[sample+1]*8
   if start+length>len(self.sound) or length==0:raise ValueError('Invalid sample extent')
   pcm=decode_adpcm(self.sound[start:start+length]);ratio=2**((note-center+fine/128)/12)
   volume=self.sound[attr+2]/127*self.sound[0x818]/127*self.sound[0x820+program*16+1]/127
   size=min(44100*5,int(len(pcm)/ratio))
   layers.append([round(pcm[min(len(pcm)-1,int(i*ratio))]*volume) for i in range(size)])
  mixed=[max(-32768,min(32767,sum(layer[i] if i<len(layer) else 0 for layer in layers))) for i in range(max(map(len,layers),default=0))]
  self.cache[sound_id]=mixed;return mixed
 def wav(self,sound_id,gain=.05):
  if not 0<=gain<=1:raise ValueError('Preview volume must be0..1')
  output=io.BytesIO()
  with wave.open(output,'wb') as writer:
   writer.setparams((1,2,44100,0,'NONE','not compressed'))
   writer.writeframes(struct.pack('<'+'h'*len(self.pcm(sound_id)),*(round(value*gain) for value in self.pcm(sound_id))))
  return output.getvalue()

def library_for_editor(editor):
 session=editor.session
 if session is None:return None
 key=(session,getattr(session,'path',None))
 if getattr(editor,'sound_library_key',None)==key:return editor.sound_library
 from mod_export import read_datas
 path=session.path
 if path and path.name.upper()=='DATAS.BIN':
  sound_path=path.parent/'SOUND.BIN';exe_path=path.parent.parent/'ALUN_CD.EXE'
  if not sound_path.is_file() or not exe_path.is_file():raise ValueError('Select the game disc BIN, or keep SOUND.BIN and ALUN_CD.EXE beside its extracted data')
  sound=sound_path.read_bytes();exe=exe_path.read_bytes()
 elif path:sound=read_datas(path,'DATA/SOUND.BIN');exe=read_datas(path,'ALUN_CD.EXE')
 elif session.source_verified:
  root=Path(__file__).resolve().parents[1]/'private-inputs/disc'
  sound=(root/'DATA/SOUND.BIN').read_bytes();exe=(root/'ALUN_CD.EXE').read_bytes()
 else:raise ValueError('Sound previews need the selected game disc or extracted audio files')
 editor.sound_library=SoundLibrary(sound,exe);editor.sound_library_key=key
 return editor.sound_library
