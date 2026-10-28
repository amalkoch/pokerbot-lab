import importlib.util
import unittest

@unittest.skipUnless(importlib.util.find_spec('sklearn'), 'Install research dependencies')
class PreflopTests(unittest.TestCase):
    def row(self, cards='AsKh', label='call'):
        return {'prev_line':'UTG/2.0bb','hero_pos':'BB','hero_holding':cards,
                'pot_size':'3.5','num_players':'2','num_bets':'1',
                'available_moves':"['call', 'fold']",'correct_decision':label}

    def test_suit_and_card_order_identity(self):
        from train_preflop import identity
        self.assertEqual(identity(self.row()),identity(self.row('KcAd')))
        self.assertNotEqual(identity(self.row()),identity(self.row('AsKs')))

    def test_conflicts_quarantined(self):
        from train_preflop import clean
        kept,report,_=clean([self.row(),self.row('KcAd'),self.row('AcKd','fold')])
        self.assertEqual(kept,[])
        self.assertEqual(report['quarantined_rows'],3)

    def test_feature_information_boundary(self):
        from train_preflop import features
        a=self.row();b=dict(a,correct_decision='fold',board_turn='Ah',opponent_cards='AcAd')
        self.assertEqual(features(a,'call'),features(b,'call'))

    def test_selection_scopes_to_each_hand(self):
        from train_preflop import select
        self.assertEqual(select([.1,.9,.8,.2],['call','fold','check','2.0bb'],[2,2]),['fold','check'])

    def test_exact_size_is_feature(self):
        from train_preflop import features
        self.assertNotEqual(features(self.row(),'3.0bb'),features(self.row(),'8.0bb'))

if __name__=='__main__':
    unittest.main()
