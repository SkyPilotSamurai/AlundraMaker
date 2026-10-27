import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
ROOT=Path(__file__).resolve().parents[1]
US=ROOT/'game/disc/DATA/BALANCE.BIN'


@unittest.skipUnless(US.is_file(),'needs the local US BALANCE.BIN')
class JPBalanceTests(unittest.TestCase):
    def setUp(self):
        from enemy_definition import BalanceSession
        from content_database import ContentDatabase
        self.us=US.read_bytes()
        self.db=ContentDatabase();self.db.import_balance_table(self.us)
        self.extras={'DATA/BALANCE.BIN':BalanceSession(self.us)}

    def slime(self):
        return next(r for r in self.db.definitions if r['source'].get('balance_entry')==329 and not r.get('clone_of'))

    def test_switch_on_uses_japanese_stats_and_off_restores(self):
        from jp_balance import switch_balance,jp_balance_bytes
        self.assertEqual(self.slime()['data']['max_hp'],9)
        session,count=switch_balance(self.extras,self.db,True)
        self.assertEqual(bytes(session.data),jp_balance_bytes());self.assertEqual(session.disc_original,self.us)
        self.assertEqual(self.slime()['data']['max_hp'],6);self.assertGreaterEqual(count,100)
        session,_=switch_balance(self.extras,self.db,False)
        self.assertEqual(bytes(session.data),self.us);self.assertFalse(hasattr(session,'disc_original'))
        self.assertEqual(self.slime()['data']['max_hp'],9)

    def test_us_and_jp_buttons_each_apply_their_balance(self):
        from jp_balance import switch_balance,jp_balance_bytes,us_balance_bytes,balance_mode
        session,_=switch_balance(self.extras,self.db,'jp');self.assertEqual(self.slime()['data']['max_hp'],6)
        session,_=switch_balance(self.extras,self.db,'us')
        self.assertEqual(bytes(session.data),self.us);self.assertEqual(self.slime()['data']['max_hp'],9)
        self.assertEqual(us_balance_bytes(jp_balance_bytes()),self.us)  # modified disc: falls back to the stock file
        self.assertEqual(balance_mode({'jp_balance':True}),'jp');self.assertEqual(balance_mode({'balance':'us'}),'us')
        self.assertIsNone(balance_mode({}))

    def test_edited_entries_are_detected_for_the_warning(self):
        from jp_balance import edited_entries,switch_balance
        balance=self.extras['DATA/BALANCE.BIN']
        self.assertEqual(edited_entries(balance),[])
        balance.edit_stats(329,0,max_hp=20)
        self.assertEqual(edited_entries(balance),[329])
        session,_=switch_balance(self.extras,self.db,True)
        self.assertEqual(edited_entries(session),[])

    def test_database_edits_apply_against_the_jp_base(self):
        from jp_balance import switch_balance
        from database_balance import apply_definition_balance
        from enemy_definition import BalanceTable
        session,_=switch_balance(self.extras,self.db,True)
        row=self.slime();row['data']['max_hp']=11
        self.assertTrue(apply_definition_balance(session,row))
        self.assertEqual(BalanceTable(session.data).record(329)['max_hp'],11)
        patch=session.patch();self.assertEqual(len(patch['changes']),1)


if __name__=='__main__':unittest.main()
