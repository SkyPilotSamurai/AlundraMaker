import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from entity_animation import parse_sprite_animation_record, prepare_animation_edit, _read_stream, MAX_ANIMATION_STREAM_FRAMES
from editor_session import EditSession


def synthetic_sprite():
    data=bytearray(420);start=64;end=400
    struct.pack_into("<i",data,start+48,64)  # sprite slot 0 -> record at 128
    record=start+64
    struct.pack_into("<4I",data,record,96,110,164,184)
    # One 14-byte set: four relative streams, unsigned speed, opaque tail.
    struct.pack_into("<4hH4B",data,record+32,0,16,-1,-1,17,9,8,7,6)
    first=record+46
    data[first:first+5]=bytes([0x82,0xff,0xff,2,0])
    data[first+5:first+10]=bytes([0x85,0x03,0,4,0])
    data[first+10:first+12]=bytes([0,0x31])
    second=first+16
    data[second:second+5]=bytes([0x81,0xff,0xff,4,0])
    data[second+5:second+7]=bytes([0,0x44])
    return data,start,end


class EntityAnimationTests(unittest.TestCase):
    def test_valid72_frame_native_loop_is_preserved_and_editable(self):
        raw=bytes([0x81,0xff,0xff,2,0])*72+bytes([1])
        stream=_read_stream(raw,0,len(raw),0,0)
        self.assertEqual(len(stream.frames),72);self.assertEqual(stream.terminator,b'\x01')
        self.assertEqual(b''.join(f.raw for f in stream.frames)+stream.terminator,raw)

    def test_long_stream_still_requires_section_terminator_and_resource_bound(self):
        raw=bytes([0x81,0xff,0xff,2,0])*72
        with self.assertRaisesRegex(ValueError,'outside'):_read_stream(raw,0,len(raw),0,0)
        raw=bytes([0x81,0xff,0xff,2,0])*(MAX_ANIMATION_STREAM_FRAMES+1)+b'\x01'
        with self.assertRaisesRegex(ValueError,'resource bound'):_read_stream(raw,0,len(raw),0,0)
    def test_reads_set_speed_direction_streams_and_transition_marker(self):
        data,start,end=synthetic_sprite()
        sets=parse_sprite_animation_record(data,start,end,0,48,52)
        self.assertEqual(len(sets),1)
        anim=sets[0]
        self.assertEqual(anim.speed_raw,17)
        self.assertEqual(anim.tail,bytes([9,8,7,6]))
        self.assertEqual([f.image_set_index for f in anim.streams[0].frames],[2,4])
        self.assertEqual(anim.streams[0].terminator,bytes([0,0x31]))
        self.assertEqual(anim.streams[1].frames[0].delay_raw,0x81)
        self.assertIsNone(anim.streams[2])

    def test_edits_speed_order_and_known_sources_without_changing_stream_size(self):
        data,start,end=synthetic_sprite()
        anim=parse_sprite_animation_record(data,start,end,0,48,52)[0]
        stream=anim.streams[0]
        changes=prepare_animation_edit(data,anim,stream,258,[1,0],{0:{"delay_raw":0x8a,"image_set_index":2}})
        self.assertEqual(len(changes),2)
        for offset,replacement,_ in changes:data[offset:offset+len(replacement)]=replacement
        reread=parse_sprite_animation_record(data,start,end,0,48,52)[0]
        self.assertEqual(reread.speed_raw,258)
        sequence=reread.streams[0]
        self.assertEqual([f.image_set_index for f in sequence.frames],[4,2])
        self.assertEqual(sequence.frames[1].delay_raw,0x8a)
        self.assertEqual(sequence.terminator,bytes([0,0x31]))
        self.assertEqual(data[anim.offset+10:anim.offset+14],bytes([9,8,7,6]))

    def test_animation_edits_are_undoable_redoable_and_patchable(self):
        data,start,end=synthetic_sprite()
        original=bytes(data);anim=parse_sprite_animation_record(data,start,end,0,48,52)[0]
        changes=prepare_animation_edit(data,anim,anim.streams[0],321,[1,0],{0:{"delay_raw":0x8a}})
        session=EditSession(original,verify=False)
        for offset,replacement,label in changes:session.replace(offset,replacement,label)
        edited=bytes(session.data)
        self.assertNotEqual(edited,original)
        for _ in changes:session.undo()
        self.assertEqual(bytes(session.data),original)
        for _ in changes:session.redo()
        self.assertEqual(bytes(session.data),edited)
        fresh=EditSession(original,verify=False);fresh.apply_patch(session.patch())
        self.assertEqual(bytes(fresh.data),edited)

    def test_rejects_stream_growth_bad_order_unknown_image_and_marker_loss(self):
        data,start,end=synthetic_sprite();anim=parse_sprite_animation_record(data,start,end,0,48,52)[0]
        stream=anim.streams[0]
        with self.assertRaises(ValueError):prepare_animation_edit(data,anim,stream,1,[0])
        with self.assertRaises(ValueError):prepare_animation_edit(data,anim,stream,1,[0,0])
        with self.assertRaises(ValueError):prepare_animation_edit(data,anim,stream,1,[0,1],{0:{"image_set_index":65535}})
        with self.assertRaises(ValueError):prepare_animation_edit(data,anim,stream,1,[0,1],{0:{"delay_raw":4}})

    def test_rejects_unbounded_pointer_or_missing_terminator(self):
        data,start,end=synthetic_sprite()
        with self.assertRaises(ValueError):parse_sprite_animation_record(data,start,end,1,48,52)
        broken=bytearray(data);record=start+64
        struct.pack_into("<h",broken,record+32,500)
        with self.assertRaises(ValueError):parse_sprite_animation_record(broken,start,end,0,48,52)


if __name__=="__main__":unittest.main()
