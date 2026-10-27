import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_class_placement import (record_cluster,donor_record,trigger_record,
    duplicate_entity,add_map_trigger,append_record_cluster,class_donors,
    donor_record_for_map,global_sprite_available,resolve_class_donor)
from map_block_repack import pointers,sections


def fixture():
    block=bytearray(2048)
    struct.pack_into('<7I',block,0,28,32,36,40,320,324,328)
    block[32:34]=bytes((52,60))
    sh=[128,152,156,48,52,56,88,90,92,94,96,98]
    struct.pack_into('<12I',block,40,*sh)
    struct.pack_into('<I',block,88,160) # sprite-table target relative to sprite-info
    struct.pack_into('<4I',block,200,192,200,212,220)
    row=bytes([0,0,40,30,1,0xc2,7,10,12,4,1,2,3,4,5,6,0x12,0x34,0x22,0])
    block[168:188]=row
    block[192:196]=b'EFCT'
    block[320:324]=b'SPRT';block[324:328]=b'TEXT'
    data=bytearray(2048)+block*483
    struct.pack_into('<2I',data,0,0x828,0x940)
    struct.pack_into('<484I',data,0x28,*[2048+i*2048 for i in range(484)])
    return data


class PlacementTests(unittest.TestCase):
    def test_resolution_prefers_target_and_rejects_absent_local_asset(self):
        d=fixture();found=resolve_class_donor(d,2,263)
        self.assertEqual((found['donor_map_id'],found['donor_entity_index']),(2,0))
        self.assertIsNone(resolve_class_donor(d,2,264))

    def test_global_cross_map_donor_clears_foreign_logic(self):
        d=fixture()
        # Fixture global sprite info is map0's same structurally valid bank.
        sp=2088;struct.pack_into('<I',d,sp+48+7*4,160)
        struct.pack_into('<I',d,sp+16,80) # table end covers eight entries
        donor=record_cluster(d,2);offset=donor['sprite_start']+donor['header'][0]
        d[offset+5]=0x42 # dedicated global bank
        self.assertTrue(global_sprite_available(d,7))
        row=donor_record_for_map(d,3,2,0,4,5,programs={'F':9})
        self.assertEqual(row[:4],bytes((0,0,51,59)))
        self.assertEqual(row[4:7],bytes((1,0x42,7)))
        self.assertEqual(row[10:15],bytes(5));self.assertEqual(row[15],9)
        self.assertEqual(row[16:18],bytes(2))
        self.assertEqual(row[18:],donor['entities'][0][18:])

    def test_foreign_local_actor_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'asset import'):
            donor_record_for_map(fixture(),3,2,0,4,5)
    def test_class_identity_uses_high_bank(self):
        d=fixture()
        self.assertEqual(class_donors(d,2,7),[])
        self.assertEqual(class_donors(d,2,263)[0]['entity_index'],0)

    def test_donor_keeps_unknowns_callbacks_bank_and_flags(self):
        d=fixture();source=record_cluster(d,2)['entities'][0]
        row=donor_record(d,2,0,24,16,9,contents=0x1234,programs={'F':8})
        self.assertEqual(row[:7],source[:7]);self.assertEqual(row[7:10],bytes([48,32,18]))
        self.assertEqual(row[10:15],source[10:15]);self.assertEqual(row[15],8)
        self.assertEqual(row[16:18],source[16:18]);self.assertEqual(row[18:],b'4\x12')

    def test_duplicate_preserves_existing_and_opaque_assets(self):
        d=fixture();old=record_cluster(d,2)
        new,report=duplicate_entity(d,2,0,24,16)
        fresh=record_cluster(new,2)
        self.assertEqual(fresh['entities'][0],old['entities'][0])
        self.assertEqual(fresh['effects'],old['effects'])
        self.assertEqual(fresh['header'][3:],old['header'][3:])
        self.assertEqual(new[fresh['sprite_start']+12:old['sprite_end']],d[old['sprite_start']+12:old['sprite_end']])
        self.assertEqual(report['entity_index'],1)
        pp,qq=pointers(d),pointers(new)
        for m in (0,1,3,242,482):
            self.assertEqual(d[pp[m]:pp[m+1]],new[qq[m]:qq[m+1]])
        b=qq[2];h=sections(new[b:qq[3]])
        self.assertEqual(new[b+h[4]:b+h[5]],b'SPRT')
        self.assertEqual(new[b+h[5]:b+h[6]],b'TEXT')

    def test_trigger_append_preserves_entities(self):
        d=fixture();new,report=add_map_trigger(d,2,(8,9,8,9),3)
        c=record_cluster(new,2)
        self.assertEqual(c['events'],[bytes([8,9,8,9,3,0,0,0])])
        self.assertEqual(c['entities'],record_cluster(d,2)['entities'])
        self.assertFalse(report['gameplay_verified'])

    def test_multiple_appends(self):
        d=fixture();d,_=duplicate_entity(d,2,0,24,16)
        d,_=duplicate_entity(d,2,1,26,18)
        d,_=add_map_trigger(d,2,(8,9,10,11),3)
        c=record_cluster(d,2)
        self.assertEqual(len(c['entities']),3);self.assertEqual(len(c['events']),1)

    def test_capacity_terminators_and_range_rejected(self):
        d=fixture();row=record_cluster(d,2)['entities'][0]
        for erows,mrows in (([row]*128,None),(None,[trigger_record((1,1,1,1),1)]*64),([bytes(20)],None)):
            with self.assertRaises(ValueError):append_record_cluster(d,2,entities=erows,map_events=mrows)
        for args in (((0,0,0,0),1),((4,1,3,2),1),((1,1,1,1),0)):
            with self.assertRaises(ValueError):trigger_record(*args)
        for coord in (128,-1,1.5,True):
            with self.assertRaises(ValueError):donor_record(d,2,0,coord,5)


if __name__=='__main__':unittest.main()
