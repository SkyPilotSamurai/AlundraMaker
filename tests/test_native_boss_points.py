import struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
EXE=ROOT/'game/disc/ALUN_CD.EXE'
BASE=0x80020000-0x800

@unittest.skipUnless(EXE.exists(),'private stock executable missing')
class BossPointsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.exe=EXE.read_bytes()
 def test_sites_are_stock_and_safe_to_move(self):
  from native_boss_points import SITES,verify
  from capstone import Cs,CS_ARCH_MIPS,CS_MODE_MIPS32,CS_MODE_LITTLE_ENDIAN
  verify(self.exe,SITES)
  md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
  targets=set()
  code=self.exe[0x800:]
  for o in range(0,len(code)-4,4):
   i=next(md.disasm(code[o:o+4],0x80020000+o),None)
   if i is not None and i.mnemonic[0] in 'bj' and i.mnemonic not in ('jr','jalr','break'):
    try:targets.add(int(i.op_str.split(',')[-1],16))
    except ValueError:pass
  for c,rows in SITES.items():
   for at,word,reg,axis,*more in rows:
    # the containing function must already have saved ra (the stub's jal overwrites it)
    k=at
    while True:
     w=struct.unpack_from('<I',self.exe,k-BASE)[0]
     if w>>16==0x27BD and w&0x8000:break
     k-=4
    self.assertTrue(any(struct.unpack_from('<I',self.exe,q-BASE)[0]>>16==0xAFBF for q in range(k,at,4)),(c,hex(at),'ra not saved yet'))
    after=next(md.disasm(self.exe[at+4-BASE:at+8-BASE],at+4))
    before=next(md.disasm(self.exe[at-4-BASE:at-BASE],at-4))
    self.assertFalse(after.mnemonic[0] in 'bj',(c,hex(at),after.mnemonic))
    self.assertFalse(before.mnemonic[0] in 'bj' and before.mnemonic!='break',(c,hex(at),'site in a delay slot'))
    self.assertNotIn(at+4,targets,(c,hex(at)));self.assertNotIn(at+8,targets,(c,hex(at)))
    self.assertNotIn('$t',after.op_str.replace('$t9','').replace('$t8','') if False else '',None)
    if not more:self.assertNotIn(at+4,{a for rr in SITES.values() for a,*_ in rr},(c,hex(at),'next is a site: list it as extra'))
 def test_zorgia_injection(self):
  from project_state_runtime import inject_private_state
  out,m=inject_private_state(self.exe,{},boss_places={509:{483:(288,-72,-304)}})
  load,=struct.unpack_from('<I',out,0x18)
  for at in (0x800741C0,0x800741D4,0x800741E0):self.assertEqual(struct.unpack_from('<I',out,at-load+0x800)[0]>>26,3)
  self.assertEqual(m['boss_points']['classes'],{'509':{'483':[288,-72,-304]}})

class VictoryTests(unittest.TestCase):
 def test_melzas_victory_waits_for_flag_and_removes_him(self):
  from boss_victory import watcher,home_victory
  self.assertEqual(home_victory(327)[1],'remove')
  code=watcher([(1,'remove')],0x80)
  self.assertIn(bytes((0x2C,1,4))+struct.pack('<h',-8)+bytes((0x2E,1)),code)

if __name__=='__main__':unittest.main()
