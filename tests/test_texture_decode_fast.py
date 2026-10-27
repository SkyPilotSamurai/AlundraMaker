import sys,unittest,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from texture_codec import unpack_ez,pack_ez

def reference(source,limit=196608):
 if source[:2]!=b'EZ' or len(source)<6:raise ValueError('header')
 out=bytearray();i=6
 while i<len(source):
  v=source[i];i+=1
  if v!=173:out.append(v)
  else:
   if i>=len(source):raise ValueError('escape')
   d=source[i];i+=1
   if d==0:out.append(173)
   else:
    if i>=len(source):raise ValueError('match')
    n=source[i];i+=1
    if d==255 and n==0:return bytes(out),i
    if n==0 or d>len(out):raise ValueError('invalid')
    if len(out)+n>limit:raise ValueError('limit')
    window=out[-d:];out.extend((window*((n+d-1)//d))[:n])
  if len(out)>limit:raise ValueError('limit')
  if len(out)==limit:return bytes(out),i
 raise ValueError('end')

class BulkLiteralTests(unittest.TestCase):
 def test_differential_packed_streams_and_limits(self):
  rng=random.Random(2219)
  for size in (0,1,2,31,255,256,1024):
   raw=bytes(rng.randrange(256) for _ in range(size))+b'abab'*64+b'\xad'*32
   packed=pack_ez(raw)
   for source in (packed,bytearray(packed),memoryview(packed)):
    for limit in (1,2,16,size+1,len(raw),len(raw)+1):
     try:expected=reference(source,limit)
     except ValueError:
      with self.assertRaises(ValueError):unpack_ez(source,limit)
     else:self.assertEqual(unpack_ez(source,limit),expected)
 def test_differential_malformed_streams(self):
  rng=random.Random(919)
  for _ in range(500):
   source=b'EZ'+bytes(4)+bytes(rng.randrange(256) for _ in range(rng.randrange(50)))
   try:expected=reference(source,128)
   except ValueError:
    with self.assertRaises(ValueError):unpack_ez(source,128)
   else:self.assertEqual(unpack_ez(source,128),expected)
