# Pokerbot preparation experiments

Measured October 28, 2026. This is an unofficial learning lab. The event variant and Python Agent interface are not yet available. Two-player toy-game results do not establish eight-player tournament strength.

## Tools and algorithm choices

| Tool | Role | Decision |
| --- | --- | --- |
| [OpenSpiel](https://github.com/google-deepmind/open_spiel) | Games, CFR/CFR+, external-sampling MCCFR, exact exploitability | Installed and benchmarked on Kuhn and Leduc |
| [PokerKit](https://pokerkit.readthedocs.io/en/stable/) | Poker rules, hand evaluation, multiple variants | Installed; five-card evaluator checked against UCI |
| [RLCard](https://github.com/datamllab/rlcard) | Card-game reinforcement-learning environments | Alternative for later RL experiments; not benchmarked here |

[CFR+](https://arxiv.org/abs/1407.5042) is our initial small-game baseline. It trains offline; the exported policy samples legal actions from a lookup table. [External-sampling MCCFR](https://www.cs.cmu.edu/~waugh/publications/nips09b.pdf) samples game-tree trajectories, making it a useful next candidate as games grow. [Discounted CFR](https://arxiv.org/abs/1809.04040) is another research candidate, not implemented in this lab.

There is no demonstrated universally best choice here. Exact tables do not scale to full-size poker. Larger variants will require abstractions or other approximations, and multiplayer tournament points are a different objective from two-player zero-sum chip gain. Neural methods such as Deep CFR/NFSP would add training and deployment work; we have not tested them.

## Reproduce

Use Python 3.11+. Research packages are optional; the original arena and poker math remain dependency-free.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-research-lock.txt
.venv/bin/python -m unittest -v
.venv/bin/python simulation_benchmark.py --iterations 1000 --pairs 12500 --seed 42
.venv/bin/python validate_uci.py
```

`--pairs` is per opponent, so 12,500 produces 100,000 hands across four opponent types and two seats. Use `--pairs 125000 --output results-million` for one million hands. This trains again before evaluation. Expect greater runtime and disk use. Keep large output directories out of Git. Scores reproduce with the same environment and seeds; timings and compressed-file hashes can vary.

## Measured results

All solvers received 1,000 iterations. Times include checkpoint metric calculations; this is **not an equal-compute comparison**. The three MCCFR runs use seeds 42, 43, and 44.

| Algorithm | Kuhn exploitability | Leduc exploitability | Leduc elapsed seconds |
| --- | ---: | ---: | ---: |
| CFR | 0.000938 | 0.011817 | 5.89 |
| CFR+ | 0.0000874 | 0.000246 | 6.81 |
| External MCCFR, seed 42 | 0.048620 | 1.271005 | 0.13 |
| External MCCFR, seed 43 | 0.024226 | 1.366680 | 0.13 |
| External MCCFR, seed 44 | 0.016915 | 1.247668 | 0.13 |

Lower OpenSpiel exploitability is better. CFR+ was selected using exact exploitability in each training game, not by tuning against the evaluation opponents. MCCFR needs an equal-wall-time follow-up before drawing a practical efficiency conclusion.

The selected Leduc policy played 25,000 hands per opponent with paired chance seeds and swapped seats:

| Opponent | Net chips/hand | Approximate 95% interval |
| --- | ---: | ---: |
| Uniform random | +0.69568 | [0.65161, 0.73975] |
| Check/call | +0.65880 | [0.63338, 0.68422] |
| Raise when legal | +0.32168 | [0.25704, 0.38632] |
| Same trained policy | 0 | Seat-symmetry check only |

Intervals use the sample variance of paired means. Identical-policy self-play repeats identical seat-specific random streams and cancels exactly; its zero interval is not a strength estimate. Paired seeds share chance randomness, but different action paths can produce different chance histories. Baseline opponents are simple; defeating them does not prove robustness against strong adaptive bots.

No illegal actions occurred. Across recorded policy decisions, p99 lookup/sampling time was below 1 microsecond and none exceeded 1 millisecond. This excludes observation construction, loading, process overhead and organizer sandbox costs. The selected Leduc JSON policy is 160,879 bytes. Neither size nor local timing makes it an event-ready submission.

Machine, package versions, convergence checkpoints and full figures are in [benchmark.json](results/benchmark.json). Policies and an 80-hand replay sample are committed; the full 100,000-hand compressed dataset is generated locally and ignored by Git.

## Data: what each source can teach us

1. **Generated simulations:** `results/simulated_hands.jsonl.gz` contains the 100,000 generated hands, actions, player-visible information states, legal actions, chance events and returns. Seeds and a SHA-256 digest are recorded. Full histories expose hidden cards for offline replay; never pass them into an acting bot or use future information as model features. This is the useful starting source for strategy experiments, not a sample of real tournament opponents.
2. **[UCI Poker Hand](https://archive.ics.uci.edu/dataset/158/poker%2Bhand):** all 25,010 training rows and 1,000,000 testing rows matched PokerKit's evaluator. The mapper splits royal flushes from straight flushes to match UCI labels. These are five-card classifications, with no bets, stacks or opponent actions. Use them for evaluator validation, not betting-policy training. Download is cached in ignored `data/`; [validation report](results/uci_validation.json) records provenance, class counts, version and archive digest. Attribution: Cattral & Oppacher (2002), [DOI](https://doi.org/10.24432/C5KW38), CC BY 4.0.
3. **[PHH hand-history dataset](https://github.com/uoftcprg/phh-dataset):** a promising follow-up for replaying actual betting sequences across variants, including 10,000 Pluribus hands. Not downloaded or benchmarked in this run. Examine provenance, hidden-card availability and selection bias before using for training. Match the eventual event variant; historical play is not automatically a useful opponent distribution.

The public [event rules](https://pokerbot.sequoiacap.com/rules.html) specify offline execution, a one-millisecond decision budget and the variant revealed at the event. They do not establish that importing this prebuilt lab is allowed.

## Next experiment

Compare CFR+ and MCCFR at equal elapsed budgets with multiple seeds, then expand the opponent pool and evaluate tournament points alongside chip gain. Once the official interface and variant are released, prioritize legal-action handling, end-to-end timing and organizer-simulator tests before adding complexity.
