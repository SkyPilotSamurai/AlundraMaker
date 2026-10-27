import sys,unittest,struct
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from item_categories import *
from mod_export import prepare_item_metadata_executable
from item_categories_ui import ItemCategoryPanel


class ItemCategoryTests(unittest.TestCase):
    def row(self,identity):return {'id':'item:0001','kind':'item','name':'Local item','source':{'item_id':identity},'data':{}}
    def exe(self):
        evidence=json.loads((ROOT/'data/inventory-selection.json').read_text())
        load=0x80020000;size=0xb0000;raw=bytearray(size+0x800);raw[:8]=b'PS-X EXE'
        struct.pack_into('<II',raw,0x18,load,size)
        words=[int(word,16) for word in evidence['words']]
        off=int(evidence['entry'],16)-load+0x800
        struct.pack_into('<'+'I'*len(words),raw,off,*words)
        off=TABLE+36*10-load+0x800
        struct.pack_into('<hHhhH',raw,off,12,0x8420,0,9,66)
        return bytes(raw)
    def test_grouping_does_not_invent_use_handlers(self):
        self.assertEqual(category_for(self.row(36)),'Consume')
        self.assertEqual(category_for(self.row(51)),'Accessory')
        self.assertEqual(category_for(self.row(73)),'Key item')
        original=self.row(36);edited=apply(original,'Key item')
        self.assertNotIn('item_native_properties',edited['data'])
        self.assertEqual(original['data'],{})
    def test_verified_metadata_export_preserves_unrelated_bits_icon_and_input(self):
        exe=self.exe();row=apply(self.row(36),'Consume',exe=exe,menu_group=13,
            highest_priority=True,priority=2,max_quantity=12)
        patched,report=patch_native_properties(exe,[row]);props=native_properties(patched,36)
        self.assertEqual((props['menu_group'],props['priority'],props['max_quantity']),(13,2,12))
        self.assertEqual(props['flags_raw'],0x8421);self.assertEqual(props['icon_id'],66)
        self.assertEqual(native_properties(exe,36)['max_quantity'],9)
        self.assertFalse(report['category_changes_native'])
        self.assertEqual(patch_native_properties(patched,[row])[0],patched)
    def test_bad_preimage_code_clones_and_bounds_reject(self):
        exe=self.exe();row=apply(self.row(36),'Consume',exe=exe,max_quantity=12)
        bad=bytearray(exe);bad[TABLE+36*10-0x80020000+0x800+8]=5
        with self.assertRaisesRegex(ValueError,'changed since'):patch_native_properties(bad,[row])
        bad=bytearray(exe);bad[0x8004F810-0x80020000+0x800]=0
        with self.assertRaisesRegex(ValueError,'signature'):patch_native_properties(bad,[row])
        clone=dict(row,clone_of='item:0002')
        with self.assertRaisesRegex(ValueError,'Cloned'):apply(clone,'Consume',exe=exe,max_quantity=4)
        with self.assertRaises(ValueError):apply(row,'Consume',exe=exe,menu_group=32)
    def test_header_mapping_supports_prepended_composed_exe(self):
        exe=self.exe();row=apply(self.row(36),'Consume',exe=exe,max_quantity=12)
        shifted=bytearray(exe[:0x800]+bytes(0x800)+exe[0x800:])
        struct.pack_into('<II',shifted,0x18,0x8001F800,len(shifted)-0x800)
        patched,_=patch_native_properties(shifted,[row])
        self.assertEqual(native_properties(patched,36)['max_quantity'],12)
    def test_export_without_qol_options_preserves_original_source_identity(self):
        exe=self.exe();row=apply(self.row(36),'Consume',exe=exe,max_quantity=12)
        session=SimpleNamespace(content_database={'definitions':[row]},extra_files={})
        report=prepare_item_metadata_executable(session,exe)
        self.assertEqual(session.extra_files['ALUN_CD.EXE'].original,exe)
        self.assertEqual(native_properties(session.extra_files['ALUN_CD.EXE'].data,36)['max_quantity'],12)
        self.assertEqual(len(report['changes']),1)
    def test_unchanged_panel_does_not_create_export_properties(self):
        class Var:
            def __init__(self,value):self.value=value
            def get(self):return self.value
        panel=ItemCategoryPanel.__new__(ItemCategoryPanel);panel.exe_provider=self.exe
        panel.native_enabled=True;panel.category=Var('Consume');panel.menu_group=Var('12')
        panel.priority=Var('0');panel.maximum=Var('9');panel.highest=Var(False)
        panel.native_baseline=dict(menu_group=12,priority=0,max_quantity=9,highest_priority=False)
        result=panel.apply(self.row(36))
        self.assertNotIn('item_native_properties',result['data'])
        self.assertNotIn('item_metadata_native',result['source'])

if __name__=='__main__':unittest.main()
