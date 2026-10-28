# First preflop supervised models

October 28, 2026. Trained locally on PokerBench structured preflop data. The best validation model was histogram gradient boosting; a depth-eight decision tree was nearly as accurate and substantially faster. These models imitate dataset targets, not proven optimal play.

## Cleaning and evaluation

The original 63,200 training rows collapsed to 30,612 observations after treating reversed hole-card order and equivalent suits as identical. We quarantined 26 canonical groups with conflicting labels (230 original rows), then kept one example per remaining observation: **30,586 examples**. This stricter identity differs from the earlier exact-string audit.

Entire public betting histories stay in one partition. Train/validation/test contain 21,616 / 4,458 / 4,512 hands and 1,535 / 329 / 330 distinct histories. Group intersections are asserted empty. The models never use CSV indices, target labels or opponent/future cards as features. Splits are deterministic with seeds 42 and 43. Exact public histories are grouped; semantically similar betting sequences may still cross partitions.

Each model scores each supplied action candidate. Features describe the player's ranks/suitedness, position, pot, player/bet counts, per-seat public action summaries, action menu and candidate amount. Candidate scoring permits distinct raise sizes without creating a separate classifier class for every size. These history summaries lose some ordering detail; they are a baseline abstraction.

Fixed configurations were selected before fitting: scaled logistic regression, decision tree (depth 8, minimum leaf 40), boosted trees (100 iterations, 15 leaves, L2=1, no internal early stopping). Each hand has total training weight one across its candidates. Selection uses validation exact-action accuracy. A most-common-legal-action baseline uses training target frequencies. No hyperparameter search was performed.

## Measured results

Exact accuracy includes the action and its listed raise amount. Local timing includes feature extraction, single-hand inference and legal-candidate selection, after warmup with one CPU thread; it excludes process startup and JSON loading.

| Model | Grouped test accuracy | p99 time | Calls >1 ms / 1,000 |
| --- | ---: | ---: | ---: |
| Most common legal action | 79.72% | 0.083 ms | 0 |
| Logistic regression | 79.57% | 0.176 ms | 0 |
| Decision tree | 91.42% | 0.116 ms | 0 |
| Boosted trees | 91.69% | 0.634 ms | 4 |

Every output was in its supplied menu by construction. This does not verify that the dataset menu matches a tournament engine. Timing is machine/load dependent; earlier measurements differed, so do not treat p99 below 1 ms as a hard deadline guarantee. Logistic regression did not beat the simple frequency baseline.

### Coverage limitations matter

The grouped test has 3,597 folds, 620 calls, 237 raises and 58 checks. Because all canonical check targets share a public action line assigned to test, **training and validation have zero check targets**. Boosted trees recovered 97.0% of folds, 75.0% of calls, 76.8% of raises and **0% of checks**. No partition has an all-in target. This split exposes a training coverage gap; we have not moved the check group into training after seeing results.

The selected model's fixed-five-family macro-F1 is 0.493; that average includes the unsupported all-in family. Per-family precision/recall/support are saved in the JSON report. The 91.69% headline must not be read as balanced mastery of all decisions. The legal-frequency baseline already scores nearly 80% because folds dominate.

The published 1,000-row external test becomes 784 unique, non-conflicting observations; removing canonical overlap against the entire original training corpus leaves only **174 rows** (163 folds and 11 checks). Boosted trees score 90.80% there, but this tiny skewed subset is not a useful overall ranking. We report it without tuning to it. Broader suit-canonical overlap is much larger than the previous exact-string overlap.

## Reproduce and inspect

```sh
.venv/bin/python -m pip install -r requirements-research-lock.txt
# If datasets are absent:
.venv/bin/python audit_pokerbench.py --download
.venv/bin/python train_preflop.py
.venv/bin/python -m unittest -q
```

The run writes cleaned train/validation/test/external JSONL under ignored `data/preflop_clean/` and the selected fitted model to `data/models/preflop.joblib`. Only load a joblib model you trust. Generated artifacts stay local; training code and result summaries are public.

- [Full metrics, warnings, source hashes and timing](results/preflop_training.json)
- [Split sizes, file hashes and public-history group hashes](results/preflop_split_manifest.json)
- [Dataset investigation](DATASETS.md)

Next: collect independent scenarios covering checks/all-ins and more stack sizes, retain this test as a fixed benchmark, then test a lightweight policy in a compatible Hold'em simulator. Do not attach this policy to the existing Kuhn/Leduc games: their states and actions differ. Full-hand performance, chip gain, tournament points and organizer-runtime compliance remain unmeasured.
