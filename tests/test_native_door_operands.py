"""Recovered native operands remain fixed-length edits with exact undo."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_session import EditSession
from event_editor import EDITABLE,SIZES,script_roots,instructions,edit_instruction

class DoorOperandsTests(unittest.TestCase):
    def test_sizes_and_meaning(self):
        import struct
        for opcode in (0x84,0x59,0x2E):
            self.assertEqual(1+struct.calcsize('<'+EDITABLE[opcode][1]),SIZES[opcode])
        self.assertIn('Remove one item',EDITABLE[0x84][0])
        self.assertNotIn('Give',EDITABLE[0x84][0])

    def test_stock_door_operand_edit_and_undo(self):
        source=ROOT/'game/disc/DATA/DATAS.BIN'
        if not source.exists():self.skipTest('Private input unavailable')
        session=EditSession(source.read_bytes());original=bytes(session.data)
        checked=set()
        for key in script_roots(session,42):
            for offset,opcode,size in instructions(session,42,key):
                if opcode not in (0x84,0x59,0x2E) or opcode in checked:continue
                import struct
                values=list(struct.unpack_from('<'+EDITABLE[opcode][1],session.data,offset+1))
                values[-1]=(values[-1]+1)%256
                edit_instruction(session,42,key,offset,values)
                self.assertEqual(len(session.data),len(original))
                self.assertEqual(session.data[:offset],original[:offset])
                self.assertEqual(session.data[offset+size:],original[offset+size:])
                session.undo();self.assertEqual(bytes(session.data),original)
                checked.add(opcode)
        self.assertEqual(checked,{0x84,0x59,0x2E})

if __name__=='__main__':unittest.main()
