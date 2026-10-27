import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_session import EditSession
from mod_export import load_mod,save_mod

DATAS=Path(__file__).resolve().parents[1]/'game/disc/DATA/DATAS.BIN'


@unittest.skipUnless(DATAS.exists(),'private DATAS.BIN not present')
class ModLoadHistoryTests(unittest.TestCase):
 def test_loaded_project_has_no_undo_and_still_saves_its_changes(self):
  # 2026-10-25: Undo after a height paint took back "Imported new maps", cutting
  # the added map blocks while the map table still pointed past the data end.
  stock=DATAS.read_bytes();s=EditSession(stock,verify=False,allow_compatible=True)
  s.replace(0x900,b'\x01\x02',"edit");s.set_tail(bytes(4096),"tail")
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'p.alundramod';save_mod(s,path,'t',163)
   loaded,_=load_mod(stock,path,{})
   self.assertEqual(loaded.undo_stack,[]);self.assertEqual(bytes(loaded.data),bytes(s.data))
   again=Path(folder)/'q.alundramod';save_mod(loaded,again,'t',163)
   self.assertEqual(bytes(load_mod(stock,again,{})[0].data),bytes(s.data))


if __name__=='__main__':unittest.main()
