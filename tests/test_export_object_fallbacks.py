import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from event_export import _default_chest_item,_with_chest_item

DEFS=[{'id':'object:0023','kind':'object','name':'Treasure Chest','source':{'catalogue_index':30}},
      {'id':'object:0050','kind':'object','name':'Grave','source':{'catalogue_index':300}},
      {'id':'item:0001','kind':'item','name':'Herb','source':{}}]

def graph(class_id,**page):
 return {'id':'event:0001','map_id':1,'pages':[dict(class_id=class_id,**page)]}

class ObjectFallbackTests(unittest.TestCase):
 def test_chest_without_contents_gets_default_item(self):
  exported=SimpleNamespace(content_database={'definitions':DEFS})
  g=graph('object:0023')
  self.assertEqual(_default_chest_item(exported,g),'item:0001')
  self.assertEqual(_with_chest_item(g,'item:0001')['pages'][0]['contained_item_class_id'],'item:0001')
  self.assertNotIn('contained_item_class_id',g['pages'][0])

 def test_chosen_contents_and_other_objects_untouched(self):
  exported=SimpleNamespace(content_database={'definitions':DEFS})
  self.assertIsNone(_default_chest_item(exported,graph('object:0023',contained_item_class_id='item:0009')))
  self.assertIsNone(_default_chest_item(exported,graph('object:0050')))

if __name__=='__main__':unittest.main()
