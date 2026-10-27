import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import item_text
ETC=ROOT/'game/disc/DATA/ETC_USA.R'


@unittest.skipUnless(ETC.is_file(),'needs private ETC_USA.R')
class ItemText(unittest.TestCase):
    def test_rename_keeps_size_and_other_text(self):
        raw=ETC.read_bytes();row=dict(kind='item',source=dict(item_id=36),data=dict(game_text=dict(name="Alundra's Herbs")))
        out,report=item_text.patch(raw,[row])
        self.assertEqual(len(out),len(raw));self.assertEqual(report,[dict(item=36,field='name')])
        self.assertEqual(item_text.stock(out,row)['name'],"Alundra's Herbs")
        self.assertTrue(all(item_text._at(out,s)==item_text._at(raw,s) for s in range(1024) if s!=0x224))

    def test_too_long_refused(self):
        raw=ETC.read_bytes();row=dict(kind='item',source=dict(item_id=36),data=dict(game_text=dict(description='x'*len(raw))))
        with self.assertRaises(ValueError):item_text.patch(raw,[row])
