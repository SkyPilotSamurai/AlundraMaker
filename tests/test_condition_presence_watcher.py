import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from native_actor_lifecycle import compile_condition_presence_watcher

def run(code,flags,tests,present):
    """Tiny interpreter for the watcher: returns 'spawn', 'destroy' or None."""
    p=1;cond=None
    while True:
        op=code[p]
        if op in (0x30,0x31):
            flag,delta=struct.unpack_from('<Hh',code,p+1);taken=(flags.get(flag,False) if op==0x30 else not flags.get(flag,False))
            p=p+delta if taken else p+5;continue
        if op==0xE1:cond=tests.pop(0);p+=4;continue
        if op in (3,4):
            delta=struct.unpack_from('<h',code,p+1)[0];taken=cond if op==3 else not cond
            p=p+delta if taken else p+3;continue
        if op==2:
            delta=struct.unpack_from('<h',code,p+1)[0]
            if p+delta==0:return None
            p+=delta;continue
        if op==0x2C:cond=not present;p+=2;continue
        if op==0x2D:return 'spawn'
        if op==0x2E:return 'destroy'
        raise AssertionError(hex(op))

class WatcherTests(unittest.TestCase):
    def test_any_page_with_all_conditions_shows_actor(self):
        test=struct.pack('<BHB',0xE1,0,1)
        code=compile_condition_presence_watcher([[('flag',7,True),('test',test)],[('flag',9,False)]],3)
        self.assertEqual(code[0],0)
        self.assertEqual(run(code,{7:True,9:True},[True],False),'spawn')     # page 1 matches
        self.assertEqual(run(code,{7:True,9:True},[False],True),'destroy')   # neither page
        self.assertEqual(run(code,{7:False,9:False},[],False),'spawn')       # page 2 (switch 9 OFF)
        self.assertIsNone(run(code,{7:False,9:False},[],True))              # already there
        self.assertIsNone(run(code,{7:False,9:True},[],False))              # hidden stays hidden

if __name__=='__main__':unittest.main()
