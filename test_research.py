"""Optional research checks; core lab still runs without third-party packages."""
import importlib.util
import json
from pathlib import Path
import random
import unittest

HAS_RESEARCH = all(importlib.util.find_spec(name) for name in ('pyspiel', 'pokerkit'))


@unittest.skipUnless(HAS_RESEARCH, 'Install requirements-research.txt')
class ResearchTests(unittest.TestCase):
    def test_export_and_convergence(self):
        import pyspiel
        from simulation_benchmark import states, export_policy
        game = pyspiel.load_game('kuhn_poker')
        solver = pyspiel.CFRPlusSolver(game)
        initial = pyspiel.exploitability(game, solver.average_policy())
        for _ in range(100):
            solver.evaluate_and_update_policy()
        self.assertLess(pyspiel.exploitability(game, solver.average_policy()), initial / 10)
        reps = states(game)
        for key, distribution in export_policy(solver.average_policy(), reps).items():
            self.assertEqual(set(reps[key].legal_actions()), {a for a, _ in distribution})
            self.assertAlmostEqual(sum(p for _, p in distribution), 1)
            self.assertTrue(all(p >= 0 for _, p in distribution))

    def test_replay_sample(self):
        import pyspiel
        rows = json.loads((Path(__file__).parent / 'results/simulation_sample.json').read_text())
        for row in rows:
            state = pyspiel.load_game(row['game']).new_initial_state()
            for event in row['history']:
                if state.is_chance_node():
                    self.assertEqual(event['player'], -1)
                    self.assertIn(event['action'], dict(state.chance_outcomes()))
                else:
                    self.assertEqual(event['player'], state.current_player())
                    self.assertEqual(event['information'], state.information_state_string())
                    self.assertEqual(event['legal_actions'], state.legal_actions())
                    self.assertIn(event['action'], state.legal_actions())
                state.apply_action(event['action'])
            self.assertTrue(state.is_terminal())
            self.assertEqual(state.returns(), row['returns'])

    def test_reproducibility_and_information_boundary(self):
        import pyspiel
        from simulation_benchmark import simulate, decide
        game = pyspiel.load_game('kuhn_poker')
        first = simulate(game, ('uniform', 'uniform'), {}, 123, 456)
        second = simulate(game, ('uniform', 'uniform'), {}, 123, 456)
        self.assertEqual(first[:2], second[:2])
        # Two hidden opponent cards give exactly the same visible information.
        a, b = game.new_initial_state(), game.new_initial_state()
        for state, card in ((a, 1), (b, 2)):
            state.apply_action(0)
            state.apply_action(card)
        self.assertEqual(a.information_state_string(), b.information_state_string())
        table = {a.information_state_string(): [[0, .4], [1, .6]]}
        self.assertEqual(decide('trained', a.information_state_string(), a.legal_actions(), table, random.Random(1)),
                         decide('trained', b.information_state_string(), b.legal_actions(), table, random.Random(1)))

    def test_uci_mapping(self):
        from validate_uci import classify
        self.assertEqual(classify([1, 1, 1, 10, 1, 11, 1, 12, 1, 13]), 9)
        self.assertEqual(classify([2, 1, 2, 2, 2, 3, 2, 4, 2, 5]), 8)
        self.assertEqual(classify([1, 1, 2, 1, 3, 1, 4, 1, 1, 2]), 7)
        with self.assertRaises(ValueError):
            classify([1, 1] * 5)


if __name__ == '__main__':
    unittest.main()
