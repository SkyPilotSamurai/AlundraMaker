import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from native_event_authoring import compile_command
import native_player_swap as nps


class PlayerSwapEventTests(unittest.TestCase):
    def test_compiles_alundra_and_meia_only(self):
        self.assertEqual(compile_command({'type': 'change_player_character', 'character': 'Meia'}), b'\xEB\x01')
        self.assertEqual(compile_command({'type': 'change_player_character', 'character': 'Alundra'}), b'\xEB\x00')
        with self.assertRaises(ValueError):
            compile_command({'type': 'change_player_character', 'character': 'Elene'})

    def test_logic_compiler_emits_opcode(self):
        from event_logic_compile import compile_logic
        out = compile_logic([{'type': 'change_player_character', 'character': 'Meia'}])
        self.assertIn(b'\xEB\x01', bytes(out if isinstance(out, (bytes, bytearray)) else out[0]))

    def test_handler_layout(self):
        code = nps.emit(0x80019000, 0x80019010, 0x80019100, 0x80019200)
        words = struct.unpack('<%dI' % (len(code) // 4), code)
        self.assertEqual(words[-2:], (0x03E00008, 0))
        self.assertEqual(words[-3], 0x24020002)          # v0 = 2 (opcode size)
        self.assertIn(0x40000000 | 25 << 16 | 12 << 11, words)   # mfc0 t9, SR

    def test_runs_merge_small_gaps(self):
        self.assertEqual(nps._runs([0, 4, 8, 40], 2), [(0, 8), (40, 40)])
        self.assertEqual(nps.max_span_words(struct.pack('<I', 192 | 490 << 10 | 8 << 19) + bytes(32) + bytes(4)), 8)

    def test_no_dash_word_in_ram_list(self):
        import types
        nps_patch = nps.patch_data
        stock = bytearray(0x40); struct.pack_into('<3I', stock, 0, 0x800, 0x800, 0)
        # bank empty: only the code word entry and terminator (texture parts mocked)
        import texture_codec
        real = texture_codec.unpack_ez
        texture_codec.unpack_ez = lambda data, limit=0: (bytes(262144), 0)
        try:
            ram, vram = nps_patch(bytes(stock) + bytes(0x1000), bytes(stock) + bytes(0x1000), True)
        finally:
            texture_codec.unpack_ez = real
        self.assertEqual(ram, struct.pack('<3I', nps.NO_DASH, 1, 0x10) + bytes(8))
        self.assertEqual(vram, bytes(4))

    def test_disc_chunks_keep_records_whole(self):
        span = lambda x, y, n: struct.pack('<I', x | y << 10 | n << 19) + bytes(range(1, 4 * n + 1))
        vram = span(320, 256, 18) * 70 + bytes(4)           # 70 x 76 bytes: crosses one 4 KB chunk
        ram = struct.pack('<2I', 0x800CC000, 300) + bytes(1200) + bytes(8)
        blob, count = nps.disc_blob(ram, vram)
        self.assertEqual(len(blob), count * nps.CHUNK); self.assertEqual(count, 2)
        first = blob[:nps.CHUNK]
        self.assertEqual(struct.unpack_from('<2I', first, 0), (0x800CC000, 256))          # runs split at 256 words
        self.assertEqual(struct.unpack_from('<2I', first, 8 + 1024), (0x800CC400, 44))
        code = nps.emit_disc(0x80019000, 0x80019100, 0x8001A100, 0x067E7000, count)
        words = struct.unpack('<%dI' % (len(code) // 4), code)
        self.assertIn(0x0C000000 | (nps.READ_FILE >> 2) & 0x3FFFFFF, words)
        self.assertEqual(words[-2:], (0x03E00008, 0x27BD0028))

    def test_verify_exe_rejects_other_code(self):
        exe = bytearray(0x800 + 0x70000); struct.pack_into('<4I', exe, 0x10, 0, 0, 0x80020000, 0x70000)
        with self.assertRaises(ValueError):
            nps.verify_exe(bytes(exe))

    def test_dialog_labels_meia_options(self):
        text = (Path(__file__).resolve().parents[1] / 'tools' / 'event_command_dialog.py').read_text(encoding='utf-8')
        self.assertIn("label='Meia basic attack'", text)
        self.assertIn("label='Alundra for other actions'", text)


if __name__ == '__main__':
    unittest.main()
