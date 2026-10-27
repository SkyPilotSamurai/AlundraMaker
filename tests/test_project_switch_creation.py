import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from content_database import ContentDatabase
from project_state_registry import ProjectStateRegistry,MAX_PER_KIND
from project_state_ui import StateSelector,NEW_SWITCH


class Variable:
    def __init__(self,value=''):self.current=value
    def get(self):return self.current
    def set(self,value):self.current=value


class Widget:
    def configure(self,**values):self.values=values


def selector(database,scope='My project'):
    obj=StateSelector.__new__(StateSelector)
    obj.database=database;obj.registry=ProjectStateRegistry(database.document)
    obj.kind='switches';obj.editor=SimpleNamespace(dirty=False);obj.frame=None
    obj.scope=Variable(scope);obj.selected=Variable();obj.mapping={}
    obj.combo=Widget();obj.rename_button=Widget()
    obj.scope_key='switch_scope';obj.id_key='switch_id'
    obj.refresh();return obj


class SwitchCreationTests(unittest.TestCase):
    def test_immediate_numbered_creation_and_selection(self):
        db=ContentDatabase();control=selector(db)
        self.assertIn(NEW_SWITCH,control.combo.values['values'])
        control.selected.set(NEW_SWITCH);control.on_selected()
        self.assertEqual(control.value(),{'switch_id':1,'switch_scope':'project'})
        self.assertEqual(control.registry.get('switches',1)['name'],'Switch1')
        self.assertTrue(control.editor.dirty)
        control.selected.set(NEW_SWITCH);control.on_selected()
        self.assertEqual(control.value()['switch_id'],2)
        self.assertEqual(control.registry.get('switches',2)['name'],'Switch2')

    def test_native_selection_new_switch_allocates_only_private_registry(self):
        db=ContentDatabase();control=selector(db,'Existing game switch')
        control.selected.set(NEW_SWITCH);control.on_selected()
        self.assertEqual(control.scope.get(),'My project')
        self.assertNotIn('native_flag_operand',control.value())
        self.assertEqual(set(db.document['project_state']),
            {'format','switches','variables','next_switch_id','next_variable_id'})

    def test_optional_rename_shared_across_forms_and_reload(self):
        db=ContentDatabase();condition=selector(db);condition.new()
        command=selector(db);command.refresh(1)
        with patch('project_state_ui.simpledialog.askstring',return_value='Tower unlocked'):
            condition.rename()
        command.refresh(1)
        self.assertEqual(command.selected.get(),'0001: Tower unlocked')
        self.assertEqual(command.value()['switch_id'],1)
        restored=ContentDatabase(db.to_json())
        self.assertEqual(ProjectStateRegistry(restored.document).get('switches',1)['name'],'Tower unlocked')
        with patch('project_state_ui.simpledialog.askstring',return_value=None):condition.rename()
        self.assertEqual(condition.registry.get('switches',1)['name'],'Tower unlocked')

    def test_deleted_ids_not_reused_and_capacity_guard(self):
        registry=ProjectStateRegistry({});registry.create_auto('switches');registry.delete('switches',1)
        self.assertEqual(registry.create_auto('switches')['name'],'Switch2')
        for _ in range(MAX_PER_KIND-1):registry.create_auto('switches')
        with self.assertRaises(ValueError):registry.create_auto('switches')

if __name__=='__main__':unittest.main()
