"""Exact best responses to fixed strategy tables in unofficial Kuhn practice."""
from fractions import Fraction
from itertools import permutations, product

from pokerbot_lab import LEGAL, TOKEN, terminal_payoff


def baseline(jack_bet):
    """Probability of the second legal action (bet or call), by history and rank."""
    bet = (jack_bet, 0, 1)
    call = (0, Fraction(1, 2), 1)
    return {"": bet, "k": bet, "b": call, "kb": call}


def best_response_value(profile, seat):
    """Maximum responder chips per hand over legal pure plans for one seat."""
    if seat not in (0, 1):
        raise ValueError("seat must be 0 or 1")
    histories = [h for h in LEGAL if len(h) % 2 == seat]
    keys = list(product(histories, range(3)))

    def payoff(cards, history, plan):
        if history not in LEGAL:
            value = terminal_payoff(cards, history)
            return value if seat == 0 else -value
        actor = len(history) % 2
        actions = LEGAL[history]
        if actor == seat:
            action = actions[plan[history, cards[seat]]]
            return payoff(cards, history + TOKEN[action], plan)
        p = profile[history][cards[actor]]
        return sum(weight * payoff(cards, history + TOKEN[action], plan)
                   for action, weight in zip(actions, (1-p, p)))

    # A single plan applies to every deal. Maximizing per deal would reveal
    # the hidden card and overstate the value of a legal response.
    values = []
    for choices in product((0, 1), repeat=len(keys)):
        plan = dict(zip(keys, choices))
        total = sum(payoff(cards, "", plan) for cards in permutations(range(3), 2))
        values.append(Fraction(total, 6))
    return max(values)


if __name__ == "__main__":
    for name, bluff in (("mixed", Fraction(1, 3)), ("low_bluff", Fraction(1, 6))):
        profile = baseline(bluff)
        first, second = (best_response_value(profile, seat) for seat in (0, 1))
        print(f"{name}: opponent chips/hand first={first}, second={second}, "
              f"seat average={(first + second) / 2}")
