"""Tile picker grouped spatially, retaining map palette and wall arrangement."""
from PIL import Image,ImageDraw
from area_map import grid

def map_library(renderer,columns=1):
 if type(columns) is not int or not 1<=columns<=8:raise ValueError("Tile picker columns must be1..8")
 w,h,cells=grid(renderer.session,renderer.m);groups={}
 for c in cells:
  x,y=c["x"],c["y"];v=c["values"];px=(x%8)*24;py=(y%8)*16-v[3]*16
  pieces=[(px,py,v[4])]+[(px,py+(i+1-shift)*16,code) for _,code,shift,i in c["walls"]]
  visible=[p for p in pieces if renderer.tile(p[2]).getbbox()]
  if visible:groups.setdefault((x//8,y//8),[]).extend(visible)
 sections=[];height=0;row_height=0
 for index,((gx,gy),pieces) in enumerate(sorted(groups.items(),key=lambda item:(item[0][1],item[0][0]))):
  low=min(y for x,y,code in pieces);high=max(y+16 for x,y,code in pieces)
  if index and index%columns==0:height+=row_height;row_height=0
  sections.append((gx,gy,pieces,low,height,(index%columns)*240));row_height=max(row_height,high-low+34)
 image=Image.new("RGBA",(240*columns,max(40,height+row_height)),(25,31,41,255));draw=ImageDraw.Draw(image);hits=[]
 for gx,gy,pieces,low,top,left in sections:
  draw.text((left+8,top+3),f"Area {gx*8},{gy*8}",fill=(184,199,218,255))
  for x,y,code in pieces:
   px=left+x+8;py=top+24+y-low;image.alpha_composite(renderer.tile(code),(px,py));hits.append((px,py,code))
 return image,hits


def map_source_views(renderer):
 """Actual static map arrangement, cropped only at tile boundaries.

 Sections are connected visible artwork, not guessed room names. Black void
 tiles remain in the whole-map image but do not join separate rooms together.
 The independent renderer prevents picker elevation from changing map hit tests.
 """
 image,_,margin=renderer.render(True)
 _,_,cells=grid(renderer.session,renderer.m)
 hits=[];height_hits=[];grid_hits=[];occupied=set();artwork={}
 for c in cells:
  v=c['values'];x=c['x']*24;y=c['y']*16+margin-v[3]*16
  pieces=[(x,y,v[4],'floor')]+[(x,y+(i+1-shift)*16,code,'wall') for _,code,shift,i in c['walls']]
  for px,py,code,kind in pieces:
   tile=renderer.tile(code)
   if not tile.getbbox():continue
   if px<0 or py<0 or px+24>image.width or py+16>image.height:continue
   hits.append((px,py,code));height_hits.append((px,py,code,v[3]))
   # Source grid position: group brushes copy by map cell, not by picture position.
   grid_hits.append((px,py,code,c['x'],c['y'],v[3],kind))
   # Transparent RGB is normally zero; include only opaque coloured artwork.
   if code not in artwork:artwork[code]=any(a and max(r,g,b)>8 for r,g,b,a in getattr(tile,'get_flattened_data',tile.getdata)())
   if artwork[code]:occupied.add((px//24,py//16))
 def crop(points,label):
  left=min(x for x,y in points)*24;top=min(y for x,y in points)*16
  right=(max(x for x,y in points)+1)*24;bottom=(max(y for x,y in points)+1)*16
  selected=[(x-left,y-top,code) for x,y,code in hits if left<=x<right and top<=y<bottom]
  selected_heights=[(x-left,y-top,code,height) for x,y,code,height in height_hits if left<=x<right and top<=y<bottom]
  selected_grid=[(x-left,y-top,code,tx,ty,h,kind) for x,y,code,tx,ty,h,kind in grid_hits if left<=x<right and top<=y<bottom]
  return dict(label=label,image=image.crop((left,top,right,bottom)),hits=selected,height_hits=selected_heights,grid_hits=selected_grid,bounds=(left,top,right,bottom))
 if not occupied:
  return [dict(label='Whole map',image=image,hits=hits,height_hits=height_hits,grid_hits=grid_hits,bounds=(0,0,image.width,image.height))]
 views=[crop(occupied,'Whole map')];remaining=set(occupied);components=[]
 while remaining:
  first=min(remaining,key=lambda p:(p[1],p[0]));remaining.remove(first);component={first};pending=[first]
  while pending:
   x,y=pending.pop()
   for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if p in remaining:remaining.remove(p);component.add(p);pending.append(p)
  components.append(component)
 components.sort(key=lambda pts:(min(y for x,y in pts),min(x for x,y in pts)))
 sections=[]
 for points in components:
  x0=min(x for x,y in points);y0=min(y for x,y in points)
  if max(x for x,y in points)-x0<24 and max(y for x,y in points)-y0<24:
   sections.append(points)
  else:
   # Large connected landscapes get navigable spatial sections as well.
   groups={}
   for x,y in points:groups.setdefault(((x-x0)//24,(y-y0)//24),set()).add((x,y))
   sections.extend(group for key,group in sorted(groups.items(),key=lambda item:(item[0][1],item[0][0])))
 for i,points in enumerate(sections,1):
  views.append(crop(points,f'Section {i} - {min(x for x,y in points)},{min(y for x,y in points)}'))
 return views
