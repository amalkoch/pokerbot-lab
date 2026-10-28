"""Educational poker math in simulated chips/points; no external dependencies."""
from functools import lru_cache
from math import comb, isfinite


def _number(value, name, minimum=0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a finite number')
    if not isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f'{name} is outside its allowed range')
    return float(value)


def pot_odds(pot, call):
    """Break-even equity: call/(pot+call). Pot INCLUDES the opponent's bet."""
    pot, call = _number(pot, 'pot'), _number(call, 'call')
    if pot + call == 0:
        raise ValueError('No pot or call to evaluate')
    return call / (pot + call)


def call_ev(pot, call, equity):
    """Net chip EV relative to folding; no future betting, rake, or side pots.

    Equity is expected fraction of the final pot, including ties.
    """
    pot, call = _number(pot, 'pot'), _number(call, 'call')
    equity = _number(equity, 'equity', maximum=1)
    return equity * (pot + call) - call


def bluff_ev(pot, bet, fold_probability):
    """Pure bluff: win existing pot if opponent folds; lose bet if called.

    Assumes zero showdown equity, one opponent, and no later betting.
    """
    pot, bet = _number(pot, 'pot'), _number(bet, 'bet')
    fold_probability = _number(fold_probability, 'fold_probability', maximum=1)
    return fold_probability * pot - (1 - fold_probability) * bet


def hit_probability(outs, unseen, draws):
    """At least one out in uniform draws WITHOUT replacement.

    Fixed outs, no changing board effects; hitting an out need not win the hand.
    """
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (outs, unseen, draws)):
        raise ValueError('Card counts must be integers')
    if not 0 <= outs <= unseen or not 0 <= draws <= unseen:
        raise ValueError('Require 0 <= outs, draws <= unseen')
    misses = comb(unseen - outs, draws) if draws <= unseen - outs else 0
    return 1 - misses / comb(unseen, draws)


def weighted_score(scores):
    """Six-round No Limit weighted TOTAL, not a weighted average."""
    scores = tuple(scores)
    if len(scores) != 6:
        raise ValueError('Provide exactly six round scores')
    return sum(i * _number(score, 'score') for i, score in enumerate(scores, 1))


def icm_equities(stacks, payouts):
    """Exact finite-state ICM in floating point, for 1..10 surviving players.

    Model: next finisher is selected proportional to remaining chips, then
    removed. Returns expected payout per player. Missing payouts are zero.
    Payout units may be tournament points. All surviving stacks must be positive;
    remove eliminated players and their already-awarded places before calling.
    Equal skill is assumed; position, blinds and strategy are not modeled.
    This offline study calculator is not a one-millisecond runtime guarantee.
    """
    stacks, payouts = tuple(stacks), tuple(payouts)
    n = len(stacks)
    if not 1 <= n <= 10:
        raise ValueError('Use 1 to 10 surviving players')
    stacks = tuple(_number(x, 'stack') for x in stacks)
    if any(x == 0 for x in stacks):
        raise ValueError('Surviving stacks must be positive')
    if not 1 <= len(payouts) <= n:
        raise ValueError('Provide 1 to n payouts')
    payouts = tuple(_number(x, 'payout') for x in payouts)
    if any(a < b for a, b in zip(payouts, payouts[1:])):
        raise ValueError('Payouts must be nonincreasing')
    payouts += (0.0,) * (n - len(payouts))
    # Normalize to avoid overflow when summing large finite stacks.
    scale = max(stacks)
    stacks = tuple(x / scale for x in stacks)
    if any(x == 0 for x in stacks):
        raise ValueError('Stack ratio is too extreme for floating point')

    @lru_cache(None)
    def solve(remaining):
        if not remaining:
            return (0.0,) * n
        rank = n - len(remaining)
        total = sum(stacks[i] for i in remaining)
        result = [0.0] * n
        for winner in remaining:
            probability = stacks[winner] / total
            result[winner] += probability * payouts[rank]
            tail = solve(tuple(i for i in remaining if i != winner))
            for i in remaining:
                result[i] += probability * tail[i]
        return tuple(result)

    return solve(tuple(range(n)))


if __name__ == '__main__':
    print('SIMULATED-CHIP / POINT EXAMPLES')
    print(f'Call 20 into pot 80: break-even equity = {pot_odds(80, 20):.1%}')
    print(f'At 30% equity, call EV = {call_ev(80, 20, .30):+.2f} chips')
    print(f'Bluff 50 into 100, opponent folds 40%: EV = {bluff_ev(100, 50, .40):+.2f} chips')
    print(f'9 fixed outs, 47 unseen cards, 2 draws: hit probability = {hit_probability(9, 47, 2):.2%}')
    print('ICM: stacks [50,30,20], points [50,30,20] ->',
          [round(x, 4) for x in icm_equities([50, 30, 20], [50, 30, 20])])
    print('Six scores [1,2,3,4,5,6], weighted total =', weighted_score([1, 2, 3, 4, 5, 6]))
