import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import native_murgg_bundle as bundle


class MurggBundleTests(unittest.TestCase):
    def sources(self,catalogue):
        p=bundle.PROFILES[catalogue]
        records=[bytes(20)]*(p['entity_index']+1)
        records[-1]=bytes.fromhex(p['record_hex'])
        profiles={catalogue:p['callbacks'],**p['projectiles']}
        return records,profiles

    def test_fixed_slots_and_native_parent_profiles(self):
        for c,slots in ((347,[]),(350,[95]),(356,[101])):
            records,profiles=self.sources(c);calls=[]
            def imported(data,target,donor,slot):
                calls.append((donor,slot));return data+b'x',{'slot':slot}
            with patch.object(bundle,'record_cluster',return_value={'entities':records}),patch.object(bundle,'sprite_callbacks',side_effect=lambda d,m,i:profiles[i]),patch.object(bundle,'import_local_sprite',side_effect=imported):
                out,report=bundle.import_bundle(b'source',163,c)
            self.assertEqual([s for m,s in calls],[c-256,*slots])
            self.assertEqual(report['fixed_projectile_slots'],slots)
            self.assertFalse(report['gameplay_verified'])
            self.assertEqual(out,b'source'+b'x'*len(calls))

    def test_projectile_callback_drift_rejected_before_import(self):
        records,profiles=self.sources(350);profiles[351]=[('C',25)]
        with patch.object(bundle,'record_cluster',return_value={'entities':records}),patch.object(bundle,'sprite_callbacks',side_effect=lambda d,m,i:profiles[i]),patch.object(bundle,'import_local_sprite') as importer:
            with self.assertRaisesRegex(ValueError,'callback profile differs'):bundle.import_bundle(b'source',163,350)
        importer.assert_not_called()

    def test_hook_or_source_record_drift_rejected(self):
        records,profiles=self.sources(347);changed=bytearray(records[-1]);changed[10]=1;records[-1]=bytes(changed)
        with patch.object(bundle,'record_cluster',return_value={'entities':records}):
            with self.assertRaisesRegex(ValueError,'source record differs'):bundle.verified_donor(b'',347)

    def test_failed_dependency_leaves_original_untouched(self):
        records,profiles=self.sources(356);original=bytearray(b'source')
        with patch.object(bundle,'record_cluster',return_value={'entities':records}),patch.object(bundle,'sprite_callbacks',side_effect=lambda d,m,i:profiles[i]),patch.object(bundle,'import_local_sprite',side_effect=[(b'parent',{}),ValueError('native page capacity')]):
            with self.assertRaisesRegex(ValueError,'page capacity'):bundle.import_bundle(original,163,356)
        self.assertEqual(original,b'source')

    def test_other_enemies_remain_guarded(self):
        with self.assertRaisesRegex(ValueError,'No recovered'):bundle.verified_donor(b'',353)

    def test_claws_special_source_map_parent_dependency_remains_guarded(self):
        with self.assertRaisesRegex(ValueError,'parent/controller'):bundle.import_bundle(b'',153,347)


if __name__=='__main__':unittest.main()
