import struct, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
import confirm_button_swap as cb


def synthetic(sites):
    exe = bytearray(0x800 + 0x40000); struct.pack_into('<II', exe, 0x18, 0x80020000, 0x40000)
    for address, stock, context, rel, _ in sites:
        at = 0x800 + address - 0x80020000
        struct.pack_into('<I', exe, at, stock); struct.pack_into('<I', exe, at + 4 * rel, context)
    return bytes(exe)


class ConfirmButtonSwap(unittest.TestCase):
    def test_sites_become_square_only(self):
        for sites in (cb.ALUN_SITES, cb.SLUS_SITES):
            exe = synthetic(sites); out, report = cb.patch(exe, sites, 'x')
            self.assertEqual(sum(a != b for a, b in zip(exe, out)), len(sites))
            for address, stock, *_ in sites:
                self.assertEqual(struct.unpack_from('<I', out, 0x800 + address - 0x80020000)[0], (stock & ~0xFFFF) | 0x80)
            self.assertEqual(cb.patch(out, sites, 'x')[0], out)   # idempotent

    def test_jump_is_not_a_site(self):
        self.assertNotIn(0x8003253C, [s[0] for s in cb.ALUN_SITES])

    def test_unexpected_code_refused(self):
        exe = bytearray(synthetic(cb.ALUN_SITES)); exe[0x800 + cb.ALUN_SITES[0][0] - 0x80020000 - 8] ^= 1
        with self.assertRaises(ValueError): cb.patch_alun(bytes(exe))

    def test_slus_option(self):
        import mod_export
        self.assertIn('confirm', mod_export._slus_options({'confirm_square': True}))
        self.assertNotIn('confirm', mod_export._slus_options({'confirm_square': False}))

    def test_stock_executables(self):
        disc = ROOT / 'game/disc'
        if not (disc / 'ALUN_CD.EXE').exists(): self.skipTest('no private inputs')
        cb.patch_alun((disc / 'ALUN_CD.EXE').read_bytes()); cb.patch_slus((disc / 'SLUS_005.53').read_bytes())


if __name__ == '__main__': unittest.main()
