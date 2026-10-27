import struct,sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from starting_equipment import STAT_SITES,read_starting_stats,patch_starting_stats,validate_starting_stats


def stats_fixture():
    b=bytearray(0x40000);b[:8]=b'PS-X EXE'
    struct.pack_into('<4I',b,0x10,0x80020000,0,0x80020000,len(b)-0x800)
    stock={'max_hp':0x2404000A,'hp':0x2404000A,'max_mp':0x00002021,'mp':0x00002021,'gilder':0x00002021}
    for key,address,call,_ in STAT_SITES:
        struct.pack_into('<II',b,0x800+address-0x80020000,call,stock[key])
    return bytes(b)


class StartingStatsTests(unittest.TestCase):
    def test_reads_stock_new_game_values(self):
        self.assertEqual(read_starting_stats(stats_fixture()),dict(max_hp=10,hp=10,max_mp=0,mp=0,gilder=0,keys=0))
    def test_patch_changes_only_argument_words_and_round_trips(self):
        exe=stats_fixture()
        new,report=patch_starting_stats(exe,dict(max_hp=20,hp=15,max_mp=2,mp=1,gilder=500))
        self.assertEqual(read_starting_stats(new),dict(max_hp=20,hp=15,max_mp=2,mp=1,gilder=500,keys=0))
        self.assertEqual(len(report['changes']),5)
        changed=[i for i,(a,b) in enumerate(zip(exe,new)) if a!=b]
        allowed=set()
        for _,address,_,_ in STAT_SITES:
            o=0x800+address+4-0x80020000;allowed.update(range(o,o+4))
        self.assertTrue(set(changed)<=allowed)
        back,_=patch_starting_stats(new,dict(max_hp=10,hp=10,max_mp=0,mp=0,gilder=0))
        self.assertEqual(back,exe)
    def test_none_preserves_and_limits_are_enforced(self):
        exe=stats_fixture()
        self.assertEqual(patch_starting_stats(exe,None)[0],exe)
        for bad in (dict(max_hp=51,hp=1,max_mp=0,mp=0,gilder=0),dict(max_hp=10,hp=11,max_mp=0,mp=0,gilder=0),
                    dict(max_hp=10,hp=10,max_mp=5,mp=0,gilder=0),dict(max_hp=10,hp=10,max_mp=1,mp=2,gilder=0),
                    dict(max_hp=10,hp=10,max_mp=0,mp=0,gilder=10000),dict(max_hp=0,hp=0,max_mp=0,mp=0,gilder=0)):
            with self.assertRaises(ValueError):validate_starting_stats(bad)
    def test_changed_call_is_rejected(self):
        b=bytearray(stats_fixture());_,address,_,_=STAT_SITES[0]
        struct.pack_into('<I',b,0x800+address-0x80020000,0)
        with self.assertRaises(ValueError):read_starting_stats(bytes(b))
    def test_panel_stores_stats_only_when_changed(self):
        from starting_equipment_ui import StartingEquipmentPanel
        class Var:
            def __init__(self,v):self.v=v
            def get(self):return self.v
        p=StartingEquipmentPanel.__new__(StartingEquipmentPanel)
        p.database=SimpleNamespace(document={'mod_options':{}});p.editor=SimpleNamespace(database=p.database)
        p.selected=[];p.custom=False;p.stat_defaults=dict(max_hp=10,hp=10,max_mp=0,mp=0,gilder=0)
        p.stat_vars={k:Var(str(v)) for k,v in p.stat_defaults.items()}
        p.apply();self.assertNotIn('starting_stats',p.database.document['mod_options'])
        p.stat_vars['gilder']=Var('250');p.apply()
        self.assertEqual(p.database.document['mod_options']['starting_stats']['gilder'],250)

    def test_item_grid_picker_can_add_several_without_closing(self):
        from unittest.mock import MagicMock
        from database_picker import DatabasePicker
        obj=DatabasePicker.__new__(DatabasePicker);obj.keep_open=True;obj.category=lambda:'item'
        obj.rows={'item':[{'id':'item:0001','name':'Herbs'}]};obj.selected={'item':'item:0001'}
        obj.choose=MagicMock();obj.finish=MagicMock();obj.description=MagicMock()
        obj.select();obj.select()
        self.assertEqual(obj.choose.call_count,2);obj.finish.assert_not_called()
        obj.description.set.assert_called_with('Added Herbs')

    def test_meia_entry_saves_to_its_own_definition_not_build_options(self):
        from starting_equipment_ui import StartingEquipmentPanel
        class Var:
            def __init__(self,v):self.v=v
            def get(self):return self.v
        meia={'id':'player:0002','data':{}}
        p=StartingEquipmentPanel.__new__(StartingEquipmentPanel)
        p.database=SimpleNamespace(document={'mod_options':{}},get=lambda i:meia);p.editor=SimpleNamespace(database=p.database)
        p.meia_id='player:0002';p.selected=[5,1,5];p.custom=True
        p.stat_defaults=dict(max_hp=10,hp=10,max_mp=0,mp=0,gilder=0)
        p.stat_vars={k:Var(str(v)) for k,v in dict(max_hp=12,hp=12,max_mp=1,mp=1,gilder=7).items()}
        p.apply()
        self.assertEqual(meia['data']['starting_equipment'],[1,5])
        self.assertEqual(meia['data']['starting_stats']['gilder'],7)
        self.assertEqual(p.database.document['mod_options'],{})


if __name__=='__main__':unittest.main()
