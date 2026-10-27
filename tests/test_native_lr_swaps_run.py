"""Run the L/R swap wrapper in a MIPS emulator (unicorn) with stub native getters/setters:
cycle orders follow the item-swap Lua script, unowned entries are skipped, and
nothing happens while a menu or event runs."""
import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
try:
    import unicorn
    from unicorn import mips_const as M
except ImportError:
    unicorn=None
import native_lr_swaps as lr

BASE=0x80010000;STATS=0x80100000;STACK=0x801FF000;RET=0x8002BD9C
UPDATE,GET,SET_WEAPON,SET_ITEM=0x8002E3B4,0x8004F810,0x8004FB28,0x8004FB84
# item group -> native item id that the stub getter returns
ITEM_OF={12:0x24,14:0x29,13:0x25,15:0x26,30:0x27,11:0x23,16:0x2B,17:0x2D,18:0x2F,19:0x31,
         26:0x20,27:0x28,31:0x36,23:0x3B,29:0x1F,20:0x33,21:0x35,22:0x37}


@unittest.skipIf(unicorn is None,'unicorn not installed')
class LRSwapRunTests(unittest.TestCase):
    def run_swap(self,pressed,weapon=1,item=0x24,owned_weapons=(1,2,3,4,5,6),owned_groups=tuple(ITEM_OF),menu=0,held=0):
        mu=unicorn.Uc(unicorn.UC_ARCH_MIPS,unicorn.UC_MODE_MIPS32+unicorn.UC_MODE_LITTLE_ENDIAN)
        mu.mem_map(0,0x200000)
        P=lambda a:a&0x1FFFFFFF
        mu.mem_write(P(BASE),lr.emit_wrapper(BASE))
        for f in (UPDATE,GET,SET_WEAPON,SET_ITEM):mu.mem_write(P(f),struct.pack('<2I',0x03E00008,0))
        mu.mem_write(P(RET),struct.pack('<I',0))
        # item metadata (group per item id), 10 bytes each
        meta=bytearray(10*128)
        for group,item_id in ITEM_OF.items():struct.pack_into('<h',meta,10*item_id,group)
        mu.mem_write(P(0x800BBE50),bytes(meta))
        stats=bytearray(0x20);struct.pack_into('<hh',stats,0x0A,weapon,item);mu.mem_write(P(STATS),bytes(stats))
        mu.mem_write(P(0x80119AE8),struct.pack('<I',STATS))
        mu.mem_write(P(0x801F0060),struct.pack('<I',menu))
        mu.mem_write(P(0x801DDA48),struct.pack('<HH',held,pressed))
        for r,v in dict(SP=STACK,RA=RET).items():mu.reg_write(getattr(M,'UC_MIPS_REG_'+r),v)
        calls=[]
        def hook(uc,address,size,_):
            a0=uc.reg_read(M.UC_MIPS_REG_A0)
            if address==UPDATE:uc.reg_write(M.UC_MIPS_REG_V0,0x77)
            elif address==GET:
                if a0 in owned_weapons and len(calls)>=0 and calls_kind[0]=='weapon':
                    uc.reg_write(M.UC_MIPS_REG_V0,a0)
                elif calls_kind[0]=='item' and a0 in owned_groups:
                    uc.reg_write(M.UC_MIPS_REG_V0,ITEM_OF[a0])
                else:uc.reg_write(M.UC_MIPS_REG_V0,0xFFFFFFFF)
                for r in ('T0','T1','T2','A1','A2','A3'):uc.reg_write(getattr(M,'UC_MIPS_REG_'+r),0xDEAD)
            elif address==SET_WEAPON:calls.append(('weapon',a0))
            elif address==SET_ITEM:calls.append(('item',a0))
        calls_kind=['weapon' if pressed&0xC else 'item']
        mu.hook_add(unicorn.UC_HOOK_CODE,hook)
        mu.emu_start(BASE,RET,count=20000)
        self.assertEqual(mu.reg_read(M.UC_MIPS_REG_V0),0x77)        # UpdateWorld result kept
        self.assertEqual(mu.reg_read(M.UC_MIPS_REG_SP),STACK)
        return calls

    def test_weapon_order_matches_script(self):
        R1,L1=0x08,0x04
        self.assertEqual(self.run_swap(R1,weapon=1),[('weapon',3)])   # sword -> flail
        self.assertEqual(self.run_swap(R1,weapon=3),[('weapon',2)])   # flail -> bow
        self.assertEqual(self.run_swap(R1,weapon=6),[('weapon',1)])   # spirit wand -> sword
        self.assertEqual(self.run_swap(L1,weapon=1),[('weapon',6)])   # sword <- spirit wand
        self.assertEqual(self.run_swap(L1,weapon=2),[('weapon',3)])   # bow <- flail

    def test_unowned_weapons_are_skipped(self):
        self.assertEqual(self.run_swap(0x08,weapon=2,owned_weapons=(1,2)),[('weapon',1)])
        self.assertEqual(self.run_swap(0x04,weapon=1,owned_weapons=(1,2)),[('weapon',2)])

    def test_item_order_matches_script(self):
        R2,L2=0x02,0x01
        self.assertEqual(self.run_swap(R2,item=0x24),[('item',0x29)])   # herbs -> strength tonic
        self.assertEqual(self.run_swap(L2,item=0x24),[('item',0x37)])   # herbs <- recovery ring
        self.assertEqual(self.run_swap(R2,item=0x27),[('item',0x23)])   # wonder essence -> mining bomb
        self.assertEqual(self.run_swap(R2,item=0x24,owned_groups=(12,11)),[('item',0x23)])

    def test_no_swap_in_menu_or_with_select(self):
        self.assertEqual(self.run_swap(0x08,menu=1),[])
        self.assertEqual(self.run_swap(0x08,held=0x100),[])


if __name__=='__main__':unittest.main()
