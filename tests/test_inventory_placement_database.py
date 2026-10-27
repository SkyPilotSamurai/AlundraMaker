"""Database schema accepts guarded pickup identity, not invented game items."""
import unittest
from content_database import ContentDatabase
from event_graph import new_event_graph

class InventoryPlacementTests(unittest.TestCase):
 def make(self,kind='item'):
  db=ContentDatabase();row=db.new(kind,'Key');row['source']={'catalogue_index':91,'item_id':61}
  graph=db.new_event_graph(163,'Key pickup',4,15);graph['class_id']=row['id'];graph['pages'][0]['class_id']=row['id']
  return db,row,graph
 def test_key_placement_survives_add_and_reload(self):
  db,row,graph=self.make();db.replace_event_graph(graph['id'],graph)
  loaded=ContentDatabase(db.to_json());self.assertEqual(loaded.document['event_graphs'][0]['class_id'],row['id'])
 def test_weapon_and_armor_use_same_inventory_identity_contract(self):
  for kind in ('weapon','armor'):
   db,row,graph=self.make(kind);db.replace_event_graph(graph['id'],graph);ContentDatabase(db.to_json())
 def test_unbacked_or_mismatched_item_identity_rejects(self):
  for source in ({},{'item_id':61},{'item_id':61,'catalogue_index':92},{'item_id':True,'catalogue_index':31}):
   db,row,graph=self.make();row['source']=source
   with self.subTest(source=source),self.assertRaisesRegex(ValueError,'native item identity'):db.replace_event_graph(graph['id'],graph)
 def test_item_page_actions_and_conditions_are_accepted(self):
  # 2026-10-23: an item page keeps its conditions and its actions (run after the pickup)
  db,row,graph=self.make();graph['pages'][0]['commands']=[{'type':'change_money','amount':7}]
  graph['pages'][0]['trigger']='touch'
  graph['pages'][0]['conditions']=[{'type':'switch','switch_scope':'project','switch_id':1,'value':True,'operator':'=='}]
  db.replace_event_graph(graph['id'],graph);ContentDatabase(db.to_json())
 def test_item_page_refuses_only_what_cannot_apply(self):
  for trigger in ('death','activate','hit'):   # kept: Death / Activate ignored, Hit runs on a hit
   db,row,graph=self.make();graph['pages'][0]['trigger']=trigger;db.replace_event_graph(graph['id'],graph)
  db,row,graph=self.make();graph['pages'][0]['trigger']='event_touch'
  with self.assertRaisesRegex(ValueError,'picked up or hit; the event_touch trigger'):db.replace_event_graph(graph['id'],graph)
  db,row,graph=self.make();graph['pages'][0]['commands']=[{'type':'change_animation','animation_id':1}]
  with self.assertRaisesRegex(ValueError,'gone once picked up'):db.replace_event_graph(graph['id'],graph)
