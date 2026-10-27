import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from native_item_grant import compile_item_grant,grant_step
from event_vm_compatibility import verify_event_vm_abi

class ItemGrantTests(unittest.TestCase):
    def test_normal_native_cap_and_success_condition(self):
        self.assertEqual(grant_step(0,9),(1,1))
        self.assertEqual(grant_step(8,9),(9,1))
        self.assertEqual(grant_step(9,9),(9,0))
        self.assertEqual(grant_step(32767,0),(-32768,0))
    def test_bounded_direct_herb_bytes_and_message_limits(self):
        self.assertEqual(compile_item_grant(36),b'\x82\x24')
        self.assertEqual(compile_item_grant(42,3),b'\x82\x2a'*3)   # any item; quantity repeats the native add
        for item in (-1,256,True,None):
            with self.assertRaises(ValueError):compile_item_grant(item)
        for qty in (0,100,True,None):
            with self.assertRaises(ValueError):compile_item_grant(36,qty)
        with self.assertRaisesRegex(ValueError,'no automatic'):compile_item_grant(36,obtained_message='Got it')

    def test_native_grant_dependency_mutations_rejected(self):
        path=ROOT/'game/disc/ALUN_CD.EXE'
        if not path.exists():self.skipTest('Private stock module unavailable')
        stock=path.read_bytes();report=verify_event_vm_abi(stock,stock,[0x82])
        self.assertEqual(len(report['dependencies']),5)
        for row in report['dependencies']:
            candidate=bytearray(stock);candidate[int(row['address'],16)-0x80020000+0x800]^=1
            with self.assertRaisesRegex(ValueError,'grant dependency'):
                verify_event_vm_abi(candidate,stock,[0x82])

    def test_quantity_read_and_return_tail_mutations_rejected(self):
        path=ROOT/'game/disc/ALUN_CD.EXE'
        if not path.exists():self.skipTest('Private stock module unavailable')
        import struct
        stock=path.read_bytes();load=struct.unpack_from('<I',stock,0x18)[0]
        # These actual quantity-read/return instructions lay beyond the old
        # guarded ranges. A matching opcode82 entry alone was insufficient.
        for pc in (0x8004FB14,0x8004FB20,0x8004FC74,0x8004FC78):
            with self.subTest(pc=hex(pc)):
                candidate=bytearray(stock);candidate[pc-load+0x800]^=1
                with self.assertRaisesRegex(ValueError,'grant dependency'):
                    verify_event_vm_abi(candidate,stock,[0x82])

if __name__=='__main__':unittest.main()
