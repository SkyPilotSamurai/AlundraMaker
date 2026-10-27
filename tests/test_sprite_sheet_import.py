"""Sprite frame replacement, per-animation sheet import, Meia action frames (private DATAS.BIN)."""
import os, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'tools'))
DATAS = ROOT / 'game' / 'disc' / 'DATA' / 'DATAS.BIN'


def frames(data, m, cat, anim, direction=0):
    from editor_session import EditSession
    from animation_preview import load_animation
    s = EditSession(bytes(data), None, verify=False)
    return [f for f in load_animation(s, m, cat, anim, direction).frames if f.image is not None]


@unittest.skipUnless(DATAS.is_file(), 'private retail DATAS.BIN not present')
class SpriteSheetImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = DATAS.read_bytes()

    def test_mirrored_pictures_round_trip_global_and_local(self):
        from PIL import ImageOps
        from sprite_frame_replace import replace_image_sets
        for m, cat, anim in ((163, 0, 0), (327, 418, 3)):
            before = frames(self.data, m, cat, anim)
            rep = {f.image_set_index: (ImageOps.mirror(f.image.convert('RGBA')), f.left, f.top) for f in before}
            out, report = replace_image_sets(self.data, cat, rep, map_id=None if cat < 256 else m)
            self.assertFalse(report['kept'])
            for f, g in zip(before, frames(out, m, cat, anim)):
                a = ImageOps.mirror(f.image.convert('RGBA')); box = a.getbbox(); a = a.crop(box)
                self.assertEqual((f.left + box[0], f.top + box[1]), (g.left, g.top))
                self.assertEqual(a.tobytes(), g.image.convert('RGBA').tobytes())
            other = [f.image.tobytes() for f in frames(self.data, m, cat, 1)]
            self.assertEqual(other, [f.image.tobytes() for f in frames(out, m, cat, 1)])

    def test_edited_sheet_is_stored_and_drawn_at_build(self):
        from PIL import Image, ImageDraw
        from editor_session import EditSession
        from sprite_sheet_import import export_sheet, import_sheet, apply_sprite_imports, remove_import
        session = EditSession(bytes(self.data), None, verify=False); doc = {}
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'sheet.png')
            entry = export_sheet(session, doc, 327, 418, 3, path)
            self.assertEqual(import_sheet(session, doc, 327, 418, 3, path)['changed'], 0)
            image = Image.open(path).convert('RGBA'); ox, oy = entry['cells'][0]['origin']
            ImageDraw.Draw(image).rectangle([ox - 2, oy - 12, ox + 2, oy - 8], fill=(0, 0, 0, 0))
            image.save(path)
            self.assertEqual(import_sheet(session, doc, 327, 418, 3, path)['changed'], 1)
        class Built: pass
        built = Built(); built.data = bytearray(self.data)
        report = apply_sprite_imports(built, doc)
        self.assertTrue(any(r.get('map_id') == 327 and r.get('replaced') == 1 for r in report), report)
        f = frames(built.data, 327, 418, 3)[0]
        self.assertEqual(f.image.convert('RGBA').getpixel((-f.left, -f.top - 10))[3], 0)
        self.assertEqual(remove_import(doc, 418, 3), 1); self.assertFalse(doc['sprite_imports'])

    def test_meia_basic_attack_modes(self):
        from editor_session import EditSession
        from player_costume import apply_costume
        for fallback in (False, True):
            s = EditSession(bytes(self.data), None, verify=False); s.data = bytearray(self.data)
            report = apply_costume(s, basic_attack=True, alundra_fallback=fallback)['meia_actions']
            if fallback:
                self.assertGreater(report['quads_painted'], 40)
            else:
                self.assertGreater(report['replaced'] + report.get('painted_in_place', 0), 200)
            self.assertGreater(report['backpack_pixels'], 1000)
            self.assertLess(len(report['head_not_found']), 10)
            self.assertTrue(frames(s.data, 163, 0, 0x3F))


if __name__ == '__main__':
    unittest.main()
