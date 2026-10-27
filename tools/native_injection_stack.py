"""Separate the fingerprinted native descending stack from prepended code.

The main loop explicitly switches SP to8001FFF0. Its call frames can overwrite
editor injections below80020000. Move that stack below the lowest loaded
injected byte, preserving the native switch/restore helper and all existing
code addresses. 32KiB remains above 80010000 (STACK_FLOOR).
Measured 2026-10-23 (BizHawk, zero-word canary, docs/2026-10-22-maker-demo-qa.txt):
deepest use 1,288 bytes below the top (map transitions); boss fight 1,004; boot ~600.
A 16KiB floor was tried and reverted: the game itself keeps a buffer at 80010000
(0x800614A4 copies 0x760 bytes there; 0x80063828, data word 0x80029B68), BizHawk's
Nymashock core has no read callbacks, so no proof that nothing reads that space.
"""
import struct
STACK_SITE=0x80083F94
CALLER=(0x27BDFFE8,0xAFBF0014,0x0C023792,0xAFB00010,0x3C048001,
        0x0C02109F,0x3484FFF0,0x0C00B04B,0x00408021,0x0C02109F,
        0x02002021,0x8FBF0014,0x8FB00010,0x27BD0018,0x03E00008,0)
HELPER=(0x03A01021,0x03E00008,0x0080E821)
STACK_FLOOR=0x80018000   # lowest allowed code start: 32KiB above 0x80010000 (16KiB not proven safe, 2026-10-23)

def protect(exe):
 output=bytearray(exe)
 if output[:8]!=b'PS-X EXE':raise ValueError('Stack protection requires PS-X EXE')
 load,size=struct.unpack_from('<II',output,0x18)
 if len(output)!=size+0x800 or not STACK_FLOOR<=load<0x80020000:
  raise ValueError('Injected stack allocation must retain at least 32KiB above 80010000')
 def words(address,count):
  offset=address-load+0x800
  if offset<0x800 or offset+count*4>len(output):raise ValueError('Native stack signature outside module')
  return struct.unpack_from('<'+'I'*count,output,offset)
 observed=list(words(0x80083F7C,len(CALLER)))
 previous=observed[6]
 if previous>>16!=0x3484:raise ValueError('Native stack setup instruction changed')
 old_top=0x80010000|(previous&65535)
 if old_top!=0x8001FFF0 and not (STACK_FLOOR-16<=old_top<0x8001FFF0 and old_top&15==0):
  raise ValueError('Native stack setup preimage is unsupported')
 observed[6]=CALLER[6]
 if tuple(observed)!=CALLER or words(0x8008427C,len(HELPER))!=HELPER:
  raise ValueError('Native stack switch/restore contract differs')
 top=load-16
 struct.pack_into('<I',output,STACK_SITE-load+0x800,0x34840000|(top&65535))
 return bytes(output),{'native_site':STACK_SITE,'original_stack_top':0x8001FFF0,
  'previous_stack_top':old_top,'stack_top':top,'lowest_injected_address':load,
  'reserved_stack_bytes':top-0x80010000,'injection_stack_overlap':False,
  'scope':'Exact native setup relocated below injections; maximum depth and hardware not certified'}
