import hashlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from weapon_damage_ui import WeaponDamagePanel
from weapon_damage_fields import weapon_damage_profile
from enemy_definition import BalanceSession


class WeaponDamageFormTests(unittest.TestCase):
    def panel(self):
        path=ROOT/'game/disc/DATA/BALANCE.BIN'
        if not path.exists():self.skipTest('Local input unavailable')
        raw=path.read_bytes()
        panel=WeaponDamagePanel.__new__(WeaponDamagePanel)
        panel.balance=BalanceSession(raw)
        panel.exe=(ROOT/'game/disc/ALUN_CD.EXE').read_bytes()
        panel.item_id=2
        panel.profile=weapon_damage_profile(raw,2,panel.exe)
        panel.loaded_hash=hashlib.sha256(raw).hexdigest()
        panel.values={'normal':SimpleNamespace(get=lambda:'9'), 'charge':SimpleNamespace(get=lambda:'14')}
        return panel

    def test_two_controls_change_native_records_and_undo_together(self):
        panel=self.panel();original=bytes(panel.balance.data)
        result=panel.apply()
        self.assertEqual(result['profile']['normal']['power'],9)
        self.assertEqual(result['profile']['charge']['power'],14)
        self.assertEqual(set(result['changed_entries']),{0,32})
        self.assertEqual(panel.balance.original,original)
        panel.balance.undo();self.assertEqual(bytes(panel.balance.data),original)

    def test_stale_or_invalid_form_cannot_overwrite_other_edits(self):
        panel=self.panel();panel.balance.edit_stats(329,max_hp=29)
        before=bytes(panel.balance.data)
        with self.assertRaisesRegex(ValueError,'changed'):panel.apply()
        self.assertEqual(bytes(panel.balance.data),before)
        panel.loaded_hash=hashlib.sha256(before).hexdigest()
        panel.values['charge']=SimpleNamespace(get=lambda:'invalid')
        with self.assertRaisesRegex(ValueError,'whole number'):panel.apply()
        self.assertEqual(bytes(panel.balance.data),before)

    def test_existing_editor_database_refreshes_cached_us_names(self):
        from editor_ui import Editor
        from content_database import ContentDatabase
        from database_catalogue import entity_names
        db=ContentDatabase();row=db.new('enemy','Muruta (claws)')
        index=next(i for i,entry in enumerate(entity_names()) if entry['text_en'].startswith('◆Muruta (claws)'))
        row['source']={'catalogue_index':index,'default_name':'Muruta (claws)'}
        editor=Editor.__new__(Editor);editor.database=db;editor.db_window=None
        Editor.db_refresh(editor)
        self.assertEqual(row['name'],'Murgg (claws)')


if __name__=='__main__':unittest.main()
