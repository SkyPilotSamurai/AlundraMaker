import sys
import unittest
from pathlib import Path
from dataclasses import replace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from portal_records import Portal, replace_portal

class PortalTests(unittest.TestCase):
    def test_signed_fields_and_unknown_flags_round_trip(self):
        raw = bytes.fromhex("01020304ffff05060080ffff")
        portal = Portal.read(raw)
        self.assertEqual(portal.destination_map, -1)
        self.assertEqual(portal.z, -32768)
        self.assertEqual(portal.encode(), raw)

    def test_edit_preserves_surroundings_and_original(self):
        raw = bytes.fromhex("01020304010005060000abcd")
        source = b"before" + raw + b"after"
        original = Portal.read(source, 6)
        edited = replace(original, destination_map=241)
        result = replace_portal(source, 6, original, edited)
        self.assertEqual(source, b"before" + raw + b"after")
        self.assertEqual(result, b"before" + edited.encode() + b"after")
        self.assertEqual(replace_portal(result, 6, edited, original), source)

    def test_reject_bad_preimage_bounds_and_overflow(self):
        p = Portal(1,2,3,4,5,6,7,8,9)
        for off in [-1, 1, 20]:
            with self.assertRaises(ValueError): Portal.read(p.encode(), off)
        with self.assertRaises(ValueError):
            replace_portal(p.encode(), 0, replace(p, flags=0), p)
        with self.assertRaises(ValueError): replace(p, destination_map=32768).encode()
