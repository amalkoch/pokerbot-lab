import unittest
from build_drill import review, CHECKPOINTS


class BuildDrillTests(unittest.TestCase):
    def entry(self,name,minute):
        return {'checkpoint':name,'minute':minute,'evidence':'self-reported test-output.txt'}

    def test_empty_plan_is_not_completed(self):
        r=review([],0)
        self.assertFalse(r['all_checkpoints_recorded']);self.assertFalse(r['all_on_time'])
        self.assertEqual(r['remaining_minutes'],60)
        self.assertTrue(all(x['status']=='pending' for x in r['checkpoints']))

    def test_exact_deadline_boundary(self):
        self.assertEqual(review([],10)['checkpoints'][0]['status'],'overdue')
        self.assertEqual(review([self.entry('baseline',10)],10)['checkpoints'][0]['status'],'on_time')

    def test_late_missing_and_finished_are_distinct(self):
        r=review([self.entry('baseline',12)],65)
        self.assertTrue(r['session_finished']);self.assertEqual(r['remaining_minutes'],0)
        self.assertFalse(r['all_checkpoints_recorded']);self.assertEqual(r['checkpoints'][0]['status'],'late')
        self.assertTrue(all(x['status']=='overdue' for x in r['checkpoints'][1:]))

    def test_complete_log_does_not_claim_verified_evidence(self):
        entries=[self.entry(name,deadline) for name,deadline,_ in CHECKPOINTS]
        r=review(entries,60)
        self.assertTrue(r['all_on_time']);self.assertTrue(r['all_checkpoints_recorded'])
        self.assertFalse(r['evidence_verified'])

    def test_malformed_logs_rejected(self):
        cases=[([self.entry('unknown',1)],5),([self.entry('baseline',6)],5),
               ([self.entry('baseline',2),self.entry('baseline',3)],5),
               ([self.entry('baseline',3),self.entry('legality',2)],5),
               ([{'checkpoint':'baseline','minute':1,'evidence':' '}],5),
               ([self.entry('baseline',True)],5),([],float('nan')),([],True),({},5)]
        for entries,elapsed in cases:
            with self.subTest(entries=entries,elapsed=elapsed),self.assertRaises(ValueError):review(entries,elapsed)
