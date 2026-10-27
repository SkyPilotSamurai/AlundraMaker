import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import event_editor


class Session:
    def __init__(self,data):self.data=bytearray(data)


class ReachableDecodeTests(unittest.TestCase):
    def decode(self,raw,roots=None,metadata=None):
        session=Session(raw)
        if metadata is not None:session.native_event_export_report=metadata
        roots=roots or {'F 0':(0,len(raw),0)}
        with patch.object(event_editor,'script_roots',return_value=roots):
            return event_editor.reachable_instructions(session,0,'F 0')

    def test_conditional_tail_after_early_end_is_preserved(self):
        raw=bytes.fromhex('030600ff01013701ff')
        self.assertEqual(self.decode(raw),[(0,3,3),(3,255,1),(6,0x37,2),(8,255,1)])

    def test_call_shared_root_and_return_keeps_caller_end(self):
        raw=bytes.fromhex('780700ff0101019801007dff')
        roots={'F 0':(0,len(raw),0),'C 1':(7,len(raw),0)}
        self.assertEqual(self.decode(raw,roots),[(0,0x78,3),(3,255,1),(7,0x98,3),(10,0x7D,1)])

    def test_last_unknown_does_not_swallow_record_storage(self):
        self.assertEqual(self.decode(bytes([0xFE])+bytes(20000)),[(0,0xFE,1)])

    def test_unconditional_loop_is_bounded(self):
        raw=bytes.fromhex('370102feff')
        self.assertEqual(self.decode(raw),[(0,0x37,2),(2,2,3)])

    def test_generated_private_root_requires_exact_metadata_hash(self):
        code=bytes.fromhex('e10000010405002e80ff')
        raw=code+bytes(20000)
        meta=[{'map_id':0,'bank':'F','root_index':0,'code_bytes':len(code),
               'code_sha256':hashlib.sha256(code).hexdigest()}]
        self.assertEqual(self.decode(raw,metadata=meta),[(0,0xE1,4),(4,4,3),(7,0x2E,2),(9,255,1)])
        meta[0]['code_sha256']='0'*64
        self.assertEqual(self.decode(raw,metadata=meta),[(0,0xE1,1)])

    def test_branch_into_operand_does_not_decode_fake_command(self):
        raw=bytes.fromhex('0304003701ff')
        self.assertEqual(self.decode(raw),[(0,3,3),(3,0x37,2),(5,255,1)])

    def test_bounded_generated_caller_can_enter_declared_shared_root(self):
        code=bytes.fromhex('780700ff');raw=code+bytes.fromhex('0101019801007dff')
        roots={'F 0':(0,len(raw),0),'C 1':(7,len(raw),0)}
        meta=[{'map_id':0,'bank':'F','root_index':0,'code_bytes':len(code),
               'code_sha256':hashlib.sha256(code).hexdigest()}]
        self.assertEqual(self.decode(raw,roots,meta),[(0,0x78,3),(3,255,1),(7,0x98,3),(10,0x7D,1)])


if __name__=='__main__':unittest.main()
