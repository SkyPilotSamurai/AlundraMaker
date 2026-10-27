"""Loading bar while a mod project opens (user request 2026-10-16).

A small window over the editor with a bar and the step it is on: reading the
mod file and putting its edits on the game (off the UI thread), preparing the
Database, indexing the maps, and opening the start map. The editor cannot be
clicked meanwhile (the window holds the grab); it closes itself when done."""
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk


class ModLoadingBar:
    def __init__(self, root, name):
        self.root = root
        self.win = win = tk.Toplevel(root)
        win.title('Opening mod')
        win.resizable(False, False); win.transient(root)
        win.protocol('WM_DELETE_WINDOW', lambda: None)
        try:
            from editor_theme import apply_dark
            apply_dark(win)
        except Exception:
            pass
        ttk.Label(win, text=f'Opening {name}', font=('Segoe UI', 14, 'bold'), padding=(18, 14, 18, 4)).pack(fill='x')
        self.text = tk.StringVar(value='Reading the mod file…')
        ttk.Label(win, textvariable=self.text, padding=(18, 2), width=60).pack(fill='x')
        self.bar = ttk.Progressbar(win, mode='determinate', maximum=100, length=520)
        self.bar.pack(fill='x', padx=18, pady=(8, 4))
        self.percent = tk.StringVar(value='0%')
        ttk.Label(win, textvariable=self.percent, padding=(18, 0, 18, 14)).pack(anchor='e')
        win.update_idletasks()
        x = root.winfo_rootx() + max(0, (root.winfo_width() - win.winfo_reqwidth()) // 2)
        y = root.winfo_rooty() + max(0, (root.winfo_height() - win.winfo_reqheight()) // 3)
        win.geometry(f'+{x}+{y}')
        try:
            win.grab_set()
        except tk.TclError:
            pass
        self.span = (0, 100)
        self.paint()

    def paint(self):
        try:
            self.win.update_idletasks(); self.win.update()
        except tk.TclError:
            pass

    def set(self, value, text=None):
        value = max(0, min(100, value))
        try:
            if text:
                self.text.set(text)
            self.bar.configure(value=value); self.percent.set(f'{int(value)}%')
        except tk.TclError:
            return
        self.paint()

    def step(self, start, end, text):
        """The next step fills the bar from start to end (sub-progress via sub())."""
        self.span = (start, end); self.set(start, text)

    def sub(self, done, total, text=None):
        """Progress inside the current step (any thread may not call this: UI only)."""
        start, end = self.span
        if total:
            self.set(start + (end - start) * min(1.0, done / total), text)
        elif text:
            self.set(self.bar['value'], text)

    def run(self, start, end, text, work):
        """work(progress) on a worker thread (it must not touch Tk); the bar moves
        from start to end with its progress(done, total, text) calls."""
        self.step(start, end, text)
        messages = queue.Queue(); finished = tk.BooleanVar(value=False); outcome = []

        def progress(done, total, label=None):
            messages.put(('progress', (done, total, label)))

        def worker():
            try:
                messages.put(('done', work(progress)))
            except BaseException as exc:
                messages.put(('error', exc))

        def poll():
            latest = None
            while True:
                try:
                    kind, value = messages.get_nowait()
                except queue.Empty:
                    break
                if kind == 'progress':
                    latest = value
                else:
                    outcome.append((kind, value))
            if latest:
                self.sub(*latest)
            if outcome:
                finished.set(True); return
            self.root.after(30, poll)

        threading.Thread(target=worker, daemon=True, name='mod-load').start()
        self.root.after(30, poll)
        self.root.wait_variable(finished)
        kind, value = outcome[0]
        if kind == 'error':
            raise value
        self.set(end)
        return value

    def close(self):
        try:
            self.win.grab_release()
        except tk.TclError:
            pass
        try:
            self.win.destroy()
        except tk.TclError:
            pass
