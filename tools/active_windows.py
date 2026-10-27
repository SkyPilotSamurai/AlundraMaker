"""Every window the program opens comes to the front and takes focus
(user request 2026-10-18): each Toplevel, when it is shown (mapped), is
lifted and given focus. Windows that are only redrawn are not re-raised.
Each time a window opens it is centred on the main Alundra Maker window
(user 2026-10-18); while open it stays where you move it."""
import tkinter as tk

_installed = False


def _activate(window):
    try:
        if not window.winfo_exists() or window.state() == 'withdrawn':
            return
        window.lift()
        window.focus_force()
        try:   # Windows: briefly topmost so it is raised above other programs too
            window.attributes('-topmost', True)
            window.after(150, lambda: window.winfo_exists() and window.attributes('-topmost', False))
        except tk.TclError:
            pass
    except tk.TclError:
        pass


def _center_on_app(window):
    """Centre window on the main program window (kept inside its top/left edge)."""
    try:
        app = window.master
        while app is not None and app.master is not None:
            app = app.master
        if app is None or app is window:
            return
        window.update_idletasks()
        ww, wh = window.winfo_width(), window.winfo_height()
        if ww <= 1 or wh <= 1:   # not shown yet: its set size, else what it needs
            import re
            m = re.match(r'^(\d+)x(\d+)', window.geometry())
            ww, wh = (int(m.group(1)), int(m.group(2))) if m and int(m.group(1)) > 1 else (window.winfo_reqwidth(), window.winfo_reqheight())
        ax, ay, aw, ah = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
        x = ax + (aw - ww) // 2
        y = max(ay, ay + (ah - wh) // 2)
        if ww >= aw:
            x = ax
        window.geometry(f'+{x}+{y}')
    except tk.TclError:
        pass


def install():
    global _installed
    if _installed:
        return
    _installed = True
    original = tk.Toplevel.__init__

    def init(self, *args, **kwargs):
        original(self, *args, **kwargs)
        def on_map(event, window=self):
            if event.widget is window:   # the window itself, not a child widget
                window.after_idle(lambda: _center_on_app(window))   # each time it opens
                window.after_idle(lambda: _activate(window))
        self.bind('<Map>', on_map, add='+')

    tk.Toplevel.__init__ = init
    real_deiconify = tk.Toplevel.deiconify

    def deiconify(self):
        # placed before it shows (a hidden window opened again from a button)
        if self.state() != 'normal':
            _center_on_app(self)
        return real_deiconify(self)

    tk.Toplevel.deiconify = tk.Toplevel.wm_deiconify = deiconify
