import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_memory_loading import run_memory_load


class MemoryLoadingTests(unittest.TestCase):
 def run_task(self,work):
  jobs=[];window=MagicMock();bar=MagicMock()
  root=SimpleNamespace(after=lambda ms,job:jobs.append((ms,job)),wait_window=lambda win:self.pump(jobs))
  with patch('editor_memory_loading.tk.Toplevel',return_value=window),patch('editor_memory_loading.tk.StringVar',return_value=MagicMock()),patch('editor_memory_loading.ttk.Label'),patch('editor_memory_loading.ttk.Progressbar',return_value=bar),patch('editor_memory_loading.threading.Thread',side_effect=lambda target,**kw:SimpleNamespace(start=target)):
   result=run_memory_load(root,work)
  return result,window,bar

 def pump(self,jobs):
  # Run worker first, then queue poll. Both are scheduled, not inline startup.
  start=next(i for i,(ms,job) in enumerate(jobs) if ms==80)
  jobs.pop(start)[1]()
  while jobs:jobs.pop(0)[1]()

 def test_progress_window_maps_before_work_and_shows_asset_count(self):
  def work(progress):progress(10,20,'Assets');return 'ready'
  result,window,bar=self.run_task(work)
  self.assertEqual(result,'ready');window.deiconify.assert_called_once()
  window.grab_release.assert_called_once();window.destroy.assert_called_once()
  bar.configure.assert_called_with(mode='determinate',value=50)

 def test_worker_failure_closes_window_and_surfaces_original_error(self):
  def work(progress):raise ValueError('Bad map')
  with self.assertRaisesRegex(ValueError,'Bad map'):self.run_task(work)

if __name__=='__main__':unittest.main()
