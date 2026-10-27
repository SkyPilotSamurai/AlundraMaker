import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_event_variables import (counter_step,compile_counter_init,compile_counter_step,
    compile_counted_repeat,distance_condition,compile_save_position,compile_distance_condition,analyse)


class NativeVariableTests(unittest.TestCase):
    def test_counter_signed_decrement_not_result_boolean(self):
        self.assertEqual(counter_step(2,-5),(1,-5))
        self.assertEqual(counter_step(1,-5),(0,3))
        self.assertEqual(counter_step(0,-5),(-1,3))
        self.assertEqual(counter_step(-0x80000000,-5),(0x7fffffff,-5))
        self.assertEqual(compile_counter_init(255),b'\x73\xff')
        self.assertEqual(compile_counter_step(-5),b'\x74\xfb\xff')

    def test_repeat_count_and_opcode_relative_branch(self):
        code=compile_counted_repeat(b'\x75\x04\x00',3,continuation_proven=True)
        self.assertEqual(code,b'\x73\x03\x75\x04\x00\x74\xfd\xff')
        pc=2;counter=code[1];iterations=0
        while pc<len(code):
            iterations+=1;pc+=3
            counter,delta=counter_step(counter,-3);pc+=delta
        self.assertEqual(iterations,3)
        for bad in (b'\xff',b'\x73\x02',b'\x74\x01\x00',b'\x75',b'\x02\x00\x00',b''):
            with self.assertRaises(ValueError):compile_counted_repeat(bad,3)
        for count in (0,256,True):
            with self.assertRaises(ValueError):compile_counted_repeat(b'\x00',count)
        for body in (b'\x00',b'\x37\x02',b'\x39'):
            with self.assertRaisesRegex(ValueError,'retained native continuation'):compile_counted_repeat(body,2)
        self.assertEqual(compile_counted_repeat(b'\x75\x04',2),b'\x73\x02\x75\x04\x74\xfe\xff')

    def test_distance_native_ge_and_signed_edges(self):
        self.assertEqual(distance_condition(0,9<<16,10),0)
        self.assertEqual(distance_condition(0,10<<16,10),1)
        self.assertEqual(distance_condition(10<<16,0,10),1)
        self.assertEqual(distance_condition(0,0,0),1)
        self.assertEqual(distance_condition(-0x80000000,0,0),0)
        self.assertEqual(distance_condition(0,0,0x8000),1)
        self.assertEqual(compile_save_position(),b'\x6a')
        self.assertEqual(compile_distance_condition('z',10),b'\x6d\x0a\x00')
        with self.assertRaises(ValueError):compile_distance_condition('x',0x8000)

    def test_unknown_build_and_invalid_scalar_types(self):
        with self.assertRaises(ValueError):analyse(b'unknown')
        for value in (True,256,-1):
            with self.assertRaises(ValueError):compile_counter_init(value)


if __name__=='__main__':unittest.main()
