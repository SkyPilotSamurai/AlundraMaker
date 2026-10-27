"""Dark menu bar (user 2026-10-18). Windows draws a Tk window's menu bar itself
and ignores Tk colours, so the main window's menu bar is rebuilt as a dark row
of buttons that open the same menus (every menu item and command is unchanged)."""
import tkinter as tk

BG, FG, HOVER = '#181c24', '#e6edf5', '#2d4156'


def convert(root, menu):
    """Replace root's native menu bar `menu` with a dark bar. Returns the bar."""
    bar = tk.Frame(root, bg=BG, bd=0, highlightthickness=0)
    slaves = root.pack_slaves()
    if slaves:
        bar.pack(side='top', fill='x', before=slaves[0])
    else:
        bar.pack(side='top', fill='x')
    state = {'open': None}
    buttons = []

    def post(button, sub):
        state['open'] = button
        button.configure(bg=HOVER)
        x, y = button.winfo_rootx(), button.winfo_rooty() + button.winfo_height()
        try:
            sub.tk_popup(x, y)
        finally:
            sub.grab_release()
            button.configure(bg=BG)
            state['open'] = None

    end = menu.index('end')
    for i in range(0 if end is None else end + 1):
        if menu.type(i) != 'cascade':
            continue
        sub = root.nametowidget(menu.entrycget(i, 'menu'))
        label = menu.entrycget(i, 'label')
        b = tk.Label(bar, text=label, bg=BG, fg=FG, padx=10, pady=4, font=('Segoe UI', 10))
        b.pack(side='left')
        b.bind('<Button-1>', lambda e, b=b, s=sub: post(b, s))
        b.bind('<Enter>', lambda e, b=b: b.configure(bg=HOVER))
        b.bind('<Leave>', lambda e, b=b: b.configure(bg=BG) if state['open'] is not b else None)
        buttons.append(b)
        if True:
            try:
                sub.configure(bg='#202632', fg=FG, activebackground=HOVER, activeforeground=FG,
                              selectcolor=FG, bd=0, relief='flat')
            except tk.TclError:
                pass
    root.configure(menu='')   # the native (light) bar goes away
    return bar
