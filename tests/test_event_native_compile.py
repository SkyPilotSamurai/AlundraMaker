import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from editor_session import EditSession
from event_graph import new_event_graph
from event_native_compile import native_binding, compile_bound_event, dialogue_binding
from event_export import prepare_native_event_export, EventExportError


class NativeCompileTests(unittest.TestCase):
    def setUp(self):
        self.session = EditSession(bytes(64), verify=False)
        self.session.data[10:22] = bytes([0x0D, 128, 0, 5, 2, 0, 6, 3, 0, 0, 0, 255])
        self.session.data[40:45] = b"Hello"
        self.roots = patch("event_native_compile.script_roots", return_value={"F 0": (10, 22, 10)})
        self.instructions = patch("event_native_compile.instructions", return_value=[(10, 13, 3), (13, 5, 3), (16, 6, 3), (19, 0, 1), (20, 0, 1), (21, 255, 1)])
        self.roots.start(); self.instructions.start()
        self.addCleanup(self.roots.stop); self.addCleanup(self.instructions.stop)
        self.graph = new_event_graph("event:0001", 244)
        self.graph["native_binding"] = native_binding(self.session, 244, "F 0")
        self.session.content_database = {"event_graphs": [self.graph]}

    def commands(self, commands):
        self.graph["pages"][0]["commands"] = commands

    def test_flag_and_warp_emit_known_bytes_without_mutating_authoring_session(self):
        self.commands([{"type": "set_switch", "value": True, "native_flag_operand": 0x0234},
                       {"type": "warp_player", "map_id": 427, "x": 3, "y": 4, "z": 5}])
        before = bytes(self.session.data)
        exported = prepare_native_event_export(self.session)
        self.assertEqual(exported.data[10:22], bytes.fromhex("05 34 02 53 ab 01 03 04 05 00 00 ff"))
        self.assertEqual(bytes(self.session.data), before)

    def test_generic_project_switch_is_not_a_native_flag(self):
        self.commands([{"type": "set_switch", "value": True, "switch_id": 1}])
        with self.assertRaisesRegex(ValueError, "native flag"):
            compile_bound_event(self.session, self.graph)

    def test_preimage_and_capacity_and_unsupported_commands(self):
        self.commands([{"type": "set_switch", "value": True, "native_flag_operand": 1}] * 4)
        with self.assertRaisesRegex(ValueError, "need 13"):
            compile_bound_event(self.session, self.graph)
        self.commands([{"type": "give_item", "item_class_id": "item:0001"}])
        with self.assertRaisesRegex(ValueError, "no verified"):
            compile_bound_event(self.session, self.graph)
        self.commands([])
        self.session.data[13] = 6
        with self.assertRaisesRegex(ValueError, "changed since"):
            compile_bound_event(self.session, self.graph)

    def test_alias_and_duplicate_replacements_rejected(self):
        with patch("event_native_compile.script_roots", return_value={"F 0": (10, 22, 10), "F 1": (10, 22, 10)}):
            with self.assertRaisesRegex(ValueError, "shared"):
                compile_bound_event(self.session, self.graph)
        self.session.content_database["event_graphs"].append(self.graph)
        with self.assertRaisesRegex(EventExportError, "same process"):
            prepare_native_event_export(self.session)

    def test_dialogue_reuses_instruction_speaker_and_fixed_capacity(self):
        with patch("map_text.dialogue_entry", return_value=(0, 40, b"Hello")):
            binding = dialogue_binding(self.session, 244, 10)
            self.commands([dict(type="show_dialogue", text="Hi", **binding)])
            exported = prepare_native_event_export(self.session)
            self.assertEqual(exported.data[10:13], self.session.data[10:13])
            self.assertEqual(exported.data[40:45], b"Hi   ")
            self.assertEqual(self.session.data[40:45], b"Hello")
            self.graph["pages"][0]["commands"][0]["text"] = "Too long"
            with self.assertRaisesRegex(ValueError, "capacity"):
                compile_bound_event(self.session, self.graph)

    def test_bound_dialogue_honors_explicit_wrapping_within_capacity(self):
        from event_native_compile import _dialogue_patch
        with patch('map_text.dialogue_entry', return_value=(0, 40, b'Hello')):
            binding = dialogue_binding(self.session, 244, 10)
            self.assertEqual(_dialogue_patch(self.session, 244, dict(text='A\nB', auto_wrap=True, **binding)),
                             (40, b'A\\NB '))
            with self.assertRaisesRegex(ValueError, 'capacity'):
                _dialogue_patch(self.session, 244, dict(text='A\nBCD', auto_wrap=True, **binding))


if __name__ == "__main__":
    unittest.main()
