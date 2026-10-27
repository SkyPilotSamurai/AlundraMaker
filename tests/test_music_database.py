import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from music_database import encode_music,patch_map_music,map_music,map_music_values,map_table_offset
from event_logic_compile import compile_logic
from event_graph import new_event_graph,validate_event_graph
from native_event_commands import encode_insert

def fixture():
    exe=bytearray(8192);exe[:8]=b'PS-X EXE';struct.pack_into('<2I',exe,0x18,0x80020000,len(exe)-2048)
    struct.pack_into('<6I',exe,0x900,0x00041080,0x3C018002,0x00220821,0x8C220800,0x03E00008,0)
    struct.pack_into('<483i',exe,0x1000,*([7]*483));return bytes(exe)

class MusicTests(unittest.TestCase):
    def test_native_music_command_and_order(self):
        commands=[dict(type='change_music',music_id=30),dict(type='wait',frames=2),dict(type='play_sound',sound_id=7)]
        graph=new_event_graph('event:music',12);graph['pages'][0]['commands']=commands
        validate_event_graph(graph)
        self.assertEqual(compile_logic(commands),bytes.fromhex('a71e003702bd0700'))
        self.assertEqual(encode_insert(commands[0]),bytes.fromhex('a71e00'))
        for invalid in (-1,47,True,'30'):
            with self.assertRaises(ValueError):encode_music(invalid)
    def test_map_music_is_exported_without_changing_other_bytes(self):
        original=fixture();patched,report=patch_map_music(original,{'0':30,'482':46})
        self.assertEqual(map_music(patched,0),30);self.assertEqual(map_music(patched,482),46)
        self.assertEqual(map_music(patched,1),7);self.assertEqual(len(map_music_values(patched)),483)
        restored=bytearray(patched)
        for row in report:struct.pack_into('<i',restored,row['file_offset'],row['before'])
        self.assertEqual(bytes(restored),original)
        again,_=patch_map_music(patched,{'0':12});self.assertEqual(map_music(again,0),12)
    def test_unknown_lookup_and_bad_map_fail(self):
        original=fixture()
        with self.assertRaises(ValueError):map_table_offset(original.replace(bytes.fromhex('80100400'),b'\x00'*4))
        for selections in ({'483':1},{'x':1},{'12':47}):
            with self.assertRaises(ValueError):patch_map_music(original,selections)

if __name__=='__main__':unittest.main()
