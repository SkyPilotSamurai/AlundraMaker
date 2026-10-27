import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_save_coverage import SIGNATURES,preflight_words,analyse,native_checksum,catalogue_entries,STOCK_SHA256


def fixture(load=0x80020000):
    end=max(address+4*len(words) for address,words in SIGNATURES.items())
    size=(end-load+2047)&~2047
    raw=bytearray(2048+size);raw[:8]=b'PS-X EXE'
    struct.pack_into('<4I',raw,0x10,load,0,load,size)
    for address,words in SIGNATURES.items():
        struct.pack_into('<'+'I'*len(words),raw,address-load+2048,*words)
    return raw


class SaveCoverageTests(unittest.TestCase):
    def test_exact_sites_and_header_mapping(self):
        for load in (0x80020000,0x80010000):
            result=preflight_words(fixture(load))
            row=next(r for r in result if r['virtual_address']=='0x80031B1C')
            self.assertEqual(int(row['exe_offset'],16),0x80031b1c-load+2048)

    def test_modified_site_and_unfingerprinted_build_rejected(self):
        d=fixture();d[0x80031b20-0x80020000+2048]^=1
        with self.assertRaisesRegex(ValueError,'site mismatch'):preflight_words(d)
        with self.assertRaisesRegex(ValueError,'fingerprinted'):analyse(fixture())

    def test_checksum_initial_polynomial_final_vector(self):
        self.assertEqual(native_checksum(b''),0)
        self.assertEqual(native_checksum(b'123456789'),0xfc891918)

    def test_catalogue_schema_preserves_build_evidence_and_no_runtime_claim(self):
        rows=catalogue_entries(dict(module='ALUN_CD.EXE',sha256=STOCK_SHA256,
            build='Exact test build',confidence='Static',limits=['No runtime proof'],native_sites=[]))
        self.assertEqual(len(rows),14)
        self.assertEqual(len({r['id'] for r in rows}),14)
        for row in rows:
            self.assertEqual(row['details']['module_sha256'],STOCK_SHA256)
            self.assertEqual(row['details']['build'],'Exact test build')
            self.assertFalse(row['details']['runtime_verified'])
            self.assertEqual(row['source'],'data/native-save-flag-coverage.json')

    def test_entire_flag_bank_inside_copy_and_checksum_span(self):
        base=0x801dd2d8;flag=0x801dd334;span=0x758
        self.assertEqual(flag-base,0x5c)
        for slot in range(4):
            destination=0x200+slot*0x76c
            self.assertLessEqual(destination+span,0x1ffc)
            self.assertLessEqual((flag-base)+256,span)
            # Both edges of the copied bank affect the reconstructed checksum.
            empty=bytes(0x1ffc)
            for n in (0,255):
                changed=bytearray(empty);changed[destination+(flag-base)+n]=0x80
                self.assertNotEqual(native_checksum(changed),native_checksum(empty))


if __name__=='__main__':unittest.main()
