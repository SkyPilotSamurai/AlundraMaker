import copy,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from project_state_registry import ProjectStateRegistry
from project_state_runtime import (layout,compile_project_command,compile_project_condition,
    emit_handler,inject_private_state,verify_private_state_injection,OPCODES)
from event_logic_compile import compile_logic


def signed(n):return n-0x100000000 if n&0x80000000 else n


def execute_handler(code,command,state,context=0x80102000,owner=0):
    """Independent subset interpreter for emitted leaf handlers and native ABI."""
    words=struct.unpack('<'+'I'*(len(code)//4),code);regs=[0]*32
    regs[6]=0x80101000;regs[7]=context
    regs[5]=owner
    memory={}
    def store(addr,blob):
        for i,value in enumerate(blob):memory[addr+i]=value
    def read(addr,count):return int.from_bytes(bytes(memory.get(addr+i,0) for i in range(count)),'little')
    store(regs[6],struct.pack('<I',0x80101100));store(0x80101100,command)
    for address,value in state.items():store(address,struct.pack('<I',value&0xFFFFFFFF))
    pc=0
    for _ in range(300):
        word=words[pc];op=word>>26;rs=(word>>21)&31;rt=(word>>16)&31;rd=(word>>11)&31
        immediate=word&65535;simm=immediate-65536 if immediate&32768 else immediate
        next_pc=pc+1
        if op==0:
            fn=word&63;shift=(word>>6)&31
            if fn==0:regs[rd]=regs[rt]<<shift
            elif fn==8:
                assert words[pc+1]==0
                return regs[2],read(context+0x2C,4),{a:read(a,4) for a in state}
            elif fn==0x21:regs[rd]=regs[rs]+regs[rt]
            elif fn==0x25:regs[rd]=regs[rs]|regs[rt]
            elif fn==0x26:regs[rd]=regs[rs]^regs[rt]
            elif fn==0x2A:regs[rd]=int(signed(regs[rs])<signed(regs[rt]))
            elif fn==0x2B:regs[rd]=int(regs[rs]<regs[rt])
            else:raise AssertionError(hex(word))
        elif op==9:regs[rt]=regs[rs]+simm
        elif op==11:regs[rt]=int(regs[rs]<(simm&0xFFFFFFFF))
        elif op==12:regs[rt]=regs[rs]&immediate
        elif op==14:regs[rt]=regs[rs]^immediate
        elif op==15:regs[rt]=immediate<<16
        elif op in (4,5):
            equal=regs[rs]==regs[rt]
            if equal if op==4 else not equal:
                assert words[pc+1]==0
                next_pc=pc+1+simm
        elif op in (35,36):
            self_address=(regs[rs]+simm)&0xFFFFFFFF
            regs[rt]=read(self_address,4 if op==35 else 1)
            assert words[pc+1]==0,'MIPS load delay not protected'
        elif op==43:store((regs[rs]+simm)&0xFFFFFFFF,struct.pack('<I',regs[rt]))
        else:raise AssertionError(hex(word))
        regs=[v&0xFFFFFFFF for v in regs];regs[0]=0;pc=next_pc
    raise AssertionError('Handler failed to return')


class RegistryTests(unittest.TestCase):
    def test_named_state_ids_never_reused_and_mod_document_roundtrip(self):
        doc={'event_graphs':[]};registry=ProjectStateRegistry(doc)
        first=registry.create('switches',' Gate open ',False)
        registry.update('switches',first['id'],name='Gate activated',initial_value=True)
        registry.delete('switches',first['id'])
        second=registry.create('switches','New gate')
        self.assertEqual((first['id'],second['id']),(1,2))
        var=registry.create('variables','Puzzle count',-5)
        self.assertEqual(ProjectStateRegistry(copy.deepcopy(doc)).get('variables',var['id'])['initial_value'],-5)
        doc['event_graphs']=[{'pages':[{'conditions':[{'type':'switch','switch_scope':'project','switch_id':2,'value':True}]}]}]
        with self.assertRaisesRegex(ValueError,'referenced'):registry.delete('switches',2)
        registry.validate_references();doc['event_graphs'][0]['pages'][0]['conditions'][0]['switch_id']=1
        with self.assertRaisesRegex(ValueError,'missing or deleted'):registry.validate_references()

    def test_bounds_and_copy_options(self):
        registry=ProjectStateRegistry({})
        for value in (True,2147483648,-2147483649):
            with self.assertRaises(ValueError):registry.create('variables','bad',value)
        for value in (0,1,None):
            if value is None:continue
            with self.assertRaises(ValueError):registry.create('switches','bad',value)
        for i in range(128):registry.create('switches',str(i))
        with self.assertRaises(ValueError):registry.create('switches','overflow')
        options=registry.options('switches');options[0]['name']='Changed'
        self.assertEqual(registry.get('switches',1)['name'],'0')


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.doc={};self.registry=ProjectStateRegistry(self.doc)
        self.switch=self.registry.create('switches','Door',False)
        self.variable=self.registry.create('variables','Count',-5)
        self.state_address=0x8001F400

    def test_switch_native_abi_set_and_conditions(self):
        command={'type':'set_switch','switch_scope':'project','switch_id':1,'value':True}
        raw=compile_project_command(command,self.registry)
        result,condition,state=execute_handler(emit_handler(0xE0,self.state_address,1,1),raw,{self.state_address:0})
        self.assertEqual(result,4);self.assertEqual(state[self.state_address],1)
        for expected in (True,False):
            raw=compile_project_condition({'type':'switch','switch_scope':'project','switch_id':1,'value':expected},self.registry)
            result,condition,state=execute_handler(emit_handler(0xE1,self.state_address,1,1),raw,state)
            self.assertEqual(condition,int(expected));self.assertEqual(result,4)

    def test_variable_set_wrap_arithmetic_and_signed_comparisons(self):
        address=self.state_address+512;state={address:0}
        for operation,value in (('set',2147483647),('add',1),('subtract',-5)):
            raw=compile_project_command({'type':'set_variable','variable_scope':'project','variable_id':1,'value':value,'operation':operation},self.registry)
            _,_,state=execute_handler(emit_handler(raw[0],self.state_address,1,1),raw,state)
        self.assertEqual(signed(state[address]),-2147483643)
        operations={'==':lambda a,b:a==b,'!=':lambda a,b:a!=b,'<':lambda a,b:a<b,'<=':lambda a,b:a<=b,'>':lambda a,b:a>b,'>=':lambda a,b:a>=b}
        for actual,expected in ((-2147483648,2147483647),(-1,0),(0,0),(2147483647,-2147483648)):
            for operator,compare in operations.items():
                raw=compile_project_condition({'type':'variable','variable_scope':'project','variable_id':1,'operator':operator,'value':expected},self.registry)
                result,condition,_=execute_handler(emit_handler(0xE4,self.state_address,1,1),raw,{address:actual})
                self.assertEqual(result,8);self.assertEqual(condition,int(compare(actual,expected)))

    def test_bounds_invalid_slot_does_not_overwrite_state(self):
        for opcode in OPCODES:
            raw=bytes([opcode,128,0])+bytes(OPCODES[opcode]-3)
            result,condition,state=execute_handler(emit_handler(opcode,self.state_address,1,1),raw,{self.state_address:123,self.state_address+512:456})
            self.assertEqual(state,{self.state_address:123,self.state_address+512:456})
            self.assertEqual(result,OPCODES[opcode]);self.assertEqual(condition,0)
        for args in ((0xE0,0x80100000,1,1),(0xE0,self.state_address,129,1),
                     (0xE0,self.state_address,True,1)):
            with self.assertRaises(ValueError):emit_handler(*args)

    def test_if_branch_uses_private_condition_without_stock_flag_operands(self):
        row={'type':'if','condition':{'type':'switch','switch_scope':'project','switch_id':1,'value':True},
             'then':[{'type':'set_variable','variable_scope':'project','variable_id':1,'value':3}],'else':[]}
        raw=compile_logic([row],lambda row:compile_project_command(row,self.registry),
            project_condition_emitter=lambda row:compile_project_condition(row,self.registry))
        self.assertEqual(raw[:4],bytes.fromhex('e1000001'));self.assertEqual(raw[4],4)
        with self.assertRaisesRegex(ValueError,'private-state runtime'):compile_logic([row])

    def test_stock_guarded_prepend_initialized_array_and_manifest(self):
        path=ROOT/'game/disc/ALUN_CD.EXE'
        if not path.exists():self.skipTest('Private stock executable unavailable')
        source=path.read_bytes();old=copy.deepcopy(self.doc)
        exe,manifest=inject_private_state(source,self.doc)
        self.assertEqual(self.doc,old)
        self.assertEqual(manifest['expansion']%2048,0);self.assertGreaterEqual(manifest['new_load'],0x80010000)
        offset=manifest['state_address']-manifest['new_load']+0x800
        self.assertEqual(struct.unpack_from('<ii',exe,offset)[0],0)
        self.assertEqual(struct.unpack_from('<i',exe,offset+512)[0],-5)
        self.assertTrue(verify_private_state_injection(exe,manifest)['memory_card_persistent'])   # companion card file (2026-10-22)
        with self.assertRaisesRegex(ValueError,'modified executables'):inject_private_state(exe,self.doc)
        changed=bytearray(exe);changed[offset]^=1
        with self.assertRaisesRegex(ValueError,'exact export manifest'):verify_private_state_injection(changed,manifest)


if __name__=='__main__':unittest.main()
