"""Run the animation-spawn wrapper in a MIPS emulator (unicorn) with a stub spawn routine."""
import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
try:
    import unicorn
    from unicorn import mips_const as M
except ImportError:
    unicorn=None
import native_animation_spawns as nas

BASE=0x80010000;ENTITY=0x80100000;STACK=0x801FF000;RET=0x80039410

@unittest.skipIf(unicorn is None,'unicorn not installed')
class AnimationSpawnTests(unittest.TestCase):
    def run_wrapper(self,rules,klass,target,previous,spawn_result=0x80150000):
        mu=unicorn.Uc(unicorn.UC_ARCH_MIPS,unicorn.UC_MODE_MIPS32+unicorn.UC_MODE_LITTLE_ENDIAN)
        mu.mem_map(0,0x200000)   # kseg0 80xxxxxx runs from physical 0
        P=lambda a:a&0x1FFFFFFF
        code=nas.emit(BASE,rules);mu.mem_write(P(BASE),code)
        mu.mem_write(P(nas.SPAWN),struct.pack('<2I',0x03E00008,0))     # stub: jr ra; nop
        mu.mem_write(P(RET),struct.pack('<I',0))
        e=bytearray(0x200);struct.pack_into('<I',e,0x68,klass);struct.pack_into('<I',e,0x8C,12)
        struct.pack_into('<3i',e,0x114,100<<16,200<<16,30<<16);mu.mem_write(P(ENTITY),bytes(e))
        regs=dict(S0=ENTITY,A0=0x1111,A1=0x2222,A2=target,A3=0x3333,V0=previous,V1=0x4444,SP=STACK,RA=RET)
        for k,v in regs.items():mu.reg_write(getattr(M,'UC_MIPS_REG_'+k),v)
        calls=[]
        def hook(uc,address,size,_):
            if address==nas.SPAWN:
                sp=uc.reg_read(M.UC_MIPS_REG_SP);y,z,d=struct.unpack('<3i',uc.mem_read((sp+0x10)&0x1FFFFFFF,12))
                calls.append(dict(parent=uc.reg_read(M.UC_MIPS_REG_A0),local=uc.reg_read(M.UC_MIPS_REG_A1),
                    index=uc.reg_read(M.UC_MIPS_REG_A2),x=struct.unpack('<i',struct.pack('<I',uc.reg_read(M.UC_MIPS_REG_A3)))[0]>>16,
                    y=y>>16,z=z>>16,direction=d,guard=struct.unpack('<I',uc.mem_read((BASE+4*78)&0x1FFFFFFF,4))[0]))
                # clobber caller-saved registers like a real routine would
                for r in ('A0','A1','A2','A3','V0','V1','T0','T1','T2','T3','T4','T5','T6','T7'):uc.reg_write(getattr(M,'UC_MIPS_REG_'+r),0xDEAD)
                uc.reg_write(M.UC_MIPS_REG_V0,spawn_result)
        mu.hook_add(unicorn.UC_HOOK_CODE,hook)
        mu.emu_start(BASE,RET,count=5000)
        out={k:mu.reg_read(getattr(M,'UC_MIPS_REG_'+k)) for k in ('A0','A1','A2','A3','V0','V1','SP','RA','S0')}
        return calls,out,struct.unpack('<I',mu.mem_read(P(BASE+4*78),4))[0]
    def rule(self,**k):
        r=dict(animation=3,spawn=420,dx=0,dy=0,dz=0);r['class']=418;r.update(k);return r
    def test_matching_animation_spawns_at_entity_with_offset(self):
        calls,out,guard=self.run_wrapper([self.rule(dx=8,dy=-4,dz=16)],0x1A2,3,1)
        self.assertEqual(len(calls),1);c=calls[0]
        self.assertEqual((c['parent'],c['local'],c['index']),(ENTITY,1,420-256))
        self.assertEqual((c['x'],c['y'],c['z'],c['direction']),(108,196,46,12))
        self.assertEqual(c['guard'],1);self.assertEqual(guard,0)
        self.assertEqual(out['V0'],3*7)                       # replaced instructions recomputed
        self.assertEqual((out['A0'],out['A1'],out['A2'],out['A3'],out['V1'],out['SP'],out['RA']),(0x1111,0x2222,3,0x3333,0x4444,STACK,RET))
    def test_same_animation_or_other_class_or_animation_does_nothing(self):
        for klass,target,previous in ((0x1A2,3,3),(0x1A3,3,1),(0x1A2,4,1)):
            calls,out,_=self.run_wrapper([self.rule()],klass,target,previous)
            self.assertEqual(calls,[]);self.assertEqual(out['V0'],target*7)
    def test_several_rules_and_global_class(self):
        calls,_,_=self.run_wrapper([self.rule(),self.rule(spawn=25),self.rule(animation=5,spawn=419)],0x1A2,3,0)
        self.assertEqual([(c['local'],c['index']) for c in calls],[(1,164),(0,25)])
    def test_rule_checks(self):
        with self.assertRaises(ValueError):nas.check_rules([self.rule(spawn=418)])
        with self.assertRaises(ValueError):nas.check_rules([self.rule(dx=9999)])
    def test_stock_hook_signature(self):
        exe=Path(__file__).resolve().parents[1]/'game'/'disc'/'ALUN_CD.EXE'
        if not exe.is_file():self.skipTest('private retail EXE not present')
        nas.validate(exe.read_bytes())

if __name__=='__main__':unittest.main()
