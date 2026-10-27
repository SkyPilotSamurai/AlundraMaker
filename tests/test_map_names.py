import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import map_names

class MapNameTests(unittest.TestCase):
 def test_reported_unused_labels_are_identified_without_claiming_runtime_safety(self):
  self.assertTrue(map_names.map_is_reported_unused(427))
  self.assertFalse(map_names.map_is_reported_unused(0))

if __name__=="__main__":unittest.main()
