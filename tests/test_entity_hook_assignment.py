import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from editor_session import EditSession
from event_editor import assign_entity_hook


class EntityHookAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.session = EditSession(bytes(128), verify=False)
        self.map_rows = {"entities": [{"offset": "0x20"}]}

    def test_assign_existing_interaction_root_and_undo(self):
        with patch("map_inspector.inspect_map", return_value=self.map_rows), \
             patch("event_editor.script_roots", return_value={"F 3": (0x40, 0x60, 0x50)}):
            value = assign_entity_hook(self.session, 5, 0, "F", "F 3")
        self.assertEqual(value, 0x83)
        self.assertEqual(self.session.data[0x20 + 15], 0x83)
        self.session.undo()
        self.assertEqual(self.session.data[0x20 + 15], 0)

    def test_can_disable_hook(self):
        with patch("map_inspector.inspect_map", return_value=self.map_rows):
            assign_entity_hook(self.session, 5, 0, "D", None)
        self.assertEqual(self.session.data[0x20 + 13], 0)

    def test_rejects_script_from_different_hook_bank(self):
        with patch("map_inspector.inspect_map", return_value=self.map_rows), \
             patch("event_editor.script_roots", return_value={"A 3": (0x40, 0x60, 0x50)}):
            with self.assertRaisesRegex(ValueError, "same event hook bank"):
                assign_entity_hook(self.session, 5, 0, "F", "A 3")

    def test_refuses_missing_script_and_entity(self):
        with patch("map_inspector.inspect_map", return_value=self.map_rows), \
             patch("event_editor.script_roots", return_value={}):
            with self.assertRaisesRegex(ValueError, "existing map-local"):
                assign_entity_hook(self.session, 5, 0, "F", "F 1")
            with self.assertRaisesRegex(ValueError, "no longer exists"):
                assign_entity_hook(self.session, 5, 1, "F", "F 1")


if __name__ == "__main__":
    unittest.main()
