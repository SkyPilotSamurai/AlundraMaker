"""Visible, responsive memory-loading window; workers never call Tk."""
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk


def run_memory_load(root, work, report=None):
    """Run work(progress) off the UI thread, pumping Tk until completion.
    report(done, total, text), optional, is told the progress on the UI thread
    (the Open mod loading bar)."""
    win=tk.Toplevel(root);win.title('Preloading memory — Alundra')
    win.geometry('620x230');win.resizable(False,False);win.transient(root)
    win.protocol('WM_DELETE_WINDOW',lambda:None)
    ttk.Label(win,text='Loading game into memory',font=('Segoe UI',16,'bold'),padding=(18,16,18,6)).pack(fill='x')
    label=tk.StringVar(value='Preparing database and game assets…')
    ttk.Label(win,textvariable=label,wraplength=580,padding=(18,4)).pack(fill='x')
    bar=ttk.Progressbar(win,mode='indeterminate',maximum=100)
    bar.pack(fill='x',padx=18,pady=12);bar.start(20)
    count=tk.StringVar(value='Preparing…');ttk.Label(win,textvariable=count,padding=(18,0)).pack(anchor='w')
    elapsed=tk.StringVar(value='0 seconds elapsed')
    ttk.Label(win,textvariable=elapsed,padding=(18,8)).pack(anchor='w')
    win.withdraw()   # no loading window: the load runs quietly behind the editor
    messages=queue.Queue();result=[];failure=[];started=time.monotonic()
    def progress(done,total,text):messages.put(('progress',(done,total,text)))
    def worker():
        try:messages.put(('done',work(progress)))
        except Exception as exc:messages.put(('error',exc))
    def poll():
        latest=None;terminal=None
        while True:
            try:kind,value=messages.get_nowait()
            except queue.Empty:break
            if kind=='progress':latest=value
            else:terminal=(kind,value)
        if latest:
            done,total,text=latest;label.set(text)
            if report is not None:
                try:report(done,total,text)
                except Exception:pass
            if total:
                bar.stop();bar.configure(mode='determinate',value=min(100,100*done/total))
                count.set(f'{done:,} / {total:,} · {100*done/total:.0f}%')
            else:count.set('Preparing database…')
        elapsed.set(f'{int(time.monotonic()-started)} seconds elapsed — please wait')
        if terminal:
            kind,value=terminal
            (result if kind=='done' else failure).append(value)
            bar.stop();win.destroy();return
        root.after(30,poll)
    # Give Tk a real event-loop turn to paint the window before CPU-heavy work.
    root.after(80,lambda:threading.Thread(target=worker,daemon=True).start())
    root.after(30,poll);root.wait_window(win)
    if failure:raise failure[0]
    return result[0] if result else None
