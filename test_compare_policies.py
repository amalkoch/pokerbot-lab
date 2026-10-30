import unittest
from unittest.mock import patch
from compare_policies import compare


class ComparisonTests(unittest.TestCase):
    def run_case(self, **overrides):
        args = dict(candidate='mixed', baseline='cautious', opponents=['calling','random'], seeds=[7,19], pairs=20)
        args.update(overrides)
        return compare(**args)

    def test_same_policy_is_zero_despite_stochastic_actions(self):
        r = self.run_case(baseline='mixed')
        self.assertTrue(all(x['delta_chips_per_hand'] == 0 for x in r['records']))
        self.assertEqual(r['equal_weight_pool']['seed_block_standard_error'], 0)

    def test_reproduction_and_reversed_comparison(self):
        a = self.run_case(); b = self.run_case()
        self.assertEqual(a['per_opponent'], b['per_opponent'])
        reverse = self.run_case(candidate='cautious', baseline='mixed')
        self.assertAlmostEqual(a['equal_weight_pool']['mean_delta_chips_per_hand'],
                               -reverse['equal_weight_pool']['mean_delta_chips_per_hand'])
        self.assertEqual(a['total_hands'], 320)

    def test_block_aggregation_uses_seed_not_opponent_count(self):
        # Deliberately correlated opponent results: per-seed pool differences
        # are 1 and 3, so sample SD/sqrt(2) is exactly 1.
        def fake(first, second, pairs, seed):
            return {'chips_per_hand': (1 if seed == 7 else 3) if first.__name__ == 'mixed' else 0}
        with patch('compare_policies.run_match', side_effect=fake):
            r = self.run_case()
        self.assertEqual(r['equal_weight_pool']['blocks'], 2)
        self.assertEqual(r['equal_weight_pool']['mean_delta_chips_per_hand'], 2)
        self.assertAlmostEqual(r['equal_weight_pool']['seed_block_standard_error'], 1)

    def test_order_does_not_change_summary(self):
        a = self.run_case(); b = self.run_case(opponents=['random','calling'], seeds=[19,7])
        self.assertEqual(a['per_opponent'], b['per_opponent'])
        self.assertEqual(a['equal_weight_pool'], b['equal_weight_pool'])

    def test_invalid_experiment_rejected(self):
        for kwargs in [dict(seeds=[1,1]),dict(seeds=[1]),dict(seeds=[True,2]),
                       dict(opponents=[]),dict(opponents=['calling','calling']),
                       dict(candidate='unknown'),dict(pairs=True),dict(pairs=1)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_case(**kwargs)
