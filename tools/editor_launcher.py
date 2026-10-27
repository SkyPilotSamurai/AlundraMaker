"""Windowed launcher; preserve startup failures without a console window."""
from pathlib import Path
import runpy
import traceback

ROOT = Path(__file__).resolve().parents[1]

def main():
    # Hard crashes (no Python error) write their stack here.
    import faulthandler
    crash = ROOT / 'private-inputs/editor-crash.log'
    crash.parent.mkdir(parents=True, exist_ok=True)
    faulthandler.enable(open(crash, 'a', encoding='utf-8'))
    try:
        runpy.run_path(str(ROOT / 'tools/editor_ui.py'), run_name='__main__')
    except Exception:
        detail = traceback.format_exc()
        log = ROOT / 'private-inputs/editor-startup-error.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(detail, encoding='utf-8')
        # A failed GUI initialization may also prevent this dialog; the log survives.
        try:
            from tkinter import messagebox
            messagebox.showerror('Alundra editor could not start', f'Startup failed. Details were saved to:\n{log}')
        except Exception:
            pass

if __name__ == '__main__':
    main()
