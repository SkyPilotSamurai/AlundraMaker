import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import build_cache

class BuildCacheTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  patcher=patch.object(build_cache,'CACHE',Path(self.temp.name));patcher.start();self.addCleanup(patcher.stop)
 def step(self,session,calls):
  def run():
   calls.append(1);session.data[10:14]=b'ABCD';session.data[900]=7;return {'redrawn':2}
  return build_cache.cached_step('demo',session,[(0,100)],[('x',1)],('build_cache',),run)
 def test_second_build_reuses_the_changes(self):
  calls=[];first=SimpleNamespace(data=bytearray(1000))
  self.assertEqual(self.step(first,calls),{'redrawn':2})
  second=SimpleNamespace(data=bytearray(1000));second.data[500]=9   # outside what the step reads
  report=self.step(second,calls)
  self.assertEqual(len(calls),1);self.assertTrue(report['from_cache'])
  self.assertEqual(second.data[10:14],b'ABCD');self.assertEqual(second.data[900],7);self.assertEqual(second.data[500],9)
 def test_changed_input_runs_again(self):
  calls=[];self.step(SimpleNamespace(data=bytearray(1000)),calls)
  other=SimpleNamespace(data=bytearray(1000));other.data[50]=1
  self.step(other,calls);self.assertEqual(len(calls),2)
 def test_byte_changes(self):
  a=bytes(200000);b=bytearray(a);b[5]=1;b[6]=2;b[150000]=3
  self.assertEqual(build_cache.byte_changes(a,bytes(b)),[(5,b'\x01\x02'),(150000,b'\x03')])

if __name__=='__main__':unittest.main()
