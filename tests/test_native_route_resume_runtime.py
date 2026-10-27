import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_route_resume_runtime import emit,emit_indexed,inject,verify_contract
INPUT=Path(__file__).resolve().parents[1]/'game/disc/ALUN_CD.EXE'

class ResumeEmitterTests(unittest.TestCase):
    def test_independent_interpreter_guards_slot_and_owner_and_restores_only_its_context(self):
        from test_project_state_runtime import execute_handler
        owner=0x801AC6F8+12*0x294;storage=0x8001D000
        state={storage+i:0 for i in range(0,160,4)}
        state.update({owner+0x234+i:100+i for i in range(0,64,4)})
        state.update({owner+0x10:2,owner+0x88:1,owner+0x8C:24})
        result,_,invalid=execute_handler(emit_indexed(0xE6,storage,2),bytes((0xE6,2)),state,owner=owner)
        self.assertEqual(result,0);self.assertEqual(invalid,state)
        result,_,saved=execute_handler(emit_indexed(0xE6,storage,2),bytes((0xE6,1)),state,owner=owner)
        self.assertEqual(result,2);self.assertEqual(saved[storage+80+4],104)
        self.assertEqual(saved[storage+80+72],owner);self.assertEqual(saved[storage+80+76],1)
        self.assertEqual([saved[storage+i] for i in range(0,80,4)],[0]*20)
        other=owner+0x294;saved[other+0x10]=2
        result,_,rejected=execute_handler(emit_indexed(0xE7,storage,2),bytes((0xE7,1)),saved,owner=other)
        self.assertEqual(result,0);self.assertEqual(rejected,saved)
        for i in range(0,64,4):saved[owner+0x234+i]=999
        saved[owner+0x88]=0;saved[owner+0x8C]=0
        result,_,restored=execute_handler(emit_indexed(0xE7,storage,2),bytes((0xE7,1)),saved,owner=owner)
        self.assertEqual(result,0)
        self.assertEqual([restored[owner+0x234+i] for i in range(0,64,4)],[100+i for i in range(0,64,4)])
        self.assertEqual((restored[owner+0x88],restored[owner+0x8C]),(1,24))
        self.assertEqual(restored[storage+80+76],0)

    def test_snapshot_and_restore_use_distinct_return_contracts(self):
        snapshot=emit(0xE6,0x8001D000);restore=emit(0xE7,0x8001D000)
        self.assertTrue(snapshot.endswith(struct.pack('<3I',0x24020001,0x03E00008,0)))
        self.assertIn(struct.pack('<3I',0x24020000,0x03E00008,0),restore)
        self.assertIn(struct.pack('<I',0xACA90238),restore) # restore owned cursor
        self.assertIn(struct.pack('<I',0xACA90088),restore) # live animation target

    def test_indexed_snapshot_validates_capacity_and_returns_two_byte_width(self):
        for slots in (0,17,True):
            with self.assertRaises(ValueError):emit_indexed(0xE6,0x8001D000,slots)
        code=emit_indexed(0xE6,0x8001D000,2)
        self.assertIn(struct.pack('<I',0x2D4B0002),code) # sltiu slot,count
        self.assertIn(struct.pack('<3I',0x24020002,0x03E00008,0),code)
        restore=emit_indexed(0xE7,0x8001D000,2)
        self.assertIn(struct.pack('<I',0xAD00004C),restore) # clear only own active slot

    @unittest.skipUnless(INPUT.exists(),'Lawful native input required')
    def test_optional_indexed_feature_is_explicit_and_zero_initialized(self):
        from project_state_runtime import inject_private_state,verify_private_state_injection
        from event_vm_compatibility import verify_event_vm_abi
        stock=INPUT.read_bytes();document={'definitions':[],'event_graphs':[]}
        default,plain=inject_private_state(stock,document)
        self.assertNotIn('route_resume',plain)
        load=struct.unpack_from('<I',default,24)[0]
        self.assertEqual(struct.unpack_from('<I',default,0x8009B814+0xE6*4-load+2048)[0],0x8003DBD0)
        with self.assertRaises(ValueError):inject_private_state(stock,document,route_resume_slots=2)
        result,manifest=inject_private_state(stock,document,optional_features=('actor_route_resume',),route_resume_slots=2)
        self.assertEqual(manifest['route_resume']['storage_size'],160)
        verify_private_state_injection(result,manifest);verify_event_vm_abi(result,stock,[0xE6,0xE7],manifest)

    @unittest.skipUnless(INPUT.exists(),'Lawful native input required')
    def test_injection_preserves_native_contract_and_protects_stack(self):
        stock=INPUT.read_bytes();original=verify_contract(stock)
        result,report=inject(stock)
        self.assertEqual(verify_contract(result),original)
        self.assertTrue(report['single_owner_only'])
        self.assertFalse(report['runtime_verified'])
        self.assertFalse(report['native_stack']['injection_stack_overlap'])
        changed=bytearray(stock);load=struct.unpack_from('<I',stock,24)[0]
        changed[0x80042E98-load+0x800]^=1
        with self.assertRaisesRegex(ValueError,'contract'):inject(changed)

if __name__=='__main__':unittest.main()
