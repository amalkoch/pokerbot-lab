import unittest
from fractions import Fraction
from itertools import permutations
import random

from kuhn_matchup import expected_payoff, seat_average, opponent_profiles
from kuhn_response import baseline
from pokerbot_lab import POLICIES, play_hand


class MatchupTests(unittest.TestCase):
    def test_deterministic_tables_match_engine_all_deals(self):
        tables = opponent_profiles()
        for first in ('cautious', 'calling'):
            for second in ('cautious', 'calling'):
                total = sum(play_hand(cards, (POLICIES[first], POLICIES[second]),
                                      (random.Random(0), random.Random(1)))[0]
                            for cards in permutations(range(3), 2))
                self.assertEqual(expected_payoff(tables[first], tables[second]),
                                 Fraction(total, 6))

    def test_equilibrium_value_and_seat_sign(self):
        third = Fraction(1, 3)
        equilibrium = {'': (third, 0, 1), 'k': (third, 0, 1),
                       'b': (0, third, 1), 'kb': (0, 2 * third, 1)}
        self.assertEqual(expected_payoff(equilibrium, equilibrium), -Fraction(1, 18))
        self.assertEqual(seat_average(equilibrium, equilibrium), 0)
        mixed = baseline(third)
        self.assertEqual(seat_average(mixed, equilibrium),
                         -seat_average(equilibrium, mixed))

    def test_malformed_table_is_rejected(self):
        with self.assertRaises(ValueError):
            expected_payoff({}, baseline(Fraction(1, 3)))
