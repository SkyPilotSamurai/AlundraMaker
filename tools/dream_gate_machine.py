"""Small instruction runner for injected dream-gate tests, not a PS1 emulator.
Supports only the integer instructions emitted by this patch and executes
branch delay slots. Loads are checked against emitted NOP delay slots.
"""
import struct
class GateMachine:
 def __init__(self, exe):
  self.r=[0]*32; self.mem={}
  load,size=struct.unpack_from("<II",exe,0x18)
  self.base=load; self.code=exe[0x800:0x800+size]
 def put(self,a,v,n=4):
  for i in range(n):self.mem[a+i]=(v>>(8*i))&255
 def get(self,a,n=4):
  if self.base<=a and a+n<=self.base+len(self.code):
   return int.from_bytes(self.code[a-self.base:a-self.base+n],"little")
  return sum(self.mem.get(a+i,0)<<(8*i) for i in range(n))
 def step(self,pc):
  w=self.get(pc); op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;im=w&65535;si=im if im<32768 else im-65536
  r=self.r; target=None
  signed=lambda v:v if v<0x80000000 else v-0x100000000
  if op==0:
   f=w&63
   if f==0:r[rd]=r[rt]<<(w>>6&31)
   elif f in (0x20,0x21):r[rd]=r[rs]+r[rt]
   elif f==0x2a:r[rd]=int(signed(r[rs])<signed(r[rt]))
   elif f==8:target=r[rs]
   else:raise AssertionError(hex(w))
  elif op==9:r[rt]=r[rs]+si
  elif op==15:r[rt]=im<<16
  elif op==10:r[rt]=int(signed(r[rs])<si)
  elif op in (0x23,0x21):
   assert self.get(pc+4)==0,"load delay not modelled without NOP"
   val=self.get((r[rs]+si)&0xffffffff,4 if op==0x23 else 2)
   if op==0x21 and val&32768:val-=65536
   r[rt]=val
  elif op==0x2b:self.put((r[rs]+si)&0xffffffff,r[rt])
  elif op in (4,5):
   if (r[rs]==r[rt])==(op==4):target=pc+4+si*4
  elif op==1 and rt==1:
   if signed(r[rs])>=0:target=pc+4+si*4
  elif op in (2,3):
   target=((pc+4)&0xf0000000)|((w&0x3ffffff)<<2)
   if op==3:r[31]=pc+8
  else:raise AssertionError(hex(w))
  self.r=[v&0xffffffff for v in r];self.r[0]=0
  return target
 def run(self,pc,stops):
  for _ in range(4000):
   if pc in stops:return pc
   target=self.step(pc)
   if target is not None:
    assert self.step(pc+4) is None
    pc=target
   else:pc+=4
  raise AssertionError("loop")
