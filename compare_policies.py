"""Fixed-work, paired-seed comparisons in unofficial Kuhn poker only."""
import argparse
import json
import statistics
from pokerbot_lab import POLICIES, run_match


def compare(candidate, baseline, opponents, seeds, pairs=1000):
    opponents, seeds = tuple(opponents), tuple(seeds)
    if candidate not in POLICIES or baseline not in POLICIES:
        raise ValueError('Unknown candidate or baseline')
    if not opponents or len(set(opponents)) != len(opponents) or any(o not in POLICIES for o in opponents):
        raise ValueError('Choose distinct known opponents')
    if len(seeds) < 2 or any(isinstance(s, bool) or not isinstance(s, int) for s in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError('Use at least two distinct integer seeds')
    if isinstance(pairs, bool) or not isinstance(pairs, int) or pairs < 2:
        raise ValueError('Use at least two paired deals')
    rows = []
    for opponent in opponents:
        for seed in seeds:
            old = run_match(POLICIES[baseline], POLICIES[opponent], pairs, seed)
            new = run_match(POLICIES[candidate], POLICIES[opponent], pairs, seed)
            rows.append({'opponent': opponent, 'seed': seed, 'baseline': old,
                         'candidate': new, 'delta_chips_per_hand': new['chips_per_hand'] - old['chips_per_hand']})
    def summarize(values):
        return {'mean_delta_chips_per_hand': statistics.mean(values),
                'seed_block_standard_error': statistics.stdev(values) / len(values)**.5,
                'positive_blocks': sum(v > 0 for v in values), 'blocks': len(values)}
    per_opponent = {o: summarize([r['delta_chips_per_hand'] for r in rows if r['opponent'] == o]) for o in opponents}
    # Average opponents INSIDE each seed block; do not pretend shared-seed
    # opponents or the two seats constitute independent observations.
    blocks = [statistics.mean(r['delta_chips_per_hand'] for r in rows if r['seed'] == s) for s in seeds]
    return {'game': 'Unofficial Kuhn poker practice', 'candidate': candidate,
            'baseline': baseline, 'opponents': opponents, 'seeds': seeds,
            'pairs_per_match': pairs, 'total_hands': 4*pairs*len(opponents)*len(seeds),
            'per_opponent': per_opponent, 'equal_weight_pool': summarize(blocks),
            'notes': 'Fixed hand count, not equal wall-clock training. Shared deal seeds and seat swaps; action RNG streams can diverge. Standard error is descriptive, not a tournament-strength guarantee. Timings are local observations, not enforced deadlines.',
            'records': rows}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', choices=POLICIES, default='mixed')
    p.add_argument('--baseline', choices=POLICIES, default='cautious')
    p.add_argument('--opponents', nargs='+', choices=POLICIES, default=['cautious','calling','random'])
    p.add_argument('--seeds', nargs='+', type=int, default=[101,202,303,404,505])
    p.add_argument('--pairs', type=int, default=1000)
    a = p.parse_args()
    try:
        result = compare(a.candidate, a.baseline, a.opponents, a.seeds, a.pairs)
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(result, indent=2))
