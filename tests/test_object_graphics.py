import sys,struct,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from database_catalogue import graphic_maps,preview_maps
from placement_catalogue import placement_info,database_rows
from content_database import ContentDatabase
from entity_preview import EntityPreview

class ObjectGraphicsTests(unittest.TestCase):
 def test_bank_record_discovered_without_any_entity(self):
  data=bytearray(4000);struct.pack_into('<I',data,0x28,2200)
  struct.pack_into('<7I',data,2200,28,28,28,100,300,350,350)
  struct.pack_into('<2I',data,2300+12,48,52)
  struct.pack_into('<i',data,2300+48,60)
  self.assertEqual(graphic_maps(data),{256:[0]})
  struct.pack_into('<i',data,2348,9999)
  self.assertEqual(graphic_maps(data),{})

 def test_entity_maps_precede_extra_bank_sources(self):
  self.assertEqual(preview_maps({'observed_map':3,'observed_maps':[2,3],'graphic_maps':[1,2]}),[3,2,1])

 def test_invisible_and_spawned_objects_are_misc_without_changing_kind(self):
  db=ContentDatabase();visible=db.new('object','Vase');visible['source']={'catalogue_index':291}
  hidden=db.new('object','Invisible helper');hidden['source']={'catalogue_index':244}
  emitted=db.new('object','Custom emitted spark');emitted['source']={'spawned_by_class_id':visible['id']}
  self.assertEqual(database_rows(db,'object'),[visible])
  self.assertEqual({r['id'] for r in database_rows(db,'misc')},{hidden['id'],emitted['id']})
  self.assertEqual(hidden['kind'],'object')
  # Missing preview/unknown source does not imply invisibility.
  self.assertEqual(placement_info(db.new('object','Undecoded'))['category'],'object')

 def test_secondary_animation_frame_fallback_and_reuse(self):
  from PIL import Image
  p=EntityPreview.__new__(EntityPreview);p.cache={};p.start=0;p.header=(0,0,0,48,52)
  p.frame=MagicMock(return_value=None)
  def read(fmt,pos):
   if (fmt,pos)==('i',48):return (60,)
   if (fmt,pos)==('4I',60):return (92,120,0,150)
   if fmt=='4h':return (-1,-1,-1,-1) if pos==92 else (0,-1,-1,-1)
   if (fmt,pos)==('B',120):return (128,)
   if (fmt,pos)==('H',123):return (2,)
   raise ValueError('Out of section')
  p.read=read;image=Image.new('RGBA',(2,3),(255,0,0,255));p.image_set=MagicMock(return_value=(image,0,-3))
  self.assertIs(p.representative_frame(0)[0],image)
  self.assertIs(p.representative_frame(0)[0],image)
  p.image_set.assert_called_once_with(0,2)
