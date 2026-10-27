"""Undoable map sprite palettes; edits deliberately affect shared references."""
import struct
from entity_preview import EntityPreview
from map_inspector import inspect_map

def palettes(session,m):
 preview=EntityPreview(session,m)
 start=preview.start+preview.header[5];end=preview.start+preview.header[6]
 if not preview.start<=start<=end<=preview.end:
  raise ValueError('Unsupported sprite palette bounds')
 return [(i,start+i*32,struct.unpack_from('<16H',session.data,start+i*32)) for i in range((end-start)//32)]

def recolor(words,source,target):
 channels={'Red':0,'Green':5,'Blue':10}
 if source not in channels or target not in channels or source==target:
  raise ValueError('Choose two different colour channels')
 a,b=channels[source],channels[target];out=[]
 for word in words:
  rgb=[word&31,(word>>5)&31,(word>>10)&31];src=rgb[a//5]
  # Strict dominance avoids changing greys, outlines and neutral highlights.
  if src>max(rgb[i] for i in range(3) if i!=a//5):
   rgb[a//5],rgb[b//5]=rgb[b//5],rgb[a//5]
  out.append((word&0x8000)|rgb[0]|rgb[1]<<5|rgb[2]<<10)
 return tuple(out)

def apply_palette(session,m,index,words):
 rows=palettes(session,m)
 if not 0<=index<len(rows):raise ValueError('Palette index outside map')
 if len(words)!=16 or any(not isinstance(w,int) or not 0<=w<=65535 for w in words):
  raise ValueError('Palette must contain 16 native colour words')
 session.replace(rows[index][1],struct.pack('<16H',*words),'Shared sprite palette recolour')

class PalettePreview(EntityPreview):
 def __init__(self,session,m,replacements=None):
  self.replacements=replacements or {};self.used=set();super().__init__(session,m)
 def read(self,fmt,offset):
  result=super().read(fmt,offset)
  if fmt=='16H':
   self.used.add(offset)
   return self.replacements.get(offset,result)
  return result

def affected_sprites(session,m,palette_index):
 rows=palettes(session,m)
 if not 0<=palette_index<len(rows):raise ValueError('Palette index outside map')
 target=rows[palette_index][1];preview=PalettePreview(session,m);result=[];usage={}
 for i,row in enumerate(inspect_map(session.data,m)['entities']):
  o=int(row['offset'],16)
  if not session.data[o+5]&0x80:continue # Shared/global sprites do not use this map palette.
  key=(session.data[o+6],session.data[o+5])
  if key not in usage:
   preview.used.clear();frame=preview.frame(*key);usage[key]=(target in preview.used,frame)
  uses,frame=usage[key]
  if uses and frame:result.append((i,key,frame))
 return result,preview.raw

