"""Canvas exposing logical coordinates while rendering at a selected zoom."""
import tkinter as tk
from PIL import Image,ImageTk
class ZoomCanvas(tk.Canvas):
 def __init__(self,*a,**kw):
  self.zoom_factor=1.;self.zoom_images=[]
  super().__init__(*a,**kw)
 def _points(self,args):
  if len(args)==1 and isinstance(args[0],(tuple,list)):args=args[0]
  return [v*self.zoom_factor for v in args]
 def create_rectangle(self,*args,**kw):return super().create_rectangle(*self._points(args),**kw)
 def create_polygon(self,*args,**kw):return super().create_polygon(*self._points(args),**kw)
 def create_line(self,*args,**kw):return super().create_line(*self._points(args),**kw)
 def create_oval(self,*args,**kw):return super().create_oval(*self._points(args),**kw)
 def create_text(self,*args,**kw):return super().create_text(*self._points(args),**kw)
 def create_image(self,*args,**kw):
  if self.zoom_factor!=1 and kw.get("image"):
   im=ImageTk.getimage(kw["image"]);im=im.resize((max(1,round(im.width*self.zoom_factor)),max(1,round(im.height*self.zoom_factor))),Image.Resampling.NEAREST)
   photo=ImageTk.PhotoImage(im,master=self);self.zoom_images.append(photo);kw["image"]=photo
  return super().create_image(*self._points(args),**kw)
 def canvasx(self,x,gridspacing=None):return super().canvasx(x)/self.zoom_factor
 def canvasy(self,y,gridspacing=None):return super().canvasy(y)/self.zoom_factor
 def move(self,tag,x,y):return super().move(tag,x*self.zoom_factor,y*self.zoom_factor)
 def bbox(self,*args):
  b=super().bbox(*args);return tuple(v/self.zoom_factor for v in b) if b else None
 def configure(self,cnf=None,**kw):
  if "scrollregion" in kw:kw["scrollregion"]=self._points(kw["scrollregion"])
  return super().configure(cnf,**kw)
 def delete(self,*args):
  result=super().delete(*args)
  if "all" in args:self.zoom_images=[]
  return result
