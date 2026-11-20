import math
import unittest
from unittest.mock import Mock
from fractions import Fraction

from kuhn_response import baseline, best_response_value
from pokerbot_lab import LEGAL, Observation, mixed, low_bluff


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

    def test_analysis_tables_match_executable_policy_thresholds(self):
        # Probe every observable state at either side of each decision threshold.
        # This catches stale analysis tables when a policy's probabilities change.
        for policy, bluff in ((mixed, Fraction(1, 3)),
                              (low_bluff, Fraction(1, 6))):
            profile = baseline(bluff)
            for history, actions in LEGAL.items():
                for card in range(3):
                    probability = float(profile[history][card])
                    probes = {0.0, math.nextafter(1.0, 0.0)}
                    if 0 < probability < 1:
                        probes.update((math.nextafter(probability, 0.0),
                                       probability,
                                       math.nextafter(probability, 1.0)))
                    observation = Observation(card, history, len(history) % 2, actions)
                    for draw in probes:
                        with self.subTest(policy=policy.__name__, history=history,
                                          card=card, draw=draw):
                            rng = Mock()
                            rng.random.return_value = draw
                            expected = actions[int(draw < probability)]
                            self.assertEqual(policy(observation, rng), expected)
