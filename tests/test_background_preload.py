import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_background_preload import BackgroundPreload

class BackgroundPreloadTests(unittest.TestCase):
 def job(self,plan,**kw):
  session=SimpleNamespace();editor=SimpleNamespace(session=session)
  with patch('editor_asset_preload.preload_plan',return_value=plan):
   job=BackgroundPreload(editor,session,SimpleNamespace(definitions=[]),**kw)
  return job,editor,session
 def test_everything_loads_and_result_is_recorded(self):
  ran=[];plan=[(('map',m),f'Map {m}',lambda m=m:ran.append(m)) for m in range(3)]+[('class','Bad',lambda:1/0)]
  job,editor,session=self.job(plan,sleep=lambda s:None);job.run()
  self.assertEqual(ran,[0,1,2]);self.assertTrue(job.finished)
  self.assertEqual(session.asset_preload_result['errors'][0]['asset'],'Bad');self.assertIs(editor.asset_preload_stats,session.asset_preload_result)
  self.assertTrue(session._full_asset_preload);self.assertEqual(job.status_text(),'')
 def test_what_you_open_moves_to_the_front(self):
  ran=[];plan=[(('map',m),f'Map {m}',lambda m=m:ran.append(m)) for m in range(5)]+[('class','A',lambda:ran.append('A'))]
  job,_,_=self.job(plan,sleep=lambda s:None)
  self.assertEqual(job.prioritize(('map',3)),1);job.prioritize('class');job.run()
  self.assertEqual(ran,['A',3,0,1,2,4])
 def test_pauses_while_you_work(self):
  now=[0.0];slept=[]
  def sleep(s):slept.append(s);now[0]+=s
  ran=[];job,_,_=self.job([('global','G',lambda:ran.append(now[0]))],sleep=sleep,clock=lambda:now[0])
  job.user_active(0.35);job.run()
  self.assertGreaterEqual(ran[0],0.35)
 def test_waits_while_the_editor_is_busy(self):
  now=[0.0];ran=[]
  def sleep(s):
   now[0]+=s
   if now[0]>=1.0:job.tick()   # the editor is free again at 1 s
  job,_,_=self.job([('global','G',lambda:ran.append(now[0]))],sleep=sleep,clock=lambda:now[0])
  job.ui_tick=0.0;now[0]=0.5;job.run()   # no tick since 0: busy
  self.assertGreaterEqual(ran[0],1.0)
 def test_stops_when_another_game_is_opened(self):
  ran=[];job,editor,session=self.job([('global','G',lambda:ran.append(1))],sleep=lambda s:None)
  editor.session=object();job.run()
  self.assertEqual(ran,[]);self.assertFalse(job.finished);self.assertFalse(hasattr(session,'asset_preload_result'))

if __name__=='__main__':unittest.main()
