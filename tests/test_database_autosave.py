import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_ui import Editor
from content_database import ContentDatabase


class Var:
    def __init__(self,v):self.v=v
    def get(self):return self.v
    def set(self,v):self.v=v


class Text:
    def __init__(self):self.modified=False
    def edit_modified(self,value=None):
        if value is None:return self.modified
        self.modified=value
    def get(self,*a):return '{}'


class Tree:
    def __init__(self):self.items={}
    def exists(self,i):return True
    def item(self,i,**kw):self.items[i]=kw


class Window:
    def winfo_exists(self):return True


def editor():
    db=ContentDatabase();row=db.new('npc','Old name')
    e=Editor.__new__(Editor);e.database=db;e.db_window=Window();e.db_active_kind='npc'
    e.db_loaded=('npc',row['id']);e.db_texts={'npc':Text()};e.db_trees={'npc':Tree()}
    e.db_class_name=Var('Old name');e.db_field_vars={};e.db_attack_vars={};e.db_hue_vars={'npc':Var('0')}
    e.status=Var('');e.dirty=False;e.root=SimpleNamespace(after_cancel=lambda j:None);e.session=None
    return e,row['id']


class AutosaveTests(unittest.TestCase):
    def test_unchanged_class_is_not_marked_dirty(self):
        e,cid=editor();e.db_autosave();self.assertFalse(e.dirty)

    def test_edits_are_remembered_without_apply(self):
        e,cid=editor();e.db_class_name.set('Village Elder');e.db_hue_vars['npc'].set('40')
        e.db_autosave()
        row=e.database.get(cid)
        self.assertEqual(row['name'],'Village Elder');self.assertEqual(row['data']['palette_shift'],{'hue_degrees':40})
        self.assertTrue(e.dirty);self.assertEqual(e.db_trees['npc'].items[cid],{'text':'Village Elder'})

    def test_changes_made_by_other_windows_are_not_overwritten(self):
        e,cid=editor();e.database.get(cid)['data']['extra_from_attack_window']=7
        e.db_class_name.set('Renamed');e.db_autosave()
        self.assertEqual(e.database.get(cid)['data']['extra_from_attack_window'],7)

    def test_invalid_value_is_reported_not_raised(self):
        e,cid=editor();e.db_hue_vars['npc'].set('abc')
        e.db_autosave();self.assertIn('Not saved yet',e.status.get())


if __name__=='__main__':unittest.main()
