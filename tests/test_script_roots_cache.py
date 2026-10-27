"""Script roots must follow a map block that moved (an earlier map grew) even
when the map's own script section is unchanged (stale absolute offsets broke
Open World / Remove cutscenes builds)."""
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
DATAS = ROOT / 'game' / 'disc' / 'DATA' / 'DATAS.BIN'


@unittest.skipUnless(DATAS.is_file(), 'private retail DATAS.BIN not present')
class ScriptRootsCacheTests(unittest.TestCase):
    def test_roots_follow_moved_map_block(self):
        from editor_session import EditSession
        from event_editor import script_roots
        from map_block_repack import pointers, sections, replace_section
        data = DATAS.read_bytes()
        session = EditSession(bytes(data), None, verify=False)
        before = script_roots(session, 411)
        # grow map 2's texture section by 4 KiB: every later map block moves
        pp = pointers(data); h = sections(data[pp[2]:pp[3]])
        grown = replace_section(data, 2, 4, bytes(data[pp[2] + h[4]:pp[2] + h[5]]) + bytes(4096))
        session.data = bytearray(grown)
        after = script_roots(session, 411)
        fresh = script_roots(EditSession(bytes(grown), None, verify=False), 411)
        self.assertEqual(after, fresh)
        self.assertNotEqual(after, before)


if __name__ == '__main__':
    unittest.main()
