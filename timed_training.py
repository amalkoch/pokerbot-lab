"""Unofficial offline solver comparison with equal requested training time."""
import argparse
import importlib.metadata
import json
import math
import platform
import time


def train_for(step, seconds, clock=time.perf_counter):
    """Check a soft deadline BETWEEN atomic updates; never interrupt an update.

    Includes loop/timer overhead, excludes construction and final evaluation.
    Returns measured overshoot rather than claiming a hard time limit.
    """
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('seconds must be finite and positive')
    start = clock()
    iterations = 0
    elapsed = clock() - start
    while elapsed < seconds:
        step()
        iterations += 1
        elapsed = clock() - start
    return {'iterations': iterations, 'training_seconds': elapsed,
            'requested_seconds': seconds, 'overshoot_seconds': max(0, elapsed - seconds)}


def run(seconds=.2, seeds=(17,29,43)):
    # Keep core timer tests dependency-free; research runs require OpenSpiel.
    if isinstance(seconds, bool) or not isinstance(seconds, (int,float)) or not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('seconds must be finite and positive')
    seeds = tuple(seeds)
    if len(seeds) < 2 or len(set(seeds)) != len(seeds) or any(type(s) is not int or not 0 <= s < 2**31 for s in seeds):
        raise ValueError('Provide at least two distinct nonnegative 32-bit signed seeds')
    import pyspiel
    records = []
    names = ('cfr', 'cfr_plus', 'external_mccfr')
    for game_name in ('kuhn_poker', 'leduc_poker'):
        game = pyspiel.load_game(game_name)
        for repeat, seed in enumerate(seeds):
            # Rotate execution order to reduce always-first/always-last effects.
            order = names[repeat % 3:] + names[:repeat % 3]
            for position, name in enumerate(order):
                start = time.perf_counter()
                if name == 'cfr': solver = pyspiel.CFRSolver(game)
                elif name == 'cfr_plus': solver = pyspiel.CFRPlusSolver(game)
                else: solver = pyspiel.ExternalSamplingMCCFRSolver(game, seed)
                construction = time.perf_counter() - start
                step = solver.run_iteration if name == 'external_mccfr' else solver.evaluate_and_update_policy
                timing = train_for(step, seconds)
                start = time.perf_counter()
                metric = pyspiel.exploitability(game, solver.average_policy())
                evaluation = time.perf_counter() - start
                records.append({'game': game_name, 'algorithm': name, 'repeat': repeat,
                                'seed': seed if name == 'external_mccfr' else None,
                                'order_in_repeat': position, 'construction_seconds': construction,
                                'evaluation_seconds': evaluation, 'exploitability': metric, **timing})
    return {'environment': {'python': platform.python_version(), 'platform': platform.platform(),
                            'open_spiel': importlib.metadata.version('open_spiel')},
            'notes': ['Unofficial two-player zero-sum practice, not the unreleased event game.',
                      'Same requested UPDATE time; construction and evaluation reported separately.',
                      'Soft deadlines can overshoot by an update plus scheduling/timer overhead.',
                      'CFR variants are deterministic; repeats measure machine variation, not random seeds.',
                      'Lower exploitability is better in these games; no tournament or one-millisecond compliance claim.',
                      'Wall-clock iterations and metrics vary across runs, including with the same seed.'],
            'records': records}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seconds', type=float, default=.2)
    p.add_argument('--seeds', type=int, nargs='+', default=[17,29,43])
    a = p.parse_args()
    try: result = run(a.seconds, a.seeds)
    except ValueError as e: p.error(str(e))
    print(json.dumps(result, indent=2))
