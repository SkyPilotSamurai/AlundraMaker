import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import intro_skip
from editor_session import EditSession


def exe_fixture():
    data=bytearray(0x14000);data[:8]=b'PS-X EXE'
    struct.pack_into('<4I',data,0x10,0x80020000,0,0x80020000,len(data)-0x800)
    for address,old,new,label in intro_skip.EXE_FIELDS:
        struct.pack_into('<I',data,0x800+address-0x80020000,old)
    return data


def session_fixture():
    start=100;body=intro_skip.RETAINED_SETUP+intro_skip.FIRST_WAKE_BODY+b'\x00'*20+intro_skip.COMPLETION_TAIL
    end=start+5+len(body)-1
    data=bytearray(512);data[start:start+5]=b'\x30\x00\x00'+struct.pack('<h',end-start)
    data[start+5:end+1]=body
    return EditSession(data,verify=False),[(start,0x30,5),(end,255,1)]


class IntroSkipTests(unittest.TestCase):
    def test_spawn_native_preimages_coordinates_and_length(self):
        exe=exe_fixture();before=bytes(exe);patched,sites=intro_skip.patch_intro_spawn(exe)
        self.assertEqual(len(patched),len(exe));self.assertEqual(bytes(exe),before)
        self.assertEqual(len(sites),7)
        for address,old,new,label in intro_skip.EXE_FIELDS:
            self.assertEqual(struct.unpack_from('<I',patched,0x800+address-0x80020000)[0],new)

    def test_first_wake_guard_tail_and_jump_preserved_undo_exact(self):
        session,rows=session_fixture();before=bytes(session.data)
        with patch.object(intro_skip,'instructions',return_value=rows):
            exe,report=intro_skip.apply_intro_skip(exe_fixture(),session)
            offset=int(report['process']['patch_file_offset'],16)
            target=offset+3+struct.unpack_from('<h',session.data,offset+4)[0]
            self.assertEqual(session.data[offset:offset+4],b'\x59\x81\x00\x02')
            self.assertEqual(session.data[target:target+len(intro_skip.COMPLETION_TAIL)],intro_skip.COMPLETION_TAIL)
            self.assertEqual(session.data[:offset],before[:offset])
            self.assertEqual(session.data[offset+12:],before[offset+12:])
            self.assertFalse(report['gameplay_verified'])
            self.assertFalse(report['process']['mass_progression_flags'])
            undo_count=len(session.undo_stack)
            again,_=intro_skip.apply_intro_skip(exe,session)
            self.assertEqual(again,exe);self.assertEqual(len(session.undo_stack),undo_count)
        session.undo();self.assertEqual(bytes(session.data),before)

    def test_skip_intro_can_preserve_spawn_for_open_world_entry_patch(self):
        session,rows=session_fixture();exe=exe_fixture()
        with patch.object(intro_skip,'instructions',return_value=rows):
            result,report=intro_skip.apply_intro_skip(exe,session,patch_spawn=False)
        self.assertEqual(result,bytes(exe))
        self.assertIsNone(report['spawn'])
        self.assertFalse(report['spawn_fields_patched'])
        self.assertEqual(session.data[109:113],b'\x59\x81\x00\x02')

    def test_conflicting_exe_rejected_before_datas_mutation(self):
        session,rows=session_fixture();before=bytes(session.data);exe=exe_fixture()
        struct.pack_into('<I',exe,0x12558,0)
        with patch.object(intro_skip,'instructions',return_value=rows):
            with self.assertRaisesRegex(ValueError,'instruction changed'):
                intro_skip.apply_intro_skip(exe,session)
        self.assertEqual(bytes(session.data),before);self.assertEqual(session.undo_stack,[])

    def test_prepended_module_uses_header_address_mapping(self):
        old=exe_fixture();shift=0x1000
        candidate=old[:0x800]+bytes(shift)+old[0x800:]
        struct.pack_into('<II',candidate,0x18,0x80020000-shift,len(candidate)-0x800)
        patched,sites=intro_skip.patch_intro_spawn(candidate)
        self.assertEqual(int(sites[0]['file_offset'],16),0x1254c+shift)
        self.assertEqual(struct.unpack_from('<I',patched,0x12558+shift)[0],0x240200a3)

    def test_changed_story_process_rejected(self):
        session,rows=session_fixture();session.data[109]=0xff
        with patch.object(intro_skip,'instructions',return_value=rows):
            with self.assertRaisesRegex(ValueError,'setup commands changed'):
                intro_skip.intro_process_plan(session)
        session,rows=session_fixture();session.data[rows[-1][0]-1]=0x11
        with patch.object(intro_skip,'instructions',return_value=rows):
            with self.assertRaisesRegex(ValueError,'completion flags changed'):
                intro_skip.intro_process_plan(session)


if __name__=='__main__':unittest.main()
