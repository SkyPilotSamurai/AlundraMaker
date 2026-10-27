"""Bounded local text pool rebuild; preserve the complete old payload as a tail.

Offsets remain native signed16 values. This does not reuse padding or relax
limits. It retains the original table and every referenced string at its exact
relative offset, and keeps the complete old section bytes after the new pool.
"""
import struct

def repack_pool(block,start,values,slot,payload):
 block=bytes(block);payload=bytes(payload)
 if len(values)!=128 or not 0<=slot<128 or start<28 or start+256>len(block):
  raise ValueError('Invalid complete native text table')
 if tuple(values)!=struct.unpack_from('<128h',block,start):
  raise ValueError('Native text table values differ from source bytes')
 if b'\0' in payload:raise ValueError('Dialogue cannot contain a zero byte')
 extent=256
 for index,relative in enumerate(values):
  if relative==0:continue
  else:
   if not 256<=relative<=32767 or start+relative>=len(block):
    raise ValueError('Unknown native text pointer cannot be repacked')
   end=block.find(b'\0',start+relative)
   if end<0:raise ValueError('Unterminated native text cannot be repacked')
   extent=max(extent,end-start+1)
 if extent>32767 or extent+len(payload)+1>32768:
  raise ValueError('Compact text pool exceeds native signed16 bounds')
 compact=bytearray(block[start:start+extent]);struct.pack_into('<h',compact,slot*2,extent);compact.extend(payload+b'\0');compact=bytes(compact);old=block[start:]
 rebuilt=block[:start]+compact+old
 assert rebuilt[:start]==block[:start] and rebuilt[start+len(compact):]==old
 return bytearray(rebuilt),{'text_pool_repacked':True,'compact_pool_bytes':len(compact),'original_text_payload_bytes_preserved':len(old),'original_slot_offsets_preserved':127,'original_payload_tail_offset':start+len(compact),'native_signed16_limit':32767}

def experimental_append_repacked_text(datas,map_id,text,**options):
 """Owned experiment only: use the existing proven slot/wrapping rules."""
 from native_text_allocation import append_local_text
 from map_block_repack import pointers,sections,replace_block
 from map_loader_constraints import validate_layout
 try:return append_local_text(datas,map_id,text,**options)
 except ValueError as error:
  if str(error)!='New text exceeds native signed16 map-local text bounds':raise
 table=pointers(datas);block=bytes(datas[table[map_id]:table[map_id+1]]);start=sections(block)[6];values=struct.unpack_from('<128h',block,start)
 # Validate all128 source roots before making even an intermediate copy.
 extent=256
 for relative in values:
  if relative==0:continue
  if not 256<=relative<=32767 or start+relative>=len(block):raise ValueError('Unknown native text pointer cannot be repacked')
  end=block.find(b'\0',start+relative)
  if end<0:raise ValueError('Unterminated native text cannot be repacked')
  extent=max(extent,end-start+1)
 temporary=replace_block(bytes(datas),map_id,block[:start+extent])   # a trial: datas must stay as it is
 allocated,report=append_local_text(temporary,map_id,text,**options)
 roots=pointers(allocated);newblock=allocated[roots[map_id]:roots[map_id+1]];newstart=sections(newblock)[6];offset=struct.unpack_from('<h',newblock,newstart+2*report['text_index'])[0];end=newblock.find(0,newstart+offset);payload=bytes(newblock[newstart+offset:end])
 rebuilt,proof=repack_pool(block,start,values,report['text_index'],payload)
 result=replace_block(datas,map_id,rebuilt);validate_layout(result);report.update(proof)
 return result,report
