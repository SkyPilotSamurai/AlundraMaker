"""Export / Import Sprites (user 2026-10-18): pick the class with the same
picker as the event graphic selector, then a window lists that class's
animations. Export: tick the animations and choose a folder. Import: each
animation has its own file field (Browse...), filled automatically from a
folder of '<name> animation NN.png' sheets; only filled fields are imported."""
import re
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog


def open_sprite_transfer(editor, mode):
    from database_picker import DatabasePicker
    editor.need()
    parent = editor.db_window if getattr(editor, 'db_window', None) and editor.db_window.winfo_viewable() else editor.root
    title = 'Export sprites: choose a class' if mode == 'export' else 'Import sprites: choose the class to import into'

    def chosen(class_id):
        if class_id is not None:
            editor.guard(lambda: SpriteTransferWindow(editor, parent, class_id, mode))
    DatabasePicker(editor, parent, chosen, title=title, confirm='Choose class', allow_empty=False)


class SpriteTransferWindow:
    def __init__(self, editor, parent, class_id, mode):
        from animation_preview import available_animations
        from animation_names import auto_names, display_name
        self.editor = editor; self.mode = mode
        row, maps = editor.db_sprite_target(class_id)
        self.row = row; self.index = row['source']['catalogue_index']
        self.map_id = None; choices = ()
        for map_id in maps[:8]:
            try:
                choices = available_animations(editor.session, map_id, self.index)
            except Exception:
                continue
            if choices:
                self.map_id = map_id; break
        if not choices:
            raise ValueError(f"{row['name']} has no animations that can be read")
        try:
            balance = bytes(editor.native_balance_session().data)
        except Exception:
            balance = None
        try:
            names = auto_names(editor.session, row, choices, balance)
        except Exception:
            names = {}
        self.safe = re.sub(r'[^A-Za-z0-9 ()_-]', '', row['name'])

        w = self.window = tk.Toplevel(parent)
        w.title(('Export' if mode == 'export' else 'Import') + f" sprites: {row['name']}")
        w.transient(parent)
        top = ttk.Frame(w, padding=10); top.pack(fill='x')
        if mode == 'import':
            ttk.Button(top, text='Fill from folder...', command=self.fill_from_folder).pack(anchor='w', pady=(6, 0))

        main = ttk.Frame(w, padding=(10, 0)); main.pack(fill='both', expand=True)
        outer = ttk.Frame(main); outer.pack(side='left', fill='both', expand=True)
        # Preview of the selected animation: the game's sheet, and for Import the chosen sheet beside it
        side = ttk.Frame(main, padding=(10, 0)); side.pack(side='right', fill='both', expand=True)
        self.preview_title = tk.StringVar(value='')
        ttk.Label(side, textvariable=self.preview_title).pack(anchor='w')
        pics = ttk.Frame(side); pics.pack(fill='both', expand=True)
        self.current_label = ttk.Label(pics, text='Game' if mode == 'import' else '')
        self.current_label.grid(row=0, column=0, sticky='w')
        self.current_pic = tk.Label(pics, bg='#202020'); self.current_pic.grid(row=1, column=0, sticky='nw', padx=(0, 8))
        if mode == 'import':
            ttk.Label(pics, text='Chosen sheet').grid(row=0, column=1, sticky='w')
            self.new_pic = tk.Label(pics, bg='#202020'); self.new_pic.grid(row=1, column=1, sticky='nw')
        self.photos = []; self.sheet_cache = {}; self.selected = None
        canvas = tk.Canvas(outer, highlightthickness=0, height=min(480, 30 * len(choices) + 10))
        bar = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        body = ttk.Frame(canvas)
        body.bind('<Configure>', lambda _: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=body, anchor='nw'); canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side='left', fill='both', expand=True); bar.pack(side='right', fill='y')
        canvas.bind_all('<MouseWheel>', lambda e: canvas.yview_scroll(-1 * (e.delta // 120), 'units'))

        self.fields = {}
        for n, r in enumerate(choices):
            a = r['index']
            label = display_name(editor.database.document, row, names, a)
            if mode == 'export':
                var = tk.BooleanVar(value=True)
                cb = ttk.Checkbutton(body, text=label, variable=var); cb.grid(row=n, column=0, sticky='w', pady=2)
                ttk.Button(body, text='Preview', command=lambda a=a, l=label: editor.guard(lambda: self.preview(a, l))).grid(row=n, column=1, padx=6)
            else:
                var = tk.StringVar()
                lab = ttk.Label(body, text=label, width=28, cursor='hand2'); lab.grid(row=n, column=0, sticky='w', pady=2)
                lab.bind('<Button-1>', lambda _, a=a, l=label: editor.guard(lambda: self.preview(a, l)))
                var.trace_add('write', lambda *_, a=a, l=label: self.selected == a and self.preview(a, l))
                ttk.Entry(body, textvariable=var, width=60).grid(row=n, column=1, sticky='we', padx=6)
                ttk.Button(body, text='Browse...', command=lambda v=var, a=a: self.browse(v, a)).grid(row=n, column=2)
                ttk.Button(body, text='Preview', command=lambda a=a, l=label: editor.guard(lambda: self.preview(a, l))).grid(row=n, column=4, padx=(4, 0))
                ttk.Button(body, text='Clear', command=lambda v=var: v.set('')).grid(row=n, column=3, padx=(4, 0))
            self.fields[a] = var

        bottom = ttk.Frame(w, padding=10); bottom.pack(fill='x')
        if mode == 'export':
            ttk.Button(bottom, text='All', command=lambda: [v.set(True) for v in self.fields.values()]).pack(side='left')
            ttk.Button(bottom, text='None', command=lambda: [v.set(False) for v in self.fields.values()]).pack(side='left', padx=6)
            ttk.Button(bottom, text='Export...', command=lambda: editor.guard(self.export)).pack(side='right')
        else:
            ttk.Button(bottom, text='Import', command=lambda: editor.guard(self.do_import)).pack(side='right')
        ttk.Button(bottom, text='Cancel', command=w.destroy).pack(side='right', padx=8)
        w.update_idletasks()
        try:
            px, py, pw, ph = parent.winfo_rootx(), parent.winfo_rooty(), parent.winfo_width(), parent.winfo_height()
            ww, wh = max(w.winfo_reqwidth(), 1100), max(w.winfo_reqheight(), 560)
            w.geometry(f'{ww}x{wh}+{px + max(0, (pw - ww) // 2)}+{py + max(0, (ph - wh) // 2)}')
        except tk.TclError:
            pass
        w.lift(); w.focus_force()
        first = choices[0]['index']
        editor.guard(lambda: self.preview(first, display_name(editor.database.document, row, names, first)))

    # ---- preview
    def _photo(self, image, box=(520, 460)):
        from PIL import ImageTk
        image = image.convert('RGBA')
        scale = max(1, min(4, box[0] // max(1, image.width), box[1] // max(1, image.height)))
        if scale > 1:
            image = image.resize((image.width * scale, image.height * scale), 0)
        elif image.width > box[0] or image.height > box[1]:
            image = image.copy(); image.thumbnail(box)
        photo = ImageTk.PhotoImage(image, master=self.window); self.photos.append(photo)
        return photo

    def preview(self, animation, label):
        from sprite_sheet_import import render
        self.selected = animation; self.photos = self.photos[-4:]
        self.preview_title.set(f'Animation {label}')
        if animation not in self.sheet_cache:
            self.sheet_cache[animation] = render(self.editor.session, self.editor.database.document, self.map_id, self.index, animation)[0]
        self.current_pic.configure(image=self._photo(self.sheet_cache[animation], (520 if self.mode == 'export' else 360, 460)))
        if self.mode == 'import':
            path = self.fields[animation].get().strip()
            if path and Path(path).is_file():
                from PIL import Image
                try:
                    self.new_pic.configure(image=self._photo(Image.open(path), (360, 460)), text='')
                except Exception as exc:
                    self.new_pic.configure(image='', text=f'Cannot open: {exc}', fg='white')
            else:
                self.new_pic.configure(image='', text='No sheet chosen', fg='white')

    # ---- import
    def browse(self, var, animation):
        path = filedialog.askopenfilename(parent=self.window, title=f'Sheet for animation {animation}',
                                          filetypes=[('PNG sheet', '*.png')], initialdir=str(Path(var.get()).parent) if var.get() else None)
        if path:
            var.set(path)

    def fill_from_folder(self):
        folder = filedialog.askdirectory(parent=self.window, title='Folder with "… animation NN.png" sheets')
        if not folder:
            return
        found = 0
        for path in sorted(Path(folder).glob('*.png')):
            m = re.search(r'animation (\d+)\.png$', path.name)
            if m and int(m.group(1)) in self.fields:
                self.fields[int(m.group(1))].set(str(path)); found += 1
        self.editor.status.set(f'Filled {found} animation field(s) from {folder}.')

    def do_import(self):
        from sprite_sheet_import import import_sheet
        chosen = [(a, v.get().strip()) for a, v in self.fields.items() if v.get().strip()]
        if not chosen:
            raise ValueError('Choose at least one sheet to import')
        changed = 0
        for a, path in chosen:
            if not Path(path).is_file():
                raise ValueError(f'Animation {a}: file not found: {path}')
            changed += import_sheet(self.editor.session, self.editor.database.document, self.map_id, self.index, a, path)['changed']
        if changed:
            self.editor.dirty = True
        self.editor.status.set(f"Imported {len(chosen)} sheet(s) into {self.row['name']}: {changed} changed frame picture(s); drawn into the game when you build.")
        self.window.destroy()

    # ---- export
    def export(self):
        from sprite_sheet_import import export_sheet
        chosen = [a for a, v in self.fields.items() if v.get()]
        if not chosen:
            raise ValueError('Tick at least one animation to export')
        folder = filedialog.askdirectory(parent=self.window, title=f"Export {self.row['name']} sprites to folder")
        if not folder:
            return
        n = 0; errors = []
        for a in chosen:
            try:
                export_sheet(self.editor.session, self.editor.database.document, self.map_id, self.index, a,
                             str(Path(folder) / f'{self.safe} animation {a:02d}.png')); n += 1
            except Exception as exc:
                errors.append(f'{a}: {exc}')
        if not n:
            raise ValueError('Nothing exported: ' + '; '.join(errors[:3]))
        self.editor.status.set(f"Exported {n} sheet(s) of {self.row['name']} to {folder}" + (f' ({len(errors)} skipped)' if errors else '') + '.')
        self.window.destroy()
        try:
            import os
            os.startfile(folder)
        except Exception:
            pass
