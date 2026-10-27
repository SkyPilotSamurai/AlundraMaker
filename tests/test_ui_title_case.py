import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ui_title_case import title_case


class TitleCaseTests(unittest.TestCase):
    def test_rule(self):
        self.assertEqual(title_case('Save mod as...'),'Save Mod As...')
        self.assertEqual(title_case('Build & test in BizHawk...'),'Build & Test In BizHawk...')
        self.assertEqual(title_case("Zazan's rock"),"Zazan's Rock")
        self.assertEqual(title_case('Save DATAS copy...'),'Save DATAS Copy...')

    def test_widgets_and_menus_after_install(self):
        import tkinter as tk
        from tkinter import ttk
        from ui_title_case import install
        try:root=tk.Tk()
        except tk.TclError as exc:self.skipTest(str(exc))
        try:
            install()
            b=ttk.Button(root,text='use source defaults');self.assertEqual(b.cget('text'),'Use Source Defaults')
            b.configure(text='add items...');self.assertEqual(b.cget('text'),'Add Items...')
            c=ttk.Checkbutton(root,text='tile grid');self.assertEqual(c.cget('text'),'Tile Grid')
            r=ttk.Radiobutton(root,text='select tile',value='x');self.assertEqual(r.cget('text'),'Select Tile')
            self.assertEqual(str(b).split('.')[-1].startswith('!button'),True)
            m=tk.Menu(root,tearoff=False);m.add_command(label='open game data...');m.add_checkbutton(label='height preview')
            self.assertEqual(m.entrycget(0,'label'),'Open Game Data...');self.assertEqual(m.entrycget(1,'label'),'Height Preview')
            self.assertIn('command',m.entryconfig(0))   # query form used by Menu.delete
            m.entryconfigure(0,label='renamed item');self.assertEqual(m.entrycget(0,'label'),'Renamed Item')
            m.delete(0,'end');self.assertIsNone(m.index('end'))
            v=tk.StringVar(master=root,value='choose switch…');t=ttk.Button(root,textvariable=v);self.assertEqual(v.get(),'choose switch…')
        finally:root.destroy()


if __name__=='__main__':unittest.main()
