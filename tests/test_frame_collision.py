import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from test_local_sprite_import import fixture
from frame_collision import frame_hitboxes,edit_collision,prepare_collision_edit
from editor_session import EditSession


def collision_fixture():
    d=fixture();sp=2048+2*2048+40
    struct.pack_into('<h',d,sp+218+1,0)
    struct.pack_into('<h',d,sp+204+2,0) # two directions share one frame and box
    d[sp+224:sp+230]=struct.pack('<3b3B',-8,4,-2,16,12,20)
    return d


class CollisionTests(unittest.TestCase):
    def test_read_signed_fields_and_all_aliases(self):
        boxes=frame_hitboxes(collision_fixture(),2,263)
        self.assertEqual(len(boxes),1)
        box=boxes[0]
        self.assertEqual(box.values,(-8,4,-2,16,12,20))
        self.assertEqual(box.references,((0,0,0),(0,1,0)))
        self.assertEqual(box.projected_corners[0],(-8,6))
        self.assertEqual(box.projected_corners[-1],(8,-2))

    def test_edit_undo_redo_exact_six_bytes(self):
        d=collision_fixture();session=EditSession(d,verify=False)
        box=frame_hitboxes(session.data,2,263)[0]
        self.assertTrue(edit_collision(session,box,(-10,5,-4,22,14,18)))
        self.assertEqual(frame_hitboxes(session.data,2,263)[0].values,(-10,5,-4,22,14,18))
        self.assertEqual(len(session.undo_stack),1)
        self.assertEqual(session.data[:box.offset],d[:box.offset])
        self.assertEqual(session.data[box.offset+6:],d[box.offset+6:])
        session.undo();self.assertEqual(session.data,d)
        session.redo();self.assertEqual(frame_hitboxes(session.data,2,263)[0].width,22)
        with self.assertRaisesRegex(ValueError,'Stale'):edit_collision(session,box,box.values)

    def test_global_bank_uses_global_root(self):
        d=collision_fixture();sp=2048+2*2048+40
        struct.pack_into('<2I',d,0,sp,sp+320)
        self.assertEqual(frame_hitboxes(d,427,7)[0].values,(-8,4,-2,16,12,20))

    def test_ranges_missing_and_outside_table(self):
        d=collision_fixture();box=frame_hitboxes(d,2,263)[0]
        for values in ((128,0,0,1,1,1),(0,0,0,256,1,1),(0,0,0,-1,1,1),(True,0,0,1,1,1)):
            with self.assertRaises(ValueError):prepare_collision_edit(d,box,values)
        self.assertIsNone(prepare_collision_edit(d,box,box.values))
        sp=2048+2*2048+40;struct.pack_into('<h',d,sp+219,-1)
        self.assertEqual(frame_hitboxes(d,2,263),[])
        struct.pack_into('<h',d,sp+219,12)
        with self.assertRaisesRegex(ValueError,'outside collision table'):frame_hitboxes(d,2,263)


if __name__=='__main__':unittest.main()
