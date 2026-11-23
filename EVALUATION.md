# Reproduce the Kuhn policy evaluation

This walkthrough evaluates the public, unofficial two-player Kuhn practice
policies using simulated chips. Run the commands from the repository root
with Python 3.9 or newer. The commands below use the standard library.

## Check the implementation

Run the tests before interpreting a strategy comparison.

```sh
python3 -m unittest -q
```

A minimal installation skips nine optional research tests. The remaining
tests cover the practice engine, math, exact evaluator and policy/table
agreement. Investigate any failure before continuing.

## Reproduce the fixed opponent comparison

```sh
python3 compare_policies.py --candidate low_bluff --baseline mixed --opponents cautious calling random --seeds 1101 1102 1103 1104 1105 --pairs 2000
```

This command plays 120,000 hands across two versions, three opponents, five
seeds and both seats. In each record, check both versions'
`invalid_or_failed_actions` arrays. Every count should be zero.

Read `per_opponent` before `equal_weight_pool`. The reported delta is
candidate minus baseline in net chips per hand.

| Opponent | Expected mean delta |
| --- | ---: |
| cautious | -0.04425 |
| calling | +0.05950 |
| random | -0.02580 |

The pool mean is approximately -0.00351667 with a descriptive seed-block
standard error of 0.00218445. The reduced-bluff candidate gains against the
calling policy and loses against the other two policies. The recorded
promotion rule rejects it.

These seeds reproduce an existing experiment and have already been inspected.
Choose fresh evaluation seeds before tuning a new candidate. Scores reproduce
for the same implementation and random streams. Local timing measurements
vary with machine load.

## Evaluate an optimal response to each fixed table

```sh
python3 kuhn_response.py
```

Expected output:

```text
mixed: opponent chips/hand first=-1/36, second=1/9, seat average=1/24
low_bluff: opponent chips/hand first=1/36, second=5/36, seat average=1/12
```

Here the sign describes the responding opponent's gain. Positive means the
evaluated strategy loses that many chips on average. Average the two seats
to remove the positional advantage. Each seat's response maximizes expected
payoff across all deals while observing only its own card and public history.

The opponent's equal-seat expected gain doubles when jack bluffs fall from
1/3 to 1/6. This explains why a gain against the calling baseline is insufficient
to establish robustness against a wider range of opponents.

## Keep enough evidence to reproduce a decision

Record the code revision with `git rev-parse HEAD`, the command, all
opponent deltas, action failure counts and your keep/reject decision. Keep
timing observations with their machine and runtime context. Apply these
results to the specified Kuhn model and fixed policies.

Verified on November 23, 2026 with 120,000 hands, zero action failures and the
exact values above. The minimal-environment suite ran 62 tests with nine
optional research skips.
