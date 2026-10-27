import copy
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from native_actor_lifecycle import conditional_template, compile_destroy_owned_template, compile_switch_presence_watcher, recover_native_evidence


def run_poll(code, flag, count):
    """Synthetic scheduler/model. At00 yield, deferred destruction is resolved.

    This is bytecode branch testing, not proof of gameplay cleanup order.
    """
    pc = 1  # resume after the initial00 yield
    result = False
    spawned = destroyed = 0
    for _ in range(100):
        op = code[pc]
        if op == 0: return count, spawned, destroyed
        if op in (0x30, 0x31):
            expected = op == 0x30
            delta = struct.unpack_from('<h', code, pc + 3)[0]
            pc += delta if flag == expected else 5
        elif op == 0x2C:
            result = count == 0; pc += 2
        elif op in (2, 3, 4):
            take = op == 2 or (op == 3 and result) or (op == 4 and not result)
            pc += struct.unpack_from('<h', code, pc + 1)[0] if take else 3
        elif op == 0x2D:
            count += 1; spawned += 1; pc += 2
        elif op == 0x2E:
            destroyed += count; count = 0; pc += 2
        else: raise AssertionError(f'Unexpected opcode{op:02X}')
    raise AssertionError('Watcher did not yield')


class NativeActorLifecycleTests(unittest.TestCase):
    def test_guarded_presence_no_duplicate_spawns_and_inverse_switch(self):
        for inverted in (False, True):
            code = compile_switch_presence_watcher(0x8007, 12, when_set=not inverted)
            count = 0
            for flag in (False, False, True, True, True, False, False, True):
                wanted = flag != inverted
                old = count
                count, spawned, destroyed = run_poll(code, flag, count)
                self.assertEqual(count, int(wanted))
                self.assertEqual(spawned, int(wanted and old == 0))
                self.assertEqual(destroyed, int(not wanted and old != 0))

    def test_watcher_uses_owned_identity_not_global_sprite_or_deactivation(self):
        code = compile_switch_presence_watcher(0x7FF, 127)
        self.assertEqual(code[:6], bytes.fromhex('00 31 ff07 0f00'))
        self.assertEqual(compile_destroy_owned_template(127), b'\x2e\x7f')
        self.assertEqual(code[-3], 2)
        self.assertEqual(len(code) - 3 + struct.unpack_from('<h', code, len(code) - 2)[0], 0)
        self.assertEqual(run_poll(code, False, 3), (0, 0, 3))

    def test_template_auto_spawn_suppression_preserves_all_other_bytes(self):
        donor = bytes.fromhex('0000333b01c70210203081828384858612002300')
        old = copy.copy(donor)
        raw = conditional_template(donor)
        self.assertEqual(raw[5], 0x87)
        self.assertEqual(raw[:5] + raw[6:], donor[:5] + donor[6:])
        self.assertEqual(donor, old)
        for invalid in (b'', bytes(20), donor[:19]):
            with self.assertRaises(ValueError): conditional_template(invalid)

    def test_invalid_operands_and_unverified_module_rejected(self):
        for operand in (-1, True, 0x800, 0x7FFB, 0x8800, 65536):
            with self.assertRaises(ValueError): compile_switch_presence_watcher(operand, 2)
        for index in (-1, True, 128, 256):
            with self.assertRaises(ValueError): compile_switch_presence_watcher(1, index)
        with self.assertRaises(ValueError): compile_switch_presence_watcher(1, 2, when_set=1)
        with self.assertRaises(ValueError): recover_native_evidence(bytes(2048))


if __name__ == '__main__': unittest.main()
