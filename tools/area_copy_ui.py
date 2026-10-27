"""Map > Copy area from another map: drag a rectangle on any map, paste it at
the tile selected on the current map (floor, walls, heights, stairs and
collision come along; tile pictures are imported automatically)."""
import tkinter as tk
from tkinter import ttk
from map_tile_picker import MapTileDialog


class CopyAreaDialog(MapTileDialog):
    def __init__(self, editor, parent):
        self.start = None; self.rect = None
        super().__init__(editor, parent, lambda *a: None, map_id=editor.current_map,
                         title='Copy Area From A Map', confirm='Paste At Selected Tile')
        bar = ttk.Frame(self.window, padding=(8, 0)); bar.pack(fill='x', before=self.canvas.master)
        ttk.Label(bar, text='Drag over the area to copy, select the target tile on your map, then Paste.').pack(side='left')
        ttk.Label(bar, text='Height change').pack(side='left', padx=(16, 4))
        self.height_delta = tk.StringVar(value='0')
        ttk.Spinbox(bar, from_=-40, to=40, textvariable=self.height_delta, width=5).pack(side='left')
        self.keep_empty = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text='Keep my tiles where the area is empty', variable=self.keep_empty).pack(side='left', padx=12)
        self.canvas.bind('<Button-1>', self.press)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<Double-Button-1>', lambda e: None)

    def tile_at(self, event):
        hit = self.renderer.surface_at(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        if hit is None:
            return None
        x, y = hit[2:4]
        return (x, y) if 0 <= x < self.width and 0 <= y < self.height else None

    def press(self, event):
        self.start = self.tile_at(event)
        if self.start: self.set_rect(self.start, self.start)

    def drag(self, event):
        tile = self.tile_at(event)
        if self.start and tile: self.set_rect(self.start, tile)

    def set_rect(self, a, b):
        x0, x1 = sorted((a[0], b[0])); y0, y1 = sorted((a[1], b[1]))
        self.rect = (x0, y0, x1 - x0 + 1, y1 - y0 + 1)
        self.canvas.delete('area')
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                px, py = self.tile_position(x, y)
                self.canvas.create_rectangle(px, py, px + 24, py + 16, outline='#ffd84a', tags='area')
        self.label.set(f'Area {self.rect[2]}×{self.rect[3]} from tile {x0}, {y0}')

    def mark(self):
        pass   # no single-tile marker here; the dragged area is shown instead

    def confirm(self):
        """Problems are shown in this window's caption, never as a pop-up."""
        try:
            self.paste()
        except Exception as exc:
            self.label.set('Not done: ' + (str(exc) or exc.__class__.__name__))

    def paste(self):
        editor = self.editor; area = editor.area
        if self.rect is None:
            raise ValueError('Drag over the area you want to copy first')
        if area.selected is None:
            raise ValueError('Select the tile on your map where the area starts (its top-left)')
        try:
            delta = int(self.height_delta.get())
        except ValueError:
            raise ValueError('Height change must be a whole number')
        area.commit_stacks(); area.flush_textures()   # waiting paint first, or it would overwrite the paste
        from map_area_copy import copy_area
        count = copy_area(editor.session, editor.database, self.map_id, self.rect, editor.current_map,
                          area.selected, height_delta=delta, skip_empty=self.keep_empty.get())
        editor.dirty = True
        from area_map import MapRenderer
        area.renderer = MapRenderer(editor.session, editor.current_map)
        area.refresh(reload_textures=False)
        editor.status.set(f'Copied {count} tiles from map {self.map_id}. Undo removes them.')
        self.label.set(f'Pasted {count} tiles. Drag another area or close.')
