import struct, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from native_object_controller import rebind_controller, LENGTHS
from project_state_registry import ProjectStateRegistry

LEVER_C=bytes.fromhex('3002800a002a0002f9ff2b30018011001a031c011a0006028002e7ff1a021c011a0106028002dbffff')
LEVER_D=bytes.fromhex('2b320180050280ff')

def run(code, state, pc=0):
    """Bounded interpreter checks resized control flow, not PS1 execution."""
    condition=False; animations=[]
    for _ in range(100):
        op=code[pc]; start=pc
        if op==0: return pc+1, animations
        if op==255: return None, animations
        if op in (0xE0,0xE1):
            slot,value=struct.unpack_from('<HB',code,pc+1)
            if op==0xE0: state[slot]=bool(value)
            else: condition=state[slot]==bool(value)
            pc+=4
        elif op in (2,3,4):
            pc=start+struct.unpack_from('<h',code,pc+1)[0] if op==2 or (condition if op==3 else not condition) else pc+3
        elif op==0x98:
            state['money']=state.get('money',0)+struct.unpack_from('<H',code,pc+1)[0];pc+=3
        else:
            if op==0x1A: animations.append(code[pc+1])
            pc+=LENGTHS[op]
    raise AssertionError('Controller did not yield or end')

class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.registry=ProjectStateRegistry({})
        self.bind={0x8001:self.registry.create('switches','Lever state')['id'],
                   0x8002:self.registry.create('switches','Lever request')['id']}
    def test_two_activations_keep_native_animation_order_and_clear_request(self):
        c,report=rebind_controller(LEVER_C,self.bind,self.registry)
        d,_=rebind_controller(LEVER_D,self.bind,self.registry)
        state={0:False,1:False}; pc,_=run(c,state)
        run(d,state); self.assertEqual(state,{0:True,1:True})
        pc,animations=run(c,state,pc); self.assertEqual(animations,[2,1])
        self.assertFalse(state[1])
        run(d,state); self.assertEqual(state,{0:False,1:True})
        _,animations=run(c,state,pc); self.assertEqual(animations,[3,0])
        self.assertEqual(state,{0:False,1:False})
        self.assertEqual(report['native_flags_replaced'],[0x8001,0x8002])
    def test_instances_do_not_share_state(self):
        other={flag:self.registry.create('switches','Other '+str(flag))['id'] for flag in self.bind}
        d,_=rebind_controller(LEVER_D,self.bind,self.registry)
        d2,_=rebind_controller(LEVER_D,other,self.registry)
        state=dict.fromkeys(range(4),False);run(d,state)
        self.assertEqual(state,{0:True,1:True,2:False,3:False})
        run(d2,state);self.assertTrue(all(state.values()))
    def test_unbound_and_room_owned_commands_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unbound'): rebind_controller(LEVER_D,{},self.registry)
        with self.assertRaisesRegex(ValueError,'Unrecovered'): rebind_controller(bytes.fromhex('85000000000000ff'),self.bind,self.registry)
    def test_bad_branch_and_truncation_rejected(self):
        for code in (bytes.fromhex('020100ff'),bytes.fromhex('300280'),bytes.fromhex('1a00')):
            with self.assertRaises(ValueError):rebind_controller(code,self.bind,self.registry)
    def test_authored_activation_runs_once_per_request_not_each_tick(self):
        c,_=rebind_controller(LEVER_C,self.bind,self.registry,insert_before={10:bytes.fromhex('980100')})
        d,_=rebind_controller(LEVER_D,self.bind,self.registry)
        state={0:False,1:False};pc,_=run(c,state)
        for count in (1,2):
            run(d,state);pc,_=run(c,state,pc)
            for _ in range(30):pc,_=run(c,state,pc)
            self.assertEqual(state['money'],count)
    def test_profile_runs_authored_commands_on_both_completed_animation_paths(self):
        from native_lever_profile import compile_lever
        programs,report=compile_lever(self.registry,self.bind[0x8001],self.bind[0x8002],
            [{'type':'change_money','amount':7}])
        state={0:False,1:False};pc,_=run(programs['C'],state)
        for expected,animations in [(7,[2,1]),(14,[3,0])]:
            run(programs['D'],state);pc,observed=run(programs['C'],state,pc)
            self.assertEqual(observed,animations);self.assertEqual(state['money'],expected)
        self.assertFalse(report['gameplay_verified'])
        with self.assertRaises(ValueError):compile_lever(self.registry,self.bind[0x8001],self.bind[0x8001])
