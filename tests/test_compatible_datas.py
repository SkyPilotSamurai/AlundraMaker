import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from editor_session import EditSession

def compatible_fixture():
 table=0x28;start=0x800;count=483;data=bytearray(start+count*2048)
 struct.pack_into("<484I",data,table,*(start+i*2048 for i in range(count+1)))
 for i in range(count):struct.pack_into("<7I",data,start+i*2048,28,28,28,28,28,28,28)
 return bytes(data)

class CompatibleDatasTests(unittest.TestCase):
 def test_structural_compatibility_is_explicitly_not_revision_identity(self):
  session=EditSession(compatible_fixture(),allow_compatible=True)
  self.assertFalse(session.source_verified)
  with self.assertRaises(ValueError):EditSession(compatible_fixture())

 def test_rejects_misaligned_map_table(self):
  data=bytearray(compatible_fixture());struct.pack_into("<I",data,0x28+4,0x801)
  with self.assertRaises(ValueError):EditSession(data,allow_compatible=True)

if __name__=="__main__":unittest.main()
