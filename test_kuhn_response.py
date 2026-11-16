import unittest
from fractions import Fraction

from kuhn_response import best_response_value


class ResponseTest(unittest.TestCase):
    def test_equilibrium_has_no_seat_averaged_loss(self):
        third = Fraction(1, 3)
        equilibrium = {"": (third, 0, 1), "k": (third, 0, 1),
                       "b": (0, third, 1), "kb": (0, 2 * third, 1)}
        self.assertEqual(best_response_value(equilibrium, 0), -Fraction(1, 18))
        self.assertEqual(best_response_value(equilibrium, 1), Fraction(1, 18))

    def test_always_folding_to_bets_costs_one_ante(self):
        passive = dict.fromkeys(("", "k", "b", "kb"), (0, 0, 0))
        for seat in (0, 1):
            self.assertEqual(best_response_value(passive, seat), 1)
