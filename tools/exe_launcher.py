"""Alundra Maker.exe (a folder build: the .exe plus its _internal folder,
which holds Python, Tk, Pillow and numpy, so no Python install is needed).
The editor code itself is read from the project's tools folder next to that
folder, so later edits take effect without rebuilding the .exe."""
import runpy,sys,traceback
from pathlib import Path
here=Path(sys.executable if getattr(sys,'frozen',False) else __file__).resolve().parent
root=next((p for p in (here,here.parent,here.parent.parent) if (p/'tools/editor_ui.py').exists()),here.parent)
if not getattr(sys,'frozen',False):
 import subprocess;subprocess.Popen([sys.executable,'-B',str(root/'tools/editor_launcher.py')],cwd=str(root));sys.exit()
import os;os.chdir(root);sys.path.insert(0,str(root/'tools'));sys.dont_write_bytecode=True
try:runpy.run_path(str(root/'tools/editor_ui.py'),run_name='__main__')
except Exception:
 log=root/'game/editor-startup-error.log';log.parent.mkdir(parents=True,exist_ok=True);log.write_text(traceback.format_exc(),encoding='utf-8')
 try:
  from tkinter import messagebox;messagebox.showerror('Alundra Maker could not start',f'Details: {log}')
 except Exception:pass
