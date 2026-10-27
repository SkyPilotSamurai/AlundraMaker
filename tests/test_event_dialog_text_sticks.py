"""Bug 2026-10-24: edited Show Text did not stick when page['commands'] was
replaced (auto-apply / _commit_command) while the CommandDialog was open."""
import sys, unittest, types
from copy import deepcopy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import event_command_dialog
from event_graph_ui import EventGraphWindow


class TextSticksTest(unittest.TestCase):
    def run_case(self,index):
        cmds=[{'type':'show_text','text':'old'},
              {'type':'if','then':[{'type':'show_text','text':'old'}],'else':[]}]
        stub=types.SimpleNamespace(working={'pages':[{'id':'p','commands':cmds}]},page_id='p',
            command_index=None,insert_target=None,editor=types.SimpleNamespace(dirty=False),db=None,window=None,
            refresh_commands=lambda *a:None,_commit_command=lambda:None)
        stub.current_page=lambda:EventGraphWindow.current_page(stub)
        stub._locate=lambda iid:EventGraphWindow._locate(stub,iid)
        captured={}
        old=event_command_dialog.CommandDialog
        event_command_dialog.CommandDialog=lambda e,w,row,save,database=None:captured.update(row=row,save=save)
        try:EventGraphWindow.open_command_form(stub,index=index)
        finally:event_command_dialog.CommandDialog=old
        stub.working=deepcopy(stub.working)   # auto-apply replaced the event meanwhile
        captured['save'](dict(captured['row'],text='new'))
        return stub.working['pages'][0]['commands']

    def test_top_level(self):
        self.assertEqual(self.run_case('0')[0]['text'],'new')

    def test_inside_branch(self):
        self.assertEqual(self.run_case('1:then:0')[1]['then'][0]['text'],'new')


if __name__=='__main__':unittest.main()
