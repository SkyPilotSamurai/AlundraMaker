import struct,unittest
from native_text_pool_repack import repack_pool

class TextPoolRepackTests(unittest.TestCase):
 def fixture(self):
  start=28;block=bytearray(start+60000);values=[0]*128
  for index,offset in [(1,256),(2,256),(3,258)]:values[index]=offset
  struct.pack_into('<128h',block,start,*values);block[start+256:start+262]=b'Hello\0';block[start+40000:start+40012]=b'opaque bytes'
  return block,start,values
 def test_large_padded_payload_retained_without_reusing_padding_or_rebasing_aliases(self):
  original,start,values=self.fixture();rebuilt,report=repack_pool(original,start,values,0,b'New')
  table=struct.unpack_from('<128h',rebuilt,start)
  self.assertEqual(table[1:],tuple(values[1:]));self.assertEqual(table[0],262)
  self.assertEqual(rebuilt[start+256:start+262],b'Hello\0')
  self.assertEqual(rebuilt[start+262:start+266],b'New\0')
  self.assertEqual(rebuilt[:start],original[:start]);self.assertEqual(rebuilt[report['original_payload_tail_offset']:],original[start:])
  self.assertEqual(table[1],table[2]);self.assertEqual(table[3],table[1]+2)
 def test_unknown_or_unterminated_pointers_fail_preserving_source(self):
  for pointer in (-1,1,255):
   original,start,values=self.fixture();values[1]=pointer;struct.pack_into('<h',original,start+2,pointer);before=bytes(original)
   with self.assertRaisesRegex(ValueError,'Unknown native text'):repack_pool(original,start,values,0,b'New')
   self.assertEqual(bytes(original),before)
  original,start,values=self.fixture();original[start+256:]=b'A'*(len(original)-start-256)
  with self.assertRaisesRegex(ValueError,'Unterminated'):repack_pool(original,start,values,0,b'New')
 def test_genuine_referenced_text_capacity_is_not_relaxed(self):
  original,start,values=self.fixture();original[start+256:start+33257]=b'A'*33000+b'\0'
  with self.assertRaisesRegex(ValueError,'signed16'):repack_pool(original,start,values,0,b'New')
 def test_payload_zero_rejected(self):
  original,start,values=self.fixture()
  with self.assertRaisesRegex(ValueError,'zero byte'):repack_pool(original,start,values,0,b'X\0Y')
