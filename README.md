# Pokerbot Lab

An unofficial, offline practice arena for learning to build, test, and improve poker agents under time pressure. Built for Arzu Malkoch's competition preparation.

## Run it

Python 3.9+; no packages, API keys, or network calls needed.

```sh
python3 -m pokerbot_lab --agent mixed --opponent cautious --pairs 5000 --seed 42
python3 -m unittest -v
```

Choose `mixed`, `cautious`, `calling`, or `random`. Results report net chips per hand, an approximate 95% confidence interval half-width, invalid/failed actions, and local decision timing. Each deal is played with the agents in both seats. Random seeds reproduce scores, not execution times.

## The practice game

This is two-player **Kuhn poker**, not a model of the competition's unreleased game. A three-card deck contains Jack, Queen, and King. Each player antes one chip and privately receives one card. Players may check or bet one chip; facing a bet they may call or fold. One betting round ends in a fold or showdown. The higher card wins. A checked showdown transfers one net chip; a called bet transfers two.

Agents receive only their card, seat, public history, and legal actions. Public history uses `k` for check, `b` for bet, `c` for call, and `f` for fold. Exceptions and illegal actions fall back to checking when possible, otherwise folding.

The hand-written policies are teaching baselines, not optimal strategies. Winning against one weak opponent is not evidence of tournament strength. Confidence intervals summarize sampled paired deals; they do not account for every source of uncertainty or adaptively changing opponents.

## First exercise

1. Run `mixed` against all three other policies using the same seed.
2. Explain why bluffing behaves differently against an opponent who always calls.
3. Change one probability in a new policy, rerun against the entire opponent set, and keep a separate seed for evaluation.
4. Record both favorable and unfavorable results before deciding whether the change helped.

## Poker math exercises

Run `python3 poker_math.py` for worked examples. Import the functions from `poker_math` to try your own simulated-chip scenarios.

| Function | What it calculates | Example |
| --- | --- | --- |
| `pot_odds(pot, call)` | Break-even equity | Call 20 into an existing pot of 80: 20% |
| `call_ev(pot, call, equity)` | Expected net chip gain relative to folding | 30% equity in that spot: +10 chips |
| `bluff_ev(pot, bet, fold_probability)` | Zero-showdown-equity bluff EV | Bet 50 into 100 with 40% folds: +10 chips |
| `hit_probability(outs, unseen, draws)` | Chance to hit at least one fixed out | 9 outs, 47 unseen, 2 draws: 34.97% |
| `icm_equities(stacks, payouts)` | Expected tournament points under ICM | Stacks 50/30/20, points 50/30/20: 38.3929/32.75/28.8571 |
| `weighted_score(scores)` | Six-round weighted total | Scores 1/2/3/4/5/6: 91 |

### Derive the decisions

Let P be the pot **including the opponent's bet**, C the amount to call, and e your expected share of the final pot. With no further betting, rake, or side pots:

- Call EV = e(P + C) − C. Setting EV to zero gives break-even equity C/(P + C).
- A pure bluff of B into P, with fold probability f, has EV = fP − (1 − f)B. It breaks even at f = B/(P + B). This assumes one opponent and zero equity when called.
- With O fixed outs, U unseen cards and D uniform draws without replacement, P(hit) = 1 − choose(U − O, D)/choose(U, D). Hitting an out is not necessarily winning the hand.
- Six-round score = Σ r × score[r], for r = 1…6. This is a total; divide by 21 only if you explicitly want the weighted average. See the official rules linked below for the event scoring context.

### Why chip gain and tournament points differ

The ICM model selects the next finishing player with probability proportional to their remaining stack, removes them, and repeats. Expected points sum each finishing probability times its payout. The implementation caches remaining-player subsets and evaluates the finite model directly in floating point; it does not use Monte Carlo sampling.

Use 1–10 positive surviving stacks and nonincreasing payouts. Missing lower payouts become zero. Remove eliminated players and their already-awarded places first. Equal stacks have equal equity; multiplying every stack by the same amount leaves equity unchanged; total equities conserve the remaining payout pool. The tests check these properties and compare against an independent four-player permutation calculation.

ICM ignores skill differences, positions, blinds, and future strategic interactions. This is an offline study calculator, not an assertion that the computation fits the event's one-millisecond limit. Background: [Gilbert, The Independent Chip Model and Risk Aversion](https://arxiv.org/abs/0911.3100) and [PokerStars' ICM introduction](https://www.pokerstars.com/poker/learn/lesson/icm-and-its-impact-on-tournaments/).

## Competition context

The [official No Limit rules](https://pokerbot.sequoiacap.com/rules.html), checked October 28, 2026, describe a Python Agent interface supplied at the event, a 60-minute initial build phase, offline execution, and a one-millisecond decision limit. The poker variant is revealed on event day. The starter kit includes a simulator and ICM calculator. Six scored rounds have increasing weights.

This repository is preparation material, not an official starter kit or a ready-to-submit bot. Do not assume prewritten code can be brought into the competition; confirm that with the organizer. No unreleased event details belong here. No money is wagered in this lab.

Timing reports measure policy calls on the current machine; they do not enforce timeouts, isolate processes, or establish compliance on organizer hardware. The practice engine uses net chips, not the event's finishing-position/ICM scoring.

## Trained preflop baselines

[First model results](PREFLOP_RESULTS.md): logistic regression, decision tree and boosted trees trained on cleaned PokerBench data with public-history group splits. Includes accuracy, action coverage and single-hand latency; this is not a tournament-ready policy.

## Datasets for algorithm experiments

See [DATASETS.md](DATASETS.md) for a ranked source review, a full PokerBench CSV audit, and a replay-validated Pluribus sample. The audit identifies future-card leakage and train/test overlap before model fitting.

## Research benchmark

See [RESEARCH.md](RESEARCH.md) for library and algorithm comparisons, reproducible training commands, 100,000 simulated hands, and validation against all 1,025,010 UCI hand labels. OpenSpiel and PokerKit are optional research dependencies.

## Next increments

- Compare solvers at equal wall-clock budgets across multiple seeds.
- Extend the math exercises with tournament risk scenarios and explanations.
- Add more practice opponents and constrained, legal-action adapters.
- Run a timed 60-minute build drill; adapt to the official interface only when released.
