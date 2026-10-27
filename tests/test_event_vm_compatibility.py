import hashlib
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from event_vm_compatibility import verify_event_vm_abi, DISPATCH_TABLE_ADDRESS, verify_sprite_callback_abi, SPRITE_CALLBACK_ROOTS


class EventAbiTests(unittest.TestCase):
    def setUp(self):
        self.stock = bytearray(0xA0000)
        self.stock[:8] = b'PS-X EXE'
        struct.pack_into('<2I', self.stock, 0x18, 0x80020000, len(self.stock)-2048)
        table = 2048 + DISPATCH_TABLE_ADDRESS - 0x80020000
        struct.pack_into('<I', self.stock, table+13*4, 0x80030000)
        for bank in 'ACDEF':
            native_table = 0x80050000 + 'ABCDEF'.index(bank)*1024
            struct.pack_into('<I', self.stock, 2048+SPRITE_CALLBACK_ROOTS-0x80020000+'ABCDEF'.index(bank)*4, native_table)
            struct.pack_into('<I', self.stock, 2048+native_table-0x80020000+255*4, 0x80030000)
        self.hash = patch('event_vm_compatibility.STOCK_EXE_SHA256', hashlib.sha256(self.stock).hexdigest())
        self.hash.start()
        self.addCleanup(self.hash.stop)

    def test_unrelated_mod_is_allowed(self):
        mod = bytearray(self.stock)
        mod[-1] = 7
        self.assertTrue(verify_event_vm_abi(mod, self.stock, [0, 13, 255])['relevant_handler_signatures_compatible'])

    def test_handler_and_dispatch_changes_rejected(self):
        for offset in (2048+0x10000, 2048+DISPATCH_TABLE_ADDRESS-0x80020000+13*4):
            mod = bytearray(self.stock)
            mod[offset] ^= 1
            with self.assertRaises(ValueError):
                verify_event_vm_abi(mod, self.stock, [13])

    def test_header_and_reference_validation(self):
        with self.assertRaises(ValueError):
            verify_event_vm_abi(b'bad', self.stock, [13])
        with self.assertRaises(ValueError):
            verify_event_vm_abi(self.stock, b'bad', [13])
        with self.assertRaises(ValueError):
            verify_event_vm_abi(self.stock, self.stock, [256])

    def test_sprite_builtin_accepts_unrelated_mod_and_null_handlers(self):
        mod = bytearray(self.stock); mod[-1] = 17
        result = verify_sprite_callback_abi(mod, self.stock, [('A', 255), ('C', 0), ('F', 255)])
        self.assertTrue(result['callback_entry_signatures_compatible'])
        self.assertTrue(result['callbacks'][1]['null_handler'])

    def test_sprite_dispatch_root_entry_and_handler_reject(self):
        offsets = [2048+SPRITE_CALLBACK_ROOTS-0x80020000,
                   2048+0x80050000-0x80020000+255*4, 2048+0x10000,
                   2048+0x800391FC-0x80020000]
        for offset in offsets:
            mod = bytearray(self.stock); mod[offset] ^= 1
            with self.assertRaises(ValueError):
                verify_sprite_callback_abi(mod, self.stock, [('A', 255)])

    def test_sprite_invalid_selector_rejects(self):
        for row in [('B', 0), ('A', 256), ('A', True)]:
            with self.assertRaises(ValueError):
                verify_sprite_callback_abi(self.stock, self.stock, [row])


if __name__ == '__main__':
    unittest.main()
