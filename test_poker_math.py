import itertools
import math
import unittest
from poker_math import pot_odds, call_ev, bluff_ev, hit_probability, weighted_score, icm_equities


class MathTests(unittest.TestCase):
    def test_call_break_even_and_tie_equity(self):
        self.assertEqual(pot_odds(80, 20), .2)
        self.assertAlmostEqual(call_ev(80, 20, .2), 0)
        self.assertAlmostEqual(call_ev(80, 20, .3), 10)
        self.assertEqual(call_ev(100, 0, .5), 50)
        self.assertEqual(call_ev(20, 20, .5), 0)

    def test_bluff_threshold(self):
        self.assertAlmostEqual(bluff_ev(100, 50, 1/3), 0)
        self.assertEqual(bluff_ev(100, 50, 0), -50)
        self.assertEqual(bluff_ev(100, 50, 1), 100)

    def test_outs_against_enumeration(self):
        for unseen in range(1, 8):
            for outs in range(unseen + 1):
                for draws in range(unseen + 1):
                    hands = list(itertools.combinations(range(unseen), draws))
                    expected = sum(any(c < outs for c in hand) for hand in hands) / len(hands)
                    self.assertAlmostEqual(hit_probability(outs, unseen, draws), expected)
        self.assertEqual(hit_probability(0, 0, 0), 0)

    def test_weighted_total(self):
        self.assertEqual(weighted_score([1] * 6), 21)
        self.assertEqual(weighted_score([1, 2, 3, 4, 5, 6]), 91)

    def test_icm_known_cases(self):
        self.assertEqual(icm_equities([10], [100]), (100,))
        self.assertEqual(icm_equities([75, 25], [100]), (75, 25))
        self.assertEqual(icm_equities([75, 25], [70, 30]), (60, 40))
        for equity in icm_equities([20, 20, 20], [50, 30, 20]):
            self.assertAlmostEqual(equity, 100/3)
        for equity in icm_equities([80, 15, 5], [10, 10, 10]):
            self.assertAlmostEqual(equity, 10)

    def test_icm_against_independent_permutation_oracle(self):
        stacks, payouts = [50, 30, 15, 5], [60, 25, 10, 5]
        expected = [0.0] * 4
        for order in itertools.permutations(range(4)):
            remaining, probability = sum(stacks), 1.0
            for i in order:
                probability *= stacks[i] / remaining
                remaining -= stacks[i]
            for rank, i in enumerate(order):
                expected[i] += probability * payouts[rank]
        actual = icm_equities(stacks, payouts)
        for a, e in zip(actual, expected):
            self.assertAlmostEqual(a, e)
        self.assertAlmostEqual(sum(actual), sum(payouts))

    def test_icm_invariance(self):
        original = icm_equities([50, 30, 20], [50, 30, 20])
        scaled = icm_equities([500, 300, 200], [50, 30, 20])
        reordered = icm_equities([20, 50, 30], [50, 30, 20])
        for a, b in zip(original, scaled):
            self.assertAlmostEqual(a, b)
        for a, b in zip(reordered, [original[2], original[0], original[1]]):
            self.assertAlmostEqual(a, b)

    def test_reject_bad_inputs(self):
        cases = [(pot_odds, (0, 0)), (pot_odds, (-1, 20)),
                 (call_ev, (80, 20, 1.1)), (bluff_ev, (80, 20, math.nan)),
                 (pot_odds, (math.inf, 20)), (hit_probability, (9, 5, 2)),
                 (hit_probability, (1, 5, 6)), (hit_probability, (True, 5, 1)),
                 (weighted_score, ([1, 2],)), (icm_equities, ([], [10])),
                 (icm_equities, ([10, 0], [10])), (icm_equities, ([10, 20], [5, 10])),
                 (icm_equities, ([10], [10, 5])), (icm_equities, ([10] * 11, [10]))]
        for function, args in cases:
            with self.subTest(function=function.__name__, args=args):
                with self.assertRaises(ValueError):
                    function(*args)


if __name__ == '__main__':
    unittest.main()
