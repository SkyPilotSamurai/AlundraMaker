"""Pick a map and a tile on it by clicking the rendered map.

Used by Transfer Player and New Warp. The landing height (Z) follows the
clicked tile's floor height, as the warp destination picker does.
"""
import tkinter as tk
from tkinter import ttk
from map_names import map_label


def map_choices(data=None):
    from map_slots import map_count
    return {f'{n:03d}  {map_label(n)}': n for n in range(map_count(data) if data is not None else 483)}


class MapTileDialog:
    def __init__(self, editor, parent, on_pick, map_id=None, x=0, y=0, z=None,
                 title='Choose Map And Tile', fixed_map=False, confirm='Use This Tile'):
        if editor.session is None:
            raise ValueError('Open game data first')
        self.editor = editor; self.on_pick = on_pick
        self.map_id = int(editor.current_map if map_id is None else map_id)
        self.point = [int(x), int(y), z]
        self.window = win = tk.Toplevel(parent); win.title(title); win.transient(parent)
        win.geometry('980x720')
        top = ttk.Frame(win, padding=8); top.pack(fill='x')
        ttk.Label(top, text='Map').pack(side='left')
        self.choices = map_choices(editor.session.data)
        self.map_text = tk.StringVar(value=next(k for k, v in self.choices.items() if v == self.map_id))
        self.combo = ttk.Combobox(top, textvariable=self.map_text, values=list(self.choices), width=52)
        self.combo.pack(side='left', padx=6)
        if fixed_map:
            self.combo.state(['disabled'])
        self.combo.bind('<<ComboboxSelected>>', lambda _: editor.guard(self.change_map))
        self.combo.bind('<KeyRelease>', self.filter_maps)
        self.combo.bind('<Return>', lambda _: editor.guard(self.change_map))
        self.label = tk.StringVar(); ttk.Label(top, textvariable=self.label).pack(side='right')
        body = ttk.Frame(win); body.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(body, background='#202630', highlightthickness=0)
        sx = ttk.Scrollbar(body, orient='horizontal', command=self.canvas.xview)
        sy = ttk.Scrollbar(body, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=sx.set, yscrollcommand=sy.set)
        body.rowconfigure(0, weight=1); body.columnconfigure(0, weight=1)
        self.canvas.grid(row=0, column=0, sticky='nsew'); sy.grid(row=0, column=1, sticky='ns'); sx.grid(row=1, column=0, sticky='ew')
        self.canvas.bind('<Button-1>', self.pick)
        self.canvas.bind('<Double-Button-1>', lambda e: (self.pick(e), editor.guard(self.confirm)))
        footer = ttk.Frame(win, padding=8); footer.pack(fill='x')
        ttk.Label(footer, text='Click a tile. Purple boxes are existing warps.').pack(side='left')
        ttk.Button(footer, text=confirm, command=lambda: editor.guard(self.confirm)).pack(side='right')
        ttk.Button(footer, text='Cancel', command=win.destroy).pack(side='right', padx=6)
        win.bind('<Escape>', lambda _: win.destroy())
        self.draw(first=True)

    def filter_maps(self, event):
        if event.keysym in ('Return', 'Up', 'Down', 'Escape'):
            return
        text = self.map_text.get().strip().casefold()
        values = [k for k in self.choices if text in k.casefold()] if text else list(self.choices)
        self.combo.configure(values=values or list(self.choices))

    def change_map(self):
        text = self.map_text.get().strip()
        if text not in self.choices:
            matches = [k for k in self.choices if text.casefold() in k.casefold()]
            if not matches:
                raise ValueError('Choose a map from the list')
            text = matches[0]; self.map_text.set(text)
        new = self.choices[text]
        if new != self.map_id:
            self.map_id = new; self.point = [0, 0, None]; self.draw(first=True)

    def draw(self, first=False):
        from area_map import MapRenderer, grid
        from warp_editor import warps
        from PIL import ImageTk
        session = self.editor.session
        self.width, self.height, self.cells = grid(session, self.map_id)
        self.renderer = MapRenderer(session, self.map_id)
        image, _, self.margin = self.renderer.render(elevation=True)
        self.photo = ImageTk.PhotoImage(image, master=self.canvas)
        self.canvas.delete('all'); self.canvas.create_image(0, 0, image=self.photo, anchor='nw')
        self.canvas.configure(scrollregion=(0, 0, image.width, image.height))
        for index, _, p in warps(session, self.map_id):
            for ty in range(p.y1, min(p.y2 + 1, self.height)):
                for tx in range(p.x1, min(p.x2 + 1, self.width)):
                    px, py = self.tile_position(tx, ty)
                    self.canvas.create_rectangle(px, py, px + 24, py + 16, outline='#bf91ff')
        x, y = self.point[:2]
        if not (0 <= x < self.width and 0 <= y < self.height):
            self.point = [0, 0, None]
        if self.point[2] is None:
            self.point[2] = self.cells[self.point[1] * self.width + self.point[0]]['values'][3]
        self.mark()
        if first:
            px, py = self.tile_position(*self.point[:2])
            self.canvas.xview_moveto(max(0, (px - 400) / max(1, image.width)))
            self.canvas.yview_moveto(max(0, (py - 260) / max(1, image.height)))

    def tile_position(self, x, y):
        height = self.cells[y * self.width + x]['values'][3] if 0 <= x < self.width and 0 <= y < self.height else 0
        return x * 24, y * 16 + self.margin - height * 16

    def mark(self):
        x, y, z = self.point
        self.label.set(f'Tile {x}, {y} · height {z}')
        self.canvas.delete('chosen')
        px, py = self.tile_position(x, y)
        self.canvas.create_rectangle(px, py, px + 24, py + 16, outline='#62cbff', width=3, tags='chosen')
        self.canvas.create_text(px + 12, py + 8, text='X', fill='white', tags='chosen')

    def pick(self, event):
        hit = self.renderer.surface_at(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        if hit is None:
            return
        x, y = hit[2:4]
        if 0 <= x < self.width and 0 <= y < self.height:
            self.point = [x, y, self.cells[y * self.width + x]['values'][3]]; self.mark()

    def confirm(self):
        x, y, z = self.point
        self.window.destroy()
        self.on_pick(self.map_id, x, y, z)
