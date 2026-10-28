"""Two-player Kuhn poker: three cards, one betting round, unit ante/bet.

This intentionally small practice game is NOT the No Limit competition variant.
Players see only their own card and public actions. Net payoffs are zero-sum.
"""
from dataclasses import dataclass
from itertools import permutations
import random
from time import perf_counter_ns
from typing import Callable, Tuple

LEGAL = {
    "": ("check", "bet"),
    "k": ("check", "bet"),
    "b": ("fold", "call"),
    "kb": ("fold", "call"),
}
TOKEN = {"check": "k", "bet": "b", "call": "c", "fold": "f"}


@dataclass(frozen=True)
class Observation:
    card: int  # 0=Jack, 1=Queen, 2=King
    history: str
    seat: int
    legal_actions: Tuple[str, ...]


Policy = Callable[[Observation, random.Random], str]


def cautious(obs: Observation, rng: random.Random) -> str:
    """Value-bet and call with kings; otherwise check or fold."""
    if obs.card == 2:
        return "call" if "call" in obs.legal_actions else "bet"
    return "check" if "check" in obs.legal_actions else "fold"


def calling_station(obs: Observation, rng: random.Random) -> str:
    return "call" if "call" in obs.legal_actions else "check"


def random_policy(obs: Observation, rng: random.Random) -> str:
    return rng.choice(obs.legal_actions)


def mixed(obs: Observation, rng: random.Random) -> str:
    """A hand-written bluffing baseline, not a solved or proven strategy."""
    if "call" in obs.legal_actions:
        return "call" if obs.card == 2 or (obs.card == 1 and rng.random() < 0.5) else "fold"
    if obs.card == 2 or (obs.card == 0 and rng.random() < 1 / 3):
        return "bet"
    return "check"


POLICIES = {"cautious": cautious, "calling": calling_station,
            "random": random_policy, "mixed": mixed}


def terminal_payoff(cards: Tuple[int, int], history: str) -> int:
    """Net chips for seat zero, including the ante; not gross pot winnings."""
    if history == "bf":
        return 1
    if history == "kbf":
        return -1
    if history not in ("kk", "bc", "kbc"):
        raise ValueError("Not a terminal history")
    stake = 1 if history == "kk" else 2
    return stake if cards[0] > cards[1] else -stake


def play_hand(cards, policies, rngs, timings=None, failures=None):
    if len(cards) != 2 or len(set(cards)) != 2 or any(c not in (0, 1, 2) for c in cards):
        raise ValueError("Deal two distinct cards from 0, 1, 2")
    history = ""
    while history in LEGAL:
        seat = len(history) % 2
        obs = Observation(cards[seat], history, seat, LEGAL[history])
        started = perf_counter_ns()
        try:
            action = policies[seat](obs, rngs[seat])
        except Exception:
            action = None
        elapsed = perf_counter_ns() - started
        if timings is not None:
            timings[seat].append(elapsed)
        if action not in obs.legal_actions:
            if failures is not None:
                failures[seat] += 1
            action = "check" if "check" in obs.legal_actions else "fold"
        history += TOKEN[action]
    payoff = terminal_payoff(cards, history)
    return payoff, -payoff


def run_match(first: Policy, second: Policy, pairs=5000, seed=42):
    """Swap seats on each deal. Report one sample per paired deal.

    Timing is observational: this harness does not interrupt slow policies.
    Decision samples exclude engine work and are not competition benchmarks.
    """
    if pairs < 2:
        raise ValueError("At least two paired deals are required")
    dealer = random.Random(seed)
    policy_rngs = (random.Random(seed + 1), random.Random(seed + 2))
    timings = [[], []]
    failures = [0, 0]
    paired = []
    deals = tuple(permutations(range(3), 2))
    for _ in range(pairs):
        cards = dealer.choice(deals)
        p1 = play_hand(cards, (first, second), policy_rngs, timings, failures)[0]
        reverse_timings = [[], []]
        reverse_failures = [0, 0]
        p2 = play_hand(cards, (second, first), policy_rngs[::-1],
                       reverse_timings, reverse_failures)[1]
        timings[0].extend(reverse_timings[1])
        timings[1].extend(reverse_timings[0])
        failures[0] += reverse_failures[1]
        failures[1] += reverse_failures[0]
        paired.append((p1 + p2) / 2)
    mean = sum(paired) / pairs
    variance = sum((x - mean) ** 2 for x in paired) / (pairs - 1)
    summaries = []
    for samples in timings:
        values = sorted(samples)
        summaries.append({
            "decisions": len(values),
            "median_us": values[len(values) // 2] / 1000,
            "p99_us": values[min(len(values) - 1, (99 * len(values) + 99) // 100 - 1)] / 1000,
            "max_us": max(values) / 1000,
            "over_1ms": sum(x > 1_000_000 for x in values),
        })
    return {"hands": 2 * pairs, "seed": seed, "chips_per_hand": mean,
            "approx_95pct_half_width": 1.96 * (variance / pairs) ** 0.5,
            "invalid_or_failed_actions": failures, "timing": summaries}


import argparse
import json


def main():
    parser = argparse.ArgumentParser(description="Unofficial Kuhn poker practice arena")
    parser.add_argument("--agent", choices=POLICIES, default="mixed")
    parser.add_argument("--opponent", choices=POLICIES, default="cautious")
    parser.add_argument("--pairs", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.pairs < 2:
        parser.error("--pairs must be at least 2")
    result = run_match(POLICIES[args.agent], POLICIES[args.opponent], args.pairs, args.seed)
    print(json.dumps({"game": "Kuhn poker (practice only)", "agent": args.agent,
                      "opponent": args.opponent, **result}, indent=2))


if __name__ == "__main__":
    main()
