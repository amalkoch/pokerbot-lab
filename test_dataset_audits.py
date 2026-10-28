import csv
import tempfile
from pathlib import Path
import unittest
from audit_pokerbench import fingerprint, inspect_file, observation


class DatasetAuditTests(unittest.TestCase):
    def test_future_cards_and_targets_excluded(self):
        row = {'': '4', 'correct_decision': 'Fold', 'evaluation_at': 'Flop',
               'board_flop': 'AsKd2c', 'board_turn': 'Qh', 'board_river': 'Ts', 'holding': '3h3d'}
        visible = observation(row)
        self.assertNotIn('board_turn', visible)
        self.assertNotIn('board_river', visible)
        self.assertNotIn('correct_decision', visible)
        self.assertNotIn('', visible)
        row['board_turn'], row['board_river'], row['correct_decision'] = '9c', '9h', 'Call'
        self.assertEqual(fingerprint(visible), fingerprint(observation(row)))

    def test_street_visibility(self):
        row = {'evaluation_at':'Turn','board_turn':'Qh','board_river':'Ts'}
        self.assertIn('board_turn', observation(row))
        self.assertNotIn('board_river', observation(row))
        row['evaluation_at']='River'
        self.assertIn('board_river', observation(row))

    def test_duplicate_and_conflicting_labels(self):
        row = {'': '0', 'evaluation_at':'Flop','board_flop':'AsKd2c','board_turn':'Qh',
               'board_river':'Ts','holding':'3h3d','available_moves':"['Fold', 'Call']",'correct_decision':'Fold'}
        second = dict(row, correct_decision='Call', board_river='9h')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'fixture.csv'
            with path.open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=row.keys()); writer.writeheader(); writer.writerows([row,second])
            report, keys, labels = inspect_file(path)
        self.assertEqual(report['duplicate_observation_rows'], 1)
        self.assertEqual(report['observations_with_conflicting_labels'], 1)
        self.assertEqual(report['issues']['rows_with_populated_future_board_fields'], 2)
        self.assertEqual(len(keys), 1)
        self.assertEqual(next(iter(labels.values())), {'fold','call'})

    def test_index_does_not_define_identity(self):
        self.assertEqual(fingerprint(observation({'':'1','holding':'AsKd'})),
                         fingerprint(observation({'':'999','holding':'AsKd'})))


if __name__ == '__main__':
    unittest.main()
