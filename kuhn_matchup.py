"""Exact fixed-policy matchups in unofficial two-player Kuhn practice."""
from fractions import Fraction
from itertools import permutations

from kuhn_response import baseline, validated_profile
from pokerbot_lab import LEGAL, TOKEN, terminal_payoff


def expected_payoff(first, second):
    """Expected net chips for seat zero over six uniform deals."""
    profiles = (validated_profile(first), validated_profile(second))

    def visit(cards, history):
        if history not in LEGAL:
            return terminal_payoff(cards, history)
        seat = len(history) % 2
        probability = profiles[seat][history][cards[seat]]
        return sum(weight * visit(cards, history + TOKEN[action])
                   for action, weight in zip(LEGAL[history],
                                             (1 - probability, probability)))

    return sum(visit(cards, '') for cards in permutations(range(3), 2)) / 6


def seat_average(candidate, opponent):
    """Candidate's expected chips per hand with equal weight on each seat."""
    return (expected_payoff(candidate, opponent)
            - expected_payoff(opponent, candidate)) / 2


def opponent_profiles():
    return {
        'cautious': dict.fromkeys(LEGAL, (0, 0, 1)),
        'calling': {'': (0, 0, 0), 'k': (0, 0, 0),
                    'b': (1, 1, 1), 'kb': (1, 1, 1)},
        'random': dict.fromkeys(LEGAL, (Fraction(1, 2),) * 3),
    }


if __name__ == '__main__':
    mixed = baseline(Fraction(1, 3))
    low = baseline(Fraction(1, 6))
    deltas = []
    for name, opponent in opponent_profiles().items():
        delta = seat_average(low, opponent) - seat_average(mixed, opponent)
        deltas.append(delta)
        print(f'{name}: low_bluff minus mixed = {delta} ({float(delta):.8f})')
    print(f'Equal-weight pool: {sum(deltas) / len(deltas)}')
