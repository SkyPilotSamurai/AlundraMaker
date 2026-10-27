import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from editor_session import EditSession
from event_export import EventExportError, prepare_native_event_export, project_event_export_issues, require_native_event_export
from event_graph import new_event_graph
from mod_export import build_game, save_mod


class EventExportTests(unittest.TestCase):
    def session(self):
        session = EditSession(bytes(64), verify=False)
        session.content_database = {"format": "alundra-content-database-v1",
                                    "definitions": [], "event_graphs": []}
        return session

    def test_native_byte_edits_and_database_catalogue_are_allowed(self):
        session = self.session()
        session.replace(10, bytes([5, 1, 0]), "Native flag edit")
        session.content_database["definitions"] = [{"id": "npc:0001"}]
        require_native_event_export(session)
        self.assertEqual(project_event_export_issues(session), [])

    def test_unexportable_empty_event_is_reported_without_stopping_export(self):
        session = self.session()
        graph = new_event_graph("event:0001", 244, "Village conversation", 3, 4)
        session.content_database["event_graphs"].append(graph)
        warnings = project_event_export_issues(session)
        self.assertEqual(warnings[0]["event_id"], "event:0001")
        self.assertIn("Village conversation", warnings[0]["name"])
        exported = prepare_native_event_export(session, best_effort=True)
        self.assertEqual(exported.native_event_export_skipped[0]["event_id"], "event:0001")
        self.assertEqual(exported.native_event_export_skipped[0]["map_id"], 244)
        self.assertEqual(bytes(session.data), bytes(64))

    def test_claimed_compilation_cannot_bypass_validation(self):
        session = self.session()
        graph = new_event_graph("event:0001", 244)
        graph["compiled"] = True
        graph["native_export"] = {"supported": True}
        session.content_database["event_graphs"].append(graph)
        with self.assertRaises(EventExportError):require_native_event_export(session)

    def test_event_issue_does_not_stop_build_attempt_or_change_saved_project(self):
        session = self.session()
        graph = new_event_graph("event:0001", 244)
        graph["pages"][0]["commands"] = [{"type": "show_dialogue", "text": "Hello"}]
        session.content_database["event_graphs"].append(graph)
        before = bytes(session.data)
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "new.bin"
            with patch("mod_export.read_datas") as read, patch("mod_export.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "does not match the original data"):
                    build_game(session, "unused.bin", destination)
                read.assert_called_once()
                run.assert_not_called()
            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_suffix(".cue").exists())
            project = Path(folder) / "keep.alundramod"
            save_mod(session, project, "Keep events", 244)
            self.assertEqual(json.loads(project.read_text())["content_database"]["event_graphs"], [graph])
        self.assertEqual(bytes(session.data), before)

    def test_malformed_event_list_is_not_treated_as_no_events(self):
        session = self.session()
        for value in (None, {}, "events"):
            session.content_database["event_graphs"] = value
            with self.assertRaises(EventExportError):
                require_native_event_export(session)

    def test_selected_event_filter_does_not_compile_unrelated_graphs(self):
        session = self.session()
        session.content_database["event_graphs"] = [new_event_graph("first", 244), new_event_graph("second", 244)]
        with patch("new_event_compile.compile_new_events", side_effect=ValueError("unsupported")) as compile_events:
            issues = project_event_export_issues(session, event_ids=["second"])
        self.assertEqual([row["event_id"] for row in issues], ["second"])
        self.assertEqual(compile_events.call_count, 1)
        self.assertEqual(compile_events.call_args.args[1][0]["id"], "second")


if __name__ == "__main__":
    unittest.main()
