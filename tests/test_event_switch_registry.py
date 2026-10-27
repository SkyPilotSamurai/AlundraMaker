import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from event_switch_registry import EventSwitchRegistry, validate_native_flag_operand
from event_logic_compile import compile_logic


class SwitchRegistryTests(unittest.TestCase):
    def test_initialized_banks_and_high_bit_aliases(self):
        for n in (0, 0x7FF, 0x8000, 0x87FF):
            self.assertEqual(validate_native_flag_operand(n), n)
        for n in (True, -1, 0x800, 0x7FFB, 0x7FFF, 0x8800, 0xFFFF, 65536):
            with self.assertRaises(ValueError): validate_native_flag_operand(n)

    def test_binding_resolution_serialization_and_no_input_mutation(self):
        registry = EventSwitchRegistry()
        row = registry.bind(10, 'Door story condition', 0x123, evidence='map/script/source record', purpose='Intentional existing door edit')
        self.assertEqual(row['word_address'], 0x801DD358)
        self.assertEqual(registry.resolve({'switch_id': 10}), 0x123)
        raw = compile_logic([{'type': 'set_switch', 'switch_id': 10, 'value': True}], switch_resolver=registry.resolve)
        self.assertEqual(raw, b'\x05\x23\x01')
        row['name'] = 'Changed returned copy'
        self.assertEqual(registry.export()[0]['name'], 'Door story condition')
        self.assertEqual(EventSwitchRegistry(registry.export()).resolve({'switch_id': 10}), 0x123)

    def test_binding_requires_evidence_and_distinct_native_flag(self):
        registry = EventSwitchRegistry()
        with self.assertRaises(ValueError): registry.bind(1, 'x', 1, evidence='', purpose='x')
        registry.bind(1, 'x', 1, evidence='source', purpose='edit existing')
        with self.assertRaises(ValueError): registry.bind(2, 'y', 1, evidence='source', purpose='edit existing')
        with self.assertRaises(ValueError): registry.resolve({'switch_id': 2})
        with self.assertRaises(ValueError): registry.allocate('New switch')


if __name__ == '__main__':
    unittest.main()
