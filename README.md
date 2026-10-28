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

## Competition context

The [official No Limit rules](https://pokerbot.sequoiacap.com/rules.html), checked October 28, 2026, describe a Python Agent interface supplied at the event, a 60-minute initial build phase, offline execution, and a one-millisecond decision limit. The poker variant is revealed on event day. The starter kit includes a simulator and ICM calculator. Six scored rounds have increasing weights.

This repository is preparation material, not an official starter kit or a ready-to-submit bot. Do not assume prewritten code can be brought into the competition; confirm that with the organizer. No unreleased event details belong here. No money is wagered in this lab.

Timing reports measure policy calls on the current machine; they do not enforce timeouts, isolate processes, or establish compliance on organizer hardware. The practice engine uses net chips, not the event's finishing-position/ICM scoring.

## Next increments

- Add a benchmark matrix with held-out seeds and saved results.
- Study tournament point scoring and ICM separately from chip profit.
- Add more practice opponents and constrained, legal-action adapters.
- Run a timed 60-minute build drill; adapt to the official interface only when released.
