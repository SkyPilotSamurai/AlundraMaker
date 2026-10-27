import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Alundra Maker GitHub" / "tools"))
from event_graph import class_event_name, lettered_name, is_auto_name, DEFAULT_EVENT_NAME
from content_database import ContentDatabase


class ClassEventNameTests(unittest.TestCase):
    def test_new_event_takes_class_name(self):
        self.assertEqual(class_event_name(DEFAULT_EVENT_NAME, {"name": "Red Reaper", "kind": "enemy"}), "Red Reaper")

    def test_empty_event_keeps_default(self):
        self.assertEqual(class_event_name(DEFAULT_EVENT_NAME, None), DEFAULT_EVENT_NAME)

    def test_warp_keeps_default(self):
        warp = {"name": "Warp Panel", "kind": "object", "source": {"variant": "warp_panel"}}
        self.assertEqual(class_event_name(DEFAULT_EVENT_NAME, warp), DEFAULT_EVENT_NAME)

    def test_user_name_is_kept(self):
        self.assertEqual(class_event_name("Guard", {"name": "Red Reaper"}), "Guard")


    def test_lettered_name(self):
        self.assertEqual(lettered_name("Red Reaper", []), ("Red Reaper", None))
        self.assertEqual(lettered_name("Red Reaper", ["Red Reaper"]), ("Red Reaper B", "Red Reaper A"))
        self.assertEqual(lettered_name("Red Reaper", ["Red Reaper A", "Red Reaper B"]), ("Red Reaper C", None))
        self.assertEqual(lettered_name("Red Reaper", ["Red Reaper A", "Red Reaper C"]), ("Red Reaper B", None))

    def test_auto_name(self):
        self.assertTrue(is_auto_name("Chest B", ["Chest"]))
        self.assertFalse(is_auto_name("Chest of Doom", ["Chest"]))

    def test_database_letters_per_map(self):
        db = ContentDatabase(); enemy = db.new("enemy", "Red Reaper")
        first = db.new_event_graph(1, class_id=enemy["id"])
        second = db.new_event_graph(1, class_id=enemy["id"])
        other_map = db.new_event_graph(2, class_id=enemy["id"])
        third = db.new_event_graph(1, class_id=enemy["id"])
        self.assertEqual([first["name"], second["name"], third["name"]], ["Red Reaper A", "Red Reaper B", "Red Reaper C"])
        self.assertEqual(other_map["name"], "Red Reaper")
        self.assertEqual(db.new_event_graph(1)["name"], DEFAULT_EVENT_NAME)


if __name__ == "__main__":
    unittest.main()
