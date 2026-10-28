# Datasets for poker algorithm experiments

Research and local file audit: October 28, 2026. Recommendation: start with **PokerBench for supervised decision models**, **Pluribus/PHH for sequential replay and opponent modelling**, and **generated self-play for CFR/MCCFR and actual policy evaluation**. These serve different experiments. No reviewed source establishes a match to the unreleased competition variant or its eight-player tournament objective.

## Ranked sources

| Source | Contents and access | Best experiment | Main limitation |
| --- | --- | --- | --- |
| [PokerBench](https://huggingface.co/datasets/RZ412/PokerBench) | Structured CSV and prompt JSON; downloaded all four CSVs, about 91.5 MB | Decision trees, boosted trees, small neural policies, solver-action imitation | Single decision labels; leakage and overlap issues described below |
| [PHH: Pluribus](https://github.com/uoftcprg/phh-dataset/tree/main/data/pluribus) | 10,000 published six-player hands; replayed one 71-hand session locally | Behaviour cloning, opponent action prediction, trajectory reconstruction | Small expert pool; logged choices are not action-value labels |
| [PHH: ACPC archive](https://zenodo.org/records/17136841) | 341,172,750 fixed-limit and 278,842,225 no-limit records, explicitly including duplicates; full combined archive 20.3 GB | Large-scale bot behaviour and value-model experiments | Primarily heads-up, plus three-player fixed-limit; deduplication essential |
| [PHH: HandHQ](https://github.com/uoftcprg/phh-dataset/tree/main/data/handhq) | 21,605,687 anonymized hands from six online networks, July 2009 | Human opponent modelling and action-frequency calibration | Old cash-game population; incomplete private-card observations need measurement |
| [IRC Poker Database](https://poker.cs.ualberta.ca/irc_poker_database.html) | University of Alberta describes over 10 million hands from 1995–2001; links to an archive | Historical behavioural modelling | Old play-money population and legacy format; archive not locally audited |
| [UCI Poker Hand](https://archive.ics.uci.edu/dataset/158/poker%2Bhand) | 1,025,010 five-card examples; previously validated locally | Hand-ranker correctness | No bets, trajectories or strategy labels |

PHH is a common format, not a single homogeneous population. Do not pool its sources without source labels. Its repository also has 83 televised mixed-game WSOP hands: useful parser fixtures, far too small for a primary training corpus. The repository declares MIT; the full Zenodo archive declares CC BY 4.0. Preserve source attribution and asset provenance. We commit code, manifests and aggregate audits rather than rehosting downloaded histories. [PHH source inventory](https://github.com/uoftcprg/phh-dataset), [versioned archive](https://zenodo.org/records/17136841).

## PokerBench: best immediate supervised-learning candidate, after cleaning

The authors provide six-max no-limit Hold'em scenarios with solver-derived targets. Their construction selects dominant actions and balances evaluation action categories; the CSV label is not a full mixed strategy or per-action EV vector. Consequently, label accuracy alone cannot establish equilibrium quality or tournament strength. See the [paper](https://arxiv.org/abs/2501.08328).

Local audit, pinned Hugging Face revision `7ac61f961c81a50fc0f667820b2fb0e432dfec0d`:

| Check | Preflop train | Preflop test | Postflop train | Postflop test |
| --- | ---: | ---: | ---: | ---: |
| Actual rows | 63,200 | 1,000 | 500,000 | 10,000 |
| Repeated visible-observation rows beyond first | 101 | 0 | 6,187 | 2 |
| Observation groups with multiple distinct labels | 101 | 0 | 0 | 0 |
| Rows containing future board columns | 0 | 0 | 239,581 | 4,732 |
| Test rows matching a training observation | — | 10 | — | 227 |

These are our measurements, not claims copied from the dataset card. The file named `preflop_60k...` actually has 63,200 rows. The declared dataset license is Apache-2.0. [Machine-readable audit](results/pokerbench_audit.json) records file sizes, SHA-256 digests, label counts and street counts.

**Important input rule:** at a flop decision, drop `board_turn` and `board_river`; at a turn decision, drop `board_river`. Those fields are populated even before those cards are dealt. Also exclude the target and CSV row index. The audit's `observation()` function implements this column filtering; it is not a complete game-state validator. The audit found no repeated visible cards or targets outside the listed action menu under its checks.

The overlap test hashes exact visible fields without the label/index/future columns. It does **not** canonicalize suits, normalize all semantically equivalent histories or group related solver trees. Thus 237 overlapping test rows is a minimum finding under this identity definition, not a full leakage estimate. Conflicting preflop labels require investigation; they might reflect mixed actions or missing context, not necessarily bad records.

Recommended experiment protocol:

1. Preserve the published split for comparability, but report its overlap explicitly. Create a second stricter evaluation split grouped by originating public action line and board family; canonicalize equivalent card suits before splitting. Do not randomly split individual rows from related scenarios.
2. Deduplicate training observations. Quarantine the 101 conflicting groups for a first hard-label classifier. Do not silently choose whichever label was loaded last.
3. Keep test data out of tuning. Removing exact train overlap leaves 990 preflop test rows and 9,773 postflop test rows before test deduplication; further grouped filtering may shrink this substantially.
4. Fit a majority-label baseline, logistic regression and a shallow decision tree before a boosted-tree or small neural model. Encode hole-card ranks/suitedness, visible board texture, position, action history, pot and legal choices. Preflop amounts such as `13.0bb` are raise-to choices, not ordinary text classes to conflate with calls.
5. Report exact action-and-size match, action-family accuracy, macro-F1, illegal-choice rate and results by street. Test latency including feature construction. Evaluate any deployed policy in fresh games against varied opponents.

Steps 1–5 are a proposed training protocol. This research turn audited data; it did not fit those models or produce a cleaned training export.

## Pluribus: the best next trajectory source

We pinned PHH revision `e47fbd5816372360bade4de5d712346fe1bb70f6` and fetched every hand in session `data/pluribus/100`:

- **71/71 hands** replayed to terminal states with PokerKit.
- Reconstructed finishing stacks matched each recorded result; total chips were conserved.
- Downloads matched their pinned Git blob hashes; SHA-256 digests are in the [audit](results/pluribus_audit.json).
- This is one fixed session, not a random or representative sample of all 10,000 hands.

The histories expose private cards, including opponents' cards. An actor observation must contain only its own cards, currently revealed board, public actions, stacks and legal choices. Never feed the entire replay state directly to a policy. PokerKit provides the [PHH replay interface](https://pokerkit.readthedocs.io/en/stable/notation.html).

For an opponent model, predict fold/call/raise and conditional raise-size buckets from preceding visible actions. Split by session and player, not individual action. Use only earlier hands for running player statistics. Report log loss, calibration and held-out-player performance. For imitation, identify whose actions are being copied; do not label every human action as a Pluribus action. A recorded outcome is one stochastic result, not the value of every available decision.

## What the larger archives can and cannot do

ACPC is attractive after the pipeline works, but duplicate deal/seat-swap/expected-utility records must stay in the same split. Match game rules and betting units before mixing years. For HandHQ, first sample each site and measure unknown hole cards, parse failures, rake, player counts and stack distributions. Showdown-only training conditions on players reaching showdown and produces selection bias. Neither large archive was downloaded in this run.

Other candidates reviewed: [heads-up behavioural simulation data](https://zenodo.org/records/14840332) is generated under parameterized risk/bluffing assumptions; not an expert-action oracle. [PokerGPT's repository](https://github.com/hch1017/TH_LLM) is a research lead, but its inspected README does not provide a clear enough dataset card/license/split specification to prefer over the audited sources. Card-image datasets and UCI mirrors do not answer our betting-strategy question.

**Static logs cannot replace a simulator:** if our algorithm changes an action, the recorded opponent continuation may no longer be legal or representative. Historical logs also generally lack behaviour-policy probabilities needed for simple importance-weighted off-policy evaluation. Use fresh self-play/opponent simulations for policy improvement and win-rate comparisons. CFR/MCCFR optimize through a game model; they do not require millions of human labels. [OpenSpiel](https://github.com/google-deepmind/open_spiel) supplies the training environments already used in this lab. [AIVAT](https://arxiv.org/abs/1612.06915) is a later variance-reduction option when its required known strategies/value estimates are available.

## Reproduce the audits

Run from the repository root with the existing research environment:

```sh
.venv/bin/python audit_pokerbench.py --download
.venv/bin/python audit_pluribus.py
.venv/bin/python -m unittest -q
```

Downloads stay in ignored `data/`. The scripts save reports in `results/`. PokerBench downloads about 91.5 MB; the Pluribus script fetches only the 71-file sample listed in `pluribus_sample_manifest.json`. The full 20.3 GB archive is not needed for these experiments.
