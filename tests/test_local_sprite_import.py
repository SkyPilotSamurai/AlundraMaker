import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from local_sprite_import import import_local_sprite,sprite_assets,layout,imported_actor_record
from texture_codec import pack_ez,unpack_ez
from map_block_repack import pointers
from editor_session import EditSession
from entity_preview import EntityPreview


def fixture():
    raw=bytearray(32768);raw[0]=0x11;raw[128]=0x11
    packed=pack_ez(bytes(raw));packed+=bytes((-len(packed))%4)
    block=bytearray(2048);end=360+len(packed)
    struct.pack_into('<7I',block,0,28,32,36,40,360,end,end)
    block[32:34]=bytes((52,60))
    roots=[140,164,168,48,84,88,124,126,128,130,132,134]
    struct.pack_into('<12I',block,40,*roots)
    struct.pack_into('<I',block,40+48+7*4,172)
    struct.pack_into('<16H',block,40+88,*([0,31]+[0]*14))
    struct.pack_into('<h',block,40+134,12);block[40+136:40+138]=b'\xff\xff'
    block[40+140:40+160]=bytes((0,0,51,59,1,0xc0,7,10,10,0,0,0,0,0,0,0,0,0,0,0))
    struct.pack_into('<4I',block,40+172,204,218,224,230)
    struct.pack_into('<4hH4B',block,40+204,0,-1,-1,-1,1,0,0,0,0)
    block[40+218:40+224]=b'\x81\xff\xff\x00\x00\x01'
    block[40+230:40+246]=bytes((0,1,0,0,0,0,2,2,0,0,2,0,0,2,2,2))
    block[360:end]=packed
    data=bytearray(2048)+block*483
    struct.pack_into('<484I',data,0x28,*[2048+i*2048 for i in range(484)])
    target=2048+3*2048
    struct.pack_into('<I',data,target+40+48+7*4,0)
    return data


class LocalImportTests(unittest.TestCase):
    def test_nonzero_donor_trailer_is_not_copied(self):
        d=fixture();_,_,start,_,header=layout(d,2)
        d[start+header[6]-4:start+header[6]]=bytes.fromhex('00424423')
        source=bytes(d);new,report=import_local_sprite(d,3,2,7)
        _,_,target,_,roots=layout(new,3)
        self.assertEqual(new[target+roots[6]-4:target+roots[6]],bytes(4))
        self.assertEqual(bytes(d),source)
        donor=EntityPreview(EditSession(d,verify=False),2).frame(7)[0]
        placed=EntityPreview(EditSession(new,verify=False),3).frame(7)[0]
        self.assertEqual(donor.tobytes(),placed.tobytes())

    def test_nonzero_target_trailer_remains_guarded(self):
        d=fixture();_,_,start,_,header=layout(d,3)
        d[start+header[6]-4:start+header[6]]=bytes.fromhex('00000009')
        with self.assertRaisesRegex(ValueError,'target palette'):
            import_local_sprite(d,3,2,7)

    def test_imported_actor_retains_native_class_with_new_hooks(self):
        d=fixture();new,report=import_local_sprite(d,3,2,7)
        row=imported_actor_record(new,report,0,9,12,5,programs={'F':11})
        self.assertEqual(row[:7],bytes((0,0,51,59,1,0xc0,7)))
        self.assertEqual(row[7:10],bytes((18,24,10)))
        self.assertEqual(row[10:15],bytes(5));self.assertEqual(row[15],11)
        self.assertEqual(row[16:18],bytes(2))

    def test_import_maintains_pixels_dimensions_native_id_and_other_maps(self):
        d=fixture();new,report=import_local_sprite(d,3,2,7)
        source=EntityPreview(EditSession(d,verify=False),2).frame(7)[0]
        placed=EntityPreview(EditSession(new,verify=False),3).frame(7)[0]
        self.assertEqual(source.size,placed.size);self.assertEqual(source.tobytes(),placed.tobytes())
        old,latest=pointers(d),pointers(new)
        for m in (0,1,2,4,242,482):self.assertEqual(d[old[m]:old[m+1]],new[latest[m]:latest[m+1]])
        b,h,s,e,sh=layout(new,3)
        # Original callbacks/scripts and native list bytes are copied without changes.
        self.assertEqual(new[s+sh[0]:s+sh[1]],d[old[3]+40+140:old[3]+40+164])
        self.assertFalse(report['gameplay_verified'])

    def test_occupied_slot_rejects_without_mutation(self):
        d=fixture();before=bytes(d)
        with self.assertRaisesRegex(ValueError,'already contains'):import_local_sprite(d,2,3,7)
        self.assertEqual(bytes(d),before)

    def test_effect_pages_are_preserved_and_donor_uses_appended_page(self):
        from map_block_repack import replace_section
        d=fixture();sp=2048+3*2048+40;struct.pack_into('<i',d,sp+84,180)
        raw=bytes([0x22])*32768;packed=pack_ez(raw);packed+=bytes((-len(packed))%4)
        d=replace_section(d,3,4,packed)
        new,report=import_local_sprite(d,3,2,7)
        self.assertTrue(report['effect_pages_reserved']);self.assertEqual(report['page_mapping'],{0:1})
        b,h,s,e,sh=layout(new,3);decoded,_=unpack_ez(new[b+h[4]:b+h[5]],limit=262144)
        self.assertEqual(decoded[:32768],raw)
        self.assertEqual(struct.unpack_from('<i',new,s+sh[4])[0],180)
        self.assertEqual(EntityPreview(EditSession(d,verify=False),2).frame(7)[0].tobytes(),
                         EntityPreview(EditSession(new,verify=False),3).frame(7)[0].tobytes())

    def test_import_after_process_allocation_preserves_pixels_and_palette_bounds(self):
        from native_script_allocation import append_native_process
        d=fixture()
        # Preserve an original palette whose first DWORD is zero: scanning
        # zero sentinels would wrongly treat this actual palette as absent.
        donor=2048+2*2048+40
        struct.pack_into('<16H',d,donor+88,*([0,0,31]+[0]*13))
        allocated,_=append_native_process(d,3,'F',b'\xff')
        b,h,s,e,sh=layout(allocated,3)
        self.assertEqual(sh[6]-sh[5],36)
        new,report=import_local_sprite(allocated,3,2,7)
        source=EntityPreview(EditSession(d,verify=False),2).frame(7)[0]
        placed=EntityPreview(EditSession(new,verify=False),3).frame(7)[0]
        self.assertEqual(source.tobytes(),placed.tobytes())
        # Another process after the import preserves exact contiguous palette
        # bytes and remains usable by palette-fork editing.
        allocated2,_=append_native_process(new,3,'C',b'\xff')
        _,_,s1,_,r1=layout(new,3);_,_,s2,_,r2=layout(allocated2,3)
        self.assertEqual(new[s1+r1[5]:s1+r1[6]],allocated2[s2+r2[5]:s2+r2[6]])
        from local_sprite_recolor import recolor_local_class
        recolored,_=recolor_local_class(allocated2,3,263,120)
        self.assertEqual(sprite_assets(recolored,3,7)['pages'],sprite_assets(allocated2,3,7)['pages'])

    def test_two_sprite_imports_with_interleaved_process_keep_first_pixels(self):
        from native_script_allocation import append_native_process
        d=fixture();donor=2048+2*2048+40;target=2048+3*2048+40
        struct.pack_into('<I',d,donor+48+6*4,172)
        struct.pack_into('<I',d,target+48+6*4,0)
        one,_=import_local_sprite(d,3,2,7)
        first=EntityPreview(EditSession(one,verify=False),3).frame(7)[0].tobytes()
        allocated,_=append_native_process(one,3,'C',b'\x37\x01\xff')
        two,_=import_local_sprite(allocated,3,2,6)
        self.assertEqual(EntityPreview(EditSession(two,verify=False),3).frame(7)[0].tobytes(),first)
        self.assertEqual(EntityPreview(EditSession(two,verify=False),3).frame(6)[0].tobytes(),first)
        from event_editor import instructions,script_roots
        sess=EditSession(two,verify=False)
        roots=script_roots(sess,3);key=max((k for k in roots if k.startswith('C ')),key=lambda k:int(k.split()[1]))
        self.assertEqual([op for _,op,_ in instructions(sess,3,key)],[0x37,0xff])


if __name__=='__main__':unittest.main()
