"""2026-10-22: project switches / variables / Self Switches kept in a companion memory-card file
(native_save_persistence); the native save block code path is only redirected, not changed."""
import struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
import native_save_persistence as N

EXE = ROOT / 'game' / 'disc' / 'ALUN_CD.EXE'


class SavePersistence(unittest.TestCase):
    def test_layout_constants(self):
        self.assertEqual(N.ENTRY, 8 + 1024)
        self.assertEqual(N.SIZE % 128, 0)
        self.assertGreaterEqual(N.SIZE, 0x200 + 4 * N.ENTRY)
        self.assertLessEqual(N.SIZE, 0x2000)              # one card block
        self.assertEqual(len(N.NAME), 20)                 # same length as the game's own file name
        block = N.data_block()
        self.assertEqual(len(block), N.SIZE + 64)
        self.assertTrue(block[N.SIZE:].startswith(b'bu00:' + N.NAME + b'\0'))
        self.assertTrue(block[N.SIZE + 32:].startswith(b'bu10:' + N.NAME + b'\0'))

    def test_hooks_call_the_native_routines(self):
        save, load = N.emit(0x8001F000, 0x8001E000, 0x8001C000, 0x8001D300)
        words = lambda code: struct.unpack('<%dI' % (len(code) // 4), code)
        jal = lambda t: 0x0C000000 | (t >> 2) & 0x3FFFFFF
        sw = words(save)
        for target in (N.WRITE, N.OPEN, N.READ, N.BWRITE, N.CLOSE):
            self.assertIn(jal(target), sw)
        self.assertEqual(sw.index(jal(N.WRITE)), min(sw.index(jal(t)) for t in (N.WRITE, N.OPEN)))   # native write first
        self.assertEqual(sw[-2], 0x03E00008)              # jr ra
        lw = words(load)
        self.assertNotIn(jal(N.BWRITE), lw)               # loading never writes the card
        self.assertIn(0x0C000000 | (N.RESTORE >> 2) & 0x3FFFFFF, lw[:12])   # the native copy runs first

    @unittest.skipUnless(EXE.exists(), 'private stock EXE')
    def test_injection_patches_both_sites(self):
        from project_state_runtime import inject_private_state, verify_private_state_injection
        exe = EXE.read_bytes()
        from project_state_registry import ProjectStateRegistry
        doc = {}; ProjectStateRegistry(doc).create('switches', 'A')
        out, man = inject_private_state(exe, doc)
        load = man['new_load']; p = man['save_persistence']
        word = lambda a: struct.unpack_from('<I', out, a - load + 0x800)[0]
        self.assertEqual(word(N.SAVE_SITE), 0x0C000000 | (p['save_hook'] >> 2) & 0x3FFFFFF)
        self.assertEqual(word(N.LOAD_SITE), 0x0C000000 | (p['load_hook'] >> 2) & 0x3FFFFFF)
        self.assertEqual(word(N.LOAD_SITE + 4), 0)   # delay slot unchanged (stock nop)
        self.assertTrue(verify_private_state_injection(out, man)['memory_card_persistent'])
        self.assertGreaterEqual(load, 0x80018000)

    @unittest.skipUnless(EXE.exists(), 'private stock EXE')
    def test_verify_rejects_changed_code(self):
        exe = bytearray(EXE.read_bytes()); load = struct.unpack_from('<I', exe, 0x18)[0]
        N.verify(bytes(exe), load)
        exe[N.SAVE_SITE - load + 0x800] ^= 1
        with self.assertRaises(ValueError):
            N.verify(bytes(exe), load)


if __name__ == '__main__':
    unittest.main()
