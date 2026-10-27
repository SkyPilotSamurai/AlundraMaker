import sys,struct,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from editor_start_point import native_start_point,effective_start_point
from intro_skip import EXE_FIELDS,ARRIVAL


def exe_fixture(words=None):
    b=bytearray(0x40000);b[:8]=b'PS-X EXE'
    struct.pack_into('<4I',b,0x10,0x80020000,0,0x80020000,len(b)-0x800)
    for address,stock,intro,label in EXE_FIELDS:
        struct.pack_into('<I',b,0x800+address-0x80020000,(words or {}).get(address,stock))
    return bytes(b)


class EffectiveStartTests(unittest.TestCase):
    def test_stock_new_game_start_is_read_from_the_exe(self):
        self.assertEqual(native_start_point(exe_fixture()),{'map_id':389,'x':33,'y':35,'z':0})

    def test_modded_exe_start_is_read(self):
        words={EXE_FIELDS[0][0]:0x24120005,EXE_FIELDS[1][0]:0x24130006,EXE_FIELDS[2][0]:0x24140002,EXE_FIELDS[3][0]:0x240200F2}
        self.assertEqual(native_start_point(exe_fixture(words)),{'map_id':242,'x':5,'y':6,'z':2})

    def test_unknown_code_is_rejected(self):
        with self.assertRaises(ValueError):native_start_point(exe_fixture({EXE_FIELDS[3][0]:0}))

    def test_options_choose_the_shown_start(self):
        session=SimpleNamespace(extra_files={'ALUN_CD.EXE':SimpleNamespace(data=exe_fixture())})
        def editor(options):return SimpleNamespace(session=session,database=SimpleNamespace(document={'mod_options':options}))
        self.assertEqual(effective_start_point(editor({}))[0]['map_id'],389)
        self.assertEqual(effective_start_point(editor({'skip_intro':True}))[0],ARRIVAL)
        self.assertEqual(effective_start_point(editor({'open_world':True}))[0]['map_id'],242)
        self.assertFalse(effective_start_point(editor({}))[2])


if __name__=='__main__':unittest.main()
