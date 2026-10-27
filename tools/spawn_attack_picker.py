"""New attacks (Database > Spawned attacks): pick the animation, the frame and
the spawn point by looking at them (user 2026-10-18).

AttackPicker is a fork of the animation window's list: the class's animations
by name on the left; the chosen animation's frames laid out as pictures; click
a frame to choose it; then 'Choose spawn point' and click on the big frame
where the attack should come out (the cross is the enemy's origin). The point
is stored as the offset in pixels: X across, Height up (the attack starts at
that height above the enemy's feet; Y, depth, stays 0).
"""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

THUMB = 72
ZOOM = 3


class AttackPicker:
    def __init__(self, editor, parent, row, spawn, done):
        """spawn: dict with animation, frame, dx, dy, dz; done(values dict) when OK."""
        import animation_preview as A
        from native_spawn_attacks import class_maps
        from stock_donors import source_for
        self.editor, self.row, self.done = editor, row, done
        self.cat = row.get('source', {}).get('catalogue_index')
        if type(self.cat) is not int:
            raise ValueError('This class has no game sprite to pick animations from')
        self.A = A
        self.source = None
        for m in class_maps(row):
            try:
                src = source_for(editor.session, m)
                self.choices = A.available_animations(src, m, self.cat)
                self.source, self.map_id = src, m
                break
            except Exception:
                continue
        if self.source is None:
            raise ValueError('No map has this class\'s animations')
        self.value = dict(animation=int(spawn.get('animation', 0)), frame=int(spawn.get('frame', 0)),
                          dx=int(spawn.get('dx', 0)), dy=int(spawn.get('dy', 0)), dz=int(spawn.get('dz', 0)))
        self.photos = []
        w = self.window = tk.Toplevel(parent)
        w.title(f"{row['name']} — attack animation, frame and spawn point")
        w.geometry('1000x640')
        body = ttk.Panedwindow(w, orient='horizontal'); body.pack(fill='both', expand=True, padx=8, pady=8)
        side = ttk.Frame(body); body.add(side, weight=1)
        ttk.Label(side, text='Animations').pack(anchor='w')
        self.anims = ttk.Treeview(side, show='tree', selectmode='browse', height=20)
        self.anims.pack(fill='both', expand=True)
        from animation_names import auto_names, display_name
        try:
            balance = bytes(editor.native_balance_session().data)
        except Exception:
            balance = None
        try:
            names = auto_names(editor.session, row, self.choices, balance)
        except Exception:
            names = {}
        for r in self.choices:
            label = display_name(editor.database.document, row, names, r['index']) if names is not None else str(r['index'])
            self.anims.insert('', 'end', iid=str(r['index']), text=label)
        self.anims.bind('<<TreeviewSelect>>', lambda e: self.show_frames())
        right = ttk.Frame(body); body.add(right, weight=4)
        ttk.Label(right, text='Frames (click one)').pack(anchor='w')
        self.strip = tk.Canvas(right, height=THUMB + 28, background='#151a22', highlightthickness=0)
        self.strip.pack(fill='x')
        sx = ttk.Scrollbar(right, orient='horizontal', command=self.strip.xview); sx.pack(fill='x')
        self.strip.configure(xscrollcommand=sx.set)
        self.strip.bind('<Button-1>', self.pick_frame)
        bar = ttk.Frame(right); bar.pack(fill='x', pady=(6, 2))
        self.point_button = ttk.Button(bar, text='Choose spawn point', command=self.arm_point); self.point_button.pack(side='left')
        self.note = tk.StringVar(); ttk.Label(bar, textvariable=self.note).pack(side='left', padx=8)
        self.big = tk.Canvas(right, background='#101318', highlightthickness=0)
        self.big.pack(fill='both', expand=True)
        self.big.bind('<Button-1>', self.place_point)
        self.big.bind('<Configure>', lambda e: self.show_big())
        buttons = ttk.Frame(w); buttons.pack(fill='x', padx=8, pady=(0, 8))
        ttk.Button(buttons, text='Cancel', command=w.destroy).pack(side='right')
        ttk.Button(buttons, text='OK', command=self.ok).pack(side='right', padx=6)
        self.armed = False
        a = str(self.value['animation'])
        if self.anims.exists(a):
            self.anims.selection_set(a); self.anims.see(a)
        elif self.choices:
            self.anims.selection_set(str(self.choices[0]['index']))
        self.show_frames(keep_frame=True)

    # -- frames ------------------------------------------------------------
    def clip(self):
        return self.A.load_animation(self.source, self.map_id, self.cat, self.value['animation'], 0)

    def show_frames(self, keep_frame=False):
        sel = self.anims.selection()
        if sel:
            new = int(sel[0])
            if new != self.value['animation']:
                self.value['animation'] = new; self.value['frame'] = 0   # another animation starts at frame 0
        try:
            self.frames = self.clip().frames
        except Exception as exc:
            self.frames = (); self.note.set(str(exc))
        self.value['frame'] = min(self.value['frame'], max(0, len(self.frames) - 1))
        self.draw_strip(); self.show_big()

    def draw_strip(self):
        c = self.strip; c.delete('all'); self.photos = [p for p in self.photos if getattr(p, '_big', False)]
        for i, f in enumerate(self.frames):
            x = i * (THUMB + 8) + 4
            if i == self.value['frame']:
                c.create_rectangle(x - 3, 2, x + THUMB + 3, THUMB + 24, outline='#7fb3ff', width=2)
            if f.image is not None:
                im = f.image.convert('RGBA').copy(); im.thumbnail((THUMB, THUMB))
                ph = ImageTk.PhotoImage(im); self.photos.append(ph)
                c.create_image(x + THUMB // 2, 4 + THUMB // 2, image=ph)
            c.create_text(x + THUMB // 2, THUMB + 14, text=f'Frame {i}', fill='#c8d3e0')
        c.configure(scrollregion=(0, 0, len(self.frames) * (THUMB + 8) + 8, THUMB + 28))

    def pick_frame(self, event):
        i = int(self.strip.canvasx(event.x) // (THUMB + 8))
        if 0 <= i < len(self.frames):
            self.value['frame'] = i; self.draw_strip(); self.show_big()

    # -- big frame and spawn point -------------------------------------------
    def show_big(self):
        c = self.big; c.delete('all')
        if not getattr(self, 'frames', None):
            return
        f = self.frames[self.value['frame']]
        W, H = max(50, c.winfo_width()), max(50, c.winfo_height())
        self.origin = (W // 2, int(H * 0.7))   # the enemy's feet
        ox, oy = self.origin
        if f.image is not None:
            im = f.image.convert('RGBA').resize((f.image.width * ZOOM, f.image.height * ZOOM), Image.NEAREST)
            ph = ImageTk.PhotoImage(im); ph._big = True; self.photos.append(ph)
            c.create_image(ox + f.left * ZOOM, oy + f.top * ZOOM, image=ph, anchor='nw')
        c.create_line(ox - 10, oy, ox + 10, oy, fill='#7a8799'); c.create_line(ox, oy - 10, ox, oy + 10, fill='#7a8799')
        px, py = ox + self.value['dx'] * ZOOM, oy - self.value['dz'] * ZOOM + self.value['dy'] * ZOOM
        c.create_oval(px - 6, py - 6, px + 6, py + 6, outline='#ff5a5a', width=2)
        c.create_line(px - 9, py, px + 9, py, fill='#ff5a5a'); c.create_line(px, py - 9, px, py + 9, fill='#ff5a5a')
        self.note.set(f"Animation {self.value['animation']}, frame {self.value['frame']} · spawn point: "
                      f"{self.value['dx']:+} across, {self.value['dz']:+} up"
                      + (' — click the frame where the attack starts' if self.armed else ''))

    def arm_point(self):
        self.armed = True; self.big.configure(cursor='crosshair'); self.show_big()

    def place_point(self, event):
        if not self.armed:
            return
        ox, oy = self.origin
        dx = round((event.x - ox) / ZOOM); dz = round((oy - event.y) / ZOOM)
        self.value.update(dx=max(-512, min(512, dx)), dy=0, dz=max(-512, min(512, dz)))
        self.armed = False; self.big.configure(cursor=''); self.show_big()

    def ok(self):
        v = dict(self.value)
        v['ticks'] = sum(f.ticks for f in getattr(self, 'frames', ())[:v['frame']])   # game frames from the animation start
        self.done(v); self.window.destroy()
