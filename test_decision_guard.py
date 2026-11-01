import unittest
from decision_guard import guarded_decision, fault_drill
from pokerbot_lab import Observation, play_hand


class GuardTests(unittest.TestCase):
    def call(self, policy, legal=('check','bet'), elapsed=100, budget=1000000):
        ticks=iter((0,elapsed))
        return guarded_decision(policy, Observation(2,'',0,legal),None,budget,lambda:next(ticks))

    def test_late_valid_action_checks_or_folds(self):
        for legal in [('check','bet'),('fold','call')]:
            r=self.call(lambda o,r:o.legal_actions[-1],legal,1000001)
            self.assertEqual(r['action'],legal[0]);self.assertTrue(r['late'])
            self.assertFalse(r['invalid_action'])

    def test_boundary_and_disabled_budget(self):
        self.assertEqual(self.call(lambda o,r:'bet',elapsed=1000000)['action'],'bet')
        self.assertEqual(self.call(lambda o,r:'bet',elapsed=1000001,budget=None)['action'],'bet')

    def test_exception_is_distinct_from_invalid(self):
        def crash(o,r): raise RuntimeError('test')
        result=self.call(crash)
        self.assertTrue(result['exception']);self.assertFalse(result['invalid_action'])
        result=self.call(lambda o,r:'raise')
        self.assertFalse(result['exception']);self.assertTrue(result['invalid_action'])

    def test_arbitrary_return_object_cannot_crash_comparison(self):
        class Bad:
            def __eq__(self,other): raise RuntimeError('bad equality')
        self.assertEqual(self.call(lambda o,r:Bad())['action'],'check')

    def test_fault_matrix(self):
        r=fault_drill();self.assertEqual(r['cases'],60);self.assertEqual(r['fallbacks'],36)
        self.assertEqual(sum(x['late'] for x in r['records']),12)

    def test_arena_uses_fallback_and_counts_each_failure_once(self):
        class Bad:
            def __eq__(self, other): raise RuntimeError('bad equality')
        def broken(o,r): return Bad()
        failures=[0,0]
        payoff=play_hand((2,0),(broken,broken),(None,None),failures=failures)
        self.assertEqual(payoff,(1,-1));self.assertEqual(failures,[1,1])

    def test_invalid_budget_and_no_safe_fallback(self):
        for budget in [0,-1,True,1.5]:
            with self.assertRaises(ValueError): self.call(lambda o,r:'bet',budget=budget)
        with self.assertRaises(ValueError): self.call(lambda o,r:'call',legal=('call',))
