import math,time,struct
from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk,messagebox
from PIL import ImageTk
from zoom_canvas import ZoomCanvas
from area_map import grid,edit_cell,edit_wall,edit_height,tile_at_canvas,MapRenderer,entity_preview_anchor,entity_tile_selection_anchor,tile_stroke_steps,first_visible_row,map_y_to_view,view_y_to_map
from map_inspector import inspect_map

def _safe_pack():
 """A widget packed before/after one that is hidden raised 'isn't packed' and stopped
 whatever was running (opening a map). Now it is packed without that position
 instead (user 2026-10-25: errors must never stop the editor)."""
 if getattr(tk.Pack,'_safe',False):return
 original=tk.Pack.pack_configure
 def pack_configure(self,cnf={},**kw):
  try:return original(self,cnf,**kw)
  except tk.TclError as exc:
   if "isn't packed" not in str(exc):raise
   kw.pop('before',None);kw.pop('after',None)
   cnf={k:v for k,v in dict(cnf or {}).items() if k not in ('before','after')}
   return original(self,cnf,**kw)
 tk.Pack.pack_configure=pack_configure;tk.Pack.pack=pack_configure;tk.Widget.pack=pack_configure;tk.Widget.pack_configure=pack_configure
 tk.Pack._safe=True
_safe_pack()
from entity_preview import EntityPreview,cached_preview
from event_records_edit import move_record
from warp_editor import warps,move_warp,WarpWindow,projected_warp_boxes,warp_at_visual_point
from map_names import map_label
from event_selection import covers_map
from event_deletion import record_deleted
DEFAULT_HEIGHT_EDIT=False
GAME_TREES={'3:10:47','12:32:30','8:41:32','2:44:48','8:37:37'}
# Tiles > Floors / Walls / Slopes / Water / Lava: their own row of tabs (user request 2026-10-15)
_PLACES=(('map','This Map'),('indoor','Indoor'),('outdoor','Outdoor'))
_LIQUID_PLACES=(('map','This Map'),('all','All'))   # Sand / Water / Ice / Lava (user 2026-10-18)
_MAP_LAYERS=[('all','All Layers'),('floor','Layer 1'),('wall','Layer 2')]   # Map tab: each map's floors / pieces on top (user 2026-10-21)
TILE_PARTS={'maplayers':_MAP_LAYERS,'floors':_PLACES,'walls':_PLACES,'stairs':_PLACES,
 'water':_LIQUID_PLACES,'ice':_LIQUID_PLACES,'lava':_LIQUID_PLACES,'sand':_LIQUID_PLACES,'spikes':_LIQUID_PLACES}   # like Floors (user 2026-10-18)

class AreaPanel:
 def __init__(self,editor,tabs=None):
  self.editor=editor;self.frame=ttk.Frame(tabs if tabs is not None else editor.root)
  if tabs is None:self.frame.pack(fill="both",expand=True,padx=8,pady=0)
  else:tabs.insert(0,self.frame,text="Map editor");tabs.select(self.frame)
  self.mode=tk.StringVar(value="Select tile");self.height=tk.BooleanVar(value=True);self.show_grid=tk.BooleanVar(value=False);self.show_event_numbers=tk.BooleanVar(value=False);self.brush=None;self.selected=None
  self.map_crop_top=0
  self.show_default_objects=tk.BooleanVar(value=True);self.show_default_events=tk.BooleanVar(value=True);self.show_warps=tk.BooleanVar(value=True)
  bar=ttk.Frame(self.frame);bar.pack(fill="x")
  self.mode_buttons=[]
  # One radio group: Select / Paint / Events / Warps and the Edit heights, No Walk Area and
  # Mask layer tools (user 2026-10-21); the tools keep their own on/off state underneath
  self.tool=tk.StringVar(value="Select tile");self._tool_sync=False
  def radio(label,value):
   button=ttk.Radiobutton(bar,text=label,variable=self.tool,value=value);button.pack(side="left",padx=(0,4));self.mode_buttons.append(button)
  for label,value in [("Select","Select tile"),("Paint","Paint tiles"),("Events","Events"),("Warps","Warps")]:radio(label,value)
  self.tool.trace_add("write",lambda *_:self._tool_sync or editor.guard(lambda:self.select_tool(self.tool.get())))
  self.drag_point=None;self.stroke_cells=set();self.record_drag=None;self.paint_job=None;self.selected_record=None;self.drag_delta=(0,0)
  self.event_clipboard=None
  self.event_clipboard=None
  self.height_preview_button=None
  self.height_edit=tk.BooleanVar(value=DEFAULT_HEIGHT_EDIT)
  radio("Edit heights","heights")
  self.event_action_buttons=[]
  # (Delete/Copy/Paste event buttons removed: right-click an event, or press Delete)
  self.mark_walls=tk.BooleanVar(value=False)
  radio("No Walk Area","no_walk")
  self.walk_blocks=tk.StringVar(value="Blocks everyone")   # x blocks everyone; hold Shift for player-only x
  self.mask_layer=tk.BooleanVar(value=False)   # Mask layer: click a tile to draw it in front of the player (★)
  radio("Mask layer","mask")
  self.grid_check=ttk.Checkbutton(bar,text="Grid",variable=self.show_grid,command=lambda:editor.guard(self.refresh));self.grid_check.pack(side="left",padx=(5,0))
  self.map_zoom=tk.StringVar(value="100%")
  ttk.Label(bar,text="Map zoom").pack(side="left",padx=(8,2))
  zoom=ttk.Combobox(bar,textvariable=self.map_zoom,values=[f"{p}%" for p in range(25,501,25)],width=6,state="readonly");zoom.pack(side="left");zoom.bind("<<ComboboxSelected>>",lambda _:editor.guard(self.change_map_zoom))
  self.whole_event_button=ttk.Menubutton(bar,text="Whole-map events (0)",state="disabled")
  self.whole_event_menu=tk.Menu(self.whole_event_button,tearoff=False)
  self.whole_event_button.configure(menu=self.whole_event_menu);self.whole_event_button.pack(side="left",padx=(6,0))
  self.start_point_armed=False;self.ignore_start_double_until=0
  self.start_point_button=ttk.Button(bar,text="Set start point",command=lambda:editor.guard(self.arm_start_point));self.start_point_button.pack(side="left",padx=(6,0))
  ttk.Button(bar,text="Jump to start point",command=lambda:editor.guard(self.jump_to_start_point)).pack(side="left",padx=(4,0))
  self.group_brush=None;self.group_brush_heights=None;self.bush_brush=None;self.face_brush=False;self.brush_height=None;self.library_start=None
  self.caption=tk.StringVar(value="Load a map to edit the assembled area.")
  ttk.Label(self.frame,textvariable=self.caption,padding=(8,4)).pack(side="bottom",fill="x")
  body=ttk.Panedwindow(self.frame,orient="horizontal");body.pack(fill="both",expand=True)
  self.workspace_panes=body
  self.picker_width_fraction=0.26;self.picker_sash_dragging=False;self.pane_layout_job=None
  body.bind('<Configure>',self.queue_pane_layout)
  body.bind('<ButtonPress-1>',self.begin_pane_resize,add='+')
  body.bind('<ButtonRelease-1>',self.end_pane_resize,add='+')
  side=ttk.Frame(body,padding=8,width=500);body.add(side,weight=1)
  viewport=ttk.Frame(body);body.add(viewport,weight=3)
  self.canvas=ZoomCanvas(viewport,bg="#20242a",highlightthickness=0)
  xs=ttk.Scrollbar(viewport,orient="horizontal",command=self.canvas.xview);ys=ttk.Scrollbar(viewport,command=self.canvas.yview)
  self.canvas.configure(xscrollcommand=xs.set,yscrollcommand=ys.set)
  viewport.rowconfigure(0,weight=1);viewport.columnconfigure(0,weight=1)
  self.canvas.grid(row=0,column=0,sticky="nsew");ys.grid(row=0,column=1,sticky="ns");xs.grid(row=1,column=0,sticky="ew")
  self.canvas.bind("<Button-1>",lambda e:editor.guard(lambda:self.press(e)))
  self.canvas.bind("<B1-Motion>",lambda e:self.drag(e))
  self.canvas.bind('<Motion>',self.preview_group)
  self.canvas.bind('<Motion>',lambda e:self.hover_height(e),add='+')
  self.canvas.bind('<Motion>',lambda e:self.hover_layers(e),add='+')
  self.canvas.bind('<Motion>',lambda e:self.hover_tile_info(e),add='+')
  self.canvas.bind('<Leave>',lambda _:self.clear_group_preview())
  self.canvas.bind("<ButtonRelease-1>",lambda e:editor.guard(lambda:self.release(e)))
  self.canvas.bind("<Double-Button-1>",lambda e:editor.guard(lambda:self.double_click(e)))
  self.canvas.bind("<Button-3>",lambda e:editor.guard(lambda:self.right_click(e)))
  # Shift + drag in Paint mode: fill a rectangle with the brush (one undo step).
  self.canvas.bind("<Shift-Button-1>",lambda e:editor.guard(lambda:self.fill_press(e)))
  self.canvas.bind("<Shift-B1-Motion>",lambda e:self.fill_drag(e))
  self.canvas.bind("<Shift-ButtonRelease-1>",lambda e:editor.guard(lambda:self.fill_release(e)))
  self.fill_start=None;self.pending_tiles={};self.pending_heights={};self.bush_brush=None;self.face_brush=False;self.bush_stroke=None
  self.canvas.bind("<Delete>",lambda _:editor.guard(self.delete_selected_event))
  # Copy / Cut / Paste / Delete for events, on the map and in the event list (user 2026-10-18)
  for widget in (self.canvas,):
   widget.bind("<Control-c>",lambda _:editor.guard(self.copy_selected_event))
   widget.bind("<Control-x>",lambda _:editor.guard(self.cut_selected_event))
   widget.bind("<Control-v>",lambda _:editor.guard(self.paste_event_at_selected_tile))
  self.tile_tools_window=tk.Toplevel(editor.root);self.tile_tools_window.title("Tile Properties — Alundra")
  self.tile_tools_window.withdraw();self.tile_tools_window.transient(editor.root)
  self.tile_tools_window.protocol('WM_DELETE_WINDOW',self.tile_tools_window.withdraw)
  tools=ttk.Frame(self.tile_tools_window,padding=12);tools.pack(fill='both',expand=True)
  self.vars=[]
  for label in ["Walkability (raw)","Ground property","Slope (raw)","Height","Tile + palette code"]:
   ttk.Label(tools,text=label).pack(anchor="w");v=tk.StringVar();self.vars.append(v);ttk.Entry(tools,textvariable=v,width=28).pack(fill='x',pady=(0,5))
  ttk.Button(tools,text="Apply tile properties",command=lambda:editor.guard(self.apply)).pack(fill="x",pady=5)
  self.pal=tk.StringVar(value="0");self.manual_palette=tk.BooleanVar(value=False)
  ttk.Checkbutton(tools,text="Advanced: manual palette / all tiles",variable=self.manual_palette,command=self.toggle_palette).pack(anchor="w",pady=5)
  palette_host=ttk.Frame(tools);palette_host.pack(fill="x")
  self.palette_controls=ttk.Frame(palette_host)
  ttk.Label(self.palette_controls,text="Palette (0-15)").pack(side="left")
  ttk.Spinbox(self.palette_controls,from_=0,to=15,textvariable=self.pal,width=6,command=lambda:editor.guard(self.atlas)).pack(side="left")
  tool_button=ttk.Button(bar,text='Tile Properties',command=self.open_tile_tools);self.tile_tools_button=tool_button
  tool_button.pack(side='left',padx=8)
  self.height.trace_add('write',lambda *_:self.keep_height_preview())
  self.update_height_controls()
  ttk.Button(bar,text='Map Properties',command=lambda:editor.guard(self.open_map_music)).pack(side='left')
  self.wall=tk.StringVar(value="Floor")
  self.tile_zoom=tk.StringVar(value="100%")
  tile_row=ttk.Frame(side);tile_row.pack(fill="x",pady=(6,3))
  self.layer_floor=tk.BooleanVar(value=False)

  ttk.Checkbutton(tile_row,text="Layer On Top",variable=self.layer_floor,command=self.layer_floor_changed).pack(side="left",padx=(8,0))
  self.force_wall=tk.BooleanVar(value=False)   # painted tiles become walls (x) only when this is ticked
  # Force wall checkbox removed (user 2026-10-25); the setting stays off
  ttk.Label(tile_row,text="Tile Picker Zoom").pack(side="left",padx=(10,4))
  zoom=ttk.Combobox(tile_row,textvariable=self.tile_zoom,values=[f"{p}%" for p in range(25,501,25)],width=6,state="readonly");zoom.pack(side="left");zoom.bind("<<ComboboxSelected>>",lambda _:editor.guard(self.change_tile_zoom))
  button_row=ttk.Frame(side);button_row.pack(fill="x",pady=(0,3))   # Add map tiles / No tile, under the options row
  ttk.Button(button_row,text="Add map tiles…",command=lambda:editor.guard(self.add_map_tiles)).pack(side="left")
  ttk.Button(button_row,text="No tile (erase)",command=lambda:editor.guard(self.choose_eraser)).pack(side="left",padx=(6,0))
  ttk.Button(button_row,text="Remove map",command=lambda:editor.guard(self.remove_map_tiles)).pack(side="left",padx=(6,0))
  from wrap_tabs import WrapTabs
  self.tile_source_tabs=WrapTabs(side);self.tile_source_tabs.pack(fill="x")   # wraps onto more rows when there are many map tabs
  # Tiles tab: its own Floors / Walls tabs (shown only while Tiles is open)
  self.tile_kind='floors';self.tile_kind_tabs=WrapTabs(side,sub=True);self.tile_kind_tabs.pack(fill="x",pady=(2,0))
  self.tile_kind_frames={}
  self.tile_kind_tabs.bind('<<NotebookTabChanged>>',lambda _:editor.guard(self.tile_kind_changed))
  # third row: This Map / Indoor / Outdoor, or Main / Edges / Other (shown only when the open sub-tab has them)
  self.tile_part_tabs=WrapTabs(side,sub=True);self.tile_part_frames={};self.tile_part_key=None
  self.tile_parts={'floors':'map','walls':'map','stairs':'map','water':'map','ice':'map','lava':'map','sand':'map','spikes':'map'}
  self.tile_part_tabs.bind('<<NotebookTabChanged>>',lambda _:editor.guard(self.tile_part_changed))
  self.tile_source_frames={};self.tile_tab_key=None
  self.tile_source_tabs.bind('<<NotebookTabChanged>>',lambda _:editor.guard(self.tile_source_changed))
  self.tile_section=tk.StringVar(value="Whole map")
  self.tile_section_choices=ttk.Combobox(side,textvariable=self.tile_section,values=["Whole map"],state="readonly")
  # (the section dropdown above the tile picker was removed 2026-10-11; it still exists, unshown)
  self.tile_section_choices.bind('<<ComboboxSelected>>',lambda _:editor.guard(self.tile_section_changed))
  self.tile_section_memory={};self.tile_view_key=None
  library=ttk.Frame(side);library.pack(fill="both",expand=True)
  self.library=ZoomCanvas(library,width=480,height=600);scroll=ttk.Scrollbar(library,command=self.library.yview)
  hscroll=ttk.Scrollbar(library,orient="horizontal",command=self.library.xview);hscroll.pack(side="bottom",fill="x");self.library.configure(xscrollcommand=hscroll.set)
  def scrolled(first,last):
   scroll.set(first,last)
   if getattr(self,'column_items',None):self.editor.root.after_idle(self.draw_visible_columns)
  self.library.configure(yscrollcommand=scrolled);scroll.pack(side="right",fill="y");self.library.pack(side="left",fill="both",expand=True)
  self.library.bind("<Button-1>",lambda e:editor.guard(lambda:self.library_press(e)))
  self.library.bind("<B1-Motion>",self.library_drag)
  self.library.bind("<ButtonRelease-1>",lambda e:editor.guard(lambda:self.library_release(e)))
  self.library.bind("<Button-3>",lambda e:editor.guard(lambda:self.library_right_click(e)))
  self.tile_widgets=[(w,w.pack_info()) for w in side.winfo_children() if w.winfo_manager()]
  self.event_side=ttk.Frame(side)
  # Edit heights: a palette of height numbers instead of tiles
  self.height_side=ttk.Frame(side);self.height_brush=tk.IntVar(value=-1)   # -1: clicks add/subtract 1
  ttk.Label(self.height_side,text="Heights",font=("Segoe UI",14,"bold")).pack(anchor="w",pady=(0,6))
  row=ttk.Frame(self.height_side);row.pack(anchor="w",fill="x",pady=(0,6))
  ttk.Radiobutton(row,text="+1 / -1 clicks",value=-1,variable=self.height_brush).pack(side="left")
  self.show_wall_pit_heights=tk.BooleanVar(value=False)   # off: grey squares stay plain, no-walk tiles show x
  ttk.Checkbutton(row,text="Show Wall / Pit Heights",variable=self.show_wall_pit_heights,command=lambda:editor.guard(lambda:(self.store_setting('show_wall_pit_heights'),self.redraw_height_numbers_from_grid()))).pack(side="left",padx=(16,0))
  self.wall_empty=tk.BooleanVar(value=False)   # on: empty tiles (no picture, no walls) are no-walk
  grid=ttk.Frame(self.height_side);grid.pack(anchor="w")
  # Number buttons: all plain white text; hover only lightens the background a
  # little and the picked number gets a quiet box - no coloured text.
  st=ttk.Style()
  st.configure("HeightNumber.Toolbutton",foreground="#e6e6e6",anchor="center")
  st.map("HeightNumber.Toolbutton",foreground=[("selected","#ffffff"),("active","#ffffff"),("!disabled","#e6e6e6")],
         background=[("selected","#3a4250"),("active","#2c323c")])
  for n in range(32):
   ttk.Radiobutton(grid,text=str(n),value=n,variable=self.height_brush,style="HeightNumber.Toolbutton",width=4).grid(row=n//8,column=n%8,padx=2,pady=2)
  # (hidden for now, user 2026-10-25; code kept) ttk.Button(self.height_side,text="No Mask",command=lambda:editor.guard(self.no_mask_all)).pack(anchor="w",pady=(6,0))
  # (hidden for now, user 2026-10-25; code kept) ttk.Button(self.height_side,text="Fix Masks",command=lambda:editor.guard(self.fix_masks_button)).pack(anchor="w",pady=(4,0))
  self.show_layers=tk.BooleanVar(value=False)   # (hover window, not shown in the panel)
  self.layer_view=tk.IntVar(value=0)   # Layer 1-10: the map shows only that layer of every square (user 2026-10-25)
  self.tile_info=tk.BooleanVar(value=False)   # Tile info: hover tells the heights on a square, click opens them to edit (user 2026-10-25)
  self.height_wall_mode=tk.BooleanVar(value=False)
  wt=ttk.Frame(self.height_side);wt.pack(anchor="w",pady=(6,0))   # Wall, then Tile fix, on one row
  ttk.Checkbutton(wt,text="Wall",variable=self.height_wall_mode).pack(side="left")
  ttk.Checkbutton(wt,text="Tile fix",variable=self.tile_info).pack(side="left",padx=(12,0))
  # Draw all further back is its own button, outside the Tile fix window (user 2026-10-25): the whole map
  # hidden; F9 shows / hides it (user 2026-10-25). Builds run it anyway, before Fix Masks.
  self.draw_behind_button=ttk.Button(self.height_side,text="Draw all behind Alundra",command=lambda:editor.guard(self.tile_fix_mask_map))
  self.draw_behind_anchor=wt
  def _toggle_draw_behind(_e=None):
   b=self.draw_behind_button
   try:
    if b.winfo_manager():b.pack_forget()
    else:b.pack(anchor="w",pady=(6,0),after=self.draw_behind_anchor)
   except Exception:pass
  try:editor.root.bind_all('<F9>',_toggle_draw_behind,add='+')
  except Exception:pass   # replaces Draw all further back (user 2026-10-25)
  self.height_show=tk.StringVar(value='Highest')
  show=ttk.Frame(self.height_side);show.pack(anchor="w",pady=(6,0))
  for name in ('Highest','Lowest'):   # Buggy tiles view kept in the code but no longer pickable (user 2026-10-25)
   ttk.Radiobutton(show,text=f"{name} tiles",value=name,variable=self.height_show,command=lambda:editor.guard(self.redraw_height_numbers_from_grid)).pack(side="left",padx=(0,10))
  ttk.Label(self.event_side,text="Characters & events",font=("Segoe UI",14,"bold")).pack(anchor="w",pady=(0,8))
  ttk.Label(self.event_side,text="Click to select. Drag to move.\nDouble-click an event to edit its command list; double-click an empty tile to create one.").pack(anchor="w",pady=(0,12))
  self.record_filter=tk.StringVar()
  ttk.Label(self.event_side,text="Find an event").pack(anchor="w")
  ttk.Entry(self.event_side,textvariable=self.record_filter).pack(fill="x",pady=(3,8))
  self.record_list=ttk.Treeview(self.event_side,columns=("name",),show="headings",height=18,selectmode="browse")
  self.record_list.heading("name",text="Name / record");self.record_list.column("name",width=240)
  self.record_list.pack(fill="both",expand=True)
  self.record_list.bind("<<TreeviewSelect>>",self.choose_record)
  self.record_list.bind("<Double-Button-1>",lambda _:editor.guard(self.edit_selected_process))
  self.record_list.bind("<Delete>",lambda _:editor.guard(self.delete_selected_event))
  self.record_list.bind("<Control-c>",lambda _:editor.guard(self.copy_selected_event))
  self.record_list.bind("<Control-x>",lambda _:editor.guard(self.cut_selected_event))
  self.record_list.bind("<Control-v>",lambda _:editor.guard(self.paste_event_at_selected_tile))
  ttk.Button(self.event_side,text="Edit process",command=lambda:editor.guard(self.edit_selected_process)).pack(fill="x",pady=(12,4))
  ttk.Button(self.event_side,text="Properties",command=lambda:editor.guard(self.edit_selected_properties)).pack(fill="x")
  self.record_filter.trace_add("write",lambda *_:self.populate_record_list())
  self.mode.trace_add("write",lambda *_:self.change_mode())
 def queue_pane_layout(self,event=None):
  if self.picker_sash_dragging or self.pane_layout_job is not None:return
  self.pane_layout_job=self.editor.root.after_idle(self.apply_pane_layout)
 def apply_pane_layout(self):
  self.pane_layout_job=None
  width=self.workspace_panes.winfo_width()
  if width>1 and len(self.workspace_panes.panes())>1 and not self.picker_sash_dragging:
   self.workspace_panes.sashpos(0,round(width*self.picker_width_fraction))
 def begin_pane_resize(self,event):
  self.picker_sash_dragging=self.workspace_panes.identify(event.x,event.y) not in ('',None)
 def end_pane_resize(self,event):
  if not self.picker_sash_dragging:return
  self.picker_sash_dragging=False
  width=self.workspace_panes.winfo_width()
  if width>1:self.picker_width_fraction=self.workspace_panes.sashpos(0)/width
 def open_map_music(self):
  from map_music_ui import MapMusicDialog
  MapMusicDialog(self.editor)
 def open_tile_tools(self):
  self.tile_tools_window.deiconify();self.tile_tools_window.lift()
 def update_layer_choices(self):
  layers=["Floor"]+[f"Wall {i}" for i in range(max((len(c["walls"]) for c in self.grid_cells),default=0))]
  combo=getattr(self,"wall_combo",None)
  if combo is not None:combo.configure(values=layers)
  if self.wall.get() not in layers:self.wall.set("Floor")
 def show_height_side(self):
  """Edit heights shows the height numbers where the tiles normally are."""
  side=self.height_side
  if self.height_edit.get():
   for widget,_ in self.tile_widgets:widget.pack_forget()
   self.tile_part_tabs.pack_forget()
   self.event_side.pack_forget();side.pack(fill="both",expand=True)
  elif side.winfo_ismapped():
   side.pack_forget()
   if self.mode.get() not in ("Entities","Events","Warps"):
    self.repack_tile_widgets()
 def repack_tile_widgets(self):
  """Show the tile-side widgets again in their order; the third tab row
  (This Map / Indoor / Outdoor, Main / Edges / Other) goes back under the
  Floors / Walls ... tabs when one is open (it was lost before, 2026-10-15)."""
  for widget,options in self.tile_widgets:widget.pack(**options)
  if getattr(self,'tile_part_key',None) is not None:self.tile_part_tabs.pack(fill='x',pady=(2,0),after=self.tile_kind_tabs)   # (pack: see _safe_pack)
 def change_mode(self):
  if self.height_edit.get() and self.mode.get()!="Select tile":self.mode.set("Select tile")
  if self.mode.get()!="Paint tiles":self.bush_brush=None;self.face_brush=False
  self.update_height_controls()
  self.clear_group_preview()
  events=self.mode.get() in ("Entities","Events","Warps")
  self.record_drag=None;self.drag_point=None
  if hasattr(self,"info"):self.draw_records()
  if events:
   for widget,_ in self.tile_widgets:widget.pack_forget()
   self.tile_part_tabs.pack_forget()
   self.event_side.pack(fill="both",expand=True);self.populate_record_list()
   self.canvas.configure(cursor="arrow")
  else:
   self.event_side.pack_forget()
   self.repack_tile_widgets()
   self.canvas.configure(cursor="crosshair" if self.mode.get()=="Paint tiles" else "arrow")
  self.show_height_side()
 def elevation_enabled(self):
  return self.height.get()   # height editing shows the map as it looks everywhere else
 def arm_start_point(self):
  if self.editor.session is None or self.editor.current_map is None:raise ValueError('Load a map before selecting the new-game start point')
  if not self.events_allowed():self.select_tool('Select tile')   # switch the tile tool off instead of refusing (user 2026-10-25)
  self.start_point_armed=True;self.mode.set('Select tile')
  self.caption.set('Click a floor tile to place the S new-game start point. Its native height will be taken from that tile.')
 def set_start_point_from_click(self,event):
  x=self.canvas.canvasx(event.x);y=self.canvas_y(event);hit=self.renderer.surface_at(x,y)
  if hit is None:
   self.caption.set('Choose a visible floor tile for the S start point.');return
  _,_,tx,ty,_,_=hit
  if not (0<=tx<self.grid_width and 0<=ty<self.grid_height):
   self.caption.set('Start point must be on the map floor.');return
  from editor_start_point import set_start_point
  point=set_start_point(self.editor.database.document,self.editor.session,self.editor.current_map,tx,ty)
  self.editor.dirty=True;self.start_point_armed=False;self.ignore_start_double_until=time.monotonic()+0.6
  self.caption.set(f"S start point set: map {point['map_id']}, tile {point['x']},{point['y']}, height {point['z']}. Build game applies it to new games.")
  self.draw_records()
 def jump_to_start_point(self):
  from editor_start_point import effective_start_point
  point,label,authored=effective_start_point(self.editor)
  self.caption.set(('Your S start point' if authored else label+' (from game data)')+f": map {point['map_id']}, tile {point['x']},{point['y']}.")
  map_id=point.get('map_id')
  if map_id!=self.editor.current_map:
   self.editor.map_id.set(str(map_id));self.editor.guard(self.editor.load_map)
  self.editor.root.after_idle(lambda:self.center_on_start_point(point))
 def center_on_start_point(self,point):
  self.canvas.update_idletasks()
  region=self.canvas.cget('scrollregion')
  try:left,top,right,bottom=(float(value) for value in self.canvas.tk.splitlist(region))
  except (TypeError,ValueError):return
  width=max(1,right-left);height=max(1,bottom-top)
  target_x=point['x']*24+12;target_y=map_y_to_view(point['y']*16+self.margin+8,getattr(self,'map_crop_top',0))
  try:
   from editor_start_point import resolve_start_point
   resolved=resolve_start_point(self.editor.session,point)
   if self.elevation_enabled():target_y-=point.get('z',resolved['z'])*16
  except (ValueError,TypeError,KeyError):pass
  self.canvas.xview_moveto(max(0,min(1,(target_x-self.canvas.winfo_width()/2-left)/width)))
  self.canvas.yview_moveto(max(0,min(1,(target_y-self.canvas.winfo_height()/2-top)/height)))
 def clear_start_point(self):
  options=self.editor.database.document.get('mod_options',{})
  if options.pop('start_point',None) is not None:
   self.editor.dirty=True;self.draw_records();self.caption.set('S start point removed from this mod.')
 def select_tool(self,value):
  """The radio group: switch off the tool that is on, then switch on the chosen one."""
  self.commit_stacks()   # waiting tile edits first: written after, their copy of the tiles reset your x's
  if getattr(self,'pending_heights',None):self.commit_heights()   # write waiting no-walk/height edits first, or the switch redraws without them
  tools={'heights':(self.height_edit,self.toggle_height_edit),'no_walk':(self.mark_walls,self.toggle_mark_walls),
         'mask':(self.mask_layer,self.toggle_mask_mode)}
  for key,(var,toggle) in tools.items():
   if key!=value and var.get():var.set(False);toggle()
  if value in tools:
   var,toggle=tools[value]
   if not var.get():var.set(True);toggle()
  else:self.mode.set(value)
  self.sync_tool()
 def sync_tool(self):
  """Show the active tool or mode in the radio group (without running it again)."""
  value=('heights' if self.height_edit.get() else 'no_walk' if self.mark_walls.get() else
         'mask' if self.mask_layer.get() else self.mode.get())
  if self.tool.get()!=value:
   self._tool_sync=True
   try:self.tool.set(value)
   finally:self._tool_sync=False
 def toggle_mask_mode(self):
  """Mask layer: click a tile picture to have it drawn in front of the player
  (★); click a ★ to put it back. Heights and walls are not touched."""
  if self.mask_layer.get():
   if self.height_edit.get():self.height_edit.set(False);self.commit_heights()
   if self.mark_walls.get():self.mark_walls.set(False)
   self.mode.set("Select tile")
   self.caption.set("Mask layer: click a tile picture to draw it in front of the player (★). Click a ★ to put it back.")
  else:self.caption.set("Mask layer finished.")
  self.update_height_controls();self.refresh(reload_textures=False)
 def draw_buggy_tiles(self,limit=10):
  """Buggy tiles view (Edit heights, user 2026-10-25): outline in magenta every square
  drawn by a tile of height `limit` or more, labelled with that tile's map row and
  height (r22 h17). Only marks them; nothing is changed. Numbers as Lowest tiles."""
  if not hasattr(self,'canvas'):return
  self.canvas.delete('tall_tile');self.buggy_squares={}
  if not (self.height_edit.get() and self.height_show.get()=='Buggy'):return
  self.canvas.delete('height_number')   # only the buggy tiles' numbers are shown (user 2026-10-25)
  # Red number: a picture the game draws OVER Alundra (no_mask.find_masking says where he
  # stands under it). Blue number: a tile of height `limit`+. The number is that tile's height.
  from no_mask import find_masking
  w=self.grid_width;crop=getattr(self,'map_crop_top',0);elev=self.elevation_enabled()
  cells=[{'values':c['values'],'walls':((c['walls'][0][2],[k[1] for k in c['walls']]) if c['walls'] else None)} for c in self.grid_cells]
  marks={};reasons=[]
  for x,y,r,cd,where,qs in find_masking(cells,w,self.grid_height):
   marks[(x,r)]=((x,y),'#ff5a5a',where[0])
   reasons.append(f"({x},{y}) {'floor' if where[0]=='floor' else 'piece'} covers Alundra on tile "+"/".join(f"({x},{q})" for q in qs))
  tall=0
  for c in self.grid_cells:
   v=c['values']
   if v[3]<limit:continue
   tall+=1;floor=c['y']-v[3]
   marks.setdefault((c['x'],floor),((c['x'],c['y']),'#58aaff','floor'))
   for _,cd,sh,i in c['walls']:
    if cd!=0xFFFF:marks.setdefault((c['x'],floor+i+1-sh),((c['x'],c['y']),'#58aaff','wall'))
  for (x,r),((tx,ty),color,kind) in marks.items():
   py=r*16+self.margin if elev else ty*16+self.margin
   self.buggy_squares[(x,int(py)//16)]=(tx,ty,kind,r)   # a click here moves only this picture
   vy=map_y_to_view(py,crop);text=str(ty-r)   # the picture's own height (its tile's row minus its row)
   for ox,oy in ((-1,0),(1,0),(0,-1),(0,1)):self.canvas.create_text(x*24+12+ox,vy+8+oy,text=text,fill='black',font=('Segoe UI',8,'bold'),tags='tall_tile')
   self.canvas.create_text(x*24+12,vy+8,text=text,fill=color,font=('Segoe UI',8,'bold'),tags='tall_tile')
  self.canvas.tag_raise('tall_tile')
  self.caption.set((f"Red = drawn over Alundra ({len(reasons)}): "+"; ".join(reasons[:8])+(" …" if len(reasons)>8 else "")+". " if reasons else "Nothing drawn over Alundra. ")+
                   (f"Blue = {tall} tile(s) at height {limit}+. " if tall else "")+"Click a number to give that tile the picked height.")
 def buggy_click(self,event):
  """Buggy tiles view: a click on a number moves ONLY that picture to the picked height
  (row = its tile's row minus the height; +1 with '+1 / -1 clicks'). Every other picture
  of the tile stays where it is (user 2026-10-25). True if a buggy number was hit."""
  x,y=int(self.canvas.canvasx(event.x)),int(self.canvas_y(event))
  hit=getattr(self,'buggy_squares',{}).get((x//24,y//16))
  if hit is None:return False
  tx,ty,kind,r=hit;w=self.grid_width;c=self.grid_cells[ty*w+tx];v=c['values']
  n=self.height_brush.get();cur=ty-r;new=n if n>=0 else cur+1
  if new==cur:return True
  floor=ty-v[3];pieces={row-floor:cd for row,cd,f in self.record_pieces(c) if not f}
  if kind=='floor':
   # the floor picture moves with the tile's height; its pieces are re-based so they stay put
   if not 0<=new<=255:self.caption.set("Heights go from 0 to 255.");return True
   d=new-v[3];pieces={rel+d:cd for rel,cd in pieces.items()};height=new
  else:
   rel=r-floor;cd=pieces.pop(rel,None);nrel=(ty-new)-floor
   if cd is None:return True
   # a picture already at that height on this tile: they swap places (user 2026-10-25: never refuse)
   if nrel in pieces:pieces[rel]=pieces[nrel]
   pieces[nrel]=cd;height=v[3]
  walls=self.rebased_walls(pieces)
  if walls is False:return True   # past what a tile can hold (127 squares): left as it is
  old=self.tile_rows(tx,ty)
  if height!=v[3]:
   self.pending_heights[c['offset']+3]=height;c['values']=v[:3]+(height,)+v[4:]
   g=self.stack_grid();sc=g[2][ty*w+tx];sv=list(sc['values']);sv[3]=height;sc['values']=tuple(sv)
  if pieces or c['walls']:self.set_cell_walls(tx,ty,walls)
  self.editor.dirty=True
  self.redraw_columns([(tx,ty)],before={(tx,ty):old})
  self.redraw_height_numbers_from_grid()
  self.caption.set(f"Tile ({tx}, {ty}): only its {'floor picture' if kind=='floor' else 'piece'} moved from height {cur} to {new}; its other pictures stayed.")
  return True
 def no_mask_all(self):
  """No Mask button (Edit heights): pictures shown above where Alundra stands but owned
  by a tile further down the map (drawn after him in game) move to a tile further up
  the map, only when the editor picture stays the same (see no_mask.py)."""
  self.commit_pending()
  from map_area_copy import cells_of,rebuild_grid
  from no_mask import fix_map
  e=self.editor;w,hh,cells=cells_of(e.session,e.current_map)
  margin=max((c['values'][3] for c in cells),default=0)*16
  n,_=fix_map(self.renderer,cells,w,hh,margin)
  if n:
   rebuild_grid(e.session,e.current_map,cells,f"No Mask ({n} pictures)")
   e.dirty=True;self.refresh(reload_textures=False,keep_view=True)
  self.caption.set(f"No Mask: {n} tile picture(s) moved behind Alundra; the map looks the same. Undo takes it back." if n else "No Mask: nothing on this map could be moved behind Alundra.")
 def unmask_piece(self,tx,ty,idx,touched):
  """Move wall piece idx of tile (tx, ty) into the floor picture of a tile whose floor
  is drawn on the same square, if the map picture stays the same. True if moved."""
  w,hh=self.grid_width,self.grid_height
  c=self.grid_cells[ty*w+tx];v=c['values'];floor=ty-v[3]
  _,cd,shift,_=c['walls'][idx];row=floor+idx+1-shift
  keep={r-floor:c2 for r,c2,f in self.record_pieces(c) if not f};keep.pop(row-floor,None)
  walls=self.rebased_walls(keep)
  if walls is False:return False
  want=self.column_picture(tx)
  qs=[q for q in range(hh) if q-self.grid_cells[q*w+tx]['values'][3]==row]
  qs.sort(key=lambda q:(self.grid_cells[q*w+tx]['values'][4]!=0xFFFF,q))   # empty floors first
  for q in qs:
   qc=self.grid_cells[q*w+tx]
   if q==ty:over={ty:{'values':v[:4]+(cd,)+v[5:],'walls':walls}}
   else:
    qv=list(qc['values']);qv[4]=cd
    over={ty:{'values':v,'walls':walls},q:{'values':tuple(qv),'walls':((qc['walls'][0][2],[k[1] for k in qc['walls']]) if qc['walls'] else None)}}
   if self.column_picture(tx,over)!=want:continue
   for t in {(tx,ty),(tx,q)}:touched.setdefault(t,self.tile_rows(*t))
   self.set_cell_walls(tx,ty,walls)
   qv=list(qc['values']);qv[4]=cd;qc['values']=tuple(qv)
   data=self.editor.session.data
   for i,b in ((4,cd&0xFF),(5,cd>>8)):
    at=qc['offset']+i
    if data[at]==b:self.pending_heights.pop(at,None)
    else:self.pending_heights[at]=b
   g=self.stack_grid();sv=list(g[2][q*w+tx]['values']);sv[4]=cd;g[2][q*w+tx]['values']=tuple(sv)
   return True
  return False
 def toggle_mark_walls(self):
  """Mark walls: the map shows only walls (x); a click makes a floor tile a
  wall or a wall you made walkable again. Heights are not touched."""
  if self.mark_walls.get():
   self.mask_layer.set(False)
   if self.height_edit.get():self.height_edit.set(False);self.commit_heights()
   self.mode.set("Select tile")
   self.caption.set("No Walk Area: click or drag to make tiles no-walk (red x, blocks everyone); hold Shift for player-only (orange x). Start on an x to make tiles walkable.")
  else:
   self.caption.set("No Walk Area finished.")
  self.update_height_controls()
  self.refresh(reload_textures=False)
 def toggle_height_edit(self):
  if self.height_edit.get():
   self.mark_walls.set(False);self.mask_layer.set(False)
   self.start_point_armed=False
   self.height.set(True)
   self.mode.set("Select tile")
   self.selected_record=None;self.record_drag=None;self.drag_point=None
   self.caption.set("Height edit: left-click +1, right-click -1.")
   n=self.block_wall_squares() if hasattr(self,'grid_cells') else 0   # earlier Wall mode squares: no walking there either
   if n:self.caption.set(f"Height edit: {n} tile(s) under Wall mode squares made no-walk.")
  else:
   self.commit_heights();self.caption.set("Height editing finished.")
  self.update_height_controls();self.show_height_side()
  self.refresh(reload_textures=False)
 def update_height_controls(self):
  editing=self.height_edit.get() or self.mark_walls.get() or self.mask_layer.get()
  if hasattr(self,'tool'):self.sync_tool()   # one radio group: every choice stays clickable
  for button in self.event_action_buttons:button.configure(state='disabled' if editing else 'normal')
  if hasattr(self,'start_point_button'):self.start_point_button.configure(state='disabled' if editing else 'normal')
 def keep_height_preview(self):
  if not self.height.get():self.height.set(True)
 def events_allowed(self):
  lock=getattr(getattr(self,'editor',None),'lock_in_closed_events',None)
  if lock:lock()   # a just-closed event editor saves before map events change
  return not self.tile_mode_on()
 def tile_mode_on(self):
  """Edit heights, Mark walls or Mask layer is on: no events are made, moved or pasted."""
  return any(getattr(self,name,None) is not None and getattr(self,name).get() for name in ('height_edit','mark_walls','mask_layer'))
 def canvas_y(self,event):
  return view_y_to_map(self.canvas.canvasy(event.y),getattr(self,'map_crop_top',0))
 def default_visible(self,kind):
  name="show_default_objects" if kind=="entities" else "show_default_events"
  var=getattr(self,name,None)
  return var is None or var.get()
 def change_default_visibility(self):
  if self.selected_record and self.selected_record[0] in ("entities","events") and not self.default_visible(self.selected_record[0]):
   self.selected_record=None;self.record_drag=None
  if self.editor.session is not None and self.editor.current_map is not None:self.draw_records()
 def populate_record_list(self):
  if not hasattr(self,"record_list") or not hasattr(self,"info"):return
  self.record_list.delete(*self.record_list.get_children())
  search=self.record_filter.get().lower()
  if self.mode.get()=="Warps":
   for index,offset,p in self.warp_rows:
    label=f"Warp {index} -> {map_label(p.destination_map)} ({p.destination_x}, {p.destination_y})"
    if search in label.lower():self.record_list.insert("","end",iid=f"warps:{index}",values=(label,))
   return
  for kind in ("entities","events"):
   if not self.default_visible(kind):continue
   if kind=="events" and self.mode.get()=="Entities":continue
   for index,row in enumerate(self.info[kind]):
    if record_deleted(self.editor.database.document,self.editor.current_map,kind,index):continue
    label=(f"Character {index} / sprite {self.editor.session.data[int(row['offset'],16)+6]}" if kind=="entities" else f"Trigger {index} / program {row['program']&127}")
    if search in label.lower():self.record_list.insert("","end",iid=f"{kind}:{index}",values=(label,))
  for index,row in enumerate(self.editor.database.document.get("event_graphs",[])):
   if row["map_id"]!=self.editor.current_map:continue
   x,y,w,h=row["region"];label=f"{row['name']} · tile {x},{y} · {row['trigger']}"
   if search in label.lower():self.record_list.insert("","end",iid=f"graphs:{index}",values=(label,))
 def choose_record(self,event=None):
  if not self.events_allowed():return
  selection=self.record_list.selection()
  if not selection:return
  kind,index=selection[0].split(":");self.selected_record=(kind,int(index));self.highlight_record()
 def update_whole_event_menu(self,entries):
  self.whole_event_menu.delete(0,"end")
  for kind,index,label in entries:
   self.whole_event_menu.add_command(label=label,command=lambda k=kind,i=index:self.editor.guard(lambda:self.open_whole_event(k,i)))
  self.whole_event_button.configure(text=f"Whole-map events ({len(entries)})",state="normal" if entries else "disabled")
 def open_whole_event(self,kind,index):
  if not self.events_allowed():return
  self.record_drag=None;self.drag_point=None
  self.selected_record=(kind,index);self.highlight_record()
  key=f"{kind}:{index}"
  if self.record_list.exists(key):self.record_list.selection_set(key);self.record_list.see(key)
  self.edit_selected_process()
 def edit_selected_process(self):
  if not self.events_allowed():return
  if self.selected_record is None:self.caption.set("Select a character or trigger first.");return
  if self.selected_record[0]=="warps":WarpWindow(self.editor,self.selected_record[1]);return
  if self.selected_record[0]=="graphs":
   row=self.editor.database.document["event_graphs"][self.selected_record[1]]
   self.editor.open_event_builder(row["id"]);return
  from event_process_ui import EventProcess
  EventProcess(self.editor,*self.selected_record)
 def edit_selected_properties(self):
  if not self.events_allowed():return
  if self.selected_record:
   if self.selected_record[0]=="graphs":
    row=self.editor.database.document["event_graphs"][self.selected_record[1]];self.editor.open_event_builder(row["id"])
   elif self.selected_record[0]=="warps":WarpWindow(self.editor,self.selected_record[1])
   else:self.open_record(*self.selected_record)
 def delete_selected_event(self):
  if not self.events_allowed():return
  if self.selected_record is None:raise ValueError("Select an event or character to delete")
  kind,index=self.selected_record
  from event_deletion import delete_graph,delete_record
  if kind=="graphs":
   event_id=self.editor.database.document['event_graphs'][index]['id']
   message=delete_graph(self.editor.session,self.editor.database,event_id)
  elif kind in ('entities','events'):
   message=delete_record(self.editor.session,self.editor.database,self.editor.current_map,kind,index)
  elif kind=='warps':
   from warp_editor import delete_warp
   delete_warp(self.editor.session,self.editor.current_map,index);self.editor.dirty=True
   message=f'Warp {index} deleted; later warps moved up one slot. Undo restores it.'
  else:raise ValueError("Select a character, event or warp to delete")
  self.selected_record=None;self.record_drag=None
  self.editor.status.set(message);self.refresh(reload_textures=False);self.caption.set(message)
 def copy_selected_event(self):
  if not self.events_allowed():return
  if self.selected_record and self.selected_record[0]=='entities':   # an original character
   index=self.selected_record[1];data=self.editor.session.data;o=int(self.info['entities'][index]['offset'],16)
   catalogue=data[o+6]+(256 if data[o+5]&128 else 0)
   klass=next((r for r in self.editor.database.definitions if r.get('source',{}).get('catalogue_index')==catalogue and not r.get('clone_of')),None)
   if klass is None:raise ValueError('This character has no database class to copy it with')
   self.event_clipboard={'native':True,'map':self.editor.current_map,'index':index,'class_id':klass['id'],'name':klass.get('name') or 'Character'}
   self.caption.set(f"Copied {self.event_clipboard['name']} (original). Click a destination tile, then Paste event.");return
  if self.selected_record and self.selected_record[0]=='events':
   raise ValueError("Original map triggers can be deleted, not copied yet")
  if not self.selected_record or self.selected_record[0]!='graphs':raise ValueError('Select a project event on the map first')
  self.event_clipboard=self.editor.database.document['event_graphs'][self.selected_record[1]].copy()
  from copy import deepcopy
  self.event_clipboard=deepcopy(self.event_clipboard)
  self.caption.set(f"Copied {self.event_clipboard['name']}. Click a destination tile, then Paste event.")
 def paste_event_at_selected_tile(self):
  if not self.events_allowed():return
  if self.event_clipboard is None:raise ValueError('Copy a project event first')
  from copy import deepcopy
  if self.selected is None:raise ValueError('Click a destination map tile first')
  if self.editor.session is None or self.editor.current_map is None:raise ValueError('Load a map before pasting an event')
  x,y=self.selected
  from content_database import ContentDatabase
  candidate=ContentDatabase(self.editor.database.to_json())
  if self.event_clipboard.get('native'):
   # an original character: a project event of its class that borrows its behaviour
   clip=self.event_clipboard
   clone=candidate.new_event_graph(self.editor.current_map,clip['name'],x,y,clip['class_id'])
   clone.setdefault('native_placement',{}).update(donor_map_id=clip['map'],donor_entity_index=clip['index'],behaviour_variant=True)
   candidate.replace_event_graph(clone['id'],clone)
   self.editor.session.replace_document(self.editor.database.document,candidate.document,'Paste event '+clone['name'])
   self.editor.dirty=True;self.selected_record=('graphs',next(i for i,row in enumerate(self.editor.database.document['event_graphs']) if row['id']==clone['id']))
   self.refresh(reload_textures=False)
   self.caption.set(f"Pasted {clone['name']} at {x},{y} with the original's behaviour. Undo removes it.");return
  graphs=candidate.document['event_graphs'];source_gone=not any(g['id']==self.event_clipboard['id'] for g in graphs)
  if source_gone:graphs.append(deepcopy(self.event_clipboard))  # cut event: paste from the clipboard copy
  clone=candidate.duplicate_event_graph(self.event_clipboard['id'],self.editor.current_map,x,y)
  if source_gone:
   candidate.document['event_graphs']=[g for g in candidate.document['event_graphs'] if g['id']!=self.event_clipboard['id']]
   clone['name']=self.event_clipboard['name'];candidate.replace_event_graph(clone['id'],clone)
  self.editor.session.replace_document(self.editor.database.document,candidate.document,'Paste event '+clone['name'])
  self.editor.dirty=True;self.selected_record=('graphs',next(i for i,row in enumerate(self.editor.database.document['event_graphs']) if row['id']==clone['id']))
  self.refresh(reload_textures=False)
  self.caption.set(f"Pasted {clone['name']} at {x},{y}. Undo restores the project event list.")

 def refresh(self,reload_textures=True,keep_view=False):
  """Redraw the map. keep_view: an edit of this map (bushes, walls, floor
  layers): textures are read again but the view stays where it is and the
  tile picker is left alone."""
  self.commit_pending()
  self.group_preview_anchor=None
  self.authored_preview_cache={}
  if self.paint_job is not None:self.editor.root.after_cancel(self.paint_job);self.paint_job=None
  e=self.editor;e.need()
  renderer_changed=reload_textures or not hasattr(self,"renderer") or self.renderer.session is not e.session or self.renderer.m!=e.current_map
  old_crop=self.map_crop_top
  # Keep the view on the same map spot when repainting the same map (painting can
  # change the elevation headroom, which used to make the view jump).
  old_anchor=None
  if (not renderer_changed or keep_view) and hasattr(self,'margin'):
   old_anchor=(self.canvas.canvasx(0),self.canvas.canvasy(0)+old_crop-self.margin)
  if renderer_changed:
   self.selected_record=None
   self.renderer=MapRenderer(e.session,e.current_map)
   try:self.sprites=cached_preview(e.session,e.current_map)
   except (ValueError,IndexError,struct.error):
    self.sprites=SimpleNamespace(frame=lambda *a:None,representative_frame=lambda *a:None,ground_footprint=lambda *a:None)
   if not keep_view:
    try:self.atlas()   # a tile-picker problem must never stop the map from opening
    except Exception as exc:self.editor.report_problem(exc)
  im,self.hits,self.margin=self.renderer.render(self.elevation_enabled())
  self.hit_index={(px//24,py//16):(px,py,tx,ty) for px,py,tx,ty in self.hits}
  self.grid_width,self.grid_height,self.grid_cells=grid(e.session,e.current_map)
  self.load_settings()
  for r in self.editor.database.document.get('masked_tiles',{}).get(str(self.editor.current_map),[]):   # older masks made their record no-walk: undo that
   if isinstance(r,dict):
    mx,my=r['mask'];ox,oy=r['origin'][:2];w=self.grid_width
    if 0<=my<self.grid_height and 0<=oy<self.grid_height and self.grid_cells[my*w+mx]["values"][0]&1 and not self.grid_cells[oy*w+ox]["values"][0]&1:self.set_walk(mx,my,False)
  self.reopen_vanilla_gaps()
  # Automatic gap closing no longer runs on load: painted walls and empty squares
  # are left as you made them.
  self.update_layer_choices()
  self.paint_photos=[]
  self.photo=ImageTk.PhotoImage(im,master=e.root)
  self.canvas.delete("all");self.canvas.create_image(0,0,image=self.photo,anchor="nw",tags="base_map")
  self.canvas.configure(scrollregion=(0,0,im.width,im.height))
  if self.show_grid.get():
   for px,py,_,_ in self.hits:self.canvas.create_rectangle(px,py,px+24,py+16,outline="#343b46")
  # Draw records in the renderer's unshifted coordinate system, then crop only
  # the blank elevation headroom in the view. Native map coordinates stay intact.
  self.map_crop_top=0
  # Height numbers too: drawn uncropped here, then moved with everything else.
  if self.height_edit.get() or self.mark_walls.get():self.draw_height_numbers()
  self.draw_mask_stars()
  self.draw_records()
  crop_top=first_visible_row(im)
  self.map_crop_top=crop_top
  if crop_top:
   self.canvas.move("all",0,-crop_top)
  self.canvas.configure(scrollregion=(0,0,im.width,max(1,im.height-crop_top)))
  if renderer_changed and old_anchor is None:self.canvas.yview_moveto(0)
  elif old_anchor is not None:
   view_height=max(1,im.height-crop_top)
   self.canvas.xview_moveto(max(0,old_anchor[0])/max(1,im.width))
   self.canvas.yview_moveto(max(0,old_anchor[1]-crop_top+self.margin)/view_height)
  if self.selected:self.select(*self.selected)
 # -- Floor layers: "Layer on floor" paints the picked tile on top of the floor
 def layer_floor_changed(self):
  if self.layer_floor.get():
   self.caption.set("Layer On Top: pick a tile, then click a map tile to lay it on top (what is there stays). One tile per click."+" Right-click removes the layer.")
  else:self.caption.set("Painting replaces the floor again.")
 def stack_brush(self):
  """The brush that changes wall stacks (bush, walls, floor layer), or None."""
  if getattr(self,'bush_brush',None) is not None:return self.bush_brush
  if getattr(self,'layer_floor',None) is not None and self.layer_floor.get() and self.brush is not None and not self.group_brush:
   return (dict(kind='layer',code=self.brush,map=self.editor.current_map),f"tile {self.brush&1023} as a floor layer")
  if getattr(self,'face_brush',False) and self.brush is not None and not self.group_brush:
   return (dict(kind='face',code=self.brush,map=self.editor.current_map),f"wall tile {self.brush&1023}")
  if getattr(self,'brush_is_wall',False) and self.brush not in (None,0xFFFF) and not self.group_brush      and getattr(self,'tile_source_tabs',None) is not None and self.top_source_tab() in ('tiles','map'):
   # Wall tiles (Tiles > Walls, a map's Layer 2) layer on top by themselves: the floor
   # under them stays (user 2026-10-21); floor tiles still replace the floor
   return (dict(kind='layer',code=self.brush,map=self.editor.current_map,auto=True),f"wall tile {self.brush&1023} layered on top")
  return None
 # -- Bushes (database Bushes tab: "Use as map brush") ---------------------
 def set_bush_brush(self,style,name):
  """Paint bushes: click or drag over tiles to put this bush on them (the
  tiles keep their floor and height); right-click takes a bush off."""
  if self.height_edit.get():self.select_tool('Paint tiles')   # switch Edit heights off instead of refusing (user 2026-10-25)
  self.mode.set("Paint tiles");self.group_brush=None;self.group_brush_heights=None;self.brush=None
  self.bush_brush=(style,name);self.bush_stroke=None
  if style.get('kind')=='liquid':
   self.caption.set(f"Brush: {name}. Click or drag over tiles to give them this {style.get('liquid','water')} tile with its walkability, ground and slope (the height stays); what is drawn over it in the game is laid on the tile.")
  elif style.get('kind') in ('water_floors','water_stairs','stairs'):
   self.caption.set(f"Brush: {name}. Click or drag over tiles to give them this tile with its walkability, ground and slope (the height stays).")
  elif style.get('kind')=='map_object':
   on_top=self.layer_floor.get()
   self.caption.set(f"Map object: {name}. Click a tile: the object's bottom-left corner goes there and it builds right and up"+(", standing on that tile's height" if style['object']['kind']=='raised' else "; its floor pictures are laid over the tiles")+(". Layer On Top: the floor and what is there stay under it (untick to replace the tiles)." if on_top else ". Layer On Top is off: it replaces the tiles under it."))
  elif style.get('kind')=='walls':
   self.caption.set(f"Wall brush: {name}. Click or drag over tiles to give them these walls (floor and height stay); right-click a tile to remove its walls.")
  else:self.caption.set(f"Bush brush: {name}. Click or drag over tiles to plant it; right-click a bush to remove it. Pick another mode or tile to stop.")
 def store_setting(self,name):
  """Height panel checkboxes are kept in the mod project (saved with it and
  used by builds)."""
  e=self.editor
  if getattr(e,'database',None) is None:return
  e.database.document.setdefault('editor_settings',{})[name]=bool(getattr(self,name).get());e.dirty=True
 def load_settings(self):
  e=self.editor;saved=getattr(getattr(e,'database',None),'document',{}).get('editor_settings',{})
  for name in ('show_wall_pit_heights',):
   if name in saved:getattr(self,name).set(bool(saved[name]))
 def walls_block(self,quiet=False):
  """This map only: every red x square, and every square with nothing drawn,
  next to walkable floor really blocks. Walking from a floor of height h onto the square below/beside it
  uses the record (screen row + h); when that record is empty (nothing drawn)
  and walkable, it is made no-walk. Nothing else is changed."""
  e=self.editor;w=self.grid_width;H=self.grid_height
  if not self.elevation_enabled() and not quiet:self.caption.set("Turn height view on first.");return
  origins={tuple(r['origin'][:2]) for r in e.database.document.get('masked_tiles',{}).get(str(e.current_map),[]) if isinstance(r,dict)}|(getattr(self,'kept_squares',None) or (lambda:set()))()
  shown={}   # screen square (col,row) -> (walkable, height)
  for c in self.grid_cells:
   v=c["values"]
   if v[4]==0xFFFF and not c["walls"]:continue
   sq=(c["x"],c["y"]-v[3])
   cur=shown.get(sq)
   if cur is None or (cur[0] and v[0]&1):shown[sq]=(not v[0]&1,v[3])   # a wall in the square wins
  n=0
  for (col,row),(walk,h) in shown.items():
   if not walk:continue
   for dx,dy in ((0,1),(0,-1),(1,0),(-1,0)):
    nb=shown.get((col+dx,row+dy))
    if nb is not None and nb[0]:continue   # squares shown as a wall, or with nothing drawn, block
    tx,ty=col+dx,row+dy+h
    if not (0<=tx<w and 0<=ty<H) or (tx,ty) in origins:continue
    v=self.grid_cells[ty*w+tx]["values"]
    if self.vanilla_empty(self.grid_cells[ty*w+tx]):continue   # the game's own doorways/overhangs stay walkable
    if v[4]==0xFFFF and not self.grid_cells[ty*w+tx]["walls"] and not v[0]&1:
     self.set_walk(tx,ty,True,bits=0x41);n+=1   # automatic edges stop everyone, like the game's own walls
  if quiet:return n
  self.redraw_height_numbers_from_grid()
  self.caption.set(f"{n} hidden gap(s) behind walls closed on this map. Kept when you save or build.")
 def vanilla_empty(self,c):
  """A square with nothing drawn that the original game already has that way and
  lets you walk on (a doorway, the floor under a wall or roof you walk behind).
  The game handles it itself, so automatic gap closing leaves it alone."""
  e=self.editor;o=c["offset"];orig=getattr(e.session,'original',None)
  if orig is None or o+6>len(orig):return False
  return orig[o+4:o+6]==bytes(e.session.data[o+4:o+6]) and not orig[o]&1
 def reopen_vanilla_gaps(self):
  """Undo automatic gap closing on squares the original game leaves walkable
  (it used to wall off doorways such as Jess's house exit)."""
  if getattr(self,'wall_empty',None) is not None and self.wall_empty.get():return 0
  # Once per map only, so any no-walk you set yourself afterwards is never undone.
  done=self.editor.database.document.setdefault('gap_fix_maps',[])
  if self.editor.current_map in done:return 0
  done.append(self.editor.current_map)
  n=0
  for c in self.grid_cells:
   tx,ty=c["x"],c["y"]
   if c["values"][0]&1 and c["values"][4]==0xFFFF and not c["walls"] and self.vanilla_empty(c):
    self.set_walk(tx,ty,False);n+=1
  return n
 def apply_wall_empty(self):
  """Checkbox: on walls off every empty tile; off makes the ones it walled walkable again."""
  if self.wall_empty.get():return self.wall_off_empty()
  e=self.editor;walled=e.database.document.get('walled_tiles',{}).get(str(e.current_map),[]);n=0
  for c in self.grid_cells:
   v=c["values"]
   if v[4]==0xFFFF and not c["walls"] and v[0]&1 and [c["x"],c["y"]] in walled:self.set_walk(c["x"],c["y"],False);n+=1
  self.redraw_height_numbers_from_grid()
  self.caption.set(f"{n} empty tile(s) walkable again.")
 def wall_off_empty(self,quiet=False):
  """Every tile with no floor picture and no walls (the black void) becomes a
  wall (x), so the player can never walk off the floor into it."""
  n=0
  for c in self.grid_cells:
   v=c["values"]
   if v[4]==0xFFFF and not c["walls"] and not v[0]&1:
    self.set_walk(c["x"],c["y"],True);n+=1
  if quiet:return n
  self.redraw_height_numbers_from_grid()
  self.caption.set(f"{n} empty tile(s) made walls (x). Kept when you save or build.")
 def block_bits(self):
  """Walk bits a new no-walk tile gets: 0x41 stops everyone, 0x01 only the player."""
  return 0x01 if getattr(self,'walk_blocks',None) is not None and 'player' in self.walk_blocks.get() else 0x41
 def block_wall_squares(self,squares=None):
  """Wall mode squares (col, screen row): every tile whose floor lands on one becomes
  no-walk for everyone, written to the map like No Walk Area (user 2026-10-25).
  squares None: all Wall mode squares saved for this map. Returns tiles changed."""
  # A real wall (user 2026-10-25, 'cosmetic 10s are useless'): like the stock game's walls
  # (height 10, no-walk) each tile standing on the square is RAISED to the painted height
  # and made no-walk; its pictures are re-based so every one stays on its square.
  if squares is None:
   squares=[tuple(r[:3]) for r in self.editor.database.document.get('wall_squares',{}).get(str(self.editor.current_map),[])]
  w=self.grid_width;elev=self.elevation_enabled();n=0;data=self.editor.session.data;done=set()
  for col,srow,target in squares:
   if not 0<=col<w:continue
   for t in range(self.grid_height):
    c=self.grid_cells[t*w+col];v=c['values']
    if t-(v[3] if elev else 0)!=srow or (col,t) in done:continue
    done.add((col,t))   # each tile once: once raised it lands on another square
    if elev and v[3]!=target and 0<=target<=255:
     d=target-v[3];floor=t-v[3]
     pieces={row-floor+d:cd for row,cd,f in self.record_pieces(c) if not f}
     clash=v[4]!=0xFFFF and d in pieces   # a piece already on its floor's square: keep as it is
     if v[4]!=0xFFFF:pieces[d]=v[4]   # the floor picture stays on its square as a piece
     walls=False if clash else self.rebased_walls(pieces)
     if walls is not False:
      old=self.tile_rows(col,t)
      for i,b in ((3,target),(4,0xFF),(5,0xFF)):
       at=c['offset']+i
       if data[at]==b:self.pending_heights.pop(at,None)
       else:self.pending_heights[at]=b
      c['values']=v[:3]+(target,0xFFFF)+v[5:]
      g=self.stack_grid();sc=g[2][t*w+col];sv=list(sc['values']);sv[3]=target;sv[4]=0xFFFF;sc['values']=tuple(sv)
      if pieces or c['walls']:self.set_cell_walls(col,t,walls)
      self.redraw_columns([(col,t)],before={(col,t):old});n+=1
    if (self.grid_cells[t*w+col]['values'][0]&0x41)!=0x41:self.set_walk(col,t,True,bits=0x41);n+=1
  return n
 def set_walk(self,tx,ty,blocked,bits=None):
  """Make one tile no-walk (red x) or walkable, kept with the height edits."""
  e=self.editor;c=self.grid_cells[ty*self.grid_width+tx];data=e.session.data;at=c["offset"]
  walk=((c["values"][0]&~0x41)|(bits or self.block_bits())) if blocked else (c["values"][0]&~0x41)
  if walk==data[at]:self.pending_heights.pop(at,None)
  else:self.pending_heights[at]=walk
  v=list(c["values"]);v[0]=walk;c["values"]=tuple(v);self.sync_stack_walk(tx,ty,walk)
  walled=e.database.document.setdefault('walled_tiles',{}).setdefault(str(e.current_map),[])
  if blocked and [tx,ty] not in walled:walled.append([tx,ty])
  if not blocked and [tx,ty] in walled:walled.remove([tx,ty])
  e.dirty=True
 def toggle_mask(self,event):
  import struct
  x,y=self.canvas.canvasx(event.x),self.canvas_y(event);e=self.editor;w=self.grid_width
  hits=self.renderer.surface_hits.get((int(x)//24,int(y)//16),[])
  hit=next((h for h in reversed(hits) if h[5]!=0xFFFF and self.renderer.tile(h[5]).getpixel((int(x-h[0]),int(y-h[1])))[3]),None)
  if hit is None:hit=next((h for h in reversed(hits) if h[5]!=0xFFFF),None)
  if hit is None:self.caption.set("Nothing drawn here to mask.");return
  px,py,tx,ty,layer,code=hit
  stars=e.database.document.setdefault('masked_tiles',{}).setdefault(str(e.current_map),[])
  entry=next((r for r in stars if isinstance(r,dict) and r['mask']==[tx,ty]),None)
  def set_floor(cx,cy,new_code,height=None,walk=None):
   c=self.grid_cells[cy*w+cx];old=self.tile_rows(cx,cy)
   v=list(c["values"])
   if height is not None:v[3]=height
   if walk is not None:v[0]=walk;self.pending_tiles[c["offset"]]=bytes((walk,))
   v[4]=new_code;c["values"]=tuple(v)
   self.pending_tiles[c["offset"]+3]=struct.pack("<BH",v[3],new_code)
   self.redraw_columns([(cx,cy)],before={(cx,cy):old})
  def set_wall(cx,cy,index,new_code):
   c=self.grid_cells[cy*w+cx];old=self.tile_rows(cx,cy)
   offset,_,shift,i=c["walls"][index]
   if offset is None:
    g=self.stack_grid();sc=g[2][cy*w+cx];sh,codes=sc['walls'];codes=list(codes);codes[index]=new_code;sc['walls']=(sh,codes);self.pending_stack_tiles.add((cx,cy))
   else:self.pending_tiles[offset]=struct.pack("<H",new_code)
   c["walls"][index]=(offset,new_code,shift,i)
   self.redraw_columns([(cx,cy)],before={(cx,cy):old})
  if entry is not None:
   # put it back where it came from
   ox,oy,olayer=entry['origin']
   if olayer=="Floor":set_floor(ox,oy,entry['code'])
   else:set_wall(ox,oy,int(olayer.split()[1]),entry['code'])
   set_floor(tx,ty,0xFFFF)
   stars.remove(entry);e.dirty=True;self.draw_mask_stars()
   self.caption.set(f"Tile picture back on its own tile ({ox}, {oy}); no longer in front of the player.");return
  # mask: an unused tile further down this column draws the picture in the same square
  target=self.empty_square_hit(px+12,py+8,min_row=ty+1,allow_front=True)   # Mask layer: in front of him on purpose
  if target is None:self.caption.set("No unused tile further down this column to draw the mask with.");return
  _,_,bx,by,_,_=target
  b=self.grid_cells[by*w+bx]
  set_floor(bx,by,code)   # only the picture moves
  if b["values"][0]&1 and not self.grid_cells[ty*w+tx]["values"][0]&1:self.set_walk(bx,by,False)   # a mask is never a wall (x)
  if layer=="Floor":set_floor(tx,ty,0xFFFF)
  else:set_wall(tx,ty,int(layer.split()[1]),0xFFFF)
  stars.append({'mask':[bx,by],'origin':[tx,ty,layer],'code':code});e.dirty=True
  self.draw_mask_stars()
  self.caption.set(f"Tile picture is now drawn in front of the player (★). Click the ★ to put it back.")
 def draw_mask_stars(self):
  """★ on every square drawn by a mask layer (in front of the player)."""
  if not hasattr(self,'canvas'):return
  self.canvas.delete('mask_star')
  if not self.mask_layer.get():return   # stars only while Mask layer is ticked
  stars=self.editor.database.document.get('masked_tiles',{}).get(str(getattr(self.editor,'current_map','')),[])
  crop=getattr(self,'map_crop_top',0);elev=self.elevation_enabled();w=getattr(self,'grid_width',0)
  for row in stars:
   tx,ty=row['mask'] if isinstance(row,dict) else row
   if not (0<=tx<w and 0<=ty<getattr(self,'grid_height',0)):continue
   c=self.grid_cells[ty*w+tx]
   if c["values"][4]==0xFFFF:continue   # removed since
   py=ty*16+self.margin-(c["values"][3]*16 if elev else 0)
   vy=map_y_to_view(py,crop)
   for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
    self.canvas.create_text(tx*24+12+dx,vy+8+dy,text='\u2605',fill='black',font=('Segoe UI',9),anchor='center',tags='mask_star')
   self.canvas.create_text(tx*24+12,vy+8,text='\u2605',fill='#ffe066',font=('Segoe UI',9),anchor='center',tags='mask_star')
 def floor_slot_taken(self,tx,ty):
  """True when this tile already has a picture lying on its floor (a curtain,
  rug or other background piece) that a floor layer would replace."""
  g=getattr(self,'pending_stack_grid',None)
  walls=g[2][ty*self.grid_width+tx]['walls'] if g is not None else (
   (self.grid_cells[ty*self.grid_width+tx]['walls'][0][2],[x[1] for x in self.grid_cells[ty*self.grid_width+tx]['walls']]) if self.grid_cells[ty*self.grid_width+tx]['walls'] else None)
  if not walls:return False
  shift,codes=walls
  return 1<=shift<=len(codes) and codes[shift-1]!=0xFFFF
 def layer_on_square(self,event):
  """Layer on floor: the picture goes on top of exactly the square you click.
  If that square's tile already has a piece on its floor (a curtain or other
  background object), the layer is drawn by an unused tile set to land in the
  same square in front of it, so the curtain stays and the layer is on top."""
  x,y=self.canvas.canvasx(event.x),self.canvas_y(event);sq=(int(x)//24,int(y)//16)
  if sq in getattr(self,'layered_squares',set()):return
  self.layered_squares=getattr(self,'layered_squares',set());self.layered_squares.add(sq)
  hits=self.renderer.surface_hits.get(sq,[])
  floor=[h for h in hits if h[4]=="Floor" and h[5]!=0xFFFF]
  code=self.stack_brush()[0]['code']
  mask=False   # masking is its own mode now (Mask layer on the toolbar)
  # Pictures are drawn row by row: a tile further down the map drawn on this square
  # (a wall piece of a raised or moved tile) covers anything laid on an earlier one,
  # so the layer goes on the front-most tile's floor, or on an unused tile drawn after it.
  front_row=max((h[3] for h in hits if h[5]!=0xFFFF),default=-1)
  if floor and floor[-1][3]<front_row:floor=[]
  if floor and not mask and not self.floor_slot_taken(*floor[-1][2:4]):
   tile=floor[-1][2:4]
   if tile not in self.bush_stroke:self.bush_stroke.append(tile)
   vy=map_y_to_view(floor[-1][1],getattr(self,'map_crop_top',0))
   self.canvas.create_rectangle(sq[0]*24,vy,sq[0]*24+24,vy+16,outline="#7dff8a",width=2,tags="bush_stroke");return
  # A piece is drawn over a character when its tile's map row is at or below
  # the character's row. A mask layer is owned by an unused tile further down
  # this column, so it covers the player standing on or behind this spot.
  if front_row>=0 and not mask and self.layer_on_owner(hits,code):return   # the picture joins the tile you picked (user 2026-10-25)
  below=(floor[-1][3]+1) if (mask and floor) else front_row+1
  self.layer_with_free_tile(x,y,code,below,mask)
 def layer_on_owner(self,hits,code):
  """The picked square's own tile (the front-most one drawn there) gets the picture as
  one of its pieces, so it is drawn at that tile's depth. False if that row is taken."""
  drawn=[h for h in hits if h[5]!=0xFFFF]
  if not drawn:return False
  hit=drawn[-1];sr=int(hit[1]-self.margin)//16   # the square's screen row
  # Owner (user 2026-10-25): a tile the game does not draw over Alundra, on which the
  # picture lands exactly on top of what is there (no_mask.choose_owner).
  if not self.elevation_enabled():return False
  from no_mask import choose_owner
  w=self.grid_width;tx=hit[2]
  cells=[{'values':c['values'],'walls':((c['walls'][0][2],[k[1] for k in c['walls']]) if c['walls'] else None)} for c in self.grid_cells]
  pick=choose_owner(self.renderer,cells,w,self.grid_height,self.margin,tx,sr,code)
  if pick is None:return False   # no tile behind him fits: placed the usual way instead (user 2026-10-25: always place)
  ty,walls=pick
  old=self.tile_rows(tx,ty);self.set_cell_walls(tx,ty,walls)
  self.redraw_columns([(tx,ty)],before={(tx,ty):old})
  return True
 def layer_with_free_tile(self,x,y,code,below=0,mask=False,no_walk=True):
  """Draw code on top of the square at (x,y) with an unused tile of this column."""
  hit=self.empty_square_hit(x,y,min_row=below)
  if hit is None:
   if not getattr(self,'_unsafe_square',False):self.caption.set("No room to layer here: no unused tile in this column.")
   return False
  import struct
  _,_,tx,ty,_,_=hit;c=self.grid_cells[ty*self.grid_width+tx];old=self.tile_rows(tx,ty)
  walk=c["values"][0]|1 if no_walk else c["values"][0]   # a picture only: nobody walks on it (stamps leave walking alone)
  self.pending_tiles[c["offset"]]=bytes((walk,))
  self.pending_tiles[c["offset"]+3]=struct.pack("<BH",c["values"][3],code)
  v=list(c["values"]);v[0]=walk;v[4]=code;c["values"]=tuple(v)
  if mask:
   stars=self.editor.database.document.setdefault('masked_tiles',{}).setdefault(str(self.editor.current_map),[])
   if [tx,ty] not in stars:stars.append([tx,ty])
   self.editor.dirty=True
  self.redraw_columns([(tx,ty)],before={(tx,ty):old})
  self.draw_mask_stars()
  return True
 def bush_stroke_add(self,event):
  sb=self.stack_brush()
  if sb is not None and sb[0].get('kind')=='layer':return self.layer_on_square(event)
  tile=self.fill_tile(event)
  if tile is None or tile in self.bush_stroke:return
  self.bush_stroke.append(tile);x,y=tile
  height=self.grid_cells[y*self.grid_width+x]['values'][3] if self.elevation_enabled() else 0
  py=map_y_to_view(y*16+self.margin-height*16,getattr(self,'map_crop_top',0))
  self.canvas.create_rectangle(x*24,py,x*24+24,py+16,outline="#7dff8a",width=2,tags="bush_stroke")
 # -- wall-stack edits (bushes, walls, floor layers): shown now, written at save/build
 def stack_grid(self):
  """The map's cells with the waiting wall-stack edits (map_area_copy.cells_of rows)."""
  if getattr(self,'pending_stack_grid',None) is None:
   from map_area_copy import cells_of
   self.pending_stack_grid=cells_of(self.editor.session,self.editor.current_map);self.pending_stack_tiles=set()
   self.pending_stack_key=(self.editor.session,self.editor.current_map)
  return self.pending_stack_grid
 def update_renderer_textures(self):
  """New tile pictures were imported (waiting texture): draw with them, keep the map's hit areas."""
  e=self.editor
  if self.renderer.raw is not e.session.texture(e.current_map)[0]:
   hits=self.renderer.surface_hits;self.renderer=MapRenderer(e.session,e.current_map);self.renderer.surface_hits=hits
 def stack_edit(self,tiles,edit):
  """Run edit(grid) on the waiting cells and draw the changed tiles again."""
  from area_map import piece_rows
  w,h,cells=grid=self.stack_grid()
  before={t:piece_rows(cells[t[1]*w+t[0]],t[1],self.margin,self.elevation_enabled()) for t in tiles if 0<=t[0]<w and 0<=t[1]<h}
  n=edit(grid)
  if n:
   self.pending_stack_tiles.update(before)
   self.update_renderer_textures()
   for (x,y),(top,bottom) in before.items():
    after=piece_rows(cells[y*w+x],y,self.margin,self.elevation_enabled())
    self.preview_region((x*24,min(top,after[0]),x*24+24,max(bottom,after[1])))
   self.editor.dirty=True;self.schedule_texture_flush()
  return n
 def preview_region(self,rect):
  from area_map import render_region
  w,h,cells=self.pending_stack_grid
  left,top,right,bottom=rect;top=max(0,top)
  if bottom<=top:return
  image=render_region(self.renderer,cells,w,self.margin,(left,top,right,bottom),self.elevation_enabled())
  photo=ImageTk.PhotoImage(image,master=self.editor.root);self.paint_photos.append(photo)
  self.canvas.create_image(left,map_y_to_view(top,getattr(self,'map_crop_top',0)),image=photo,anchor='nw',tags='paint_preview')
  self.canvas.tag_raise('record');self.canvas.tag_raise('start_point')
  self.merge_paint_previews()
 def merge_paint_previews(self,limit=300):
  """Big copies/paint drags: thousands of stacked preview images crashed the editor.
  Past the limit, draw the whole map once from the waiting cells and free the previews."""
  if len(self.paint_photos)<=limit:return
  from area_map import render_region,view_y_to_map
  pending=getattr(self,'pending_stack_grid',None)
  if pending is not None:w,_,cells=pending
  else:
   w=self.grid_width
   cells=[{'values':c['values'],'walls':((c['walls'][0][2],[x[1] for x in c['walls']]) if c['walls'] else None)} for c in self.grid_cells]
  width,height=self.photo.width(),self.photo.height();top=view_y_to_map(0,getattr(self,'map_crop_top',0))
  image=render_region(self.renderer,cells,w,self.margin,(0,top,width,top+height),self.elevation_enabled())
  self.photo=ImageTk.PhotoImage(image,master=self.editor.root)
  self.canvas.delete('paint_preview');self.paint_photos=[]
  base=self.canvas.find_withtag('base_map')
  if base:self.canvas.itemconfigure(base[0],image=self.photo)
  else:
   self.canvas.create_image(0,0,image=self.photo,anchor='nw',tags='base_map');self.canvas.tag_lower('base_map')
 def commit_stacks(self):
  """Write the waiting wall-stack edits (one undo step) into the map as it is now."""
  pending=getattr(self,'pending_stack_grid',None)
  if pending is None:return False
  tiles=self.pending_stack_tiles;self.pending_stack_grid=None;self.pending_stack_tiles=set()
  water=getattr(self,'pending_water_tiles',set());self.pending_water_tiles=set()
  objects=getattr(self,'pending_object_tiles',set());self.pending_object_tiles=set()
  if not tiles or getattr(self,'pending_stack_key',None)!=(self.editor.session,self.editor.current_map):return False
  from map_area_copy import cells_of,rebuild_grid
  w,h,cells=pending;_,_,fresh=cells_of(self.editor.session,self.editor.current_map)
  for x,y in tiles:
   new=cells[y*w+x];cell=fresh[y*w+x]
   values=list(cell['values']);values[0]=new['values'][0]
   if (x,y) in water:   # water: picture, ground and slope too
    values[1],values[2],values[4]=new['values'][1],new['values'][2],new['values'][4]
   if (x,y) in objects:   # map objects: everything, heights too
    values=list(new['values'])
   cell['values']=tuple(values);cell['walls']=new['walls']
  rebuild_grid(self.editor.session,self.editor.current_map,fresh,f"Bushes / walls / layers on {len(tiles)} tile(s)")
  self.editor.dirty=True
  return True
 def place_bush_stroke(self):
  tiles=self.bush_stroke or [];self.bush_stroke=None;self.canvas.delete("bush_stroke");self.layered_squares=set()
  brush=self.stack_brush()
  if not tiles or brush is None:return
  from bush_catalogue import place_bush,place_face,place_layer,place_walls
  style,name=brush;e=self.editor
  if style.get('kind')=='map_object':
   from map_object_catalogue import place_object
   anchor=tiles[0];obj=style['object']
   left=min(r[0] for r in obj['rows']);bottom=max(r[1] for r in obj['rows'])   # the clicked tile is its bottom-left corner
   footprint=[(anchor[0]+dx-left,anchor[1]+dy-bottom) for dx,dy,_,_ in obj['rows']]
   footprint=[(x,y) for x,y in footprint if 0<=x<self.grid_width and 0<=y<self.grid_height]
   placed=[]
   def edit(g):
    placed[:]=place_object(e.session,e.database,e.current_map,anchor,obj,g,layer=self.layer_floor.get())
    if placed:
     if not hasattr(self,'pending_object_tiles'):self.pending_object_tiles=set()
     self.pending_object_tiles.update(placed)
     for x,y in placed:   # the shown grid follows (height numbers, x marks)
      self.grid_cells[y*self.grid_width+x]['values']=tuple(g[2][y*self.grid_width+x]['values'])
    return len(placed)
   n=self.stack_edit(footprint,edit)
   self.caption.set(f"Placed {name} at tile {anchor[0]}, {anchor[1]} ({n} tiles). Undo takes it off.")
   if obj.get('warp_panel') and n:
    self.commit_pending()   # the panel is in the map; the warp goes on top of it
    from map_object_catalogue import panel_top_left,WARP_PANEL_FLAGS
    x0,y0=panel_top_left(obj,anchor);source_map=e.current_map;session=e.session
    def create(map_id,x,y,z):
     if e.session is not session or e.current_map!=source_map:raise ValueError('The map changed; place the Warp Panel again')
     from warp_editor import add_warp
     index=add_warp(session,source_map,x0,y0,map_id,x,y,z or 0,flags=WARP_PANEL_FLAGS,width=2,height=2,warp_square=True)
     e.dirty=True;self.show_warps.set(True);self.refresh(reload_textures=False)
     self.caption.set(f"Warp Panel at tile {x0}, {y0}: warp {index} leads to map {map_id}, tile {x}, {y}. Undo takes the warp off, then the panel.")
    def ask():
     from map_tile_picker import MapTileDialog
     MapTileDialog(e,e.root,lambda m,x,y,z:e.guard(lambda:create(m,x,y,z)),map_id=source_map,title='Warp Panel: Choose Where It Leads',confirm='Create Warp')
    e.root.after(50,lambda:e.guard(ask))
   return
  if style.get('kind')=='layer':edit=lambda g:place_layer(e.session,e.current_map,tiles,style['code'],grid=g)
  elif style.get('kind')=='face':edit=lambda g:place_face(e.session,e.current_map,tiles,style['code'],grid=g)
  elif style.get('kind') in ('water_floors','water_stairs','stairs','liquid'):
   from water_catalogue import place_water
   from liquid_catalogue import place_liquid
   def edit(g):
    n=(place_liquid if style.get('kind')=='liquid' else place_water)(e.session,e.database,e.current_map,tiles,style,grid=g)
    if n:
     if not hasattr(self,'pending_water_tiles'):self.pending_water_tiles=set()
     self.pending_water_tiles.update(tiles)
     for x,y in tiles:   # the shown grid follows (height numbers, x marks)
      if 0<=x<self.grid_width and 0<=y<self.grid_height:
       c=self.grid_cells[y*self.grid_width+x];nv=g[2][y*self.grid_width+x]['values'];v=list(c['values'])
       v[0],v[1],v[2],v[4]=nv[0],nv[1],nv[2],nv[4];c['values']=tuple(v)
    return n
  else:
   place=place_walls if style.get('kind')=='walls' else place_bush
   edit=lambda g:place(e.session,e.database,e.current_map,tiles,style,grid=g)
  n=self.stack_edit(tiles,edit)
  self.caption.set(f"{'Placed' if style.get('kind') in ('walls','layer','face','water_floors','water_stairs','stairs','liquid') else 'Planted'} {name} on {n} tile(s). Shown now; written to the map when you save or build.")
 def remove_bush_at(self,event):
  tile=self.fill_tile(event)
  if tile is None:return
  from bush_catalogue import remove_bush,remove_face,remove_layer,remove_walls
  kind=self.stack_brush()[0].get('kind','bush')
  if kind=='map_object':
   self.caption.set("A placed map object is taken off with Undo.");return
  if kind in ('water_floors','water_stairs','stairs','liquid'):
   self.caption.set("This is a floor tile: use No tile (erase) or paint another floor to replace it.");return
  remove,what={'walls':(remove_walls,'walls'),'layer':(remove_layer,'floor layer'),'face':(remove_face,'wall tile below the floor')}.get(kind,(remove_bush,'bush'))
  if self.stack_edit([tile],lambda g:remove(self.editor.session,self.editor.current_map,[tile],grid=g)):
   self.caption.set(f"{what.capitalize()} removed from tile {tile[0]}, {tile[1]}. Written to the map when you save or build.")
  else:self.caption.set(f"Tile {tile[0]}, {tile[1]} has no {what}.")
 def draw_height_numbers(self):
  """Height edit keeps the map picture as it is (tiles do not jump while you
  click) and writes one height in each grid square: when raised tiles make
  several tiles meet in one square, the lowest one is shown and edited."""
  return self.redraw_height_numbers_from_grid()   # normal + mask heights, from the grid
  self.canvas.delete("height_number");self.canvas.delete("height_hover");self.height_hover_tile=None
  crop=getattr(self,'map_crop_top',0)
  floor={};squares={}
  for px,py,tx,ty in self.hits:
   if not (0<=tx<self.grid_width and 0<=ty<self.grid_height):continue
   floor[(tx,ty)]=(px,py);squares.setdefault((px,py),[]).append((tx,ty))
  self.height_floor=floor;self.height_stack={}
  height=lambda t:self.grid_cells[t[1]*self.grid_width+t[0]]["values"][3]
  for (px,py),tiles in squares.items():
   # lowest height wins; on a tie the tile drawn last (in front)
   top=max(enumerate(tiles),key=lambda item:(-height(item[1]),item[0]))[1]
   self.height_stack[(px,py)]=top
   blocked=self.grid_cells[top[1]*self.grid_width+top[0]]["values"][0]&1   # no-walk: red x
   self.canvas.create_text(px+12,map_y_to_view(py+8,crop),text="x" if blocked else str(height(top)),fill="#ff5c5c" if blocked else "#58aaff",
                           font=("Segoe UI",8,"bold"),tags=("height_number",f"hn_{top[0]}_{top[1]}"))
 def redraw_columns(self,tiles,before=None):
  """Draw the given tiles' columns again from the grid as it is now (heights
  and paint not yet written included), so changes show at once."""
  from area_map import render_region,piece_rows
  if not hasattr(self,'renderer'):return
  w=self.grid_width;elev=self.elevation_enabled()
  cells=[{'values':c['values'],'walls':((c['walls'][0][2],[x[1] for x in c['walls']]) if c['walls'] else None)} for c in self.grid_cells]
  crop=getattr(self,'map_crop_top',0)
  for (x,y) in tiles:
   top,bottom=piece_rows(cells[y*w+x],y,self.margin,elev)
   if before and (x,y) in before:top=min(top,before[(x,y)][0]);bottom=max(bottom,before[(x,y)][1])
   top=max(0,top-16);bottom+=16
   image=render_region(self.renderer,cells,w,self.margin,(x*24,top,x*24+24,bottom),elev)
   photo=ImageTk.PhotoImage(image,master=self.editor.root);self.paint_photos.append(photo)
   self.canvas.create_image(x*24,map_y_to_view(top,crop),image=photo,anchor='nw',tags='paint_preview')
  self.merge_paint_previews()
  for tag in ('record','start_point','selection','height_number','height_hover','group_footprint'):self.canvas.tag_raise(tag)
  self.rebuild_surface_hits()
 def paint_target(self,x,y):
  """The piece drawn in the square under (x,y), for painting: the visible
  (opaque) piece in front, else the front-most wall piece there, else a real
  floor tile drawn there, else empty ground drawn there, else an unused tile
  moved to draw there. Painting it changes only that square's picture."""
  hits=self.renderer.surface_hits.get((int(x)//24,int(y)//16),[])
  for h in reversed(hits):
   if h[5]!=0xFFFF and self.renderer.tile(h[5]).getpixel((int(x-h[0]),int(y-h[1])))[3]:return h
  walls=[h for h in hits if h[4]!="Floor"]
  if walls:return walls[-1]
  floors=[h for h in hits if h[4]=="Floor"]
  real=[h for h in floors if h[5]!=0xFFFF]
  if real:return real[-1]
  if floors and self.brush in (None,0xFFFF):return floors[-1]
  if self.brush not in (None,0xFFFF):
   # Empty ground: use the empty tile that lands here at the height of the
   # floor beside it (a gap in a floor of 2s is filled at 2), else the empty
   # ground already drawn here (keeps its height), else any empty tile.
   matched=self.empty_square_hit(x,y,require_match=True)
   if matched:return matched
  if floors:return floors[-1]
  return self.empty_square_hit(x,y) if self.brush not in (None,0xFFFF) else None
 def stamp_group_on_screen(self,x,y):
  """Group brush: each tile goes on the square it covers on screen, onto
  whatever is drawn there (floor, wall piece or empty ground). Nothing moves."""
  bx=int(x)//24*24;by=int(y)//16*16;keep=self.brush;keep_wall=getattr(self,'brush_is_wall',False);done=0
  try:
   under=getattr(self,'group_under',{})
   for (dx,dy),code in self.group_brush.items():
    sx,sy=bx+dx*24+12,by+dy*16+8
    pieces=under.get((dx,dy),[])+[(code,(dx,dy) in getattr(self,'group_walls',set()))]   # bottom piece first
    for i,(piece,is_wall) in enumerate(pieces):
     self.brush=piece;self.brush_is_wall=is_wall
     if i:   # pieces above the bottom one go on top of it, not over it
      done+=bool(self.layer_with_free_tile(sx,sy,piece,no_walk=False));continue
     hit=self.paint_target(sx,sy)
     if hit is None:continue
     _,_,tx,ty,layer,_=hit
     if not(0<=tx<self.grid_width and 0<=ty<self.grid_height):continue
     self.wall.set(layer);self.select(tx,ty);self.paint_single(repaint=False);done+=1
  finally:self.brush=keep;self.brush_is_wall=keep_wall
  self.caption.set(f"Stamped {done} tile(s) where shown; heights unchanged. Written to the map when you save or build.")
 def empty_square_hit(self,x,y,min_row=0,require_match=False,allow_front=False):
  """Paint on a square where nothing is drawn: use the nearest empty tile
  below it in the same column and give it the height that draws it exactly
  in that square (the picture lands where you clicked)."""
  tx=int(x)//24;row_y=int(y)//16*16
  if not 0<=tx<self.grid_width:return None
  elev=self.elevation_enabled()
  # Prefer the empty tile that lands here at the same height as the tiles
  # beside it (so a gap in a floor of 2s is filled at 2, not at whatever
  # height the next empty tile down would need).
  order=list(range(max(0,min_row),self.grid_height))
  if elev:
   def side_heights(ty):
    hs=[]
    for dx in (-1,1):
     if 0<=tx+dx<self.grid_width:
      v=self.grid_cells[ty*self.grid_width+tx+dx]["values"]
      if v[4]!=0xFFFF:hs.append(v[3])
    return hs
   matching=[ty for ty in order if (ty*16+self.margin-row_y)//16 in side_heights(ty) and (ty*16+self.margin-row_y)%16==0]
   order=matching if require_match else matching+[ty for ty in order if ty not in matching]
  elif require_match:return None
  # Never borrow a tile further down the map than a spot where Alundra stands in front
  # of this square: the game would draw the picture over him (user 2026-10-25).
  from no_mask import covered
  w=self.grid_width;sr=(row_y-self.margin)//16
  walk=[(q,q-self.grid_cells[q*w+tx]['values'][3],self.grid_cells[q*w+tx]['values'][3]) for q in range(self.grid_height)
        if not self.grid_cells[q*w+tx]['values'][0]&1 and self.grid_cells[q*w+tx]['values'][4]!=0xFFFF]
  unsafe=False;fallback=None
  for ty in order:
   c=self.grid_cells[ty*self.grid_width+tx]
   if c["values"][4]!=0xFFFF or c["walls"]:continue
   need=(ty*16+self.margin-row_y)//16 if elev else 0
   if not elev and ty*16+self.margin!=row_y:continue
   if not 0<=need<=255:continue
   if elev and not allow_front and covered(walk,ty,need,sr,('floor',)):
    unsafe=True
    if fallback is None:fallback=ty   # used only when no tile behind him is free: always place
    continue
   import struct
   data=self.editor.session.data;o=c["offset"]+3
   if need!=data[o]:self.pending_heights[o]=need
   else:self.pending_heights.pop(o,None)
   v=list(c["values"]);v[3]=need;c["values"]=tuple(v)
   return (tx*24,row_y,tx,ty,"Floor",0xFFFF)
  self._unsafe_square=False
  if fallback is not None:   # nothing behind him was free: place it anyway (user 2026-10-25: always place)
   c=self.grid_cells[fallback*self.grid_width+tx];need=(fallback*16+self.margin-row_y)//16
   data=self.editor.session.data;o=c["offset"]+3
   if need!=data[o]:self.pending_heights[o]=need
   else:self.pending_heights.pop(o,None)
   v=list(c["values"]);v[3]=need;c["values"]=tuple(v)
   return (tx*24,row_y,tx,fallback,"Floor",0xFFFF)
  return None
 def raise_empties(self,tx,ty,new_height,delta):
  """+1 / -1 only: a tile raised into the square above it covers that square, so
  the floor that was drawn there is emptied (no picture: it becomes part of the
  raised tile's wall, shown with the raised tile's height). -1 gives the last
  emptied floor back."""
  import struct
  e=self.editor;w=self.grid_width;data=e.session.data
  log=e.database.document.setdefault('raise_emptied',{}).setdefault(str(e.current_map),{})
  key=f'{tx},{ty}';done=log.setdefault(key,[])
  def put(o,code,height):
   c=self.grid_cells[o[1]*w+o[0]];old=self.tile_rows(o[0],o[1])
   for i,b in ((3,height),(4,code&0xFF),(5,code>>8)):
    at=c["offset"]+i
    if data[at]==b:self.pending_heights.pop(at,None)
    else:self.pending_heights[at]=b
   v=list(c["values"]);v[3]=height;v[4]=code;c["values"]=tuple(v)
   g=getattr(self,'pending_stack_grid',None)
   if g is not None:sc=g[2][o[1]*w+o[0]];sv=list(sc['values']);sv[3]=height;sv[4]=code;sc['values']=tuple(sv)
   self.redraw_columns([o],before={o:old})
  if delta>0:
   square=(tx*24,ty*16+self.margin-(new_height*16 if self.elevation_enabled() else 0))
   other=getattr(self,'height_stack',{}).get(square)
   if other is None or tuple(other)==(tx,ty):return
   oc=self.grid_cells[other[1]*w+other[0]]
   if oc["values"][4]==0xFFFF:return
   done.append([other[0],other[1],oc["values"][4],oc["values"][3]]);put(tuple(other),0xFFFF,new_height)   # empty, at the wall top's height
   for r in done:   # every square already emptied under it rises with the wall top
    if r is not done[-1]:put((r[0],r[1]),0xFFFF,new_height)
  elif done:
   ox,oy,code,old_h=(done.pop()+[None])[:4]
   put((ox,oy),code,old_h if old_h is not None else self.grid_cells[oy*w+ox]["values"][3])
   for r in done:put((r[0],r[1]),0xFFFF,new_height)
  if not done:log.pop(key,None)
  e.dirty=True
 def step_face(self,tx,ty,delta):
  """+1 / -1: keep the pillar built right while the tile's picture shifts.
  +1: the tile goes up a square; the square it leaves gets its picture as a face
  piece (a wall piece of this tile, so it is drawn in front of anyone behind it).
  A copy of its picture already on the square it moves into is covered by the
  tile itself and goes. -1: the tile goes down a square; the face piece it moves
  onto goes, or, when it has none (going below where it started), its picture is
  kept on the square it left. Works whatever wall pieces the tile already has."""
  c=self.grid_cells[ty*self.grid_width+tx];code=c["values"][4]
  if code==0xFFFF or not self.elevation_enabled():return
  e=self.editor;g=self.stack_grid();sc=g[2][ty*self.grid_width+tx]
  floor=ty-c["values"][3]   # step_face runs before the new height is stored
  pieces={row:cd for row,cd,is_floor in self.record_pieces(c) if not is_floor}
  if delta>0:
   new_floor=floor-1
   if pieces.get(new_floor)==code:pieces.pop(new_floor)
   if floor not in pieces:pieces[floor]=code
  else:
   new_floor=floor+1
   if pieces.get(new_floor)==code:pieces.pop(new_floor)
   elif floor not in pieces:pieces[floor]=code
  walls=self.rebased_walls({r-new_floor:cd for r,cd in pieces.items()})
  if walls is False:self.caption.set(f"Tile {tx}, {ty}: its wall pieces reach too far to keep in step.");return
  sc['walls']=(walls[0],list(walls[1])) if walls else None
  c["walls"]=[(None,cd,walls[0],i) for i,cd in enumerate(walls[1])] if walls else []
  self.pending_stack_tiles.add((tx,ty));e.dirty=True
  faces=e.database.document.setdefault('step_faces',{}).setdefault(str(e.current_map),[])
  if [tx,ty] not in faces:faces.append([tx,ty])
 def rebuild_surface_hits(self):
  """Clicks find tiles where they are drawn now: after a height change or
  paint the hit areas are worked out again from the grid, exactly as a full
  redraw would, so painting/picking works the same before and after."""
  elev=self.elevation_enabled();hits={}
  for c in self.grid_cells:
   v=c["values"];x=c["x"]*24;y=c["y"]*16+self.margin-(v[3]*16 if elev else 0)
   hits.setdefault((x//24,y//16),[]).append((x,y,c["x"],c["y"],"Floor",v[4]))
   if elev:
    for _,code,shift,i in c["walls"]:
     wy=y+(i+1-shift)*16;hits.setdefault((x//24,wy//16),[]).append((x,wy,c["x"],c["y"],f"Wall {i}",code))
  self.renderer.surface_hits=hits
 def tile_rows(self,x,y):
  from area_map import piece_rows
  c=self.grid_cells[y*self.grid_width+x]
  return piece_rows({'values':c['values'],'walls':((c['walls'][0][2],[0]*len(c['walls'])) if c['walls'] else None)},y,self.margin,self.elevation_enabled())
 def redraw_height_numbers_from_grid(self):
  """Draw the height numbers / x's the way Alundra really walks (walk-behind floor,
  x where his feet stop), but keep which tile each square selects for editing
  exactly as the original selection code works it out."""
  if hasattr(self,'canvas'):self.canvas.after_idle(lambda:self.editor.guard(self.draw_buggy_tiles))   # Buggy tiles view marks, on top
  if hasattr(self,'canvas'):self.canvas.after_idle(lambda:self.editor.guard(self.draw_layer_view))   # Layer 1-10 view, on top
  # Tiles whose picture Draw behind him moved off count as drawn here, so their square keeps
  # their height number (user 2026-10-25): the number views see them with a picture.
  kept=(getattr(self,'kept_squares',None) or (lambda:set()))();cells_real=self.grid_cells
  if kept:
   view=[]
   for c in cells_real:
    if (c["x"],c["y"]) in kept and c["values"][4]==0xFFFF:
     c=dict(c);v=list(c["values"]);v[4]=0;c["values"]=tuple(v)
    view.append(c)
   self.grid_cells=view
  try:
   self._redraw_height_display()
   shown={k:getattr(self,k,None) for k in ('height_hover_tile',)}
   real=self.canvas
   class _Quiet:
    def __getattr__(s,n):return getattr(real,n) if n in ('find_withtag','canvasx','canvasy','winfo_width','winfo_height','bbox','coords') else (lambda *a,**k:None)
   self.canvas=_Quiet()
   try:self._redraw_height_select()
   finally:self.canvas=real
  finally:self.grid_cells=cells_real
 def _redraw_height_select(self):
  """Show every square's height at once after a change (no map re-render):
  a tile is drawn at its row minus its height, so the number squares are
  worked out from the grid as it is now, including changes not yet written."""
  self.canvas.delete("height_number");self.canvas.delete("height_hover");self.height_hover_tile=None
  crop=getattr(self,'map_crop_top',0);elev=self.elevation_enabled()
  floor={};squares={}
  mask_origins={tuple(r['origin'][:2]) for r in self.editor.database.document.get('masked_tiles',{}).get(str(self.editor.current_map),[]) if isinstance(r,dict)}|(getattr(self,'kept_squares',None) or (lambda:set()))()
  for c in self.grid_cells:
   v=c["values"]
   if v[4]==0xFFFF and not c["walls"] and (c["x"],c["y"]) not in mask_origins:continue   # empty ground: nothing drawn, no number (a masked tile's own record still counts)
   px=c["x"]*24;py=c["y"]*16+self.margin-(v[3]*16 if elev else 0)
   floor[(c["x"],c["y"])]=(px,py);squares.setdefault((px,py),[]).append((c["x"],c["y"]))
  arrows=set()   # squares with no height of their own: grey up arrow, not editable
  for (px,py),tiles in squares.items():
   if all(self.grid_cells[ty*self.grid_width+tx]["values"][4]==0xFFFF and self.grid_cells[ty*self.grid_width+tx]["walls"] for tx,ty in tiles):arrows.add((px,py))
  # Fill the squares no floor lands in (under tall raised ground):
  # 1) the tile whose wall pictures hang there, 2) else the tile at that spot on the flat map.
  for c in self.grid_cells:
   v=c["values"];h=v[3] if elev else 0
   for _,_,shift,i in c["walls"]:
    px=c["x"]*24;py=c["y"]*16+self.margin-h*16+(i+1-shift)*16
    if (px,py) not in squares:squares[(px,py)]=[(c["x"],c["y"])];arrows.add((px,py))
  self.height_floor=floor;self.height_stack={};self.height_grey={};self.grey_drawn=set()   # drawn_x: kept from the drawing pass (the x's you see)
  w=self.grid_width;height=lambda t:self.grid_cells[t[1]*w+t[0]]["values"][3]
  changed={o-3 for o in self.pending_heights}|{o for o in self.pending_heights}
  self.height_masks={}
  walls_only=self.mark_walls.get() and not self.height_edit.get()
  def label(tile,x,anchor,size):
   cell=self.grid_cells[tile[1]*w+tile[0]];blocked=cell["values"][0]&1
   if walls_only and not blocked:return
   edited=cell["offset"] in changed or cell["offset"]+3 in self.pending_heights
   colour=("#ffa040" if cell["values"][0]&0x41==1 else "#ff5c5c") if blocked else ("#c8b36a" if edited else "#58aaff")
   slope=cell["values"][2]&3
   text=str(height(tile)) if (not blocked or self.height_edit.get()) else "x";ty_=map_y_to_view(py+8,crop)
   if text=="x":self.drawn_x[(x-12,py)]=tile   # a click on this x acts on its own tile
   for ox,oy in ((-1,0),(1,0),(0,-1),(0,1)):   # black outline
    self.canvas.create_text(x+ox,ty_+oy,text=text,fill='black',anchor=anchor,font=("Segoe UI",size,"bold"),tags=("height_number",))
   self.canvas.create_text(x,ty_,text=text,fill=colour,anchor=anchor,
                           font=("Segoe UI",size,"bold"),tags=("height_number",f"hn_{tile[0]}_{tile[1]}"))
  height_walls={tuple(t) for t in self.editor.database.document.get('height_walls',{}).get(str(self.editor.current_map),[])}
  for (px,py),tiles in squares.items():
   # normal height = the lowest tile in this square (the ground); mask height =
   # the highest tile drawn over it, if any. Both are shown and each can be edited:
   # left half of the square edits the normal height, right half the mask height.
   # the tile you actually see in this square: the one drawn last (in front),
   # a real floor tile before empty ground
   masked={tuple(r['mask']) for r in self.editor.database.document.get('masked_tiles',{}).get(str(self.editor.current_map),[]) if isinstance(r,dict)}
   if any(t not in masked for t in tiles):tiles=[t for t in tiles if t not in masked]   # a mask picture never takes the square's number
   real=[t for t in tiles if self.grid_cells[t[1]*w+t[0]]["values"][4]!=0xFFFF or t in mask_origins]
   walkable=[t for t in real if not self.grid_cells[t[1]*w+t[0]]["values"][0]&1]
   # a tile you just raised or lowered is shown in the square it moved into
   edited=[t for t in walkable if self.grid_cells[t[1]*w+t[0]]["offset"]+3 in self.pending_heights]
   # a tile lowered/raised into a square another tile already shows does not
   # take that square's number: the tile that was there keeps it
   settled=[t for t in walkable if t not in edited] or [t for t in real if t not in edited and t not in [e for e in edited]]
   if edited and settled and not [t for t in walkable if t not in edited]:settled=[t for t in real if t not in edited]   # an x below stays an x
   hw=[t for t in tiles if t in height_walls and self.grid_cells[t[1]*w+t[0]]["values"][0]&1]
   if hw:   # Wall mode tile (user 2026-10-25): a grey wall of its height
    vy=map_y_to_view(py,crop);self.grey_square(px,vy,("height_number",f"grey_{px}_{py}"));self.height_grey[(px,py)]=hw[-1]
    if self.show_wall_pit_heights.get():self.canvas.create_text(px+12,vy+8,text=str(self.grid_cells[hw[-1][1]*w+hw[-1][0]]["values"][3]),anchor='center',fill='#9a9a9a',font=("Segoe UI",6),tags=("height_number",f"grey_{px}_{py}"))
    continue
   normal=(settled or edited or walkable or real or tiles)[-1]   # a walkable tile before an x
   last=getattr(self,'last_height_edit',None)
   if last in tiles:normal=last   # the tile you just raised/lowered shows its new height in the square it moved to
   others=[t for t in tiles if t!=normal]
   mask=max(enumerate(others),key=lambda item:(height(item[1]),item[0]))[1] if others else None
   if (px,py) in arrows and walls_only:
    self.grey_square(px,map_y_to_view(py,crop),("height_number",f"grey_{px}_{py}"));continue
   if (px,py) in arrows:
    vy=map_y_to_view(py,crop)   # no height of its own: 50% grey square
    self.grey_square(px,vy,("height_number",f"grey_{px}_{py}"))
    self.height_grey[(px,py)]=tiles[-1]   # a picked height can still be painted here
    owner=tiles[-1];owner_edited=self.grid_cells[owner[1]*w+owner[0]]["offset"]+3 in self.pending_heights
    faces={tuple(t) for t in self.editor.database.document.get('step_faces',{}).get(str(self.editor.current_map),[])}
    if False and (owner[0],owner[1]) in faces and self.height_edit.get():   # step faces now look like every other wall (grey)
     # the face left by a +1 / -1 step: a wall at the top tile's height (red, like other walls)
     for ox,oy in ((-1,0),(1,0),(0,-1),(0,1)):self.canvas.create_text(px+12+ox,vy+8+oy,text=str(height(owner)),anchor='center',fill='black',font=("Segoe UI",8,"bold"),tags=("height_number",f"grey_{px}_{py}"))
     self.canvas.create_text(px+12,vy+8,text=str(height(owner)),anchor='center',fill='#ff5a5a',font=("Segoe UI",8,"bold"),tags=("height_number",f"grey_{px}_{py}"))
     continue
    if owner_edited:   # a height you picked for this grey square: shown in yellow so you see it took
     for ox,oy in ((-1,0),(1,0),(0,-1),(0,1)):self.canvas.create_text(px+12+ox,vy+8+oy,text=str(height(owner)),anchor='center',fill='black',font=("Segoe UI",8,"bold"),tags=("height_number",f"grey_{px}_{py}"))
     self.canvas.create_text(px+12,vy+8,text=str(height(owner)),anchor='center',fill='#c8b36a',font=("Segoe UI",8,"bold"),tags=("height_number",f"grey_{px}_{py}"))
    elif self.show_wall_pit_heights.get():self.canvas.create_text(px+12,vy+8,text=str(height(owner)),anchor='center',fill='#9a9a9a',font=("Segoe UI",6),tags=("height_number",f"grey_{px}_{py}"))   # tiny grey number, centred
    continue
   self.height_stack[(px,py)]=normal
   label(normal,px+12,'center',8)   # one number per square: the lowest height
  self.height_empty={}
  for c in self.grid_cells:   # empty tiles: their square can be given a number too
   v=c["values"]
   if v[4]==0xFFFF and not c["walls"]:
    sq=(c["x"]*24,c["y"]*16+self.margin-(v[3]*16 if elev else 0))
    if sq not in squares:self.height_empty.setdefault(sq,(c["x"],c["y"]))
  if self.show_wall_pit_heights.get():   # empty tiles (no picture): tiny grey number in their own square
   for c in self.grid_cells:
    v=c["values"]
    if v[4]!=0xFFFF or c["walls"]:continue
    px=c["x"]*24;py=c["y"]*16+self.margin-(v[3]*16 if elev else 0)
    if (px,py) in squares:continue
    squares[(px,py)]=[(c["x"],c["y"])]
    self.canvas.create_text(px+12,map_y_to_view(py+8,crop),text=str(v[3]),anchor='center',fill='#9a9a9a',font=("Segoe UI",6),tags=("height_number",))
  # A raised/lowered tile that moved into a square another tile keeps shows
  # its number on the square it left (instead of grey), so it never vanishes.
  shown=set(self.height_stack.values());data=self.editor.session.data
  for c in self.grid_cells:
   t=(c["x"],c["y"]);at=c["offset"]+3
   if t in shown or at not in self.pending_heights or c["values"][0]&1 or c["values"][4]==0xFFFF:continue
   px=c["x"]*24;py=c["y"]*16+self.margin-(data[at]*16 if elev else 0)
   if (px,py) in self.height_stack:continue
   self.canvas.delete(f"grey_{px}_{py}");self.height_grey.pop((px,py),None)
   self.height_stack[(px,py)]=t;label(t,px+12,'center',8)
  self.raise_height_numbers()
 def _redraw_height_display(self):
  """Show every square's height at once after a change (no map re-render):
  a tile is drawn at its row minus its height, so the number squares are
  worked out from the grid as it is now, including changes not yet written."""
  self.canvas.delete("height_number");self.canvas.delete("height_hover");self.height_hover_tile=None
  crop=getattr(self,'map_crop_top',0);elev=self.elevation_enabled()
  floor={};squares={}
  mask_origins={tuple(r['origin'][:2]) for r in self.editor.database.document.get('masked_tiles',{}).get(str(self.editor.current_map),[]) if isinstance(r,dict)}|(getattr(self,'kept_squares',None) or (lambda:set()))()
  for c in self.grid_cells:
   v=c["values"]
   if v[4]==0xFFFF and not c["walls"] and (c["x"],c["y"]) not in mask_origins:continue   # empty ground: nothing drawn, no number (a masked tile's own record still counts)
   px=c["x"]*24;py=c["y"]*16+self.margin-(self.stop_height(c) *16 if elev else 0)
   floor[(c["x"],c["y"])]=(px,py);squares.setdefault((px,py),[]).append((c["x"],c["y"]))
  self.walk_behind=set()
  # Walk-behind floor: a walkable square with nothing drawn whose spot on screen is
  # covered by a raised wall's x. Alundra really stands there (the wall is drawn over
  # him), so the square shows its walkable height instead of the wall's x.
  for c in self.grid_cells:
   v=c["values"]
   if v[4]!=0xFFFF or c["walls"] or v[0]&1:continue
   sq=(c["x"]*24,c["y"]*16+self.margin-(v[3]*16 if elev else 0))
   here=squares.get(sq)
   if here and all(self.grid_cells[ty*self.grid_width+tx]["values"][0]&1 for tx,ty in here):
    here.append((c["x"],c["y"]));floor[(c["x"],c["y"])]=sq
    self.walk_behind.add((c["x"],c["y"]))
  # In the game Alundra's feet stop one square earlier than the blocked square's own
  # spot: on the last walk-behind square before a no-walk square he is already
  # stopped. That square shows the x, and the all-x spot just below it is cleared.
  W=self.grid_width
  for c in self.grid_cells:
   v=c["values"];tx,ty=c["x"],c["y"]
   if v[4]!=0xFFFF or c["walls"] or v[0]&1 or ty+1>=self.grid_height:continue
   b=self.grid_cells[(ty+1)*W+tx]
   if not b["values"][0]&1 or b["values"][4]!=0xFFFF:continue   # an edge the wall is drawn over
   up=(tx*24,ty*16+self.margin-(v[3]*16 if elev else 0));down=(up[0],up[1]+16)
   if down in squares and all(self.grid_cells[y*W+x]["values"][0]&1 for x,y in squares[down]):del squares[down]
   squares[up]=[(tx,ty+1)];floor[(tx,ty+1)]=up
   self.walk_behind.discard((tx,ty))
  arrows=set()   # squares with no height of their own: grey up arrow, not editable
  for (px,py),tiles in squares.items():
   if all(self.grid_cells[ty*self.grid_width+tx]["values"][4]==0xFFFF and self.grid_cells[ty*self.grid_width+tx]["walls"] for tx,ty in tiles):arrows.add((px,py))
  # Fill the squares no floor lands in (under tall raised ground):
  # 1) the tile whose wall pictures hang there, 2) else the tile at that spot on the flat map.
  for c in self.grid_cells:
   v=c["values"];h=v[3] if elev else 0
   for _,_,shift,i in c["walls"]:
    px=c["x"]*24;py=c["y"]*16+self.margin-h*16+(i+1-shift)*16
    if (px,py) not in squares:squares[(px,py)]=[(c["x"],c["y"])];arrows.add((px,py))
  self.height_floor=floor;self.height_stack={};self.height_grey={};self.drawn_x={};self.grey_drawn=set()
  self.height_shown={}   # square -> the tile whose number is drawn there when it is not the square's own tile (a floor behind a face)
  w=self.grid_width;height=lambda t:self.grid_cells[t[1]*w+t[0]]["values"][3]
  changed={o-3 for o in self.pending_heights}|{o for o in self.pending_heights}
  self.height_masks={}
  walls_only=self.mark_walls.get() and not self.height_edit.get()
  # Each tile covers the squares from its picture down to just above its own record
  # row (its height in squares). Lowest / Highest tiles show the lowest / highest
  # height of the tiles covering each square.
  # A square under a tile's top, down to the ground (its face, leading up to its
  # height), is grey when that tile is higher than any tile whose top is there.
  cover={};tops={};face_cover={};front={}
  for c in self.grid_cells:
   v=c["values"]
   if v[4]==0xFFFF or v[0]&1:continue
   hh=v[3] if elev else 0
   for k in range(max(1,hh)):
    sq=(c["x"]*24,(c["y"]-hh+k)*16+self.margin)
    cover.setdefault(sq,[]).append(v[3]);(tops if k==0 else face_cover).setdefault(sq,[]).append(v[3])
    if sq not in front or c["y"]>front[sq][0]:front[sq]=(c["y"],v[3],k)   # the tile drawn in front on this square
  pick=max if getattr(self,'height_show',None) is not None and self.height_show.get()=='Highest' else min
  lowest=pick is min
  # Lowest tiles: the floors behind a face (walkable, also ones with no picture) show through
  behind={};behind_tile={}
  if lowest:
   for c in self.grid_cells:
    v=c["values"]
    if v[0]&1 or (v[4]==0xFFFF and c["walls"]):continue
    sq=(c["x"]*24,(c["y"]-(v[3] if elev else 0))*16+self.margin)
    behind.setdefault(sq,[]).append(v[3])
    if sq not in behind_tile or v[3]<behind_tile[sq][0]:behind_tile[sq]=(v[3],(c["x"],c["y"]))   # the tile whose number is shown
  def is_face(sq):   # the tile drawn in front on this square shows its face here, not its top
   return sq in front and front[sq][2]>=1
  def face_square(sq):
   if lowest and behind.get(sq):return False   # Lowest tiles: the floor behind it is shown instead
   return is_face(sq)
  def cover_value(tile,sq):
   if face_square(sq):return 0   # drawn as a grey square, like walls
   if lowest and is_face(sq):self.height_shown[sq]=behind_tile[sq][1];return min(behind[sq])   # a floor behind a face: a click edits that floor
   if not lowest and sq in front:return front[sq][1]   # Highest tiles: the tile drawn in front on this square
   hs=tops.get(sq);return pick(hs) if hs else height(tile)
  labelled=set()
  def label(tile,x,anchor,size):
   labelled.add((x-12,py))
   cell=self.grid_cells[tile[1]*w+tile[0]];blocked=cell["values"][0]&1
   if walls_only and not blocked:   # No Walk Area: grey areas as in Edit heights, no numbers
    if face_square((x-12,py)) or cover_value(tile,(x-12,py))==0:self.grey_square(x-12,map_y_to_view(py,crop),("height_number",f"hn_{tile[0]}_{tile[1]}"))
    return
   edited=cell["offset"] in changed or cell["offset"]+3 in self.pending_heights
   colour=("#ffa040" if cell["values"][0]&0x41==1 else "#ff5c5c") if blocked else ("#c8b36a" if edited else "#58aaff")
   if not blocked and face_square((x-12,py)):   # a face leading up to a height: grey, like walls (tiny grey height with Show Wall / Pit Heights)
    vy=map_y_to_view(py,crop);sx=x-12
    self.grey_square(sx,vy,("height_number",f"hn_{tile[0]}_{tile[1]}"))
    if self.show_wall_pit_heights.get():self.canvas.create_text(sx+12,vy+8,text=str(front[(sx,py)][1]),anchor='center',fill='#9a9a9a',font=("Segoe UI",6),tags=("height_number",f"hn_{tile[0]}_{tile[1]}"))
    return
   if not blocked and cover_value(tile,(x-12,py))==0:   # height 0 tiles look exactly like walls: grey square, tiny grey 0 with Show Wall / Pit Heights
    vy=map_y_to_view(py,crop);sx=x-12
    self.grey_square(sx,vy,("height_number",f"hn_{tile[0]}_{tile[1]}"))
    if self.show_wall_pit_heights.get():self.canvas.create_text(sx+12,vy+8,text="0",anchor='center',fill='#9a9a9a',font=("Segoe UI",6),tags=("height_number",f"hn_{tile[0]}_{tile[1]}"))
    return
   slope=cell["values"][2]&3
   text=str(cover_value(tile,(x-12,py))) if not blocked else "x";ty_=map_y_to_view(py+8,crop)
   if text=="x":self.drawn_x[(x-12,py)]=tile   # a click on this x acts on its own tile
   else:self.height_shown[(x-12,py)]=tile   # painting a number edits the tile whose number is drawn here (user 2026-10-25)
   for ox,oy in ((-1,0),(1,0),(0,-1),(0,1)):   # black outline
    self.canvas.create_text(x+ox,ty_+oy,text=text,fill='black',anchor=anchor,font=("Segoe UI",size,"bold"),tags=("height_number",))
   self.canvas.create_text(x,ty_,text=text,fill=colour,anchor=anchor,
                           font=("Segoe UI",size,"bold"),tags=("height_number",f"hn_{tile[0]}_{tile[1]}"))
  height_walls={tuple(t) for t in self.editor.database.document.get('height_walls',{}).get(str(self.editor.current_map),[])}
  for (px,py),tiles in squares.items():
   # normal height = the lowest tile in this square (the ground); mask height =
   # the highest tile drawn over it, if any. Both are shown and each can be edited:
   # left half of the square edits the normal height, right half the mask height.
   # the tile you actually see in this square: the one drawn last (in front),
   # a real floor tile before empty ground
   masked={tuple(r['mask']) for r in self.editor.database.document.get('masked_tiles',{}).get(str(self.editor.current_map),[]) if isinstance(r,dict)}
   if any(t not in masked for t in tiles):tiles=[t for t in tiles if t not in masked]   # a mask picture never takes the square's number
   real=[t for t in tiles if self.grid_cells[t[1]*w+t[0]]["values"][4]!=0xFFFF or t in mask_origins or t in self.walk_behind]
   walkable=[t for t in real if not self.grid_cells[t[1]*w+t[0]]["values"][0]&1]
   # a tile you just raised or lowered is shown in the square it moved into
   edited=[t for t in walkable if self.grid_cells[t[1]*w+t[0]]["offset"]+3 in self.pending_heights]
   # a tile lowered/raised into a square another tile already shows does not
   # take that square's number: the tile that was there keeps it
   settled=[t for t in walkable if t not in edited] or [t for t in real if t not in edited and t not in [e for e in edited]]
   if edited and settled and not [t for t in walkable if t not in edited]:settled=[t for t in real if t not in edited]   # an x below stays an x
   hw=[t for t in tiles if t in height_walls and self.grid_cells[t[1]*w+t[0]]["values"][0]&1]
   if hw:   # Wall mode tile (user 2026-10-25): a grey wall of its height
    vy=map_y_to_view(py,crop);self.grey_square(px,vy,("height_number",f"grey_{px}_{py}"));self.height_grey[(px,py)]=hw[-1]
    if self.show_wall_pit_heights.get() and not walls_only:self.canvas.create_text(px+12,vy+8,text=str(self.grid_cells[hw[-1][1]*w+hw[-1][0]]["values"][3]),anchor='center',fill='#9a9a9a',font=("Segoe UI",6),tags=("height_number",f"grey_{px}_{py}"))
    continue
   normal=(settled or edited or walkable or real or tiles)[-1]   # a walkable tile before an x
   last=getattr(self,'last_height_edit',None)
   if last in tiles:normal=last   # the tile you just raised/lowered shows its new height in the square it moved to
   others=[t for t in tiles if t!=normal]
   mask=max(enumerate(others),key=lambda item:(height(item[1]),item[0]))[1] if others else None
   if (px,py) in arrows and walls_only:
    self.grey_square(px,map_y_to_view(py,crop),("height_number",f"grey_{px}_{py}"));continue
   if (px,py) in arrows:
    vy=map_y_to_view(py,crop)   # no height of its own: 50% grey square
    self.grey_square(px,vy,("height_number",f"grey_{px}_{py}"))
    self.height_grey[(px,py)]=tiles[-1]   # a picked height can still be painted here
    owner=tiles[-1];owner_edited=self.grid_cells[owner[1]*w+owner[0]]["offset"]+3 in self.pending_heights
    faces={tuple(t) for t in self.editor.database.document.get('step_faces',{}).get(str(self.editor.current_map),[])}
    if False and (owner[0],owner[1]) in faces and self.height_edit.get():   # step faces now look like every other wall (grey)
     # the face left by a +1 / -1 step: a wall at the top tile's height (red, like other walls)
     for ox,oy in ((-1,0),(1,0),(0,-1),(0,1)):self.canvas.create_text(px+12+ox,vy+8+oy,text=str(height(owner)),anchor='center',fill='black',font=("Segoe UI",8,"bold"),tags=("height_number",f"grey_{px}_{py}"))
     self.canvas.create_text(px+12,vy+8,text=str(height(owner)),anchor='center',fill='#ff5a5a',font=("Segoe UI",8,"bold"),tags=("height_number",f"grey_{px}_{py}"))
     continue
    if owner_edited and not face_square((px,py)):   # a height you picked for this grey square: shown in yellow so you see it took (a face leading up to a height stays plain grey)
     for ox,oy in ((-1,0),(1,0),(0,-1),(0,1)):self.canvas.create_text(px+12+ox,vy+8+oy,text=str(height(owner)),anchor='center',fill='black',font=("Segoe UI",8,"bold"),tags=("height_number",f"grey_{px}_{py}"))
     self.canvas.create_text(px+12,vy+8,text=str(height(owner)),anchor='center',fill='#c8b36a',font=("Segoe UI",8,"bold"),tags=("height_number",f"grey_{px}_{py}"))
    elif self.show_wall_pit_heights.get():self.canvas.create_text(px+12,vy+8,text=str(front[(px,py)][1] if (px,py) in front else height(owner)),anchor='center',fill='#9a9a9a',font=("Segoe UI",6),tags=("height_number",f"grey_{px}_{py}"))   # tiny grey number, centred
    continue
   self.height_stack[(px,py)]=normal
   label(normal,px+12,'center',8)   # one number per square: the lowest height
  self.height_empty={}
  for c in self.grid_cells:   # empty tiles: their square can be given a number too
   v=c["values"]
   if v[4]==0xFFFF and not c["walls"]:
    sq=(c["x"]*24,c["y"]*16+self.margin-(self.stop_height(c)*16 if elev else 0))
    if sq not in squares:self.height_empty.setdefault(sq,(c["x"],c["y"]))
  if self.show_wall_pit_heights.get() and not walls_only:   # empty tiles (no picture): tiny grey number in their own square
   for c in self.grid_cells:
    v=c["values"]
    if v[4]!=0xFFFF or c["walls"]:continue
    px=c["x"]*24;py=c["y"]*16+self.margin-(self.stop_height(c)*16 if elev else 0)
    if (px,py) in squares:continue
    squares[(px,py)]=[(c["x"],c["y"])]
    self.canvas.create_text(px+12,map_y_to_view(py+8,crop),text=str(v[3]),anchor='center',fill='#9a9a9a',font=("Segoe UI",6),tags=("height_number",))
  # A raised/lowered tile that moved into a square another tile keeps shows
  # its number on the square it left (instead of grey), so it never vanishes.
  shown=set(self.height_stack.values());data=self.editor.session.data
  for c in self.grid_cells:
   t=(c["x"],c["y"]);at=c["offset"]+3
   if t in shown or at not in self.pending_heights or c["values"][0]&1 or c["values"][4]==0xFFFF:continue
   px=c["x"]*24;py=c["y"]*16+self.margin-(data[at]*16 if elev else 0)
   if (px,py) in self.height_stack:continue
   self.canvas.delete(f"grey_{px}_{py}");self.height_grey.pop((px,py),None)
   self.height_stack[(px,py)]=t;label(t,px+12,'center',8)
  # squares covered by a tile but with no number of their own (under a raised tile)
  if True:   # No Walk Area too (user 2026-10-21)
   for (sx,sy),hs in cover.items():
    if (sx,sy) in labelled:continue
    vy=map_y_to_view(sy+8,crop)
    if lowest and behind.get((sx,sy)) and is_face((sx,sy)) and walls_only:continue   # a floor shows behind the face
    if lowest and behind.get((sx,sy)) and is_face((sx,sy)):   # Lowest tiles: a floor behind a face shows its number
     self.canvas.delete(f"grey_{sx}_{sy}");hv=min(behind[(sx,sy)]);self.height_shown[(sx,sy)]=behind_tile[(sx,sy)][1]
     for ox,oy in ((-1,0),(1,0),(0,-1),(0,1)):self.canvas.create_text(sx+12+ox,vy+oy,text=str(hv),fill='black',anchor='center',font=("Segoe UI",8,"bold"),tags=("height_number",))
     self.canvas.create_text(sx+12,vy,text=str(hv),fill="#58aaff",anchor='center',font=("Segoe UI",8,"bold"),tags=("height_number",))
     continue
    if (sx,sy) in self.height_grey:continue   # wall faces stay grey
    self.grey_square(sx,vy-8,("height_number",))
  for col,srow,hgt in self.editor.database.document.get('wall_squares',{}).get(str(self.editor.current_map),[]):   # Wall mode squares
   sx,sy=col*24,srow*16+self.margin;vy=map_y_to_view(sy,crop)
   find=getattr(self.canvas,'find_overlapping',None)
   if callable(find):
    for item in find(sx+6,vy+4,sx+18,vy+12) or ():
     if 'height_number' in self.canvas.gettags(item):self.canvas.delete(item)
   if getattr(self,'grey_drawn',None) is not None:self.grey_drawn.discard((sx,vy))
   self.height_stack.pop((sx,sy),None);self.height_shown.pop((sx,sy),None);self.drawn_x.pop((sx,sy),None)
   self.grey_square(sx,vy,("height_number",f"grey_{sx}_{sy}"));self.height_grey[(sx,sy)]=(col,srow)
   if self.show_wall_pit_heights.get() and not walls_only:self.canvas.create_text(sx+12,vy+8,text=str(hgt),anchor='center',fill='#9a9a9a',font=("Segoe UI",6),tags=("height_number",f"grey_{sx}_{sy}"))
  self.raise_height_numbers()
 def grey_square(self,x,y,tags):
  """Grey area square (Edit heights / No Walk Area): dark grey at 66% opacity (user 2026-10-21)."""
  import tkinter as tk
  from PIL import Image
  if not isinstance(self.canvas,tk.Canvas):return self.canvas.create_image(x,y,tags=tags)   # the quiet (no drawing) pass
  drawn=getattr(self,'grey_drawn',None)
  if drawn is not None:   # one grey layer per square: overlaps made darker greys (user 2026-10-21)
   if (x,y) in drawn:return None
   drawn.add((x,y))
  z=getattr(self.canvas,'zoom_factor',1.);cache=getattr(self,'_grey_photos',None)
  if cache is None:cache=self._grey_photos={}
  if z not in cache:
   im=Image.new('RGBA',(max(1,round(24*z)),max(1,round(16*z))),(0x20,0x20,0x20,168))
   cache[z]=ImageTk.PhotoImage(im,master=self.editor.root)
  return tk.Canvas.create_image(self.canvas,x*z,y*z,image=cache[z],anchor='nw',tags=tags)
 def stop_height(self,c):
  """Height a square is shown at in the height view. A no-walk (x) square is shown
  where Alundra's feet stop against it: raised by the height of the walkable floor
  he reaches it from (the nearest walkable square above it in the same column), not
  by its own height. So a tall wall's x no longer covers the floor he walks behind it."""
  v=c["values"]
  return v[3]   # placement by the floor you reach it from moved whole walls into the void; reverted
  w=self.grid_width;x=c["x"]
  for y in range(c["y"]-1,-1,-1):
   u=self.grid_cells[y*w+x]["values"]
   if not u[0]&1:return min(u[3],v[3])
  return v[3]
 def walk_tile_at(self,event):
  """No Walk Area: the tile of the x drawn in the square under the pointer, else the
  square's tile. The square's tile alone could be another one (the walkable tile below),
  so an x could not be cleared (user 2026-10-21)."""
  on,lt=self.layer_tile_at(event)
  if on:return lt
  tiles=self.walk_tiles_at(event)
  if tiles:return tiles[0]
  tile=self.height_tile_at(event)
  if tile is not None:return tile
  # A grey square (covered / Wall mode) has no number: use the tile whose floor lands on
  # this square, a walkable one first, so No Walk Area works there too (user 2026-10-25).
  x=int(self.canvas.canvasx(event.x));y=int(self.canvas_y(event));col=x//24;w=self.grid_width
  if not 0<=col<w:return None
  srow=(y//16*16-self.margin)//16;elev=self.elevation_enabled()
  here=[t for t in range(self.grid_height) if t-(self.grid_cells[t*w+col]['values'][3] if elev else 0)==srow]
  if not here:return None
  walk=[t for t in here if not self.grid_cells[t*w+col]['values'][0]&1]
  return (col,(walk or here)[-1])
 def walk_tiles_at(self,event):
  """Every tile whose x is drawn in the square under the pointer (two tiles can draw
  theirs in one square: clicking clears or sets them all)."""
  on,lt=self.layer_tile_at(event)
  if on:return [lt] if lt else []
  x=int(self.canvas.canvasx(event.x));y=int(self.canvas_y(event));col,row=x//24,y//16;out=[]
  for item in self.canvas.find_overlapping(col*24+2,map_y_to_view(row*16+2,getattr(self,'map_crop_top',0)),col*24+22,map_y_to_view(row*16+14,getattr(self,'map_crop_top',0))) or ():
   if self.canvas.type(item)=='text' and self.canvas.itemcget(item,'text')=='x':
    for tag in self.canvas.gettags(item):
     if tag.startswith('hn_'):
      t=tuple(map(int,tag[3:].split('_')))
      if t not in out:out.append(t)
  first=getattr(self,'drawn_x',{}).get((col*24,row*16))
  if first is not None:out=[first]+[t for t in out if t!=first]
  return out
 def layer_tile_at(self,event):
  """Layer 1-10 picked: (True, the tile of that layer on the square under the pointer or None);
  (False, None) when the view shows all layers. Edits then act on that layer's tile only."""
  n=self.layer_view.get() if getattr(self,'layer_view',None) is not None else 0
  if not n or not (self.height_edit.get() or self.mark_walls.get()):return False,None
  x=int(self.canvas.canvasx(event.x));y=int(self.canvas_y(event));col=x//24
  srow=(y//16*16-self.margin)//16
  layers=self.layer_stacks().get((col,srow),[])
  if len(layers)<n:return True,None
  tiles=layers[n-1];walk=[t for t in tiles if not self.grid_cells[t[1]*self.grid_width+t[0]]['values'][0]&1]
  t=(walk or tiles)[0];return True,(t[0],t[1])
 def height_tile_at(self,event):
  """The tile whose height is shown in the grid square under the pointer."""
  on,lt=self.layer_tile_at(event)
  if on:return lt
  x=int(self.canvas.canvasx(event.x));y=int(self.canvas_y(event))
  square=(x//24*24,y//16*16)
  mask=getattr(self,'height_masks',{}).get(square)
  return getattr(self,'height_stack',{}).get(square)
 def layer_stacks(self):
  """{(column, screen row): [[(tile x, tile y, height), ...] per height, lowest first]}: the tiles whose
  floor lands on each square (where Alundra stands on them), grouped by height. Layer N of a square
  is its Nth lowest height (user 2026-10-25: layers are heights that line up on the same square)."""
  w=self.grid_width;elev=self.elevation_enabled();by={}
  for ty in range(self.grid_height):
   for tx in range(w):
    v=self.grid_cells[ty*w+tx]['values'];h=v[3] if elev else 0
    by.setdefault((tx,ty-h),{}).setdefault(v[3],[]).append((tx,ty,v[3]))
  return {sq:[hs[k] for k in sorted(hs)] for sq,hs in by.items()}
 def draw_layer_view(self):
  """Layer N (user 2026-10-25): the full map as usual; on each square that has tiles at N or more
  heights, the tile at its Nth lowest height has its picture drawn on top (so it can be seen even
  when another height covers it), framed blue (walkable) or red (no-walk), with its height. Tiles
  with no picture get a dotted frame. Squares with fewer heights are left as they are."""
  self.canvas.delete("layer_view")
  n=self.layer_view.get() if getattr(self,'layer_view',None) is not None else 0
  if not n or not (self.height_edit.get() or self.mark_walls.get()) or not hasattr(self,'renderer') or not isinstance(self.canvas,tk.Canvas):return
  from PIL import Image,ImageDraw
  self.canvas.delete("height_number")
  crop=getattr(self,'map_crop_top',0);w=self.grid_width;z=getattr(self.canvas,'zoom_factor',1.)
  stacks=self.layer_stacks();deepest=max((len(v) for v in stacks.values()),default=0)
  top=min(0,min((r*16+self.margin-crop for _,r in stacks),default=0))
  height=max(self.grid_height*16+self.margin-crop,max((r*16+self.margin-crop+16 for _,r in stacks),default=0))-top
  im=Image.new('RGBA',(w*24,max(16,height)),(0,0,0,0));d=ImageDraw.Draw(im);labels=[]
  for (col,r),layers in stacks.items():
   if len(layers)<n:continue
   tiles=layers[n-1];walk=[t for t in tiles if not self.grid_cells[t[1]*w+t[0]]['values'][0]&1]
   tx,ty,h=(walk or tiles)[0];v=self.grid_cells[ty*w+tx]['values'];x=col*24;y=r*16+self.margin-crop-top
   if v[4]!=0xFFFF:
    try:im.alpha_composite(self.renderer.tile(v[4]).convert('RGBA'),(x,y))
    except Exception:pass
    d.rectangle((x,y,x+23,y+15),outline=(88,170,255,255) if walk else (255,92,92,255))
   else:
    c=(88,170,255,255) if walk else (255,92,92,255)
    for k in range(0,24,4):d.point((x+k,y),fill=c);d.point((x+k,y+15),fill=c)
    for k in range(0,16,4):d.point((x,y+k),fill=c);d.point((x+23,y+k),fill=c)
   labels.append((x,y,str(h) if walk else "x","#58aaff" if walk else "#ff5c5c"))
  if z!=1:im=im.resize((max(1,round(im.width*z)),max(1,round(im.height*z))),Image.NEAREST)
  self.layer_view_photo=ImageTk.PhotoImage(im,master=self.editor.root)
  tk.Canvas.create_image(self.canvas,0,top*z,image=self.layer_view_photo,anchor='nw',tags=("layer_view",))
  for x,y,text,fill in labels:
   cx=(x+12)*z;cy=(y+top+8)*z
   for ox,oy in ((-1,0),(1,0),(0,-1),(0,1)):tk.Canvas.create_text(self.canvas,cx+ox,cy+oy,text=text,fill='black',font=("Segoe UI",8,"bold"),tags=("layer_view",))
   tk.Canvas.create_text(self.canvas,cx,cy,text=text,fill=fill,font=("Segoe UI",8,"bold"),tags=("layer_view",))
  self.canvas.tag_raise("layer_view")
  self.caption.set(f"Layer {n}: on each square, the tile at its height number {n} (lowest first) is drawn on top with its height; edits change only those tiles. Most heights on one square here: {deepest}.")
 def square_tiles(self,col,srow):
  """Tiles on screen square (col, srow): those whose floor is there (Alundra stands there on them),
  then those that only draw a wall piece there. [(tx, ty, 'floor' / 'piece')]"""
  w=self.grid_width;out=[]
  if not 0<=col<w:return out
  elev=self.elevation_enabled()
  for ty in range(self.grid_height):
   v=self.grid_cells[ty*w+col]['values']
   if ty-(v[3] if elev else 0)==srow:out.append((col,ty,'floor'))
  for ty in range(self.grid_height):
   c=self.grid_cells[ty*w+col]
   if (col,ty,'floor') in out:continue
   if any(r==srow and not f for r,_,f in self.record_pieces(c)):out.append((col,ty,'piece'))
  # tiles he walks onto at this square: walking from a walkable neighbour at height hn onto tile (col, ty),
  # he is on this square (ty - hn) whatever the tile's own height, then falls or climbs to it (user 2026-10-25)
  listed={(a,b) for a,b,_ in out}
  for ty in range(self.grid_height):
   if (col,ty) in listed:continue
   v=self.grid_cells[ty*w+col]['values']
   if v[0]&1:continue
   for dx,dy in ((0,-1),(0,1),(-1,0),(1,0)):
    nx,ny=col+dx,ty+dy
    if not(0<=nx<w and 0<=ny<self.grid_height):continue
    n=self.grid_cells[ny*w+nx]['values']
    if not n[0]&1 and n[3]!=v[3] and ty-(n[3] if elev else 0)==srow:out.append((col,ty,f'walk-in from {nx},{ny} (height {n[3]})'));listed.add((col,ty));break
  return out
 def event_square(self,event):
  x=int(self.canvas.canvasx(event.x));y=int(self.canvas_y(event))
  return x//24,(y//16*16-self.margin)//16
 def hover_tile_info(self,event):
  try:
   if getattr(self,'tile_info',None) is None or not self.tile_info.get() or not self.height_edit.get():return
   col,srow=self.event_square(event)
   if (col,srow)==getattr(self,'tile_info_hover',None):return
   self.tile_info_hover=(col,srow);w=self.grid_width
   tiles=[t for t in self.square_tiles(col,srow) if t[2]=='floor']
   walkin=[t for t in self.square_tiles(col,srow) if t[2].startswith('walk-in')]
   hs=sorted({self.grid_cells[ty*w+tx]['values'][3] for tx,ty,_ in tiles})
   walk=sum(1 for tx,ty,_ in tiles if not self.grid_cells[ty*w+tx]['values'][0]&1)
   if not tiles:self.caption.set(f"Square {col}, {srow}: no tile stands here."+(f" But he can walk onto {len(walkin)} tile(s) here from another height - click to see them." if walkin else ""))
   else:self.caption.set(f"Square {col}, {srow}: {len(tiles)} tile(s) at height(s) {', '.join(map(str,hs))} ({walk} walkable)"+(" - several heights overlap here." if len(hs)>1 else ".")+(f" {len(walkin)} tile(s) he can walk onto here from another height." if walkin else "")+" Click to edit them.")
  except Exception as exc:
   self.caption.set(f"Tile info: {exc}")
 def keep_tile_info_front(self):
  win=getattr(self,'tile_info_window',None)
  try:
   if win is not None and win.winfo_exists():win.attributes('-topmost',True);win.lift()
  except Exception:pass
 def open_tile_info(self,event):
  """Tile info window: every tile on the clicked square, each with its picture, a height box and a
  No walk box. Apply sets them (kept with the height edits, saved like them)."""
  from PIL import Image
  e=self.editor;w=self.grid_width
  col,srow=self.event_square(event);self.show_tile_fix(col,srow)
 def show_tile_fix(self,col,srow):
  from PIL import Image
  e=self.editor;w=self.grid_width;tiles=self.square_tiles(col,srow);self.tile_fix_square=(col,srow)
  masks=self.square_masks(col,srow)
  win=getattr(self,'tile_info_window',None)
  if win is None or not win.winfo_exists():
   win=self.tile_info_window=tk.Toplevel(e.root);win.title("Tile fix");win.attributes('-topmost',True)
   try:win.transient(e.root)   # kept in front of the editor (user 2026-10-25)
   except Exception:pass
   e.root.bind('<FocusIn>',lambda _e:self.keep_tile_info_front(),add='+');e.root.bind('<Configure>',lambda _e:self.keep_tile_info_front(),add='+')
  for child in win.winfo_children():child.destroy()
  self.tile_info_photos=[]
  self.keep_tile_info_front()
  ttk.Label(win,text=f"Square: column {col}, screen row {srow}").pack(anchor="w",padx=8,pady=(8,4))
  if not tiles:ttk.Label(win,text="No tile on this square.").pack(anchor="w",padx=8,pady=4);return
  rows=[]
  for tx,ty,kind in tiles:
   c=self.grid_cells[ty*w+tx];v=c['values']
   f=ttk.Frame(win);f.pack(anchor="w",fill="x",padx=8,pady=2)
   im=Image.new('RGBA',(24,16),(40,40,40,255))
   if v[4]!=0xFFFF:
    try:im.alpha_composite(self.renderer.tile(v[4]).convert('RGBA'))
    except Exception:pass
   photo=ImageTk.PhotoImage(im.resize((48,32),Image.NEAREST),master=e.root);self.tile_info_photos.append(photo)
   tk.Label(f,image=photo,borderwidth=1,relief="solid").pack(side="left")
   desc=f"  Tile {tx},{ty}"+("" if kind=='floor' else "  (wall piece here)" if kind=='piece' else f"  ({kind}: steps on here, lands at {v[3]})")+("   no picture" if v[4]==0xFFFF else "")
   ttk.Label(f,text=desc,width=62).pack(side="left")
   ttk.Label(f,text="Height").pack(side="left")
   hv=tk.StringVar(value=str(v[3]));ttk.Spinbox(f,from_=0,to=255,textvariable=hv,width=5).pack(side="left",padx=(2,10))
   nv=tk.BooleanVar(value=bool(v[0]&1));ttk.Checkbutton(f,text="No walk",variable=nv).pack(side="left")
   rows.append((tx,ty,hv,nv))
   for where,qs in masks.get((tx,ty),[]):   # this picture is drawn over Alundra (Fix Masks / No Mask rule)
    m_=ttk.Frame(win);m_.pack(anchor='w',fill='x',padx=(64,8),pady=1)
    ttk.Label(m_,text=f"{'floor picture' if where[0]=='floor' else 'wall piece'} here is drawn OVER Alundra when he stands on tile(s) "+', '.join(f'{tx},{q}' for q in qs),foreground='#ff8040').pack(side='left')
    ttk.Button(m_,text='Draw behind him',command=lambda a=(tx,ty,where):self.editor.guard(lambda:self.tile_fix_mask(*a))).pack(side='left',padx=6)
   if kind=='floor' and not v[0]&1:   # where he can step off this tile: the game checks the map cell at his
    # position, whatever its height; a walkable cell lower than this one lets him walk on and fall to it
    for dx,dy,name in ((0,-1,'up'),(0,1,'down'),(-1,0,'left'),(1,0,'right')):
     nx,ny=tx+dx,ty+dy
     if not (0<=nx<w and 0<=ny<self.grid_height):continue
     nc=self.grid_cells[ny*w+nx];nvv=nc['values']
     if nvv[0]&1 or nvv[3]>=v[3]:continue
     g=ttk.Frame(win);g.pack(anchor="w",fill="x",padx=(64,8),pady=1)
     ttk.Label(g,text=f"{name}: tile {nx},{ny} height {nvv[3]} is walkable - he walks off here and falls {v[3]-nvv[3]}"+(" (no picture)" if nvv[4]==0xFFFF else ""),foreground="#ffa040").pack(side="left")
     nhv=tk.StringVar(value=str(nvv[3]));ttk.Spinbox(g,from_=0,to=255,textvariable=nhv,width=5).pack(side="left",padx=(8,6))
     nnv=tk.BooleanVar(value=False);ttk.Checkbutton(g,text="No walk",variable=nnv).pack(side="left")
     rows.append((nx,ny,nhv,nnv))
  bar=ttk.Frame(win);bar.pack(fill='x',padx=8,pady=8)
  ttk.Button(bar,text="Apply",command=lambda:self.editor.guard(lambda:self.apply_tile_info(rows,col,srow))).pack(side="right")
 def square_masks(self,col,srow):
  """{(tx, ty): [(where, [rows he stands on])]} pictures on this square drawn over Alundra."""
  from map_area_copy import cells_of
  from no_mask import picture_covers
  self.commit_pending()
  e=self.editor;w,hh,cells=cells_of(e.session,e.current_map);out={}
  for ty in range(hh):
   c=cells[ty*w+col];v=c['values'];floor=ty-v[3]
   pics=[]
   if v[4]!=0xFFFF and floor==srow:pics.append(('floor',))
   if c.get('walls'):
    sh,codes=c['walls']
    for i,cd in enumerate(codes):
     if cd!=0xFFFF and floor+i+1-sh==srow:pics.append(('wall',i))
   for where in pics:
    qs=picture_covers(cells,w,hh,col,ty,srow,where)
    if qs:out.setdefault((col,ty),[]).append((where,qs))
  return out
 def square_pictures(self,tx,ty,srow):
  """Pictures tile (tx, ty) draws on screen row srow: ('floor',) and/or ('wall', i)."""
  c=self.grid_cells[ty*self.grid_width+tx];v=c['values'];floor=ty-(v[3] if self.elevation_enabled() else 0);out=[]
  if v[4]!=0xFFFF and floor==srow:out.append(('floor',))
  for _,cd,sh,i in c['walls']:
   if cd!=0xFFFF and floor+i+1-sh==srow:out.append(('wall',i))
  return out
 def tile_fix_push_all(self):
  """Draw all further back (user 2026-10-25): every picture on the clicked square moves to a
  tile further up the map where it can, so what stands on its row is drawn over it.
  The map looks the same; one Undo step."""
  from map_area_copy import cells_of,rebuild_grid
  from no_mask import push_back,_pictures
  self.commit_pending()
  e=self.editor;w,hh,cells=cells_of(e.session,e.current_map)
  col,srow=self.tile_fix_square
  margin=max((x['values'][3] for x in cells),default=0)*16
  moved=[];tried=set();progress=True
  while progress:
   progress=False
   for ty in range(hh-1,-1,-1):
    for r,cd,where in _pictures(cells[ty*w+col],ty):
     if r!=srow or (ty,cd,where[0]) in tried:continue
     tried.add((ty,cd,where[0]))
     done=push_back(self.renderer,cells,w,hh,margin,col,ty,srow,cd,where)
     if done:moved.append((ty,done[0]));progress=True;break
    if progress:break
  if not moved:
   self.caption.set("Tile fix: nothing on this square can go further back without the map looking different.");return
  rebuild_grid(e.session,e.current_map,cells,f"Tile fix: square {col},{srow} drawn further back")
  e.dirty=True;self.refresh(reload_textures=False,keep_view=True)
  self.caption.set("Tile fix: moved "+", ".join(f"{col},{a} to {col},{b}" for a,b in moved)+" - drawn further back, the map looks the same. Undo takes it back.")
  self.show_tile_fix(col,srow)
 def tile_fix_push_map(self):
  """Draw all further back (panel button, user 2026-10-25): every picture of the map moves to a
  tile further up the map where it can, so what stands on its row is drawn over it. The map
  looks the same; one Undo step."""
  from map_area_copy import cells_of,rebuild_grid
  from no_mask import push_back,_pictures
  self.commit_pending()
  e=self.editor;w,hh,cells=cells_of(e.session,e.current_map)
  margin=max((x['values'][3] for x in cells),default=0)*16
  count=0
  for col in range(w):
   tried=set();progress=True
   while progress:
    progress=False
    for ty in range(hh-1,-1,-1):
     for r,cd,where in _pictures(cells[ty*w+col],ty):
      if (ty,cd,where[0],r) in tried:continue
      tried.add((ty,cd,where[0],r))
      if push_back(self.renderer,cells,w,hh,margin,col,ty,r,cd,where):count+=1;progress=True;break
     if progress:break
  if not count:
   self.caption.set("Draw all further back: nothing on this map can go further back without the map looking different.");return
  rebuild_grid(e.session,e.current_map,cells,"Draw all further back")
  e.dirty=True;self.refresh(reload_textures=False,keep_view=True)
  self.caption.set(f"Draw all further back: {count} picture(s) moved further back - the map looks the same. Undo takes it back.")
  sq=getattr(self,'tile_fix_square',None);win=getattr(self,'tile_info_window',None)
  try:
   if sq and win is not None and win.winfo_exists():self.show_tile_fix(*sq)
  except Exception:pass
 def tile_fix_push(self,tx,ty,where):
  """Draw further back: the picture goes to a tile further up the map, so a gate or other
  object standing on this tile's row is drawn over it (user 2026-10-25)."""
  from map_area_copy import cells_of,rebuild_grid
  from no_mask import push_back
  self.commit_pending()
  e=self.editor;w,hh,cells=cells_of(e.session,e.current_map)
  col,srow=self.tile_fix_square;c=cells[ty*w+tx]
  cd=c['values'][4] if where[0]=='floor' else c['walls'][1][where[1]]
  margin=max((x['values'][3] for x in cells),default=0)*16
  moved=push_back(self.renderer,cells,w,hh,margin,tx,ty,srow,cd,where)
  if not moved:
   self.caption.set("Tile fix: that picture can't go further back without the map looking different here.");return
  rebuild_grid(e.session,e.current_map,cells,f"Tile fix: picture of {tx},{ty} drawn further back")
  e.dirty=True;self.refresh(reload_textures=False,keep_view=True)
  self.caption.set(f"Tile fix: picture moved to tile {tx},{moved[0]} - objects on row {ty} are now drawn over it; the map looks the same. Undo takes it back.")
  self.show_tile_fix(col,srow)
 def blank_tile_code(self,cells):
  """A tile picture on this map with nothing drawn (every pixel see-through), or None."""
  cache=getattr(self,'_blank_code',None)
  if cache and cache[0]==self.editor.current_map:return cache[1]
  found=None
  for cd in sorted({c['values'][4] for c in cells if c['values'][4]!=0xFFFF}|set(range(1024))):
   try:
    if self.renderer.tile(cd).convert('RGBA').getchannel('A').getbbox() is None:found=cd;break
   except Exception:continue
  self._blank_code=(self.editor.current_map,found);return found
 def kept_squares(self):
  """Tiles whose picture Draw behind him moved off (user 2026-10-25): they keep their square,
  height number and walking as if the picture were still there."""
  try:return {tuple(t) for t in self.editor.database.document.get('drawn_behind',{}).get(str(self.editor.current_map),[])}
  except Exception:return set()
 def tile_fix_mask(self,tx,ty,where):
  from map_area_copy import cells_of,rebuild_grid
  from no_mask import fix_picture
  self.commit_pending()
  e=self.editor;w,hh,cells=cells_of(e.session,e.current_map)
  col,srow=self.tile_fix_square;c=cells[ty*w+tx]
  cd=c['values'][4] if where[0]=='floor' else c['walls'][1][where[1]]
  margin=max((x['values'][3] for x in cells),default=0)*16
  moved=fix_picture(self.renderer,cells,w,hh,margin,tx,ty,srow,cd,where)
  if not moved:
   self.caption.set(f"Tile fix: that picture can't go behind Alundra without the map looking different here.");return
  self.keep_floor(cells,w,tx,ty)
  rebuild_grid(e.session,e.current_map,cells,f"Tile fix: picture of {tx},{ty} drawn behind Alundra")
  e.dirty=True;self.refresh(reload_textures=False,keep_view=True)
  self.caption.set(f"Tile fix: picture moved to tile {tx},{moved[-1] if moved[-1]!=ty else moved[0]} - drawn behind Alundra, the map looks the same. Undo takes it back.")
  self.show_tile_fix(col,srow)
 def keep_floor(self,cells,w,tx,ty):
  """After Draw behind him: the tile keeps a floor (a fully see-through picture) so it stays its
  height and the map looks the same; with no such picture the number views still keep it."""
  e=self.editor
  if cells[ty*w+tx]['values'][4]==0xFFFF:
   blank=self.blank_tile_code(cells)
   if blank is not None:
    v=list(cells[ty*w+tx]['values']);v[4]=blank;cells[ty*w+tx]=dict(cells[ty*w+tx],values=tuple(v))
  if cells[ty*w+tx]['values'][4]==0xFFFF:
   kept=e.database.document.setdefault('drawn_behind',{}).setdefault(str(e.current_map),[])
   if [tx,ty] not in kept:kept.append([tx,ty])
 def tile_fix_mask_map(self):
  """Draw all behind Alundra (user 2026-10-25): Draw behind him on every picture of the map drawn
  over Alundra; slopes are left alone. The map looks the same; one Undo step."""
  from map_area_copy import cells_of,rebuild_grid
  from no_mask import fix_picture,find_masking,layered,masked_tiles
  self.commit_pending()
  e=self.editor;w,hh,cells=cells_of(e.session,e.current_map)
  margin=max((x['values'][3] for x in cells),default=0)*16
  keep=masked_tiles(e.database.document,e.current_map)
  count=0;tried=set();progress=True
  while progress:
   progress=False
   for tx,ty,r,cd,where,qs in find_masking(cells,w,hh):
    if (tx,ty,r,cd) in tried:continue
    tried.add((tx,ty,r,cd))
    if cells[ty*w+tx]['values'][2]&3:continue   # a slope (Slope byte low 2 bits): left alone
    if (tx,ty) in keep or layered(cells,w,hh,tx,ty,r,where):continue   # layered masks and Mask layer tiles stay (user 2026-10-26)
    try:moved=fix_picture(self.renderer,cells,w,hh,margin,tx,ty,r,cd,where,skip_slopes=True)
    except Exception:moved=None
    if moved:
     self.keep_floor(cells,w,tx,ty);count+=1;progress=True;break
  if not count:
   self.caption.set("Draw all behind Alundra: nothing here can go behind Alundra without the map looking different.");return
  rebuild_grid(e.session,e.current_map,cells,"Draw all behind Alundra")
  e.dirty=True;self.refresh(reload_textures=False,keep_view=True)
  self.caption.set(f"Draw all behind Alundra: {count} picture(s) now drawn behind him. Undo takes it back.")
 def apply_tile_info(self,rows,col,srow):
  w=self.grid_width;changed=[];bad=[]
  for tx,ty,hv,nv in rows:
   c=self.grid_cells[ty*w+tx];v=c['values']
   try:target=int(hv.get())
   except ValueError:bad.append(f"{tx},{ty}");continue
   if not 0<=target<=255:bad.append(f"{tx},{ty}");continue
   if target!=v[3]:
    old=self.tile_rows(tx,ty)
    self.pending_heights[c['offset']+3]=target;c['values']=v[:3]+(target,)+v[4:]
    g=getattr(self,'pending_stack_grid',None)
    if g is not None:sc=g[2][ty*w+tx];sv=list(sc['values']);sv[3]=target;sc['values']=tuple(sv)
    self.redraw_columns([(tx,ty)],before={(tx,ty):old});changed.append(f"{tx},{ty} height {target}")
   if bool(c['values'][0]&1)!=bool(nv.get()):
    self.set_walk(tx,ty,bool(nv.get()));changed.append(f"{tx},{ty} {'no walk' if nv.get() else 'walkable'}")
  if changed:self.editor.dirty=True;self.schedule_height_redraw()
  msg=("Tile info: "+"; ".join(changed)) if changed else "Tile info: nothing changed."
  if bad:msg+=f" Heights must be 0-255 (skipped {', '.join(bad)})."
  self.caption.set(msg)
 def layers_toggled(self):
  if not self.show_layers.get():
   w=getattr(self,'layers_window',None)
   if w is not None:
    try:w.destroy()
    except Exception:pass
   self.layers_window=None;self.layers_square=None
 def hover_layers(self,event):
  """Layers (Edit heights, user 2026-10-25): every tile on the square under the pointer, one row each:
  its picture, tile, height, floor or wall piece, and whether Alundra can walk on it, with a button to
  switch that. Tiles with no picture whose floor is on this square (invisible floor) are listed too."""
  try:
   if not getattr(self,'show_layers',None) or not self.show_layers.get() or not self.height_edit.get() or not hasattr(self,'renderer'):return
   x=int(self.canvas.canvasx(event.x));y=int(self.canvas_y(event));col=x//24
   if not 0<=col<self.grid_width:return
   srow=(y//16*16-self.margin)//16
   if (col,srow)==getattr(self,'layers_square',None):return
   self.layers_square=(col,srow);self.fill_layers(col,srow)
  except Exception as exc:
   self.caption.set(f"Layers: {exc}")
 def fill_layers(self,col,srow):
  from PIL import Image
  e=self.editor;w=self.grid_width
  win=getattr(self,'layers_window',None)
  if win is None or not win.winfo_exists():
   win=self.layers_window=tk.Toplevel(e.root);win.title("Layers");win.attributes('-topmost',True)
   win.protocol("WM_DELETE_WINDOW",lambda:(self.show_layers.set(False),self.layers_toggled()))
  for child in win.winfo_children():child.destroy()
  self.layer_photos=[]
  ttk.Label(win,text=f"Square: column {col}, screen row {srow}   (drawn first at the top)").pack(anchor="w",padx=6,pady=(6,2))
  rows=[]
  for ty in range(self.grid_height):
   c=self.grid_cells[ty*w+col]
   for r,cd,is_floor in self.record_pieces(c):
    if r==srow:rows.append((ty,cd,'floor' if is_floor else 'wall piece'))
   v=c['values']
   if v[4]==0xFFFF and ty-v[3]==srow:rows.append((ty,None,'floor, no picture'))
  if not rows:ttk.Label(win,text="Nothing on this square.").pack(anchor="w",padx=6,pady=4)
  for ty,cd,kind in rows:
   c=self.grid_cells[ty*w+col];v=c['values']
   f=ttk.Frame(win);f.pack(anchor="w",fill="x",padx=6,pady=2)
   im=Image.new('RGBA',(24,16),(40,40,40,255))
   if cd is not None:
    try:
     tile=self.renderer.tile(cd).convert('RGBA');im.alpha_composite(tile.crop((0,0,24,16)))
    except Exception:pass
   photo=ImageTk.PhotoImage(im.resize((48,32),Image.NEAREST),master=e.root);self.layer_photos.append(photo)
   tk.Label(f,image=photo,borderwidth=1,relief="solid").pack(side="left")
   blocked=v[0]&1;walk=("no-walk (player only)" if v[0]&0x41==1 else "no-walk (everyone)") if blocked else "WALKABLE"
   floor_square=ty-v[3]
   where="" if kind!='wall piece' else f", its floor is on screen row {floor_square}"
   ttk.Label(f,text=f"  Tile {col},{ty}   height {v[3]}   {kind}{where}   {walk}",foreground=("#ff5c5c" if blocked else "#58aaff")).pack(side="left")
   ttk.Button(f,text=("Make walkable" if blocked else "Make no-walk"),
              command=lambda tx=col,tty=ty,b=blocked:self.layer_set_walk(tx,tty,not b)).pack(side="right")
 def layer_set_walk(self,tx,ty,blocked):
  try:
   self.set_walk(tx,ty,blocked);self.schedule_height_redraw()
   if self.layers_square:self.fill_layers(*self.layers_square)
  except Exception as exc:
   self.caption.set(f"Layers: {exc}")
 def hover_height(self,event):
  if not self.height_edit.get() or not hasattr(self,'renderer'):
   if getattr(self,'height_hover_tile',None) is not None:self.canvas.delete("height_hover");self.height_hover_tile=None
   return
  tile=self.height_tile_at(event)
  sq=None
  if tile not in getattr(self,'height_floor',{}):   # a grey square: the selector still shows on it (user 2026-10-25)
   try:
    x=int(self.canvas.canvasx(event.x));y=int(self.canvas_y(event));sq=(x//24*24,y//16*16)
    if sq not in getattr(self,'height_grey',{}):sq=None
   except Exception:sq=None
  key=tile if sq is None else ('grey',sq)
  if key==getattr(self,'height_hover_tile',None):return   # same tile: nothing to redraw
  self.canvas.delete("height_hover");self.height_hover_tile=key
  if sq is not None:
   px,py=sq;vy=map_y_to_view(py,getattr(self,'map_crop_top',0))
   self.canvas.create_rectangle(px,vy,px+24,vy+16,outline="#58aaff",width=2,tags="height_hover");return
  if tile not in getattr(self,'height_floor',{}):return
  px,py=self.height_floor[tile];vy=map_y_to_view(py,getattr(self,'map_crop_top',0))
  self.canvas.create_rectangle(px,vy,px+24,vy+16,outline="#58aaff",width=2,tags="height_hover")
 def _unused_height_numbers(self):
  for cell in self.grid_cells:
   x=cell["x"]*24+2
   y=cell["y"]*16+self.margin-(cell["values"][3]*16 if self.elevation_enabled() else 0)+2
   self.canvas.create_text(x,y,text=str(cell["values"][3]),anchor="nw",fill="#58aaff",font=("Segoe UI",8,"bold"),tags="height_number")
 def sync_stack_walk(self,tx,ty,walk):
  g=getattr(self,'pending_stack_grid',None)
  if g is not None:
   sc=g[2][ty*self.grid_width+tx];sv=list(sc['values']);sv[0]=walk;sc['values']=tuple(sv)
 def mask_key(self,event):
  """The tile a Mask-layer click acts on, and whether it is already a mask (★)."""
  x,y=self.canvas.canvasx(event.x),self.canvas_y(event)
  hits=self.renderer.surface_hits.get((int(x)//24,int(y)//16),[])
  hit=next((h for h in reversed(hits) if h[5]!=0xFFFF),None)
  if hit is None:return None,False
  e=self.editor;stars=e.database.document.get('masked_tiles',{}).get(str(e.current_map),[])
  key=(hit[2],hit[3])
  return key,any(isinstance(r,dict) and tuple(r['mask'])==key for r in stars)
 def landing_tiles(self,event):
  """Every tile whose floor lands on the square under the pointer (where Alundra stands
  when he is on that tile), whatever number or grey square the view shows there."""
  on,lt=self.layer_tile_at(event)
  if on:return [lt] if lt else []
  x=int(self.canvas.canvasx(event.x));y=int(self.canvas_y(event));col=x//24;w=self.grid_width
  if not 0<=col<w:return []
  srow=(y//16*16-self.margin)//16;elev=self.elevation_enabled()
  return [(col,t) for t in range(self.grid_height) if t-(self.grid_cells[t*w+col]['values'][3] if elev else 0)==srow]
 def stroke_start(self,kind,event):
  """Click-and-drag in Edit heights (+1), No Walk Area and Mask layer: the first
  tile decides the action (add or remove) and every tile the pointer then
  crosses gets the same action once. Shift: the x blocks only the player."""
  self.tile_stroke={'kind':kind,'done':set(),'shift':bool(event.state&0x0001)}
  self.height_paint_last_empty=None
  if kind=='walls':
   tile=self.walk_tile_at(event);landing=self.landing_tiles(event)
   if tile is None and not landing:self.tile_stroke=None;return
   cell=self.grid_cells[tile[1]*self.grid_width+tile[0]] if tile is not None else None
   self.tile_stroke['block']=(cell is None or not cell["values"][0]&1 or (self.tile_stroke['shift'] and cell["values"][0]&0x41!=1)
                              or any(not self.grid_cells[t[1]*self.grid_width+t[0]]['values'][0]&1 for t in landing))   # anything walkable here: block it
  if kind=='mask':
   key,is_mask=self.mask_key(event)
   if key is None:self.tile_stroke=None;self.caption.set("Nothing drawn here to mask.");return
   self.tile_stroke['remove']=is_mask
  self.stroke_continue(event)
 def stroke_continue(self,event):
  st=self.tile_stroke
  if st is None:return
  if st['kind']=='height':
   tile=self.height_tile_at(event)
   if tile is None:
    return   # +1 / -1 never places tiles on empty squares
   if tile in st['done']:return
   st['done'].add(tile);self.adjust_height(event,+1);return
  if st['kind']=='mask':
   key,is_mask=self.mask_key(event)
   if key is None or key in st['done'] or is_mask!=st['remove']:return
   st['done'].add(key);self.toggle_mask(event)
   for k,_ in [self.mask_key(event)]:
    if k is not None:st['done'].add(k)   # the new ★ tile too, so the stroke never undoes it
   return
  more=[t for t in dict.fromkeys(self.walk_tiles_at(event)[1:]+self.landing_tiles(event)) if t not in st['done']]
  for t in more:   # the other x's drawn in this square, and every tile standing on it (user 2026-10-25)
   st['done'].add(t);c=self.grid_cells[t[1]*self.grid_width+t[0]]
   if st['block']:
    if not c["values"][0]&1:self.set_walk(*t,True,bits=0x01 if st['shift'] else self.block_bits())
   elif c["values"][0]&1:self.set_walk(*t,False)
  tile=self.walk_tile_at(event)
  if tile is None or tile in st['done']:
   if more:self.schedule_height_redraw()
   return
  st['done'].add(tile);tx,ty=tile
  bits=0x01 if st['shift'] else self.block_bits()
  cell=self.grid_cells[ty*self.grid_width+tx];walk=cell["values"][0]
  if st['block']:
   if walk&1 and (walk&0x41)==bits:return
   self.set_walk(tx,ty,True,bits=bits)
  else:
   if not walk&1:return
   self.set_walk(tx,ty,False)
  self.schedule_height_redraw()
  self.caption.set(f"Tile {tx}, {ty}: " + (("no-walk for the player only." if bits==1 else "no-walk for everyone. Shift+click for no-walk for the player only.") if st['block'] else "walkable."))
 def set_slope(self,event):
  """Slope brush: the square's tile gets the chosen slope (Slope byte, low 2 bits:
  flat, stairs rising up the screen, ramp rising left, ramp rising right). The
  game works out the height across the square from it (ComputeEntityGroundHeight)."""
  tile=self.height_tile_at(event)
  if tile is None:return
  tx,ty=tile;c=self.grid_cells[ty*self.grid_width+tx];at=c["offset"]+2
  kind={-3:0,-4:1,-5:2,-6:3}[self.height_brush.get()]
  v=list(c["values"]);new=(v[2]&~3)|kind
  if new==v[2]:return
  data=self.editor.session.data
  if new==data[at]:self.pending_heights.pop(at,None)
  else:self.pending_heights[at]=new
  v[2]=new;c["values"]=tuple(v);self.editor.dirty=True
  self.schedule_height_redraw()
  self.caption.set(f"Tile {tx}, {ty}: {('flat','stairs (rises up the screen)','ramp rising left','ramp rising right')[kind]}. Kept when you save or build.")
 def set_record_height(self,tx,ty,target):
  """Move a tile record to the height wanted, picture unchanged; returns where it ends up."""
  w=self.grid_width;guard=0
  while self.grid_cells[ty*w+tx]["values"][3]!=target and guard<300:
   guard+=1;step=1 if target>self.grid_cells[ty*w+tx]["values"][3] else -1
   before=self.grid_cells[ty*w+tx]["values"][3]
   if not self.move_square_height(tx,ty,step,redraw=False):break
   if not 0<=ty+step<self.grid_height or self.grid_cells[(ty+step)*w+tx]["values"][3]!=before+step:break
   ty+=step
  return tx,ty
 def wall_follows(self,tx,ty,delta):
  """+1 / -1: the wall squares under a raised tile (above a lowered one) take
  its new height, so the whole wall belongs with it."""
  w=self.grid_width;c=self.grid_cells[ty*w+tx];H=c["values"][3]
  self.redraw_height_numbers_from_grid()
  px=tx*24;py=ty*16+self.margin-(H*16 if self.elevation_enabled() else 0)
  direction=1 if delta>0 else -1;moved=0
  if delta>0:
   # the square the raised tile just left: the floor shown there becomes wall at the new height
   under=getattr(self,'height_stack',{}).get((px,py+16))
   if under is not None and under!=(tx,ty) and self.grid_cells[under[1]*w+under[0]]["values"][4]!=0xFFFF:
    if self.make_grey(None,tile=under,check=False)!=False:
     self.set_record_height(under[0],under[1],H);moved+=1
     self.redraw_height_numbers_from_grid()
  for k in range(1,17):
   sq=(px,py+16*k*direction)
   owner=getattr(self,'height_grey',{}).get(sq)
   if owner is None:
    if sq in getattr(self,'height_stack',{}):break   # a real floor: the wall ends here
    continue
   if owner==(tx,ty):continue                         # its own step face
   oc=self.grid_cells[owner[1]*w+owner[0]]
   if oc["values"][4]!=0xFFFF:break
   if oc["values"][3]!=H:self.set_record_height(owner[0],owner[1],H);moved+=1
  if moved:self.redraw_height_numbers_from_grid()
  return moved
 def undo_made_wall(self,tx,ty):
  """A square made into a wall (Make Wall) gets its floor picture back when its
  height is changed. Returns True if it was a made wall."""
  e=self.editor;made=e.database.document.get('made_walls',{}).get(str(e.current_map),[])
  entry=next((r for r in made if r['tile']==[tx,ty]),None)
  if entry is None:return False
  c=self.grid_cells[ty*self.grid_width+tx]
  if c["values"][4]!=0xFFFF:made.remove(entry);return False
  old=self.tile_rows(tx,ty);g=self.stack_grid();sc=g[2][ty*self.grid_width+tx]
  sc['walls']=tuple(entry['walls']) if entry['walls'] else None
  c["walls"]=[(None,cd,sc['walls'][0],i) for i,cd in enumerate(sc['walls'][1])] if sc['walls'] else []
  self.pending_stack_tiles.add((tx,ty))
  data=e.session.data;code=entry['code']
  for i,b in ((4,code&0xFF),(5,code>>8)):
   at=c["offset"]+i
   if data[at]==b:self.pending_heights.pop(at,None)
   else:self.pending_heights[at]=b
  v=list(c["values"]);v[4]=code;c["values"]=tuple(v)
  sv=list(sc["values"]);sv[4]=code;sc["values"]=tuple(sv)
  made.remove(entry);e.dirty=True
  self.redraw_columns([(tx,ty)],before={(tx,ty):old})
  if entry.get('height') is not None and c["values"][3]!=entry['height']:self.set_record_height(tx,ty,entry['height'])
  return True
 def make_grey(self,event,tile=None,check=True):
  """Heights 'Make grey': the clicked tile keeps its picture in the same place,
  but as a wall piece of its own record instead of its floor, so the square
  has no height of its own (a grey square), like the game's wall faces."""
  import struct
  if tile is None:tile=self.height_tile_at(event)
  if tile is None:return False
  tx,ty=tile;c=self.grid_cells[ty*self.grid_width+tx];code=c["values"][4]
  if code==0xFFFF:return False
  w=self.grid_width;h=c["values"][3];around=[]
  for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
   x,y=tx+dx,ty+dy
   if 0<=x<w and 0<=y<self.grid_height:
    n=self.grid_cells[y*w+x]
    if n["values"][4]!=0xFFFF:around.append(n["values"][3])
  if check and around and all(a==h for a in around):
   self.caption.set(f"Tile {tx}, {ty} is level with the tiles around it: no wall made.");return False
  g=self.stack_grid();sc=g[2][ty*self.grid_width+tx]
  shift,codes=sc['walls'] if sc['walls'] else (0,[])
  codes=list(codes);n=len(codes)
  if not codes:new=(1,[code])
  elif shift==0:new=(1,[code]+codes)          # pieces all below: picture goes on top of them
  elif n-shift==-1:new=(shift,codes+[code])   # pieces all above: picture goes under them
  else:
   self.caption.set(f"Tile {tx}, {ty}: a wall piece already sits behind its floor; it can't be made grey.");return False
  old=self.tile_rows(tx,ty)
  made=self.editor.database.document.setdefault('made_walls',{}).setdefault(str(self.editor.current_map),[])
  made[:]=[r for r in made if r['tile']!=[tx,ty]]
  made.append({'tile':[tx,ty],'code':code,'walls':[shift,codes] if sc['walls'] else None,'height':c["values"][3]})
  sc['walls']=new;c["walls"]=[(None,cd,new[0],i) for i,cd in enumerate(new[1])]
  self.pending_stack_tiles.add((tx,ty))
  v=list(c["values"]);v[4]=0xFFFF;c["values"]=tuple(v)
  sv=list(sc["values"]);sv[4]=0xFFFF;sc["values"]=tuple(sv)
  data=self.editor.session.data
  for i in (4,5):   # floor picture -> none (0xFFFF); the height byte is left alone
   at=c["offset"]+i
   if data[at]==0xFF:self.pending_heights.pop(at,None)
   else:self.pending_heights[at]=0xFF
  self.pending_tiles.pop(c["offset"]+3,None)
  self.editor.dirty=True
  self.redraw_columns([(tx,ty)],before={(tx,ty):old});self.schedule_height_redraw()
  self.caption.set(f"Tile {tx}, {ty} is now a wall: same picture, no height of its own. Kept when you save or build.")
 def unwall(self,event):
  """Shift+click on a wall you placed (x): walkable again, at the height of
  the tile it took over (that height was kept when the wall was placed)."""
  tile=self.height_tile_at(event)
  if tile is None:return
  tx,ty=tile;e=self.editor
  walled=e.database.document.get('walled_tiles',{}).get(str(e.current_map),[])
  cell=self.grid_cells[ty*self.grid_width+tx]
  data=e.session.data;walk_at=cell["offset"]
  if not cell["values"][0]&1:
   # walkable tile: Shift+click makes it a wall (x), keeping its height
   walk=(cell["values"][0]&~0x41)|self.block_bits()
   if walk==data[walk_at]:self.pending_heights.pop(walk_at,None)
   else:self.pending_heights[walk_at]=walk
   v=list(cell["values"]);v[0]=walk;cell["values"]=tuple(v);self.sync_stack_walk(tx,ty,walk)
   e.database.document.setdefault('walled_tiles',{}).setdefault(str(e.current_map),[])
   walled=e.database.document['walled_tiles'][str(e.current_map)]
   if [tx,ty] not in walled:walled.append([tx,ty])
   e.dirty=True;self.redraw_height_numbers_from_grid()
   self.caption.set(f"Tile {tx}, {ty} is now no-walk (x, {'only the player' if walk&0x41==1 else 'everyone'}) at height {v[3]}. Click again to make it walkable.");return
  # any wall can be unwalled, also the original map's (Mark walls / Shift+click again makes it a wall)
  walk=data[walk_at]&~0x41&0xFF
  self.pending_tiles.pop(walk_at,None)
  if walk==data[walk_at]:self.pending_heights.pop(walk_at,None)
  else:self.pending_heights[walk_at]=walk
  v=list(cell["values"]);v[0]=walk;cell["values"]=tuple(v);self.sync_stack_walk(tx,ty,walk)
  if [tx,ty] in walled:walled.remove([tx,ty])
  e.dirty=True
  self.redraw_height_numbers_from_grid()
  self.caption.set(f"Tile {tx}, {ty} unwalled: walkable at height {v[3]}.")
 def schedule_height_redraw(self,delay=40):
  """Redraw the numbers (and events) once after a burst of clicks or a drag,
  not after every single tile - this keeps painting heights smooth."""
  job=getattr(self,'height_redraw_job',None)
  if job is not None:self.editor.root.after_cancel(job)
  def run():
   self.height_redraw_job=None
   self.redraw_height_numbers_from_grid()
   if hasattr(self,'info'):self.clear_in_front_of_switches();self.draw_records()
  self.height_redraw_job=self.editor.root.after(delay,run)
 def clear_x_at(self,square):
  """After a number was put on a square that showed an x: every tile whose x is still
  drawn on that square becomes walkable (user 2026-10-21)."""
  for _ in range(3):
   self.redraw_height_numbers_from_grid()
   t=getattr(self,'drawn_x',{}).get(square)
   if t is None or not self.grid_cells[t[1]*self.grid_width+t[0]]["values"][0]&1:return
   self.set_walk(t[0],t[1],False)
 def paint_height(self,event,square=None):
  """Edit heights number brush, one square at a time (user 2026-10-25: 'One edits the
  other'): the edit is tried, and kept only when every other square still shows what
  it showed and the map picture is unchanged. Otherwise the clicked square is split
  off onto the record of its own row (paint_square_alone). If neither works the edit
  is undone and nothing changes."""
  if square is None:
   x=int(self.canvas.canvasx(event.x));y=int(self.canvas_y(event));square=(x//24*24,y//16*16)
  target=self.height_brush.get()
  wall_mode=bool(getattr(self,'height_wall_mode',None) is not None and self.height_wall_mode.get())
  key=(square,target,wall_mode)
  if key==getattr(self,'height_paint_alone_last',None):return
  if wall_mode:   # Wall mode (user 2026-10-25): the square becomes a grey wall of that height; no record moves
   db=getattr(self.editor,'database',None);ws=(db.document if db else {}).setdefault('wall_squares',{}).setdefault(str(getattr(self.editor,'current_map',None)),[])
   col,srow=square[0]//24,(square[1]-self.margin)//16
   ws[:]=[r for r in ws if r[:2]!=[col,srow]];ws.append([col,srow,target])
   self.block_wall_squares([(col,srow,target)])   # a real wall of that height, in the map data itself (user 2026-10-25)
   self.height_paint_alone_last=key;self.editor.dirty=True
   self.caption.set(f"Square {col}, {srow} is now a wall of height {target}. Kept when you save or build.")
   self.schedule_height_redraw();return
  db=getattr(self.editor,'database',None);ws=(db.document if db else {}).get('wall_squares',{}).get(str(getattr(self.editor,'current_map',None)))
  if ws:ws[:]=[r for r in ws if r[:2]!=[square[0]//24,(square[1]-self.margin)//16]]   # a number painted on a wall square ends the wall
  tx=square[0]//24
  if not 0<=tx<self.grid_width:return
  # The number goes on the tile that is already on this square (user 2026-10-25): its
  # own height is set; no other tile is moved, swapped or borrowed.
  tile=getattr(self,'height_shown',{}).get(square) or getattr(self,'height_stack',{}).get(square)
  # Grey square / red x (user 2026-10-26): the picked number is forced on that tile.
  # An x: its own tile gets the height (the x stays). A grey square with no tile of its own:
  # it gets a tile at the picked number (force_empty). Nothing else changes here.
  xt=getattr(self,'drawn_x',{}).get(square)
  if xt is not None:   # a red x (also one made No walk in Tile fix): walkable, then the number below
   tile=xt
   if self.grid_cells[xt[1]*self.grid_width+xt[0]]['values'][0]&1:
    self.set_walk(xt[0],xt[1],False);self.editor.dirty=True
    if self.grid_cells[xt[1]*self.grid_width+xt[0]]['values'][3]==target:
     self.height_paint_alone_last=key;self.caption.set(f"Tile ({xt[0]}, {xt[1]}): walkable at height {target}.");self.schedule_height_redraw();return
  elif tile is None and square in getattr(self,'height_grey',{}):
   self.height_paint_alone_last=key;self.force_empty(square,target);return
  if tile is not None:
   ttx,tty=tile;w=self.grid_width;c=self.grid_cells[tty*w+ttx];v=c['values']
   self.height_paint_alone_last=key
   if v[3]==target:return
   old=self.tile_rows(ttx,tty)
   self.pending_heights[c['offset']+3]=target;c['values']=v[:3]+(target,)+v[4:]
   g=getattr(self,'pending_stack_grid',None)
   if g is not None:sc=g[2][tty*w+ttx];sv=list(sc['values']);sv[3]=target;sc['values']=tuple(sv)
   self.last_height_edit=(ttx,tty);self.editor.dirty=True
   self.redraw_columns([(ttx,tty)],before={(ttx,tty):old})
   self.caption.set(f"Tile ({ttx}, {tty}): height {v[3]} -> {target}.")
   self.schedule_height_redraw();return
  before=self.height_view_values()
  if before.get(square)==self.wanted_square_value(target,wall_mode):self.height_paint_alone_last=key;return
  pics={tx:self.column_picture(tx)}   # every height edit stays in the clicked column
  empty=not self.square_has_picture(square)
  snap=self.height_snapshot()
  calls=[];real_redraw=self.__dict__.get('redraw_columns');real_sched=self.__dict__.get('schedule_height_redraw')
  self.redraw_columns=lambda tiles,before=None:calls.append((list(tiles),before))
  self.schedule_height_redraw=lambda delay=40:None
  caption=None
  try:
   for attempt in (lambda:self._paint_height_body(None,square),lambda:self.paint_square_alone(square,target,wall_mode)):
    try:attempt();break   # always keep the edit: 'changes another square' check removed (user 2026-10-25)
    except (IndexError,ValueError,KeyError):self.height_restore(snap)
   else:caption=f"Height {target} can't be put on this square without changing another square: nothing changed."
  finally:
   if real_redraw is None:self.__dict__.pop('redraw_columns',None)
   else:self.redraw_columns=real_redraw
   if real_sched is None:self.__dict__.pop('schedule_height_redraw',None)
   else:self.schedule_height_redraw=real_sched
  self.height_paint_alone_last=key
  for tiles,b in calls:self.redraw_columns(tiles,before=b)
  if caption:self.caption.set(caption)
  self.schedule_height_redraw()
 @staticmethod
 def wanted_square_value(target,wall_mode):
  return frozenset({'g'}) if wall_mode else frozenset({str(target)})
 def height_view_values(self):
  """{square: frozenset of what Edit heights draws there ('g' grey, number, 'x')},
  worked out on a recording canvas (the real canvas is not touched)."""
  real=self.canvas;items=[]
  class _Rec:
   def create_text(s,x,y,text='',tags=(),**k):items.append(('t',x,y,text,tuple(tags)));return len(items)
   def create_image(s,x,y,tags=(),**k):items.append(('g',x,y,None,tuple(tags)));return len(items)
   def delete(s,tag):items[:]=[i for i in items if tag not in i[4]]
   def canvasx(s,v):return v
   def canvasy(s,v):return v
   def find_withtag(s,t):return [n for n,i in enumerate(items) if t in i[4]]
   def __getattr__(s,n):return lambda *a,**k:None
  self.canvas=_Rec();grey=self.__dict__.get('grey_square')
  self.grey_square=lambda x,y,tags:self.canvas.create_image(x,y,tags=tags)
  try:self.redraw_height_numbers_from_grid()
  finally:
   self.canvas=real
   if grey is None:self.__dict__.pop('grey_square',None)
   else:self.grey_square=grey
  crop=getattr(self,'map_crop_top',0);out={}
  for kind,x,y,text,_ in items:
   y=y+crop   # back to map coordinates
   if kind=='g':out.setdefault((int(x),int(y)),set()).add('g')
   else:out.setdefault((int(x)//24*24,int(y)//16*16),set()).add(text)
  return {k:frozenset(v) for k,v in out.items()}
 def square_has_picture(self,square):
  tx=square[0]//24;row=(square[1]-self.margin)//16;w=self.grid_width
  return any(r==row for k in range(self.grid_height) for r,_,_ in self.record_pieces(self.grid_cells[k*w+tx]))
 def height_paint_isolated(self,square,before,pics,target,wall_mode,empty):
  """True when the clicked square shows the painted value, no other square changed
  and the picture is the same (a square with nothing drawn may get its new tile)."""
  after=self.height_view_values()
  if after.get(square)!=self.wanted_square_value(target,wall_mode):return False
  if any(before.get(k)!=after.get(k) for k in set(before)|set(after) if k!=square):return False
  tx=square[0]//24
  now=self.column_picture(tx)
  if now==pics[tx]:return True
  if not empty:return False
  band=len(now)//(self.grid_height*16+self.margin);y0=square[1]*band;y1=y0+16*band   # rows of the clicked square only
  return now[:y0]==pics[tx][:y0] and now[y1:]==pics[tx][y1:]
 def height_snapshot(self):
  import copy
  doc=self.editor.database.document
  return dict(cells=[(c['values'],list(c['walls'])) for c in self.grid_cells],
              pending=dict(self.pending_heights),grid=copy.deepcopy(getattr(self,'pending_stack_grid',None)),
              tiles=set(getattr(self,'pending_stack_tiles',set())),
              doc={k:copy.deepcopy(doc[k]) if k in doc else None for k in ('height_walls','made_walls','walled_tiles')},
              attrs={k:getattr(self,k,None) for k in ('last_height_edit','height_paint_last','height_paint_last_empty')},
              dirty=getattr(self.editor,'dirty',False))
 def height_restore(self,s):
  for c,(v,walls) in zip(self.grid_cells,s['cells']):c['values']=v;c['walls']=walls
  self.pending_heights.clear();self.pending_heights.update(s['pending'])
  self.pending_stack_grid=s['grid'];self.pending_stack_tiles=s['tiles']
  doc=self.editor.database.document
  for k,v in s['doc'].items():
   if v is None:doc.pop(k,None)
   else:doc[k]=v
  for k,v in s['attrs'].items():setattr(self,k,v)
  self.editor.dirty=s['dirty']
 def paint_square_alone(self,square,target,wall_mode):
  """Give the clicked square a record of its own: the record of row
  (screen row + height) gets the picked height and, as its floor, the picture drawn
  on top of that square; the pictures it drew before stay where they were as its
  wall pieces. The picture's old owner keeps everything else."""
  import struct
  w=self.grid_width;elev=self.elevation_enabled();data=self.editor.session.data
  tx=square[0]//24;s=(square[1]-self.margin)//16;ny=s+(target if elev else 0)
  if not (0<=tx<w and 0<=ny<self.grid_height and 0<=target<=255):return
  top=None
  for k in range(self.grid_height):
   for i,(r,cd,fl) in enumerate(self.record_pieces(self.grid_cells[k*w+tx])):
    if r==s:top=(k,cd,fl)
  if top is None:return
  k_top,code,is_floor=top
  def write(row,rec):
   c=self.grid_cells[row*w+tx]
   for i,b in enumerate(rec):
    o=c['offset']+i
    if b==data[o]:self.pending_heights.pop(o,None)
    else:self.pending_heights[o]=b
   c['values']=struct.unpack('<4BHh',bytes(rec))
   g=self.stack_grid();g[2][row*w+tx]['values']=c['values'];self.pending_stack_tiles.add((tx,row))
  read=lambda row:bytearray(self.pending_byte(self.grid_cells[row*w+tx]['offset']+i) for i in range(8))
  n=self.grid_cells[ny*w+tx];old={r:cd for r,cd,_ in self.record_pieces(n)}
  if k_top!=ny:   # the picture leaves its old owner
   o=self.grid_cells[k_top*w+tx]
   if is_floor:
    rec=read(k_top);rec[4:6]=struct.pack('<H',0xFFFF);write(k_top,rec)
   else:
    keep={r:cd for r,cd,f in self.record_pieces(o) if not f and r!=s}
    fl=k_top-(o['values'][3] if elev else 0)
    walls=self.rebased_walls({r-fl:cd for r,cd in keep.items()})
    if walls is False:return
    self.set_cell_walls(tx,k_top,walls)
  old.pop(s,None)
  rec=read(ny);like=read(k_top)
  rec[0]=(like[0]&~0x41&0xFF)|(0x41 if wall_mode else 0);rec[1]=like[1];rec[2]=like[2];rec[3]=target
  rec[4:6]=struct.pack('<H',code);write(ny,rec)
  walls=self.rebased_walls({r-s:cd for r,cd in old.items()})
  if walls is False:return
  self.set_cell_walls(tx,ny,walls)
  hw=self.editor.database.document.setdefault('height_walls',{}).setdefault(str(self.editor.current_map),[])
  if wall_mode and [tx,ny] not in hw:hw.append([tx,ny])
  if not wall_mode and [tx,ny] in hw:hw.remove([tx,ny])
  self.last_height_edit=(tx,ny);self.editor.dirty=True
  self.caption.set(f"Square now {'is a wall of height' if wall_mode else 'reads'} {target} (record {tx}, {ny}); pictures stay where they are. Kept when you save or build.")
 def _paint_height_body(self,event,square=None):
  """A picked height number is forced onto the square you click: the square
  keeps its picture and now reads that number. The tile record is moved to the
  row that is drawn there at that height, and the tile it swaps with is
  shifted the other way, so every picture stays where it is (user 2026-10-11:
  'force a number on a tile even if everything shifts')."""
  if square is None:
   x=int(self.canvas.canvasx(event.x));y=int(self.canvas_y(event));square=(x//24*24,y//16*16)
   cell=self.height_tile_at(event)
  else:cell=getattr(self,'height_stack',{}).get(square)
  shown=getattr(self,'height_shown',{}).get(square)
  if shown is not None:cell=shown   # the number drawn here belongs to a floor behind a face: that floor is edited (user 2026-10-25)
  # an x drawn here: the number goes to the tile of that x, which becomes walkable (user 2026-10-21)
  unmark=getattr(self,'drawn_x',{}).get(square)
  if unmark is not None and not (getattr(self,'height_wall_mode',None) is not None and self.height_wall_mode.get()):cell=unmark
  else:unmark=None
  db=getattr(self.editor,'database',None);walls=(db.document if db else {}).setdefault('height_walls',{}).setdefault(str(getattr(self.editor,'current_map',None)),[])
  hw=getattr(self,'height_grey',{}).get(square)
  if hw is not None and list(hw) in walls:   # a Wall mode wall: painting it again edits that wall
   cell=hw
   if not self.height_wall_mode.get():walls.remove(list(hw));self.set_walk(*hw,False)
  # A grey square (no number of its own) or a square with nothing is an empty
  # square: it gets a tile at the picked number, it never moves the grey tile.
  if cell is None or (square in getattr(self,'height_grey',{}) and cell!=hw):
   result=self.force_empty(square)
   if unmark is not None:self.clear_x_at(square)   # the x drawn here goes
   return result
  if cell is None or (cell,square)==getattr(self,'height_paint_last',None):return
  tx,ty=cell;target=self.height_brush.get();w=self.grid_width
  wall_mode=getattr(self,'height_wall_mode',None) is not None and self.height_wall_mode.get()
  if not wall_mode:self.undo_made_wall(tx,ty)
  # Only this tile changes: its record goes to the row drawn here at the new
  # height (row = screen row + height). The record that was in that row swaps
  # into the row this tile left and keeps its own height; every picture stays
  # where it was drawn. Walls (x) stay on their own x/y.
  ny=ty+(target-self.grid_cells[ty*w+tx]["values"][3])
  if not 0<=target<=255:self.caption.set("Heights go from 0 to 255.");return
  if not 0<=ny<self.grid_height:self.caption.set(f"Height {target} here would need row {ny}, which is off the map.");return
  if ny!=ty:
   self.swap_for_height(tx,ty,ny,target)
   ty=ny
  if wall_mode:   # Wall mode (user 2026-10-25): the moved tile becomes a grey wall of that height
   self.make_wall_bits(tx,ty)
   if [tx,cell[1]] in walls:walls.remove([tx,cell[1]])
   if [tx,ty] not in walls:walls.append([tx,ty])
  self.height_paint_last=((tx,ty),square);self.last_height_edit=(tx,ty)   # the square shows the tile you painted
  self.fix_masks([tx])
  now=self.grid_cells[ty*w+tx]["values"][3]
  if unmark is not None:self.clear_x_at(square)   # the x that was drawn here goes: walkable at its new height
  self.schedule_height_redraw()
  if now==target:self.caption.set(f"Square now reads {target} (tile record moved from row {cell[1]} to row {ty}; pictures stay where they are). Kept when you save or build.")
  else:self.caption.set(f"Could only get this square to {now} (map edge or height limit).")
 def make_wall_bits(self,tx,ty):
  """Byte 0 |= 0x41 on one tile (no-walk for everyone), waiting with the heights."""
  w=self.grid_width;c=self.grid_cells[ty*w+tx];at=c['offset'];data=self.editor.session.data
  walk=self.pending_byte(at)|0x41
  if walk==data[at]:self.pending_heights.pop(at,None)
  else:self.pending_heights[at]=walk
  v=list(c['values']);v[0]=walk;c['values']=tuple(v)
  g=getattr(self,'pending_stack_grid',None)
  if g is not None:sc=g[2][ty*w+tx];sv=list(sc['values']);sv[0]=walk;sc['values']=tuple(sv)
  self.editor.dirty=True
 def rebased_walls(self,pieces):
  """(shift, codes) for pieces {row offset from the floor: code}; gaps are empty (0xFFFF)."""
  if not pieces:return None
  lo,hi=min(pieces),max(pieces);shift=1-lo
  if not -128<=shift<=127 or hi-lo+1>255:return False
  return (shift,[pieces.get(r,0xFFFF) for r in range(lo,hi+1)])
 def record_pieces(self,cell):
  """Every picture a record draws, in drawing order: [(screen row, code, is_floor)]."""
  v=cell['values'];floor=cell['y']-(v[3] if self.elevation_enabled() else 0)
  out=[(floor,v[4],True)] if v[4]!=0xFFFF else []
  for _,cd,sh,i in cell['walls']:
   if cd!=0xFFFF:out.append((floor+i+1-sh,cd,False))
  return out
 def set_cell_walls(self,tx,ty,walls):
  """Wall pieces of one record, in the shown grid and the waiting wall-stack copy."""
  c=self.grid_cells[ty*self.grid_width+tx]
  c['walls']=[(None,cd,walls[0],i) for i,cd in enumerate(walls[1])] if walls else []
  g=self.stack_grid();g[2][ty*self.grid_width+tx]['walls']=(walls[0],list(walls[1])) if walls else None
  self.pending_stack_tiles.add((tx,ty));self.editor.dirty=True
 def column_picture(self,tx,override=None):
  """The column as it is drawn (to check that pictures stay where they were)."""
  from area_map import render_region
  w=self.grid_width;cells=[]
  for k in range(self.grid_height):
   if override and k in override:cells.append(override[k]);continue
   c=self.grid_cells[k*w+tx]
   cells.append({'values':c['values'],'walls':((c['walls'][0][2],[x[1] for x in c['walls']]) if c['walls'] else None)})
  return render_region(self.renderer,cells,1,self.margin,(0,0,24,self.grid_height*16+self.margin),self.elevation_enabled()).tobytes()
 def swap_for_height(self,tx,ty,ny,target):
  """Number brush: the clicked tile's record (row ty) moves to row ny at the new
  height, so its picture stays on the clicked square. The record in row ny swaps
  into row ty and keeps its height. Every other picture the two records drew stays
  on the same square, carried as wall pieces by whichever of the two records can
  draw it there (the arrangement that draws the column exactly as before wins).
  Walls (x) keep their x/y: if either row was a wall, both rows keep the
  walkability they had."""
  import struct
  data=self.editor.session.data;w=self.grid_width;elev=self.elevation_enabled()
  g=self.stack_grid()   # the waiting wall-stack copy must exist before records move
  a=self.grid_cells[ty*w+tx];b=self.grid_cells[ny*w+tx]
  old_rows={(tx,ty):self.tile_rows(tx,ty),(tx,ny):self.tile_rows(tx,ny)}
  walls_here=self.marked_wall(tx,ty) or self.marked_wall(tx,ny)
  bits={y:self.pending_byte(self.grid_cells[y*w+tx]['offset'])&0x41 for y in (ty,ny)}
  ra=bytearray(self.pending_byte(a['offset']+i) for i in range(8));rb=bytearray(self.pending_byte(b['offset']+i) for i in range(8))
  ra[3]=target
  if walls_here:ra[0]=(ra[0]&~0x41)|bits[ny];rb[0]=(rb[0]&~0x41)|bits[ty]
  pa=[('a',)+p for p in self.record_pieces(a)];pb=[('b',)+p for p in self.record_pieces(b)]
  order=pa+pb if ny>ty else pb+pa          # the order they were drawn in
  hb=rb[3];floor_ty=ty-(hb if elev else 0);floor_ny=ny-(target if elev else 0)
  bcode=struct.unpack_from('<H',rb,4)[0]
  def layout(pref,keep_b_floor):
   runs={'ty':{},'ny':{}};layout.moves=0
   first,second=('ty','ny') if ty<ny else ('ny','ty')   # which of the two records is drawn first
   for owner,row,code,is_floor in order:
    if owner=='a' and is_floor:continue    # the moved record's own floor
    t=pref[owner];o='ny' if t=='ty' else 'ty'
    if row in runs[t] and row not in runs[o]:
     # two pictures on one square: the one drawn first goes to the record drawn first
     if t==second:runs[first][row]=runs[t][row];runs[t][row]=code
     else:runs[second][row]=code
     continue
    runs[t][row]=code
    if (owner,t) in (('a','ny'),('b','ty')):layout.moves+=1   # drawn in another row's turn: masks sprites differently
   if ny>ty:
    # raising: the squares from the tile's top down to its own row are its face.
    # They become its wall pieces (showing what is drawn there now), so the face
    # is drawn in front of anyone standing behind it, as a wall should be.
    for r in range(floor_ny+1,floor_ny+(ny-ty)+1):
     if r in top:runs['ny'][r]=top[r]
   return runs
  def build(runs,keep_b_floor):
   wt=self.rebased_walls({r-floor_ty:c for r,c in runs['ty'].items()})
   wn=self.rebased_walls({r-floor_ny:c for r,c in runs['ny'].items()})
   if wt is False or wn is False:return None
   return (bcode if keep_b_floor else 0xFFFF),wt,wn
  def score(lay):
   fb,wt,wn=lay;rb2=bytearray(rb);rb2[4:6]=struct.pack('<H',fb)
   over={ty:{'values':struct.unpack('<4BHh',bytes(rb2)),'walls':wt},ny:{'values':struct.unpack('<4BHh',bytes(ra)),'walls':wn}}
   pic=self.column_picture(tx,over)
   return [k//band for k in range(0,len(pic),band) if pic[k:k+band]!=want[k:k+band]]
  want=self.column_picture(tx);band=24*4*16
  # what was drawn last (on top) on each square of the column before
  top={}
  for k in range(self.grid_height):
   for row,code,_ in self.record_pieces(self.grid_cells[k*w+tx]):top[row]=code
  best=None
  for keep in ((False,True) if bcode!=0xFFFF else (False,)):
   for pref in ({'a':'ty','b':'ny'},{'a':'ny','b':'ny'},{'a':'ty','b':'ty'},{'a':'ny','b':'ty'}):
    runs=layout(pref,keep);moves=layout.moves;lay=build(runs,keep)
    if lay is None:continue
    bad=score(lay)
    for _ in range(4):   # a picture that was on top of a square is put back on top
     if not bad:break
     fixed=False
     for r in bad:
      code=top.get(r-self.margin//16)
      if code is None:continue
      for run in ('ny','ty') if ny>ty else ('ty','ny'):
       if r-self.margin//16 in runs[run]:continue
       trial={'ty':dict(runs['ty']),'ny':dict(runs['ny'])};trial[run][r-self.margin//16]=code
       tl=build(trial,keep)
       if tl is None:continue
       tb=score(tl)
       if len(tb)<len(bad):runs,lay,bad,fixed=trial,tl,tb,True;break
     if not fixed:break
    if best is None or (len(bad),moves)<best[0]:best=((len(bad),moves),lay)
    if not bad and not moves:break
   if best and best[0]==(0,0):break
  if best is None:lay=(bcode,(g[2][ny*w+tx]['walls'] or None),(g[2][ty*w+tx]['walls'] or None))   # too far apart: walls follow their record
  else:lay=best[1]
  fb,wt,wn=lay;rb[4:6]=struct.pack('<H',fb)
  e=self.editor
  for r in e.database.document.get('made_walls',{}).get(str(e.current_map),[]):
   if r['tile']==[tx,ty]:r['tile']=[tx,ny]
   elif r['tile']==[tx,ny]:r['tile']=[tx,ty]
  for rc,raw in ((b,ra),(a,rb)):
   for i,v in enumerate(raw):
    o=rc['offset']+i
    if v==data[o]:self.pending_heights.pop(o,None)
    else:self.pending_heights[o]=v
  a['values']=struct.unpack('<4BHh',bytes(rb));b['values']=struct.unpack('<4BHh',bytes(ra))
  ga,gb=g[2][ty*w+tx],g[2][ny*w+tx]
  ga['values'],gb['values']=a['values'],b['values'];self.pending_stack_tiles.update({(tx,ty),(tx,ny)})
  self.set_cell_walls(tx,ty,wt);self.set_cell_walls(tx,ny,wn)
  self.redraw_columns([(tx,ty),(tx,ny)],before=old_rows);e.dirty=True
 def original_pieces(self):
  """The game's own wall pieces on this map, {(x, y): {(offset from floor, code)}}, or None for a new map."""
  e=self.editor;key=(id(e.session.original),e.current_map)
  cache=getattr(self,'_original_pieces',{})
  if key not in cache:
   try:
    from editor_session import EditSession
    from map_area_copy import cells_of
    w,h,cells=cells_of(EditSession(bytes(e.session.original),verify=False,allow_compatible=True),e.current_map)
    out={}
    for i,c in enumerate(cells):
     if c['walls']:
      sh,codes=c['walls'];out[(i%w,i//w)]={(k+1-sh,cd) for k,cd in enumerate(codes)}
    cache[key]=out
   except Exception:cache[key]=None
   self._original_pieces=cache
  return cache[key]
 def fix_masks(self,cols=None,redraw=True,only=None):
  """Wall pieces that wrongly cover Alundra: a piece of a tile that is not taller
  than the walkable floor it is drawn over (or just above), so it is drawn in front
  of him while he stands there. Each one is taken off, or, when the picture has to
  stay, moved into that floor's own picture. Pillar faces (taller than the floor
  behind them), the game's own pieces and mask-layer (star) tiles are left alone.
  The picture of the map never changes. Returns the number of pieces fixed.
  only: just these tiles' own pieces (a height edit must not rework the rest of
  its column: every +1 used to move pictures down the whole column)."""
  if not self.elevation_enabled():return 0
  import struct
  e=self.editor;w,hh=self.grid_width,self.grid_height;data=e.session.data
  orig=self.original_pieces()
  stars=set()
  for r in e.database.document.get('masked_tiles',{}).get(str(e.current_map),[]):
   if isinstance(r,dict):
    for k in ('mask','origin'):
     if r.get(k):stars.add(tuple(r[k][:2]))
  fixed=0;touched={}
  for tx in (cols if cols is not None else range(w)):
   if (tx,None) in stars:continue
   want=None
   walk={}
   for y in range(hh):
    v=self.grid_cells[y*w+tx]['values']
    if not v[0]&1:walk.setdefault(y-v[3],[]).append(y)
   for y in range(hh):
    c=self.grid_cells[y*w+tx]
    if not c['walls'] or (tx,y) in stars or (only is not None and (tx,y) not in only):continue
    v=c['values'];floor=y-v[3]
    for row,cd,is_floor in list(self.record_pieces(c)):
     if is_floor:continue
     # a wall piece is drawn over Alundra when he stands on a tile of the same row or
     # one higher up the map, on its square or up to two squares below it (his body)
     under=[q for s in (row,row+1,row+2) for q in walk.get(s,[]) if q<=y and (tx,q) not in stars and self.grid_cells[q*w+tx]['values'][3]>=v[3]]
     if not under:continue
     if orig is not None and (row-floor,cd) in orig.get((tx,y),()):continue   # the game's own piece
     if want is None:want=self.column_picture(tx)
     keep={r:c2 for r,c2,f in self.record_pieces(c) if not f};keep.pop(row,None)
     walls=self.rebased_walls({r-floor:c2 for r,c2 in keep.items()})
     if walls is False:continue
     tries=[None]+[q for q in sorted(set(under),reverse=True) if q-self.grid_cells[q*w+tx]['values'][3]==row]
     for q in tries:
      over={y:{'values':v,'walls':walls}}
      if q==y:over[y]={'values':v[:4]+(cd,)+v[5:],'walls':walls}   # into its own floor
      elif q is not None:
       qv=list(self.grid_cells[q*w+tx]['values']);qv[4]=cd;qc=self.grid_cells[q*w+tx]
       over[q]={'values':tuple(qv),'walls':((qc['walls'][0][2],[x[1] for x in qc['walls']]) if qc['walls'] else None)}
      if self.column_picture(tx,over)!=want:continue
      for t in [(tx,y)]+([(tx,q)] if q is not None else []):touched.setdefault(t,self.tile_rows(*t))
      self.set_cell_walls(tx,y,walls)
      if q is not None:   # the picture becomes that floor's own (drawn under Alundra)
       qc=self.grid_cells[q*w+tx];qv=list(qc['values']);qv[4]=cd;qc['values']=tuple(qv)
       for i,b in ((4,cd&0xFF),(5,cd>>8)):
        at=qc['offset']+i
        if data[at]==b:self.pending_heights.pop(at,None)
        else:self.pending_heights[at]=b
       g=self.stack_grid();sv=list(g[2][q*w+tx]['values']);sv[4]=cd;g[2][q*w+tx]['values']=tuple(sv)
      fixed+=1;break
  if fixed:
   e.dirty=True
   if redraw:self.redraw_columns(list(touched),before=touched);self.schedule_height_redraw()
  return fixed
 def fix_masks_button(self):
  n=self.fix_masks()
  self.caption.set(f"Fixed {n} wall piece(s) drawn over Alundra by mistake; the map looks the same. Kept when you save or build." if n else "No masking problems found on this map.")
 def force_empty(self,square,target=None):
  """An empty square (nothing drawn) given a height: a floor tile is put in
  the record that is drawn on this square at that height (row = screen row +
  height), walkable, so the square now shows a tile at the picked number.
  The picture is the selected tile brush, else the nearest floor beside it."""
  import struct
  if (square,target if target is not None else self.height_brush.get())==getattr(self,'height_paint_last_empty',None):return
  px,py=square;target=self.height_brush.get() if target is None else target;w=self.grid_width;data=self.editor.session.data
  tx=px//24;ty=(py-self.margin)//16+(target if self.elevation_enabled() else 0)
  if not (0<=tx<w and 0<=ty<self.grid_height):self.caption.set(f"Height {target} here would be off the map (row {ty}).");return
  code=self.brush if isinstance(self.brush,int) and self.brush!=0xFFFF else None
  src=None
  for r in range(1,max(w,self.grid_height)):
   for dx,dy in ((-r,0),(r,0),(0,-r),(0,r)):
    x,y=tx+dx,ty+dy
    if 0<=x<w and 0<=y<self.grid_height:
     c=self.grid_cells[y*w+x]
     if c['values'][4]!=0xFFFF and not c['values'][0]&1:src=c;break
   if src:break
  if code is None and src is None:   # nothing nearby: copy any walkable floor tile on the map
   src=next((c for c in self.grid_cells if c['values'][4]!=0xFFFF and not c['values'][0]&1),None)
  dst=self.grid_cells[ty*w+tx];old_rows=self.tile_rows(tx,ty)
  wall=self.marked_wall(tx,ty);drawn=self.record_pieces(dst)   # pictures this record draws now stay where they are
  read=lambda o:bytes(self.pending_byte(o+i) for i in range(8))
  rec=bytearray(read(dst['offset']));like=read(src['offset']) if src else rec
  rec[0]=(rec[0]&0x41)|(like[0]&~0x41&0xFF) if wall else like[0]&0xFE   # a wall (x) keeps its x
  if getattr(self,'height_wall_mode',None) is not None and self.height_wall_mode.get():rec[0]|=0x41   # Wall mode: a wall (no-walk) of that height
  rec[1]=like[1];rec[2]=like[2];rec[3]=target
  rec[4:6]=struct.pack('<H',code if code is not None else struct.unpack_from('<H',like,4)[0])
  for i,b in enumerate(rec):
   if b==data[dst['offset']+i]:self.pending_heights.pop(dst['offset']+i,None)
   else:self.pending_heights[dst['offset']+i]=b
  dst['values']=struct.unpack('<4BHh',bytes(rec))
  g=self.stack_grid();sv=list(g[2][ty*w+tx]['values']);sv[0]=dst['values'][0];sv[3]=target;sv[4]=dst['values'][4];g[2][ty*w+tx]['values']=tuple(sv)
  nf=ty-(target if self.elevation_enabled() else 0);pieces={}
  for r,cd,_ in drawn:
   if r!=nf:pieces[r-nf]=cd
  rebased=self.rebased_walls(pieces)
  if rebased is not False and (pieces or dst['walls']):self.set_cell_walls(tx,ty,rebased)
  self.pending_stack_tiles.add((tx,ty))
  self.height_paint_last_empty=(square,target)
  self.fix_masks([tx],redraw=False,only={(tx,ty)})
  self.redraw_columns([(tx,ty)],before={(tx,ty):old_rows});self.schedule_height_redraw()
  self.editor.dirty=True
  self.caption.set(f"Empty square now has a tile at height {target} (record {tx}, {ty}). Kept when you save or build.")
 def adjust_height(self,event,delta,cell=None):
  cell=cell or self.height_tile_at(event)
  if cell is None:return
  tx,ty=cell
  # Clicks only change the number: the heights are written to the game data
  # together (one undo step) when you save, build, change map, undo or leave
  # Edit heights. The picture is redrawn when height editing ends.
  # Right-click below height 0 makes the tile no-walk (walkability bit 0x01,
  # shown as a red x); a left-click on an x makes it walkable again.
  # pending_heights holds every changed byte of the tile (walkability, height).
  old_rows=self.tile_rows(tx,ty)
  cell=self.grid_cells[ty*self.grid_width+tx];data=self.editor.session.data
  walk_at=cell["offset"];offset=cell["offset"]+3
  walk=self.pending_heights.get(walk_at,data[walk_at]);height=self.pending_heights.get(offset,data[offset])
  def keep(at,value):
   if value==data[at]:self.pending_heights.pop(at,None)
   else:self.pending_heights[at]=value
  # Only this tile's height changes; no other tile is moved or changed.
  if False:pass   # walls (x) are edited like any tile in Edit heights; they stay walls
  else:
   value=height+delta
   if value<0:
    self.caption.set(f"Tile {tx}, {ty} is already at height 0.");return   # never turns a tile into a locked x
   elif value>255:self.caption.set("Tile height is already at its byte limit");return
   else:
    keep(offset,value);height=value;text=str(value);what=f"height {value}"
    self.step_face(tx,ty,delta)
    # A raised tile builds a pillar: the floors it rises in front of stay as they
    # are (behind it, with their own heights). -1 still gives back floors that an
    # earlier +1 emptied.
    if delta<0:self.raise_empties(tx,ty,value,delta)
  values=list(cell["values"]);values[0]=walk;values[3]=height;cell["values"]=tuple(values)
  self.last_height_edit=(tx,ty)
  g0=getattr(self,'pending_stack_grid',None)
  if g0 is not None:sc0=g0[2][ty*self.grid_width+tx];sv0=list(sc0['values']);sv0[0]=walk;sv0[3]=height;sc0['values']=tuple(sv0)
  self.fix_masks([tx],redraw=False,only={(tx,ty)})   # a wall turned back into floor: nothing may still be drawn over Alundra there
  g=getattr(self,'pending_stack_grid',None)
  if g is not None:   # keep the waiting wall-stack copy in step (it writes walkability back)
   sc=g[2][ty*self.grid_width+tx];sv=list(sc['values']);sv[0]=walk;sv[3]=height;sc['values']=tuple(sv)
  # The picture moves at once (as it will in game) and every number follows.
  self.redraw_columns([(tx,ty)],before={(tx,ty):old_rows})
  self.redraw_height_numbers_from_grid()
  if hasattr(self,'info'):self.clear_in_front_of_switches();self.draw_records()   # events re-check which tiles in front cover them
  self.caption.set(f"Tile {tx}, {ty}: {what}. {len(self.pending_heights)} change(s) are kept when you save or build.")
 def wall_under(self,tx,ty):
  """Wall mode: grey wall pieces (the tile's own picture) fill the squares under
  the tile at (tx,ty), from its floor down to the first square below that already
  shows a floor tile (or down to height 0)."""
  w=self.grid_width;c=self.grid_cells[ty*w+tx];H=c["values"][3];code=c["values"][4]
  if code==0xFFFF or H<=0:return 0
  sr=ty-H;n=H
  for k in range(1,H+1):
   if any(y!=ty and self.grid_cells[y*w+tx]["values"][4]!=0xFFFF and y-self.grid_cells[y*w+tx]["values"][3]==sr+k for y in range(self.grid_height)):
    n=k-1;break
  if n<=0:return 0
  g=self.stack_grid();sc=g[2][ty*w+tx]
  if sc['walls'] and sc['walls'][0]!=0:return 0   # pieces above the floor already: leave them
  sc['walls']=(0,[code]*n);c["walls"]=[(None,code,0,i) for i in range(n)]
  self.pending_stack_tiles.add((tx,ty));self.editor.dirty=True
  return n
 def marked_wall(self,tx,ty):
  """A no-walk (x) square that is a wall: it has a picture or wall pieces, or you
  marked it. The number brush never moves these; they stay on the same spot."""
  if not (0<=ty<self.grid_height):return False
  c=self.grid_cells[ty*self.grid_width+tx]
  if not c['values'][0]&1:return False
  if c['values'][4]!=0xFFFF or c['walls']:return True
  e=self.editor;walled=e.database.document.get('walled_tiles',{}).get(str(e.current_map),[])
  return [tx,ty] in walled
 def move_square_height(self,tx,ty,delta,redraw=True):
  """Raise/lower a square without moving its picture. The game draws a tile
  at (row - height), so the whole 8-byte tile record moves one row down
  (raise) or up (lower) and its height changes by the same step: it is drawn
  in the same place but counts as higher/lower. The square it leaves becomes
  empty no-walk ground; whatever was in the row it moves into is replaced."""
  masks={tuple(r['mask']) for r in self.editor.database.document.get('masked_tiles',{}).get(str(self.editor.current_map),[]) if isinstance(r,dict)}
  if (tx,ty) in masks or (tx,ty+delta) in masks:
   self.caption.set("A masked picture (★) is in the way: height changes never move a mask.");return False
  ny=ty+delta
  if not 0<=ny<self.grid_height:self.caption.set("That square is at the map edge: it cannot move a row.");return True
  if getattr(self,'_keep_walls',False) and (self.marked_wall(tx,ty) or self.marked_wall(tx,ny)):
   self.caption.set("A marked wall (x) is in the way: walls stay on their spot.");return False
  data=self.editor.session.data;w=self.grid_width
  src=self.grid_cells[ty*w+tx];dst=self.grid_cells[ny*w+tx]
  read=lambda o:bytes(self.pending_byte(o+i) for i in range(8))
  record=bytearray(read(src['offset']))
  if not 0<=record[3]+delta<=255:return False
  record[3]+=delta
  # The tile already in that row swaps into the square left behind, with its
  # height shifted the other way, so it is still drawn exactly where it was.
  other=bytearray(read(dst['offset']));replaced=False
  if 0<=other[3]-delta<=255:
   other[3]-=delta;vacated=other
   if other[4:6]==b'\xff\xff' and other[6:8]==b'\xff\xff':other[0]|=1   # void moved next to the floor: never walkable
  else:
   replaced=dst['values'][4]!=0xFFFF or dst['walls']
   vacated=bytearray(read(src['offset']));vacated[0]|=1;vacated[4:6]=b'\xff\xff';vacated[6:8]=b'\xff\xff'
  def keep(o,raw):
   for i,b in enumerate(raw):
    if b==data[o+i]:self.pending_heights.pop(o+i,None)
    else:self.pending_heights[o+i]=b
  keep(dst['offset'],record);keep(src['offset'],vacated)
  e=self.editor   # walls made with Make Wall follow their record to its new row
  for r in e.database.document.get('made_walls',{}).get(str(e.current_map),[]):
   if r['tile']==[tx,ty]:r['tile']=[tx,ny]
   elif r['tile']==[tx,ny] and vacated is other:r['tile']=[tx,ty]
  g=getattr(self,'pending_stack_grid',None)
  if g is not None:   # waiting wall pieces (Make Wall, step faces) belong to the record, not the row
   a,b=g[2][ty*w+tx],g[2][ny*w+tx]
   a['walls'],b['walls']=b['walls'],a['walls']
   moved={(tx,ty),(tx,ny)}&self.pending_stack_tiles
   if moved:self.pending_stack_tiles.update({(tx,ty),(tx,ny)})
  import struct
  src_walls=src['walls']
  src['values']=struct.unpack('<4BHh',bytes(vacated));src['walls']=[] if replaced or vacated is not other else dst['walls']
  dst['values']=struct.unpack('<4BHh',bytes(record));dst['walls']=src_walls
  # the number square now belongs to the moved record
  sq=getattr(self,'height_floor',{}).pop((tx,ty),None)
  if sq is not None:
   self.height_floor[(tx,ny)]=sq;self.height_stack[sq]=(tx,ny)
   for item in self.canvas.find_withtag(f"hn_{tx}_{ty}"):
    self.canvas.itemconfigure(item,text=str(record[3]),fill="#c8b36a",tags=("height_number",f"hn_{tx}_{ny}"))
  if redraw:self.redraw_height_numbers_from_grid()
  what='higher' if delta>0 else 'lower'
  self.caption.set(f"Tile {tx}, {ty} now counts as {what} (height {record[3]}), picture unchanged"+(f" — it replaced what was at {tx}, {ny}." if replaced else ".")+f" {len(self.pending_heights)} byte change(s) kept for save/build.")
  return True
 def right_click(self,event):
  if self.mark_walls.get() or self.mask_layer.get():return
  if self.height_edit.get():return self.adjust_height(event,-1)
  if self.mode.get()=="Paint tiles":return self.pick_brush_at(event)   # right-click picks the tile under the pointer (user 2026-10-25)
  record=self.record_at(event) if self.events_allowed() and self.selecting() else None
  if record is not None and record[0] in ("events","graphs","entities","warps"):return self.event_menu(event,record)
  if self.events_allowed() and self.mode.get() in ("Select tile","Events"):return self.event_menu(event,None)   # always the event menu here
  return self.click(event,pick=True)
 def pick_brush_at(self,event):
  """Paint mode right-click: the picture you see under the pointer becomes the brush
  (the front-most one drawn there, as the editor shows it)."""
  x,y=self.canvas.canvasx(event.x),self.canvas_y(event)
  hit=self.renderer.surface_at(x,y) if hasattr(self,'renderer') else None
  if hit is None or hit[5]==0xFFFF:
   hits=[h for h in self.renderer.surface_hits.get((int(x)//24,int(y)//16),[]) if h[5]!=0xFFFF] if hasattr(self,'renderer') else []
   if not hits:return
   hit=hits[-1]
  code=hit[5]
  self.bush_brush=None;self.face_brush=False;self.group_brush=None;self.group_brush_heights=None
  self.brush=code;self.brush_is_wall=False;self.brush_height=None
  self.caption.set(f"Brush: tile {code&1023} (picked from the map at tile {hit[2]}, {hit[3]}). Left-click to paint it.")
 def cut_selected_event(self):
  self.copy_selected_event();self.delete_selected_event()
  self.caption.set(f"Cut {self.event_clipboard['name']}.")
 def tile_under(self,event):
  hit=self.renderer.surface_at(self.canvas.canvasx(event.x),self.canvas_y(event)) if hasattr(self,'renderer') else None
  return None if hit is None else hit[2:4]
 def event_menu(self,event,record):
  """Right-click on an event: Cut / Copy / Paste / Delete."""
  tile=self.tile_under(event)
  if record is None:   # empty tile: Paste (and the rest greyed out)
   if tile is not None:self.select(*tile)
  else:
   self.selected_record=record;self.record_drag=None;self.highlight_record()
  def paste_here():
   if tile is not None:self.select(*tile)
   self.paste_event_at_selected_tile()
  def cut():
   self.cut_selected_event()
  project=record is not None and record[0] in ("graphs","entities")   # original characters copy too
  menu=tk.Menu(self.canvas,tearoff=False)
  menu.add_command(label="Cut",command=lambda:self.editor.guard(cut),state="normal" if project else "disabled")
  menu.add_command(label="Copy",command=lambda:self.editor.guard(self.copy_selected_event),state="normal" if project else "disabled")
  menu.add_command(label="Paste",command=lambda:self.editor.guard(paste_here),state="normal" if self.event_clipboard is not None else "disabled")
  menu.add_separator()
  menu.add_command(label="Delete",command=lambda:self.editor.guard(self.delete_selected_event),state="normal" if record is not None else "disabled")
  try:menu.tk_popup(event.x_root,event.y_root)
  finally:menu.grab_release()
 def raise_height_numbers(self):
  """Edit heights: its numbers (and grey squares, hover box) sit above events."""
  for tag in ("height_number","height_hover"):
   try:self.canvas.tag_raise(tag)
   except tk.TclError:pass
 def clear_in_front_of_switches(self):
  """A Switch (Step On) with Flush With Floor ticked, on a tile lowered by one, with the tile below and the
  tile above both one height higher: the piece left on top of the switch (the
  tile's own picture kept one row up when it was lowered) is removed."""
  e=self.editor;w=getattr(self,'grid_width',0);changed=[]
  defs={d['id']:d for d in e.database.definitions}
  for row in e.database.document.get('event_graphs',[]):
   if row.get('map_id')!=e.current_map:continue
   cid=(row.get('pages') or [{}])[0].get('class_id',row.get('class_id'))
   if defs.get(cid,{}).get('source',{}).get('catalogue_index')!=301:continue
   continue   # Flush With Floor was removed: nothing is taken off any more
   x,y=row['region'][:2]
   if not (0<=x<w and 1<=y<self.grid_height-1):continue
   c=self.grid_cells[y*w+x];h=c['values'][3]
   if self.grid_cells[(y-1)*w+x]['values'][3]!=h+1 or self.grid_cells[(y+1)*w+x]['values'][3]!=h+1:continue
   g=self.stack_grid();sc=g[2][y*w+x]
   if not sc['walls']:continue
   shift,codes=sc['walls'];codes=list(codes)
   if shift==2 and codes and codes[0]==c['values'][4]:   # the top piece on the switch
    old=self.tile_rows(x,y);codes=codes[1:]
    sc['walls']=(1,codes) if codes else None
    c['walls']=[(None,cd,1,i) for i,cd in enumerate(codes)]
    self.pending_stack_tiles.add((x,y));e.dirty=True
    self.redraw_columns([(x,y)],before={(x,y):old});changed.append((x,y))
  if changed:
   self.caption.set("Removed the piece on top of the step-on switch at "+", ".join(f"{a},{b}" for a,b in changed)+".")
 def front_tiles_cover(self,image,left,top,row,col=None):
  """Tiles in the rows in front of an event (drawn after it in game) hide the
  part of its picture they overlap, e.g. a raised tile just below a step-on
  switch covers the switch's bottom. Returns the picture with those parts clear."""
  from area_map import piece_rows
  w,h=image.size;left=int(round(left));top=int(round(top));cut=None
  own=self.grid_cells[row*self.grid_width+col]['values'][3] if col is not None and 0<=col<self.grid_width else None
  for ty in range(max(0,row-1),min(self.grid_height,row+1+h//16+3)):
   for tx in range(max(0,left//24-1),min(self.grid_width,(left+w)//24+2)):
    if (tx,ty)==(col,row):continue
    c=self.grid_cells[ty*self.grid_width+tx]
    if own is not None and c['values'][3]!=own+1:continue   # only a tile exactly one higher covers it
    if c['values'][4]==0xFFFF and not c['walls']:continue
    a,b=self.tile_rows(tx,ty)
    if c['values'][4]==0xFFFF:a+=16   # walls only, no floor picture
    x0,x1=max(left,tx*24),min(left+w,tx*24+24);y0,y1=max(top,a),min(top+h,b)
    if x0>=x1 or y0>=y1:continue
    if cut is None:cut=image.copy();alpha=cut.getchannel('A')
    alpha.paste(0,(x0-left,y0-top,x1-left,y1-top))
  if cut is None:return image
  cut.putalpha(alpha);return cut
 def event_number(self,x,y,text,tag):
  """View > Event Numbers: the event's number centred on its placement tile."""
  if not self.show_event_numbers.get():return
  for ox,oy in ((-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,1),(-1,1),(1,-1)):
   self.canvas.create_text(x+ox,y+oy,text=str(text),fill="#10151e",font=("Segoe UI",9,"bold"),tags=("record",tag,"event_number"))
  self.canvas.create_text(x,y,text=str(text),fill="#ffffff",font=("Segoe UI",9,"bold"),tags=("record",tag,"event_number"))
 def draw_records(self):
  result=self._draw_records()
  self.raise_height_numbers()   # Edit heights numbers stay above events, warps and markers
  return result
 def _draw_records(self):
  e=self.editor
  if getattr(self,"record_drag",None):
   self.redraw_after_drag=True;return   # a timer redraw mid-drag made the event jump; redrawn when the drag ends
  self.canvas.delete("record")
  self.info=inspect_map(e.session.data,e.current_map)
  self.markers=[];self.sprite_photos=[];self.sprite_boxes=[];self.sprite_masks={}
  # Look the map's sprite decoder up on every draw: tile imports move the map's
  # sections, and a decoder kept from before reads the wrong bytes ("Sprite
  # record outside section" on every redraw).
  try:self.sprites=cached_preview(e.session,e.current_map)
  except (ValueError,IndexError,struct.error):
   self.sprites=SimpleNamespace(frame=lambda *a:None,representative_frame=lambda *a:None,ground_footprint=lambda *a:None)
  try:global_sprites=cached_preview(e.session,e.current_map,True)
  except (ValueError,IndexError,struct.error):
   global_sprites=SimpleNamespace(frame=lambda *a:None,representative_frame=lambda *a:None,ground_footprint=lambda *a:None)
  for index,r in enumerate(self.info["entities"]):
   if not self.default_visible("entities"):continue
   if record_deleted(e.database.document,e.current_map,'entities',index):continue
   x,y,z=r["position_raw"]
   offset=int(r["offset"],16)
   sprite_index=e.session.data[offset+6]
   decoder=self.sprites if e.session.data[offset+5]&128 else global_sprites
   # A damaged/unknown sprite record must never stop the map drawing (or
   # repeat an error on every redraw): draw the plain marker instead.
   try:footprint=decoder.ground_footprint(sprite_index) if hasattr(decoder,"ground_footprint") else None
   except (ValueError,IndexError,struct.error):footprint=None
   centre_x,actor_y,ground_z=entity_preview_anchor(x,y,z,self.grid_cells,self.grid_width,self.grid_height,self.margin,self.elevation_enabled(),footprint)
   tile_x,tile_y,_=entity_tile_selection_anchor(x,y,self.grid_cells,self.grid_width,self.grid_height,self.margin,self.elevation_enabled())
   if self.elevation_enabled():tile_y-=max(0,(y*8+8+self.margin-ground_z*16)-actor_y)   # raised objects: box and number follow the sprite up
   try:preview=decoder.representative_frame(sprite_index,e.session.data[offset+5])
   except (ValueError,IndexError,struct.error):preview=None
   if preview:
    image,ox,oy=preview
    left=centre_x+ox;top=actor_y+oy
    photo=ImageTk.PhotoImage(image,master=e.root);self.sprite_photos.append(photo)
    self.canvas.create_image(left,top,image=photo,anchor="nw",tags=("record",f"entities_{index}"))
    self.sprite_masks[index]=image.getchannel("A")
    self.sprite_boxes.append((left,top,left+image.width,top+image.height,index))
   else:self.canvas.create_text(centre_x,tile_y-8,text='E',fill="#ffcf40",font=('Segoe UI',12,'bold'),tags=("record",f"entities_{index}"))
   self.canvas.create_rectangle(tile_x-12,tile_y-16,tile_x+12,tile_y,outline="#ffca72",width=2,dash=(3,2),tags=("record",f"entities_{index}"))   # same orange tile box as events
   self.event_number(tile_x,tile_y-8,index,f"entities_{index}")
   self.markers.append((tile_x,tile_y,index))
  width=max((hit[2] for hit in self.hits),default=-1)+1;height=max((hit[3] for hit in self.hits),default=-1)+1
  whole_entries=[];self.whole_map_events=set();self.whole_map_graphs=set()
  for index,r in enumerate(self.info["events"]):
   if not self.default_visible("events"):continue
   if record_deleted(e.database.document,e.current_map,'events',index):continue
   x1,y1,x2,y2=r["rectangle"]
   if covers_map((x1,y1,x2,y2),width,height):
    self.whole_map_events.add(index)
    whole_entries.append(('events',index,f"Event {index} · program {r['program']&127}"))
   else:
    self.canvas.create_rectangle(x1*24,y1*16+self.margin,(x2+1)*24,(y2+1)*16+self.margin,outline="#ffca72",width=2,dash=(3,2),tags=("record",f"events_{index}"))
    from native_event_view import event_graphic
    graphic,basis,entity=event_graphic(e.session,e.current_map,'events',index,self.info)
    if graphic is not None:
     photo=ImageTk.PhotoImage(graphic,master=e.root);self.sprite_photos.append(photo)
     self.canvas.create_image(x1*24+12,(y1+1)*16+self.margin,image=photo,anchor='s',tags=('record',f'events_{index}'))
    self.event_number(x1*24+12,y1*16+self.margin+8,index,f"events_{index}")
  self.project_graphs=[]
  view=getattr(e,'event_graphs_view',None)
  graphs=view() if view else e.database.document.get("event_graphs",[])
  for index,row in enumerate(graphs):
   if row["map_id"]!=e.current_map:continue
   self.project_graphs.append((index,row))
   x,y,w,h=row["region"];lift=self.event_lift(row)   # stand on the tile's height, like the game and the tile box
   left=x*24;top=y*16+self.margin-lift;right=(x+w)*24;bottom=(y+h)*16+self.margin-lift
   if covers_map((x,y,x+w-1,y+h-1),width,height):
    self.whole_map_graphs.add(index)
    whole_entries.append(('graphs',index,f"{row['name']} · {row['trigger']}"))
    continue
   else:self.canvas.create_rectangle(left,top,right,bottom,outline="#ffca72",width=2,dash=(3,2),tags=("record",f"graphs_{index}"))
   # The first page is an authoring preview; runtime page conditions are not evaluated.
   from project_event_preview import event_world_image,anchor_world_image
   first_page=row.get("pages",[{}])[0]
   class_id=first_page.get("class_id",row.get("class_id"))
   klass=next((item for item in e.database.definitions if item["id"]==class_id),None)
   if not hasattr(self,'authored_preview_cache'):self.authored_preview_cache={}
   from class_instance import effective_placement
   facing=effective_placement(row,klass).get('facing')   # the class's current facing unless the event overrides it
   key=(facing,class_id,repr(klass),e.current_map)   # any class change makes a new picture
   if key not in self.authored_preview_cache:
    try:self.authored_preview_cache[key]=event_world_image(e.session,klass,e.current_map,facing)
    except (ValueError,IndexError,struct.error):self.authored_preview_cache[key]=None
   image=self.authored_preview_cache[key]
   tile=row.get('native_placement',{}).get('tile_graphic')
   if class_id is None and tile:   # Use Tile event: its tile is drawn at the event (the map itself is unchanged)
    from tile_event_graphic import tile_image
    image=tile_image(e.session,tile)
    if image is not None:
     photo=ImageTk.PhotoImage(image,master=e.root);self.sprite_photos.append(photo)
     self.canvas.create_image(left,top,image=photo,anchor='nw',tags=('record',f'graphs_{index}'));continue
   if image is not None:
    photo=ImageTk.PhotoImage(image,master=e.root);self.sprite_photos.append(photo)
    placement=row.get('native_placement',{})
    image_x,image_y=anchor_world_image(image,x,y,self.margin-lift,placement.get('offset_x',0),placement.get('offset_y',0))
    if (klass or {}).get('source',{}).get('catalogue_index')==301:
     occluded=self.front_tiles_cover(image,image_x,image_y,y,x)
     if occluded is not image:
      photo=ImageTk.PhotoImage(occluded,master=e.root);self.sprite_photos.append(photo)
    self.canvas.create_image(image_x,image_y,image=photo,anchor='nw',tags=('record',f'graphs_{index}'))
   else:
    for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
     self.canvas.create_text(left+12+dx,top+8+dy,text='E',fill='#10151e',font=('Segoe UI',10,'bold'),tags=('record',f'graphs_{index}'))
    self.canvas.create_text(left+12,top+8,text='E',fill='#ffe0a5',font=('Segoe UI',10,'bold'),tags=('record',f'graphs_{index}'))
  for index,row in self.project_graphs:
   if index in self.whole_map_graphs:continue
   x,y=row["region"][:2];lift=self.event_lift(row)
   number=row['id'].split(':')[-1].lstrip('0') or '0'
   self.event_number(x*24+12,y*16+self.margin-lift+8,number,f"graphs_{index}")
  self.raise_height_numbers()
  # Show where a new game starts: your S marker, or the start the game/options already use.
  try:
   from editor_start_point import effective_start_point
   point,label,authored=effective_start_point(e)
  except (ValueError,TypeError,KeyError,OSError,StopIteration):point=None
  if point is not None and point.get('map_id')==e.current_map:
   # one whole tile wide, like the tile the game starts you on
   sx=point['x']*24;sy=point['y']*16+self.margin
   if self.elevation_enabled():sy-=point['z']*16
   if authored:self.canvas.create_rectangle(sx,sy,sx+24,sy+16,fill='#123624',outline='#72e5a0',width=1,tags=('record','start_point'))
   else:self.canvas.create_rectangle(sx,sy,sx+24,sy+16,fill='#1c2a3a',outline='#8fb8e8',width=1,dash=(2,2),tags=('record','start_point'))
   self.canvas.create_text(sx+12,sy+8,text='S',fill='#e6fff0' if authored else '#cfe2fa',font=('Segoe UI',9,'bold'),tags=('record','start_point'))
   if not authored:self.canvas.create_text(sx+28,sy+8,text=label,anchor='w',fill='#a9c6ea',font=('Segoe UI',8),tags=('record','start_point'))
  self.warp_rows=warps(e.session,e.current_map);self.warp_hit_boxes=[]
  for index,offset,p in (getattr(self,'warp_rows',[]) if getattr(self,'show_warps',None) is None or self.show_warps.get() else []):
   boxes=projected_warp_boxes(p,self.hits)
   self.warp_hit_boxes.append(((p.x2-p.x1+1)*(p.y2-p.y1+1),index,boxes))
   for left,top,right,bottom in boxes:
    self.canvas.create_rectangle(left,top,right,bottom,outline="#bf91ff",width=1,tags=("record",f"warps_{index}",f"warp_box_{index}"))
   if boxes:
    right=max(box[2] for box in boxes);top=min(box[1] for box in boxes);bottom=max(box[3] for box in boxes)
    self.canvas.create_text(right+6,(top+bottom)/2,text=f"W{index} > {p.destination_map}",anchor="w",fill="#d1b0ff",tags=("record",f"warps_{index}"))
  self.update_whole_event_menu(whole_entries)
  self.canvas.tag_raise("event_number")
  crop=getattr(self,'map_crop_top',0)
  if crop:
   self.canvas.move("record",0,-crop)
  self.highlight_record()   # after the crop move: the white box is not tagged "record", so it was left crop pixels below the event
  self.populate_record_list()
  self.canvas.tag_raise('start_point')   # the start tile stays visible over characters
 def highlight_record(self):
  self.canvas.delete("record_selection")
  if self.selected_record:self.canvas.delete("selection")   # never a tile box and an event box together
  if self.selected_record:
   kind,index=self.selected_record;bounds=self.canvas.bbox(f"{kind}_{index}")
   if kind=="warps":bounds=self.canvas.bbox(f"warp_box_{index}")
   if kind=="entities":
    marker=next(((px,py) for px,py,i in self.markers if i==index),None)
    if marker:
     px,py=marker
     if self.record_drag and self.record_drag[:2]==(kind,index):px+=self.drag_delta[0]*24;py+=self.drag_delta[1]*16
     left=math.floor(px/24)*24;top=map_y_to_view(math.floor((py-8)/16)*16,getattr(self,'map_crop_top',0));bounds=(left,top,left+24,top+16)
   if bounds:self.canvas.create_rectangle(*bounds,outline="#ffffff",width=2,tags="record_selection")
 def toggle_palette(self):
  if self.manual_palette.get():self.palette_controls.pack(fill="x")
  else:self.palette_controls.pack_forget()
  if hasattr(self,"renderer"):self.editor.guard(self.atlas)
 def change_map_zoom(self):
  self.canvas.zoom_factor=int(self.map_zoom.get().rstrip("%"))/100
  self.refresh(reload_textures=False)
 def change_tile_zoom(self):
  self.library.zoom_factor=int(self.tile_zoom.get().rstrip("%"))/100
  self.atlas()
 def atlas(self):
  if not hasattr(self,"renderer"):return
  from PIL import Image
  self.sync_tile_source_tabs()
  self.warm_liquids()
  tab=self.top_source_tab()
  source_map=self.picker_source()
  self.show_tile_kind_tabs('objects' if tab=='objects' else 'map' if tab=='map' else (None if source_map in ('water','lava') else ('objects' if source_map=='objects' else source_map=='tiles')))   # Floors / Walls (/ Stairs for Water), Map Objects' kinds
  self.show_tile_part_tabs(self.tile_kind if tab=='tiles' and source_map=='tiles' else 'maplayers' if tab=='map' else None)   # never on Bushes / Map Objects / Trees
  if source_map=='bushes':return self.draw_bush_library()
  if source_map in ('objects','trees'):return self.draw_object_library(source_map)
  part=self.tile_parts.get(self.tile_kind,'map') if source_map=='tiles' else None
  if source_map=='tiles' and self.tile_kind in ('water','ice','lava','sand','spikes'):return self.draw_liquid_library(f"{self.tile_kind}_{part if part in ('map','all') else 'map'}")
  if source_map=='tiles' and self.tile_kind=='stairs':return self.draw_water_library(stairs=True,part=part)
  if source_map=='tiles' and part in ('indoor','outdoor'):return self.draw_place_tiles(self.tile_kind,part)
  category=source_map if source_map=='tiles' else None
  if category:source_map=self.editor.current_map
  snap=self.picker_session()
  key=(id(snap),source_map)   # the picker shows the maps as they were when this map was opened
  if category:   # Tiles: only this map's renderer is needed, not its picture sections
   lr=getattr(self,'library_renderer',None)
   if lr is None or lr.m!=source_map or lr.session is not snap:self.library_renderer=MapRenderer(snap,source_map)
  elif self.tile_view_key!=key:
   from map_tile_library import map_source_views
   if getattr(self,'library_renderer',None) is None or self.library_renderer.m!=source_map or self.library_renderer.session is not snap:
    self.library_renderer=MapRenderer(snap,source_map)
   self.tile_views=map_source_views(self.library_renderer);self.tile_view_key=key
  labels=[view['label'] for view in self.tile_views] if not category else []
  if category:
   self.tile_section.set('Whole map');self.tile_section_choices.configure(values=['Whole map'],state='disabled')
  else:
   remembered=self.tile_section_memory.get(source_map,'Whole map')
   self.tile_section.set(remembered if remembered in labels else 'Whole map')
   self.tile_section_choices.configure(values=labels,state='disabled' if self.manual_palette.get() else 'readonly')
  if category=='tiles':
   im=self.floor_category_image(self.tile_kind);self.library_height_lookup={};self.library_grid={}
   self.set_picker_jumps()
   self.atlas_photo=ImageTk.PhotoImage(im,master=self.editor.root)
   self.library.delete("all");self.library.create_image(0,0,image=self.atlas_photo,anchor="nw");self.library.configure(scrollregion=(0,0,im.width,im.height))
   return
  if self.manual_palette.get():
   p=int(self.pal.get())
   if not 0<=p<16:raise ValueError("Palette must be 0-15")
   im=Image.new("RGBA",(240,96*16),(31,34,40,255));self.library_hits=[];self.library_height_lookup={};self.library_grid={}
   for n in range(960):
    x=n%10*24;y=n//10*16;code=n|(p<<12)
    im.alpha_composite(self.library_renderer.tile(code),(x,y));self.library_hits.append((x,y,code))
  else:
   view=next(view for view in self.tile_views if view['label']==self.tile_section.get())
   im,self.library_hits=view['image'],view['hits']
   self.library_height_lookup={(px,py,code):height for px,py,code,height in view.get('height_hits',[])}
   self.library_grid={(px,py,code):(tx,ty,h,kind) for px,py,code,tx,ty,h,kind in view.get('grid_hits',[])}
   layer=self.tile_parts.get('maplayers','all') if tab=='map' else 'all'
   if layer!='all':   # Layer 1: the floor tiles only; Layer 2: the pieces drawn on top only
    keep=[hit for hit in view.get('grid_hits',[]) if hit[6]==layer]
    im=Image.new("RGBA",im.size,(31,34,40,255))
    for px,py,code,*_ in keep:
     if 0<=px<=im.width-24 and 0<=py<=im.height-16:im.alpha_composite(self.library_renderer.tile(code),(px,py))
    self.library_hits=[(px,py,code) for px,py,code,*_ in keep]
    self.library_height_lookup={(px,py,code):h for px,py,code,_,_,h,_ in keep}
    self.library_grid={(px,py,code):(tx,ty,h,kind) for px,py,code,tx,ty,h,kind in keep}
  self.atlas_photo=ImageTk.PhotoImage(im,master=self.editor.root)
  self.library.delete("all");self.library.create_image(0,0,image=self.atlas_photo,anchor="nw");self.library.configure(scrollregion=(0,0,im.width,im.height))
 # -- Floors / Walls tabs: pieces as they stand on the maps ----------------
 COLUMN_STEP=28;COLUMNS_PER_ROW=16;BAND=512
 def draw_column_view(self,kind):
  """Tile picker Floors / Walls: every different map cell look (Floors: the
  floor with its layers; Walls: the wall layers) drawn as on the maps, this
  map first, then every map, ordered by look so similar ones sit together.
  Pictures are packed into 16 lanes (each next one goes where its lane is
  shortest), so tall and short ones leave no gaps. Click a piece to paint
  with it: a floor piece is a floor brush, a wall piece adds that wall tile
  (see place_face). The picture is drawn in bands as you scroll."""
  from bush_catalogue import column_catalogue,map_columns
  session=self.picker_session();here=self.picker_map()
  self.library_hits=[];self.library_height_lookup={};self.library_grid={}
  self.library.delete("all");self.column_photos={};self.column_kind=kind
  step,lanes=self.COLUMN_STEP,self.COLUMNS_PER_ROW
  self.column_items=[];self.column_lanes=[[] for _ in range(lanes)];self.column_bands={}
  def pack(items,y):
   heights=[y]*lanes
   for pieces,_ in items:
    lane=min(range(lanes),key=lambda n:heights[n])
    height=max(dy for _,dy,_ in pieces)+16
    item=dict(x=lane*step+2,y=heights[lane],h=height,pieces=pieces)
    self.column_items.append(item);self.column_lanes[lane].append(item)
    for number in range(item['y']//self.BAND,(item['y']+height)//self.BAND+1):self.column_bands.setdefault(number,[]).append(item)
    heights[lane]+=height+4
   return max(heights)
  mine=[([(('map',here,code),dy,floor) for code,dy,floor in pieces],used) for pieces,used in map_columns(session,here,kind,self.picker_renderer(here))]
  catalogue=column_catalogue(session,kind,build=False);self.column_catalogue_data=catalogue
  title='THIS MAP' if here==self.editor.current_map else f"MAP {here} - {map_label(here).rsplit(' (Map',1)[0].upper()}"
  self.library.create_text(4,4,anchor='nw',text=title,fill='white',font=('Segoe UI',8,'bold'))
  y=pack(mine,20)+10;all_top=y
  if catalogue:
   self.library.create_text(4,y+4,anchor='nw',text="ALL MAPS",fill='white',font=('Segoe UI',8,'bold'))
   y=pack([([(('atlas',index),dy,floor) for index,dy,floor in pieces],used) for pieces,used,_ in catalogue['columns']],y+20)
  else:
   self.library.create_text(4,y+4,anchor='nw',text="ALL MAPS: loading in the background…",fill='white',font=('Segoe UI',8,'bold'));y+=24
   self.editor.preload_prioritize(f'{kind}-columns') if hasattr(self.editor,'preload_prioritize') else None
   self.editor.root.after(1500,self.refresh_floor_tab_when_ready)
  self.column_height=y;self.column_rows=True
  self.floor_jumps=[('This map',0),('All maps',all_top)]
  self.set_picker_jumps()
  self.library.configure(scrollregion=(0,0,lanes*step,max(y,16)));self.library.yview_moveto(0)
  self.draw_visible_columns()
 def column_piece_image(self,ref):
  if ref[0]=='map':return self.picker_renderer(ref[1]).tile(ref[2])
  index=ref[1];x=index%20*24;y=index//20*16
  return self.column_catalogue_data['atlas'].crop((x,y,x+24,y+16))
 def draw_visible_columns(self):
  if not getattr(self,'column_items',None) or self.source_tab()!=getattr(self,'column_kind',None):return
  from PIL import Image
  band=self.BAND
  top=max(0,int(self.library.canvasy(0))-band);bottom=int(self.library.canvasy(self.library.winfo_height()))+band
  for number in range(top//band,bottom//band+1):
   if number in self.column_photos or number*band>self.column_height:continue
   y0=number*band;im=Image.new("RGBA",(self.COLUMNS_PER_ROW*self.COLUMN_STEP,band),(31,34,40,255))
   for item in self.column_bands.get(number,[]):
     for ref,dy,_ in item['pieces']:
      piece=self.column_piece_image(ref);im.paste(piece,(item['x'],item['y']+dy-y0),piece)
   photo=ImageTk.PhotoImage(im,master=self.editor.root);self.column_photos[number]=photo
   self.library.create_image(0,y0,image=photo,anchor='nw',tags='column_band')
   self.library.tag_lower('column_band')
  self.library.tag_raise('brush_selection')
 def column_click(self,event):
  import bisect
  x=self.library.canvasx(event.x);y=self.library.canvasy(event.y)
  lane=int(x//self.COLUMN_STEP)
  if not 0<=lane<len(getattr(self,'column_lanes',[])):return
  items=self.column_lanes[lane];i=bisect.bisect_right([item['y'] for item in items],y)-1
  if i<0 or y>=items[i]['y']+items[i]['h']:return
  item=items[i];lx=int(x-item['x']);ly=int(y-item['y'])
  hit=None
  for ref,dy,floor in reversed(item['pieces']):   # walls are drawn over the floor
   if 0<=lx<24 and dy<=ly<dy+16:
    if self.column_piece_image(ref).getpixel((lx,ly-dy))[3]:hit=(ref,dy,floor);break
    if hit is None:hit=(ref,dy,floor)
  if hit is None:return
  ref,dy,floor=hit
  source,code=(ref[1],ref[2]) if ref[0]=='map' else self.column_catalogue_data['entries'][ref[1]]
  self.group_brush=None;self.group_brush_heights=None;self.bush_brush=None
  translated=self.translate_library_tiles([code],source=source)
  if translated is None:return
  self.brush=translated[code];self.brush_height=None;self.face_brush=False;self.brush_is_wall=not floor   # wall pieces place like floor tiles, then act as a wall
  where="" if source==self.editor.current_map else f" From map {source}, copied into this map."
  if floor:self.caption.set(f"Floor brush: tile {code&1023}, palette {code>>12}. Tick Layer On Top to lay it over what is there instead."+where)
  else:self.caption.set(f"Wall brush: tile {code&1023}, palette {code>>12}."+where)
  self.mode.set("Paint tiles")
  px=item['x'];py=item['y']+dy
  self.library.delete('brush_selection');self.library.create_rectangle(px,py,px+24,py+16,outline='white',width=2,tags='brush_selection')
 # -- "Jump to": a map by ID and name shows that map's pieces at the top --
 def picker_map(self):
  """The map whose pieces the Floors/Walls tabs show first (Jump to), else this map."""
  chosen=getattr(self,'picker_map_choice',None)
  if chosen is None or chosen[0]!=self.editor.current_map:return self.editor.current_map
  return chosen[1]
 def picker_session(self):
  """A frozen copy of the game data for the tile picker: the current map and
  the added maps stay exactly as they were when you opened this map, however
  you paint, raise or erase on the map you are working on."""
  e=self.editor;key=(id(e.session),e.current_map)
  if getattr(self,'_picker_snap_key',None)!=key:
   import copy
   snap=copy.copy(e.session)
   # textures are cached by their bytes, so the session's decoded textures stay valid here
   snap.data=bytes(e.session.data);snap._texture_cache=dict(getattr(e.session,'_texture_cache',None) or {})
   snap._pending_textures=dict(getattr(e.session,'_pending_textures',{}) or {})
   snap._pending_palettes=dict(getattr(e.session,'_pending_palettes',{}) or {})
   snap.undo_stack=[];snap.redo_stack=[]
   def frozen(*_a,**_k):raise ValueError('The tile picker is read-only')
   snap.replace=frozen
   # pictures erased to make room still show here; using one puts it back (user 2026-10-25)
   erased=e.database.document.get('erased_tile_art',{}).get(str(e.current_map)) if getattr(e,'database',None) else None
   if erased:
    try:
     from map_tile_import import write_tile
     raw=bytearray(snap.texture(e.current_map)[0])
     for i,art in erased.items():write_tile(raw,int(i),bytes.fromhex(art))
     snap._pending_textures[e.current_map]=bytes(raw)
    except Exception:pass
   self._picker_snap=snap;self._picker_snap_key=key
  return self._picker_snap
 def picker_renderer(self,m):
  if m==self.editor.current_map and hasattr(self,'library_renderer') and self.library_renderer.m==m:return self.library_renderer
  snap=self.picker_session()   # one renderer per map, kept while the snapshot lasts
  cache=self.__dict__.get('_picker_renderers')
  if cache is None or cache.get('snap') is not snap:cache=self._picker_renderers={'snap':snap}
  if m not in cache:cache[m]=MapRenderer(snap,m)
  return cache[m]
 def jump_maps(self):
  """Every map there is (by ID), for Jump to."""
  key=id(self.editor.session)
  if getattr(self,'_jump_maps_key',None)!=key:
   from map_slots import map_count
   maps=[];session=self.editor.session
   for m in range(map_count(session.data)):   # a map with a tile grid (its width byte), without reading the whole grid
    try:
     base,h=session.layout(m)
     if session.data[base+h[1]]:maps.append(m)
    except Exception:
     if m>=483:break
   self._jump_maps=maps;self._jump_maps_key=key
  return self._jump_maps
 def tile_kind_changed(self):
  kind=self.tile_kind_frames.get(self.tile_kind_tabs.select())
  if getattr(self,'tile_kind_mode',None)=='map':
   if kind is not None and kind!=getattr(self,'map_sub',None):
    self.map_sub=kind;self.group_brush=None;self.group_brush_heights=None;self.bush_brush=None;self.brush=None;self.library_start=None
    self.atlas()
   return
  if getattr(self,'tile_kind_mode',None)=='objects':
   if kind and kind!=getattr(self,'object_kind','furniture'):
    self.object_kind=kind;self.bush_brush=None;self.atlas();self.library.yview_moveto(0)
   return
  if getattr(self,'tile_kind_mode',None)=='water':
   if kind and kind!=getattr(self,'water_kind','floors'):
    self.water_kind=kind;self.bush_brush=None;self.atlas();self.library.yview_moveto(0)
   return
  if kind and kind!=self.tile_kind:
   self.tile_kind=kind;self.atlas();self.library.yview_moveto(0)
 def show_tile_kind_tabs(self,shown):
  """The Floors / Walls tabs inside Tiles (Water adds Stairs): present only
  while Tiles or Water is open."""
  bar=self.tile_kind_tabs
  mode=shown if shown in ('water','map','objects') else ('tiles' if shown else None)
  if getattr(self,'tile_kind_mode',None)==mode and (bar.tabs() or mode is None):return
  for tab in bar.tabs():bar.forget(tab)
  self.tile_kind_frames={};self.tile_kind_mode=mode
  if mode is None:return
  if mode=='map':   # Current Map first, then every added map
   for m in getattr(self,'picker_maps',[self.editor.current_map]):
    name=map_label(m).rsplit(' (Map',1)[0]
    title='Current Map' if m==self.editor.current_map else f"{m} {name if len(name)<=16 else name[:15]+'…'}"
    frame=ttk.Frame(bar);bar.add(frame,text=title[:27]);self.tile_kind_frames[str(frame)]=m
    if m==getattr(self,'map_sub',None):bar.select(frame)
   return
  if mode=='objects':   # Map Objects: Furniture, Stairs, Ladders, Other
   from map_object_catalogue import CATEGORIES
   for kind,title in [c for c in CATEGORIES if c[0]!='other']+[('bushes','Bushes'),('trees','Trees')]+[c for c in CATEGORIES if c[0]=='other']:
    frame=ttk.Frame(bar);bar.add(frame,text=title);self.tile_kind_frames[str(frame)]=kind
    if kind==getattr(self,'object_kind','furniture'):bar.select(frame)
   return
  kinds=(('floors','Floors'),('walls','Walls'),('stairs','Slopes'))+((('spikes','Spikes'),('sand','Sand'),('water','Water'),('ice','Ice'),('lava','Lava')) if mode=='tiles' else ())   # Spikes: floors that hurt (user 2026-10-21)
  current=getattr(self,'water_kind','floors') if mode=='water' else self.tile_kind
  for kind,title in kinds:
   frame=ttk.Frame(bar);bar.add(frame,text=title);self.tile_kind_frames[str(frame)]=kind
   if kind==current:bar.select(frame)
 def given_maps(self):
  """The maps the Tiles tab shows: the map picked in Jump to (if any), this
  map, and the maps added with Add map tiles…"""
  e=self.editor;here=e.current_map
  sources=e.database.document.get('map_tile_sources',{}).get(str(here),[])
  maps=[self.picker_map(),here]+[m for m in sources if type(m) is int and 0<=m<2547]
  return list(dict.fromkeys(maps))
 def map_title(self,m):
  name=map_label(m).rsplit(' (Map',1)[0]
  return 'This map' if m==self.editor.current_map else f"{m} - {name}"
 def set_picker_jumps(self):
  given=[self.map_title(m) for m in self.given_maps()]
  values=given+[f"{m} - {map_label(m).rsplit(' (Map',1)[0]}" for m in self.jump_maps() if f"{m} - {map_label(m).rsplit(' (Map',1)[0]}" not in given]
  self.tile_section.set(given[0])
  self.tile_section_choices.configure(values=values,state='readonly',height=20)
 def picker_jump(self,label):
  target=dict(getattr(self,'floor_jumps',[])).get(label)
  if target is not None:   # a map already shown: scroll to it
   height=float(self.library.cget('scrollregion').split()[3]) if self.library.cget('scrollregion') else 0
   if height:self.library.yview_moveto(max(0,target)*self.library.zoom_factor/height)
   return
  try:m=int(label.split(' - ',1)[0])
  except ValueError:return
  self.picker_map_choice=(self.editor.current_map,m);self.atlas();self.library.yview_moveto(0)
 def floor_category_image(self,kind='floors'):
  """Tile picker, Tiles: single floor tiles (Floors) or single wall tiles
  (Walls) of the given maps only (Jump to's map, this map, the maps added
  with Add map tiles…), each map's tiles ordered by how alike they look.
  Click one to paint with it; a tile from another map is copied into this
  map's tile set first. A wall tile is added under a tile's lowest layer."""
  from PIL import Image,ImageDraw
  from bush_catalogue import FLOOR_COLUMNS,floor_codes,floor_sheet,wall_codes
  session=self.picker_session();columns=FLOOR_COLUMNS;head=18
  sections=[]
  for m in self.given_maps():
   codes_cache=self.__dict__.setdefault('floor_codes_cache',{});ck=(m,kind,id(session))
   if ck not in codes_cache:
    try:codes_cache[ck]=(floor_codes if kind=='floors' else wall_codes)(session,m)
    except Exception:codes_cache[ck]=None
   codes=codes_cache[ck]
   if codes is None:continue
   renderer=self.picker_renderer(m) if m!=self.editor.current_map else self.library_renderer
   cache=self.__dict__.setdefault('floor_sheet_cache',{})
   key=(m,kind,id(session),tuple(codes))
   if key not in cache:cache[key]=floor_sheet([renderer.tile(code) for code in codes])
   sheet,blocks=cache[key]
   sections.append((m,codes,sheet,blocks))
  height=sum(head+sheet.height+8 for _,_,sheet,_ in sections) or 16
  im=Image.new("RGBA",(columns*24,height),(24,26,31,255));draw=ImageDraw.Draw(im)
  self.library_hits=[];self.floor_blocks=[];self.floor_jumps=[];y=0
  for m,codes,sheet,blocks in sections:
   title=self.map_title(m)
   draw.text((2,y+3),title.upper(),fill=(255,255,255,255))
   self.floor_jumps.append((title,y));y+=head
   im.alpha_composite(sheet,(0,y))
   self.floor_blocks+=[(y+top,[(m,codes[i]) for i in members]) for top,members in blocks]
   y+=sheet.height+8
  return im
 def refresh_floor_tab_when_ready(self):
  return   # (the Tiles tab shows only the given maps; nothing loads in the background)
  kind=None
  if kind not in ('floors','walls'):return
  from bush_catalogue import column_catalogue,floor_catalogue
  ready=floor_catalogue(self.editor.session,build=False) if kind=='floors' else column_catalogue(self.editor.session,kind,build=False)
  if ready is None:
   self.editor.root.after(1500,self.refresh_floor_tab_when_ready);return
  self.editor.guard(self.atlas)
 def floor_library_click(self,event):
  from bush_catalogue import FLOOR_COLUMNS
  x=int(self.library.canvasx(event.x));y=int(self.library.canvasy(event.y))
  for top,entries in getattr(self,'floor_blocks',[]):
   rows=(len(entries)+FLOOR_COLUMNS-1)//FLOOR_COLUMNS
   if not (top<=y<top+rows*16 and 0<=x<FLOOR_COLUMNS*24):continue
   index=(y-top)//16*FLOOR_COLUMNS+x//24
   if not 0<=index<len(entries):return
   source,code=entries[index]
   self.group_brush=None;self.group_brush_heights=None;self.bush_brush=None;self.face_brush=False
   translated=self.translate_library_tiles([code],source=source)
   if translated is None:return
   self.brush=translated[code];self.brush_height=None
   walls=self.tile_kind=='walls';self.face_brush=False;self.brush_is_wall=walls   # wall tiles place like floor tiles, then act as a wall
   if walls:
    self.caption.set(f"Brush: wall tile {code&1023}, palette {code>>12}"+("" if source==self.editor.current_map else f" From map {source}, copied into this map."))
    self.mode.set("Paint tiles")
   else:self.caption.set(f"Brush: floor tile {code&1023}, palette {code>>12}"+("" if source==self.editor.current_map else f" from map {source} (copied into this map)"))
   if not walls:self.mode.set("Paint tiles")
   px=index%FLOOR_COLUMNS*24;py=top+index//FLOOR_COLUMNS*16
   self.library.delete('group_selection');self.library.delete('brush_selection')
   self.library.create_rectangle(px,py,px+24,py+16,outline='white',width=2,tags='brush_selection')
   return
 def wall_category_image(self):
  """Tile picker, Walls: every different wall stack of the source map
  (cliff faces, fronts, pillars, bushes), most used first. Click one, then
  click or drag over tiles; right-click removes a tile's walls."""
  from PIL import Image
  from bush_catalogue import wall_stacks
  stacks=wall_stacks(self.editor.session,self.library_renderer.m)
  columns=8;cell=30;rows=[stacks[i:i+columns] for i in range(0,len(stacks),columns)] or [[]]
  heights=[max([s['image'].height for s in row]+[16])+4 for row in rows]
  im=Image.new("RGBA",(columns*cell,sum(heights)),(31,34,40,255));self.wall_library_cells=[];y=0
  for row,height in zip(rows,heights):
   for column,style in enumerate(row):
    x=column*cell;picture=style['image']
    im.alpha_composite(picture,(x+3,y+height-picture.height-2))
    self.wall_library_cells.append((x,y,cell,height,style))
   y+=height
  return im
 def wall_library_click(self,event):
  x=self.library.canvasx(event.x);y=self.library.canvasy(event.y)
  for cx,cy,w,h,style in getattr(self,'wall_library_cells',[]):
   if cx<=x<cx+w and cy<=y<cy+h:
    self.set_bush_brush(style,f"Walls from map {style['map']} tile {style['x']},{style['y']}")
    self.library.delete('brush_selection');self.library.create_rectangle(cx,cy,cx+w,cy+h,outline='white',width=2,tags='brush_selection')
    return
 def draw_bush_library(self):
  """Tile picker, Bushes tab: every bush picture in the game. Click one to
  paint it on map tiles (they keep their floor and height); right-click a
  bush on the map to remove it."""
  from PIL import Image
  from bush_catalogue import cached_bush_styles
  styles=cached_bush_styles(self.editor.session)
  self.tile_section.set('Whole map');self.tile_section_choices.configure(values=['Whole map'],state='disabled')
  columns=8;cell_w,cell_h=30,40;rows=max(1,(len(styles)+columns-1)//columns)
  im=Image.new("RGBA",(columns*cell_w,rows*cell_h),(31,34,40,255));self.bush_library_cells=[]
  for index,style in enumerate(styles):
   x=index%columns*cell_w;y=index//columns*cell_h;picture=style['image']
   im.alpha_composite(picture,(x+(cell_w-picture.width)//2,y+max(0,cell_h-picture.height)))
   self.bush_library_cells.append((x,y,index,style))
  self.library_hits=[];self.library_height_lookup={};self.library_grid={}
  self.atlas_photo=ImageTk.PhotoImage(im,master=self.editor.root)
  self.library.delete("all");self.library.create_image(0,0,image=self.atlas_photo,anchor="nw");self.library.configure(scrollregion=(0,0,im.width,im.height))
  chosen=getattr(self,'bush_brush',None)
  for x,y,index,style in self.bush_library_cells:
   if chosen is not None and chosen[0] is style:self.library.create_rectangle(x,y,x+cell_w,y+cell_h,outline='white',width=2,tags='brush_selection')
 def show_tile_part_tabs(self,kind):
  """Third row of tabs under Tiles (user request 2026-10-15): Floors, Walls
  and Slopes -> This Map (this map and the added maps), Indoor, Outdoor (the
  whole game's); Water and Lava -> Main, Edges, Other. Hidden otherwise."""
  bar=self.tile_part_tabs;parts=TILE_PARTS.get(kind) if kind else None
  if not parts:
   if self.tile_part_key is not None:bar.pack_forget();self.tile_part_key=None
   return
  if self.tile_part_key==kind:return
  self.tile_part_building=True
  try:
   for tab in bar.tabs():bar.forget(tab)
   self.tile_part_frames={};want=self.tile_parts.get(kind,parts[0][0])
   for part,title in parts:
    frame=ttk.Frame(bar);bar.add(frame,text=title);self.tile_part_frames[str(frame)]=part
    if part==want:bar.select(frame)
  finally:self.tile_part_building=False
  if self.tile_part_key is None:
   # after the kind tabs when they are shown; they may be hidden (Map tab): then just pack it
   try:bar.pack(fill='x',pady=(2,0),after=self.tile_kind_tabs) if self.tile_kind_tabs.winfo_manager() else bar.pack(fill='x',pady=(2,0))
   except Exception:bar.pack(fill='x',pady=(2,0))
  self.tile_part_key=kind
 def tile_part_changed(self):
  if getattr(self,'tile_part_building',False):return
  part=self.tile_part_frames.get(self.tile_part_tabs.select())
  kind='maplayers' if self.tile_part_key=='maplayers' else self.tile_kind
  if part and part!=self.tile_parts.get(kind):
   self.tile_parts[kind]=part;self.bush_brush=None;self.atlas();self.library.yview_moveto(0)
 def draw_place_tiles(self,kind,part):
  """Tiles > Floors / Walls > Indoor / Outdoor: every different floor (or
  wall) tile of the game's indoor or outdoor maps (map_places), similar ones
  together. Click one to paint with it; it is copied into this map's tiles."""
  from PIL import Image,ImageDraw
  from map_places import place_sheet
  sheet,entries=place_sheet(self.editor.session,kind,part)
  head=18;im=Image.new("RGBA",(sheet.width,sheet.height+head),(24,26,31,255))
  ImageDraw.Draw(im).text((2,3),f"{part.upper()} {'FLOORS' if kind=='floors' else 'WALL TILES'} - WHOLE GAME ({len(entries)})",fill=(255,255,255,255))
  im.alpha_composite(sheet,(0,head))
  self.library_hits=[];self.floor_blocks=[(head,list(entries))];self.floor_jumps=[];self.library_height_lookup={};self.library_grid={}
  self.tile_section.set('Whole map');self.tile_section_choices.configure(values=['Whole map'],state='disabled')
  self.atlas_photo=ImageTk.PhotoImage(im,master=self.editor.root)
  self.library.delete("all");self.library.create_image(0,0,image=self.atlas_photo,anchor="nw");self.library.configure(scrollregion=(0,0,im.width,im.height))
 def draw_water_library(self,stairs=False,part='map'):
  """Tile picker, Water tab: every water picture of the game (Floors, Walls,
  Stairs). Click one, then click or drag over map tiles: they get the water
  picture and its logic (walkability, ground, slope); the height stays."""
  from PIL import Image
  from water_catalogue import cached_water_styles
  kind=getattr(self,'water_kind','floors')
  if stairs:
   # Slopes: the stair / slope tiles of the same maps the Floors and Walls tabs show
   from water_catalogue import stair_styles,cached_stair_styles
   if part in ('indoor','outdoor'):   # the whole game's indoor / outdoor slopes
    from map_places import map_place
    styles=[r for r in cached_stair_styles(self.editor.session) if map_place(r['map'])==part];kind='stairs'
   else:
    maps=tuple(m for m in self.given_maps() if type(m) is int)
    snap=self.picker_session();key=(id(snap),maps)
    if getattr(self,'slope_styles_key',None)!=key:
     self.slope_styles=stair_styles(snap,maps);self.slope_styles_key=key
    kind='stairs';styles=self.slope_styles
  else:styles=cached_water_styles(self.editor.session).get(kind,[])
  self.tile_section.set('Whole map');self.tile_section_choices.configure(values=['Whole map'],state='disabled')
  columns=8;cell_w,cell_h=(30,40) if kind=='walls' else (30,22);rows=max(1,(len(styles)+columns-1)//columns)
  im=Image.new("RGBA",(columns*cell_w,rows*cell_h),(31,34,40,255));self.water_library_cells=[]
  for index,style in enumerate(styles):
   x=index%columns*cell_w;y=index//columns*cell_h;picture=style['image']
   if picture.height>cell_h:picture=picture.crop((0,picture.height-cell_h,picture.width,picture.height))
   im.alpha_composite(picture,(x+(cell_w-picture.width)//2,y+max(0,cell_h-picture.height)))
   self.water_library_cells.append((x,y,cell_w,cell_h,style))
  self.library_hits=[];self.library_height_lookup={};self.library_grid={}
  self.atlas_photo=ImageTk.PhotoImage(im,master=self.editor.root)
  self.library.delete("all");self.library.create_image(0,0,image=self.atlas_photo,anchor="nw");self.library.configure(scrollregion=(0,0,im.width,im.height))
  chosen=getattr(self,'bush_brush',None)
  for x,y,cw,ch,style in self.water_library_cells:
   if chosen is not None and chosen[0] is style:self.library.create_rectangle(x,y,x+cw,y+ch,outline='white',width=2,tags='brush_selection')
 def warm_liquids(self):
  """Read the Sand / Water / Ice / Lava catalogue in the background once, so
  those tabs open at once instead of loading when first clicked."""
  session=self.editor.session
  if session is None or getattr(session,'_liquid_warm',False):return
  session._liquid_warm=True
  import threading
  def work():
   try:
    from liquid_catalogue import cached_liquid_styles
    cached_liquid_styles(session)
   except Exception:pass
  threading.Thread(target=work,daemon=True).start()
 def draw_liquid_library(self,tab):
  """Tiles > Main Water / Water Edges / Water Other (and the same for Lava),
  user request 2026-10-15: every water / lava picture of the game once, by
  kind; Main is only water, Edges water with land at a side or corner, Other
  things lying on it (pictures without water are left out). Each picture
  sits next to the pictures it touches in the game, no empty squares. Click
  one, then click or drag over map tiles."""
  from PIL import Image
  from liquid_catalogue import cached_liquid_styles,library_picture
  liquid,place=tab.split('_',1)
  kinds=cached_liquid_styles(self.editor.session).get(liquid,[])
  # This Map (this map and the added maps) / Indoor / Outdoor, like Floors
  if place=='map':
   here={m for m in self.given_maps() if type(m) is int}
   kinds=[k for k in kinds if here & set(k.get('maps') or [])]

  self.tile_section.set('Whole map');self.tile_section_choices.configure(values=['Whole map'],state='disabled')
  cache=getattr(self,'liquid_pictures',{});self.liquid_pictures=cache
  key=(tab,tuple(id(k) for k in kinds))
  if key not in cache:
   parts=[library_picture(kinds,part) for part in ('main','edges','other')]
   width=max(p[0].width for p in parts);height=sum(p[0].height for p in parts if p[1]) or 1
   im=Image.new('RGBA',(width,height),(31,34,40,255));hits=[];top=0
   for picture,found in parts:
    if not found:continue
    im.alpha_composite(picture,(0,top));hits+=[(x,y+top,w,h,row) for x,y,w,h,row in found];top+=picture.height
   cache[key]=(im,hits)
  im,hits=cache[key]
  self.water_library_cells=list(hits)
  self.library_hits=[];self.library_height_lookup={};self.library_grid={}
  photos=getattr(self,'liquid_photos',{});self.liquid_photos=photos
  if key not in photos:photos[key]=ImageTk.PhotoImage(im,master=self.editor.root)
  self.atlas_photo=photos[key]
  self.library.delete("all");self.library.create_image(0,0,image=self.atlas_photo,anchor="nw");self.library.configure(scrollregion=(0,0,im.width,im.height))
  chosen=getattr(self,'bush_brush',None)
  for x,y,cw,ch,style in self.water_library_cells:
   if chosen is not None and chosen[0] is style:self.library.create_rectangle(x,y,x+cw,y+ch,outline='white',width=2,tags='brush_selection')
 def water_library_click(self,event):
  x=self.library.canvasx(event.x);y=self.library.canvasy(event.y)
  for cx,cy,cw,ch,style in getattr(self,'water_library_cells',[]):
   if cx<=x<cx+cw and cy<=y<cy+ch:
    kind=style.get('liquid','water') if style['kind']=='liquid' else {'water_floors':'water','water_stairs':'water stairs','walls':'water walls','stairs':'slope'}.get(style['kind'],'water')
    self.set_bush_brush(style,f"{kind} from map {style['map']} tile {style['x']},{style['y']}")
    self.library.delete('brush_selection');self.library.create_rectangle(cx,cy,cx+cw,cy+ch,outline='white',width=2,tags='brush_selection')
    return
 def object_styles_for_library(self,tab='objects'):
  """Map Objects or Trees: your own first, then the game's. A right-click
  moves one to the other tab (kept in the project)."""
  from map_object_catalogue import cached_object_styles,user_objects,object_category,builtin_objects
  doc=self.editor.database.document
  rows=user_objects(doc)+list(cached_object_styles(self.editor.session))   # (the Warp Panel is an object: Database / event editor)
  wanted='trees' if tab=='trees' else getattr(self,'object_kind','furniture')
  rows=[r for r in rows if object_category(doc,r)==wanted]
  if wanted=='trees':   # the game's trees kept in the Trees tab (user 2026-10-18); your own always show
   rows=[r for r in rows if r.get('user') or r.get('key') in GAME_TREES]
  return rows
 def draw_object_library(self,tab='objects'):
  """Tile picker, Map Objects tab: furniture and decorations made of map
  tiles (your own first, then the game's). Click one, then click a map tile."""
  from PIL import Image
  from map_object_catalogue import object_picture
  styles=self.object_styles_for_library(tab)
  self.tile_section.set('Whole map');self.tile_section_choices.configure(values=['Whole map'],state='disabled')
  columns=5;cell=56;rows=max(1,(len(styles)+columns-1)//columns)
  im=Image.new("RGBA",(columns*cell,rows*cell),(31,34,40,255));self.object_library_cells=[]
  for index,style in enumerate(styles):
   picture=style.get('image')
   if picture is None:
    try:picture=style['image']=object_picture(MapRenderer(self.editor.session,style['map']),style['rows'],style['kind'],style.get('cut'))[0]
    except Exception:continue
   scale=min(1,(cell-4)/picture.width,(cell-4)/picture.height)
   if scale<1:picture=picture.resize((max(1,int(picture.width*scale)),max(1,int(picture.height*scale))))
   x=index%columns*cell;y=index//columns*cell
   if style.get('user'):im.paste((44,52,66,255),(x+1,y+1,x+cell-1,y+cell-1))
   im.alpha_composite(picture,(x+(cell-picture.width)//2,y+cell-2-picture.height))
   self.object_library_cells.append((x,y,index,style))
  self.library_hits=[];self.library_height_lookup={};self.library_grid={}
  self.atlas_photo=ImageTk.PhotoImage(im,master=self.editor.root)
  self.library.delete("all");self.library.create_image(0,0,image=self.atlas_photo,anchor="nw");self.library.configure(scrollregion=(0,0,im.width,im.height))
  chosen=getattr(self,'bush_brush',None)
  for x,y,index,style in self.object_library_cells:
   if chosen is not None and chosen[0].get('kind')=='map_object' and chosen[0]['object'].get('key')==style.get('key'):
    self.library.create_rectangle(x,y,x+cell,y+cell,outline='white',width=2,tags='brush_selection')
 def object_at(self,event):
  x=self.library.canvasx(event.x);y=self.library.canvasy(event.y)
  for cx,cy,index,style in getattr(self,'object_library_cells',[]):
   if cx<=x<cx+56 and cy<=y<cy+56:return cx,cy,index,style
  return None
 def object_library_click(self,event):
  from map_object_catalogue import object_name
  hit=self.object_at(event)
  if hit is None:return
  cx,cy,index,style=hit
  if not getattr(self,'object_layer_auto',False):   # objects, trees and ladders lay on top by default
   self.object_layer_before=self.layer_floor.get();self.object_layer_auto=True
  self.layer_floor.set(True)
  self.set_bush_brush(dict(kind='map_object',object=style),object_name(self.editor.database.document,style,index))
  self.library.delete('brush_selection');self.library.create_rectangle(cx,cy,cx+56,cy+56,outline='white',width=2,tags='brush_selection')
 def library_right_click(self,event):
  """Map Objects / Trees: right-click an object to move it to the other tab
  (or delete one of your own)."""
  tab=self.source_tab()
  if tab not in ('objects','trees'):return
  hit=self.object_at(event)
  if hit is None:return
  style=hit[3];doc=self.editor.database.document
  menu=tk.Menu(self.library,tearoff=0)
  from map_object_catalogue import CATEGORIES,object_category
  here=object_category(doc,style)
  def move(other):
   doc.setdefault('map_object_categories',{})[style['key']]=other
   self.editor.dirty=True;self.atlas()
  for other,title in list(CATEGORIES)+[('trees','Trees')]:
   if other!=here:menu.add_command(label=f'Move to {title}',command=lambda o=other:self.editor.guard(lambda:move(o)))
  if style.get('user'):
   def delete():
    if not messagebox.askyesno('Delete map object',f"Delete your map object \"{style.get('name')}\"? Copies already placed stay.",parent=self.editor.root):return
    rows=doc.get('map_objects') or []
    rows[:]=[r for r in rows if r.get('key')!=style.get('key')]
    self.editor.dirty=True;self.atlas()
   menu.add_command(label='Delete',command=lambda:self.editor.guard(delete))
  try:menu.tk_popup(event.x_root,event.y_root)
  finally:menu.grab_release()
 def bush_library_click(self,event):
  from bush_catalogue import bush_name
  x=self.library.canvasx(event.x);y=self.library.canvasy(event.y)
  for cx,cy,index,style in getattr(self,'bush_library_cells',[]):
   if cx<=x<cx+30 and cy<=y<cy+40:
    self.set_bush_brush(style,bush_name(self.editor.database.document,style,index))
    self.library.delete('brush_selection');self.library.create_rectangle(cx,cy,cx+30,cy+40,outline='white',width=2,tags='brush_selection')
    return
 def tile_section_changed(self):
  if self.source_tab()=='tiles':
   return self.picker_jump(self.tile_section.get())
  source=self.picker_source()
  self.tile_section_memory[source]=self.tile_section.get()
  self.group_brush=None;self.group_brush_heights=None;self.bush_brush=None;self.face_brush=False;self.brush=None;self.brush_height=None;self.library_start=None
  self.atlas();self.library.xview_moveto(0);self.library.yview_moveto(0)
 def top_source_tab(self):
  return self.tile_source_frames.get(self.tile_source_tabs.select(),'map')
 def source_tab(self):
  """The picker tab in use; Bushes and Trees are sub-tabs of Map Objects (user 2026-10-18)."""
  top=self.top_source_tab()
  if top=='objects' and getattr(self,'object_kind','furniture') in ('bushes','trees'):return self.object_kind
  return top
 def picker_source(self):
  """What the tile picker shows: 'tiles', 'bushes', or a map number (Map tab)."""
  source=self.source_tab()
  if source=='map':
   m=getattr(self,'map_sub',None)
   return m if m in getattr(self,'picker_maps',[]) else self.editor.current_map
  return source
 def sync_tile_source_tabs(self):
  e=self.editor
  sources=e.database.document.get('map_tile_sources',{}).get(str(e.current_map),[])
  maps=[e.current_map]+[m for m in sources if type(m) is int and 0<=m<2547 and m!=e.current_map]
  maps=list(dict.fromkeys(maps));key=(id(e.session),e.current_map,tuple(maps))
  if self.tile_tab_key==key:return
  previous=self.top_source_tab() if self.tile_tab_key and self.tile_tab_key[:2]==key[:2] else 'map'
  for tab in self.tile_source_tabs.tabs():self.tile_source_tabs.forget(tab)
  for frame in getattr(self,'tile_source_widgets',[]):frame.destroy()
  self.tile_source_widgets=[];self.tile_source_frames={}
  # Map (its own tabs: Current Map and every added map), Tiles, Bushes
  self.picker_maps=maps
  if getattr(self,'map_sub',None) not in maps:self.map_sub=e.current_map
  self.tile_kind_mode=None   # rebuild the sub tabs for the new map list
  for source,title in (('map','Map'),('tiles','Tiles'),('objects','Map Objects')):
   frame=ttk.Frame(self.tile_source_tabs);self.tile_source_widgets.append(frame)
   self.tile_source_tabs.add(frame,text=title);self.tile_source_frames[str(frame)]=source
   if previous==source:self.tile_source_tabs.select(frame)
  self.tile_tab_key=key
 def choose_eraser(self):
  """'No tile' brush: painting removes the floor tile (or, on a wall layer, that wall piece)."""
  self.group_brush=None;self.group_brush_heights=None;self.bush_brush=None;self.face_brush=False
  self.brush=0xFFFF;self.brush_height=None;self.brush_is_wall=False;self.mode.set("Paint tiles")
  self.library.delete('group_selection');self.library.delete('brush_selection')
  self.caption.set("No tile: click or drag over tiles to remove them (the floor, or the wall piece you click).")
 def tile_source_changed(self):
  if not hasattr(self,'renderer') or not self.tile_source_tabs.select():return
  if getattr(self,'object_layer_auto',False) and self.top_source_tab()!='objects':
   self.layer_floor.set(self.object_layer_before);self.object_layer_auto=False   # back to how it was for tiles
  self.group_brush=None;self.group_brush_heights=None;self.bush_brush=None;self.face_brush=False;self.brush=None;self.brush_height=None;self.library_start=None
  self.atlas()
 def remove_map_tiles(self):
  """Take the map open in Map > (added map) off this map's list. Tiles already
  painted from it stay: they were copied into this map's own tile set."""
  e=self.editor;e.need()
  tab=self.source_tab()
  m=getattr(self,'map_sub',None)
  if tab!='map' or m is None or m==e.current_map:
   raise ValueError('Open the added map under Map first (Current Map cannot be removed)')
  sources=e.database.document.get('map_tile_sources',{}).get(str(e.current_map),[])
  if m in sources:sources.remove(m);e.dirty=True
  self.map_sub=e.current_map;self.tile_tab_key=None;self.sync_tile_source_tabs();self.atlas()
  self.caption.set(f"Map {m} removed from this map's tile list. Tiles you already used from it stay.")
 def add_map_tiles(self):
  self.editor.need()
  from location_picker import LocationPicker
  source_session=self.editor.session;target=self.editor.current_map
  def add(m):
   if self.editor.session is not source_session or self.editor.current_map!=target:raise ValueError('The target map changed; reopen Add map tiles')
   self.add_tile_source(m)
  LocationPicker(self.editor,on_choose=add)
 def add_tile_source(self,m):
   target=self.editor.current_map
   MapRenderer(self.editor.session,m) # Validate the donor before adding a tab.
   sources=self.editor.database.document.setdefault('map_tile_sources',{}).setdefault(str(target),[])
   if m!=target and m not in sources:sources.append(m);self.editor.dirty=True
   self.sync_tile_source_tabs()
   chosen=next((frame for frame,number in self.tile_source_frames.items() if number==m),None)
   if chosen:self.tile_source_tabs.select(chosen)
   self.atlas();self.caption.set('Added tile source: '+map_label(m))
 def restore_erased_tiles(self,codes):
  """Tile pictures of this map erased to make room (kept in the mod as erased_tile_art):
  the ones in `codes` are written back into the map's tile sheet before they are used."""
  e=self.editor;m=e.current_map
  erased=e.database.document.get('erased_tile_art',{}).get(str(m))
  if not erased:return
  want={c&1023 for c in codes if c!=0xFFFF and str(c&1023) in erased}
  if not want:return
  from map_tile_import import write_tile
  raw=bytearray(e.session.texture(m)[0])
  for i in want:write_tile(raw,i,bytes.fromhex(erased.pop(str(i))))
  e.session.defer_texture(m,bytes(raw))
  rt=e.session.__dict__.setdefault('restored_tiles',{});rt.setdefault(m,set()).update(want)   # never erased again while waiting
  self._flush_failed=set()
  self.update_renderer_textures();e.dirty=True;self.schedule_texture_flush()
 def translate_library_tiles(self,codes,source=None):
  from map_tile_import import import_tiles
  source=self.library_renderer.m if source is None else source;e=self.editor
  if source==e.current_map:self.restore_erased_tiles(codes)   # a picture erased to make room: put it back first
  # defer: the tile shows at once; compressing the map texture (seconds) is
  # done in the background a moment later, or at save/build/undo/map change.
  pending=getattr(self,'pending_stack_grid',None)   # waiting paint must not count as unused art
  keep=[] if pending is None else [c['values'][4] for c in pending[2]]+[k for c in pending[2] if c.get('walls') for k in c['walls'][1]]
  try:translated=import_tiles(e.session,e.database,e.current_map,source,codes,defer=True,keep_codes=keep)
  except ValueError as error:
   if 'texture/padding space' not in str(error) and 'No unused blank' not in str(error):raise
   # The tile sheet is full: offer to erase tile art this map never places.
   translated=import_tiles(e.session,e.database,e.current_map,source,codes,erase_unused=True,defer=True,keep_codes=keep)
  # pictures picked for painting are never erased to make room (paint may not be written yet)
  rt=e.session.__dict__.setdefault('restored_tiles',{})
  rt.setdefault(e.current_map,set()).update(c&1023 for c in (translated.values() if isinstance(translated,dict) else translated) if isinstance(c,int) and c!=0xFFFF)
  if source!=e.current_map:
   self.update_renderer_textures();e.dirty=True   # no full redraw: waiting edits stay waiting
   self.schedule_texture_flush()
  return translated
 # -- imported tile pictures: compressed in the background ------------------
 def schedule_texture_flush(self,delay=1500):
  job=getattr(self,'texture_flush_job',None)
  if job is not None:self.editor.root.after_cancel(job)
  self.texture_flush_job=self.editor.root.after(delay,self.start_texture_flush)
 def start_texture_flush(self):
  """Compress waiting textures on a worker thread (no Tk there); the result
  is written on the UI thread if the texture did not change meanwhile."""
  import threading,queue
  self.texture_flush_job=None
  session=self.editor.session;pending=dict(getattr(session,'_pending_textures',{}))
  failed=getattr(self,'_flush_failed',set())
  pending={m:raw for m,raw in pending.items() if id(raw) not in failed}   # never retry one that could not be stored
  if not pending:return
  from texture_codec import pack_ez_fit
  jobs=[]
  for m,raw in pending.items():
   _,start,end=session.texture(m);jobs.append((m,raw,bytes(session.data[start:start+6]),end-start))
  results=queue.Queue()
  def work():
   for m,raw,header,room in jobs:
    try:results.put((m,raw,room,pack_ez_fit(raw,header,room)))
    except Exception:results.put((m,raw,room,None))
  threading.Thread(target=work,daemon=True).start()
  def poll(left=len(jobs)):
   while True:
    try:m,raw,room,packed=results.get_nowait()
    except queue.Empty:break
    left-=1
    current=getattr(self.editor.session,'_pending_textures',{}).get(m)
    if current is raw and self.editor.session is session:
     _,start,end=session.texture(m)
     from map_tile_import import flush_texture
     before=getattr(session,'made_room',0)
     # too big to fit (packed None): flush_texture makes room itself (user 2026-10-25)
     try:flush_texture(session,self.editor.database,m,packed=packed if packed is not None and end-start==room else None)
     except Exception as exc:
      self._flush_failed=getattr(self,'_flush_failed',set())|{id(raw)}   # reported once, not retried
      self.editor.report_problem(exc)
     else:
      erased=getattr(session,'made_room',0)-before
      if erased:self.editor.status.set(f"Made room for the new tile pictures: {erased} tile picture(s) this map never uses were erased.")
   if left>0:self.editor.root.after(100,lambda:poll(left))
   elif any(id(r) not in getattr(self,'_flush_failed',set()) for r in getattr(self.editor.session,'_pending_textures',{}).values()):self.schedule_texture_flush()
  self.editor.root.after(100,poll)
 def flush_textures(self):
  """Save, build, undo, map change: write waiting textures now."""
  if getattr(self.editor.session,'_pending_textures',None):
   from map_tile_import import flush_texture
   for m in list(self.editor.session._pending_textures):
    try:flush_texture(self.editor.session,self.editor.database,m)   # makes room itself when too big
    except Exception as exc:self.editor.report_problem(exc)        # reported; saving and building carry on
 def library_press(self,event):
  if self.source_tab()=='bushes':
   self.library_start=None;return self.bush_library_click(event)
  if self.source_tab() in ('objects','trees'):
   self.library_start=None;return self.object_library_click(event)
  if self.source_tab() in ('water','lava'):
   self.library_start=None;return self.water_library_click(event)
  if self.source_tab()=='tiles':
   if self.tile_kind in ('stairs','water','ice','lava','sand','spikes'):self.library_start=None;return self.water_library_click(event)
   self.library_start=None;return self.floor_library_click(event)
  self.library_start=(self.library.canvasx(event.x),self.library.canvasy(event.y));self.library_click(event)
 def library_drag(self,event):
  if self.library_start:
   x,y=self.library_start;xx=self.library.canvasx(event.x);yy=self.library.canvasy(event.y)
   left,right=sorted((x,xx));top,bottom=sorted((y,yy))
   self.mark_library_tiles([(px,py,code) for px,py,code in self.library_hits if left<=px+12<=right and top<=py+8<=bottom])
 def mark_library_tiles(self,selected):
  self.library.delete('group_selection');self.library.delete('brush_selection')
  for px,py,code in selected:
   self.library.create_rectangle(px,py,px+24,py+16,outline='white',width=2,tags='brush_selection')
 def library_release(self,event):
  if not self.library_start:return
  x,y=self.library_start;self.library_start=None;xx=self.library.canvasx(event.x);yy=self.library.canvasy(event.y)
  if abs(xx-x)<8 and abs(yy-y)<8:return
  left,right=sorted((x,xx));top,bottom=sorted((y,yy))
  selected=[(px,py,code) for px,py,code in self.library_hits if left<=px+12<=right and top<=py+8<=bottom]
  if not selected:return
  ox=min(p[0] for p in selected);oy=min(p[1] for p in selected)
  # (a group across areas of the picker used to be refused: it is taken as selected now)
  translated=self.translate_library_tiles([code for px,py,code in selected])
  if translated is None:return
  self.brush=translated[selected[0][2]]
  self.group_brush={(int((px-ox)/24),int((py-oy)/16)):translated[code] for px,py,code in selected};self.brush_is_wall=False
  self.group_walls={(int((px-ox)/24),int((py-oy)/16)) for px,py,code in selected if getattr(self,'library_grid',{}).get((px,py,code),(0,0,0,'floor'))[3]=='wall'}
  # A square can show several pieces (floor under a claw): keep the ones under the top
  # piece too, or stamping left holes in the floor (user 2026-10-21)
  self.group_under={};stacks={};grid_info=getattr(self,'library_grid',{})
  for n,(px,py,code) in enumerate(selected):
   key=(int((px-ox)/24),int((py-oy)/16));info=grid_info.get((px,py,code))
   # draw order: lower map rows are in front; on one tile the floor is under its wall pieces
   order=(info[1],info[3]=='wall',n) if info else (-1,False,n)
   stacks.setdefault(key,[]).append((order,translated[code],bool(info) and info[3]=='wall'))
  self.group_walls=set()
  for key,pieces in stacks.items():
   pieces.sort()
   self.group_brush[key]=pieces[-1][1]
   if pieces[-1][2]:self.group_walls.add(key)
   if len(pieces)>1:self.group_under[key]=[(code,wall) for _,code,wall in pieces[:-1]]
  # The picker shows the source map raised by height, so the group is the picture
  # you selected. Stamping it at the source heights raised it a second time and
  # left gaps; the stamp is laid flat instead (see paint_selected).
  self.group_brush_heights=None
  self.mark_library_tiles(selected)
  self.mode.set("Paint tiles");self.caption.set(f"Group brush: {len(self.group_brush)} tiles. Click map to stamp floor artwork.")
 def library_click(self,event):
  x=int(self.library.canvasx(event.x));y=int(self.library.canvasy(event.y))
  for px,py,code in reversed(self.library_hits):
   if px<=x<px+24 and py<=y<py+16:
    if not self.manual_palette.get() and not self.library_renderer.tile(code).getpixel((x-px,y-py))[3]:continue
    self.group_brush=None;self.group_brush_heights=None;self.bush_brush=None;self.face_brush=False
    translated=self.translate_library_tiles([code])
    if translated is None:return
    kind=getattr(self,'library_grid',{}).get((px,py,code),(0,0,0,'floor'))[3]
    self.brush=translated[code];self.brush_height=self.library_height_lookup.get((px,py,code));self.brush_is_wall=kind=='wall'   # walls from this map / imported maps act as walls too
    self.caption.set(f"Brush tile {code&1023}, palette {code>>12}");self.mode.set("Paint tiles")
    self.mark_library_tiles([(px,py,code)])
    return
 def event_lift(self,row):
  """Pixels a project event is drawn above the ground: its set height, else
  the height of its top-left tile (0 when elevation is off)."""
  if not self.elevation_enabled():return 0
  x,y=row["region"][:2];height=row.get('native_placement',{}).get('height')
  if height is None and 0<=x<getattr(self,'grid_width',0) and 0<=y<getattr(self,'grid_height',0):
   height=self.grid_cells[y*self.grid_width+x]["values"][3]
  return (height or 0)*16
 def selecting(self):
  """Select, Events and Warps tabs handle the map the same way; Events and
  Warps only add their list beside the map."""
  return self.mode.get() in ("Select tile","Events","Warps")
 def record_at(self,event):
  if not self.events_allowed():return None
  x=self.canvas.canvasx(event.x);y=self.canvas_y(event)
  for px,py,index in reversed(self.markers):
   left=math.floor(px/24)*24;top=math.floor((py-8)/16)*16
   if left<=x<left+24 and top<=y<top+16:return "entities",index
  if self.selecting():
   warp=warp_at_visual_point(self.warp_hit_boxes,x,y)
   if warp is not None:return "warps",warp
  if self.selecting():
   choices=[]
   for i,r in enumerate(self.info["events"]):
    if not self.default_visible("events"):continue
    if i in self.whole_map_events or record_deleted(self.editor.database.document,self.editor.current_map,'events',i):continue
    a,b,c,d=r["rectangle"]
    if a*24<=x<(a+1)*24 and b*16+self.margin<=y<(b+1)*16+self.margin:choices.append(((c-a+1)*(d-b+1),i))  # top-left tile only
   if choices:return "events",min(choices)[1]
  if self.selecting():
   choices=[]
   for index,row in self.project_graphs:
    if index in self.whole_map_graphs:continue
    a,b,w,h=row["region"];lift=self.event_lift(row)
    if a*24<=x<(a+1)*24 and b*16+self.margin-lift<=y<(b+1)*16+self.margin-lift:  # top-left tile only
     choices.append((w*h,index))
   if choices:return "graphs",min(choices)[1]
   # also the picture itself: a sprite taller than its tile box is clickable anywhere on it
   cx=self.canvas.canvasx(event.x);cy=self.canvas.canvasy(event.y)
   for item in reversed(self.canvas.find_overlapping(cx,cy,cx,cy)):
    for tag in self.canvas.gettags(item):
     if tag.startswith('graphs_') and tag[7:].isdigit() and int(tag[7:]) not in self.whole_map_graphs:
      return "graphs",int(tag[7:])
 def press(self,event):
  self.canvas.focus_set()
  if self.start_point_armed:
   self.set_start_point_from_click(event);return
  if self.mask_layer.get():return self.stroke_start('mask',event)
  if self.mark_walls.get():return self.stroke_start('walls',event)
  if self.height_edit.get():
   if getattr(self,'tile_info',None) is not None and self.tile_info.get():return self.open_tile_info(event)   # Tile info: edit the tiles on this square
   if self.height_show.get()=='Buggy' and self.buggy_click(event):return   # Buggy tiles view: edit the tall tile clicked
   if event.state&0x0001:return self.stroke_start('walls',event)   # Shift: x that blocks only the player
   if self.height_brush.get()==-2:return self.make_grey(event)
   if self.height_brush.get()<=-3:return self.set_slope(event)
   if self.height_brush.get()>=0:self.height_paint_last=None;self.height_paint_last_empty=None;self.height_paint_alone_last=None;self.paint_height(event);return
   return self.stroke_start('height',event)
  if self.stack_brush() is not None and self.mode.get()=="Paint tiles":
   if self.stack_brush()[0].get('kind') in ('map_object','layer') and not self.stack_brush()[0].get('auto'):   # one click, one tile/object: no dragging (Layer On Top: user 2026-10-18); wall tiles drag
    self.drag_point=None;self.record_drag=None;self.bush_stroke=[];self.bush_stroke_add(event);return self.place_bush_stroke()
   self.bush_stroke=[];self.bush_stroke_add(event);return
  self.drag_point=(event.x,event.y);self.stroke_cells=set();self.record_drag=None
  if self.mode.get() in ("Select tile","Entities","Events","Warps"):
   lock=getattr(self.editor,'lock_in_closed_events',None)
   if lock:lock()   # clicks pick from the saved event list
   record=self.record_at(event)
   self.selected_record=record;self.drag_delta=(0,0);self.drag_shift=(0,0);self.highlight_record()
   if record:
    key=f"{record[0]}:{record[1]}"
    if self.record_list.exists(key):self.record_list.selection_set(key);self.record_list.see(key)
   if record:
    self.selected=None;self.canvas.delete("selection")
    self.record_drag=(*record,self.editor.current_map,self.canvas.canvasx(event.x),self.canvas_y(event))
    self.caption.set(f"Selected {record[0]} {record[1]}: drag to move; double-click to edit process.")
   if record or not self.selecting():return
  self.click(event,repaint=self.mode.get()!="Paint tiles")
  if self.mode.get()=="Paint tiles":self.schedule_lock_in()
 def fill_tile(self,event):
  hit=self.renderer.surface_at(self.canvas.canvasx(event.x),self.canvas_y(event)) if hasattr(self,'renderer') else None
  if hit is None:return None
  tx,ty=hit[2:4]
  return (tx,ty) if 0<=tx<self.grid_width and 0<=ty<self.grid_height else None
 def fill_press(self,event):
  if self.height_edit.get() or self.mark_walls.get() or self.mask_layer.get():return self.press(event)
  if self.mode.get()!="Paint tiles":return self.press(event)
  self.canvas.focus_set();self.fill_start=self.fill_tile(event);self.fill_drag(event)
 def fill_bounds(self,event):
  end=self.fill_tile(event) or self.fill_start
  (x1,y1),(x2,y2)=self.fill_start,end
  return min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2)
 def fill_drag(self,event):
  if getattr(self,'tile_stroke',None) is not None:return self.drag(event)
  if self.fill_start is None or self.mode.get()!="Paint tiles":return
  x1,y1,x2,y2=self.fill_bounds(event)
  self.canvas.delete('fill_preview')
  for tx in range(x1,x2+1):
   for ty in range(y1,y2+1):
    cell=self.grid_cells[ty*self.grid_width+tx]
    py=map_y_to_view(ty*16+self.margin-(cell["values"][3]*16 if self.elevation_enabled() else 0),getattr(self,'map_crop_top',0))
    self.canvas.create_rectangle(tx*24,py,tx*24+24,py+16,outline='#ffd84a',tags='fill_preview')
  self.caption.set(f"Fill {x2-x1+1} x {y2-y1+1} tiles: release to paint them all")
 def fill_release(self,event):
  if self.mode.get()!="Paint tiles" or self.fill_start is None:return self.release(event)
  bounds=self.fill_bounds(event);self.fill_start=None;self.canvas.delete('fill_preview')
  self.fill_rectangle(*bounds)
 def fill_rectangle(self,x1,y1,x2,y2):
  """Paint every tile in the rectangle with the brush; a group brush repeats as a pattern."""
  import struct
  if self.brush is None and not self.group_brush:raise ValueError("Pick a tile from the tile picker first")
  self.commit_pending()
  e=self.editor;edits=[]
  if self.group_brush:
   gw=max(dx for dx,dy in self.group_brush)+1;gh=max(dy for dx,dy in self.group_brush)+1
  for ty in range(y1,y2+1):
   for tx in range(x1,x2+1):
    if self.group_brush:
     key=((tx-x1)%gw,(ty-y1)%gh);code=self.group_brush.get(key)
     if code is None:continue
    else:code=self.brush
    height=None   # painting changes the picture only; the floor keeps its height
    cell=self.grid_cells[ty*self.grid_width+tx]
    if self.wall.get()!="Floor":
     layer=int(self.wall.get().split()[1])
     if layer<len(cell["walls"]):edits.append((cell["walls"][layer][0],struct.pack("<H",code)))
     continue
    if cell["values"][4]==0xFFFF:height=self.new_tile_height(tx,ty)  # new tile on empty ground
    if height is None:height=cell["values"][3]
    edits.append((cell["offset"]+3,struct.pack("<BH",height,code)))
  if not edits:return
  start=min(o for o,raw in edits);end=max(o+len(raw) for o,raw in edits)
  payload=bytearray(e.session.data[start:end])
  for o,raw in edits:payload[o-start:o-start+len(raw)]=raw
  e.session.replace(start,payload,f"Fill {x2-x1+1}x{y2-y1+1} tiles")
  e.dirty=True;self.refresh(reload_textures=False);self.atlas()
  self.caption.set(f"Filled {len(edits)} tiles. Undo removes the whole fill.")
 def finish_paint(self):
  self.schedule_lock_in()
 def release(self,event=None):
  try:return self.release_action(event)
  finally:self.commit_action()
 def release_action(self,event=None):
  if getattr(self,'tile_stroke',None) is not None:
   kind=self.tile_stroke['kind'];n=len(self.tile_stroke['done']);self.tile_stroke=None
   if kind=='walls':self.redraw_height_numbers_from_grid()
   if n>1:self.caption.set(f"{n} tiles changed in one stroke.")
   return
  if getattr(self,'bush_stroke',None) is not None:return self.place_bush_stroke()
  if self.pending_tiles:self.schedule_lock_in()
  record=self.record_drag;self.record_drag=None;self.drag_point=None;self.stroke_cells=set();self.canvas.delete("move_preview")
  pending_redraw=getattr(self,'redraw_after_drag',False);self.redraw_after_drag=False
  if pending_redraw and not (record and event is not None):self.draw_records()
  if record:self.highlight_record()   # also when dropped back on the same tile
  if record and event is not None:
   kind,index,m,x,y=record
   if m!=self.editor.current_map:return
   dx=round((self.canvas.canvasx(event.x)-x)/24);dy=round((self.canvas_y(event)-y)/16)
   if kind=="graphs" and abs(self.canvas.canvasx(event.x)-x)<6 and abs(self.canvas_y(event)-y)<6 and self.drag_delta==(0,0):
    dx=dy=0   # a plain click selects; it never moves the event
   elif kind=="graphs":
    # A quick flick can end with the button released before the last pointer
    # move was handled: take the tile under the release point too.
    self.drag_graph(index,self.canvas.canvasx(event.x),self.canvas_y(event))
    dx,dy=self.drag_delta   # the tile it is shown on
   self.drag_shift=(0,0)
   if pending_redraw and not (dx or dy):self.draw_records();self.highlight_record()
   if dx or dy:
    try:
     if kind=="warps":move_warp(self.editor.session,m,index,dx,dy)
     elif kind=="graphs":
      document=self.editor.database.document
      row=document["event_graphs"][index]
      x,y,w,h=row["region"]
      if 0<=x+dx<256 and 0<=y+dy<256:
       # one undo step (Undo puts the event back where it was)
       moved=dict(row,region=[x+dx,y+dy,w,h])
       replacement=dict(document,event_graphs=[moved if i==index else r for i,r in enumerate(document["event_graphs"])])
       self.editor.session.replace_document(document,replacement,'Move event '+row.get('name',row.get('id','')))
       row=document["event_graphs"][index]
       self.editor.dirty=True;self.clear_in_front_of_switches()
       window=getattr(self.editor,'event_graph_window',None)   # keep an open event editor in step
       if window is not None and window.window.winfo_exists():window.event_moved(row['id'],row['region'])
      else:self.caption.set("Event cannot be moved outside the map coordinate range.")
     else:move_record(self.editor.session,m,kind,index,dx,dy)
    finally:self.draw_records();self.highlight_record()   # box follows the moved event
    self.caption.set("Event moved. Undo restores its previous position.")
 def double_click(self,event):
  if self.height_edit.get():
   if self.height_brush.get()>=0:return   # painting a height: a double-click is just two clicks on the same tile
   return self.adjust_height(event,+1)   # quick clicks: every click counts
  if self.mark_walls.get():return self.unwall(event)               # never an event while marking walls
  if self.mask_layer.get():return self.toggle_mask(event)          # nor while masking
  if self.mode.get()=="Paint tiles":return                          # painting never creates events
  if time.monotonic()<getattr(self,'ignore_start_double_until',0):return
  if not self.events_allowed():return
  if not self.selecting():return
  x=self.canvas.canvasx(event.x);y=self.canvas_y(event)
  self.record_drag=None;self.drag_point=None
  record=self.record_at(event)
  if record:
   if record[0]=="graphs":
    row=self.editor.database.document["event_graphs"][record[1]];self.editor.open_event_builder(row["id"]);return
   if record[0]=="warps":WarpWindow(self.editor,record[1]);return
   from event_process_ui import EventProcess
   EventProcess(self.editor,*record)
  else:
   hit=self.renderer.surface_at(x,y)
   if hit is None:return
   _,_,tx,ty,_,_=hit
   self.editor.create_event_at(self.editor.current_map,tx,ty)

 def click(self,event,pick=False,repaint=True):
  x=self.canvas.canvasx(event.x);y=self.canvas_y(event);e=self.editor
  if self.mode.get()=="Entities" and not pick:
   for left,top,right,bottom,index in reversed(self.sprite_boxes):
    if left<=x<right and top<=y<bottom:self.open_record("entities",index);return
  if self.mode.get()=="Entities" and not pick:
   candidates=[(abs(x-px)+abs(y-(py-8)),i) for px,py,i in self.markers]
   if candidates and min(candidates)[0]<32:self.open_record("entities",min(candidates)[1])
   return
  if not pick and self.mode.get()=="Paint tiles" and self.group_brush:
   key=('stamp',int(x)//24,int(y)//16)
   if key in self.stroke_cells:return
   self.stroke_cells.add(key);return self.stamp_group_on_screen(x,y)
  hit=self.paint_target(x,y) if not pick and self.mode.get()=="Paint tiles" else self.renderer.surface_at(x,y)
  for px,py,tx,ty,layer,code in ([hit] if hit else []):
   if px<=x<px+24 and py<=y<py+16:
    if not pick and self.mode.get()=="Paint tiles":
     if (tx,ty,layer) in self.stroke_cells:return
     self.stroke_cells.add((tx,ty,layer))
    self.wall.set(layer)
    self.select(tx,ty)
    if pick:self.pick()
    elif self.mode.get()=="Paint tiles":
     if self.brush is None:self.caption.set("Choose a tile from the library, or right-click the map to pick a brush.");return
     self.paint_selected(repaint=repaint)
    return
 def floor_tile_at(self,x,y):
  """Map tile whose floor is drawn under canvas point x, y (None off the map)."""
  renderer=getattr(self,'renderer',None)
  if renderer is None:return None
  candidates=renderer.surface_hits.get((int(x)//24,int(y)//16),[])
  floors=[c for c in candidates if c[4]=="Floor"]
  for px,py,tx,ty,layer,code in reversed(floors):
   try:
    if renderer.tile(code).getpixel((int(x-px),int(y-py)))[3]:return tx,ty
   except Exception:continue
  return (floors[-1][2],floors[-1][3]) if floors else None
 def drag_graph(self,index,px,py):
  """Your events follow the tile under the pointer (at that tile's height),
  so where it is shown while dragging is exactly where it is dropped."""
  # Follow the pointer one tile per tile moved (no snapping to raised
  # surfaces), so any tile can be reached, hidden or not.
  rows=dict(self.project_graphs);row=rows.get(index)
  if row is None or not self.record_drag:return
  sx,sy=self.record_drag[3:5]
  ox,oy=row["region"][:2];dx=round((px-sx)/24);dy=round((py-sy)/16)
  # The tile under the pointer as drawn (raised tiles are drawn higher up), kept
  # at the same offset from the event as where it was grabbed (2026-10-18: moving
  # by raw pixels dropped events on the wrong tile next to raised ground).
  start=self.floor_tile_at(sx,sy);now=self.floor_tile_at(px,py)
  if start is not None and now is not None:dx,dy=now[0]-start[0],now[1]-start[1]
  tx,ty=ox+dx,oy+dy
  if not (0<=tx<getattr(self,'grid_width',256) and 0<=ty<getattr(self,'grid_height',256)):return
  if (dx,dy)==self.drag_delta:return
  def lifted(x,y):
   return self.event_lift(dict(row,region=[x,y]+list(row["region"][2:])))
  shift=(dx*24,dy*16-(lifted(tx,ty)-lifted(ox,oy)))   # shown at the height it will have when dropped
  old=getattr(self,'drag_shift',(0,0))
  self.canvas.move(f"graphs_{index}",shift[0]-old[0],shift[1]-old[1])
  self.drag_shift=shift;self.drag_delta=(dx,dy);self.highlight_record()
  self.caption.set(f"Move event to tile {tx}, {ty}")
 def drag(self,event):
  if getattr(self,'bush_stroke',None) is not None:return self.bush_stroke_add(event)
  if getattr(self,'tile_stroke',None) is not None:return self.editor.guard(lambda:self.stroke_continue(event))
  if self.height_edit.get():
   if self.height_brush.get()==-2:self.editor.guard(lambda:self.make_grey(event))
   if self.height_brush.get()<=-3:self.editor.guard(lambda:self.set_slope(event))
   if self.height_brush.get()>=0:self.editor.guard(lambda:self.paint_height(event))
   return
  if self.record_drag:
   kind,index,m,x,y=self.record_drag
   px=self.canvas.canvasx(event.x);py=self.canvas_y(event)
   if kind=="graphs":
    if abs(px-x)<6 and abs(py-y)<6 and self.drag_delta==(0,0):return   # a click, not a drag
    return self.drag_graph(index,px,py)
   dx=round((px-x)/24);dy=round((py-y)/16)
   oldx,oldy=self.drag_delta
   if (dx,dy)==self.drag_delta:return
   self.canvas.move(f"{kind}_{index}",(dx-oldx)*24,(dy-oldy)*16)
   self.drag_delta=(dx,dy);self.highlight_record()
   self.caption.set(f"Move {kind} {index}: {dx:+} tiles across, {dy:+} tiles down")
   return
  if self.drag_point is None:return
  if self.selecting():
   self.editor.guard(lambda:self.click(event));return
  if self.mode.get()!="Paint tiles":return
  def stroke():
   x,y=self.drag_point;dx=event.x-x;dy=event.y-y
   # Pointer events may span hundreds of pixels. One sample per crossed tile
   # keeps strokes continuous without doing redundant work for every pixel.
   steps=tile_stroke_steps(dx,dy)
   for i in range(1,steps+1):
    self.click(SimpleNamespace(x=x+dx*i/steps,y=y+dy*i/steps),repaint=False)
   self.drag_point=(event.x,event.y)
   self.schedule_lock_in()
  self.editor.guard(stroke)
 def select(self,x,y):
  w,h,cells=self.grid_width,self.grid_height,self.grid_cells
  if not 0<=x<w or not 0<=y<h:self.selected=None;return
  self.selected=(x,y);c=cells[y*w+x]
  for var,v in zip(self.vars,c["values"][:5]):var.set(str(v))
  self.update_layer_choices()
  self.caption.set(f"Selected cell {x}, {y} | brush {self.brush if self.brush is not None else 'none'}")
  self.canvas.delete("selection");self.canvas.delete("record_selection");self.selected_record=None
  yy=map_y_to_view(y*16+self.margin-(c["values"][3]*16 if self.elevation_enabled() else 0),getattr(self,'map_crop_top',0))
  if self.wall.get()!="Floor" and int(self.wall.get().split()[1])<len(c["walls"]) and self.elevation_enabled():
   _,_,shift,i=c["walls"][int(self.wall.get().split()[1])];yy+=(i+1-shift)*16
  self.canvas.create_rectangle(x*24,yy,x*24+24,yy+16,outline="white",width=2,tags="selection")
 def pick(self):
  if self.selected is None:raise ValueError("Select a floor cell first")
  x,y=self.selected;c=self.grid_cells[y*self.grid_width+x]
  self.group_brush=None;self.group_brush_heights=None;self.bush_brush=None;self.face_brush=False
  if self.wall.get()!="Floor" and int(self.wall.get().split()[1])>=len(c["walls"]):self.wall.set("Floor")   # that layer is not on this tile: pick its floor (user 2026-10-25)
  self.brush=c["values"][4] if self.wall.get()=="Floor" else c["walls"][int(self.wall.get().split()[1])][1]
  self.brush_is_wall=False   # a brush picked with right-click paints, it never makes walls (x)
  self.brush_height=c["values"][3] if self.wall.get()=="Floor" else None
  self.caption.set(f"Picked {self.wall.get()} tile code {self.brush}");self.mode.set("Paint tiles")
 def new_tile_height(self,x,y):
  """Height for a tile placed on empty ground: the commonest height of the
  existing tiles around it (up to 2 tiles away), else 1."""
  heights=[]
  for r in (1,2):
   for dy in range(-r,r+1):
    for dx in range(-r,r+1):
     tx,ty=x+dx,y+dy
     if (dx or dy) and 0<=tx<self.grid_width and 0<=ty<self.grid_height:
      v=self.grid_cells[ty*self.grid_width+tx]["values"]
      if v[4]!=0xFFFF:heights.append(v[3])
   if heights:return max(set(heights),key=heights.count)
  return 1
 def paint_selected(self,repaint=True):
  if self.selected is None or self.brush is None:raise ValueError("Select a cell and a tile brush")
  if not self.group_brush:return self.paint_single(repaint)
  e=self.editor;x,y=self.selected
  if self.group_brush:
   import struct
   self.commit_pending()
   edits=[]
   anchor=self.grid_cells[y*self.grid_width+x]["values"]
   stamp_height=self.new_tile_height(x,y) if anchor[4]==0xFFFF else anchor[3]
   for (dx,dy),code in self.group_brush.items():
    tx,ty=x+dx,y+dy
    if not 0<=tx<self.grid_width or not 0<=ty<self.grid_height:continue   # the part over the edge is simply left off
    cell=self.grid_cells[ty*self.grid_width+tx]
    if self.wall.get()=="Floor":offset=cell["offset"]+4
    else:
     layer=int(self.wall.get().split()[1])
     if layer>=len(cell["walls"]):continue   # no such wall layer on this tile
     offset=cell["walls"][layer][0]
    # One flat height for the whole stamp (the clicked tile's, or 1 on empty
    # ground), so the copied picture lands exactly as selected with no gaps.
    # Each placed tile keeps the height of the tile it lands on (empty ground
    # takes the stamp's height).
    own=cell["values"][3] if cell["values"][4]!=0xFFFF else stamp_height
    source_height=own if self.wall.get()=="Floor" else None
    edits.append((offset,code,source_height,cell))
   if not edits:return
   start=min(o-1 if height is not None and self.wall.get()=="Floor" else o for o,code,height,cell in edits)
   end=max(o+2 for o,code,height,cell in edits)
   payload=bytearray(e.session.data[start:end])
   for o,code,height,cell in edits:
    if height is not None and self.wall.get()=="Floor":
     struct.pack_into("<BH",payload,o-1-start,height,code)
     cell["values"]=tuple(cell["values"][:3])+(height,code)+tuple(cell["values"][5:])
    else:struct.pack_into("<H",payload,o-start,code)
   e.session.replace(start,payload,"Tile group stamp");self.refresh(reload_textures=False);return
 def paint_single(self,repaint=True):
  import struct
  e=self.editor;x,y=self.selected
  c=self.grid_cells[y*self.grid_width+x];old_rows=self.tile_rows(x,y)
  if self.wall.get()=="Floor":
   # Painting changes the picture only: the floor keeps its own height (the
   # tile's height in the picker or where it was picked is not copied, which
   # dropped or raised the painted tile and left a gap). A tile placed where
   # there was none takes the height of the floor around it.
   height=c["values"][3]   # the painted tile keeps the height of the tile it replaces
   if getattr(self,'force_wall',None) is not None and self.force_wall.get() and self.brush!=0xFFFF:
    # Force wall: the painted tile keeps the height there and acts as a wall: no-walk
    walk=self.pending_tiles.get(c["offset"],bytes((c["values"][0],)))[0]|1
    self.pending_tiles[c["offset"]]=bytes((walk,))
    walled=self.editor.database.document.setdefault('walled_tiles',{}).setdefault(str(self.editor.current_map),[])
    if [x,y] not in walled:walled.append([x,y])
    v0=list(c["values"]);v0[0]=walk;c["values"]=tuple(v0);self.sync_stack_walk(x,y,walk)
   # Painting is visual first: the change waits in pending_tiles and is locked in
   # (one undo step) when you pause, change map, save, build or undo.
   self.pending_tiles[c["offset"]+3]=struct.pack("<BH",height,self.brush)
   values=list(c["values"]);values[3]=height;values[4]=self.brush;c["values"]=tuple(values)
   py=map_y_to_view(y*16+self.margin-(values[3]*16 if self.elevation_enabled() else 0),getattr(self,'map_crop_top',0))
  else:
   layer=int(self.wall.get().split()[1])
   if layer>=len(c["walls"]):   # that layer is not on this tile: the picture is laid on top of it instead (user 2026-10-25)
    old=self.tile_rows(x,y);floor=y-(c["values"][3] if self.elevation_enabled() else 0)
    pieces={row-floor:cd for row,cd,f in self.record_pieces(c) if not f};rel=(max(pieces)+1) if pieces else 0
    pieces[rel]=self.brush;walls=self.rebased_walls(pieces)
    if walls is not False:self.set_cell_walls(x,y,walls);self.redraw_columns([(x,y)],before={(x,y):old})
    self.schedule_lock_in();return
   offset,_,shift,i=c["walls"][layer]
   if offset is None:
    g=self.stack_grid();w=self.grid_width;sc=g[2][y*w+x]
    sh,codes=sc['walls'];codes=list(codes);codes[layer]=self.brush;sc['walls']=(sh,codes);self.pending_stack_tiles.add((x,y))
   else:self.pending_tiles[offset]=struct.pack("<H",self.brush)
   c["walls"][layer]=(offset,self.brush,shift,i)
   floor_y=y*16+self.margin-(c["values"][3]*16 if self.elevation_enabled() else 0)
   py=map_y_to_view(floor_y+(i+1-shift)*16,getattr(self,'map_crop_top',0))
  self.redraw_columns([(x,y)],before={(x,y):old_rows})
  if self.height_edit.get():self.redraw_height_numbers_from_grid()
  self.schedule_lock_in()
  if repaint:self.lock_in()
 def schedule_lock_in(self,delay=1500):
  """Painted tiles stay shown as a preview and are written to the map when
  you save or build (or change map / undo); no timed lock-in any more."""
  return
 def has_pending_edits(self):
  """Painted tiles, clicked heights or wall-stack edits not yet in the game data
  (waiting imported tile pictures do not count)."""
  return bool(getattr(self,'pending_tiles',None) or getattr(self,'pending_heights',None) or getattr(self,'pending_stack_grid',None) is not None)
 def commit_action(self):
  """Each placement (a tile stroke, a bush, a map object) goes into the game
  data when the mouse is let go: Undo then takes back just that one. Height
  editing keeps its edits waiting as before."""
  if self.height_edit.get() or not self.has_pending_edits():return
  self.commit_pending()
 def has_pending(self):
  return bool(getattr(self,'pending_tiles',None) or getattr(self,'pending_heights',None) or getattr(self,'pending_stack_grid',None) is not None
              or getattr(getattr(self.editor,'session',None),'_pending_textures',None))
 def commit_heights(self):
  """Write the clicked heights to the game data as one undo step."""
  heights=getattr(self,'pending_heights',None)
  if not heights or self.editor.session is None:return False
  self.pending_heights={}
  session=self.editor.session
  with session.group(f"Height edits ({len(heights)})"):
   for offset,value in sorted(heights.items()):session.replace(offset,bytes((value,)),"Map tile")
  self.editor.dirty=True
  self.editor.status.set(f"{len(heights)} height/no-walk change(s) saved. Undo restores them together.")
  return True
 def pending_byte(self,at):
  """A map byte as it will be written: clicked heights win over painted tiles."""
  if at in self.pending_heights:return self.pending_heights[at]
  for o,raw in getattr(self,'pending_tiles',{}).items():
   if o<=at<o+len(raw):return raw[at-o]
  return self.editor.session.data[at]
 def commit_pending(self):
  """Write painted tiles (and clicked heights) to the game data as one undo
  step each; True if anything was written."""
  # Painted tiles are merged into the clicked heights first (a height you set
  # later always wins over the height byte a paint stored), then all go in.
  pending=getattr(self,'pending_tiles',None) or {}
  heights=getattr(self,'pending_heights',{})
  for o,raw in list(pending.items()):
   raw=bytearray(raw)
   for i in range(len(raw)):
    if o+i in heights:raw[i]=heights[o+i]
   pending[o]=bytes(raw)
  wrote=self.commit_heights()   # heights first: their byte positions are from the grid as loaded
  wrote=self.commit_stacks() or wrote   # then wall stacks: rebuilt from the map as it is now
  if not pending or self.editor.session is None:return wrote
  self.pending_tiles={}
  start=min(pending);end=max(o+len(raw) for o,raw in pending.items())
  payload=bytearray(self.editor.session.data[start:end])
  for o,raw in pending.items():payload[o-start:o-start+len(raw)]=raw
  self.editor.session.replace(start,payload,f"Paint {len(pending)} tiles")
  self.editor.dirty=True
  self.editor.status.set(f"Painted {len(pending)} tiles. Undo removes them together.")
  return True
 def lock_in(self):
  """Commit pending paint, then redraw the map once. (Waiting imported
  textures are written by flush_textures: save, build, undo, map change.)"""
  if self.paint_job is not None:self.editor.root.after_cancel(self.paint_job);self.paint_job=None
  if self.commit_pending():
   self.refresh(reload_textures=False)
 def clear_group_preview(self):
  self.canvas.delete('group_footprint');self.group_preview_anchor=None
 def preview_tile(self,event):
  """White placer under the pointer in Paint mode: the exact tile (floor or
  wall face, layer on floor included) a click paints."""
  x,y=self.canvas.canvasx(event.x),self.canvas_y(event)
  hit=self.renderer.surface_at(x,y)
  if hit is None:
   walls=[h for h in self.renderer.surface_hits.get((int(x)//24,int(y)//16),[]) if h[4]!="Floor"]
   hit=walls[-1] if walls else ((int(x)//24*24,int(y)//16*16) if self.brush not in (None,0xFFFF) else None)
  if hit is None:self.clear_group_preview();return
  px,py=hit[0],hit[1];key=('tile',px,py)
  if key==getattr(self,'group_preview_anchor',None):return
  self.clear_group_preview();self.group_preview_anchor=key
  vy=map_y_to_view(py,getattr(self,'map_crop_top',0))
  self.canvas.create_rectangle(px,vy,px+24,vy+16,outline='white',width=2,tags='group_footprint')
 def preview_group(self,event):
  if self.mode.get()=='Paint tiles' and not self.group_brush and hasattr(self,'renderer'):
   return self.preview_tile(event)
  if self.mode.get()!='Paint tiles' or not self.group_brush or not hasattr(self,'renderer'):
   self.clear_group_preview();return
  bx=int(self.canvas.canvasx(event.x))//24*24;by=int(self.canvas_y(event))//16*16
  key=(bx,by,tuple(self.group_brush))
  if key==getattr(self,'group_preview_anchor',None):return
  self.clear_group_preview();self.group_preview_anchor=key
  crop=getattr(self,'map_crop_top',0)
  for dx,dy in self.group_brush:   # the squares the stamp covers on screen, exactly
   px=bx+dx*24;py=map_y_to_view(by+dy*16,crop)
   self.canvas.create_rectangle(px,py,px+24,py+16,outline='white',fill='white',stipple='gray25',width=2,tags='group_footprint')
 def apply(self):
  if self.selected is None:raise ValueError("Select a cell first")
  edit_cell(self.editor.session,self.editor.current_map,*self.selected,[int(v.get(),0) for v in self.vars]);self.refresh(reload_textures=False)
 def open_record(self,kind,index):
  tree,fields,names=self.editor.record_views[kind];tree.selection_set(str(index));tree.see(str(index));self.editor.select_record(kind)
  win=tk.Toplevel(self.editor.root);win.title("Character properties" if kind=="entities" else "Event properties")
  form=ttk.Frame(win,padding=12);form.pack(fill="both",expand=True)
  source_session=self.editor.session;source_map=self.editor.current_map
  values=[]
  for n,(name,field) in enumerate(zip(names,fields)):
   ttk.Label(form,text=name).grid(row=n,column=0,sticky="w",padx=(0,12),pady=2)
   value=tk.StringVar(value=field.get());values.append(value)
   ttk.Entry(form,textvariable=value,state="readonly" if "Reserved" in name or "Unknown" in name else "normal").grid(row=n,column=1,pady=2)
  def apply():
   if self.editor.session is not source_session or self.editor.current_map!=source_map:
    raise ValueError("The open map changed. Close these properties and select the character again.")
   tree.selection_set(str(index))
   for field,value in zip(fields,values):field.set(value.get())
   self.editor.apply_record(kind);self.refresh(reload_textures=False);win.destroy()
  ttk.Button(form,text="Apply",command=lambda:self.editor.guard(apply)).grid(row=len(names),column=0,pady=10)
  ttk.Button(form,text="Cancel",command=win.destroy).grid(row=len(names),column=1,pady=10)
