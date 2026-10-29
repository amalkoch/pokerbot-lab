"""Unofficial offline ICM exercise: equal-stakes, no-tie chip gambles.

This is not a poker action adapter or an event submission. There is no dead pot,
no sunk bet, no side pot, and no future action in the modeled binary gamble.
"""
from poker_math import _number, icm_equities


def compare_gamble(stacks, payouts, hero, opponent, risk, win_probability):
    """Compare keeping current stacks with an equal-size chip transfer.

    Win: opponent transfers risk to hero. Lose: hero transfers risk to opponent.
    At most one player busts per outcome; that player earns the last remaining
    payout, and survivors divide the higher payouts using ICM. Payout units are
    arbitrary simulated tournament points, not the unreleased event payouts.
    """
    stacks, payouts = tuple(stacks), tuple(payouts)
    before = icm_equities(stacks, payouts)  # Validate and price the baseline.
    n = len(stacks)
    if any(isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < n
           for i in (hero, opponent)) or hero == opponent:
        raise ValueError('Choose distinct valid hero and opponent indices')
    risk = _number(risk, 'risk', maximum=min(stacks[hero], stacks[opponent]))
    if risk == 0:
        raise ValueError('risk must be positive')
    probability = _number(win_probability, 'win_probability', maximum=1)
    payouts += (0.0,) * (n - len(payouts))

    def outcome(winner, loser):
        after = list(stacks)
        after[winner] += risk
        after[loser] -= risk
        if after[loser] > 0:
            return icm_equities(after, payouts)[hero]
        if loser == hero:
            return float(payouts[-1])
        survivors = [i for i in range(n) if after[i] > 0]
        return icm_equities([after[i] for i in survivors], payouts[:-1])[survivors.index(hero)]

    win = outcome(hero, opponent)
    lose = outcome(opponent, hero)
    baseline = before[hero]
    # Equal payouts make every outcome identical: no unique break-even value.
    threshold = None if win == lose else (baseline - lose) / (win - lose)
    return {'baseline_points': baseline, 'win_points': win, 'lose_points': lose,
            'expected_points': probability * win + (1 - probability) * lose,
            'point_ev': probability * win + (1 - probability) * lose - baseline,
            'chip_ev': risk * (2 * probability - 1), 'chip_break_even': .5,
            'point_break_even': threshold,
            'risk_premium': None if threshold is None else threshold - .5}


if __name__ == '__main__':
    import json
    print(json.dumps(compare_gamble([40, 40, 20], [50, 30, 20],
                                   hero=0, opponent=1, risk=40,
                                   win_probability=.55), indent=2))
