"""Magic & weapon swap mod option (tools/magic_weapon_swap.py) and the tabbed Mod options page."""
import struct, sys, unittest
from pathlib import Path
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
import magic_weapon_swap as mws

EXE = ROOT / 'game' / 'disc' / 'ALUN_CD.EXE'
LOAD = 0x80020000


def _fake():
    size = 0xAC000
    exe = bytearray(0x800 + size); exe[:8] = b'PS-X EXE'; struct.pack_into('<II', exe, 0x18, LOAD, size)
    put = lambda a, w: struct.pack_into(f'<{len(w)}I', exe, 0x800 + a - LOAD, *w)
    put(mws.BEST, mws.BEST_STOCK); put(mws.MENU_HOOK, mws.MENU_STOCK); put(0x8005869C, (0x30420040,))
    for f, h in mws.CALLEE_HEADS.items():
        if h is not None: put(f, (h,))
    put(0x800BBCD0 + 48, (0x8004FA44, 0x8004FA64, 0x8004FA84, 0x8004FAA4))
    return exe


class MagicWeaponSwap(unittest.TestCase):
    def test_validate_and_hooks(self):
        exe = _fake(); mws.validate(bytes(exe))
        rep = mws.patch_hooks(exe, 0x8001F000)
        w = lambda a: struct.unpack_from('<I', exe, 0x800 + a - LOAD)[0]
        self.assertEqual(w(mws.BEST), 0x08000000 | (0x8001F000 >> 2 & 0x3FFFFFF))
        self.assertEqual(w(mws.BEST + 4), 0)
        self.assertEqual(w(mws.MENU_HOOK), 0x0C000000 | (int(rep['circle_hook'], 16) >> 2 & 0x3FFFFFF))
        self.assertEqual(w(mws.MENU_HOOK + 4), 0x2610DA4E)          # delay slot kept
        self.assertEqual(rep['module'], 'ALUN_CD.EXE')

    def test_changed_code_refused(self):
        exe = _fake(); struct.pack_into('<I', exe, 0x800 + mws.MENU_HOOK - LOAD + 16, 0x30420812)
        with self.assertRaises(ValueError): mws.validate(bytes(exe))

    def test_square_confirm_accepted(self):
        exe = _fake(); struct.pack_into('<I', exe, 0x800 + 0x8005869C - LOAD, 0x30420080); mws.validate(bytes(exe))

    def test_block(self):
        raw = mws.Block()(0x8001F000); self.assertEqual(len(raw), mws.SIZE)
        words = struct.unpack(f'<{mws.SIZE // 4}I', raw)
        self.assertEqual(raw[-32:], bytes(32))                       # pick table starts empty (stock best)
        self.assertIn(0x08000000 | ((mws.BEST + 8) >> 2 & 0x3FFFFFF), words)     # best_hook falls back into the stock body
        self.assertIn(0xAFBF0010, words); self.assertIn(0x27BDFFE8, words)   # displaced prologue redone
        self.assertEqual(words[-8 - 3:-8], (0x3C10801E, 0x03E00008, 0x2610DA4E))   # s0 = pad repeat on return
        _, circle, picks = mws._code_words(0x8001F000)
        self.assertEqual(picks, 0x8001F000 + mws.SIZE - 32)

    @unittest.skipUnless(EXE.exists(), 'local US1.1 executable not present')
    def test_retail_signature(self):
        mws.validate(EXE.read_bytes())

    def test_qol_option(self):
        import editor_qol, inspect
        src = inspect.getsource(editor_qol.apply_qol)
        self.assertIn("options.get('magic_weapon_swap') is True", src)


class RegularItemSounds(unittest.TestCase):
    def test_split_from_remove_cutscenes(self):
        import editor_qol, inspect
        src = inspect.getsource(editor_qol.apply_qol)
        cut = src[src.index("if requested['remove_cutscenes']:"):src.index("if options.get('regular_item_sounds') is True:")]
        self.assertNotIn('remove_item_fanfares', cut)
        self.assertIn('remove_item_fanfares', src[src.index("if options.get('regular_item_sounds') is True:"):])

    @unittest.skipUnless(EXE.exists(), 'local US1.1 executable not present')
    def test_fanfare_bytes(self):
        import cutscene_removal as cr
        exe = EXE.read_bytes(); new, rep = cr.remove_item_fanfares(exe)
        self.assertTrue(rep['items']); self.assertNotEqual(new, exe)


class ModOptionTabs(unittest.TestCase):
    def test_tabs_load_and_save(self):
        try:
            import tkinter as tk
            root = tk.Tk(); root.withdraw()
        except Exception as exc: self.skipTest(f'no Tk: {exc}')
        try:
            import editor_ui as ui
            doc = {}
            stub = SimpleNamespace(root=root, database=SimpleNamespace(document=doc), dirty=False,
                                   status=tk.StringVar(), guard=lambda f: f(), update_title=lambda: None,
                                   choose_game_bin=lambda: None, save_project_preferences=lambda: None,
                                   choose_emulator=lambda: None, set_balance=lambda w: None,
                                   show_balance_state=lambda: None, select_initial_map=lambda: None)
            for name in ('update_meia_option_state', 'change_mod_options'):
                setattr(stub, name, getattr(ui.Editor, name).__get__(stub))
            ui.Editor.preferences_windows(stub)
            for w in stub.preference_windows.values(): w.withdraw()
            tabs = [stub.mod_tabs.tab(t, 'text') for t in stub.mod_tabs.tabs()]
            self.assertEqual(tuple(tabs), ui.MOD_OPTION_TABS)
            self.assertFalse(stub.mod_option_vars['magic_weapon_swap'].get())     # off by default
            for key in ui.MOD_OPTION_TAB_OF: self.assertIn(key, stub.mod_option_vars)
            stub.mod_option_vars['magic_weapon_swap'].set(True); stub.mod_option_vars['confirm_square'].set(True)
            stub.change_mod_options()
            self.assertTrue(doc['mod_options']['magic_weapon_swap']); self.assertTrue(doc['mod_options']['confirm_square'])
            self.assertTrue(doc['mod_options']['more_sound_room'])
            self.assertFalse(doc['mod_options']['regular_item_sounds'])
            self.assertEqual(ui.MOD_OPTION_TAB_OF['magic_weapon_swap'], 'Controls')
        finally:
            root.destroy()


if __name__ == '__main__': unittest.main()
