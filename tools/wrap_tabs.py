"""A tab bar that wraps onto more rows when the tabs do not fit (the tile
picker's map tabs). It answers the ttk.Notebook calls the editor uses:
add(frame, text=), tabs(), select([tab]), forget(tab), tab(tab, 'text') and
the <<NotebookTabChanged>> event. The frames are only keys; nothing is shown
inside the bar."""
import tkinter as tk
from tkinter import ttk


BG = '#1b212b'          # bar background
IDLE = '#a8b6c8'        # unselected text
HOVER = '#262f3d'
SEL_BG = '#2d4156'
ACCENT = '#5b9bd5'


class _Tab(tk.Frame):
    """A flat tab: label plus a 2px accent strip that shows when selected."""
    def __init__(self, parent, text, command, sub):
        super().__init__(parent, background=BG, cursor='hand2')
        self._text = text; self._selected = False; self._hover = False
        pad = (10, 4) if sub else (14, 6)
        self._label = tk.Label(self, text=text, background=BG, foreground=IDLE, padx=pad[0], pady=pad[1],
                               font=('Segoe UI', 9 if sub else 10, 'bold' if not sub else 'normal'))
        self._label.pack(side='top', fill='x')
        self._bar = tk.Frame(self, height=2, background=BG); self._bar.pack(side='bottom', fill='x')
        for w in (self, self._label):
            w.bind('<Button-1>', lambda _e: command())
            w.bind('<Enter>', lambda _e: self._set_hover(True))
            w.bind('<Leave>', lambda _e: self._set_hover(False))

    def cget(self, key):
        return self._text if key == 'text' else super().cget(key)

    def _set_hover(self, on):
        self._hover = on; self._paint()

    def set_selected(self, on):
        self._selected = on; self._paint()

    def _paint(self):
        bg = SEL_BG if self._selected else (HOVER if self._hover else BG)
        self.configure(background=bg)
        self._label.configure(background=bg, foreground='white' if self._selected or self._hover else IDLE)
        self._bar.configure(background=ACCENT if self._selected else bg)


class WrapTabs(tk.Frame):
    def __init__(self, parent, sub=False, **options):
        options.pop('height', None)
        super().__init__(parent, background=BG, **options)
        self._sub = sub
        self._tabs = []          # [(name, frame, button)]
        self._selected = None
        self._body = tk.Frame(self, background=BG); self._body.pack(fill='x')
        self._line = tk.Frame(self, height=1, background='#394354')
        self.bind('<Configure>', lambda _e: self._layout())

    # -- Notebook-like API ---------------------------------------------------
    def add(self, frame, text=''):
        name = str(frame)
        button = _Tab(self._body, text, lambda n=name: self.select(n), self._sub)
        self._tabs.append((name, frame, button))
        if self._selected is None:
            self._select(name, notify=True)
        self.after_idle(self._layout)

    def tabs(self):
        return [name for name, _, _ in self._tabs]

    def forget(self, tab):
        tab = str(tab)
        for item in list(self._tabs):
            if item[0] == tab:
                item[2].destroy(); self._tabs.remove(item)
        if self._selected == tab:
            self._selected = None
            if self._tabs:
                self._select(self._tabs[0][0], notify=True)
        self.after_idle(self._layout)

    def select(self, tab=None):
        if tab is None:
            return self._selected or ''
        self._select(str(tab), notify=True)

    def tab(self, tab, option=None):
        for name, _, button in self._tabs:
            if name == str(tab):
                return button.cget('text') if option == 'text' else {'text': button.cget('text')}
        raise tk.TclError(f'no tab {tab}')

    # -- inside --------------------------------------------------------------
    def _select(self, name, notify):
        if name not in self.tabs():
            return
        changed = name != self._selected
        self._selected = name
        for n, _, button in self._tabs:
            button.set_selected(n == name)
        if changed and notify:
            self.event_generate('<<NotebookTabChanged>>', when='tail')   # queued, like ttk.Notebook

    def _layout(self):
        """Pack the tab buttons into as many rows as the width needs. Rows are
        frames inside the bar (pack -in), so the bar always asks for the right
        height; earlier versions used place(), which left the bar 1 pixel tall
        on some systems."""
        width = self.winfo_width()
        if width <= 1:
            width = max(self.master.winfo_width(), 300)
        key = (width, tuple(name for name, _, _ in self._tabs))
        if key == getattr(self, '_layout_key', None):
            return
        self._layout_key = key
        if self._tabs:
            self._line.pack(fill='x')
        else:
            self._line.pack_forget()   # no tabs: the bar takes no room
            self.configure(height=1)
        for _, _, button in self._tabs:
            button.pack_forget()
        for row in getattr(self, '_rows', []):
            row.destroy()
        self._rows = []; x = width
        for _, _, button in self._tabs:
            w = button.winfo_reqwidth()
            if x + w > width or not self._rows:
                row = tk.Frame(self._body, background=BG); row.pack(fill='x', anchor='w'); self._rows.append(row); x = 0
            button.pack(in_=self._rows[-1], side='left')
            button.lift(self._rows[-1])
            x += w
