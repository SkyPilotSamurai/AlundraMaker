"""Desktop UI for bounded Alundra DATAS edits."""
import json,struct,threading,queue,hashlib
import sys as _sys
# Speed (user 2026-10-26): the background loaders (preload, build warmer) are Python threads; with the
# default 5 ms GIL switch every Tk call of the window waited behind them, so drawing a map or the
# Edit heights numbers took seconds while they ran (measured 5 s -> 0.2 s). A short switch interval
# lets the window run at once; the loaders only get a little slower.
_sys.setswitchinterval(0.0002)
from types import SimpleNamespace
from mod_export import save_mod,load_mod,build_game,read_datas
from pathlib import Path
from attack_attributes import parse_attribute
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,colorchooser
from PIL import Image,ImageTk
import os
from editor_session import EditSession
from editor_theme import apply_dark
from area_ui import AreaPanel
from map_inspector import inspect_map
from map_names import map_label
from location_picker import LocationPicker,initial_map
from disc_inventory import Disc
from event_editor import script_roots,instructions,edit_instruction,EDITABLE
from map_delete_ui import delete_current_map
from map_copy_ui import new_map_copy as new_map_copy_full
from content_database import ContentDatabase,KINDS,OBJECT_REACTIONS
MOD_OPTION_TABS=("Gameplay","Controls","Speed","Sound")
MOD_OPTION_TAB_OF={'elemental_bombs':'Gameplay','boss_hp_hud':'Gameplay','magic_weapon_swap':'Controls','start_as_meia':'Gameplay',
 'lr_swaps':'Controls','confirm_square':'Controls','skip_intro':'Gameplay','open_world':'Gameplay',
 'remove_cutscenes':'Gameplay','instant_text':'Speed','fast_loading':'Speed','instant_boot':'Speed',
 'more_sound_room':'Sound','regular_item_sounds':'Sound'}
MOD_OPTION_DEFAULTS={'more_sound_room':True}   # Expand Sound Space: on by default (user 2026-10-23)
ROOT=Path(__file__).resolve().parents[1]

def build_percent(text):
 """Percent done for a build progress message (the build's steps, in order)."""
 import re
 m=re.search(r'Writing changed sectors (\d+)/(\d+)',text)
 if m:return 55+int(30*int(m.group(1))/max(1,int(m.group(2))))
 for key,value in (('Waiting',2),('Compiling map events',5),('Checking original disc',20),('Updating',55),('Extracting',30),('Building the edited game',55),('Verifying',90)):
  if text.startswith(key):return value
 return None

def _shift_colour(image,hue,sat):
 """Hue +hue degrees, saturation x sat% on visible pixels (the per-pixel colorsys rule, on arrays)."""
 import numpy as np
 a=np.asarray(image,dtype=np.float64)/255;r,g,b,al=a[...,0],a[...,1],a[...,2],a[...,3]
 v=a[...,:3].max(-1);mn=a[...,:3].min(-1);d=v-mn
 s=np.where(v>0,d/np.where(v>0,v,1),0);dd=np.where(d>0,d,1)
 h=np.where(v==r,(g-b)/dd,np.where(v==g,2+(b-r)/dd,4+(r-g)/dd));h=np.where(d>0,(h/6)%1,0)
 h=(h+hue/360)%1;s=np.minimum(1,s*sat/100)
 i=np.floor(h*6);f=h*6-i;p=v*(1-s);q=v*(1-s*f);u=v*(1-s*(1-f));i=i.astype(int)%6
 out=np.stack([np.choose(i,[v,q,p,p,u,v]),np.choose(i,[u,v,v,q,p,p]),np.choose(i,[p,p,u,v,v,q])],-1)
 rgb=np.where((al>0)[...,None],np.round(out*255),np.asarray(image)[...,:3])
 return Image.fromarray(np.dstack([rgb,np.asarray(image)[...,3]]).astype(np.uint8),'RGBA')

class Editor:
 def __init__(self,root):
  self.root=root;self.session=None;self.texture_raw=None;self.dirty=False;self.color=1
  # Any error inside a window or button goes to the status line, never a pop-up.
  root.report_callback_exception=lambda kind,value,trace:self.report_problem(value)
  root.title("Alundra Maker")   # the project name follows (see update_title)
  screen_width,screen_height=root.winfo_screenwidth(),root.winfo_screenheight()
  width,height=round(screen_width*0.85),round(screen_height*0.85)
  root.geometry(f"{width}x{height}+{(screen_width-width)//2}+0")
  apply_dark(root)
  self.status=tk.StringVar(value="Open your DATAS.BIN or original disc BIN to begin.")
  bar=ttk.Frame(root,padding=8);bar.pack(fill="x");self.options_bar=bar
  # Save mode (2026-10-08, testing): 'on_build' keeps every edit in the editor
  # (shown on the map and in events) and writes the mod project only when you
  # Build game / Build & test. 'manual' is the old mode: the Save mod button.
  self.build_fingerprint=None
  for label,command in [("Save mod",self.save_mod_project),("Build game",self.build_modded_game),("Build & test",self.build_and_test),("Database",self.open_content_database)]:
   button=ttk.Button(bar,text=label,command=lambda c=command:self.guard(c));button.pack(side="left",padx=3)
   if label=="Save mod":self.toolbar_save_button=button
  # Ctrl+S saves the project under its current name, Ctrl+B builds, Ctrl+P builds and tests
  for keys,command in (('s',self.save_mod_project),('b',self.build_modded_game),('p',self.build_and_test)):
   for key in (keys,keys.upper()):
    root.bind_all(f'<Control-{key}>',lambda _e,c=command:(self.guard(c),'break')[1])
  from history_icons import circular_arrow
  self.history_icons=[ImageTk.PhotoImage(circular_arrow(clockwise),master=root) for clockwise in (False,True)]
  for icon,command,name in zip(self.history_icons,(self.undo,self.redo),('Undo','Redo')):
   button=ttk.Button(bar,image=icon,command=lambda c=command:self.guard(c),width=3);button.pack(side='left',padx=3)
   setattr(self,'toolbar_'+name.lower()+'_button',button)
  self.map_id=tk.StringVar(value=str(initial_map()))
  self.map_load_job=None
  self.map_id.trace_add("write",self.schedule_map_load)
  ttk.Label(bar,text="Map").pack(side="left",padx=5)
  ttk.Spinbox(bar,from_=0,to=2546,textvariable=self.map_id,width=5).pack(side="left")
  self.location_name=tk.StringVar(value="")
  ttk.Label(bar,textvariable=self.location_name,font=("Segoe UI",10,"bold")).pack(side="left",padx=(10,8))
  ttk.Button(bar,text="Choose Map",command=lambda:self.guard(self.choose_location)).pack(side="left",padx=3)
  self.build_running=False
  status_bar=ttk.Frame(root);status_bar.pack(side="bottom",fill="x")
  self.preload_status=tk.StringVar(value="")   # background loading progress
  ttk.Label(status_bar,textvariable=self.preload_status,padding=(10,5),anchor="e").pack(side="right")
  self.status_label=ttk.Label(status_bar,textvariable=self.status,padding=(10,5),anchor="w");self.status_label.pack(side="left",fill="x",expand=True)
  ttk.Style(root).configure("Build.Horizontal.TProgressbar",troughcolor="#151a22",background="#5b9bd5",bordercolor="#394354",lightcolor="#5b9bd5",darkcolor="#5b9bd5")
  self.build_bar=ttk.Progressbar(status_bar,mode="determinate",maximum=100,length=220,style="Build.Horizontal.TProgressbar")
  self.build_percent=tk.StringVar(value="")
  self.build_percent_label=ttk.Label(status_bar,textvariable=self.build_percent,width=5,anchor="e")
  # Loading game into memory: a bar on the right of the status bar (the start-up
  # load, then the background preload), hidden when nothing loads.
  self.memory_bar=ttk.Progressbar(status_bar,mode="determinate",maximum=100,length=200,style="Build.Horizontal.TProgressbar")
  self.memory_bar_status_bar=status_bar;self.memory_bar_shown=False
  ttk.Style(root).layout("Workspace.TNotebook",[("Notebook.client",{"sticky":"nswe"})])
  tabs=ttk.Notebook(root,style="Workspace.TNotebook") # Legacy editors are detached from the main screen.
  tex=ttk.Frame(tabs);tabs.add(tex,text="Textures")
  controls=ttk.Frame(tex);controls.pack(fill="x")
  self.sheet=tk.StringVar(value="0");self.palette_id=tk.StringVar(value="0")
  for label,var,maximum in [("Sheet",self.sheet,5),("Palette",self.palette_id,31)]:
   ttk.Label(controls,text=label).pack(side="left",padx=4)
   ttk.Spinbox(controls,from_=0,to=maximum,textvariable=var,width=5,command=lambda:self.guard(self.draw)).pack(side="left")
  for label,command in [("Refresh",self.draw),("Apply pixels",self.apply_pixels),("Export PNG",self.export_png),("Import PNG",self.import_png),("Change selected colour",self.change_color)]:
   ttk.Button(controls,text=label,command=lambda c=command:self.guard(c)).pack(side="left",padx=3)
  body=ttk.Frame(tex);body.pack(fill="both",expand=True)
  self.canvas=tk.Canvas(body,width=512,height=512,background="#30343b",highlightthickness=0)
  self.canvas.pack(side="left",anchor="nw",padx=12,pady=12)
  self.canvas.bind("<Button-1>",self.paint);self.canvas.bind("<B1-Motion>",self.paint)
  side=ttk.Frame(body,padding=12);side.pack(side="left",fill="both",expand=True)
  ttk.Label(side,text="Paint with a palette colour",font=("Segoe UI",12,"bold")).pack(anchor="w")
  swatches=ttk.Frame(side);swatches.pack(anchor="w",pady=10)
  self.swatches=[]
  for i in range(16):
   button=tk.Button(swatches,text=str(i),width=5,command=lambda n=i:self.choose(n))
   button.grid(row=i//4,column=i%4,padx=2,pady=2);self.swatches.append(button)
  ttk.Label(side,text="Click or drag to paint pixels. Apply pixels commits a stroke batch.\n\nPNG import matches colours to the selected 16-colour palette. Exported indexed PNGs retain pixel indices.\n\nA palette is shared by multiple tiles. Changing a colour may affect other parts of the map.\n\nTextures must fit their original compressed space; oversized changes are rejected.\n\nEntity identities and full AI behaviour are not decoded. Use a copy for testing.",wraplength=480,justify="left").pack(anchor="w",pady=15)
  self.record_views={}
  self.record_panel(tabs,"entities","Entities / enemies",
   ["Area left","Area top","Area right","Area bottom","Enabled (raw)","Direction (raw)","Sprite index","Position X (raw)","Position Y (raw)","Height (raw)","A load program","B map program","C tick program","D touch program","E deactivate program","F interact program","Unknown word","Contents (raw)"])
  self.record_panel(tabs,"events","Map events",
   ["Area left","Area top","Area right","Area bottom","B program index","Reserved 1","Reserved 2","Reserved 3"])
  script_frame=ttk.Frame(tabs);tabs.add(script_frame,text="Event scripts");self.script_frame=script_frame;self.tabs=tabs
  self.script_key=tk.StringVar()
  self.script_combo=ttk.Combobox(script_frame,textvariable=self.script_key,state="readonly",width=25)
  self.script_combo.pack(anchor="w",padx=8,pady=8)
  self.script_combo.bind("<<ComboboxSelected>>",lambda e:self.guard(self.load_script))
  self.script_tree=ttk.Treeview(script_frame,columns=("offset","command","operands"),show="headings",height=15)
  for key,width in [("offset",150),("command",300),("operands",500)]:
   self.script_tree.heading(key,text=key.title());self.script_tree.column(key,width=width)
  self.script_tree.pack(fill="both",expand=True,padx=8)
  self.script_tree.bind("<<TreeviewSelect>>",lambda e:self.guard(self.select_instruction))
  self.operand_frame=ttk.Frame(script_frame,padding=8);self.operand_frame.pack(fill="x")
  self.operand_vars=[]
  animation_frame=ttk.Frame(tabs);tabs.add(animation_frame,text="Animations")
  animation_body=ttk.Panedwindow(animation_frame,orient="horizontal");animation_body.pack(fill="both",expand=True,padx=10,pady=8)
  animation_left=ttk.Frame(animation_body);animation_body.add(animation_left,weight=1)
  animation_right=ttk.Frame(animation_body,padding=10);animation_body.add(animation_right,weight=2)
  ttk.Label(animation_left,text="Content definition").pack(anchor="w")
  self.animation_definition=tk.StringVar()
  self.animation_definition_combo=ttk.Combobox(animation_left,textvariable=self.animation_definition,state="readonly")
  self.animation_definition_combo.pack(fill="x",pady=(2,8));self.animation_definition_combo.bind("<<ComboboxSelected>>",lambda e:self.animation_refresh())
  ttk.Label(animation_left,text="Animation sequences").pack(anchor="w")
  self.animation_tree=ttk.Treeview(animation_left,columns=("speed","frames"),show="tree headings",height=16)
  for col,label,width in [("#0","Name",150),("speed","Ticks / frame",100),("frames","Frame order",240)]:
   self.animation_tree.heading(col,text=label);self.animation_tree.column(col,width=width)
  self.animation_tree.pack(fill="both",expand=True);self.animation_tree.bind("<<TreeviewSelect>>",lambda e:self.animation_select())
  animation_toolbar=ttk.Frame(animation_left);animation_toolbar.pack(fill="x",pady=6)
  for label,command in [("Add",self.animation_add),("Delete",self.animation_delete)]:
   ttk.Button(animation_toolbar,text=label,command=lambda c=command:self.guard(c)).pack(side="left",padx=(0,5))
  ttk.Label(animation_right,text="Animation settings",font=("Segoe UI",13,"bold")).pack(anchor="w")
  settings=ttk.Frame(animation_right);settings.pack(fill="x",pady=8)
  ttk.Label(settings,text="Name").grid(row=0,column=0,sticky="w")
  self.animation_name=tk.StringVar();ttk.Entry(settings,textvariable=self.animation_name,width=20).grid(row=0,column=1,sticky="w",padx=6)
  ttk.Label(settings,text="Ticks per frame").grid(row=0,column=2,sticky="w",padx=(18,0))
  self.animation_speed=tk.StringVar(value="8")
  ttk.Spinbox(settings,from_=1,to=255,textvariable=self.animation_speed,width=6).grid(row=0,column=3,sticky="w",padx=6)
  ttk.Label(animation_right,text="Frames play from top to bottom. Select a frame to change its ID, or add, remove and reorder frames. Lower ticks/frame is faster. Apply before switching sequences.").pack(anchor="w",pady=(4,6))
  frame_controls=ttk.Frame(animation_right);frame_controls.pack(fill="x")
  self.animation_frames_tree=ttk.Treeview(animation_right,columns=("frame_id",),show="headings",height=14,selectmode="browse")
  self.animation_frames_tree.heading("frame_id",text="Frame ID");self.animation_frames_tree.column("frame_id",width=100,anchor="center")
  self.animation_frames_tree.pack(fill="both",expand=True)
  self.animation_frames_tree.bind("<<TreeviewSelect>>",lambda e:self.animation_frame_select())
  ttk.Label(frame_controls,text="Frame ID").pack(side="left")
  self.animation_frame_id=tk.StringVar(value="0")
  ttk.Spinbox(frame_controls,from_=0,to=255,textvariable=self.animation_frame_id,width=6).pack(side="left",padx=5)
  for label,command in [("Set selected",self.animation_frame_set),("Add frame",self.animation_frame_add),("Remove",self.animation_frame_remove),("Move up",lambda:self.animation_frame_move(-1)),("Move down",lambda:self.animation_frame_move(1))]:
   ttk.Button(frame_controls,text=label,command=lambda c=command:self.guard(c)).pack(side="left",padx=3)
  ttk.Button(animation_right,text="Apply animation",command=lambda:self.guard(self.animation_apply)).pack(anchor="w",pady=8)
  native_animation_frame=ttk.Frame(tabs);tabs.add(native_animation_frame,text="Map animations")
  native_toolbar=ttk.Frame(native_animation_frame,padding=8);native_toolbar.pack(fill="x")
  ttk.Button(native_toolbar,text="Load selected map character",command=lambda:self.guard(self.native_animation_load)).pack(side="left",padx=3)
  self.native_animation_location=tk.StringVar(value="Select a character on the Entities / enemies tab")
  ttk.Label(native_toolbar,textvariable=self.native_animation_location,font=("Segoe UI",10,"bold")).pack(side="left",padx=10)
  native_controls=ttk.Frame(native_animation_frame,padding=(8,0,8,6));native_controls.pack(fill="x")
  ttk.Label(native_controls,text="Animation set").pack(side="left")
  self.native_animation_set=tk.StringVar()
  self.native_animation_set_combo=ttk.Combobox(native_controls,textvariable=self.native_animation_set,state="readonly",width=6)
  self.native_animation_set_combo.pack(side="left",padx=5);self.native_animation_set_combo.bind("<<ComboboxSelected>>",lambda e:self.native_animation_refresh())
  ttk.Label(native_controls,text="Direction slot").pack(side="left",padx=(12,0))
  self.native_animation_slot=tk.StringVar()
  self.native_animation_slot_combo=ttk.Combobox(native_controls,textvariable=self.native_animation_slot,values=("0","1","2","3"),state="readonly",width=5)
  self.native_animation_slot_combo.pack(side="left",padx=5);self.native_animation_slot_combo.bind("<<ComboboxSelected>>",lambda e:self.native_animation_refresh())
  ttk.Label(native_controls,text="Movement speed (raw 16-bit)").pack(side="left",padx=(18,2))
  self.native_animation_speed=tk.StringVar(value="0")
  ttk.Spinbox(native_controls,from_=0,to=65535,textvariable=self.native_animation_speed,width=8).pack(side="left",padx=5)
  self.native_animation_tree=ttk.Treeview(native_animation_frame,columns=("delay","collision","image_set"),show="tree headings",height=14)
  for column,label,width in [("#0","Frame",70),("delay","Delay / flag (raw)",150),("collision","Collision ref (raw)",170),("image_set","Frame image-set ID",180)]:
   self.native_animation_tree.heading(column,text=label);self.native_animation_tree.column(column,width=width)
  self.native_animation_tree.pack(fill="both",expand=True,padx=8,pady=(0,8));self.native_animation_tree.bind("<<TreeviewSelect>>",lambda e:self.native_animation_frame_select())
  native_frame_controls=ttk.Frame(native_animation_frame,padding=8);native_frame_controls.pack(fill="x")
  ttk.Label(native_frame_controls,text="Raw delay/flag").pack(side="left")
  self.native_frame_delay=tk.StringVar(value="128")
  ttk.Spinbox(native_frame_controls,from_=128,to=255,textvariable=self.native_frame_delay,width=7).pack(side="left",padx=5)
  ttk.Label(native_frame_controls,text="Existing image-set ID").pack(side="left",padx=(12,2))
  self.native_frame_image_set=tk.StringVar()
  self.native_frame_image_set_combo=ttk.Combobox(native_frame_controls,textvariable=self.native_frame_image_set,state="readonly",width=12)
  self.native_frame_image_set_combo.pack(side="left",padx=5)
  for label,command in [("Set frame fields",self.native_animation_set_frame),("Move up",lambda:self.native_animation_move(-1)),("Move down",lambda:self.native_animation_move(1))]:
   ttk.Button(native_frame_controls,text=label,command=lambda c=command:self.guard(c)).pack(side="left",padx=3)
  ttk.Button(native_animation_frame,text="Apply to this map's DATAS",command=lambda:self.guard(self.native_animation_apply)).pack(anchor="w",padx=12,pady=(2,6))
  self.database=ContentDatabase();self.database.populate_catalogue()
  import weakref,content_database as _cdb
  _ref=weakref.WeakMethod(self.class_definition_changed)
  def _listener(db,definition_id,_ref=_ref):
   method=_ref()
   if method is None:_cdb.DEFINITION_LISTENERS.remove(_listener)
   else:method(db,definition_id)
  _cdb.DEFINITION_LISTENERS.append(_listener)
  self.preferences_windows()
  self.db_window=None;self.db_trees={};self.db_texts={};self.db_preview_canvases={};self.db_dialogue_preview_canvases={};self.db_frames={}
  self.db_kind=tk.StringVar(value="npc");self.db_active_kind="npc"
  self.db_object_type_vars={};self.db_object_reaction_vars={};self.db_object_item=tk.StringVar(value="No item");self.db_object_item_combo=None
  self.db_instances_tree=None;self.db_instance_class=tk.StringVar();self.db_class_combo=None
  __import__('audio_preview').warm_up()   # find the music player now, not on the first Play
  self.db_refresh()
  self.area=AreaPanel(self)
  for tab in list(tabs.tabs()):
   if tabs.tab(tab,'text') in ('Textures','Entities / enemies','Map events','Event scripts','Animations','Map animations'):
    tabs.forget(tab)
  self.workspace_views={tabs.tab(tab,"text"):tab for tab in tabs.tabs()}

  self.make_menus()
  try:   # dark menu bar (Windows ignores Tk colours on the native one)
   from dark_menubar import convert;self.dark_menubar=convert(self.root,self.main_menu)
  except Exception:pass
  self.make_workspace_buttons()
  self.root.protocol("WM_DELETE_WINDOW",self.close)
  self.root.after(150,self.auto_open_workspace)

 def preferences_windows(self):
  self.preference_windows={}
  def host(label,width,height):
   window=tk.Toplevel(self.root);window.withdraw();window.title(label+' - Alundra Maker')
   window.geometry(f'{width}x{height}+60+40');window.transient(self.root)
   window.protocol('WM_DELETE_WINDOW',window.withdraw);self.preference_windows[label]=window
   frame=ttk.Frame(window,padding=18);frame.pack(fill='both',expand=True);return frame
  from editor_emulator import chosen_emulator
  from editor_preferences import load_preferences,project_build_name,selected_game_bin,save_preferences,DEFAULT_BUILD_NAME
  saved=load_preferences()
  project=host('Project',900,330)
  ttk.Label(project,text="Project and game paths",font=("Segoe UI",16,"bold")).grid(row=0,column=0,columnspan=3,sticky="w")
  ttk.Label(project,text="These settings are kept on this computer and restored the next time the editor opens.",wraplength=820).grid(row=1,column=0,columnspan=3,sticky="w",pady=(6,14))
  ttk.Label(project,text="Original game BIN").grid(row=2,column=0,sticky="w",pady=5)
  self.game_bin_path=tk.StringVar(value=str(selected_game_bin() or saved.get('game_bin_path','')))
  ttk.Entry(project,textvariable=self.game_bin_path,width=86).grid(row=2,column=1,sticky="ew",padx=8)
  ttk.Button(project,text="Browse…",command=lambda:self.guard(self.choose_game_bin)).grid(row=2,column=2)
  ttk.Label(project,text="Project build name").grid(row=3,column=0,sticky="w",pady=5)
  self.project_build_name=tk.StringVar(value=project_build_name())
  self.project_build_name.trace_add('write',lambda *_:self.update_title());self.update_title()
  ttk.Entry(project,textvariable=self.project_build_name,width=48).grid(row=3,column=1,sticky="w",padx=8)
  ttk.Label(project,text="Used automatically for the saved mod and exported BIN/CUE. Rebuilding the same name replaces the prior build.",wraplength=780).grid(row=4,column=0,columnspan=3,sticky="w",pady=(6,14))
  ttk.Button(project,text="Save project settings",command=lambda:self.guard(self.save_project_preferences)).grid(row=5,column=1,sticky="w")
  project.columnconfigure(1,weight=1)
  emulator=host('Emulator',850,280)
  ttk.Label(emulator,text="Emulator",font=("Segoe UI",16,"bold")).pack(anchor="w")
  ttk.Label(emulator,text="Choose BizHawk for Build & test. Choosing a location does not start it.").pack(anchor="w",pady=8)
  self.emulator_path=tk.StringVar(value=str(chosen_emulator() or "Not selected"))
  ttk.Entry(emulator,textvariable=self.emulator_path,state="readonly",width=90).pack(anchor="w",fill="x",pady=8)
  ttk.Button(emulator,text="Choose BizHawk…",command=lambda:self.guard(self.choose_emulator)).pack(anchor="w")
  ttk.Label(emulator,text="Build & test opens a completed game build with separate test saves. Build game exports without starting an emulator.",wraplength=800).pack(anchor="w",pady=16)
  mods=host('Mod options',850,760)
  ttk.Label(mods,text="Game options",font=("Segoe UI",16,"bold")).pack(anchor="w")
  ttk.Label(mods,text="Saved with this mod and applied when you build the game. All options are off by default.").pack(anchor="w",pady=8)
  self.mod_option_vars={}
  # Tabs by category (user 2026-10-24); keys and behaviour unchanged
  self.mod_tabs=ttk.Notebook(mods);self.mod_tabs.pack(fill="both",expand=True)
  pages={}
  for name in MOD_OPTION_TABS:
   page=ttk.Frame(self.mod_tabs,padding=8);self.mod_tabs.add(page,text=name);pages[name]=page
  for key,label,description in [
   ("skip_intro","Skip intro","New game starts in Inoa, no opening."),
   ("open_world","Open world (without dreams)","Randomizer-style open routes; dreams not included."),
   ("lr_swaps","L/R swaps","Swap equipment with the shoulder buttons."),
   ("instant_text","Instant text","Text appears at once; you still press to continue."),
   ("fast_loading","Fast loading","Shorter fades and no waiting for music or sounds when changing rooms; faster title exit."),
   ("instant_boot","Instant boot","No opening movies: power-on goes straight to the main menu. Instant boot + skips the menu too and starts the game at once."),
   ("remove_cutscenes","Remove cutscenes","Skip optional story cutscenes; story stays."),
   ("start_as_meia","Start as Meia","Play as Meia; Basic Attack adds sword, carry and throw."),
   ("confirm_square","Confirm button","Menus, Yes/No, save book, title and load menu confirm with Cross (US/EU) or Square (JP)."),
   ("elemental_bombs","Elemental bomb effects","Fire Wand and fire magic set a bomb off at once; an Ice Wand or water magic hit makes its fuse burn at half speed."),
   ("magic_weapon_swap","Magic & weapon swap","Circle in the menu picks which weapon or magic is used."),
   ("boss_hp_hud","Boss HP on the HUD","Shows the boss's hit points between the life and Gilder numbers in boss rooms."),
   # One sound setting (user 2026-10-23); it replaces "Extended map sound sets"
   ("more_sound_room","Expand Sound Space","Gives each map room for all its events sounds."),
   ("regular_item_sounds","Use regular item sounds for rare items","Rare items play the normal pickup sound instead of the fanfare.")]:
   var=tk.BooleanVar(value=MOD_OPTION_DEFAULTS.get(key,False));self.mod_option_vars[key]=var
   mods_page=pages[MOD_OPTION_TAB_OF[key]]
   if key=="instant_boot":
    row=ttk.Frame(mods_page);row.pack(anchor="w",pady=(14,2))
    ttk.Checkbutton(row,text=label,variable=var,command=lambda:self.guard(self.change_mod_options)).pack(side="left")
    plus=tk.BooleanVar(value=False);self.mod_option_vars["instant_boot_plus"]=plus
    ttk.Checkbutton(row,text="Instant boot +",variable=plus,command=lambda:self.guard(self.change_mod_options)).pack(side="left",padx=(18,0))
   elif key=="confirm_square":
    row=ttk.Frame(mods_page);row.pack(anchor="w",pady=(14,2));ttk.Label(row,text=label+":").pack(side="left")
    for value,text in ((False,"Cross (US)"),(True,"Square (JP)")):
     ttk.Radiobutton(row,text=text,variable=var,value=value,command=lambda:self.guard(self.change_mod_options)).pack(side="left",padx=(12,0))
   elif key=="start_as_meia":
    row=ttk.Frame(mods_page);row.pack(anchor="w",pady=(14,2))
    ttk.Checkbutton(row,text=label,variable=var,command=lambda:self.guard(self.change_mod_options)).pack(side="left")
    self.meia_option_buttons={}
    for sub,sub_label in (("meia_basic_attack","Meia basic attack"),("meia_alundra_fallback","Alundra for missing actions")):
     sub_var=tk.BooleanVar(value=False);self.mod_option_vars[sub]=sub_var
     button=ttk.Checkbutton(row,text=sub_label,variable=sub_var,command=lambda:self.guard(self.change_mod_options));button.pack(side="left",padx=(18,0))
     self.meia_option_buttons[sub]=button
   else:
    button=ttk.Checkbutton(mods_page,text=label,variable=var,command=lambda:self.guard(self.change_mod_options));button.pack(anchor="w",pady=(14,2))
    if key=="skip_intro":self.skip_intro_button=button
   ttk.Label(mods_page,text=description,wraplength=800).pack(anchor="w",padx=24)
  self.update_meia_option_state()
  ttk.Label(pages["Gameplay"],text="Game balance",font=("Segoe UI",12,"bold")).pack(anchor="w",pady=(18,2))
  balance_row=ttk.Frame(pages["Gameplay"]);balance_row.pack(anchor="w",padx=24)
  ttk.Button(balance_row,text="US Balance",command=lambda:self.guard(lambda:self.set_balance('us'))).pack(side="left")
  ttk.Button(balance_row,text="JP Balance",command=lambda:self.guard(lambda:self.set_balance('jp'))).pack(side="left",padx=8)
  self.balance_state=tk.StringVar();ttk.Label(balance_row,textvariable=self.balance_state).pack(side="left",padx=8)
  self.show_balance_state()
  # Size the window to everything in it (it grew with the Meia options).
  window=mods.winfo_toplevel();window.update_idletasks()
  needed=mods.winfo_reqheight()+20;limit=window.winfo_screenheight()-80
  window.geometry(f'{max(850,mods.winfo_reqwidth()+20)}x{min(needed,limit)}+60+20');window.minsize(700,400)

 def update_meia_option_state(self):
  """Meia basic attack needs Start as Meia; Alundra for missing actions needs Meia basic attack."""
  v=getattr(self,'mod_option_vars',{});buttons=getattr(self,'meia_option_buttons',{})
  if not buttons:return
  if not v['start_as_meia'].get():v['meia_basic_attack'].set(False)
  if not v['meia_basic_attack'].get():v['meia_alundra_fallback'].set(False)
  buttons['meia_basic_attack'].configure(state='normal' if v['start_as_meia'].get() else 'disabled')
  buttons['meia_alundra_fallback'].configure(state='normal' if v['meia_basic_attack'].get() else 'disabled')
  # Open world starts after the opening by itself: Skip intro is unticked and greyed out
  button=getattr(self,'skip_intro_button',None)
  if 'open_world' in v and 'skip_intro' in v:
   if v['open_world'].get():v['skip_intro'].set(False)
   if button is not None:button.configure(state='disabled' if v['open_world'].get() else 'normal')

 def change_mod_options(self):
  self.update_meia_option_state()
  previous=self.database.document.get('mod_options',{}).get('open_world',False)
  # options only change when the user ticks them (open world greys out Skip intro, user request)
  self.database.document.setdefault('mod_options',{}).update({key:var.get() for key,var in self.mod_option_vars.items()})
  self.dirty=True;self.status.set("Game options updated. Save mod to keep them; Build game applies them.")
  picker=getattr(self,'location_picker',None)
  if picker is not None and picker.window.winfo_exists():picker.refresh()
  if previous!=self.mod_option_vars['open_world'].get():self.select_initial_map()

 def select_initial_map(self):
  if not hasattr(self,'map_id'):return
  enabled=self.database.document.get('mod_options',{}).get('open_world',False)
  dirty=self.dirty
  # Open world on/off: show where a new game now starts (S start point, else the game start)
  if self.session is not None:self.go_to_start_point(fallback_map=initial_map(enabled))
  else:self.map_id.set(str(initial_map(enabled)))
  self.dirty=dirty

 def go_to_start_point(self,fallback_map=None):
  """Show the map where a new game starts with this project (your S start point,
  else the Open World / Skip intro / game start) and centre it. One map load;
  if the start cannot be worked out, fallback_map is shown instead."""
  try:
   from editor_start_point import effective_start_point
   point,label,authored=effective_start_point(self)
  except Exception:
   point=None
  if point is None:
   if fallback_map is not None:self.map_id.set(str(fallback_map));self.guard(self.load_map)
   return
  self.map_id.set(str(point['map_id']));self.guard(self.load_map)
  area=getattr(self,'area',None)
  if area is not None and self.current_map==point['map_id']:
   area.caption.set(('Your S start point' if authored else label+' (from game data)')+f": map {point['map_id']}, tile {point['x']},{point['y']}.")
   self.root.after_idle(lambda:area.center_on_start_point(point))
  elif fallback_map is not None and self.current_map!=point['map_id']:
   self.map_id.set(str(fallback_map));self.guard(self.load_map)

 def ask_import_world_mode(self):
  """New game data opened: name the project and choose the world mode in one window."""
  from editor_preferences import project_output_paths,safe_build_name,save_preferences
  win=tk.Toplevel(self.root);win.title('New project');win.transient(self.root);win.resizable(False,False)
  try:apply_dark(win)
  except Exception:pass
  body=ttk.Frame(win,padding=16);body.pack(fill='both',expand=True)
  ttk.Label(body,text='New project',font=('Segoe UI',14,'bold')).pack(anchor='w')
  # Default name: the first free "New Project N", so it never replaces a project.
  def free(stem):
   paths=project_output_paths(stem)
   return not paths['mod'].is_file() and not paths['mod'].parent.exists()
  n=1
  while not free(f'New Project {n}'):n+=1
  name=tk.StringVar(value=f'New Project {n}')
  entry=ttk.Entry(body,textvariable=name,width=44);entry.pack(anchor='w',fill='x')
  note=tk.StringVar();ttk.Label(body,textvariable=note,foreground='#e0b050',wraplength=430).pack(anchor='w',pady=(2,0))
  def check(*_):
   try:
    path=project_output_paths(safe_build_name(name.get()))['mod']
    note.set('A project with this name already exists; saving will replace it.' if path.is_file() else '')
   except Exception as exc:note.set(str(exc))
  name.trace_add('write',check);check()
  open_world=tk.BooleanVar(value=bool(self.database.document.get('mod_options',{}).get('open_world')))
  ttk.Checkbutton(body,text='Open world (without dreams)',variable=open_world).pack(anchor='w',pady=(12,2))
  ttk.Label(body,text='Open world like the randomizer.',wraplength=430,foreground='#8c99ab').pack(anchor='w',padx=(22,0))
  buttons=ttk.Frame(body);buttons.pack(fill='x',pady=(14,0))
  def create():
   try:stem=safe_build_name(name.get())
   except Exception as exc:note.set(str(exc));return
   options=self.database.document.setdefault('mod_options',{})
   options['open_world']=open_world.get()
   if open_world.get():options['skip_intro']=False   # open world skips the opening itself (Skip intro greyed out)
   if hasattr(self,'mod_option_vars'):
    for key,var in self.mod_option_vars.items():var.set(options.get(key,MOD_OPTION_DEFAULTS.get(key,False)))
    self.update_meia_option_state()
   if hasattr(self,'project_build_name'):self.project_build_name.set(stem)
   save_preferences({'project_build_name':stem,'last_mod_path':str(project_output_paths(stem)['mod'].resolve())})
   self.dirty=True;win.destroy()
   self.db_refresh();self.go_to_start_point(fallback_map=initial_map(open_world.get()))
   self.status.set(f'New project "{stem}"'+(' (open world)' if open_world.get() else '')+'. Save mod or Build to write it.')
  def cancel():
   win.destroy();self.db_refresh();self.go_to_start_point(fallback_map=initial_map(False))
  ttk.Button(buttons,text='Create project',command=lambda:self.guard(create)).pack(side='right')
  ttk.Button(buttons,text='Cancel',command=cancel).pack(side='right',padx=6)
  win.protocol('WM_DELETE_WINDOW',cancel);win.bind('<Return>',lambda _:self.guard(create))
  entry.focus_set();entry.select_range(0,'end')
  try:win.grab_set()
  except Exception:pass
  self.new_project_window=win

 def auto_open_workspace(self):
  if self.session is not None:return
  path=ROOT/"game/disc/DATA/DATAS.BIN"
  if not path.is_file():
   self.status.set("Choose Open to load your game data.");return
  try:
   self.session=EditSession.open_data(path.read_bytes(),path);self.dirty=False
   # Reopen the project you worked on last (saved by Save mod or by Build),
   # so placed events and their settings are still there after a restart.
   # The game is read once: the project is opened straight away, and the
   # plain game database and map are only built when there is no project.
   from editor_preferences import load_preferences,project_output_paths
   last=load_preferences().get('last_mod_path')
   candidates=[Path(last)] if last else []
   candidates.append(project_output_paths()['mod'])
   mod=next((p for p in candidates if p.is_file()),None)
   if mod is not None:
    try:
     self.load_mod_path(mod)
     self.status.set(f'Reopened your mod: {mod.stem}');return
    except Exception as exc:
     self.report_problem(f'Could not reopen {mod.stem}: {exc}')
   self.populate_database_from_game();self.db_refresh()
   self.guard(self.load_map)
  except Exception as exc:
   self.session=None;self.status.set(f"Automatic data load failed: {exc}. Use Open to choose game data.")

 def open_balance(self):
  from enemy_definition import BalanceSession,BALANCE_SHA256
  if not hasattr(self.session,"extra_files"):self.session.extra_files={}
  if "DATA/BALANCE.BIN" not in self.session.extra_files:
   if self.session.source_verified:data=(ROOT/"game/disc/DATA/BALANCE.BIN").read_bytes()
   elif self.session.path and self.session.path.suffix.lower()==".bin":data=read_datas(self.session.path,"DATA/BALANCE.BIN")
   else:raise ValueError("Open the modded disc BIN, not DATAS.BIN alone, to edit its matching balance table.")
   self.session.extra_files["DATA/BALANCE.BIN"]=BalanceSession(data,verify=hashlib.sha256(data).hexdigest()==BALANCE_SHA256)
  from balance_ui import BalanceWindow
  BalanceWindow(self)

 def open_sprite_palette(self):
  self.need()
  from sprite_palette_ui import SpritePaletteWindow
  SpritePaletteWindow(self)

 def make_menus(self):
  menu=tk.Menu(self.root,tearoff=False);self.root.configure(menu=menu);self.main_menu=menu
  def group(label,items):
   child=tk.Menu(menu,tearoff=False)
   for title,action in items:
    if title is None:child.add_separator()
    else:child.add_command(label=title,command=action)
   menu.add_cascade(label=label,menu=child);return child
  def run(action):return lambda:self.guard(action)
  group("File",[("New mod...",run(self.new_mod_project)),("Open ROM...",run(self.open_rom)),("Open game data...",run(self.open)),("Open mod...",run(self.open_mod_project)),("Save mod",run(self.save_mod_project)),("Save mod as...",run(self.save_mod_project_as)),(None,None),("Save DATAS copy...",run(self.save)),("Exit",self.close)])
  group("Edit",[("Undo",run(self.undo)),("Redo",run(self.redo)),(None,None),("Copy",run(self.edit_copy)),("Paste",run(self.edit_paste))])
  group("Map",[("New map...",run(self.new_map)),("New map: copy of another map...",run(lambda:new_map_copy_full(self))),("Copy area from another map...",run(self.copy_area)),("Rename map...",run(self.rename_map)),("Clear current map",run(self.clear_current_map)),(None,None),("Delete this map...",run(lambda:delete_current_map(self)))])
  mods=group("Mods",[("New mod...",run(self.new_mod_project)),("Open mod...",run(self.open_mod_project)),("Save mod",run(self.save_mod_project)),("Build modded game...",run(self.build_modded_game)),("Build & test in BizHawk...",run(self.build_and_test)),("Choose emulator...",run(self.choose_emulator))])
  view=group("View",[])
  view.add_checkbutton(label="Tile grid",variable=self.area.show_grid,command=run(self.area.refresh))
  view.add_checkbutton(label="Event Numbers",variable=self.area.show_event_numbers,command=run(self.area.draw_records))
 def new_map(self):
  """New blank map in the next of the 17 new slots (483-499); when they are all used,
  ask which existing map to save over. Then ask for a map to take tiles from."""
  self.need()
  from map_create import create_map,SlotsFull,blank_existing_map
  previous=self.current_map
  def opened(m,text):
   self.dirty=True;self.populate_database_from_game()
   from tkinter import simpledialog
   name=simpledialog.askstring('Name The New Map',f'Name for map {m}:',initialvalue=map_label(m).rsplit(' (Map ',1)[0],parent=self.root)
   if name:self.set_map_name(m,name)
   self.map_id.set(str(m));self.load_map()
   if previous is not None and previous!=m:self.area.add_tile_source(previous)   # the map you were on is a tile source too
   self.status.set(f'{text}: blank, height 1, no characters, events or warps. Choose a map to take tiles from.')
   self.area.add_map_tiles()
  try:m,label=create_map(self.session,self.database.document)
  except SlotsFull:
   from new_map_ui import OverwriteMapDialog
   from map_create import create_expanded_map
   def over(m):
    self.guard(lambda:opened(*blank_existing_map(self.session,self.database.document,m)[:1],f'New map saved over map {m}'))
   def expand():
    def make():
     m,label=create_expanded_map(self.session,self.database.document)
     opened(m,f'Maps expanded: {label} (map {m}) created')
    self.guard(make)
   OverwriteMapDialog(self,over,expand);return
  opened(m,f'{label} (map {m}) created')
 def new_map_copy(self):
  """New map that copies another map's tiles, walls and heights (its
  characters, events and warps are left out; add your own)."""
  self.need()
  from location_picker import LocationPicker
  def make(source):
   from map_create import create_copy_of_map,record_edits,apply_edits
   with self.session.group(f'New map copied from map {source}'):
    m=create_copy_of_map(self.session,self.database.document,source)
    edits=record_edits(self.session,m)
    if edits:apply_edits(self.session,edits,f'New map {m}: leave out copied characters/events/warps')
   self.set_map_name(m,f'{map_label(source).rsplit(" (Map ",1)[0]} (copy)')
   self.dirty=True;self.populate_database_from_game()
   self.map_id.set(str(m));self.load_map()
   self.status.set(f'Map {m} is a copy of map {source}: same tiles and heights, no characters, events or warps.')
  LocationPicker(self,on_choose=lambda m:self.guard(lambda:make(m)),title="New Map: Copy Which Map?",button="Copy this map")
 def copy_area(self):
  self.need()
  from area_copy_ui import CopyAreaDialog
  CopyAreaDialog(self,self.root)
 def rename_map(self,map_id=None):
  """Name or rename a map (saved with the mod; empty restores its own name)."""
  self.need()
  m=self.current_map if map_id is None else map_id
  if m is None:raise ValueError('Open a map first')
  from tkinter import simpledialog
  current=self.database.document.get('map_names',{}).get(str(m)) or map_label(m).rsplit(' (Map ',1)[0]
  name=simpledialog.askstring('Rename Map',f'Name for map {m} (leave empty for its original name):',initialvalue=current,parent=self.root)
  if name is None:return
  self.set_map_name(m,name)
 def set_map_name(self,m,name):
  names=self.database.document.setdefault('map_names',{});name=name.strip()
  if name:names[str(m)]=name[:60]
  else:names.pop(str(m),None)
  from map_names import set_custom_names
  set_custom_names(names);self.dirty=True
  if m==self.current_map:self.location_name.set(map_label(m).rsplit(" (Map ",1)[0])
  picker=getattr(self,'location_picker',None)
  if picker is not None and picker.window.winfo_exists():picker.refresh()
  self.status.set(f'Map {m} is now called {map_label(m).rsplit(" (Map ",1)[0]}.')
 def clear_current_map(self):
  self.need()
  if self.current_map is None:raise ValueError('Open a map first')
  from map_create import clear_map_tiles
  clear_map_tiles(self.session,self.current_map);self.dirty=True
  self.area.refresh(reload_textures=False);self.status.set(f'Map {self.current_map} cleared: empty tiles at height 1.')
 def new_warp(self,source_tile=None):
  """Create a warp like the game's own: pick its tile here (or use source_tile), then where it leads."""
  self.need()
  if self.current_map is None:raise ValueError('Open a map first')
  from map_tile_picker import MapTileDialog
  from warp_editor import add_warp,WarpWindow,free_warp_slot,warps
  source_map=self.current_map;free_warp_slot(self.session,source_map)
  start=getattr(self.area,'selected',None) or (0,0)
  def destination(source):
   def create(map_id,x,y,z):
    if self.session is None or self.current_map!=source_map:raise ValueError('The map changed; start the new warp again')
    from warp_editor import add_two_way_warp,guess_door_facing,ask_door_directions
    here=guess_door_facing(self.session,source_map,*source);there=guess_door_facing(self.session,map_id,x,y)
    way_back=True   # Return warp is always offered (user 2026-10-25)
    picked=ask_door_directions(self.root,here,there,way_back=way_back and (map_id,x,y)!=(source_map,*source))
    if picked is None:return
    index,back=add_two_way_warp(self.session,source_map,source[0],source[1],map_id,x,y,picked[0],picked[1],way_back=picked[2])
    self.dirty=True;self.area.show_warps.set(True);self.area.refresh(reload_textures=False);self.area.mode.set('Warps')
    self.area.selected_record=('warps',index);self.area.highlight_record()
    self.area.center_on_start_point({'map_id':source_map,'x':source[0],'y':source[1],'z':0})
    self.status.set(f'New warp {index} on map {source_map} at tile {source[0]}, {source[1]}'+(f', and a way back on map {map_id} (warp {back}).' if back is not None else '.'))
    # one window only (user 2026-10-26): the warp opens with a double-click when you want to edit it
   return lambda map_id,x,y,z:self.guard(lambda:create(map_id,x,y,z))
  def chosen_source(_map_id,x,y,_z):
   self.guard(lambda:MapTileDialog(self,self.root,destination((x,y)),map_id=source_map,title='New Warp: Choose Where It Leads',confirm='Create Warp'))
  if source_tile is not None:chosen_source(source_map,source_tile[0],source_tile[1],None);return
  MapTileDialog(self,self.root,chosen_source,map_id=source_map,x=start[0],y=start[1],title='New Warp: Choose Its Tile On This Map',fixed_map=True,confirm='Next')
 def edit_copy(self):
  """Copy text in a focused box, otherwise the selected map event."""
  focus=self.root.focus_get()
  if focus is not None and focus.winfo_class() in ('TEntry','Entry','Text','TSpinbox','TCombobox'):focus.event_generate('<<Copy>>');return
  self.area.copy_selected_event()
 def edit_paste(self):
  """Paste into a focused box, otherwise paste the copied event at the selected tile."""
  focus=self.root.focus_get()
  if focus is not None and focus.winfo_class() in ('TEntry','Entry','Text','TSpinbox','TCombobox'):focus.event_generate('<<Paste>>');return
  self.area.paste_event_at_selected_tile()
 def make_workspace_buttons(self):
  self.workspace_buttons={}
  for label in ('Project','Emulator','Mod options'):
   button=ttk.Button(self.options_bar,text=label,command=lambda name=label:self.open_preferences(name))
   button.pack(side='left',padx=3);self.workspace_buttons[label]=button


 def open_preferences(self,label):
  window=self.preference_windows[label];window.deiconify();window.lift();window.focus_set()

 def guard(self,command):
  try:
   if self.session is None and command not in (self.open,self.choose_emulator):
    self.open()
    if self.session is None:return
   command()
  except IndexError as exc:
   if 'out of range' not in str(exc):return self.report_problem(exc)
   self.recover_map_view()   # a stale map position: clear it and carry on with the next click
  except Exception as exc:self.report_problem(exc)
 def recover_map_view(self):
  """Reload the map view from the game data (its positions were out of date)."""
  area=getattr(self,'area',None)
  if area is None:return
  area.drag_point=None;area.record_drag=None;area.stroke_cells=set();area.bush_stroke=None
  try:area.refresh(reload_textures=False,keep_view=True)
  except Exception:
   # waiting edits that no longer fit are dropped, then the map is read again
   area.pending_tiles={};area.pending_heights={};area.pending_stack_grid=None;area.pending_stack_tiles=set()
   try:area.refresh(reload_textures=False,keep_view=True)
   except Exception as exc:return self.report_problem(exc)
  self.status.set('Map view refreshed. Carry on.')
 def update_title(self):
  """Window title: Alundra Maker - <project name>."""
  name=self.project_build_name.get().strip() if hasattr(self,'project_build_name') else ''
  try:self.root.title(f"Alundra Maker - {name}" if name else "Alundra Maker")
  except tk.TclError:pass
 def report_problem(self,exc):
  """Never a pop-up (they stop your work): the message goes to the status
  line and to game/editor-messages.log."""
  text=str(exc) or exc.__class__.__name__
  try:self.status.set('Not done: '+text)
  except Exception:pass
  try:
   import datetime
   log=ROOT/'game'/'editor-messages.log';log.parent.mkdir(parents=True,exist_ok=True)
   import traceback,sys
   trace=''.join(traceback.format_exception(*sys.exc_info())) if sys.exc_info()[0] else ''   # where a program error happened
   with log.open('a',encoding='utf-8') as stream:stream.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {text}\n"+trace)
  except Exception:pass
 def need(self):
  if self.session is None:raise ValueError("Open game data first")
 def discard_paint(self):
  # Painting is kept on map swap: pending pixels/tiles are committed silently (no prompt).
  # (waiting imported tile pictures stay waiting: they are written at save /
  # build, so changing maps does not cut a map's redo steps)
  area=getattr(self,'area',None)
  if getattr(area,'has_pending_edits',getattr(area,'has_pending',lambda:False))():
   with self.session.group('Map edits'):area.commit_pending()   # one undo step
  if getattr(self,'paint_pending',False) and self.session is not None and self.texture_raw is not None and getattr(self,'current_map',None) is not None:
   self.session.set_texture(self.current_map,bytes(self.texture_raw))
  self.paint_pending=False
  return True
 def kill_audio(self):
  try:__import__('audio_preview').stop(self)
  except Exception:pass
 def close(self):
  if getattr(self,'memory_loading',False):self.status.set('Loading game into memory — please wait for the progress window.');return
  if self.build_running:self.status.set("Wait for the game export to finish before closing.");return
  self.db_autosave();self.lock_in_closed_events()
  if self.session and not self.dirty and self.build_fingerprint is not None and self.edit_fingerprint()==self.build_fingerprint:
   self.kill_audio();self.root.destroy();return   # everything was saved by the last build
  question="Close without saving? Changes since the last save or build are lost."
  if (self.dirty or (self.session and (self.session.undo_stack or any(x.undo_stack for x in getattr(self.session,"extra_files",{}).values())))) and not messagebox.askyesno("Close editor",question,parent=self.root):return
  self.kill_audio();self.root.destroy()
 def open_rom(self):
  """Pick the original game .bin, extract the base data from it into
  game/disc and remember it as the ROM used for builds."""
  from editor_preferences import load_preferences,save_preferences
  from mod_export import read_datas
  saved=load_preferences().get('game_bin_path');start=Path(saved).expanduser().parent if saved and Path(saved).expanduser().parent.is_dir() else ROOT
  path=filedialog.askopenfilename(initialdir=start,title="Open ROM (Alundra disc .bin)",filetypes=[("Disc image","*.bin *.BIN"),("All files","*")])
  if not path:return
  if self.session and (self.dirty or self.session.undo_stack or any(x.undo_stack for x in getattr(self.session,"extra_files",{}).values())) and not messagebox.askyesno("Open ROM","Discard this editing session?",parent=self.root):return
  source=Path(path).resolve()
  try:
   files={name:read_datas(source,name) for name in ("DATA/DATAS.BIN","ALUN_CD.EXE","DATA/BALANCE.BIN")}
   # every other file of the disc too (item text, sounds, executables...), so nothing is missing;
   # the XA / movie streams are left out (raw sectors the editor does not read)
   disc_image=Disc(source)
   try:
    _,rows=disc_image.inventory()
    for r in rows:
     name=r["path"].upper()
     if name not in files and not name.endswith((".XA",".MOV")) and not r.get("directory"):
      files[name]=disc_image.read(r["lba"],r["size"])
   finally:disc_image.handle.close()
  except Exception as error:
   messagebox.showerror("Open ROM",f"This doesn't look like an Alundra disc image:\n{error}",parent=self.root);return
  disc=ROOT/"game/disc"
  for name,data in files.items():
   target=disc/name;target.parent.mkdir(parents=True,exist_ok=True)
   if not target.is_file() or target.read_bytes()!=data:target.write_bytes(data)
  save_preferences({'game_bin_path':str(source)})
  if hasattr(self,'game_bin_path'):self.game_bin_path.set(str(source))
  self.session=EditSession.open_data(files["DATA/DATAS.BIN"],str(disc/"DATA/DATAS.BIN"),allow_compatible=True);self.database=ContentDatabase();self.session.content_database=self.database.to_json();self.dirty=False;self.populate_database_from_game();self.db_refresh();self.guard(self.load_map)
  self.status.set(f"ROM opened and extracted. Builds will use {source.name}.")
  self.ask_import_world_mode()
 def open(self):
  path=filedialog.askopenfilename(initialdir=ROOT/"game/disc/DATA",title="Open DATAS.BIN or raw disc BIN",filetypes=[("Game data","*.BIN *.bin"),("All files","*")])
  if not path:return
  if self.session and (self.dirty or self.session.undo_stack or any(x.undo_stack for x in getattr(self.session,"extra_files",{}).values())) and not messagebox.askyesno("Open another file","Discard this editing session?",parent=self.root):return
  with open(path,"rb") as stream:magic=stream.read(12)
  if magic==b"\0"+b"\xff"*10+b"\0":
   disc=Disc(Path(path))
   try:
    _,files=disc.inventory();entry=next(e for e in files if e["path"].upper()=="DATA/DATAS.BIN")
    data=disc.read(entry["lba"],entry["size"])
   finally:disc.handle.close()
   # the disc image is remembered for builds, so it is not asked for again
   from editor_preferences import save_preferences
   save_preferences({'game_bin_path':str(Path(path).resolve())})
   if hasattr(self,'game_bin_path'):self.game_bin_path.set(str(Path(path).resolve()))
  else:data=Path(path).read_bytes()
  self.session=EditSession.open_data(data,path,allow_compatible=True);self.database=ContentDatabase();self.session.content_database=self.database.to_json();self.dirty=False;self.populate_database_from_game();self.db_refresh();self.guard(self.load_map)
  if self.session.source_verified:self.status.set("Recognized original DATAS build loaded.")
  else:self.status.set("Compatible modified DATAS loaded. Its US 1.1 revision is not independently confirmed; edits are bound to this exact input.")
  self.ask_import_world_mode()
 def choose_location(self):
  picker=getattr(self,"location_picker",None)
  if picker is not None and picker.window.winfo_exists():
   picker.window.lift();picker.window.focus_set();return
  self.location_picker=LocationPicker(self)
 def schedule_map_load(self,*_):
  if self.map_load_job is not None:
   self.root.after_cancel(self.map_load_job);self.map_load_job=None
  if self.session is None:return
  try:m=int(self.map_id.get())
  except ValueError:return
  from map_slots import map_exists
  if self.session is not None and map_exists(self.session.data,m) and m!=getattr(self,"current_map",None):
   self.map_load_job=self.root.after(350,self.auto_load_map)
 def auto_load_map(self):
  self.map_load_job=None
  if self.session is not None:self.guard(self.load_map)
 def load_map(self,keep_view=False):
  """keep_view: the same map again (undo / redo): the view stays where it is."""
  # background loading waits while the map opens and for a second after (it made switching lag)
  self.map_loading=True
  try:self._load_map(keep_view)
  finally:self.map_loading=False;self.preload_user_active(1.0)
 def _load_map(self,keep_view=False):
  if self.map_load_job is not None:
   self.root.after_cancel(self.map_load_job);self.map_load_job=None
  self.need()
  self.preload_user_active(1.0)   # the map you open loads first
  if not self.discard_paint():return
  self.lock_in_closed_events()
  m=int(self.map_id.get());info=inspect_map(self.session.data,m)
  self.preload_prioritize_map(m)   # anything of this map still missing loads next, then the maps its doors lead to
  self.current_map=m
  self.location_name.set(map_label(m).rsplit(" (Map ",1)[0])
  self.texture_raw=bytearray(self.session.texture(m)[0]);self.dirty=False
  graphs=getattr(self,'event_graph_window',None)
  if graphs is not None and graphs.window.winfo_exists() and getattr(graphs,'list_map',None)!=m:graphs.refresh_list()
  self.sheet.set("0");self.draw()
  for kind,(tree,fields,names) in self.record_views.items():
   tree.delete(*tree.get_children())
   for i,row in enumerate(info[kind]):
    summary=("sprite "+str(self.session.data[int(row["offset"],16)+6])+" | XYZ "+str(row["position_raw"])) if kind=="entities" else ("program "+str(row["program"]))
    tree.insert("","end",iid=str(i),values=(i,summary,str(row["rectangle"])))
   for field in fields:field.set("")
  keys=list(script_roots(self.session,m))
  self.script_combo.configure(values=keys);self.script_key.set(keys[0] if keys else "")
  self.script_tree.delete(*self.script_tree.get_children())
  if keys:self.load_script()
  self.area.refresh(keep_view=bool(keep_view))
  self.status.set(f"Map {m} loaded. {len(info['entities'])} entities, {len(info['events'])} map events. Changes stay in memory until exported.")
 def palette(self):
  words,_=self.session.palette(self.current_map,int(self.palette_id.get()))
  return [((w&31)*255//31,((w>>5)&31)*255//31,((w>>10)&31)*255//31) for w in words]
 def image(self):
  self.need()
  sheet=int(self.sheet.get())
  if self.texture_raw is None or not 0<=sheet<len(self.texture_raw)//32768:raise ValueError("Sheet is outside this map's textures")
  chunk=self.texture_raw[sheet*32768:(sheet+1)*32768]
  indices=bytes(n for b in chunk for n in (b&15,b>>4))
  im=Image.frombytes("P",(256,256),indices)
  palette=self.palette();im.putpalette([v for rgb in palette for v in rgb]+[0]*720)
  return im
 def draw(self):
  im=self.image();self.photo=ImageTk.PhotoImage(im.convert("RGB").resize((512,512),Image.Resampling.NEAREST),master=self.root)
  self.canvas.delete("all");self.canvas.create_image(0,0,image=self.photo,anchor="nw")
  for i,rgb in enumerate(self.palette()):
   self.swatches[i].configure(bg="#%02x%02x%02x"%rgb,fg="white" if sum(rgb)<380 else "black",relief="sunken" if i==self.color else "raised")
 def choose(self,n):
  self.color=n
  if self.session:self.guard(self.draw)
 def paint(self,event):
  if self.texture_raw is None:return
  x,y=event.x//2,event.y//2
  if not (0<=x<256 and 0<=y<256):return
  try:
   sheet=int(self.sheet.get());o=sheet*32768+y*128+x//2
   if not 0<=o<len(self.texture_raw):return
   shift=4*(x%2);self.texture_raw[o]=(self.texture_raw[o]&~(15<<shift))|(self.color<<shift)
   self.dirty=True;self.paint_pending=True;self.draw();self.status.set("Pixels painted.")
  except Exception as exc:self.status.set(str(exc))
 def apply_pixels(self):
  self.need()
  area=getattr(self,'area',None)
  if area is not None and getattr(self.session,'_pending_textures',None):
   area.flush_textures()   # waiting imported tile pictures go into the game data before saving / building
  if getattr(self,'paint_pending',False):
   self.session.set_texture(self.current_map,bytes(self.texture_raw));self.paint_pending=False
   self.status.set("Texture applied. Undo is available; export a patch or DATAS copy to save.")
 def export_png(self):
  im=self.image()
  path=filedialog.asksaveasfilename(initialdir=ROOT/"game",defaultextension=".png",filetypes=[("PNG","*.png")])
  if path:im.save(path)
 def import_png(self):
  self.need()
  path=filedialog.askopenfilename(filetypes=[("PNG","*.png")])
  if not path:return
  with Image.open(path) as opened:
   if opened.size!=(256,256):raise ValueError("PNG must be exactly 256 x 256 pixels")
   image=opened.copy()
  reference=self.image()
  if image.mode=="P" and image.getpalette()==reference.getpalette() and max(image.tobytes())<16:
   indices=image.tobytes()
  else:
   palette=self.palette();pixels=image.convert("RGB").getdata();cache={}
   def closest(c):
    if c not in cache:cache[c]=min(range(16),key=lambda n:sum((c[k]-palette[n][k])**2 for k in range(3)))
    return cache[c]
   indices=bytes(closest(c) for c in pixels)
  packed=bytes(indices[i]|(indices[i+1]<<4) for i in range(0,len(indices),2))
  sheet=int(self.sheet.get());self.texture_raw[sheet*32768:(sheet+1)*32768]=packed
  self.dirty=True;self.paint_pending=True;self.draw();self.status.set("PNG imported.")
 def change_color(self):
  self.need();chosen=colorchooser.askcolor(color=self.palette()[self.color],parent=self.root)
  if chosen[0]:
   self.session.set_palette_color(self.current_map,int(self.palette_id.get()),self.color,tuple(int(c) for c in chosen[0]))
   self.draw();self.status.set("Palette colour applied. Undo is available.")
 def record_panel(self,tabs,kind,title,names):
  frame=ttk.Frame(tabs);tabs.add(frame,text=title)
  tree=ttk.Treeview(frame,columns=("id","summary","area"),show="headings",height=20)
  for key,width in [("id",50),("summary",250),("area",180)]:tree.heading(key,text=key.title());tree.column(key,width=width)
  tree.pack(side="left",fill="both",expand=True,padx=8,pady=8)
  form=ttk.Frame(frame,padding=10);form.pack(side="left",fill="y")
  fields=[]
  for i,name in enumerate(names):
   ttk.Label(form,text=name).grid(row=i,column=0,sticky="w",pady=2)
   var=tk.StringVar();fields.append(var)
   ttk.Entry(form,textvariable=var,width=16,state="readonly" if "Reserved" in name or "Unknown" in name else "normal").grid(row=i,column=1,pady=2)
  ttk.Button(form,text="Apply selected record",command=lambda:self.guard(lambda:self.apply_record(kind))).grid(row=len(names),columnspan=2,pady=12)
  links=ttk.Frame(form);links.grid(row=len(names)+2,columnspan=2)
  for bank in ("ABCDEF" if kind=="entities" else "B"):
   ttk.Button(links,text="Edit "+bank+" script",command=lambda b=bank:self.guard(lambda:self.open_record_script(kind,b))).pack(side="top",fill="x")
  self.record_views[kind]=(tree,fields,names)
  tree.bind("<<TreeviewSelect>>",lambda e:self.guard(lambda:self.select_record(kind)))
 def select_record(self,kind):
  tree,fields,names=self.record_views[kind]
  if not tree.selection():return
  row=inspect_map(self.session.data,self.current_map)[kind][int(tree.selection()[0])]
  o=int(row["offset"],16)
  values=struct.unpack_from("<16B2H" if kind=="entities" else "<8B",self.session.data,o)
  for var,value in zip(fields,values):var.set(str(value))
 def open_record_script(self,kind,bank):
  tree,fields,_=self.record_views[kind]
  if not tree.selection():raise ValueError("Select a character or event first")
  row=inspect_map(self.session.data,self.current_map)[kind][int(tree.selection()[0])]
  offset=int(row["offset"],16)
  index=self.session.data[offset+(10+ord(bank)-65 if kind=="entities" else 4)]
  if not index&128:
   self.status.set("This record uses a shared/global script; map-local script editing is unavailable for it.");return
  index &= 127
  key=f"{bank} {index}"
  if key not in script_roots(self.session,self.current_map):
   self.status.set(f"No map-local {bank} script for this record (index {index}); inherited scripts are not editable here.");return
  self.script_key.set(key);self.load_script();self.tabs.select(self.script_frame)
 def apply_record(self,kind):
  self.need();tree,fields,names=self.record_views[kind]
  if not tree.selection():raise ValueError("Select a record first")
  values=[int(f.get(),16) if f.get().lower().startswith("0x") else int(f.get()) for f in fields]
  self.session.edit_record(self.current_map,kind,int(tree.selection()[0]),values)
  self.status.set("Record applied. Undo is available; save a copy or export a patch.")
  selected=tree.selection()[0]
  tree.set(selected,"area",str(tuple(values[:4])))
  tree.set(selected,"summary",f"sprite {values[6]} | XYZ {tuple(values[7:10])}" if kind=="entities" else f"program {values[4]}")
  self.area.refresh()
 def undo(self):
  """Take back the last change on the map you are on: a tile placement, an
  event (placed, moved, deleted, its commands applied). Changes on other maps
  wait until you go back to them."""
  self.need();self.lock_in_closed_events()
  area=getattr(self,'area',None)
  if getattr(area,'has_pending_edits',lambda:False)():
   with self.session.group('Map edits'):area.commit_pending()   # edits still waiting (height editing): one step
  if getattr(self,'paint_pending',False):self.paint_pending=False
  m=self.current_map
  # tile pictures written in the background after the change go back with it
  while self.is_texture_write(self.session.last_for_map(m)):self.session.undo_map(m)
  change=self.session.undo_map(m)
  if change is None:
   self.status.set('Nothing to undo on this map.');return
  self.after_undo_redo(change,'Undone')
 def redo(self):
  """Put back the last change undone on the map you are on."""
  self.need();self.lock_in_closed_events()
  if not self.discard_paint():return
  m=self.current_map
  change=self.session.redo_map(m)
  if change is None:
   self.status.set('Nothing to redo on this map.');return
  while self.is_texture_write(self.session.last_for_map(m,redo=True)):self.session.redo_map(m)
  self.after_undo_redo(change,'Redone')
 def after_undo_redo(self,change,verb):
  from editor_session import DocumentEdit
  label=change[-1] if isinstance(change,tuple) else getattr(change,'label','')
  if isinstance(change,DocumentEdit):   # events only: no map reload needed
   self.refresh_deleted_events();self.status.set(f'{verb}: {label}.');return
  from map_slots import map_exists
  if not map_exists(self.session.data,int(self.map_id.get() or 0)):
   self.map_id.set(str(self.current_map if map_exists(self.session.data,self.current_map) else 163))
   self.current_map=None  # a new map slot was undone: show a map that exists
  same=self.current_map is not None and int(self.map_id.get() or 0)==self.current_map
  self.load_map(keep_view=same)   # same map: no scroll jump
  for child in self.root.winfo_children():   # an open event editor follows
   window=getattr(child,'_alundra_graph_window',None)
   if window is not None and hasattr(window,'resync'):window.resync()
  self.status.set(f'{verb}: {label}.')
 @staticmethod
 def is_texture_write(change):
  """An undo step that only wrote waiting tile pictures (Import foreign map tiles)."""
  return change is not None and getattr(change,'label','')=='Import foreign map tiles'
 def refresh_deleted_events(self):
  self.area.refresh(reload_textures=False)
  for child in self.root.winfo_children():
   window=getattr(child,'_alundra_graph_window',None)
   if window is not None:
    if hasattr(window,'resync'):window.resync()
    else:window.refresh_list()
 def save(self):
  self.need();self.apply_pixels()
  path=filedialog.asksaveasfilename(initialdir=ROOT/"game",initialfile="DATAS-edited.BIN",defaultextension=".BIN")
  if path:self.session.save_copy(path);self.status.set("DATAS copy saved. The original has not been changed.")
 def export_patch(self):
  self.need();self.apply_pixels()
  if any(x.undo_stack for x in getattr(self.session,"extra_files",{}).values()):raise ValueError("Use Save mod to include both map and balance edits. DATAS-only patches cannot contain balance changes.")
  path=filedialog.asksaveasfilename(initialdir=ROOT/"game",initialfile="alundra-edit.json",defaultextension=".json")
  if path:
   if Path(path).resolve()==self.session.path:raise ValueError("Cannot overwrite the original")
   with open(path,"x",encoding="utf-8") as f:json.dump(self.session.patch(),f,indent=2)
   self.status.set("Patch exported with source fingerprint and original-byte checks.")
 def save_mod_project(self,path=None,name=None):
  self.need();self.keep_open_event_edits();self.apply_pixels()
  from editor_preferences import project_build_name,safe_build_name,save_preferences,project_output_paths
  name=safe_build_name(name or (self.project_build_name.get() if hasattr(self,'project_build_name') else project_build_name()))
  if not path:   # Save: the file last saved/opened under this name (Save as may have put it elsewhere)
   from editor_preferences import load_preferences
   last=load_preferences().get('last_mod_path')
   path=last if last and Path(last).stem==name and Path(last).parent.is_dir() else project_output_paths(name)['mod']
  path=Path(path)
  self.session.content_database=self.database.to_json()
  save_mod(self.session,path,name,self.current_map,overwrite=True)
  save_preferences({'last_mod_path':str(Path(path).resolve())})   # reopened on next start
  if hasattr(self,'project_build_name'):self.project_build_name.set(name)
  save_preferences({'project_build_name':name})
  self.build_fingerprint=self.edit_fingerprint();self.dirty=False   # close knows it is saved
  self.status.set(f"Mod saved: {Path(path).name} (previous same-name project replaced).")
 def save_mod_project_as(self):
  """File > Save mod as...: Windows save dialog, its file name starting as the current project
  name; the mod is saved there under the name typed (user 2026-10-27)."""
  self.need()
  from editor_preferences import project_build_name,load_preferences,project_output_paths
  current=self.project_build_name.get() if hasattr(self,'project_build_name') else project_build_name()
  last=load_preferences().get('last_mod_path')
  folder=Path(last).parent if last and Path(last).parent.is_dir() else project_output_paths(current)['folder'].parent
  folder.mkdir(parents=True,exist_ok=True)
  chosen=filedialog.asksaveasfilename(title="Save mod as",parent=self.root,initialdir=str(folder),initialfile=current,
                                      defaultextension=".alundramod",filetypes=[("Alundra mod","*.alundramod")])
  if not chosen:return
  self.save_mod_project(path=chosen,name=Path(chosen).stem)
 def new_mod_project(self):
  """File / Mods > New mod: a fresh project on the original game data (nothing of
  the open project is kept), then the New project window (name, open world)."""
  if self.session is not None and (self.dirty or self.session.undo_stack or any(x.undo_stack for x in getattr(self.session,"extra_files",{}).values())) and not messagebox.askyesno("New mod","Start a new mod? Unsaved edits of this project are discarded.",parent=self.root):return
  window=getattr(self,'event_graph_window',None)
  if window is not None:
   try:
    if window.window.winfo_exists():window.window.destroy()
   except Exception:pass
   self.event_graph_window=None
  path=ROOT/"game/disc/DATA/DATAS.BIN"
  if path.is_file():data=path.read_bytes()
  elif self.session is not None:data=bytes(self.session.original);path=self.session.path
  else:raise ValueError("Open the game data first (File > Open game data).")
  self.session=EditSession.open_data(data,path,allow_compatible=True)
  self.database=ContentDatabase();self.session.content_database=self.database.to_json();self.dirty=False
  if hasattr(self,'mod_option_vars'):
   for key,var in self.mod_option_vars.items():var.set(MOD_OPTION_DEFAULTS.get(key,False))
  self.populate_database_from_game();self.db_refresh()
  self.ask_import_world_mode()
 def open_mod_project(self):
  self.need()
  path=filedialog.askopenfilename(title="Open mod",initialdir=ROOT/"game",filetypes=[("Alundra mod","*.alundramod")])
  if not path:return
  if (self.dirty or self.session.undo_stack or any(x.undo_stack for x in getattr(self.session,"extra_files",{}).values())) and not messagebox.askyesno("Open mod","Replace the current unsaved edits with this mod?",parent=self.root):return
  self.load_mod_path(path)
 def load_mod_path(self,path):
  """Load a mod project (Open mod, and the last project on start-up)."""
  # An open event editor works on a copy of the old project: close it first,
  # or its later edits would go into the old project and be lost.
  window=getattr(self,'event_graph_window',None)
  if window is not None:
   try:
    if window.window.winfo_exists():window.window.destroy()
   except Exception:pass
   self.event_graph_window=None
  extra_bases={name:getattr(extra,'disc_original',extra.original) for name,extra in getattr(self.session,"extra_files",{}).items()}
  if "DATA/BALANCE.BIN" not in extra_bases and self.session.path and self.session.path.suffix.lower()==".bin":
   try:extra_bases["DATA/BALANCE.BIN"]=read_datas(self.session.path,"DATA/BALANCE.BIN")
   except (ValueError,StopIteration):pass
  bar=None
  if hasattr(self,'root'):
   try:
    from mod_loading_bar import ModLoadingBar
    bar=ModLoadingBar(self.root,Path(path).stem)
   except Exception:bar=None
  try:
   original=self.session.original
   if bar is not None:session,m=bar.run(0,55,'Reading the mod file…',lambda progress:load_mod(original,path,extra_bases,progress=progress))
   else:session,m=load_mod(original,path,extra_bases)
   if bar is not None:bar.step(55,60,'Preparing the Database…')
   self.database=ContentDatabase(getattr(session,"content_database",None))
   self.session=session;self.dirty=False
   if bar is not None:bar.step(60,85,'Indexing map sprites, objects and instances…')
   self.mod_loading_bar=bar
   self.populate_database_from_game()
   self.mod_loading_bar=None
   if bar is not None:bar.step(85,90,'Updating the Database…')
   self.db_refresh()
   if bar is not None:bar.step(90,100,'Opening the start map…')
   self.go_to_start_point(fallback_map=m)
   if bar is not None:bar.set(100,'Done')
  finally:
   self.mod_loading_bar=None
   if bar is not None:bar.close()
  if hasattr(self,'project_build_name'):self.project_build_name.set(Path(path).stem)
  from editor_preferences import save_preferences
  save_preferences({'project_build_name':Path(path).stem,'last_mod_path':str(Path(path).resolve())})
  self.status.set("Mod loaded: "+Path(path).stem)

 def open_content_database(self):
  self.populate_database_from_game()
  self.preload_user_active(1.0);self.preload_prioritize('class')   # class previews next
  if self.db_window is not None and self.db_window.winfo_exists():
   self.db_instance_filter.set("All maps");self.db_refresh();self.db_window.deiconify();self.db_window.lift();return
  win=tk.Toplevel(self.root);self.db_window=win;win.title("Alundra Database — Classes and Instances")
  width=max(1000,min(1400,round(self.root.winfo_screenwidth()*.85)));height=max(700,min(self.root.winfo_screenheight()-60,round(self.root.winfo_screenheight()*.85)))
  win.geometry(f"{width}x{height}+30+0");win.minsize(900,600);apply_dark(win)
  toolbar=ttk.Frame(win,padding=8);toolbar.pack(fill="x");self.db_toolbar=toolbar
  for label,command in [("New class",self.db_add),("Switches / variables",self.open_project_state),("Duplicate",self.db_duplicate),("Delete",self.db_delete),("Attacks",self.db_native_attacks),("Animations",self.db_native_animations),("Hit boxes",self.db_frame_boxes),("Export Sprites...",self.db_export_sprites),("Import Sprites...",self.db_import_sprites),("Export all graphics",self.db_export_all_graphics)]:
   ttk.Button(toolbar,text=label,command=lambda c=command:self.guard(c)).pack(side="left",padx=3)
  self.db_tabs=ttk.Notebook(win);self.db_tabs.pack(fill="both",expand=True,padx=8,pady=4)
  self.db_trees={};self.db_texts={};self.db_preview_canvases={};self.db_dialogue_preview_canvases={};self.db_frames={};self.db_search_vars={}
  self.db_class_name=tk.StringVar();self.db_class_id=tk.StringVar()
  for kind in KINDS:
   frame=ttk.Frame(self.db_tabs);self.db_tabs.add(frame,text='Misc' if kind=='unclassified' else kind.replace("_"," ").title())
   self.db_frames[kind]=frame
   self._build_db_class_tab(frame,kind)
  from music_database_ui import MusicTab
  self.db_music=MusicTab(self,self.db_tabs)
  from sound_database_ui import SoundsTab
  self.db_sounds=SoundsTab(self,self.db_tabs)
  # Bushes tab removed from the Database (user 2026-10-18); bushes are still placed from the map view.
  # Map instances tab removed from the window (user request); built hidden so its data stays in sync.
  instances=ttk.Frame(self.db_window)
  self._build_db_instances_tab(instances)
  self.db_tabs.select(self.db_frames["npc"]);self.db_active_kind="npc";self.db_kind.set("npc")
  self.db_tabs.bind("<<NotebookTabChanged>>",self.db_tab_changed,add='+')   # (the Bushes tab listens too)
  win.protocol("WM_DELETE_WINDOW",self.close_content_database)
  # Delete key acts on the last thing clicked: a class list deletes its selected
  # class (asks first); lists with their own Delete (attacks, route steps) handle it.
  self.db_last_click=None
  win.bind('<Button-1>',lambda e:setattr(self,'db_last_click',e.widget),add='+')
  def delete_key(_):
   tree=self.db_last_click
   if tree in self.db_trees.values() and tree.winfo_exists() and tree.selection():self.guard(self.db_delete_key)
  win.bind('<Delete>',delete_key)
  if not getattr(self,'_db_autosave_bound',False):
   self._db_autosave_bound=True
   for sequence in ('<KeyRelease>','<ButtonRelease-1>','<<ComboboxSelected>>','<MouseWheel>'):self.root.bind_all(sequence,lambda e:self.db_schedule_autosave() if self.db_window is not None and str(e.widget).startswith(str(self.db_window)) else None,add='+')
  self.db_instance_filter.set("All maps")
  self.db_refresh()
 def populate_database_from_game(self):
  """Index and preload behind one visible loading window, off the UI thread."""
  if self.session is None:
   self.database.populate_catalogue();return
  extra=getattr(self.session,'extra_files',{}).get('DATA/BALANCE.BIN')
  # Only the game data decides whether maps must be indexed again. BALANCE.BIN
  # is written by the database itself (stats), so it is not part of the key:
  # it made every database opening after a stat change re-index all maps.
  index_key=(hashlib.sha256(self.session.data).hexdigest(),)
  self.cache_digest=index_key[0]   # per-game-data disk cache (tools/asset_cache.py)
  if getattr(self.database,'_ui_index_key',None)==index_key:return
  fresh=not self.database.document.get('definitions') and not self.database.document.get('instances')
  self.cancel_loading_map_job()
  def load(progress):
   # A progress-based bar: every step that will run gets a share of 0-100%,
   # and the long ones (reading the 483 maps, the first-start object library)
   # report inside their share.
   from stock_source import catalogue_base,map_differences
   import object_library   # every game object taken out of the disc data (first start only)
   import asset_cache
   cached=None
   if fresh:   # a new project reuses the Database an earlier one built on this game data (user 2026-10-27)
    cached=asset_cache.load_database(index_key[0],8)
    if cached is not None:self.database.document.clear();self.database.document.update(cached)
   base=catalogue_base(self.session);digest=hashlib.sha256(base).hexdigest()
   changed=map_differences(self.session);opened=bytes(self.session.original)
   key=digest+(':'+hashlib.sha256(opened).hexdigest() if changed else '')
   need_library=not object_library.available()
   need_index=self.database.document.get("indexed_map_build_sha256")!=key
   need_sprites=need_index and self.database.document.get("indexed_map_build_sha256","").split(':')[0]!=digest
   need_catalogue=self.database.document.get("named_catalogue_build")!=digest or self.database.document.get('named_catalogue_version')!=8
   plan=[('library',40,need_library),('sprites',20,need_sprites),('changed',5,need_index and bool(changed)),
         ('instances',25,True),('balance',2,True),('catalogue',15,need_catalogue)]
   weights={k:w for k,w,on in plan if on};total=sum(weights.values());TOTAL=1000
   state={'base':0.0,'share':0.0,'text':''}
   def stage(k,text):
    state['base']+=state['share'];state['share']=weights.get(k,0)/total;state['text']=text
    part(0.0)
   def part(f):
    progress(int(TOTAL*min(1.0,state['base']+state['share']*max(0.0,min(1.0,f)))),TOTAL,state['text'])
   self.database._map_progress=part
   try:
    if need_library:
     stage('library','Taking the game objects out of the disc data (first start only, about 2 minutes)…')
     def lib(text):
      try:a,b=str(text).split(':',1)[1].strip().split('/');part(int(a)/int(b))
      except (ValueError,IndexError,ZeroDivisionError):pass
     object_library.build(base,budget=10**9,progress=lib)
    if need_index:
     if need_sprites:
      stage('sprites','Indexing map sprites…');self.database.scan_all_map_sprites(base)
     if changed:
      stage('changed','Indexing changed maps…')
      for i,m in enumerate(changed):   # only maps the opened game changes; the rest match and are skipped
       part(i/len(changed));self.database.discover_map_sprites(opened,m)
     self.database.document["indexed_map_build_sha256"]=key
    stage('instances','Indexing objects and instances…')
    self.database.scan_instances(bytes(self.session.data),source_datas=base)
    stage('balance','Reading the balance table…')
    balance=None
    extra=getattr(self.session,"extra_files",{}).get("DATA/BALANCE.BIN")
    if extra is not None:balance=bytes(extra.data)
    elif self.session.source_verified:
     path=ROOT/"game/disc/DATA/BALANCE.BIN"
     if path.is_file():balance=path.read_bytes()
    elif self.session.path and self.session.path.suffix.lower()==".bin":
     try:balance=read_datas(self.session.path,"DATA/BALANCE.BIN")
     except (ValueError,StopIteration):pass
    if balance is not None:self.database.import_balance_table(balance,preserve_existing=True)
    # Database entries of the game's own objects come from the ORIGINAL game data
    # (session.original), never the project's edited maps: done once per original
    # disc, and erasing or changing stock maps never changes them.
    if need_catalogue:
     stage('catalogue','Naming the game objects…')
     self.database.populate_catalogue(base);self.database.document["named_catalogue_build"]=digest;self.database.document['named_catalogue_version']=8
   finally:
    self.database._map_progress=None
   progress(TOTAL,TOTAL,'Done')
   self.database._ui_index_key=index_key
   if fresh and cached is None:asset_cache.save_database(index_key[0],8,self.database.document)
  if hasattr(self,'root'):
   from editor_memory_loading import run_memory_load
   self.status.set('Loading game into memory…')
   self.memory_loading=True
   bar=getattr(self,'mod_loading_bar',None)
   def report(done,total,text):
    if bar is not None:bar.sub(done,total,text)
    self.set_memory_bar(done,total,'Loading game into memory')
    if text and text!='Done':self.status.set(text)
   self.set_memory_bar(0,0,'Loading game into memory')
   try:run_memory_load(self.root,load,report=report)
   finally:self.memory_loading=False;self.set_memory_bar(None)
   self.status.set('Database ready — opening map. The rest loads in the background.')
   # Sprites, textures, scripts and dialogue of every map load in the
   # background now; whatever you open first is loaded first.
   self.root.after(200,self.start_background_preload)
   # background picture warm-up switched off: its long decodes competed with the Database for
   # Python's one thread and made switching classes laggy (user 2026-10-27). Pictures still
   # load on demand and are kept on disk (asset_cache), so later sessions are fast.
  else:load(lambda *args:None)
  self.db_instance_filter.set('All maps') if hasattr(self,'db_instance_filter') else None

 def cancel_loading_map_job(self):
  if getattr(self,'map_load_job',None) is not None:
   self.root.after_cancel(self.map_load_job);self.map_load_job=None

 def schedule_asset_preload(self):
  self.start_background_preload()
 def start_background_preload(self):
  """Load the rest of the game into memory in the background (see
  tools/editor_background_preload.py); you can work meanwhile."""
  self.start_build_warmer()
  if not hasattr(self,'root') or self.session is None or getattr(self.session,'asset_preload_result',None) is not None:return
  old=getattr(self,'background_preload',None)
  if old is not None:
   if old.session is self.session and not old.stopped:return
   old.stop()
  from editor_background_preload import BackgroundPreload
  self.background_preload=BackgroundPreload(self,self.session,self.database).start()
  if not getattr(self,'_preload_activity_bound',False):
   self._preload_activity_bound=True
   for sequence in ('<ButtonPress>','<KeyPress>','<MouseWheel>'):
    self.root.bind_all(sequence,lambda _e:self.preload_user_active(),add='+')
  self.poll_background_preload();self.tick_background_preload()
 def start_build_warmer(self):
  """Compile the project's events in quiet moments, so Build finds them ready
  (tools/build_warmer.py). Started once; it follows whatever game is open."""
  if not hasattr(self,'root') or getattr(self,'build_warmer',None) is not None:return
  from build_warmer import BuildWarmer
  self.build_warmer=BuildWarmer(self)
  for sequence in ('<ButtonPress>','<KeyPress>','<MouseWheel>','<Motion>'):
   self.root.bind_all(sequence,lambda _e:self.build_warmer.user_active(),add='+')
  self.build_warmer.heartbeat();self.root.after(2000,self.build_warmer.tick)
 def tick_background_preload(self):
  """Every 50 ms: tells the background loader the editor is free (a late tick
  means the editor is busy, and the loader waits)."""
  job=getattr(self,'background_preload',None)
  if job is None or job.finished or job.stopped or job.session is not self.session:return
  job.tick()
  try:self.root.after(50,self.tick_background_preload)
  except tk.TclError:pass
 def preload_user_active(self,seconds=None):
  job=getattr(self,'background_preload',None)
  if job is not None:job.user_active() if seconds is None else job.user_active(seconds)
 def preload_prioritize_map(self,m):
  """Map m's assets first, then those of the maps its doors and warp events lead to
  (where you are most likely to go next)."""
  job=getattr(self,'background_preload',None)
  if job is None or job.finished:return
  near=[]
  try:
   from warp_editor import warps
   near+=[p.destination_map for _,_,p in warps(self.session,m)]
  except Exception:pass
  for graph in self.database.document.get('event_graphs',[]) or []:
   if isinstance(graph,dict) and graph.get('map_id')==m:
    for page in graph.get('pages',[]) or []:
     for c in page.get('commands',[]) or []:
      if isinstance(c,dict) and c.get('type')=='warp_player' and type(c.get('map_id')) is int:near.append(c['map_id'])
  seen=[]
  for n in near:
   if n!=m and n not in seen:seen.append(n)
  for n in reversed(seen[:12]):job.prioritize(('map',n))
  job.prioritize(('map',m))
 def preload_prioritize(self,group):
  job=getattr(self,'background_preload',None)
  if job is not None and not job.finished:job.prioritize(group)
 def set_memory_bar(self,done,total=0,text=''):
  """The status bar's memory loading bar: done None hides it; total 0 = still preparing."""
  bar=getattr(self,'memory_bar',None)
  if bar is None:return
  try:
   if done is None:
    if self.memory_bar_shown:bar.stop();bar.pack_forget();self.memory_bar_shown=False
    return
   if not self.memory_bar_shown:
    bar.pack(side="right",padx=(0,4),pady=5);self.memory_bar_shown=True
   if total:
    if str(bar['mode'])!='determinate':bar.stop();bar.configure(mode='determinate')
    pct=min(100,100*done/total);bar.configure(value=pct)
    self.preload_status.set(f'{text} {pct:.0f}%')
   else:
    bar.configure(value=0);self.preload_status.set(f'{text} 0%')
   bar.update_idletasks()
  except tk.TclError:pass
 def poll_background_preload(self):
  job=getattr(self,'background_preload',None)
  try:
   self.preload_status.set(job.status_text() if job is not None and job.session is self.session else '')
   if job is not None and job.session is self.session and not job.finished and not job.stopped:
    self.set_memory_bar(job.done,max(1,job.total),'Loading in background')
   else:self.set_memory_bar(None)
  except (AttributeError,tk.TclError):return
  if job is not None and not job.finished and not job.stopped and job.session is self.session:
   self.root.after(500,self.poll_background_preload)
  elif job is not None and job.finished:self.root.after(500,lambda:self.preload_status.set(''))   # done: clear the progress
 def close_content_database(self):
  self.db_autosave()
  if self.db_window is not None and self.db_window.winfo_exists():self.db_window.destroy()
  self.db_window=None;self.db_trees={};self.db_texts={};self.db_preview_canvases={};self.db_dialogue_preview_canvases={};self.db_frames={}
 def keep_open_event_edits(self):
  area=getattr(self,'area',None)
  if getattr(area,'has_pending_edits',getattr(area,'has_pending',lambda:False))():
   with self.session.group('Map edits'):wrote=area.commit_pending()   # one undo step
   if wrote:area.refresh(reload_textures=False,keep_view=True)
  autosave=getattr(self,'db_autosave',None)
  if autosave:autosave()
  window=getattr(self,'event_graph_window',None)
  if window is not None and window.window.winfo_exists():
   if getattr(window,'closing',lambda:False)():window.finish_close()
   else:window.keep_changes()
  for child in getattr(getattr(self,'root',None),'winfo_children',lambda:[])():
   native=getattr(child,'_alundra_graph_window',None)
   if native is not window and getattr(native,'native_map',None) is not None:native.keep_changes()
 def event_graphs_view(self):
  """Events to draw: a just-closed editor's edits show at once, before they are saved."""
  window=getattr(self,'event_graph_window',None)
  try:
   if window is not None and window.closing():return window.db.document.get('event_graphs',[])
  except Exception:pass
  return self.database.document.get('event_graphs',[])
 def lock_in_closed_events(self):
  """A just-closed event editor saves before the map changes."""
  window=getattr(self,'event_graph_window',None)
  if window is not None and getattr(window,'closing',lambda:False)():window.finish_close()
 def open_event_builder(self,event_id=None):
  window=getattr(self,"event_graph_window",None)
  if window is not None and window.window.winfo_exists():
   if getattr(window,'closing',lambda:False)():window.cancel_close()
   if event_id:window.open_event(event_id)
   else:window.window.deiconify();window.window.lift()
   return
  from event_graph_ui import EventGraphWindow
  self.event_graph_window=EventGraphWindow(self)
  if event_id:self.event_graph_window.open_event(event_id)
 def create_event_at(self,map_id,x,y):
  """Start an RPG-style project event at a double-clicked empty map tile."""
  if hasattr(self,'area') and self.area.tile_mode_on():
   self.status.set('Turn off Edit heights, Mark walls and Mask layer before creating events.')
   return
  if self.session is None:raise ValueError("Open game data before creating a map event")
  from map_slots import map_exists
  if not map_exists(self.session.data,map_id):raise ValueError("Map number must be an existing map")
  self.populate_database_from_game()
  from event_graph_ui import EventGraphWindow
  window=getattr(self,"event_graph_window",None)
  if window is None or not window.window.winfo_exists():
   self.event_graph_window=EventGraphWindow(self)
   window=self.event_graph_window
  window.create_at(map_id,x,y)
  if self.area:
   self.area.draw_records();self.area.mode.set("Events")
  self.status.set(f"New event at map {map_id}, tile {x},{y}. Its pages and commands are saved in the mod project.")
 def _build_db_class_tab(self,frame,kind):
  body=ttk.Panedwindow(frame,orient="horizontal");body.pack(fill="both",expand=True,padx=8,pady=8)
  left=ttk.Frame(body);body.add(left,weight=1)
  search=tk.StringVar();self.db_search_vars[kind]=search
  ttk.Label(left,text='Search by name or database ID').pack(anchor='w',pady=(0,3))
  ttk.Entry(left,textvariable=search).pack(fill='x',pady=(0,6))
  search.trace_add('write',lambda *_,k=kind:self.db_filter_classes(k))
  list_frame=ttk.Frame(left);list_frame.pack(fill='both',expand=True)
  tree=ttk.Treeview(list_frame,columns=(("id","category","sprite","members") if kind=="item" else ("id","sprite","members")),show="tree headings",height=18)
  tree.heading("id",text="ID");tree.column("id",width=55,anchor="center",stretch=False)   # the ID is its own column, never part of the name
  if kind=="item":tree.heading("category",text="Category");tree.column("category",width=100)
  tree.heading("#0",text="Name");tree.heading("sprite",text="Graphic");tree.heading("members",text="Uses")
  tree.column("#0",width=220);tree.column("sprite",width=95,anchor="center");tree.column("members",width=65,anchor="center")
  scroll=ttk.Scrollbar(list_frame,orient='vertical',command=tree.yview);scroll.pack(side='right',fill='y');tree.configure(yscrollcommand=scroll.set)
  tree.pack(side='left',fill="both",expand=True);tree.bind("<<TreeviewSelect>>",lambda e,k=kind:(self.db_autosave(),self.db_select(k)))
  right=ttk.Panedwindow(body,orient="vertical");body.add(right,weight=2)
  preview_frame=ttk.Frame(right);right.add(preview_frame,weight=0)
  preview_frame.columnconfigure(0,weight=1);preview_frame.columnconfigure(1,weight=1)
  ttk.Label(preview_frame,text="On-map graphic" if kind=="npc" else "Class graphic").grid(row=0,column=0,sticky="w",padx=5)
  canvas=tk.Canvas(preview_frame,width=300,height=190,background="#11151b",highlightthickness=1,highlightbackground="#394352")
  canvas.grid(row=1,column=0,sticky="nsew",padx=5,pady=3);canvas.create_text(150,95,text="Choose a class",fill="#b8c2d2",tags=("placeholder",))
  self.db_preview_canvases[kind]=canvas
  if kind=="npc":
   ttk.Label(preview_frame,text="Dialogue graphic").grid(row=0,column=1,sticky="w",padx=5)
   dialogue_canvas=tk.Canvas(preview_frame,width=300,height=190,background="#11151b",highlightthickness=1,highlightbackground="#394352")
   dialogue_canvas.grid(row=1,column=1,sticky="nsew",padx=5,pady=3);dialogue_canvas.create_text(150,95,text="No dialogue graphic linked",fill="#b8c2d2",tags=("placeholder",))
   self.db_dialogue_preview_canvases[kind]=dialogue_canvas
  details_host=ttk.Frame(right);right.add(details_host,weight=1)
  details_canvas=tk.Canvas(details_host,background='#202630',highlightthickness=0)
  details_scroll=ttk.Scrollbar(details_host,orient='vertical',command=details_canvas.yview);details_scroll.pack(side='right',fill='y')
  details_canvas.configure(yscrollcommand=details_scroll.set);details_canvas.pack(side='left',fill='both',expand=True)
  details=ttk.Frame(details_canvas);details_item=details_canvas.create_window((0,0),window=details,anchor='nw')
  details.bind('<Configure>',lambda _:details_canvas.configure(scrollregion=details_canvas.bbox('all')))
  details_canvas.bind('<Configure>',lambda event:details_canvas.itemconfigure(details_item,width=event.width))
  details_canvas.bind('<MouseWheel>',lambda event:details_canvas.yview_scroll(-int(event.delta/120),'units'))
  ttk.Label(details,text="Class settings",font=("Segoe UI",12,"bold")).pack(anchor="w",pady=(2,5))
  identity=ttk.Frame(details);identity.pack(fill="x",pady=(0,6))
  if kind=='item':   # how a healing item heals Alundra (item_heals), display only
   self.db_heal_text=tk.StringVar(value='')
  if kind in ('object','unclassified'):   # hit points of the class (its native balance), display only
   if not hasattr(self,'db_hp_texts'):self.db_hp_texts={}
   self.db_hp_texts[kind]=tk.StringVar(value='')
  ttk.Label(identity,text="Class name").pack(side="left")
  ttk.Entry(identity,textvariable=self.db_class_name,width=28).pack(side="left",padx=6)
  ttk.Label(identity,text="Database ID").pack(side="left",padx=(12,3))
  ttk.Label(identity,textvariable=self.db_class_id).pack(side="left")
  if kind in ('item','weapon','armor'):
   # in-game name and description (item_text, ETC_USA.R)
   if not hasattr(self,'db_text_vars'):self.db_text_vars={}
   box=ttk.LabelFrame(details,text='In-game text',padding=6);box.pack(fill='x',pady=(0,6))
   self.db_text_vars[kind]={}
   for i,(key,label) in enumerate((('name','Name'),('description','Description'),('description2','Second line'))):
    var=tk.StringVar();self.db_text_vars[kind][key]=var
    ttk.Label(box,text=label).grid(row=i,column=0,sticky='w',pady=1)
    ttk.Entry(box,textvariable=var,width=44).grid(row=i,column=1,sticky='ew',padx=6,pady=1)
    var.trace_add('write',lambda *_:self.db_schedule_autosave())
   box.columnconfigure(1,weight=1)
  if kind in getattr(self,'db_hp_texts',{}):ttk.Label(details,textvariable=self.db_hp_texts[kind]).pack(anchor='w',pady=(0,4))
  if kind=='item':
   self.db_heal_label=ttk.Label(details,textvariable=self.db_heal_text)
   # editable heal values (item_heals): part of max life + minimum, or a flat amount
   # custom consumable effect (custom_consume): items Circle can use (31-50)
   cf=ttk.LabelFrame(details,text='When used',padding=6);self.db_consume_frame=cf
   self.db_cons_hp=tk.StringVar(value='None');self.db_cons_hp_value=tk.StringVar(value='0');self.db_cons_hp_part=tk.StringVar(value='1/4')
   self.db_cons_hp_min=tk.StringVar(value='0');self.db_cons_mp=tk.StringVar(value='None');self.db_cons_mp_value=tk.StringVar(value='0')
   self.db_cons_revive=tk.BooleanVar(value=False)
   hp_line=ttk.Frame(cf);hp_line.pack(fill='x');mp_line=ttk.Frame(cf);mp_line.pack(fill='x',pady=(4,0))
   ttk.Label(hp_line,text='HP',width=4).pack(side='left')
   ttk.Combobox(hp_line,textvariable=self.db_cons_hp,values=['None','Amount','Part of max','Full'],state='readonly',width=12).pack(side='left',padx=(0,6))
   self.db_cons_hp_amount=ttk.Spinbox(hp_line,from_=0,to=999,textvariable=self.db_cons_hp_value,width=5)
   self.db_cons_hp_partbox=ttk.Combobox(hp_line,textvariable=self.db_cons_hp_part,values=['1/1','1/2','1/4','1/8','1/16'],state='readonly',width=5)
   self.db_cons_hp_minlabel=ttk.Label(hp_line,text='at least');self.db_cons_hp_minbox=ttk.Spinbox(hp_line,from_=0,to=999,textvariable=self.db_cons_hp_min,width=5)
   ttk.Label(mp_line,text='MP',width=4).pack(side='left')
   ttk.Combobox(mp_line,textvariable=self.db_cons_mp,values=['None','Amount','Full'],state='readonly',width=12).pack(side='left',padx=(0,6))
   self.db_cons_mp_amount=ttk.Spinbox(mp_line,from_=0,to=255,textvariable=self.db_cons_mp_value,width=5)
   ttk.Checkbutton(cf,text='Revive (used up when Alundra falls)',variable=self.db_cons_revive,command=self.db_schedule_autosave).pack(anchor='w',pady=(4,0))
   def consume_fields(*_):
    for w in (self.db_cons_hp_amount,self.db_cons_hp_partbox,self.db_cons_hp_minlabel,self.db_cons_hp_minbox,self.db_cons_mp_amount):w.pack_forget()
    if self.db_cons_hp.get()=='Amount':self.db_cons_hp_amount.pack(side='left')
    if self.db_cons_hp.get()=='Part of max':
     self.db_cons_hp_partbox.pack(side='left');self.db_cons_hp_minlabel.pack(side='left',padx=(6,3));self.db_cons_hp_minbox.pack(side='left')
    if self.db_cons_mp.get()=='Amount':self.db_cons_mp_amount.pack(side='left')
   for v in (self.db_cons_hp,self.db_cons_mp):v.trace_add('write',consume_fields)
   for v in (self.db_cons_hp,self.db_cons_hp_value,self.db_cons_hp_part,self.db_cons_hp_min,self.db_cons_mp,self.db_cons_mp_value):v.trace_add('write',lambda *_:self.db_schedule_autosave())
   heal=ttk.Frame(details);self.db_heal_frame=heal;self.db_heal_anchor=ttk.Frame(details);self.db_heal_anchor.pack(fill='x');self.db_heal_label.pack(anchor='w',pady=(0,2),after=self.db_heal_anchor)
   self.db_heal_part=tk.StringVar();self.db_heal_least=tk.StringVar();self.db_heal_amount=tk.StringVar()
   self.db_heal_part_row=ttk.Frame(heal)
   ttk.Label(self.db_heal_part_row,text='Heals').pack(side='left')
   ttk.Combobox(self.db_heal_part_row,textvariable=self.db_heal_part,values=['1/1','1/2','1/4','1/8','1/16','1/32'],state='readonly',width=5).pack(side='left',padx=4)
   ttk.Label(self.db_heal_part_row,text='of max life, at least').pack(side='left')
   self.db_heal_least_box=ttk.Spinbox(self.db_heal_part_row,from_=0,to=999,textvariable=self.db_heal_least,width=5);self.db_heal_least_box.pack(side='left',padx=4)
   self.db_heal_amount_row=ttk.Frame(heal)
   self.db_heal_verb=tk.StringVar(value='Heals');self.db_heal_unit=tk.StringVar(value='life')
   ttk.Label(self.db_heal_amount_row,textvariable=self.db_heal_verb).pack(side='left')
   ttk.Spinbox(self.db_heal_amount_row,from_=1,to=999,textvariable=self.db_heal_amount,width=5).pack(side='left',padx=4)
   ttk.Label(self.db_heal_amount_row,textvariable=self.db_heal_unit).pack(side='left')
   for v in (self.db_heal_part,self.db_heal_least,self.db_heal_amount):v.trace_add('write',lambda *_:self.db_schedule_autosave())
   # what a magic item spawns (magic_spawns): one global class per spawn
   self.db_magic_frame=ttk.LabelFrame(details,text='Spawned when used',padding=6);self.db_magic_vars=[]
  if kind=='player':
   from starting_equipment_ui import StartingEquipmentPanel
   self.db_starting_panel=StartingEquipmentPanel(details,self)
  if kind=="object":
   # Custom AI objects (spawned attacks): how long they last, and wall hits
   self.db_lifetime_text=tk.StringVar();self.db_destroy_wall=tk.BooleanVar(value=True)
   life=ttk.Frame(details);self.db_lifetime_row=life
   self.db_lifetime_label=ttk.Label(life,textvariable=self.db_lifetime_text)
   self.db_lifetime_button=ttk.Button(life,text='Edit…',command=lambda:self.guard(self.db_edit_lifetime))
   ttk.Checkbutton(life,text='Destroy when it hits a wall',variable=self.db_destroy_wall,command=lambda:self.guard(self.db_set_destroy_wall)).pack(side='right')
   self.db_lifetime_anchor=ttk.Frame(details);self.db_lifetime_anchor.pack(fill='x')
   outer=ttk.LabelFrame(details,text="Custom object class behaviour",padding=6);outer.pack(fill="x",pady=(0,6))
   self.db_object_custom=tk.BooleanVar(value=False)
   behavior=ttk.Frame(outer);self.db_object_custom_body=behavior
   def custom_toggled():
    if self.db_object_custom.get():behavior.pack(fill="x",pady=(4,0))
    else:
     behavior.pack_forget()   # off: the class behaves as the game made it
     self.db_object_item.set("No item")
     for var in list(self.db_object_type_vars.values())+list(getattr(self,'db_object_state_vars',{}).values()):var.set(False)
     for a,d in self.db_object_reaction_vars.values():a.set(False);d.set(False)
    self.db_schedule_autosave()
   ttk.Checkbutton(outer,text="Use custom behaviour",variable=self.db_object_custom,command=lambda:self.guard(custom_toggled)).pack(anchor="w")
   ttk.Label(behavior,text="Chest / drop item class").pack(anchor="w")
   self.db_object_item_combo=ttk.Combobox(behavior,textvariable=self.db_object_item,state="readonly",width=48)
   self.db_object_item_combo.pack(anchor="w",fill="x",pady=(0,5))
   type_row=ttk.Frame(behavior);type_row.pack(fill="x")
   self.db_object_type_vars={}
   for label,key in [("Destructible","destructible"),("Throwable","throwable"),("Reacts to hit","reacts_to_hit"),("Spawns drops","spawns_drops"),("Breaks when thrown","breaks_when_thrown")]:
    var=tk.BooleanVar(value=False);self.db_object_type_vars[key]=var
    ttk.Checkbutton(type_row,text=label,variable=var).pack(side="left",padx=4)
   state_row=ttk.Frame(behavior);state_row.pack(fill='x',pady=(4,0))
   self.db_object_state_vars={key:tk.BooleanVar(value=False) for key in ('active_by_default','activation_one_way','remember_state_until_area_exit')}
   for label,key in [('Active at start (off by default)','active_by_default'),('Activation is one-way','activation_one_way'),('Remember after leaving area','remember_state_until_area_exit')]:
    ttk.Checkbutton(state_row,text=label,variable=self.db_object_state_vars[key]).pack(side='left',padx=4)
   # Switch (Step On) only: ON only while stood on; events get a Deactivate tab for stepping off
   self.db_object_state_vars['while_pressured']=tk.BooleanVar(value=False)
   self.db_while_pressured_box=ttk.Checkbutton(state_row,text='While Pressed',variable=self.db_object_state_vars['while_pressured'])
   matrix=ttk.Frame(behavior);matrix.pack(anchor="w",fill="x",pady=(6,0))
   ttk.Label(matrix,text="React to").grid(row=0,column=0,sticky="w",padx=(0,20))
   ttk.Label(matrix,text="Activate").grid(row=0,column=1,padx=8);ttk.Label(matrix,text="Destroy").grid(row=0,column=2,padx=8)
   self.db_object_reaction_vars={}
   labels={"player_touch":"Player touch","player_standing":"Player standing","sword":"Sword","flail":"Flail","bow":"Bow","fire_wand":"Fire wand","ice_wand":"Ice wand","bomb":"Bomb","spring_bean":"Spring bean","objects":"Other objects"}
   for i,key in enumerate(OBJECT_REACTIONS,1):
    ttk.Label(matrix,text=labels[key]).grid(row=i,column=0,sticky="w")
    activate=tk.BooleanVar(value=False);destroy=tk.BooleanVar(value=False);self.db_object_reaction_vars[key]=(activate,destroy)
    ttk.Checkbutton(matrix,variable=activate).grid(row=i,column=1,padx=8);ttk.Checkbutton(matrix,variable=destroy).grid(row=i,column=2,padx=8)
  if kind in ('enemy','boss','player'):
   from enemy_stats_ui import EnemyCombatPanel
   if not hasattr(self,'db_combat_panels'):self.db_combat_panels={}
   if kind=='player':
    # Alundra: each attack named by the animation that uses it; Meia shows her NPC record.
    from player_attacks import player_label
    self.db_combat_panels[kind]=EnemyCombatPanel(details,labels=player_label,show_hp=False,readonly_attacks=True)
    ttk.Label(details,text="Alundra's attack values come from the weapons: change them in each weapon's damage settings.",wraplength=570).pack(anchor='w')
   else:self.db_combat_panels[kind]=EnemyCombatPanel(details)
   if kind in ('enemy','boss'):ttk.Button(self.db_combat_panels[kind].frame,text='Edit AI…',width=14,command=lambda:self.guard(self.db_edit_ai)).place(relx=1.0,x=-12,y=6,anchor='ne')   # top right, beside Max HP / Contact Damage
   from spawn_attacks_ui import SpawnAttacksPanel
   if not hasattr(self,'db_spawn_panels'):self.db_spawn_panels={}
   self.db_spawn_panels[kind]=SpawnAttacksPanel(details,self)
   # Shown inside Combat, right under Contact Damage and the other attacks.
   combat=self.db_combat_panels[kind]
   self.db_spawn_panels[kind].frame.pack_configure(in_=combat.frame,after=combat.attack_host,fill='x',pady=(2,4))
  if kind=='unclassified':
   # Misc lists boss parts (Melzas Double...): their spawned attacks are edited here too
   from spawn_attacks_ui import SpawnAttacksPanel
   if not hasattr(self,'db_spawn_panels'):self.db_spawn_panels={}
   self.db_spawn_panels[kind]=SpawnAttacksPanel(details,self)
  if kind in ('enemy','boss'):
   # Placed after the attacks: one setting for animation and attack speed.
   if not hasattr(self,'db_speed_vars'):self.db_speed_vars={}
   speed_box=ttk.LabelFrame(details,text='Speed',padding=6);speed_box.pack(fill='x',pady=3)
   speed_var=tk.StringVar(value='100');self.db_speed_vars[kind]=speed_var
   speed_row=ttk.Frame(speed_box);speed_row.pack(fill='x')
   ttk.Label(speed_row,text='Animation and attack %',width=22).pack(side='left')
   speed_scale=ttk.Scale(speed_row,from_=25,to=500,orient='horizontal',command=lambda value,v=speed_var:v.set(str(round(float(value)))))
   speed_scale.pack(side='left',fill='x',expand=True,padx=6)
   ttk.Spinbox(speed_row,textvariable=speed_var,from_=25,to=500,increment=5,width=6).pack(side='left')
   ttk.Button(speed_row,text='Reset',command=lambda v=speed_var:v.set('100')).pack(side='left',padx=(6,0))
   if not hasattr(self,'db_move_speed_vars'):self.db_move_speed_vars={}
   move_var=tk.StringVar(value='100');self.db_move_speed_vars[kind]=move_var
   move_row=ttk.Frame(speed_box);move_row.pack(fill='x',pady=(4,0))
   ttk.Label(move_row,text='Movement %',width=22).pack(side='left')
   move_scale=ttk.Scale(move_row,from_=25,to=500,orient='horizontal',command=lambda value,v=move_var:v.set(str(round(float(value)))))
   move_scale.pack(side='left',fill='x',expand=True,padx=6)
   ttk.Spinbox(move_row,textvariable=move_var,from_=25,to=500,increment=5,width=6).pack(side='left')
   ttk.Button(move_row,text='Reset',command=lambda v=move_var:v.set('100')).pack(side='left',padx=(6,0))
   def _move_sync(*_,v=move_var,s=move_scale):
    try:value=int(v.get())
    except ValueError:return
    if 25<=value<=500 and round(float(s.get()))!=value:s.set(value)
    self.db_schedule_autosave()
   move_var.trace_add('write',_move_sync)
   def _speed_sync(*_,v=speed_var,s=speed_scale):
    try:value=int(v.get())
    except ValueError:return
    if 25<=value<=500 and round(float(s.get()))!=value:s.set(value)
    self.db_schedule_autosave()
   speed_var.trace_add('write',_speed_sync)
  if kind=='item':
   from item_categories_ui import ItemCategoryPanel
   self.db_item_panel=ItemCategoryPanel(details,self.database_source_exe)
   self.db_item_panel.category.trace_add('write',lambda *_:self.db_item_refresh())
   # the item's colour (global bank: its look on every map; global_sprite_recolor at build)
   colour=ttk.LabelFrame(details,text='Colour',padding=6);self.db_item_colour_frame=colour
   self.db_item_hue=tk.StringVar(value='0');self.db_item_sat=tk.StringVar(value='100')
   ttk.Label(colour,text='Hue').pack(side='left')
   ttk.Spinbox(colour,from_=-180,to=180,increment=10,textvariable=self.db_item_hue,width=5).pack(side='left',padx=(3,10))
   ttk.Label(colour,text='Saturation').pack(side='left')
   ttk.Spinbox(colour,from_=0,to=200,increment=10,textvariable=self.db_item_sat,width=5).pack(side='left',padx=3)
   self.db_item_colour_preview=ttk.Label(colour);self.db_item_colour_preview.pack(side='left',padx=(10,0))
   def item_colour_preview(*_):
    row=getattr(self.db_item_panel,'loaded',None)
    try:shift=(int(self.db_item_hue.get()),int(self.db_item_sat.get()))
    except ValueError:return
    icon=self.db_class_icon(row,size=32,shift=shift) if row else None
    self.db_item_colour_preview.configure(image=icon or '');self.db_item_colour_preview.image=icon
   for v in (self.db_item_hue,self.db_item_sat):v.trace_add('write',item_colour_preview);v.trace_add('write',lambda *_:self.db_schedule_autosave())
   self.db_item_colour_show=item_colour_preview
  if kind=='armor':
   from armor_damage_ui import ArmorDamagePanel
   self.db_armor_panel=ArmorDamagePanel(details,self)
  if kind=='item':
   from armor_damage_ui import AccessoryDamagePanel
   self.db_accessory_panel=AccessoryDamagePanel(details,self)
  if kind=='weapon':
   from weapon_damage_ui import WeaponDamagePanel
   self.db_weapon_panel=WeaponDamagePanel(details,self)
  fields=ttk.LabelFrame(details,text="Misc" if kind in ('enemy','boss','player') else "General settings",padding=8)
  if kind in ('enemy','boss','player','object'):
   pass  # Misc settings stay hidden (checkbox removed 2026-10-07); objects use the behaviour panel instead (2026-10-08)
  elif kind not in ('weapon','npc'):
   # the general settings are custom settings: shown when "Custom settings" is ticked (user 2026-10-26)
   if not hasattr(self,'db_custom_settings'):self.db_custom_settings={}
   custom=tk.BooleanVar(value=False);self.db_custom_settings[kind]=custom
   anchor=ttk.Frame(details);anchor.pack(fill='x')
   def custom_toggled(kind=kind,custom=custom,fields=fields,anchor=anchor):
    if custom.get():fields.pack(fill="x",after=anchor)
    else:
     fields.pack_forget()
     for var in self.db_field_vars.get(kind,{}).values():var.set('')   # off: the game's own values
   if kind=='item':
    self.db_item_anchor=anchor;self.db_item_fields=fields
    if hasattr(self,'db_heal_anchor'):self.db_heal_anchor.pack(fill='x',before=anchor)   # Heals above Custom settings (user 2026-10-27)
   if kind=='armor':self.db_armor_anchor=anchor;self.db_armor_fields=fields
   ttk.Checkbutton(anchor,text='Custom settings',variable=custom,command=lambda f=custom_toggled:self.guard(lambda:(f(),self.db_item_refresh(),self.db_armor_refresh(True),self.db_schedule_autosave()))).pack(anchor='w')
   self.__dict__.setdefault('db_custom_toggles',{})[kind]=custom_toggled   # NPC World / Dialogue Sprite box removed (user 2026-10-11)
  if not hasattr(self,"db_field_vars"):self.db_field_vars={}
  if not hasattr(self,'db_attack_frames'):self.db_attack_frames={};self.db_attack_vars={}
  self.db_field_vars[kind]={}
  if not hasattr(self,'db_hue_vars'):self.db_hue_vars={}
  from content_database import TEMPLATES
  for i,(key,value) in enumerate((k,v) for k,v in TEMPLATES[kind].items() if (v is None or isinstance(v,(int,str))) and not (kind in ('enemy','boss','player') and k in ('max_hp','contact_damage')) and kind!='object' and not (kind=='item' and k in ('effect','use_damage'))):
   var=tk.StringVar();self.db_field_vars[kind][key]=var
   ttk.Label(fields,text=key.replace("_"," ").title()).grid(row=i//2,column=(i%2)*2,sticky="w",padx=5,pady=3)
   ttk.Entry(fields,textvariable=var,width=20).grid(row=i//2,column=(i%2)*2+1,sticky="ew",padx=5,pady=3)
  if kind in ('npc','boss'):
   # Dialogue voice (npc_voices): the game's own voice for this character, or a chosen one
   if not hasattr(self,'db_voice_vars'):self.db_voice_vars={}
   from npc_voices import CHOICES
   voice_bar=ttk.Frame(details);voice_bar.pack(fill='x',pady=(0,6))
   ttk.Label(voice_bar,text='Dialogue voice').pack(side='left')
   voice_var=tk.StringVar(value='Game default');self.db_voice_vars[kind]=voice_var
   ttk.Combobox(voice_bar,textvariable=voice_var,values=['Game default']+[label for _,label in CHOICES],state='readonly',width=24).pack(side='left',padx=6)
   voice_var.trace_add('write',lambda *_:self.db_schedule_autosave())
   if not hasattr(self,'db_voice_notes'):self.db_voice_notes={}
   self.db_voice_notes[kind]=tk.StringVar(value='');ttk.Label(voice_bar,textvariable=self.db_voice_notes[kind]).pack(side='left')
  if kind in ('npc','enemy','boss'):
   hue=ttk.LabelFrame(details,text='Colours (hue and saturation)',padding=6);hue.pack(fill='x',pady=3)
   var=tk.StringVar(value='0');self.db_hue_vars[kind]=var
   if not hasattr(self,'db_hue_previews'):self.db_hue_previews={}
   bar=ttk.Frame(hue);bar.pack(fill='x')
   ttk.Label(bar,text='Hue').pack(side='left')
   scale=ttk.Scale(bar,from_=-180,to=180,orient='horizontal',command=lambda value,v=var:v.set(str(round(float(value)))))
   scale.pack(side='left',fill='x',expand=True,padx=6)
   ttk.Spinbox(bar,textvariable=var,from_=-360,to=360,width=6).pack(side='left')
   ttk.Button(bar,text='Reset',command=lambda v=var:v.set('0')).pack(side='left',padx=(6,0))
   if not hasattr(self,'db_saturation_vars'):self.db_saturation_vars={};self.db_saturation_scales={}
   sat_var=tk.StringVar(value='100');self.db_saturation_vars[kind]=sat_var
   sat_bar=ttk.Frame(hue);sat_bar.pack(fill='x',pady=(4,0))
   ttk.Label(sat_bar,text='Saturation %').pack(side='left')
   sat_scale=ttk.Scale(sat_bar,from_=0,to=200,orient='horizontal',command=lambda value,v=sat_var:v.set(str(round(float(value)))))
   sat_scale.pack(side='left',fill='x',expand=True,padx=6);self.db_saturation_scales[kind]=sat_scale
   ttk.Spinbox(sat_bar,textvariable=sat_var,from_=0,to=200,increment=5,width=6).pack(side='left')
   ttk.Button(sat_bar,text='Reset',command=lambda v=sat_var:v.set('100')).pack(side='left',padx=(6,0))
   sat_var.trace_add('write',lambda *_,k=kind:(self.db_hue_schedule(k),self.db_schedule_autosave()))
   preview=tk.Canvas(hue,height=120,background='#171b22',highlightthickness=0);preview.pack(fill='x',pady=(6,0))
   self.db_hue_previews[kind]=(preview,scale)
   var.trace_add('write',lambda *_,k=kind:self.db_hue_schedule(k))
   preview.bind('<Configure>',lambda _,k=kind:self.db_hue_schedule(k))
  attacks=ttk.LabelFrame(details,text='Source attacks',padding=6);self.db_attack_frames[kind]=attacks
  if kind not in ('enemy','boss','weapon','player'):attacks.pack(fill='x',pady=4)
  advanced=ttk.Frame(details);advanced.pack(fill="both",expand=True)
  text=tk.Text(advanced,wrap="none",undo=True,height=9,background="#171b22",foreground="#e7eaf0",insertbackground="white")
  show=tk.BooleanVar(value=False)
  ttk.Checkbutton(advanced,text="Advanced source data",variable=show,command=lambda:text.pack(fill="both",expand=True) if show.get() else text.pack_forget()).pack(anchor="w")
  self.db_texts[kind]=text
  self.db_trees[kind]=tree
  # Database: Ctrl+C / Ctrl+V duplicates the selected class, Delete deletes it (asks first)
  tree.bind('<Control-c>',lambda _:setattr(self,'db_copied',self.db_selected_class() if tree.selection() else None))
  tree.bind('<Control-v>',lambda _:self.guard(self.db_paste_class))
 def _build_db_instances_tab(self,frame):
  body=ttk.Panedwindow(frame,orient="horizontal");body.pack(fill="both",expand=True,padx=8,pady=8)
  left=ttk.Frame(body);body.add(left,weight=2)
  filter_row=ttk.Frame(left,padding=(0,0,0,6));filter_row.pack(fill="x")
  ttk.Label(filter_row,text="Map filter").pack(side="left")
  self.db_instance_filter=tk.StringVar(value="All maps")
  filter_entry=ttk.Entry(filter_row,textvariable=self.db_instance_filter,width=10);filter_entry.pack(side="left",padx=5)
  ttk.Button(filter_row,text="Show",command=self.db_refresh).pack(side="left")
  ttk.Label(filter_row,text="Enter a map ID or All maps.").pack(side="left",padx=8)
  tree=ttk.Treeview(left,columns=("map","location","sprite","class"),show="headings",height=20)
  for key,title,width in [("map","Map",60),("location","In-game location",210),("sprite","Graphic",80),("class","Class",240)]:
   tree.heading(key,text=title);tree.column(key,width=width)
  tree.pack(fill="both",expand=True);tree.bind("<<TreeviewSelect>>",lambda e:self.db_instance_select())
  right=ttk.Frame(body,padding=10);body.add(right,weight=1)
  canvas=tk.Canvas(right,width=320,height=230,background="#11151b",highlightthickness=1,highlightbackground="#394352")
  canvas.pack(fill="x",pady=(0,10));canvas.create_text(160,115,text="Select a placed map instance",fill="#b8c2d2",tags=("placeholder",))
  self.db_preview_canvases["instances"]=canvas
  ttk.Label(right,text="Assign this instance to a shared class").pack(anchor="w")
  self.db_instance_class=tk.StringVar();self.db_class_combo=ttk.Combobox(right,textvariable=self.db_instance_class,state="readonly")
  self.db_class_combo.pack(fill="x",pady=5)
  ttk.Button(right,text="Link to class",command=lambda:self.guard(self.db_assign_instance)).pack(anchor="w")
  self.db_instance_label=tk.StringVar(value="All maps are indexed automatically when the database opens.")
  ttk.Label(right,textvariable=self.db_instance_label,wraplength=310,justify="left").pack(anchor="w",pady=10)
  self.db_instances_tree=tree
 def db_tab_changed(self,event=None):
  if not self.db_window or not self.db_tabs:return
  self.db_autosave()
  selected=self.db_tabs.select()
  if not selected:return
  label=self.db_tabs.tab(selected,"text").lower()
  for button in self.db_toolbar.winfo_children():
   if str(button.cget('text')).casefold() in ('new class','duplicate','delete','apply class','attacks','animations','frame boxes'):
    button.configure(state='disabled' if label=='sounds' else 'normal')
  if label=='sounds':return
  if label=='misc':label='unclassified'
  self.db_active_kind=label if label in KINDS else self.db_active_kind
  if self.db_active_kind in KINDS:self.db_kind.set(self.db_active_kind);self.db_select(self.db_active_kind)
 def db_refresh(self,select_id=None):
  from map_names import set_custom_names
  set_custom_names(self.database.document.setdefault('map_names',{}))
  from catalogue_names import refresh_database_names
  refresh_database_names(self.database)
  if hasattr(self.database,'ensure_meia_player'):self.database.ensure_meia_player()
  if hasattr(self.database,'ensure_alundra_npc'):self.database.ensure_alundra_npc()
  if hasattr(self.database,'ensure_kohei'):self.database.ensure_kohei()
  from enemy_clone import register_previews;register_previews(self.database.definitions)
  if hasattr(self.database,'retire_flush_switch'):self.database.retire_flush_switch()
  if hasattr(self.database,'ensure_side_rocks'):self.database.ensure_side_rocks()
  if hasattr(self.database,'ensure_heal_tiles'):self.database.ensure_heal_tiles()
  if hasattr(self.database,'ensure_pattern_plates'):self.database.ensure_pattern_plates()
  if hasattr(self.database,'ensure_floor_switch'):self.database.ensure_floor_switch()
  if hasattr(self.database,'ensure_warp_panel'):self.database.ensure_warp_panel()
  if hasattr(self.database,'ensure_save_portal'):self.database.ensure_save_portal()
  if hasattr(self.database,'ensure_block_switches'):self.database.ensure_block_switches()
  if hasattr(self.database,'ensure_sara_demons'):self.database.ensure_sara_demons()
  if hasattr(self.database,'ensure_npc_variants'):self.database.ensure_npc_variants()
  if hasattr(self.database,'ensure_color_blocks'):self.database.ensure_color_blocks()
  if hasattr(self.database,'ensure_nirude_statue_variants'):self.database.ensure_nirude_statue_variants()
  if hasattr(self.database,'ensure_pushable_stool'):self.database.ensure_pushable_stool()
  if hasattr(self.database,'ensure_talking_bosses'):self.database.ensure_talking_bosses()
  if hasattr(self.database,'ensure_sages'):self.database.ensure_sages()
  if hasattr(self.database,'ensure_drop_names'):self.database.ensure_drop_names()
  saved=self.database.document.get('mod_options',{})
  if saved.get('fast_loads'):saved['fast_loading']=True;saved.pop('fast_loads',None)   # merged 2026-10-16
  for key,var in getattr(self,'mod_option_vars',{}).items():
   var.set(saved.get(key,False))
  if hasattr(self,'meia_option_buttons'):self.update_meia_option_state()
  self.show_balance_state()
  if self.db_window is not None and self.db_window.winfo_exists():
   if hasattr(self,"db_sounds"):self.db_sounds.refresh()
   usage={}
   for instance in self.database.document["instances"]:
    cid=instance.get("class_id")
    if cid:usage[cid]=usage.get(cid,0)+1
   for kind,tree in self.db_trees.items():
    selected=tree.selection()[0] if tree.selection() else None;tree.delete(*tree.get_children())
    needle=self.db_search_vars[kind].get().strip().casefold() if hasattr(self,'db_search_vars') and kind in self.db_search_vars else ''
    from placement_catalogue import database_rows
    rows=[row for row in database_rows(self.database,kind) if not needle or needle in self.db_search_text(row)]
    if kind=='item':
     from item_categories import category_for,CATEGORIES
     rows.sort(key=lambda r:(CATEGORIES.index(category_for(r)),r['name'].casefold()))
    for row in rows:
     source=row.get("source",{});sprite=source.get("sprite_id",row.get("data",{}).get("source_sprite"))
     uses=usage.get(row["id"],0)
     tree.insert("","end",iid=row["id"],text=row['name'],values=(row['id'].split(':')[-1],)+((category_for(row),) if kind=="item" else ())+("—" if sprite is None else f"{sprite:02X}",uses))
    target=select_id if select_id in tree.get_children() else selected
    if target not in tree.get_children() and tree.get_children():target=tree.get_children()[0]
    if target in tree.get_children():tree.selection_set(target);tree.see(target)
   if self.db_instances_tree is not None:
    tree=self.db_instances_tree;selected=tree.selection()[0] if tree.selection() else None;tree.delete(*tree.get_children())
    definitions={row["id"]:row for row in self.database.definitions}
    filter_value=self.db_instance_filter.get().strip().lower() if hasattr(self,"db_instance_filter") else "all"
    for instance in self.database.document["instances"]:
     if filter_value not in ("","all"):
      try:filter_map=int(filter_value)
      except ValueError:continue
      if instance["map_id"]!=filter_map:continue
     source=instance["source"];cid=instance.get("class_id");row=definitions.get(cid)
     location=map_label(instance["map_id"])
     tree.insert("","end",iid=instance["id"],values=(instance["map_id"],location,f"{source['sprite_id']:02X}",row["name"] if row else "Unassigned"))
    if selected in tree.get_children():tree.selection_set(selected);tree.see(selected)
   values=[f"{row['name']} [{row['kind']}] — {row['id']}" for row in self.database.definitions]
   if self.db_class_combo is not None:self.db_class_combo.configure(values=values)
   if self.db_object_item_combo is not None:
    items=[row for row in self.database.definitions if row["kind"] in ('item','weapon','armor')]
    self.db_object_item_combo.configure(values=["No item"]+[f"{row['name']} — {row['id']}" for row in items])
  if hasattr(self,"animation_definition_combo"):self.animation_refresh()
 def db_filter_classes(self,kind):
  """Filter only the active class list, without rescanning every map instance."""
  tree=self.db_trees.get(kind)
  if tree is None:return
  selected=tree.selection()[0] if tree.selection() else None
  needle=self.db_search_vars[kind].get().strip().casefold();tree.delete(*tree.get_children())
  usage={}
  for instance in self.database.document['instances']:
   cid=instance.get('class_id');usage[cid]=usage.get(cid,0)+1
  from placement_catalogue import database_rows
  rows=database_rows(self.database,kind)
  if kind=='item':
   from item_categories import category_for,CATEGORIES
   rows=sorted(rows,key=lambda r:(CATEGORIES.index(category_for(r)),r['name'].casefold()))
  for row in rows:
   if needle not in self.db_search_text(row):continue
   sprite=row.get('source',{}).get('sprite_id',row.get('data',{}).get('source_sprite'))
   tree.insert('','end',iid=row['id'],text=row['name'],values=(row['id'].split(':')[-1],)+((category_for(row),) if kind=='item' else ())+('—' if sprite is None else f'{sprite:02X}',usage.get(row['id'],0)))
  children=tree.get_children();target=selected if selected in children else (children[0] if children else None)
  if target:tree.selection_set(target);tree.see(target)
 @staticmethod
 def db_search_text(row):
  return ' '.join([row['name'],row['id']]+[str(value) for value in row.get('source',{}).get('name_aliases',[])]).casefold()
 def db_select(self,kind=None):
  import time;self._db_activity=time.monotonic()   # pauses the background icon warm-up
  kind=kind or self.db_active_kind;tree=self.db_trees.get(kind);text=self.db_texts.get(kind)
  if tree is None or text is None:return
  if self.db_tabs.select()!=str(self.db_frames[kind]):return
  selected=tree.selection()
  if not selected:return
  row=self.database.get(selected[0]);self.db_kind.set(row["kind"])
  if kind in getattr(self,'db_voice_vars',{}):
   from npc_voices import CHOICES,default_voice
   chosen=row['data'].get('dialogue_voice');labels=dict(CHOICES);base=default_voice(row)
   self.db_voice_vars[kind].set(labels.get(chosen,'Game default') if chosen is not None else 'Game default')
   self.db_voice_notes[kind].set(f"Game default: {labels[base]}" if base is not None else "Game default: no voice set")
  if kind in getattr(self,'db_hue_vars',{}):self.db_hue_vars[kind].set(str(row['data'].get('palette_shift',{}).get('hue_degrees',0)))
  if kind in getattr(self,'db_saturation_vars',{}):self.db_saturation_vars[kind].set(str((row['data'].get('palette_shift') or {}).get('saturation_percent',100)))
  if kind in getattr(self,'db_speed_vars',{}):self.db_speed_vars[kind].set(str(row['data'].get('speed_percent',100)))
  if kind in getattr(self,'db_move_speed_vars',{}):self.db_move_speed_vars[kind].set(str(row['data'].get('move_speed_percent',100)))
  if kind in getattr(self,'db_hue_previews',{}):self.db_hue_schedule(kind)
  for key,var in self.db_field_vars.get(kind,{}).items():
   value=row["data"].get(key);var.set("" if value is None else str(value))
  if kind in getattr(self,'db_custom_settings',{}):
   # only values that differ from the class template count as custom ("Identify before use." is the default note, user 2026-10-27)
   from content_database import TEMPLATES
   template=TEMPLATES.get(kind,{})
   self.db_custom_settings[kind].set(any(var.get().strip() and var.get().strip()!=str(template.get(key) or '').strip() for key,var in self.db_field_vars.get(kind,{}).items()))
   self.db_custom_toggles[kind]()
  attacks=self.db_attack_frames[kind]
  for child in attacks.winfo_children():child.destroy()
  self.db_attack_vars[kind]=[]
  if kind in getattr(self,'db_combat_panels',{}):self.db_combat_panels[kind].load(self.db_combat_target(row))
  if kind=='unclassified' and kind in getattr(self,'db_spawn_panels',{}):
   panel=self.db_spawn_panels[kind]
   if row.get('kind') in ('enemy','boss'):panel.frame.pack(fill='x',pady=3);panel.load(row)
   else:panel.frame.pack_forget()
  elif kind in getattr(self,'db_spawn_panels',{}):self.db_spawn_panels[kind].load(row)
  if kind=='weapon' and hasattr(self,'db_weapon_panel'):self.db_weapon_panel.load(row)
  if kind=='armor' and hasattr(self,'db_armor_panel'):
   self.db_armor_panel.load(row);self.db_armor_row=row
   from armor_damage_ui import responses
   stock=responses({'data':{k:v for k,v in row['data'].items() if k!='damage_responses_raw'}})
   custom='damage_responses_raw' in row['data'] and row['data']['damage_responses_raw']!=stock
   self.db_custom_settings['armor'].set(custom);self.db_armor_refresh()
  if kind=='item' and hasattr(self,'db_accessory_panel'):self.db_accessory_panel.load(row)
  if kind in getattr(self,'db_text_vars',{}):
   stock=self.db_game_text_stock(row);own=row['data'].get('game_text') or {}
   for key,var in self.db_text_vars[kind].items():var.set(own.get(key,stock.get(key,'')))
  if kind=='item' and hasattr(self,'db_magic_frame'):
   import magic_spawns
   for child in self.db_magic_frame.winfo_children():child.destroy()
   self.db_magic_vars=[];self.db_magic_place_vars=[];self.db_magic_power_vars=[];self.db_magic_colour_vars=[];found=magic_spawns.sites(row);self.db_magic_like=None;own=row['source'].get('item_id')
   # any item Circle can use (31-50) shows these when its category is Magic, e.g. Herbs (user 2026-10-27)
   like_now=magic_spawns.behaves_like(row)
   if like_now not in magic_spawns.SITES:like_now=magic_spawns.DEFAULT_LIKE
   if own in magic_spawns.USABLE and not found:found=magic_spawns.SITES[like_now]
   if own in magic_spawns.USABLE:
    names={r['source'].get('item_id'):r['name'] for r in self.database.definitions if r.get('kind')=='item' and not r.get('clone_of')}
    like={f"{names.get(n,n)} ({n})":n for n in magic_spawns.SITES};self.db_magic_like=like
    top=ttk.Frame(self.db_magic_frame);top.pack(fill='x',pady=(0,6))
    ttk.Label(top,text='Behaves like').pack(side='left',padx=(0,8))
    var=tk.StringVar(value=next(k for k,v in like.items() if v==like_now));self.db_magic_like_var=var
    box=ttk.Combobox(top,textvariable=var,values=list(like),state='readonly',width=30);box.pack(side='left')
    box.bind('<<ComboboxSelected>>',lambda _:self.guard(lambda:(self.db_apply(quiet=True),self.db_select('item'))))
   if found:
    globals_=sorted({(r['source']['catalogue_index'],r['name']) for r in self.database.definitions if type(r.get('source',{}).get('catalogue_index')) is int and 0<=r['source']['catalogue_index']<magic_spawns.GLOBAL_SPRITES and not r.get('clone_of')})
    # The "at most 4 palettes" filter (for colour copies) is off: the colour change is set aside,
    # and counting every sprite's palettes made picking magic laggy (user 2026-10-27).
    labels={c:f'{n} ({c})' for c,n in globals_}
    for i,(address,stock,what) in enumerate(found):
     icon_label=ttk.Label(self.db_magic_frame,text=what,compound='left')
     spawn_box=ttk.LabelFrame(self.db_magic_frame,labelwidget=icon_label,padding=(6,2,6,4));spawn_box.pack(fill='x',pady=(0,6))
     lines=[ttk.Frame(spawn_box) for _ in range(4)]
     hidden=ttk.Frame(spawn_box)   # placement, tracking and Lasts: kept but not shown (user 2026-10-27)
     for n,line in enumerate(lines):
      if n==0:line.pack(fill='x')   # one line: class, Sprite, Power (lines 2-3 now empty)
     var=tk.StringVar(value=labels.get(magic_spawns.current(row,address,stock),str(stock)))
     def show_icon(*_,v=var,l=icon_label):   # mini picture of the spawned class
      value=v.get();n=int(value.rsplit('(',1)[1].rstrip(')')) if '(' in value else None
      self.db_icon_async(l,next((r for r in self.database.definitions if r.get('source',{}).get('catalogue_index')==n and not r.get('clone_of')),None))
     show_icon();var.trace_add('write',show_icon)
     ttk.Combobox(lines[0],textvariable=var,values=[labels[c] for c,_ in globals_],state='readonly',width=26).pack(side='left',padx=(0,4))
     var.trace_add('write',lambda *_:self.db_schedule_autosave());self.db_magic_vars.append((address,stock,var))
     # where it spawns (magic_placement)
     import magic_placement
     site=magic_placement.FOR_SPRITE[address];own=((row['data'].get('magic_placement') or {}).get(str(site)) or {})
     mode=tk.StringVar(value=magic_placement.MODES[own.get('mode',0)]);tiles=tk.StringVar(value=str(own.get('tiles',0)));rnd=tk.BooleanVar(value=bool(own.get('random')))
     ttk.Combobox(lines[1],textvariable=mode,values=magic_placement.MODES,state='readonly',width=18).pack(side='left',padx=(0,4))
     ttk.Spinbox(lines[1],from_=0,to=10,textvariable=tiles,width=4).pack(side='left',padx=(0,4))
     ttk.Label(lines[1],text='tiles').pack(side='left',padx=(0,4))
     ttk.Checkbutton(lines[1],text='Random spot',variable=rnd,command=self.db_schedule_autosave).pack(side='left',padx=(0,4))
     track=tk.StringVar(value=str(own.get('tracking',0)))
     ttk.Label(hidden,text='Enemy tracking').pack(side='left',padx=(0,4))
     ttk.Scale(hidden,from_=0,to=10,orient='horizontal',length=90,value=own.get('tracking',0),command=lambda v,t=track:t.set(str(round(float(v))))).pack(side='left',padx=(0,4))
     ttk.Label(hidden,textvariable=track,width=3).pack(side='left',padx=(0,4))
     life=tk.StringVar(value=str(own.get('frames',0)))
     ttk.Label(hidden,text='Lasts').pack(side='left',padx=(12,4))
     ttk.Spinbox(hidden,from_=0,to=9999,textvariable=life,width=6).pack(side='left',padx=(0,4))
     ttk.Label(hidden,text='frames').pack(side='left',padx=(0,4))
     for v in (mode,tiles,track,life):v.trace_add('write',lambda *_:self.db_schedule_autosave())
     # its graphics: another global class's sprite, keeping this class's behaviour and damage
     look_values=['Same as class']+[labels[c] for c,_ in globals_]
     look=tk.StringVar(value=labels.get(own.get('sprite'),'Same as class') if own.get('sprite') is not None else 'Same as class')
     ttk.Label(lines[0],text='Sprite').pack(side='left',padx=(12,4))
     ttk.Combobox(lines[0],textvariable=look,values=look_values,state='readonly',width=26).pack(side='left',padx=(0,4))
     look.trace_add('write',lambda *_:self.db_schedule_autosave())
     self.db_magic_place_vars.append((site,mode,tiles,rnd,track,life,look))
     # attack power of the spawned class (its tier-0 balance record; shared by everything that spawns it)
     cls=next((r for r in self.database.definitions if r.get('source',{}).get('catalogue_index')==magic_spawns.current(row,address,stock) and not r.get('clone_of')),None)
     spawn_attacks=(cls or {}).get('data',{}).get('attacks') or []
     if spawn_attacks:
      power=tk.StringVar(value=str(spawn_attacks[0].get('power',0)))
      ttk.Label(lines[0],text='Power').pack(side='left',padx=(12,4))   # beside Sprite (user 2026-10-27)
      ttk.Spinbox(lines[0],from_=0,to=255,textvariable=power,width=5).pack(side='left',padx=(0,4))
      power.trace_add('write',lambda *_:self.db_schedule_autosave())
      self.db_magic_power_vars.append((cls['id'],power))
     if cls is not None:
      # colour of what this item spawns: its own palette copies, the class keeps its colours elsewhere (magic_placement)
      hue=tk.StringVar(value=str(own.get('hue',0)));sat=tk.StringVar(value=str(own.get('saturation',100)))
      # Hue / Saturation boxes removed for now (user 2026-10-27); stored values are kept as they are
      self.db_magic_colour_vars.append((site,hue,sat))
  if kind=='player' and hasattr(self,'db_starting_panel'):self.db_starting_panel.load(row)
  if kind=='item' and hasattr(self,'db_item_panel'):self.db_item_panel.load(row)
  for i,attack in enumerate([] if kind in ('enemy','boss') else row['data'].get('attacks',[])):
   if not isinstance(attack,dict) or 'attribute' not in attack or 'power' not in attack:continue
   # an item's first record (Olga's / Oak's Ring) boosts Alundra's attack (user 2026-10-27)
   ttk.Label(attacks,text=('Attack boost' if kind=='item' else 'Contact Damage') if i==0 else f'Attack {i+1}').grid(row=i,column=0,padx=4)
   pair=[]
   from attack_attributes import attribute_box
   for j,key in enumerate(('attribute','power')):
    ttk.Label(attacks,text=key.title()).grid(row=i,column=1+j*2,padx=4)
    var=tk.StringVar(value=str(attack[key]));pair.append(var)
    if key=='attribute':attribute_box(attacks,var,attack[key]).grid(row=i,column=2,padx=4)
    else:ttk.Spinbox(attacks,from_=0,to=255,textvariable=var,width=6).grid(row=i,column=4,padx=4)
   self.db_attack_vars[kind].append(pair)
  if not self.db_attack_vars[kind]:ttk.Label(attacks,text='No decoded source attacks for this class').pack(anchor='w')
  self.db_class_name.set(row["name"]);self.db_class_id.set(row["id"])
  if kind=="object" and hasattr(self,"db_lifetime_row"):self.db_lifetime_load(row)
  if kind=='item' and hasattr(self,'db_heal_text'):
   import item_heals
   self.db_heal_text.set('' if item_heals.editable(row) else item_heals.heal_text(row))
   self.db_heal_label.pack_forget()
   if self.db_heal_text.get():self.db_heal_label.pack(anchor='w',pady=(0,2),after=self.db_heal_anchor)
   self.db_heal_frame.pack_forget();self.db_heal_part_row.pack_forget();self.db_heal_amount_row.pack_forget()
   if item_heals.editable(row):
    self.db_heal_frame.pack(fill='x',after=self.db_heal_anchor,pady=(0,4))
    value=item_heals.current(row)
    if value[0]=='amount':
     site=item_heals.SITES[item_heals.item_id(row)];self.db_heal_verb.set(site[4]);self.db_heal_unit.set(site[5])
     self.db_heal_amount.set(str(value[1]));self.db_heal_amount_row.pack(fill='x')
    else:
     self.db_heal_part.set(f'1/{value[0]}');self.db_heal_least.set(str(value[1]));self.db_heal_part_row.pack(fill='x')
     fixed=item_heals.SITES[item_heals.item_id(row)][2] is None
     self.db_heal_least_box.configure(state='disabled' if fixed else 'normal')
   self.db_heal_ok=item_heals.editable(row)
   acc=getattr(self,'db_accessory_panel',None);self.db_acc_ok=bool(acc and acc.raw is not None)
   c=(row.get('data') or {}).get('consume') or {}
   self.db_consume_ok=row['source'].get('item_id') in range(31,51)
   names={'none':'None','amount':'Amount','part':'Part of max','full':'Full'}
   self.db_cons_hp.set(names.get(c.get('hp','none'),'None'));self.db_cons_mp.set(names.get(c.get('mp','none'),'None'))
   self.db_cons_hp_value.set(str(c.get('hp_value',0) if c.get('hp')!='part' else 0));self.db_cons_hp_part.set(f"1/{c.get('hp_value',4)}" if c.get('hp')=='part' else '1/4')
   self.db_cons_hp_min.set(str(c.get('hp_min',0)));self.db_cons_mp_value.set(str(c.get('mp_value',0)));self.db_cons_revive.set(bool(c.get('revive')))
   g=(row.get('data') or {}).get('global_palette_shift') or {}
   self.db_item_hue.set(str(g.get('hue_degrees',0)));self.db_item_sat.set(str(g.get('saturation_percent',100)));self.db_item_colour_show()
   d=row.get('data') or {}
   if any(k in d for k in ('global_palette_shift','item_category','heal_divisor','heal_at_least','heal_amount','item_native_properties','magic_spawns','magic_behaves_like','magic_placement','consume')):
    self.db_custom_settings['item'].set(True);self.db_custom_toggles['item']()
   self.db_item_refresh()
  if kind in getattr(self,'db_hp_texts',{}):
   hp=(row.get('source',{}).get('native_data_baseline') or {}).get('max_hp')
   self.db_hp_texts[kind].set(f"Hit points: {hp}" if hp else "")
  if kind=="object":
   item_id=row["data"].get("contained_item_class_id")
   self.db_object_item.set(next((f"{item['name']} — {item['id']}" for item in self.database.definitions if item["id"]==item_id),"No item"))
   for key,var in self.db_object_type_vars.items():var.set(bool(row["data"].get(key,False)))
   for key,var in getattr(self,'db_object_state_vars',{}).items():var.set(bool(row['data'].get(key,False)))
   box=getattr(self,'db_while_pressured_box',None)
   if box is not None:
    if row.get('source',{}).get('catalogue_index')==301 or row.get('source',{}).get('variant')=='floor_switch':box.pack(side='left',padx=4)
    else:box.pack_forget()
   reactions=row["data"].get("reactions",{})
   for key,(activate,destroy) in self.db_object_reaction_vars.items():
    response=reactions.get(key,{})
    activate.set(bool(response.get("activate",False)));destroy.set(bool(response.get("destroy",False)))
   used=(row["data"].get("contained_item_class_id") or any(v.get() for v in self.db_object_type_vars.values())
         or any(v.get() for v in getattr(self,'db_object_state_vars',{}).values())
         or any(a.get() or d.get() for a,d in self.db_object_reaction_vars.values()))
   if hasattr(self,'db_object_custom'):
    self.db_object_custom.set(bool(used))
    if used:self.db_object_custom_body.pack(fill="x",pady=(4,0))
    else:self.db_object_custom_body.pack_forget()
  text.delete("1.0","end");text.insert("1.0",json.dumps(row,indent=2));self.db_show_preview(kind,row);self.db_show_preview(kind+":dialogue",row)
  text.edit_modified(False);self.db_loaded=(kind,row['id'])
 def db_show_preview(self,kind,row=None,instance=None):
  from entity_preview import EntityPreview
  slot="world"
  if kind.endswith(":dialogue"):
   kind=kind.split(":",1)[0];slot="dialogue"
  canvas=self.db_dialogue_preview_canvases.get(kind) if slot=="dialogue" else self.db_preview_canvases.get(kind)
  if canvas is None:return
  canvas.delete("all");width=max(canvas.winfo_width(),320);height=max(canvas.winfo_height(),210)
  if row and slot=='dialogue':
   from database_catalogue import portrait_image
   image=portrait_image(self.session,row)
   if image is not None:
    scale=max(1,min(6,int(min((width-20)/image.width,(height-40)/image.height))))
    photo=ImageTk.PhotoImage(image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST))
    canvas.create_image(width/2,height/2,image=photo);canvas.image=photo
    canvas.create_text(8,8,anchor='nw',text='Native dialogue portrait',fill='#d7e2f1');return
  if row and slot=='world':
   from database_catalogue import reference_image
   image=reference_image(self.session,row)
   if image is not None:
    scale=max(1,min(6,int(min((width-20)/image.width,(height-40)/image.height))))
    photo=ImageTk.PhotoImage(image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST))
    canvas.create_image(width/2,height/2,image=photo);canvas.image=photo
    canvas.create_text(8,8,anchor='nw',text=row['name'],fill='#d7e2f1');return
  if row and row["kind"] in ("item","weapon") and slot=="world":
   from database_catalogue import icon_path
   path=icon_path(row["name"])
   if path:
    with Image.open(path) as asset:image=asset.convert("RGBA")
    scale=max(1,min(6,int(min((width-20)/image.width,(height-40)/image.height))))
    photo=ImageTk.PhotoImage(image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST))
    canvas.create_image(width/2,height/2,image=photo);canvas.image=photo
    canvas.create_text(8,8,anchor="nw",text="Item reference graphic",fill="#d7e2f1");return
  source=(instance or {}).get("source",{}) if instance else (row or {}).get("source",{})
  from placement_catalogue import INVISIBLE_OBJECTS
  if (row or {}).get("source",{}).get("catalogue_index") in INVISIBLE_OBJECTS or source.get("catalogue_index") in INVISIBLE_OBJECTS:
   canvas.create_text(width/2,height/2,text="Invisible in game\nNo graphic",fill="#b8c2d2",justify="center");return
  sprite=source.get("sprite_id")
  if row is not None:
   data=row.get("data",{})
   if slot=="dialogue":sprite=data.get("dialogue_sprite")
   elif sprite is None:sprite=data.get("world_sprite",data.get("source_sprite",data.get("sprite_reference")))
  map_id=(instance or {}).get("map_id")
  if map_id is None and row is not None:
   map_id=row.get("data",{}).get("dialogue_sprite_map") if slot=="dialogue" else None
   map_ids=source.get("observed_maps",[])
   if source.get("observed_map") is not None:map_ids=[source["observed_map"]]
   if map_ids:map_id=map_ids[0]
   elif sprite is not None:
    use=next((x for x in self.database.document["instances"] if x["source"]["sprite_id"]==sprite),None)
    if use:map_id=use["map_id"]
  if self.session is None or sprite is None or map_id is None:
   note="No dialogue graphic linked" if slot=="dialogue" else "No source game graphic linked"
   canvas.create_text(width/2,height/2,text=f"{(row or {}).get('kind','Instance').title()}\n{note}",fill="#b8c2d2",justify="center")
   return
  try:
   image,left,top=EntityPreview(self.session,int(map_id)).frame(int(sprite))
   if image is None:raise ValueError("No supported frame")
   scale=max(1,min(6,int(min((width-20)/image.width,(height-20)/image.height))))
   shown=image.resize((image.width*scale,image.height*scale),Image.Resampling.NEAREST)
   photo=ImageTk.PhotoImage(shown);canvas.create_image(width/2,height/2,image=photo,anchor="center");canvas.image=photo
   canvas.create_text(8,8,anchor="nw",text=f"Map {map_id} · sprite {sprite:02X}",fill="#d7e2f1")
  except Exception as exc:
   canvas.create_text(width/2,height/2,text=f"Graphic unavailable\n{exc}",fill="#d7e2f1",width=width-30,justify="center")
 def db_add(self):
  from new_definition_ui import NewDefinitionWindow
  NewDefinitionWindow(self,self.db_kind.get())
 def db_selected_class(self):
  tree=self.db_trees.get(self.db_active_kind);selected=tree.selection() if tree else ()
  if not selected:raise ValueError("Select a class to continue")
  return selected[0]
 def db_frame_boxes(self):
  self.need()
  from frame_collision_ui import FrameCollisionWindow
  FrameCollisionWindow(self,self.database.get(self.db_selected_class()))
 def db_new_enemy(self):
  """A copy with its own class slot and own HP / attacks / resistances (enemy_clone)."""
  self.need();self.db_autosave()
  from enemy_clone import create_clone
  row=create_clone(self,self.database.get(self.db_selected_class()))
  self.db_refresh(row['id']);tree=self.db_trees.get(row['kind'])
  if tree is not None and tree.exists(row['id']):tree.selection_set(row['id']);tree.see(row['id'])
  self.status.set(f"{row['name']} created: its own enemy (slot {row['source']['own_slot']}) with its own HP, attacks and AI settings. Rename it and change its values freely.")
 def db_sprite_target(self,class_id=None):
  """The selected graphic: the class picked in the database (or the event selected on the map)."""
  self.need()
  if class_id is None:
   try:class_id=self.db_selected_class()
   except ValueError:
    sel=getattr(self.area,'selected_record',None) if self.area else None
    if sel and sel[0]=='graphs':
     g=self.database.document['event_graphs'][sel[1]];class_id=((g.get('pages') or [{}])[0].get('class_id') or g.get('class_id'))
    if class_id is None:raise ValueError('Select a class in the database (or an event with a graphic on the map) first')
  row=self.db_combat_target(self.database.get(class_id))
  if row.get('clone_of') and row.get('source',{}).get('catalogue_index') is None:
   row=dict(row,source=dict(self.database.get(row['clone_of']).get('source',{}),**row.get('source',{})))
  if row.get('source',{}).get('catalogue_index') is None:raise ValueError(f"{row['name']} has no game sprite to export")
  maps=list(row.get('source',{}).get('observed_maps',[]) or [])
  if self.current_map in maps:maps.remove(self.current_map);maps.insert(0,self.current_map)
  if not maps:maps=[self.current_map]
  return row,maps
 def db_export_sprites(self):
  from sprite_transfer_ui import open_sprite_transfer
  open_sprite_transfer(self,'export')
 def db_export_all_graphics(self):
  """Every map, tile set, door and sprite (named after the database classes) into
  assets/engine, from the current data so the remake plays your mod."""
  import threading
  from tkinter import messagebox
  self.need()
  if getattr(self,'_remake_export_running',False):self.status.set('The graphics export is already running.');return
  if not messagebox.askyesno('Export all graphics','Export every map, tile set, door and sprite (with class names) to assets/engine?\n\nThis uses your current edits and takes several minutes. You can keep working; avoid saving big changes until it finishes.',parent=self.db_window or self.root):return
  from engine_export_all import export_all,database_names
  names=database_names(self.database.document)
  self._remake_export_running=True
  def say(text):self.root.after(0,lambda t=text:self.status.set('Remake export: '+t))
  def work():
   try:
    done,failed=export_all(self.session,names,say)
    say(f'finished: {done} maps' + (f', {len(failed)} failed (assets/engine/export_failures.txt)' if failed else '') + '. Start the remake to play it.')
   except Exception as exc:
    say(f'stopped: {exc}')
   finally:
    self._remake_export_running=False
  threading.Thread(target=work,daemon=True).start()
 def db_import_sprites(self):
  from sprite_transfer_ui import open_sprite_transfer
  open_sprite_transfer(self,'import')
 def _db_lifetime(self,row):
  """(route steps, index of the remove step, frames waited before it) of a custom-AI object."""
  ai=(row.get('data') or {}).get('custom_ai') or {}
  if ai.get('mode')!='custom':return None
  steps=(ai.get('routes') or [{}])[0].get('steps') if ai.get('routes') else ai.get('route')
  steps=steps or []
  remove=next((i for i,st in enumerate(steps) if st.get('kind')=='remove'),None)
  frames=None if remove is None else sum(int(st.get('value',1)) for st in steps[:remove] if st.get('kind')=='wait')
  return steps,remove,frames
 def db_lifetime_load(self,row):
  info=self._db_lifetime(row)
  if info is None:self.db_lifetime_row.pack_forget();return
  self.db_lifetime_row.pack(fill='x',pady=(0,6),before=self.db_lifetime_anchor)
  self.db_destroy_wall.set(bool(row['data']['custom_ai'].get('destroy_on_wall',True)))
  if info[1] is None:self.db_lifetime_label.pack_forget();self.db_lifetime_button.pack_forget();return
  self.db_lifetime_text.set(f'Lasts {info[2]} frames')
  self.db_lifetime_label.pack(side='left');self.db_lifetime_button.pack(side='left',padx=6)
 def _db_change_ai(self,change):
  from copy import deepcopy
  definition_id=self.db_selected_class();row=deepcopy(self.database.get(definition_id))
  change(row['data']['custom_ai'])
  self.database.replace(definition_id,row);self.dirty=True;self.db_lifetime_load(self.database.get(definition_id))
 def db_set_destroy_wall(self):
  value=self.db_destroy_wall.get()
  self._db_change_ai(lambda ai:ai.__setitem__('destroy_on_wall',value))
 def db_edit_lifetime(self):
  from tkinter import simpledialog
  row=self.database.get(self.db_selected_class());steps,remove,frames=self._db_lifetime(row)
  value=simpledialog.askinteger('Lasts','Frames',initialvalue=frames,minvalue=1,maxvalue=6000,parent=self.db_window or self.root)
  if value is None:return
  def change(ai):
   steps=(ai.get('routes') or [{}])[0].get('steps') if ai.get('routes') else ai.get('route')
   remove=next(i for i,st in enumerate(steps) if st.get('kind')=='remove')
   waits=[i for i in range(remove) if steps[i].get('kind')=='wait']
   earlier=sum(int(steps[i].get('value',1)) for i in waits[:-1])   # earlier waits keep their timing
   if value-earlier<1:raise ValueError(f'The route already waits {earlier} frames before its last wait')
   if waits:steps[waits[-1]]['value']=value-earlier
   else:steps.insert(remove,{'kind':'wait','value':value})
   if ai.get('routes'):ai['route']=steps
  self._db_change_ai(change)
 def db_edit_ai(self):
  from ai_editor_ui import AIEditorWindow
  self.need();AIEditorWindow(self,self.database.get(self.db_selected_class()))
 def db_native_animations(self):
  self.need()
  from animation_preview_ui import AnimationPreviewWindow
  AnimationPreviewWindow(self,self.db_combat_target(self.database.get(self.db_selected_class())))   # Meia (Player): her NPC sprite's animations
 def open_project_state(self):
  from project_state_ui import ProjectStateWindow
  ProjectStateWindow(self)
 def starting_equipment(self):
  from starting_equipment_ui import StartingEquipmentWindow
  StartingEquipmentWindow(self)
 def database_source_exe(self):
  source=self.session
  if source is None:return None
  extra=getattr(source,'extra_files',{}).get('ALUN_CD.EXE')
  if extra is not None:return bytes(extra.data)
  if source.source_verified:return (ROOT/'game/disc/ALUN_CD.EXE').read_bytes()
  if source.path and source.path.suffix.lower()=='.bin':return read_datas(source.path,'ALUN_CD.EXE')
  return None
 def native_balance_session(self):
  from enemy_definition import BalanceSession
  self.need();extras=getattr(self.session,'extra_files',{})
  balance=extras.get('DATA/BALANCE.BIN')
  if balance is None:
   if self.session.source_verified:data=(ROOT/'game/disc/DATA/BALANCE.BIN').read_bytes()
   elif self.session.path and self.session.path.suffix.lower()=='.bin':data=read_datas(self.session.path,'DATA/BALANCE.BIN')
   else:raise ValueError('Open the source disc or a mod project with its companion BALANCE data')
   balance=BalanceSession(data,verify=self.session.source_verified);extras['DATA/BALANCE.BIN']=balance;self.session.extra_files=extras
   from jp_balance import balance_mode,switch_balance
   mode=balance_mode(self.database.document.get('mod_options'))
   if mode is not None:balance,_=switch_balance(extras,self.database,mode)
  return balance
 def show_balance_state(self):
  if not hasattr(self,'balance_state'):return
  from jp_balance import balance_mode
  mode=balance_mode(self.database.document.get('mod_options'))
  self.balance_state.set({'us':'Using: US balance','jp':'Using: JP balance'}.get(mode,"Using: this disc's own balance"))
 def set_balance(self,mode):
  """Apply US or JP balance to the mod (game data and database)."""
  if not self.set_jp_balance(mode):return
  options=self.database.document.setdefault('mod_options',{})
  options['balance']=mode;options['jp_balance']=mode=='jp'
  self.show_balance_state()
 def set_jp_balance(self,enable):
  """Switch the mod to JP (or back to the disc's own) balance; warn about edited stats."""
  from jp_balance import edited_entries,switch_balance
  balance=self.native_balance_session()
  edited=edited_entries(balance)
  if edited:
   names=[row['name'] for row in self.database.definitions if row.get('source',{}).get('balance_entry') in edited and not row.get('clone_of')]
   shown=', '.join(sorted(set(names))[:12])+(' …' if len(set(names))>12 else '')
   target={'us':'US balance','jp':'JP balance',True:'JP balance'}.get(enable,'the game\'s own balance')
  _,count=switch_balance(self.session.extra_files,self.database,enable)
  self.dirty=True;self.db_refresh()
  name={'us':'US','jp':'JP',True:'JP'}.get(enable)
  self.status.set((f'{name} balance applied' if name else 'Disc balance restored')+f': {count} classes changed stats.')
  return True
 def db_native_attacks(self):
  from attack_editor_ui import AttackEditorWindow
  AttackEditorWindow(self,self.database.get(self.db_selected_class()))
 def db_pick_palette(self,row):
  """Duplicate: choose the copy's colour first (user 2026-10-27). (hue, saturation), or None if cancelled."""
  old=(row.get('data') or {}).get('palette_shift') or {}
  win=tk.Toplevel(self.db_window or self.root);win.title(f"Duplicate {row['name']}");win.transient(self.db_window or self.root);win.resizable(False,False)
  body=ttk.Frame(win,padding=10);body.pack(fill='both')
  hue=tk.StringVar(value=str(old.get('hue_degrees',0)));sat=tk.StringVar(value=str(old.get('saturation_percent',100)))
  icons=ttk.Frame(body);icons.grid(row=0,column=0,columnspan=4,pady=(0,8))
  original=self.db_class_icon(row,size=48,shift=(0,100));before=ttk.Label(icons,image=original or '',text='Original',compound='top');before.pack(side='left',padx=8);before.image=original
  after=ttk.Label(icons,text='Copy',compound='top');after.pack(side='left',padx=8)
  def preview(*_):
   try:shift=(int(hue.get()),int(sat.get()))
   except ValueError:return
   icon=self.db_class_icon(row,size=48,shift=shift);after.configure(image=icon or '');after.image=icon
  ttk.Label(body,text='Hue').grid(row=1,column=0,sticky='w')
  ttk.Spinbox(body,from_=-180,to=180,increment=10,textvariable=hue,width=6).grid(row=1,column=1,sticky='w',padx=(4,12))
  ttk.Label(body,text='Saturation').grid(row=1,column=2,sticky='w')
  ttk.Spinbox(body,from_=0,to=200,increment=10,textvariable=sat,width=6).grid(row=1,column=3,sticky='w',padx=4)
  for v in (hue,sat):v.trace_add('write',preview)
  preview();result={}
  def ok():
   try:h,sa=int(hue.get()),int(sat.get())
   except ValueError:return
   if -180<=h<=180 and 0<=sa<=200:result['shift']=(h,sa);win.destroy()
  buttons=ttk.Frame(body);buttons.grid(row=2,column=0,columnspan=4,pady=(10,0),sticky='e')
  ttk.Button(buttons,text='Duplicate',command=ok).pack(side='left',padx=4);ttk.Button(buttons,text='Cancel',command=win.destroy).pack(side='left')
  win.bind('<Return>',lambda _:ok());win.bind('<Escape>',lambda _:win.destroy())
  self.db_palette_dialog=win;win.grab_set();win.wait_window()
  return result.get('shift')
 def db_duplicate(self):
  self.db_autosave()
  row=self.database.get(self.db_selected_class());src=row.get('source',{})
  shift=self.db_pick_palette(row)
  if shift is None:return
  # Enemies, bosses and NPCs: Duplicate makes its own separate class (own slot, HP, attacks).
  if row['kind'] in ('enemy','boss','npc','object') and type(src.get('catalogue_index')) is int and src['catalogue_index']>=256 and type(src.get('balance_entry')) is int:
   self.db_new_enemy()
   new=self.database.get(self.db_selected_class())
  else:
   new=self.database.duplicate(self.db_selected_class())
  from copy import deepcopy
  new=deepcopy(new);new.setdefault('data',{})['palette_shift']={'hue_degrees':shift[0],'saturation_percent':shift[1]}
  self.database.replace(new['id'],new);self.db_refresh(new["id"])
  tree=self.db_trees.get(new["kind"])
  if tree:tree.selection_set(new["id"]);self.db_select(new["kind"])
 def db_paste_class(self):
  copied=getattr(self,'db_copied',None)
  if not copied:raise ValueError('Copy a class first (Ctrl+C)')
  tree=self.db_trees.get(self.db_active_kind)
  if tree is not None and tree.exists(copied):tree.selection_set(copied)
  self.db_duplicate()
 def db_delete_key(self):
  from tkinter import messagebox
  row=self.database.get(self.db_selected_class())
  if messagebox.askyesno('Delete',f"Delete {row['name']}?",parent=self.db_window or self.root):self.db_delete()
 def db_delete(self):
  definition_id=self.db_selected_class();self.database.delete(definition_id);self.db_refresh()
 def db_scan_map(self):
  self.need();rows=self.database.discover_map_sprites(self.session.data,self.current_map);self.database.scan_instances(self.session.data);self.db_refresh(rows[-1]["id"] if rows else None)
  self.status.set(f"Indexed {len(self.database.document['instances'])} map instances. Added {len(rows)} unclassified graphic classes.")
 def db_scan_all(self):
  self.need();before=len(self.database.definitions);self.populate_database_from_game();added=len(self.database.definitions)-before;instances=self.database.document["instances"];self.db_refresh()
  self.status.set(f"Indexed {len(instances)} map instances across all maps; added {added} source-backed definitions when available. Unidentified map graphics stay unclassified.")
  if added and self.db_window is not None and self.db_window.winfo_exists():
   self.db_tabs.select(self.db_frames["unclassified"]);self.db_active_kind="unclassified";self.db_kind.set("unclassified")
 def db_import_balance(self):
  self.need();extra=getattr(self.session,"extra_files",{}).get("DATA/BALANCE.BIN")
  if extra is not None:data=bytes(extra.data)
  elif self.session.source_verified:data=(ROOT/"game/disc/DATA/BALANCE.BIN").read_bytes()
  elif self.session.path and self.session.path.suffix.lower()==".bin":data=read_datas(self.session.path,"DATA/BALANCE.BIN")
  else:raise ValueError("Open the exact modded disc BIN to import its BALANCE.BIN; this DATAS file alone does not identify its companion balance data.")
  rows=self.database.import_balance_table(data);self.db_refresh(rows[-1]["id"] if rows else None)
  self.status.set(f"Imported {len(rows)} balance classes and their source tiers. Unknown damage fields remain labelled raw.")
 def db_hue_schedule(self,kind):
  jobs=self.__dict__.setdefault('db_hue_jobs',{})
  if jobs.get(kind):self.root.after_cancel(jobs[kind])
  jobs[kind]=self.root.after(60,lambda:self.guard(lambda:self.db_hue_preview(kind)))
 def db_hue_preview(self,kind):
  """Draw the selected class before/after the hue rotation (preview only)."""
  self.__dict__.setdefault('db_hue_jobs',{})[kind]=None
  canvas,scale=self.db_hue_previews.get(kind,(None,None))
  if canvas is None or not canvas.winfo_exists():return
  try:
   degrees=int(self.db_hue_vars[kind].get())
   saturation=int(self.db_saturation_vars[kind].get()) if kind in getattr(self,'db_saturation_vars',{}) else 100
  except ValueError:return
  saturation=max(0,min(200,saturation))
  sat_scale=getattr(self,'db_saturation_scales',{}).get(kind)
  if sat_scale is not None and round(float(sat_scale.get()))!=saturation:sat_scale.set(saturation)
  shift={'hue_degrees':degrees,'saturation_percent':saturation}
  if -180<=degrees<=180 and round(float(scale.get()))!=degrees:scale.set(degrees)
  canvas.delete('all');width=max(240,canvas.winfo_width())
  tree=self.db_trees.get(kind);selected=tree.selection() if tree is not None else ()
  if not selected or self.session is None:return
  from database_catalogue import reference_image,preview_hue
  from PIL import Image,ImageTk
  row=self.database.get(selected[0])
  # The main class preview follows the hue setting live (before autosave).
  self.db_show_preview(kind,dict(row,data=dict(row.get('data',{}),palette_shift=shift)))
  base=reference_image(self.session,dict(row,data=dict(row.get('data',{}),palette_shift={'hue_degrees':0})))
  if base is None:canvas.create_text(width/2,60,text='No sprite preview for this class',fill='#8c99ab');return
  after=preview_hue(base,{'data':{'palette_shift':shift}})
  scale_factor=max(1,min(4,int(96/max(1,base.height)),int((width/2-30)/max(1,base.width))))
  photos=self.__dict__.setdefault('db_hue_photos',{});photos[kind]=[]
  for x,label,image in ((width*0.25,'Original',base),(width*0.75,f'{degrees:+d}\u00b0 · {saturation}%',after)):
   photo=ImageTk.PhotoImage(image.resize((image.width*scale_factor,image.height*scale_factor),Image.Resampling.NEAREST),master=self.root)
   photos[kind].append(photo);canvas.create_image(x,104,image=photo,anchor='s')
   canvas.create_text(x,112,text=label,fill='#b8c2d2',font=('Segoe UI',9))
 def db_autosave(self):
  """Remember edits to the class on screen (no Apply button needed)."""
  job=getattr(self,'db_autosave_job',None)
  if job:
   try:self.root.after_cancel(job)
   except Exception:pass
  self.db_autosave_job=None
  loaded=getattr(self,'db_loaded',None)
  if not loaded or getattr(self,'db_autosaving',False):return
  if not self.db_window or not self.db_window.winfo_exists() or loaded[0]!=self.db_active_kind:return
  try:self.database.get(loaded[1])
  except ValueError:self.db_loaded=None;return
  self.db_autosaving=True
  try:self.db_apply(quiet=True)
  except (ValueError,TypeError,KeyError) as exc:self.status.set(f'Not saved yet: {exc}')
  finally:self.db_autosaving=False
 def db_schedule_autosave(self,event=None):
  if not self.db_window or not self.db_window.winfo_exists():return
  job=getattr(self,'db_autosave_job',None)
  if job:self.root.after_cancel(job)
  self.db_autosave_job=self.root.after(800,self.db_autosave)
 def class_definition_changed(self,db,definition_id):
  """A Database class changed: its placed events are instances, so the map and
  an open event editor show the class's current values (coalesced, after idle)."""
  if db is not self.database and db.document.get('definitions') is not self.database.document.get('definitions'):return
  self.__dict__.pop('spawn_panel_cache',None)   # a class changed: spawned-attack results are read again
  if getattr(self,'_class_redraw_job',None):return
  def run():
   self._class_redraw_job=None
   self.refresh_placed_events()
  try:self._class_redraw_job=self.root.after_idle(run)
  except Exception:self._class_redraw_job=None;self.refresh_placed_events()
 def refresh_placed_events(self):
  area=getattr(self,'area',None)
  if area is not None:
   area.authored_preview_cache={}
   if self.session is not None and getattr(self,'current_map',None) is not None and hasattr(area,'info'):
    try:area.draw_records()
    except Exception:pass
  window=getattr(self,'event_graph_window',None)
  if window is not None:
   try:window.classes_changed()
   except Exception:pass
 def db_icon_async(self,label,row,size=24,shift=None,then=None):
  """Show a class icon on label without blocking: one shared background thread decodes
  the picture (db_icon_image), then the Tk thread makes the small icon (user 2026-10-27)."""
  label.icon_row=row
  blank=getattr(label,'placeholder','')   # keeps the line's size while/without an icon
  if row is None or self.session is None:
   label.configure(image=blank);label.image=None
   if then:then(None)
   return
  def show():
   try:
    if getattr(label,'icon_row',None) is row and label.winfo_exists():
     icon=self.db_class_icon(row,size=size,shift=shift);label.configure(image=icon or blank);label.image=icon
     if then:then(icon)
   except Exception:pass
  if self.db_icon_cached(row,size,shift) or self.db_icon_image_ready(row):show();return   # already decoded: no wait, no flicker
  self.db_background(lambda:self.db_icon_image(row),lambda _:show())
 def db_background(self,work,done):
  """Run work() on the editor's one picture thread, then done(result) on the Tk thread (FIFO)."""
  import threading,collections
  if not hasattr(self,'db_icon_jobs'):self.db_icon_jobs=collections.deque();self.db_icon_done=collections.deque();self.db_icon_lock=threading.Lock()
  self.db_icon_jobs.append((work,done))
  with self.db_icon_lock:
   if getattr(self,'db_icon_thread',None) is None or not self.db_icon_thread.is_alive():
    def run():
     import time
     while True:
      try:job,then=self.db_icon_jobs.popleft()
      except IndexError:
       # warm-up: only while nothing is waiting and you have not browsed for 3 s,
       # so it never competes with switching classes (lag, user 2026-10-27)
       if not getattr(self,'db_icon_idle',None):break
       if time.monotonic()-getattr(self,'_db_activity',0)<3:time.sleep(0.25);continue
       try:job,then=self.db_icon_idle.popleft()
       except IndexError:break
       time.sleep(0.05)
      try:result=job()
      except Exception:result=None
      if then is not None:self.db_icon_done.append((then,result))
    self.db_icon_thread=threading.Thread(target=run,daemon=True,name='class-icons');self.db_icon_thread.start()
  if not getattr(self,'db_icon_polling',False):
   self.db_icon_polling=True
   def poll():   # Tk is only touched here, on its own thread
    while self.db_icon_done:
     then,result=self.db_icon_done.popleft()
     try:then(result)
     except Exception:pass
    if self.db_icon_jobs or self.db_icon_done or self.db_icon_thread.is_alive():self.root.after(30,poll)
    else:self.db_icon_polling=False
   self.root.after(30,poll)
 def db_magic_palette_counts(self):
  """Palettes used by each global sprite (for the magic Sprite lists). Was 151 copies of the
  whole game data on the first magic item (laggy, user 2026-10-27): now one read of the bank,
  kept on disk per game data."""
  import json,asset_cache,global_sprite_recolor,magic_spawns
  d=asset_cache.folder(getattr(self,'cache_digest',None));path=d/'palette_counts.json' if d else None
  try:return {int(k):v for k,v in json.loads(path.read_text()).items()}
  except Exception:pass
  try:
   bank=global_sprite_recolor._bank(bytes(self.session.data));counts={}
   for n in range(magic_spawns.GLOBAL_SPRITES):
    bank.used=set()
    for direction in range(8):bank.fullest_frame(n,direction)
    counts[n]=len(bank.used)
  except Exception:return {}
  if path is not None:
   try:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(counts))
   except OSError:pass
  return counts
 def db_warm_cache(self):
  """Decode every class picture in the background (low priority), so the Database
  and spawned-attack icons show at once; kept on disk per game data (user 2026-10-27)."""
  import collections
  if self.session is None:return
  rows=[r for r in self.database.definitions if r.get('kind') not in ('item','weapon','armor')]
  self.db_icon_idle=collections.deque((lambda r=r:self.db_icon_image(r),None) for r in rows)
  self.db_background(lambda:None,lambda _:None)   # wakes the picture thread
 def db_icon_image_ready(self,row):
  key=(id(self.session),row['id'],repr(row.get('source')),repr(row.get('data',{}).get('palette_shift')))
  return key in self.__dict__.get('db_icon_images',{})
 def db_icon_cached(self,row,size=24,shift=None):
  if shift is None:
   g=row.get('data',{}).get('global_palette_shift') or {};shift=(g.get('hue_degrees',0),g.get('saturation_percent',100))
  return (row['id'],size,tuple(shift)) in self.__dict__.get('db_icon_cache',{})
 def db_icon_image(self,row):
  """The class picture, cropped (no Tk: safe on a background thread); cached per class source."""
  cache=self.__dict__.setdefault('db_icon_images',{})
  key=(id(self.session),row['id'],repr(row.get('source')),repr(row.get('data',{}).get('palette_shift')))
  if key in cache:return cache[key]
  import asset_cache
  hit,image=asset_cache.load_icon(getattr(self,'cache_digest',None),row)
  if hit:cache[key]=image;return image
  from_disk=False
  try:
   from database_catalogue import reference_image
   image=reference_image(self.session,row)
   if image is None:
    from entity_preview import EntityPreview
    source=row.get('source',{});sprite=source.get('sprite_id',source.get('catalogue_index'))
    maps=source.get('observed_maps') or ([source['observed_map']] if source.get('observed_map') is not None else [1])
    if sprite is not None:image=EntityPreview(self.session,int(maps[0])).frame(int(sprite))[0]
  except Exception:image=None
  if image is not None:
   image=image.convert('RGBA');bbox=image.getbbox()
   if bbox:image=image.crop(bbox)
  cache[key]=image
  if from_disk is False:asset_cache.save_icon(getattr(self,'cache_digest',None),row,image)
  return image
 def db_class_icon(self,row,size=24,shift=None):
  """A small picture of a class (its reference graphic or first sprite frame), cached; None without one.
  shift (hue degrees, saturation %) recolours it; by default its global colour setting."""
  if row is None or self.session is None:return None
  if shift is None:
   g=row.get('data',{}).get('global_palette_shift') or {};shift=(g.get('hue_degrees',0),g.get('saturation_percent',100))
  cache=self.__dict__.setdefault('db_icon_cache',{});key=(row['id'],size,tuple(shift))
  if key in cache:return cache[key]
  image=self.db_icon_image(row)
  icon=None
  if image is not None:
   scale=min(size/image.width,size/image.height)
   image=image.resize((max(1,round(image.width*scale)),max(1,round(image.height*scale))),Image.Resampling.NEAREST)
   if tuple(shift)!=(0,100):image=_shift_colour(image,*shift)
   icon=ImageTk.PhotoImage(image,master=self.root)
  cache[key]=icon;return icon
 def db_game_text_stock(self,row):
  import item_text
  if not getattr(self,'db_etc_raw',None):   # looked for again until found
   path=ROOT/'game/disc'/item_text.NAME
   self.db_etc_raw=path.read_bytes() if path.is_file() else None
  stock=item_text.stock(self.db_etc_raw,row) if self.db_etc_raw else {}
  # The game file still holds the drops' old text names (Dew of Life...); that file is not changed here:
  # the Name box shows the drop's own name (Small Life Drop...) (user 2026-10-27)
  pair=ContentDatabase.DROP_NAMES.get(row.get('source',{}).get('catalogue_index'))
  if pair and stock.get('name')==pair[0]:stock=dict(stock,name=pair[1])
  return stock
 def db_armor_refresh(self,toggled=False):
  if not hasattr(self,'db_armor_anchor'):return
  on=self.db_custom_settings['armor'].get();panel=self.db_armor_panel
  if toggled and not on and getattr(self,'db_armor_row',None):   # back to the game's values
   panel.load({**self.db_armor_row,'data':{k:v for k,v in self.db_armor_row['data'].items() if k!='damage_responses_raw'}})
  self.db_armor_fields.pack_forget();panel.frame.pack_forget();panel.frame.pack(fill='x',pady=(0,6),after=self.db_armor_anchor)
  for c in panel.host.winfo_children():
   if not isinstance(c,ttk.Label) and not (c.cget('state')=='disabled' and on and 'unchanged' in str(c.get() if hasattr(c,'get') else '')):
    try:c.configure(state='normal' if on else 'disabled')
    except tk.TclError:pass
 def db_item_refresh(self):
  # item custom settings: category first, then the fields that category uses (user 2026-10-26)
  if not hasattr(self,'db_item_anchor'):return
  on=self.db_custom_settings['item'].get();panel=self.db_item_panel;last=self.db_item_anchor
  # off: the item's own category and values, read-only; on: the custom ones take over (user 2026-10-26)
  if not on and panel.loaded is not None:
   from item_categories import category_for
   default=category_for({k:v for k,v in panel.loaded.items() if k!='data'})
   if panel.category.get()!=default:panel.category.set(default);return
   import item_heals
   site=item_heals.SITES.get(item_heals.item_id(panel.loaded)) if getattr(self,'db_heal_ok',False) else None   # flag can be the last item's
   if site:
    if site[0]=='amount':self.db_heal_amount.set(str(site[2]))
    else:self.db_heal_part.set(f'1/{1<<site[1]}');self.db_heal_least.set(str(site[4]))
   for k,v in getattr(panel,'native_baseline',{}).items():
    var={'menu_group':panel.menu_group,'priority':panel.priority,'max_quantity':panel.maximum}.get(k)
    if var is not None:var.set(str(v))
  category=panel.category.get()
  # only shown while Custom settings is ticked (user 2026-10-27)
  shown=[(self.db_item_colour_frame,False),   # item Colour box hidden (user 2026-10-27)
         (self.db_consume_frame,on and category=='Consume' and getattr(self,'db_consume_ok',False)),
         (self.db_heal_frame,on and getattr(self,'db_heal_ok',False) and category=='Consume' and not getattr(self,'db_consume_ok',False))]
  shown.append((self.db_magic_frame,on and category=='Magic' and bool(getattr(self,'db_magic_like',None))))
  acc=getattr(self,'db_accessory_panel',None)
  if acc:shown.append((acc.frame,on and getattr(self,'db_acc_ok',False) and category=='Accessory'))
  shown.append((panel.frame,on))   # category and menu properties below the category's own settings (user 2026-10-27)
  for frame,show in shown:
   frame.pack_forget()
   if show:frame.pack(fill='x',pady=(0,6),after=last);last=frame
  self.db_item_fields.pack_forget()
  def state(w):
   for c in w.winfo_children():
    if isinstance(c,(ttk.Label,ttk.LabelFrame,ttk.Frame)):state(c);continue
    try:c.configure(state=('readonly' if isinstance(c,ttk.Combobox) else 'normal') if on else 'disabled')
    except tk.TclError:pass
    state(c)
  for frame,_ in shown:state(frame)
  self.db_disable_tree=state
  if on and not panel.native_enabled:
   for w in panel.widgets:w.configure(state='disabled')
  if on and getattr(self,'db_heal_ok',False) and self.db_heal_least_box.cget('state')!='disabled':
   import item_heals
   if item_heals.SITES.get(item_heals.item_id(panel.loaded),(0,0,0))[2] is None:self.db_heal_least_box.configure(state='disabled')
 def db_apply(self,quiet=False):
  if quiet:definition_id=self.db_loaded[1]
  else:definition_id=self.db_selected_class()
  text=self.db_texts[self.db_active_kind]
  from copy import deepcopy as _copy
  before=(_copy(self.database.get(definition_id)),_copy(self.database.document.get('mod_options',{})))
  # Start from the stored class unless its JSON text was edited, so edits made in
  # the Attacks / Animations / Frame boxes windows are never overwritten.
  if not text.edit_modified():row=_copy(self.database.get(definition_id))
  else:
   try:row=json.loads(text.get("1.0","end"))
   except json.JSONDecodeError as exc:raise ValueError(f"Class JSON has an error on line {exc.lineno}: {exc.msg}")
  row["name"]=self.db_class_name.get().strip()
  if row['name']!=self.database.get(definition_id)['name']:row.setdefault('source',{})['user_named']=True
  if self.db_active_kind=='item' and hasattr(self,'db_heal_text'):
   import item_heals
   if item_heals.editable(row):
    site=item_heals.SITES[item_heals.item_id(row)]
    for k in ('heal_divisor','heal_at_least','heal_amount'):row['data'].pop(k,None)
    if site[0]=='amount':
     try:amount=int(self.db_heal_amount.get())
     except ValueError:raise ValueError('Heal amount must be a whole number')
     if not 1<=amount<=999:raise ValueError('Heal amount must be 1-999')
     if amount!=site[2]:row['data']['heal_amount']=amount
    else:
     divisor=int(self.db_heal_part.get().split('/')[1])
     if divisor!=1<<site[1]:row['data']['heal_divisor']=divisor
     if site[2] is not None:
      try:least=int(self.db_heal_least.get())
      except ValueError:raise ValueError('Minimum heal must be a whole number')
      if not 0<=least<=999:raise ValueError('Minimum heal must be 0-999')
      if least!=site[4]:row['data']['heal_at_least']=least
  if self.db_active_kind in getattr(self,'db_voice_vars',{}):
   from npc_voices import CHOICES
   chosen=next((value for value,label in CHOICES if label==self.db_voice_vars[self.db_active_kind].get()),None)
   if chosen is None:row['data'].pop('dialogue_voice',None)
   else:row['data']['dialogue_voice']=chosen
  if self.db_active_kind in getattr(self,'db_hue_vars',{}):
   degrees=int(self.db_hue_vars[self.db_active_kind].get())
   if not -360<=degrees<=360:raise ValueError('Hue rotation must be between -360 and 360 degrees')
   row['data']['palette_shift']={'hue_degrees':degrees}
   if self.db_active_kind in getattr(self,'db_saturation_vars',{}):
    saturation=int(self.db_saturation_vars[self.db_active_kind].get() or 100)
    if not 0<=saturation<=200:raise ValueError('Saturation must be between 0 and 200 percent')
    if saturation!=100:row['data']['palette_shift']['saturation_percent']=saturation
  if self.db_active_kind in getattr(self,'db_speed_vars',{}):
   speed=int(self.db_speed_vars[self.db_active_kind].get() or 100)
   if not 25<=speed<=500:raise ValueError('Speed must be between 25 and 500 percent')
   if speed!=100:row['data']['speed_percent']=speed
   else:row['data'].pop('speed_percent',None)
  if self.db_active_kind in getattr(self,'db_move_speed_vars',{}):
   move=int(self.db_move_speed_vars[self.db_active_kind].get() or 100)
   if not 25<=move<=500:raise ValueError('Movement speed must be between 25 and 500 percent')
   if move!=100:row['data']['move_speed_percent']=move
   else:row['data'].pop('move_speed_percent',None)
  from content_database import TEMPLATES
  for key,var in self.db_field_vars.get(self.db_active_kind,{}).items():
   value=var.get().strip()
   row["data"][key]=value if isinstance(TEMPLATES[self.db_active_kind].get(key),str) else (int(value,0) if value else None)
  if not row["name"]:raise ValueError("Class name cannot be empty")
  if self.db_attack_vars.get(self.db_active_kind):
   row['data']['attacks']=[dict(attribute=parse_attribute(a.get()),power=int(p.get(),0)) for a,p in self.db_attack_vars[self.db_active_kind]]
  if self.db_active_kind in getattr(self,'db_combat_panels',{}):
   target=self.db_combat_target(row)
   if target.get('id')==row.get('id'):row=self.db_combat_panels[self.db_active_kind].apply(row)
   else:
    # Meia's Player entry edits her NPC class's native record.
    updated=self.db_combat_panels[self.db_active_kind].apply(_copy(target))
    if updated!=target:
     self.database.replace(target['id'],updated)
     try:balance=self.native_balance_session()
     except (ValueError,OSError,StopIteration):balance=None
     if balance is not None:
      from database_balance import apply_definition_balance,sync_balance_aliases
      if apply_definition_balance(balance,updated):sync_balance_aliases(self.database,balance,updated['source']['balance_entry'])
     self.dirty=True
  spawned_damage={}
  if self.db_active_kind in getattr(self,'db_spawn_panels',{}) and (self.db_active_kind!='unclassified' or row.get('kind') in ('enemy','boss')):
   row=self.db_spawn_panels[self.db_active_kind].apply(row);spawned_damage=self.db_spawn_panels[self.db_active_kind].damage_edits()
  if row["kind"]=="object":
   display=self.db_object_item.get()
   row["data"]["contained_item_class_id"]=display.rsplit(" — ",1)[-1] if display!="No item" and " — " in display else None
   for key,var in self.db_object_type_vars.items():row["data"][key]=var.get()
   for key,var in getattr(self,'db_object_state_vars',{}).items():row['data'][key]=var.get()
   row["data"]["reactions"]={key:{"activate":activate.get(),"destroy":destroy.get()} for key,(activate,destroy) in self.db_object_reaction_vars.items()}
  if self.db_active_kind=='item' and hasattr(self,'db_item_panel'):row=self.db_item_panel.apply(row) if self.db_custom_settings['item'].get() else row
  if self.db_active_kind=='item' and hasattr(self,'db_item_panel') and not self.db_custom_settings['item'].get():
   for k in ('item_category','item_category_basis','item_native_properties','global_palette_shift','magic_spawns','magic_behaves_like','magic_placement','consume'):row['data'].pop(k,None)
  if self.db_active_kind=='item' and hasattr(self,'db_cons_hp'):
   row['data'].pop('consume',None)
   if self.db_custom_settings['item'].get() and self.db_item_panel.category.get()=='Consume' and row['source'].get('item_id') in range(31,51):
    keys={'None':'none','Amount':'amount','Part of max':'part','Full':'full'}
    hp,mp=keys[self.db_cons_hp.get()],keys[self.db_cons_mp.get()]
    try:
     hv=int(self.db_cons_hp_part.get().split('/')[1]) if hp=='part' else int(self.db_cons_hp_value.get() or 0)
     hmin,mv=int(self.db_cons_hp_min.get() or 0),int(self.db_cons_mp_value.get() or 0)
    except ValueError:raise ValueError('HP and MP values must be whole numbers')
    if not 0<=hv<=999 or not 0<=hmin<=999 or not 0<=mv<=255:raise ValueError('HP values are 0-999, MP 0-255')
    if hp!='none' or mp!='none' or self.db_cons_revive.get():
     row['data']['consume']=dict(hp=hp,hp_value=hv,hp_min=hmin,mp=mp,mp_value=mv,revive=bool(self.db_cons_revive.get()))
  if self.db_active_kind=='item' and hasattr(self,'db_item_hue') and self.db_custom_settings['item'].get():
   try:h,sa=int(self.db_item_hue.get()),int(self.db_item_sat.get())
   except ValueError:raise ValueError('Hue and saturation must be whole numbers')
   if not -180<=h<=180 or not 0<=sa<=200:raise ValueError('Hue is -180 to 180, saturation 0 to 200')
   if (h,sa)==(0,100):row['data'].pop('global_palette_shift',None)
   else:row['data']['global_palette_shift']={'hue_degrees':h,'saturation_percent':sa}
  if self.db_active_kind in getattr(self,'db_text_vars',{}):
   stock=self.db_game_text_stock(row);row['data'].pop('game_text',None)
   game_text={key:var.get() for key,var in self.db_text_vars[self.db_active_kind].items() if var.get()!=stock.get(key,'')}
   if game_text and stock:row['data']['game_text']=game_text
  if self.db_active_kind=='armor' and hasattr(self,'db_armor_panel'):
   if self.db_custom_settings['armor'].get():row=self.db_armor_panel.apply(row)
   else:row['data'].pop('damage_responses_raw',None)
  if self.db_active_kind=='item' and hasattr(self,'db_accessory_panel'):row=self.db_accessory_panel.apply(row)
  if self.db_active_kind=='item' and getattr(self,'db_magic_vars',None):
   chosen={}
   for address,stock,var in self.db_magic_vars:
    value=var.get();n=int(value.rsplit('(',1)[1].rstrip(')')) if '(' in value else int(value)
    if n!=stock:chosen[str(address)]=n
   if chosen:row['data']['magic_spawns']=chosen
   else:row['data'].pop('magic_spawns',None)
   import magic_placement;placed={}
   for site,mode,tiles,rnd,track,life,look in getattr(self,'db_magic_place_vars',[]):
    try:n=int(tiles.get())
    except ValueError:raise ValueError('Spawn point must be 0-10 tiles')
    if not 0<=n<=10:raise ValueError('Spawn point must be 0-10 tiles')
    m=magic_placement.MODES.index(mode.get())
    t=int(track.get() or 0)
    try:f=int(life.get() or 0)
    except ValueError:raise ValueError('Frames must be 0-9999')
    if not 0<=f<=9999:raise ValueError('Frames must be 0-9999')
    value=look.get();sprite=int(value.rsplit('(',1)[1].rstrip(')')) if '(' in value else None
    if m or t or f or sprite is not None:
     placed[str(site)]=dict(mode=m,tiles=n,random=bool(rnd.get()),tracking=t,frames=f)
     if sprite is not None:placed[str(site)]['sprite']=sprite
   if placed:row['data']['magic_placement']=placed
   else:row['data'].pop('magic_placement',None)
   for class_id,power in getattr(self,'db_magic_power_vars',[]):
    try:n=int(power.get())
    except ValueError:raise ValueError('Power must be 0-255')
    if not 0<=n<=255:raise ValueError('Power must be 0-255')
    cls=self.database.get(class_id);attacks=cls['data'].get('attacks') or []
    if attacks and attacks[0].get('power')!=n:
     from copy import deepcopy
     from database_balance import apply_definition_balance
     cls=deepcopy(cls);cls['data']['attacks'][0]['power']=n
     self.database.replace(class_id,cls);apply_definition_balance(self.native_balance_session(),cls)
   for site,hue,sat in getattr(self,'db_magic_colour_vars',[]):
    try:h,sa=int(hue.get()),int(sat.get())
    except ValueError:raise ValueError('Hue and saturation must be whole numbers')
    if not -180<=h<=180 or not 0<=sa<=200:raise ValueError('Hue is -180 to 180, saturation 0 to 200')
    if (h,sa)!=(0,100):
     entry=placed.setdefault(str(site),dict(mode=0,tiles=0,random=False,tracking=0,frames=0));entry.update(hue=h,saturation=sa)
   if placed:row['data']['magic_placement']=placed
   else:row['data'].pop('magic_placement',None)
  if self.db_active_kind=='item' and getattr(self,'db_magic_like',None):
   n=self.db_magic_like.get(self.db_magic_like_var.get())
   import magic_spawns
   item_panel=getattr(self,'db_item_panel',None)   # not Magic: a non-magic item keeps its own use
   not_magic=item_panel is not None and item_panel.category.get()!='Magic' and row['source'].get('item_id') not in magic_spawns.SITES
   if n is None or n==row['source'].get('item_id') or not_magic:row['data'].pop('magic_behaves_like',None)
   else:row['data']['magic_behaves_like']=n
  self.database._validate(row)
  applied=False
  weapon_report=None
  if self.db_active_kind=='weapon' and hasattr(self,'db_weapon_panel'):
   weapon_report=self.db_weapon_panel.apply()
   if weapon_report is not None:
    balance=self.db_weapon_panel.balance
    applied=bool(weapon_report['changed_entries'])
    from enemy_definition import BalanceTable
    entry=row.get('source',{}).get('balance_entry')
    if type(entry) is int:row['data']['attacks']=BalanceTable(balance.data).record(entry,0)['attacks']
  elif row.get('source',{}).get('balance_entry') is not None and not row.get('clone_of'):
   try:balance=self.native_balance_session()
   except (ValueError,OSError,StopIteration):balance=None
   if balance is not None:
    from database_balance import apply_definition_balance
    applied=apply_definition_balance(balance,row)
  self.database.replace(definition_id,row)
  for spawned_id,change in spawned_damage.items():
   # A spawned attack's damage and attribute live on the spawned class's own balance record.
   spawned=_copy(self.database.get(spawned_id));spawned['data']['attacks'][0]=dict(spawned['data']['attacks'][0],**change)
   self.database.replace(spawned_id,spawned)
   try:balance=self.native_balance_session()
   except (ValueError,OSError,StopIteration):balance=None
   if balance is not None:
    from database_balance import apply_definition_balance,sync_balance_aliases
    if apply_definition_balance(balance,spawned):sync_balance_aliases(self.database,balance,spawned['source']['balance_entry'])
   self.dirty=True
  if self.db_active_kind=='player' and hasattr(self,'db_starting_panel'):self.db_starting_panel.apply()
  if applied:
   from database_balance import sync_balance_aliases
   entries=weapon_report['changed_entries'] if weapon_report is not None else [row['source']['balance_entry']]
   for entry in entries:sync_balance_aliases(self.database,balance,entry)
  changed=applied or bool(spawned_damage) or (self.database.get(definition_id),self.database.document.get('mod_options',{}))!=before
  if quiet:
   if not changed:return False
   self.dirty=True;text.edit_modified(False);tree=self.db_trees.get(self.db_active_kind)
   if tree is not None and tree.exists(definition_id):tree.item(definition_id,text=row['name'])
   self.status.set(f"Saved changes to {row['name']} in the mod project.")
   return True
  self.db_refresh(definition_id);self.db_select(self.db_active_kind);self.dirty=True
  self.status.set('Source HP / attack / incoming-response edits applied to BALANCE and included in Build game; remaining class settings saved in project.' if applied else 'Class updated in the mod project. Unsupported class properties require native implementation before they affect gameplay.')
 def db_instance_select(self):
  if not self.db_instances_tree:return
  selected=self.db_instances_tree.selection()
  if not selected:return
  instance=next(row for row in self.database.document["instances"] if row["id"]==selected[0])
  cls=next((row for row in self.database.definitions if row["id"]==instance.get("class_id")),None)
  values=["Unassigned"]+[f"{row['name']} [{row['kind']}] — {row['id']}" for row in self.database.definitions]
  self.db_class_combo.configure(values=values)
  self.db_instance_class.set(next((v for v in values if instance.get("class_id") and v.endswith("— "+str(instance.get("class_id")))),"Unassigned"))
  self.db_instance_label.set(f"Map {instance['map_id']} — {map_label(instance['map_id'])}\nEntity {instance['entity_index']} · sprite {instance['source']['sprite_id']:02X}\nLinked class: {cls['name'] if cls else 'Unassigned'}")
  self.db_show_preview("instances",instance=instance)
 def db_assign_instance(self):
  selected=self.db_instances_tree.selection() if self.db_instances_tree else ()
  if not selected:raise ValueError("Select a map instance first")
  display=self.db_instance_class.get();class_id=display.rsplit("— ",1)[-1] if display and display!="Unassigned" else None
  if class_id and class_id not in {row["id"] for row in self.database.definitions}:raise ValueError("Choose a class from the list")
  self.database.assign_instance(selected[0],class_id);self.db_refresh(selected[0]);self.db_instance_select()
  self.status.set("Map instance linked to a shared class in the mod database.")
 def animation_refresh(self,select_name=None,select_frame=None):
  if not hasattr(self,"animation_tree"):return
  rows=self.database.definitions
  self.animation_display_to_id={f"{row['kind'].title()} — {row['name']} [{row['id']}]":row["id"] for row in rows}
  values=list(self.animation_display_to_id)
  previous=self.animation_definition.get()
  self.animation_definition_combo.configure(values=values)
  target=next((display for display,definition_id in self.animation_display_to_id.items() if definition_id==previous),None)
  if target is None:target=values[0] if values else ""
  self.animation_definition.set(target)
  definition_id=self.animation_display_to_id.get(target)
  self.animation_tree.delete(*self.animation_tree.get_children());self.animation_frames_tree.delete(*self.animation_frames_tree.get_children())
  self.animation_working=None
  if not definition_id:
   self.animation_name.set("");self.animation_speed.set("8");return
  row=self.database.get(definition_id);animations=row["data"].setdefault("animations",[])
  for index,animation in enumerate(animations):
   self.animation_tree.insert("","end",iid=str(index),text=animation["name"],values=(animation["ticks_per_frame"],",".join(str(v) for v in animation["frames"])))
  if select_name is not None:
   match=next((str(i) for i,a in enumerate(animations) if a["name"]==select_name),None)
   if match is not None:self.animation_tree.selection_set(match);self.animation_select(select_frame)
  elif self.animation_tree.get_children():
   selected=self.animation_tree.selection()
   key=selected[0] if selected else self.animation_tree.get_children()[0]
   self.animation_tree.selection_set(key);self.animation_select(select_frame)
  else:self.animation_name.set("");self.animation_speed.set("8")
 def animation_definition_id(self):
  definition_id=getattr(self,"animation_display_to_id",{}).get(self.animation_definition.get())
  if not definition_id:raise ValueError("Add or select a content definition first")
  return definition_id
 def animation_select(self,select_frame=None):
  selected=self.animation_tree.selection()
  if not selected:return
  animation=self.database.get(self.animation_definition_id())["data"]["animations"][int(selected[0])]
  from copy import deepcopy
  self.animation_working=deepcopy(animation)
  self.animation_name.set(animation["name"]);self.animation_speed.set(str(animation["ticks_per_frame"]))
  self.animation_frames_tree.delete(*self.animation_frames_tree.get_children())
  for index,frame in enumerate(animation["frames"]):self.animation_frames_tree.insert("","end",iid=str(index),values=(frame,))
  if self.animation_frames_tree.get_children():
   key=str(select_frame) if select_frame is not None and str(select_frame) in self.animation_frames_tree.get_children() else "0"
   self.animation_frames_tree.selection_set(key);self.animation_frame_select()
 def animation_add(self):
  row=self.database.get(self.animation_definition_id());animations=row["data"].setdefault("animations",[])
  if len(animations)>=64:raise ValueError("A definition can have at most 64 animation sequences")
  used={animation["name"] for animation in animations};number=1
  while f"animation_{number}" in used:number+=1
  name=f"animation_{number}";animations.append({"name":name,"ticks_per_frame":8,"frames":[0]})
  self.database.replace(row["id"],row);self.animation_refresh(name)
 def animation_delete(self):
  selected=self.animation_tree.selection()
  if not selected:raise ValueError("Select an animation to delete")
  row=self.database.get(self.animation_definition_id());row["data"]["animations"].pop(int(selected[0]))
  self.database.replace(row["id"],row);self.animation_refresh()
 def animation_frame_select(self):
  selected=self.animation_frames_tree.selection()
  if selected:self.animation_frame_id.set(str(self.animation_working["frames"][int(selected[0])]))
 def animation_frame_set(self):
  selected=self.animation_frames_tree.selection()
  if not selected:raise ValueError("Select a frame to change")
  try:frame=int(self.animation_frame_id.get(),0)
  except ValueError:raise ValueError("Frame ID must be a whole number")
  if not 0<=frame<=255:raise ValueError("Frame ID must be from 0 to 255")
  self.animation_working["frames"][int(selected[0])]=frame
  self.animation_frames_tree.set(selected[0],"frame_id",frame);self.animation_frame_id.set(str(frame))
 def animation_frame_add(self):
  if self.animation_working is None:raise ValueError("Select or add an animation first")
  if len(self.animation_working["frames"])>=256:raise ValueError("An animation can contain at most 256 frames")
  try:frame=int(self.animation_frame_id.get(),0)
  except ValueError:raise ValueError("Frame ID must be a whole number")
  if not 0<=frame<=255:raise ValueError("Frame ID must be from 0 to 255")
  selected=self.animation_frames_tree.selection();index=int(selected[0])+1 if selected else len(self.animation_working["frames"])
  self.animation_working["frames"].insert(index,frame);self.animation_select_frame_list(index)
 def animation_frame_remove(self):
  selected=self.animation_frames_tree.selection()
  if not selected:raise ValueError("Select a frame to remove")
  if len(self.animation_working["frames"])<=1:raise ValueError("An animation must keep at least one frame")
  index=int(selected[0]);self.animation_working["frames"].pop(index);self.animation_select_frame_list(min(index,len(self.animation_working["frames"])-1))
 def animation_frame_move(self,delta):
  selected=self.animation_frames_tree.selection()
  if not selected:raise ValueError("Select a frame to move")
  index=int(selected[0]);target=index+delta
  if not 0<=target<len(self.animation_working["frames"]):return
  frames=self.animation_working["frames"];frames[index],frames[target]=frames[target],frames[index]
  self.animation_select_frame_list(target)
 def animation_select_frame_list(self,index):
  self.animation_frames_tree.delete(*self.animation_frames_tree.get_children())
  for i,frame in enumerate(self.animation_working["frames"]):self.animation_frames_tree.insert("","end",iid=str(i),values=(frame,))
  self.animation_frames_tree.selection_set(str(index));self.animation_frame_select()
 def animation_apply(self):
  selected=self.animation_tree.selection()
  if not selected or self.animation_working is None:raise ValueError("Select or add an animation first")
  name=self.animation_name.get().strip()
  if not name:raise ValueError("Animation name cannot be empty")
  try:speed=int(self.animation_speed.get())
  except ValueError:raise ValueError("Ticks per frame must be a whole number")
  if not 1<=speed<=255:raise ValueError("Ticks per frame must be from 1 to 255")
  row=self.database.get(self.animation_definition_id());animations=row["data"]["animations"];index=int(selected[0])
  if any(i!=index and animation["name"]==name for i,animation in enumerate(animations)):raise ValueError("Animation name already exists on this definition")
  self.animation_working["name"]=name;self.animation_working["ticks_per_frame"]=speed
  animations[index]=self.animation_working
  self.database.replace(row["id"],row);self.animation_refresh(name)
  self.status.set("Animation frames and speed updated. Save mod to keep the changes.")
 def native_animation_load(self):
  from entity_animation import parse_map_sprite_animations
  self.need()
  tree=self.record_views["entities"][0];selected=tree.selection()
  if not selected:raise ValueError("Select a character on the Entities / enemies tab first")
  index=int(selected[0]);entity=inspect_map(self.session.data,self.current_map)["entities"][index]
  entity_offset=int(entity["offset"],16);sprite_id=self.session.data[entity_offset+6]
  animation_sets=parse_map_sprite_animations(self.session.data,self.current_map,sprite_id)
  self.native_animation_sprite_id=sprite_id;self.native_animation_sets=animation_sets
  self.native_animation_location.set(f"Map {self.current_map} · Entity {index} · Sprite {sprite_id} (other uses share these edits)")
  self.native_animation_set_combo.configure(values=tuple(str(row.index) for row in animation_sets))
  self.native_animation_set.set("0");self.native_animation_slot.set("0");self.native_animation_refresh()
 def native_animation_selected_set(self):
  sets=getattr(self,"native_animation_sets",())
  if not sets:raise ValueError("Load a selected map character first")
  try:index=int(self.native_animation_set.get())
  except ValueError:raise ValueError("Choose an animation set")
  if not 0<=index<len(sets):raise ValueError("Animation set is outside this sprite record")
  return sets[index]
 def native_animation_refresh(self):
  if not hasattr(self,"native_animation_tree"):return
  try:animation_set=self.native_animation_selected_set()
  except (ValueError,AttributeError):return
  self.native_animation_speed.set(str(animation_set.speed_raw))
  try:slot=int(self.native_animation_slot.get())
  except ValueError:slot=0
  if not 0<=slot<4:return
  stream=animation_set.streams[slot]
  self.native_animation_tree.delete(*self.native_animation_tree.get_children())
  self.native_animation_order=[];self.native_animation_edits={}
  if stream is None:
   self.native_frame_image_set_combo.configure(values=())
   return
  self.native_animation_order=list(range(len(stream.frames)))
  self.native_frame_image_set_combo.configure(values=tuple(str(v) for v in sorted({frame.image_set_index for frame in stream.frames})))
  for index in self.native_animation_order:
   frame=stream.frames[index]
   self.native_animation_tree.insert("","end",iid=str(index),text=str(index+1),values=(f"0x{frame.delay_raw:02X}",frame.collision_raw,frame.image_set_index))
  if self.native_animation_tree.get_children():
   self.native_animation_tree.selection_set("0");self.native_animation_frame_select()
 def native_animation_frame_select(self):
  selected=self.native_animation_tree.selection()
  if not selected:return
  try:stream=self.native_animation_selected_set().streams[int(self.native_animation_slot.get())]
  except (ValueError,IndexError):return
  if stream is None:return
  index=int(selected[0]);frame=stream.frames[index];edit=self.native_animation_edits.get(index,{})
  self.native_frame_delay.set(str(edit.get("delay_raw",frame.delay_raw)))
  self.native_frame_image_set.set(str(edit.get("image_set_index",frame.image_set_index)))
 def native_animation_set_frame(self):
  selected=self.native_animation_tree.selection()
  if not selected:raise ValueError("Select an animation frame first")
  try:delay=int(self.native_frame_delay.get());image_set=int(self.native_frame_image_set.get())
  except ValueError:raise ValueError("Frame fields must be whole numbers")
  self.native_animation_edits[int(selected[0])] = {"delay_raw":delay,"image_set_index":image_set}
  self.native_animation_refresh_select(selected[0])
 def native_animation_refresh_select(self,index):
  try:animation_set=self.native_animation_selected_set();slot=int(self.native_animation_slot.get());stream=animation_set.streams[slot]
  except (ValueError,IndexError):return
  self.native_animation_tree.delete(*self.native_animation_tree.get_children())
  for original_index in self.native_animation_order:
   frame=stream.frames[original_index];edit=self.native_animation_edits.get(original_index,{})
   self.native_animation_tree.insert("","end",iid=str(original_index),text=str(self.native_animation_order.index(original_index)+1),values=(f"0x{edit.get('delay_raw',frame.delay_raw):02X}",frame.collision_raw,edit.get("image_set_index",frame.image_set_index)))
  if str(index) in self.native_animation_tree.get_children():
   self.native_animation_tree.selection_set(str(index));self.native_animation_frame_select()
 def native_animation_move(self,delta):
  selected=self.native_animation_tree.selection()
  if not selected:raise ValueError("Select a frame to move")
  original_index=int(selected[0]);position=self.native_animation_order.index(original_index);target=position+delta
  if not 0<=target<len(self.native_animation_order):return
  self.native_animation_order[position],self.native_animation_order[target]=self.native_animation_order[target],self.native_animation_order[position]
  self.native_animation_refresh_select(original_index)
 def native_animation_apply(self):
  from entity_animation import prepare_animation_edit
  self.need();animation_set=self.native_animation_selected_set();slot=int(self.native_animation_slot.get())
  stream=animation_set.streams[slot]
  if stream is None:raise ValueError("This direction slot has no animation data")
  try:speed=int(self.native_animation_speed.get())
  except ValueError:raise ValueError("Animation speed must be an unsigned 16-bit number")
  changes=prepare_animation_edit(self.session.data,animation_set,stream,speed,
                                 self.native_animation_order,self.native_animation_edits)
  for offset,replacement,label in changes:self.session.replace(offset,replacement,label)
  if changes:self.dirty=True
  self.status.set("Map animation data updated; Undo is available. Save mod to keep the changes.")
  self.native_animation_load()
 def choose_emulator(self):
  from editor_emulator import chosen_emulator,save_emulator
  current=chosen_emulator()
  path=filedialog.askopenfilename(title="Choose BizHawk EmuHawk.exe",initialdir=current.parent if current else ROOT,
   initialfile="EmuHawk.exe",filetypes=[("BizHawk executable","EmuHawk.exe"),("Windows executable","*.exe")])
  if not path:return None
  selected=save_emulator(path)
  if hasattr(self,'emulator_path'):self.emulator_path.set(str(selected))
  self.status.set(f"Emulator selected: {selected}")
  return selected
 def choose_game_bin(self):
  from editor_preferences import save_preferences
  current=Path(self.game_bin_path.get()).expanduser() if self.game_bin_path.get().strip() else None
  path=filedialog.askopenfilename(title="Choose original Alundra game BIN",initialdir=current.parent if current and current.parent.exists() else ROOT,filetypes=[("PS1 disc BIN","*.bin *.BIN")])
  if not path:return None
  selected=Path(path).resolve()
  if selected.suffix.lower()!='.bin':raise ValueError('Choose the original game .BIN file.')
  self.game_bin_path.set(str(selected));save_preferences({'game_bin_path':str(selected)})
  self.status.set(f"Original game BIN saved for future sessions: {selected}")
  return selected
 def save_project_preferences(self):
  from editor_preferences import safe_build_name,save_preferences
  name=safe_build_name(self.project_build_name.get())
  raw=self.game_bin_path.get().strip();source=None
  if raw:
   source=Path(raw).expanduser().resolve()
   if source.suffix.lower()!='.bin' or not source.is_file():raise ValueError('Choose an existing original game .BIN file, or leave the field blank to select it when building.')
  values={'project_build_name':name}
  values['game_bin_path']=''
  if source:values['game_bin_path']=str(source)
  saved=save_preferences(values)
  self.project_build_name.set(name)
  if source:self.game_bin_path.set(str(source))
  self.status.set('Project name and game path saved between sessions.')
  return saved
 def db_combat_target(self,row):
  """The class whose combat stats a database row shows: itself, or for Meia's
  Player entry her NPC class (catalogue 302), which holds her native record."""
  if row.get('source',{}).get('player_slot')=='meia':
   npc=next((r for r in self.database.definitions if r.get('source',{}).get('catalogue_index')==302 and not r.get('clone_of')),None)
   if npc is not None:return npc
  return row
 def edit_fingerprint(self):
  """Identifies the current edits (undo history + database) for 'saved by the last build'."""
  import hashlib
  s=self.session
  stacks=[(len(s.undo_stack),id(s.undo_stack[-1]) if s.undo_stack else None)]
  stacks+=[(name,len(x.undo_stack),id(x.undo_stack[-1]) if x.undo_stack else None) for name,x in sorted(getattr(s,'extra_files',{}).items())]
  return (tuple(stacks),hashlib.sha1(json.dumps(self.database.to_json(),sort_keys=True,default=str).encode()).hexdigest())
 def build_and_test(self):
  self.kill_audio()
  return self.build_modded_game(test=True)
 def build_modded_game(self,test=False):
  if self.build_running:self.status.set("A game export is already running.");return
  self.need();self.keep_open_event_edits();self.apply_pixels()
  emulator=None
  if test:
   from editor_emulator import chosen_emulator
   emulator=chosen_emulator() or self.choose_emulator()
   if emulator is None:return
  from editor_preferences import project_build_name,save_preferences,selected_game_bin,safe_build_name,project_output_paths
  source=selected_game_bin()
  if source is None:
   from editor_preferences import load_preferences
   saved_path=load_preferences().get('game_bin_path');saved_parent=Path(saved_path).expanduser().parent if saved_path else ROOT
   source=filedialog.askopenfilename(title="Choose original Alundra disc BIN",initialdir=saved_parent if saved_parent.exists() else ROOT,filetypes=[("Disc image","*.bin *.BIN")])
   if not source:return
   source=Path(source).resolve()
   if source.suffix.lower()!='.bin':raise ValueError('Choose the original game .BIN file.')
   if hasattr(self,'game_bin_path'):self.game_bin_path.set(str(source))
   save_preferences({'game_bin_path':str(source)})
  name=safe_build_name(self.project_build_name.get() if hasattr(self,'project_build_name') else project_build_name())
  save_preferences({'project_build_name':name,'game_bin_path':str(Path(source).resolve())})
  if test:
   from editor_emulator import bizhawk_server_alive,close_running_bizhawk,live_directory
   # An open BizHawk started by Build & test stays open and plays the new
   # build; any other BizHawk (or one that stopped answering) is closed.
   if bizhawk_server_alive(live_directory()):self.status.set('BizHawk stays open; building the new game…')
   elif close_running_bizhawk():self.status.set('Closed the running BizHawk; building the new game…')
  destination=project_output_paths(name)['bin'].resolve()
  if destination==Path(source).resolve():raise ValueError('The original game BIN is protected. Choose a separate output build path.')
  destination.parent.mkdir(parents=True,exist_ok=True)
  # Each placed chest keeps its own saved game flag (stays open once opened); fixed here so it never changes between builds.
  from new_event_compile import chest_flag_for
  for graph in self.database.document.get('event_graphs',[]):
   if any(p.get('contained_item_class_id') for p in graph.get('pages',[])):chest_flag_for(self.database.document,graph['id'])
  # Every build also saves the mod project, so what you built is what is saved.
  self.save_mod_project();self.build_fingerprint=self.edit_fingerprint();self.dirty=False
  from mod_export import build_snapshot
  snapshot=build_snapshot(self.session,self.database.to_json())
  graphs=[g for g in self.database.document.get('event_graphs',[]) if (g.get('native_placement') or {}).get('tile_graphic')]
  if graphs:   # Use Tile events: their pictures go into the build copy only, never into your map
   from tile_event_graphic import apply_tile_graphics
   snapshot.data=bytearray(snapshot.data);snapshot.undo_stack=[];snapshot.redo_stack=[]
   apply_tile_graphics(snapshot,self.database,graphs);snapshot.data=bytes(snapshot.data)
  events=queue.Queue();self.build_running=True
  def worker():
   try:
    result=build_game(snapshot,source,destination,lambda text:events.put(("progress",text)),overwrite=True)
    skipped=getattr(snapshot,'native_event_export_skipped',[])
    warning=''   # no build warnings in the status bar (details stay in the export report)
    if test:
     from editor_emulator import launch_built_game
     try:
      launched=launch_built_game(emulator,result[1])
      menu=(launched.get('main_menu') or {}).get('mode','normal boot')
      where='sent to the open BizHawk' if launched.get('reused') else 'opened in BizHawk'
      events.put(("done",f"Game built and {where} ({menu}): {result[1]} — isolated saves: {launched['run_directory']}{warning}"))
     except Exception as exc:
      events.put(("launch_error",f"Game built: {result[1]}. BizHawk did not open: {exc}{warning}"))
    else:events.put(("done",f"Game exported: {result[1]} — open this CUE in your emulator.{warning}"))
   except Exception as exc:events.put(("error",str(exc)))
  def poll():
   try:
    while True:
     kind,text=events.get_nowait();self.status.set(text)
     if kind=="progress":
      done=build_percent(text)
      if done is not None and done>=self.build_bar['value']:self.build_bar.configure(value=done);self.build_percent.set(f'{done}%')
     if kind!="progress":
      self.build_running=False;self.build_bar.configure(value=100);self.build_percent.set('100%')
      self.root.after(1200,lambda:(self.build_bar.pack_forget(),self.build_percent_label.pack_forget()))
      if kind in ("error","launch_error"):self.report_problem(text)
      return
   except queue.Empty:pass
   self.root.after(100,poll)
  self.build_bar.configure(value=0);self.build_percent.set('0%')
  self.build_bar.pack(side="left",padx=(10,0),pady=5,before=self.status_label)
  self.build_percent_label.pack(side="left",padx=(4,0),before=self.status_label)
  threading.Thread(target=worker,daemon=True).start();poll()
 def load_patch(self):
  self.need()
  if self.dirty:raise ValueError("Apply or discard texture painting first")
  path=filedialog.askopenfilename(initialdir=ROOT/"game",filetypes=[("Editor patch","*.json")])
  if path:
   self.session.apply_patch(json.loads(Path(path).read_text()));self.load_map()
 def load_script(self):
  self.script_tree.delete(*self.script_tree.get_children())
  for widget in self.operand_frame.winfo_children():widget.destroy()
  for offset,op,size in instructions(self.session,self.current_map,self.script_key.get()):
   name=EDITABLE[op][0] if op in EDITABLE else f"Opcode {op:02X} (read-only)"
   operands=self.session.data[offset+1:offset+size].hex(" ")
   self.script_tree.insert("","end",iid=str(offset),values=(f"{offset:08X}",name,operands))
 def select_instruction(self):
  for widget in self.operand_frame.winfo_children():widget.destroy()
  self.operand_vars=[]
  selected=self.script_tree.selection()
  if not selected:return
  offset=int(selected[0]);op=self.session.data[offset]
  if op not in EDITABLE:
   ttk.Label(self.operand_frame,text="Operands are not decoded enough for editing.").pack()
   return
  name,fmt,labels=EDITABLE[op]
  values=struct.unpack_from("<"+fmt,self.session.data,offset+1)
  for i,(label,value) in enumerate(zip(labels,values)):
   ttk.Label(self.operand_frame,text=label).grid(row=0,column=i,padx=3)
   var=tk.StringVar(value=str(value));self.operand_vars.append(var)
   ttk.Entry(self.operand_frame,textvariable=var,width=16).grid(row=1,column=i,padx=3)
  ttk.Button(self.operand_frame,text="Apply operands",command=lambda:self.guard(self.apply_instruction)).grid(row=2,column=0,pady=8)
 def apply_instruction(self):
  selected=self.script_tree.selection()
  if not selected:raise ValueError("Select an instruction")
  offset=int(selected[0]);values=[int(v.get(),16) if v.get().lower().startswith("0x") else int(v.get()) for v in self.operand_vars]
  edit_instruction(self.session,self.current_map,self.script_key.get(),offset,values)
  self.load_script();self.script_tree.selection_set(str(offset));self.select_instruction()
  self.status.set("Event operands applied. Save a copy or export a patch; Undo is available.")
if __name__=="__main__":
 from ui_title_case import install as install_title_case
 install_title_case()
 try:   # own taskbar entry, so Windows shows the chest instead of the Python icon
  import ctypes;ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('AlundraDecomp.Editor')
 except Exception:pass
 try:
  from active_windows import install as install_active_windows;install_active_windows()   # opened windows come to the front (2026-10-18)
 except Exception:pass
 root=tk.Tk()
 try:root.iconphoto(True,ImageTk.PhotoImage(Image.open(Path(__file__).resolve().parent/'editor_icon.ico').convert('RGBA').resize((64,64),Image.NEAREST),master=root))
 except Exception:pass
 try:root.iconbitmap(default=str(Path(__file__).resolve().parent/'editor_icon.ico'))   # treasure chest icon (title bar / taskbar)
 except Exception:pass
 try:
  from dark_titlebar import install as install_dark_titlebar;install_dark_titlebar(root)   # dark window frame (2026-10-17)
 except Exception:pass
 Editor(root);root.mainloop()
