import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from map_block_repack import OwnedData, own_session_data, release_session_data


class Fake:
    pass


class InPlace(unittest.TestCase):
    def test_plain_data_is_never_edited(self):
        # byte-identical lab builds with and without ALUNDRA_NO_INPLACE=1 cover the
        # editing itself; here: the session wrapper never touches the caller's data
        s = Fake(); s.data = bytearray(b'abc')
        before = s.data
        own_session_data(s)
        self.assertIsInstance(s.data, OwnedData)
        self.assertIsNot(s.data, before)
        s.data = bytearray(b'xyz')                 # a step handing back plain data
        self.assertIsInstance(s.data, OwnedData)
        release_session_data(s)
        self.assertNotIn('inplace', vars(type(s)))
        self.assertFalse(s.data.__dict__.get('inplace', True))
        self.assertEqual(bytes(before), b'abc')


if __name__ == "__main__":
    unittest.main()
