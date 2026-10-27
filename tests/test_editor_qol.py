import json,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_qol import apply_qol
from native_lr_swaps import emit_wrapper,ITEM_GROUPS,offset,HOOK,MENU_MASK


class Machine:
    """Independent MIPS-I execution subset, including actual branch delay slots."""
    def __init__(self,code,address=0x8001E000):
        self.r=[0]*32;self.r[29]=0x801FF000;self.r[31]=0xFFFFFFFC
        self.memory={};self.put(address,code);self.pc=address;self.calls={};self.counts={};self.steps=0
    def put(self,a,data):self.memory.update({a+i:v for i,v in enumerate(data)})
    def write(self,a,value,n=4):self.put(a,(value&((1<<(n*8))-1)).to_bytes(n,'little'))
    def read(self,a,n=4):return int.from_bytes(bytes(self.memory.get(a+i,0) for i in range(n)),'little')
    def run(self):
        pending=None
        for _ in range(150000):
            if self.pc==0xFFFFFFFC:return
            self.steps+=1;w=self.read(self.pc);op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31
            im=w&65535;si=im-65536 if im&32768 else im;nextpc=self.pc+4;newpending=None
            signed=lambda n:n-0x100000000 if n&0x80000000 else n
            if op==0:
                fn=w&63
                if fn==0:self.r[rd]=self.r[rt]<<(w>>6&31)
                elif fn==8:newpending=self.r[rs]
                elif fn==0x21:self.r[rd]=self.r[rs]+self.r[rt]
                else:raise AssertionError(hex(w))
            elif op==9:self.r[rt]=self.r[rs]+si
            elif op==10:self.r[rt]=int(signed(self.r[rs])<si)
            elif op==11:self.r[rt]=int(self.r[rs]<(si&0xFFFFFFFF))
            elif op==12:self.r[rt]=self.r[rs]&im
            elif op==13:self.r[rt]=self.r[rs]|im
            elif op==15:self.r[rt]=im<<16
            elif op in (4,5):
                match=self.r[rs]==self.r[rt]
                if match if op==4 else not match:newpending=self.pc+4+si*4
            elif op in (2,3):
                newpending=(self.pc+4)&0xF0000000|(w&0x3FFFFFF)*4
                if op==3:self.r[31]=self.pc+8
            elif op in (32,35,36,37):
                n={32:1,35:4,36:1,37:2}[op];value=self.read((self.r[rs]+si)&0xFFFFFFFF,n)
                if op==32 and value&128:value-=256
                self.r[rt]=value
            elif op in (40,41,43):self.write((self.r[rs]+si)&0xFFFFFFFF,self.r[rt],{40:1,41:2,43:4}[op])
            else:raise AssertionError(hex(w))
            self.r=[v&0xFFFFFFFF for v in self.r];self.r[0]=0
            if pending is not None:
                nextpc=pending
                if nextpc in self.calls:
                    self.counts[nextpc]=self.counts.get(nextpc,0)+1;self.calls[nextpc](self);nextpc=self.r[31]
            pending=newpending;self.pc=nextpc
        raise AssertionError('Machine did not return')


def swap_machine(buttons,weapon=1,item=36,owned=None):
    m=Machine(emit_wrapper(0x8001E000));owned=owned or {}
    m.write(0x80119AE8,0x801DD81C);m.write(0x801DD826,weapon,2);m.write(0x801DD828,item,2)
    m.write(0x801DDA4A,buttons,2);m.write(0x800BBE50+item*10,12,2)
    m.calls[0x8002E3B4]=lambda vm:None
    m.calls[0x8004F810]=lambda vm:vm.r.__setitem__(2,owned.get(vm.r[4],0xFFFFFFFF))
    m.calls[0x8004FB28]=lambda vm:vm.write(0x801DD826,vm.r[4],2)
    m.calls[0x8004FB84]=lambda vm:vm.write(0x801DD828,vm.r[4],2)
    return m


class QoLTests(unittest.TestCase):
    def test_native_argument_home_spills_and_original_return_survive_swaps(self):
        for button in (0,8,2):
            m=swap_machine(button,owned={3:9,15:38})
            original_stack=m.r[29];original_saved=list(range(116,123))
            m.r[16:23]=original_saved
            def original(vm):
                for index in range(4):vm.write(vm.r[29]+index*4,0xBAD00000+index)
                vm.r[2]=0x12345678
            m.calls[0x8002E3B4]=original
            m.run()
            self.assertEqual(m.r[16:23],original_saved)
            self.assertEqual(m.r[29],original_stack)
            self.assertEqual(m.r[2],0x12345678)
    def test_weapon_wrap_owned_and_native_setter(self):
        for button,start,owned,want in ((8,1,{3:9},3),(4,1,{6:7},6),(8,6,{1:4},1),(12,2,{3:9},2),(8,1,{},1),
                                       (8,65535,{1:4,6:7},1),(4,65535,{1:4,6:7},6)):
            m=swap_machine(button,start,owned=owned);original=list(m.r)
            for i in range(16,23):m.r[i]=i+100
            m.run();self.assertEqual(m.read(0x801DD826,2),want)
            self.assertEqual(m.counts[0x8002E3B4],1);self.assertEqual(m.r[16:23],list(range(116,123)))
            self.assertEqual(m.r[29],original[29]);self.assertEqual(m.r[31],original[31])
    def test_item_wrap_empty_groups_and_simultaneous_cancel(self):
        for button,owned,want in ((2,{15:38},38),(1,{31:54},54),(3,{13:37},36),(2,{},36),(10,{2:5,13:37},37)):
            m=swap_machine(button,owned=owned);m.run();self.assertEqual(m.read(0x801DD828,2),want)
    def test_menu_warp_dialogue_and_select_guards(self):
        for address in (0x801F0060,0x801AC718,0x801F121C,0x801EFBF8,0x801DDA48):
            m=swap_machine(10,owned={2:5,13:37});m.write(address,0x100 if address==0x801DDA48 else 1)
            m.run();self.assertEqual(m.read(0x801DD826,2),1);self.assertEqual(m.read(0x801DD828,2),36)
    def test_static_export_composition_and_conflict(self):
        path=ROOT/'game/disc/ALUN_CD.EXE'
        if not path.exists():self.skipTest('Private original unavailable')
        from types import SimpleNamespace
        source=path.read_bytes();s=SimpleNamespace(content_database={'mod_options':{'lr_swaps':True,'instant_text':True}})
        exe,report=apply_qol(s,source);self.assertNotEqual(exe,source)
        self.assertEqual(struct.unpack_from('<I',exe,offset(exe,MENU_MASK))[0],0x30420800)
        self.assertEqual(exe[offset(exe,HOOK)+4:offset(exe,HOOK)+8],bytes(4))
        self.assertFalse(report['emulator_verified']);changed=bytearray(source);changed[offset(changed,0x8004FB28)]^=1
        with self.assertRaisesRegex(ValueError,'conflict'):apply_qol(s,changed)
        source_mut=bytearray(source);source_mut[offset(source_mut,0x80090000)]^=1
        patched,_=apply_qol(s,source_mut)
        self.assertEqual(patched[offset(patched,0x80090000)],source_mut[offset(source_mut,0x80090000)])
    def test_default_options_exact_bytes(self):
        from types import SimpleNamespace
        source=b'unchanged';self.assertEqual(apply_qol(SimpleNamespace(),source)[0],source)
    def test_starting_equipment_composes_with_new_module_header(self):
        path=ROOT/'game/disc/ALUN_CD.EXE'
        if not path.exists():self.skipTest('Private original unavailable')
        from types import SimpleNamespace
        s=SimpleNamespace(content_database={'mod_options':{'lr_swaps':True,'starting_equipment':[4,17,21,35]}})
        exe,report=apply_qol(s,path.read_bytes())
        for item in (1,4,17,21,35,36):
            flag=exe[offset(exe,0x800C7DEA+item*8)]
            self.assertEqual(bool(flag&128),item in (4,17,21,35))
        self.assertEqual(report['options']['starting_equipment'],[4,17,21,35])
    def test_world_state_calls_native_reset_first_and_preserves_other_bits(self):
        from editor_open_world import open_world_starting_state
        from native_open_world_state import emit_wrapper,RESET
        flags,variants=open_world_starting_state();m=Machine(emit_wrapper(flags,variants))
        def reset(vm):
            for row in flags:vm.write(int(row['byte_address'],16),0xA5,1)
        m.calls[RESET]=reset;before=list(m.r);m.run()
        self.assertEqual(m.counts[RESET],1)
        masks={}
        for row in flags:
            address=int(row['byte_address'],16);masks[address]=masks.get(address,0)|row['byte_mask']
        for address,mask in masks.items():self.assertEqual(m.read(address,1),0xA5|mask)
        for row in variants:self.assertEqual(m.read(int(row['address'],16),2),row['value'])
        self.assertEqual(m.r[29],before[29]);self.assertEqual(m.r[31],before[31])
    def test_world_access_full_snapshot_composition(self):
        path=ROOT/'game/disc/ALUN_CD.EXE';data=ROOT/'game/disc/DATA/DATAS.BIN'
        if not path.exists() or not data.exists():self.skipTest('Private original unavailable')
        from editor_session import EditSession
        from native_open_world_state import HOOK as WORLD_HOOK
        s=EditSession(data.read_bytes());s.content_database={'mod_options':{'open_world':True,'skip_intro':True,'lr_swaps':True}}
        exe,report=apply_qol(s,path.read_bytes())
        self.assertNotEqual(struct.unpack_from('<I',exe,offset(exe,WORLD_HOOK))[0],0x0C020F68)
        world=next(row for row in report['patches'] if row.get('format')=='alundra-editor-open-world-access-v1')
        self.assertFalse(world['dream_dungeon_mode']);self.assertGreater(len(world['changes']),100)
        intro=next(row for row in report['patches'] if row.get('format')=='alundra-normal-story-intro-skip-v1')
        self.assertEqual(intro['spawn'],dict(map_id=242,x=38,y=12,z=2,house_variant=260))
        self.assertIn('PatchNewGame',intro['spawn_source'])
        from alundra_memory import parse_exe
        header=parse_exe(exe)
        def word(address):return struct.unpack_from('<I',exe,0x800+address-header['load_address'])[0]
        self.assertEqual(word(0x80031D58)&0xFFFF,242)
        self.assertEqual(word(0x80031D64)&0xFFFF,38)
        self.assertEqual(word(0x80031D70)&0xFFFF,12)
        # World recipes do not rewrite the normal first-wake completion tail or
        # the native outdoor Inoa process that follows the safe initial entry.
        from editor_open_world import RECIPE
        recipe=json.loads(RECIPE.read_text());self.assertFalse(any(row['map_id'] in (162,163) for row in recipe['patches']))
        from intro_skip import intro_process_plan
        intro_process_plan(s) # Exact persistent flag guard and completion tail.

    def test_open_world_composes_with_project_switch_executable(self):
        exe_path=ROOT/'game/disc/ALUN_CD.EXE';datas_path=ROOT/'game/disc/DATA/DATAS.BIN'
        if not exe_path.exists() or not datas_path.exists():self.skipTest('Private original unavailable')
        from project_state_registry import ProjectStateRegistry
        from project_state_runtime import inject_private_state
        from editor_session import EditSession
        from editor_open_world import open_world_starting_state
        from native_open_world_state import validate
        stock_exe=exe_path.read_bytes();datas=datas_path.read_bytes()
        document={'format':'alundra-content-database-v1','definitions':[],'instances':[],'event_graphs':[]}
        ProjectStateRegistry(document).create('switches','Lab Gate Open')
        project_exe,manifest=inject_private_state(stock_exe,document)
        flags,variants=open_world_starting_state()
        # The only allowed difference inside the verified new-game reset span
        # is native_injection_stack's exact lowered stack-top immediate.
        validate(project_exe,stock_exe,flags,variants)
        session=EditSession(datas)
        session.content_database={'mod_options':{'open_world':True,'skip_intro':True},**document}
        combined,qol=apply_qol(session,project_exe)
        self.assertNotEqual(combined,project_exe)
        self.assertLess(manifest['new_load'],0x80020000)
        self.assertTrue(qol['allocation']['native_stack']['injection_stack_overlap'] is False)
        self.assertTrue(any(row.get('format')=='alundra-editor-open-world-access-v1' for row in qol['patches']))


class InstantTextTests(unittest.TestCase):
    def test_wrapper_restores_decoder_arguments_after_each_call(self):
        words=json.loads((ROOT/'extras/game edits/tests/instant_text_words.json').read_text())['wrapper_words']
        m=Machine(struct.pack('<'+'I'*len(words),*words));m.r[4]=0x123;m.r[5]=0
        m.write(0x80107478,0);m.put(0x80106B00,b'ABCD')
        seen=[]
        def decoder(vm):
            seen.append((vm.r[4],vm.r[5]))
            cursor=vm.read(0x80107478)
            if cursor<4:vm.write(0x80107478,cursor+1)
            vm.r[4]=92;vm.r[5]=17
        m.calls[0x80046FB4]=decoder;m.run()
        self.assertEqual(seen,[(0x123,0)]*8)
    def test_gate_keeps_explicit_delay_and_external_pacing(self):
        words=json.loads((ROOT/'extras/game edits/tests/instant_text_words.json').read_text())['gate_words']
        for natural,flags,text,want in ((1,0,b'AB',0x800470F0),(0,0,b'AB',0x800470F0),
                                       (0,4,b'AB',0x80047E94),(0,0,b'\\T',0x80047E94),
                                       (0,0,b'\\Y',0x800470F0)):
            m=Machine(struct.pack('<'+'I'*len(words),*words));m.r[5]=natural
            m.write(0x80107460,flags);m.write(0x80107478,2);m.put(0x80106B00,text)
            chosen=[]
            for address in (0x800470F0,0x80047E94):m.calls[address]=lambda vm,address=address:chosen.append(address)
            m.run();self.assertEqual(chosen,[want])
    def run_wrapper(self,advance,flags=0,text=b'AB',budget=False):
        words=json.loads((ROOT/'extras/game edits/tests/instant_text_words.json').read_text())['wrapper_words']
        m=Machine(struct.pack('<'+'I'*len(words),*words));m.write(0x80107478,0);m.write(0x80107460,flags)
        m.put(0x80106B00,text)
        def decoder(vm):vm.write(0x80107478,vm.read(0x80107478)+advance)
        m.calls[0x80046FB4]=decoder
        for r in (16,17,18):m.r[r]=0x12340000+r
        before=list(m.r);m.run()
        self.assertEqual(m.r[16:19],before[16:19]);self.assertEqual(m.r[29],before[29]);self.assertEqual(m.r[31],before[31])
        return m.counts[0x80046FB4]
    def test_interpreter_stops_at_unchanged_cursor_confirm_and_wait_controls(self):
        self.assertEqual(self.run_wrapper(0),4)
        self.assertEqual(self.run_wrapper(1,4),1)
        self.assertEqual(self.run_wrapper(1,8),1)
        self.assertEqual(self.run_wrapper(2,text=b'\\T'),1)
        self.assertEqual(self.run_wrapper(2,text=b'\\Y'),1)
        self.assertEqual(self.run_wrapper(1,text=b'A'*2049),2048)


if __name__=='__main__':unittest.main()
