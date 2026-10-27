"""Dark Windows title bars for the editor's windows (2026-10-17, user).

Windows draws the title bar and frame, not Tk; DWM attribute 20 (19 before
Windows 10 20H1) asks for the dark version. Applied to the main window and every
Tk Toplevel the editor opens. Native file/message dialogs follow the Windows
theme setting. Does nothing on other systems or if the call is refused."""
import sys


def apply(window):
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        window.update_idletasks()
        try:
            hwnd = int(window.wm_frame(), 16)   # the frame Windows draws (exists once mapped)
        except Exception:
            hwnd = 0
        if not hwnd:
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
        on = ctypes.c_int(1)
        dwm = ctypes.windll.dwmapi
        if dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), ctypes.sizeof(on)) != 0:
            dwm.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(on), ctypes.sizeof(on))
        # Windows 11: a fixed caption colour, so the bar stays dark when the window is not
        # focused too (dark mode alone lets an inactive bar go light on some systems).
        # COLORREF is 0x00BBGGRR; refused quietly on Windows 10.
        for attr, colour in ((35, 0x00221A15), (36, 0x00F1E2D7), (34, 0x00544339)):   # caption, text, border
            value = ctypes.c_uint(colour)
            dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
        # Redraw the frame now (an already visible window keeps the old colours otherwise).
        ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)
    except Exception:
        pass


def dark_app_mode():
    """Ask Windows for dark popup menus and controls for this program
    (uxtheme SetPreferredAppMode(ForceDark) + FlushMenuThemes; Windows 10 1903+)."""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        ux = ctypes.WinDLL('uxtheme')
        ux[135](2)   # SetPreferredAppMode: 2 = force dark
        ux[136]()    # FlushMenuThemes
    except Exception:
        pass


def _keep(win):
    """Same caption colour as the main window on every window, every time it is
    shown or gains/loses focus (Windows can repaint an inactive bar its own shade)."""
    def again(event, win=win):
        if event.widget is win:
            apply(win)
            win.after(120, lambda: win.winfo_exists() and apply(win))
    for sequence in ('<Map>', '<Activate>', '<Deactivate>'):
        win.bind(sequence, again, add='+')


def install(root):
    """Dark title bar on root now and on every Toplevel created later."""
    import tkinter as tk
    dark_app_mode()
    apply(root)
    _keep(root)
    if getattr(tk.Toplevel, '_dark_titlebar', False):
        return
    original = tk.Toplevel.__init__

    def init(self, *args, **kwargs):
        original(self, *args, **kwargs)
        try:
            self.after_idle(lambda: apply(self))
            # A window built hidden (withdrawn, then shown) has no frame yet at idle
            # time, so the dark frame is also set the first time it is shown.
            _keep(self)
        except Exception:
            pass
    tk.Toplevel.__init__ = init
    tk.Toplevel._dark_titlebar = True
