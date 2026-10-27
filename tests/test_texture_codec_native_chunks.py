"""Retail decoder returns after full tokens then resets its 32KiB output buffer."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from texture_codec import pack_ez,unpack_ez


def native_chunks(stream):
    i=6;pages=[];out=bytearray()
    while i<len(stream):
        byte=stream[i];i+=1
        if byte!=173:out.append(byte)
        else:
            distance=stream[i];i+=1
            if distance==0:out.append(173)
            else:
                count=stream[i];i+=1
                if count==0:
                    if out:pages.append(bytes(out))
                    return b''.join(pages)
                if distance>len(out):raise ValueError('Backreference before current native page')
                for _ in range(count):out.append(out[-distance])
        if len(out)>32768:raise ValueError('Native upload would discard match overflow')
        if len(out)==32768:pages.append(bytes(out));out.clear()
    raise ValueError('Missing terminator')


class NativeTextureChunksTests(unittest.TestCase):
    def test_repeated_three_pages_preserve_native_uploads(self):
        raw=bytes(32768*3)
        packed=pack_ez(raw)
        self.assertEqual(unpack_ez(packed,limit=len(raw)+1)[0],raw)
        self.assertEqual(native_chunks(packed),raw)

    def test_all_byte_values_and_partial_last_page(self):
        raw=bytes(range(256))*258+b'end'
        self.assertEqual(native_chunks(pack_ez(raw)),raw)

    def test_model_rejects_old_boundary_overflow(self):
        unsafe=b'EZ\0\0\0\0\0'+b'\xad\x01\xff'*129+b'\xad\xff\0'
        with self.assertRaisesRegex(ValueError,'discard'):
            native_chunks(unsafe)

    def test_model_rejects_previous_page_reference(self):
        first=b'\0'*32768
        with self.assertRaisesRegex(ValueError,'before current native page'):
            native_chunks(b'EZ\0\0\0\0'+first+b'\xad\x01\x10'+b'\xad\xff\0')
