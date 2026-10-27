import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import custom_consume as cc


class CustomConsume(unittest.TestCase):
    def test_settings_and_table(self):
        row=dict(kind='item',source=dict(item_id=43),data=dict(consume=dict(hp='part',hp_value=4,hp_min=5,mp='amount',mp_value=3,revive=True)))
        ch=cc.settings([row]);self.assertEqual(ch[43]['hp'],'part')
        raw=cc.Block(ch)(0x80018000);table=cc._words(0x80018000)[2]
        o=table-0x80018000+cc.ENTRY*(43-31)
        self.assertEqual(raw[o:o+8],bytes([3,2,2,0,5,0,1,3]))
        row['source']['item_id']=60
        with self.assertRaises(ValueError):cc.settings([row])
