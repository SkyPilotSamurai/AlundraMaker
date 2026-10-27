import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0,str(TOOLS))
from disc_build_queue import build_slot

class DiscBuildQueueTests(unittest.TestCase):
    def test_other_process_waits_then_acquires_released_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock=Path(tmp)/'build.lock';ready=Path(tmp)/'ready'
            script='from pathlib import Path; from disc_build_queue import build_slot; import sys;\nwith build_slot(sys.argv[1]): Path(sys.argv[2]).write_text("ready")'
            child=None
            try:
                with build_slot(lock):
                    environment=os.environ.copy()
                    environment['PYTHONPATH']=str(TOOLS)+os.pathsep+environment.get('PYTHONPATH','')
                    child=subprocess.Popen([sys.executable,'-B','-c',script,str(lock),str(ready)],env=environment)
                    with self.assertRaises(subprocess.TimeoutExpired):child.wait(timeout=.4)
                    self.assertFalse(ready.exists())
                self.assertEqual(child.wait(timeout=5),0)
                self.assertEqual(ready.read_text(),'ready')
            finally:
                if child is not None and child.poll() is None:child.terminate();child.wait()
    def test_exception_releases_slot(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock=Path(tmp)/'build.lock'
            with self.assertRaisesRegex(ValueError,'fixture'):
                with build_slot(lock):raise ValueError('fixture')
            with build_slot(lock,timeout=.1):pass
