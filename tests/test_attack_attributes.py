import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from attack_attributes import attribute_label,attribute_choices,parse_attribute


class AttackAttributeTests(unittest.TestCase):
    def test_known_names(self):
        self.assertEqual(attribute_label(0),'None (No Attack)')
        self.assertEqual(attribute_label(1),'Sword / Neutral')
        self.assertEqual(attribute_label(6),'Fire')
        self.assertEqual(attribute_label(11),'Wind Magic')
        self.assertEqual(attribute_label(133),'Tackle + Equipment Power')

    def test_unknown_values_are_kept(self):
        self.assertEqual(attribute_label(12),'Unknown (12)')
        self.assertEqual(attribute_label(0x21),'Unknown (33)')
        self.assertIn('Unknown (33)',attribute_choices(0x21))
        self.assertNotIn('Unknown (33)',attribute_choices(1))

    def test_round_trip_every_byte(self):
        for value in range(256):
            self.assertEqual(parse_attribute(attribute_label(value)),value)
        self.assertEqual(parse_attribute('0x86'),0x86);self.assertEqual(parse_attribute(' 7 '),7)
        with self.assertRaises(ValueError):parse_attribute('Lightning')
        with self.assertRaises(ValueError):parse_attribute('300')


if __name__=='__main__':unittest.main()
