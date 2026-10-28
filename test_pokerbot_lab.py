from itertools import permutations
import random
import unittest
from pokerbot_lab import LEGAL, Observation, POLICIES, play_hand, run_match, terminal_payoff


class ArenaTests(unittest.TestCase):
    def test_all_terminal_payoffs(self):
        for a, b in permutations(range(3), 2):
            sign = 1 if a > b else -1
            for history, expected in {"bf": 1, "kbf": -1, "kk": sign,
                                      "bc": 2 * sign, "kbc": 2 * sign}.items():
                self.assertEqual(terminal_payoff((a, b), history), expected)

    def test_showdown_and_zero_sum(self):
        for cards in permutations(range(3), 2):
            for first in POLICIES.values():
                for second in POLICIES.values():
                    result = play_hand(cards, (first, second), (random.Random(1), random.Random(2)))
                    self.assertEqual(sum(result), 0)
                    self.assertIn(abs(result[0]), (1, 2))

    def test_policy_legality(self):
        for policy in POLICIES.values():
            for card in range(3):
                for history, legal in LEGAL.items():
                    for seed in range(20):
                        obs = Observation(card, history, len(history) % 2, legal)
                        self.assertIn(policy(obs, random.Random(seed)), legal)

    def test_broken_policies_fall_back(self):
        def broken(obs, rng):
            raise RuntimeError("test")
        failures = [0, 0]
        result = play_hand((2, 0), (broken, broken), (None, None), failures=failures)
        self.assertEqual(result, (1, -1))
        self.assertEqual(failures, [1, 1])
        def illegal(obs, rng):
            return "raise"
        result = play_hand((0, 2), (illegal, POLICIES["cautious"]),
                           (random.Random(1), random.Random(2)))
        self.assertEqual(result, (-1, 1))

    def test_seat_balancing(self):
        result = run_match(POLICIES["calling"], POLICIES["calling"], pairs=30)
        self.assertEqual(result["chips_per_hand"], 0)
        self.assertEqual(result["hands"], 60)

    def test_reproducible_scores(self):
        a = run_match(POLICIES["mixed"], POLICIES["random"], pairs=100, seed=7)
        b = run_match(POLICIES["mixed"], POLICIES["random"], pairs=100, seed=7)
        for key in ("chips_per_hand", "approx_95pct_half_width", "invalid_or_failed_actions"):
            self.assertEqual(a[key], b[key])

    def test_reject_invalid_inputs(self):
        with self.assertRaises(ValueError):
            play_hand((1, 1), (None, None), (None, None))
        with self.assertRaises(ValueError):
            terminal_payoff((0, 1), "k")
        with self.assertRaises(ValueError):
            run_match(None, None, pairs=1)


if __name__ == "__main__":
    unittest.main()
