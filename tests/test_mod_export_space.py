import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from mod_export import check_build_space

class ExportSpaceTests(unittest.TestCase):
 def test_same_volume_requires_both_temporary_and_output_space(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);source=root/'source.bin';source.write_bytes(b'original')
   session=SimpleNamespace(original=b'a',data=b'a')
   with patch('mod_export.shutil.disk_usage',return_value=SimpleNamespace(free=200*1024*1024)):
    with self.assertRaisesRegex(ValueError,'no output game has been created'):
     check_build_space(source,root/'output.bin',root,session)
   self.assertEqual(source.read_bytes(),b'original')
   self.assertFalse((root/'output.bin').exists())
 def test_growth_of_data_and_extra_files_counts_against_reserve(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);source=root/'source.bin';source.write_bytes(b'original')
   session=SimpleNamespace(original=b'a',data=b'a'*1000,
    extra_files={'EXE':SimpleNamespace(original=b'b',data=b'b'*1000)})
   with patch('mod_export.shutil.disk_usage',return_value=SimpleNamespace(free=256*1024*1024+100)):
    with self.assertRaisesRegex(ValueError,'Not enough free space'):
     check_build_space(source,root/'output.bin',root,session)
 def test_enough_space_does_not_create_an_output(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);source=root/'source.bin';source.write_bytes(b'original')
   with patch('mod_export.shutil.disk_usage',return_value=SimpleNamespace(free=1024**3)):
    budgets=check_build_space(source,root/'new'/'output.bin',root,SimpleNamespace(original=b'a',data=b'a'))
   self.assertEqual(len(budgets),1)
   self.assertFalse((root/'new').exists())
