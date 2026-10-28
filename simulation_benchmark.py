"""Train with OpenSpiel; export small policies; simulate held-out paired games."""
import argparse
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import random
import statistics
import time
import pyspiel


def states(game):
    representatives = {}
    def visit(state):
        if state.is_terminal():
            return
        if state.is_chance_node():
            actions = [a for a, _ in state.chance_outcomes()]
        else:
            representatives.setdefault(state.information_state_string(), state.clone())
            actions = state.legal_actions()
        for action in actions:
            visit(state.child(action))
    visit(game.new_initial_state())
    return representatives


def export_policy(policy, representatives):
    table = {}
    for key, state in representatives.items():
        values = dict(policy.get_state_policy(state))
        legal = state.legal_actions()
        weights = [float(values.get(a, 0)) for a in legal]
        total = sum(weights)
        if total <= 0 or any(w < 0 for w in weights):
            raise ValueError('Invalid learned distribution')
        table[key] = [[a, w / total] for a, w in zip(legal, weights)]
    return table


def draw(distribution, rng):
    r = rng.random()
    running = 0.0
    for action, probability in distribution:
        running += probability
        if r < running:
            return action
    return distribution[-1][0]


def decide(kind, information, legal, table, rng):
    """Runtime sees only the acting player's information and legal actions."""
    if kind == 'trained':
        if information not in table:
            raise KeyError('Unseen information state: incompatible game/policy')
        distribution = table[information]
        if {a for a, _ in distribution} != set(legal):
            raise ValueError('Policy actions do not match game')
        return draw(distribution, rng)
    if kind == 'uniform':
        return rng.choice(legal)
    if kind == 'passive':
        return 1 if 1 in legal else min(legal)  # Leduc: 1=check/call
    if kind == 'aggressive':
        return 2 if 2 in legal else 1 if 1 in legal else min(legal)
    raise ValueError(kind)


def simulate(game, kinds, table, chance_seed, policy_seed):
    state = game.new_initial_state()
    chance_rng = random.Random(chance_seed)
    player_rngs = [random.Random(policy_seed), random.Random(policy_seed + 1)]
    history, latencies = [], [[], []]
    while not state.is_terminal():
        if state.is_chance_node():
            action = draw(state.chance_outcomes(), chance_rng)
            history.append({'player': -1, 'action': action})
        else:
            player = state.current_player()
            information = state.information_state_string(player)
            legal = state.legal_actions(player)
            started = time.perf_counter_ns()
            action = decide(kinds[player], information, legal, table, player_rngs[player])
            elapsed = time.perf_counter_ns() - started
            latencies[player].append(elapsed)
            if action not in legal:
                raise AssertionError('Illegal move')
            history.append({'player': player, 'information': information,
                            'legal_actions': legal, 'action': action})
        state.apply_action(action)
    payoff = state.returns()
    if abs(sum(payoff)) > 1e-9:
        raise AssertionError('Non-zero-sum payoff')
    return payoff, history, latencies


def train(game_name, iterations, seed):
    game = pyspiel.load_game(game_name)
    reps = states(game)
    solvers = [('cfr', pyspiel.CFRSolver(game)), ('cfr_plus', pyspiel.CFRPlusSolver(game))]
    solvers += [('external_mccfr_seed_' + str(s), pyspiel.ExternalSamplingMCCFRSolver(game, s))
                for s in (seed, seed + 1, seed + 2)]
    records, best = [], None
    for name, solver in solvers:
        trace = []
        start = time.perf_counter()
        step = solver.run_iteration if name.startswith('external') else solver.evaluate_and_update_policy
        for iteration in range(1, iterations + 1):
            step()
            if iteration in {1, 10, 100, iterations}:
                trace.append({'iteration': iteration, 'seconds_including_checks': time.perf_counter() - start,
                              'exploitability': pyspiel.exploitability(game, solver.average_policy())})
        elapsed = time.perf_counter() - start
        policy = solver.average_policy()
        metric = pyspiel.exploitability(game, policy)
        table = export_policy(policy, reps)
        record = {'algorithm': name, 'iterations': iterations, 'seconds_including_checks': elapsed,
                  'exploitability': metric, 'information_states': len(table), 'trace': trace}
        records.append(record)
        print(game_name, name, 'exploitability', metric, 'seconds', round(elapsed, 2), flush=True)
        if best is None or metric < best[0]:
            best = (metric, name, table)
    return records, best


def run(iterations, pairs, seed, output):
    output.mkdir(parents=True, exist_ok=True)
    report = {'seed': seed, 'iterations_per_solver': iterations,
              'environment': {'python': platform.python_version(), 'platform': platform.platform(),
                              'open_spiel': importlib.metadata.version('open_spiel')},
              'training': {}, 'evaluation': [], 'notes': [
                  'Equal iterations, not equal compute; use timing as well as exploitability.',
                  'Training games are two-player zero-sum Kuhn/Leduc, not the unreleased eight-bot event.',
                  'Decision timings exclude information-state construction, process startup and sandbox overhead.',
                  'Confidence intervals use paired-seed mean returns; self-play is a seat-symmetry check.',
                  'Synthetic replay histories include chance cards: for offline analysis, not agent inputs.']}
    selected = None
    for game_name in ['kuhn_poker', 'leduc_poker']:
        records, best = train(game_name, iterations, seed)
        report['training'][game_name] = records
        policy_path = output / (game_name + '_policy.json')
        policy_path.write_text(json.dumps({'game': game_name, 'algorithm': best[1], 'table': best[2]}, sort_keys=True))
        if game_name == 'leduc_poker':
            selected = best
            report['selected_policy'] = {'game': game_name, 'algorithm': best[1], 'exploitability': best[0],
                                         'file_bytes': policy_path.stat().st_size,
                                         'sha256': hashlib.sha256(policy_path.read_bytes()).hexdigest()}
    game = pyspiel.load_game('leduc_poker')
    table = selected[2]
    sample = []
    dataset_path = output / 'simulated_hands.jsonl.gz'
    with gzip.open(dataset_path, 'wt') as dataset:
        for opponent_index, opponent in enumerate(['uniform', 'passive', 'aggressive', 'trained']):
            pair_values, timings = [], []
            for pair in range(pairs):
                # Disjoint deterministic seeds per opponent and pair, separate from training.
                deal_seed = seed + 1_000_000 + opponent_index * 10_000_000 + pair
                values = []
                for seat in (0, 1):
                    kinds = ('trained', opponent) if seat == 0 else (opponent, 'trained')
                    returns, history, timing = simulate(game, kinds, table, deal_seed, deal_seed + 50_000_000)
                    values.append(returns[seat])
                    timings.extend(timing[seat])
                    row = {'game': 'leduc_poker', 'opponent': opponent, 'pair': pair, 'trained_seat': seat,
                           'chance_seed': deal_seed, 'returns': returns, 'history': history}
                    dataset.write(json.dumps(row, separators=(',', ':')) + '\n')
                    if pair < 10:
                        sample.append(row)
                pair_values.append(statistics.mean(values))
            ordered = sorted(timings)
            record = {'opponent': opponent, 'hands': pairs * 2,
                      'mean_net_chips_per_hand': statistics.mean(pair_values),
                      'approx_95pct_half_width': 1.96 * statistics.stdev(pair_values) / pairs ** .5,
                      'policy_decisions': len(ordered), 'p99_decision_us': ordered[int(.99*(len(ordered)-1))] / 1000,
                      'max_decision_us': ordered[-1] / 1000,
                      'decisions_over_1ms': sum(t > 1_000_000 for t in ordered), 'illegal_actions': 0}
            report['evaluation'].append(record)
            print('evaluation', record, flush=True)
    (output / 'simulation_sample.json').write_text(json.dumps(sample, indent=2))
    report['dataset'] = {'file': dataset_path.name, 'hands': pairs * 8, 'bytes': dataset_path.stat().st_size,
                         'sha256': hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
                         'provenance': 'Generated locally by simulation_benchmark.py; not observed tournament play.'}
    (output / 'benchmark.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--iterations', type=int, default=1000)
    parser.add_argument('--pairs', type=int, default=12500, help='Pairs per opponent; total hands = pairs * 8')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path, default=Path('results'))
    args = parser.parse_args()
    if args.iterations < 1 or args.pairs < 2:
        parser.error('iterations >= 1 and pairs >= 2 required')
    run(args.iterations, args.pairs, args.seed, args.output)
