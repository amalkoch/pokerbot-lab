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

## Reproducible policy comparisons

```sh
python3 compare_policies.py --candidate mixed --baseline cautious --opponents cautious calling random --seeds 101 202 303 404 505 --pairs 1000
```

This unofficial Kuhn experiment evaluates both versions against each opponent
with the same deal seeds and both seats. Each version receives the same number
of hands (fixed work, **not** equal wall-clock training). Decisions and local
latency are recorded separately. Policy random-number streams can diverge when
actions differ, so identical seeds do not imply identical subsequent choices.
Use stateless policies with the supplied RNG; global mutable state is not reset.

[Recorded example](policy_comparison_example.json): 60,000 hands, five seeds,
three opponents, zero invalid/failed actions. Mixed minus cautious, in net chips
per hand: **−0.0068** versus cautious, **−0.1069** versus calling, **+0.1025**
versus random. The equal-weight opponent-pool mean is **−0.00373**, with a
seed-block standard error of **0.00362**. These are illustrative baseline
comparisons, not evidence of a stronger tournament bot.

What to learn: a gain against one opponent may hide a loss against another.
Average opponents within each seed first; seat swaps and shared-seed opponents
are not independent samples. Five seed blocks give only a descriptive uncertainty
estimate. Choose evaluation seeds before comparing versions, keep fresh seeds
for any policy tuning, and retain unfavorable results. Timings are observations
on this local machine, not enforced deadlines or organizer-runtime compliance.

## Equal requested training-time experiment

With the optional research dependencies installed, run:

```sh
.venv/bin/python timed_training.py --seconds 0.2 --seeds 17 29 43
```

CFR, CFR+ and external-sampling MCCFR each receive the same requested **update
loop** time on unofficial Kuhn and Leduc games. Construction and final exact
exploitability evaluation are timed separately. Execution order rotates across
three repeats. CFR variants are deterministic; only MCCFR uses the supplied
random seeds. A deadline is checked between atomic solver updates, so the last
update can overshoot; the tool reports actual elapsed time and overshoot.
It does not interrupt work or enforce a one-millisecond gameplay deadline.

[Recorded local example](timed_training_example.json), median exploitability
(lower is better), three runs per cell:

| Practice game | CFR | CFR+ | External MCCFR |
| --- | ---: | ---: | ---: |
| Kuhn | 0.00010745 | 0.00000974 | 0.00365477 |
| Leduc | 0.25333873 | 0.07159431 | 0.28973930 |

The largest measured budget overshoot was **5.36 ms**. All 18 runs retain
iteration counts, setup/evaluation timings, environment metadata and results.
This is a short local benchmark, not a universal algorithm ranking. Repeat with
larger budgets and multiple runs; machine load changes the number of updates
and therefore the final policies even with identical random seeds. Do not
compare exploitability magnitudes across different games as if units matched.

What to learn: more solver iterations need not mean a stronger strategy.
Compare quality under a stated resource budget, and count setup and evaluation
costs when planning a full build session. This uses public OpenSpiel practice
games, not the event's unreleased variant or interface; importing prewritten
code at the event still requires organizer confirmation.

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

## Tournament risk exercise

Run `python3 tournament_risk.py` to compare a binary, equal-stakes chip gamble
with keeping the current stacks. This is an **unofficial offline exercise**:
no dead pot, sunk bets, ties, side pots or future betting are modeled. It is not
a call/fold recommendation for an arbitrary poker hand.

Example: stacks `[40, 40, 20]`, hypothetical point payouts `[50, 30, 20]`,
hero and opponent each risk 40, hero wins 55% of the time. Chip EV is **+4**,
but ICM point EV is **−1.3667**. The point break-even win probability is
**60.2564%**, versus 50% for chips. The calculator awards the last remaining
payout when a player busts and uses ICM for the surviving players.

What to learn: the score objective changes the decision. Try winner-take-all
payouts `[100]` (chip and point break-even coincide), then equal payouts
`[10, 10, 10]` (no unique break-even probability). These are invented payout
schedules, not the event's unreleased structure. See the reproducible output in
[tournament_risk_example.json](tournament_risk_example.json).

## Competition context

The [official No Limit rules](https://pokerbot.sequoiacap.com/rules.html), checked October 31, 2026, describe a Python Agent interface supplied at the event, a 60-minute initial build phase, offline execution, and a one-millisecond decision limit. The poker variant is revealed on event day. The starter kit includes a simulator and ICM calculator. Six scored rounds have increasing weights.

This repository is preparation material, not an official starter kit or a ready-to-submit bot. Do not assume prewritten code can be brought into the competition; confirm that with the organizer. No unreleased event details belong here. No money is wagered in this lab.

Timing reports measure policy calls on the current machine; they do not enforce timeouts, isolate processes, or establish compliance on organizer hardware. The practice engine uses net chips, not the event's finishing-position/ICM scoring.

## Trained preflop baselines

[First model results](PREFLOP_RESULTS.md): logistic regression, decision tree and boosted trees trained on cleaned PokerBench data with public-history group splits. Includes accuracy, action coverage and single-hand latency; this is not a tournament-ready policy.

## Datasets for algorithm experiments

See [DATASETS.md](DATASETS.md) for a ranked source review, a full PokerBench CSV audit, and a replay-validated Pluribus sample. The audit identifies future-card leakage and train/test overlap before model fitting.

## Research benchmark

See [RESEARCH.md](RESEARCH.md) for library and algorithm comparisons, reproducible training commands, 100,000 simulated hands, and validation against all 1,025,010 UCI hand labels. OpenSpiel and PokerKit are optional research dependencies.

## Next increments

- Repeat timed solver comparisons at larger budgets and evaluate exported policies against practice opponents.
- Extend the binary risk exercise with explicitly modeled ties and sunk-pot states.
- Add more practice opponents and constrained, legal-action adapters.
- Run a timed 60-minute build drill; adapt to the official interface only when released.
