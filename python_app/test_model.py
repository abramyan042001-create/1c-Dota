import copy
import unittest
from model import Database

class DomainTests(unittest.TestCase):
    def setUp(self):
        self.db=Database(':memory:'); self.db.add_user('Admin','test-password','Admin'); self.db.seed('Admin')
    def tearDown(self): self.db.db.close()
    def match(self):
        return dict(name='Тест',date='2026-09-11 12:00',side='Radiant',win=True,duration=40,patch='учебный',comment='',participants=[dict(player='player-me',hero='hero-Phantom Assassin',role='Carry',kills=10,deaths=2,assists=4,networth=20000,build='build-PA Crit')],purchases=[dict(player='player-me',item='item-Daedalus',minute=30)])
    def test_seed_and_calculator(self):
        first=self.db.export_data(); self.db.seed('Admin'); self.assertEqual(first,self.db.export_data())
        self.assertEqual(len(self.db.all('heroes')),25)
        self.assertEqual(self.db.calculate('build-PA Crit'),(22350,[]))
    def test_slots(self):
        b=self.db.get('builds','build-PA Crit'); b['slots'][1]['slot']=1
        with self.assertRaises(ValueError): self.db.save('builds',b,'Admin')
    def test_post_repost_unpost(self):
        ident=self.db.save('matches',self.match(),'Admin'); self.assertEqual(self.db.reports(),([],[]))
        self.db.post(ident,True,'Admin'); self.db.post(ident,True,'Admin')
        wins,purchases=self.db.reports(); self.assertEqual(wins[0][2:],(1,1,100.0,7.0)); self.assertEqual(purchases[0][-1],1)
        with self.assertRaises(ValueError): self.db.save('matches',self.db.get('matches',ident),'Admin')
        self.db.post(ident,False,'Admin'); self.assertEqual(self.db.reports(),([],[]))
        self.db.delete('matches',ident,'Admin')
    def test_invalid_purchase(self):
        m=self.match(); m['purchases'][0]['minute']=41
        with self.assertRaises(ValueError): self.db.save('matches',m,'Admin')
        m=self.match(); m['participants']=[]
        with self.assertRaises(ValueError): self.db.save('matches',m,'Admin')
    def test_permissions_and_password(self):
        self.db.add_user('Player','long-password','Player','Admin'); self.assertEqual(self.db.login('Player','long-password'),'Player')
        with self.assertRaises(ValueError): self.db.login('Player','wrong')
        with self.assertRaises(ValueError): self.db.seed('Player')
        self.db.save('matches',self.match(),'Player')
    def test_atomic_import(self):
        before=self.db.export_data(); broken=copy.deepcopy(before)
        broken['records']['items'][0]['price']=-1
        with self.assertRaises(ValueError): self.db.import_data(broken,'Admin')
        self.assertEqual(before,self.db.export_data())
    def test_references(self):
        with self.assertRaises(ValueError): self.db.delete('heroes','hero-Phantom Assassin','Admin')
    def test_round_trip(self):
        other=Database(':memory:'); other.add_user('Admin','test-password','Admin')
        other.import_data(self.db.export_data(),'Admin'); self.assertEqual(other.export_data(),self.db.export_data()); other.db.close()

if __name__=='__main__': unittest.main()
