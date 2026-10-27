import struct,sys,unittest
from types import SimpleNamespace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from starting_equipment import (patch_starting_equipment,INIT_WORDS,INIT_ADDRESS,TABLE_BYTE,
 WEAPON_INIT,SETTER_ADDRESS,SETTER_WORDS,GETTER_ADDRESS,GETTER_WORDS,GETTER_NONE_ADDRESS,GETTER_NONE_WORDS)


def fixture():
    b=bytearray(0xb0000);b[:8]=b'PS-X EXE'
    struct.pack_into('<4I',b,0x10,0x80020000,0,0x80020000,len(b)-0x800)
    struct.pack_into('<13I',b,0x800+INIT_ADDRESS-0x80020000,*INIT_WORDS)
    for address,words in ((WEAPON_INIT,(0x0C013ECA,0x24040001)),(SETTER_ADDRESS,SETTER_WORDS),
                          (GETTER_ADDRESS,GETTER_WORDS),(GETTER_NONE_ADDRESS,GETTER_NONE_WORDS)):
        struct.pack_into('<'+'I'*len(words),b,0x800+address-0x80020000,*words)
    for item,group in ((1,1),(2,1),(4,1),(5,2),(7,6),(9,3),(14,4),(16,5)):
        struct.pack_into('<h',b,0x800+0x800BBE50-0x80020000+10*item,group)
    for i in range(98):b[0x800+TABLE_BYTE-0x80020000+i*8]=(i&127)|128
    return b


class StartingEquipmentTests(unittest.TestCase):
    def test_other_options_preserve_equipment_and_open_world_enables_intro_skip(self):
     from editor_ui import Editor
     class Value:
      def __init__(self,value):self.value=value
      def get(self):return self.value
      def set(self,value):self.value=value
     editor=Editor.__new__(Editor)
     editor.database=SimpleNamespace(document={'mod_options':{'starting_equipment':[5,36]}})
     editor.mod_option_vars={k:Value(k=='open_world') for k in ('open_world','skip_intro','lr_swaps','instant_text')}
     editor.status=Value('');editor.change_mod_options()
     self.assertEqual(editor.database.document['mod_options']['starting_equipment'],[5,36])
     self.assertTrue(editor.database.document['mod_options']['skip_intro'])

    def test_selection_preserves_low_bits_other_bytes_and_unmodelled_entries(self):
        b=fixture();before=bytes(b);new,report=patch_starting_equipment(b,[2,9,2])
        changed={0x800+TABLE_BYTE-0x80020000+i*8 for i in range(1,90) if i not in (2,9)}
        self.assertEqual({i for i,(x,y) in enumerate(zip(before,new)) if x!=y},changed)
        self.assertEqual(bytes(b),before)
        self.assertEqual(report['selected_item_ids'],[2,9])
        for i in range(98):
            off=0x800+TABLE_BYTE-0x80020000+i*8
            self.assertEqual(new[off]&127,b[off]&127)
        self.assertEqual(new[0xa85ea+97*8],b[0xa85ea+97*8])

    def test_none_preserves_source_and_empty_selection_is_explicit(self):
        b=fixture();self.assertEqual(patch_starting_equipment(b,None)[0],bytes(b))
        new,report=patch_starting_equipment(b,[])
        self.assertEqual(len(report['changes']),89)
        self.assertEqual(patch_starting_equipment(new,[])[0],new)
        self.assertEqual(report['initial_equipped_weapon_slot'],-1)

    def test_initial_category_uses_metadata_not_item_id(self):
        for ids,want in (([9],3),([14],4),([16,7],5),([4,9],1),([], -1)):
            new,report=patch_starting_equipment(fixture(),ids)
            self.assertEqual(report['initial_equipped_weapon_slot'],want)
            self.assertEqual(struct.unpack_from('<I',new,0x800+WEAPON_INIT-0x80020000+4)[0],0x24040000|(want&65535))

    def test_invalid_ids_and_changed_native_initializer_rejected(self):
        b=fixture()
        for ids in ([0],[90],[-1],[True]):
            with self.assertRaises(ValueError):patch_starting_equipment(b,ids)
        b[0x12640]=0
        with self.assertRaisesRegex(ValueError,'signature'):patch_starting_equipment(b,[1])


if __name__=='__main__':unittest.main()
