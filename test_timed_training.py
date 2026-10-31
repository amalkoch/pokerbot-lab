import math
import unittest
from timed_training import train_for, run


class TimerTests(unittest.TestCase):
    def test_atomic_step_overshoot_is_reported(self):
        now = [0.0]
        def step(): now[0] += .4
        r = train_for(step, 1, clock=lambda:now[0])
        self.assertEqual(r['iterations'], 3)
        self.assertAlmostEqual(r['overshoot_seconds'], .2)

    def test_exact_deadline_does_not_start_extra_step(self):
        now = [0.0]
        def step(): now[0] += .5
        r = train_for(step, 1, clock=lambda:now[0])
        self.assertEqual(r['iterations'], 2)
        self.assertEqual(r['overshoot_seconds'], 0)

    def test_no_forced_iteration_after_expired_deadline(self):
        values = iter([0,2])
        r = train_for(lambda:self.fail('deadline already passed'), 1, clock=lambda:next(values))
        self.assertEqual(r['iterations'], 0)
        self.assertEqual(r['overshoot_seconds'], 1)

    def test_failures_are_not_silently_counted(self):
        def fail(): raise RuntimeError('broken update')
        with self.assertRaises(RuntimeError): train_for(fail, 1, clock=lambda:0)

    def test_invalid_budget_and_seeds(self):
        for x in (True,0,-1,math.nan,math.inf,'1'):
            with self.subTest(x=x), self.assertRaises(ValueError): train_for(lambda:None,x)
            with self.subTest(run=x), self.assertRaises(ValueError): run(x)
        for seeds in ([1],[1,1],[-1,2],[True,2],[2**31,2]):
            with self.subTest(seeds=seeds), self.assertRaises(ValueError): run(.1,seeds)
