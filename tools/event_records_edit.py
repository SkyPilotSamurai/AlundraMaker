"""Undoable record movement; tile units derived from map rendering conventions."""
import struct
from map_inspector import inspect_map
from area_map import grid

def move_record(session,m,kind,index,dx,dy):
 if kind not in ("entities","events"):raise ValueError("Unknown record type")
 rows=inspect_map(session.data,m)[kind]
 if not 0<=index<len(rows):raise ValueError("Record outside table")
 o=int(rows[index]["offset"],16)
 values=list(struct.unpack_from("<16B2H" if kind=="entities" else "<8B",session.data,o))
 w,h,_=grid(session,m)
 if kind=="entities":
  values[7]+=dx*2;values[8]+=dy*2
  if not 0<=values[7]<w*2 or not 0<=values[8]<h*2:raise ValueError("Character would move outside the map")
 else:
  for i in (0,2):values[i]+=dx
  for i in (1,3):values[i]+=dy
  if not 0<=values[0]<=values[2]<w or not 0<=values[1]<=values[3]<h:raise ValueError("Event area would move outside the map")
 session.edit_record(m,kind,index,values)
