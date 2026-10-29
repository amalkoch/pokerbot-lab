import math
import unittest
from tournament_risk import compare_gamble


class TournamentRiskTests(unittest.TestCase):
    def run_case(self, **overrides):
        args = dict(stacks=[40, 40, 20], payouts=[50, 30, 20],
                    hero=0, opponent=1, risk=40, win_probability=.55)
        args.update(overrides)
        return compare_gamble(**args)

    def test_positive_chip_ev_can_lose_points(self):
        r = self.run_case()
        self.assertAlmostEqual(r['chip_ev'], 4)
        self.assertLess(r['point_ev'], 0)
        self.assertGreater(r['point_break_even'], .55)
        # Winning leaves two players, 80/20, paying 50/30: .8*50+.2*30.
        self.assertAlmostEqual(r['win_points'], 46)
        self.assertEqual(r['lose_points'], 20)
        self.assertAlmostEqual(self.run_case(win_probability=r['point_break_even'])['point_ev'], 0)

    def test_winner_take_all_matches_chip_ev(self):
        r = self.run_case(payouts=[100])
        self.assertAlmostEqual(r['point_break_even'], .5)
        self.assertAlmostEqual(r['point_ev'], r['chip_ev'])

    def test_flat_payouts_have_no_unique_threshold(self):
        r = self.run_case(payouts=[10, 10, 10])
        self.assertEqual(r['point_ev'], 0)
        self.assertIsNone(r['point_break_even'])
        self.assertIsNone(r['risk_premium'])

    def test_non_bust_heads_up_is_linear(self):
        r = self.run_case(stacks=[60, 40], payouts=[70, 30], risk=10)
        self.assertAlmostEqual(r['point_ev'], .4)
        self.assertAlmostEqual(r['point_break_even'], .5)

    def test_scaling_symmetry_and_no_mutation(self):
        stacks = [40, 40, 20]
        r = self.run_case(stacks=stacks)
        scaled = self.run_case(stacks=[400, 400, 200], risk=400)
        swapped = self.run_case(hero=1, opponent=0)
        self.assertEqual(stacks, [40, 40, 20])
        for key in ('point_ev', 'point_break_even', 'win_points', 'lose_points'):
            self.assertAlmostEqual(r[key], scaled[key])
            self.assertAlmostEqual(r[key], swapped[key])

    def test_probability_endpoints(self):
        for p, key in [(0, 'lose_points'), (1, 'win_points')]:
            r = self.run_case(win_probability=p)
            self.assertEqual(r['expected_points'], r[key])

    def test_bad_inputs(self):
        for changes in [dict(hero=True), dict(hero=-1), dict(hero=3), dict(opponent=0),
                        dict(risk=0), dict(risk=41), dict(risk=math.nan),
                        dict(win_probability=1.1), dict(stacks=[40, 0, 20])]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.run_case(**changes)
