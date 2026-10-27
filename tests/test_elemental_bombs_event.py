"""Elemental bomb effects mod option (tools/elemental_bombs.py): signatures, hook words, off = stock."""
import struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
import elemental_bombs as eb

EXE = ROOT / 'game' / 'disc' / 'ALUN_CD.EXE'


def _fake():
    load = 0x80020000; size = 0xA8000
    exe = bytearray(0x800 + size); exe[:8] = b'PS-X EXE'; struct.pack_into('<II', exe, 0x18, load, size)
    put = lambda a, w: struct.pack_into(f'<{len(w)}I', exe, 0x800 + a - load, *w)
    put(eb.D_TABLE + 120, (eb.D30,)); put(eb.C_TABLE + 248, (eb.C62,)); put(eb.D30, eb.D30_WORDS)
    put(eb.C_HOOK, eb.C62_CONTEXT); put(eb.SCAN_HOOK, eb.SCAN_CONTEXT); put(eb.MARK_HOOK - 8, eb.MARK_CONTEXT)
    return exe


class ElementalBombs(unittest.TestCase):
    def test_validate_and_hooks(self):
        exe = _fake(); eb.validate(bytes(exe))
        report = eb.patch_hooks(exe, 0x8001F000)
        w = lambda a: struct.unpack_from('<I', exe, 0x800 + a - 0x80020000)[0]
        jal = lambda t: 0x0C000000 | ((t >> 2) & 0x3FFFFFF)
        flags, mark, slow = eb.addresses(0x8001F000)
        self.assertEqual((w(eb.SCAN_HOOK), w(eb.MARK_HOOK), w(eb.C_HOOK)), (jal(flags), jal(mark), jal(slow)))
        self.assertEqual(w(eb.D30 + 64), 0x03E00008)             # D30 itself untouched
        self.assertEqual(report['module'], 'ALUN_CD.EXE')

    def test_changed_code_refused(self):
        exe = _fake(); struct.pack_into('<I', exe, 0x800 + eb.D30 - 0x80020000 + 28, 0x24020005)
        with self.assertRaises(ValueError): eb.validate(bytes(exe))

    def test_block_size_and_return(self):
        raw = eb.Block()(0x8001F000); self.assertEqual(len(raw), eb.SIZE)
        words = struct.unpack(f'<{eb.SIZE // 4}I', raw)
        self.assertEqual(words.count(0x03E00008), 3)              # all three hooks return
        self.assertIn(0xAE0801D0, words)                          # hit_mark redoes the 0x19 hit store
        self.assertIn(0x8E030274, words)                          # C62's displaced fuse load is redone
        self.assertEqual(words[len(eb.TARGET_FLAGS) + len(eb.HIT_MARK) + 13], 0x24630001)  # +1 on alternate frames

    @unittest.skipUnless(EXE.exists(), 'local US1.1 executable not present')
    def test_retail_signature(self):
        eb.validate(EXE.read_bytes())

    def test_qol_option_off_is_stock(self):
        import editor_qol, inspect
        src = inspect.getsource(editor_qol.apply_qol)
        self.assertIn("options.get('elemental_bombs') is True", src)


if __name__ == '__main__': unittest.main()
