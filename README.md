# Clinical Trial Intelligence Workbench — v5.2.0.5

Research software for protocol complexity, total-duration risk, phase consistency and source-grounded scientific explanations.

[Start here](START-HERE.md) · [Full guide](docs/v5.2.0.5-full-guide.md) · [PDF guide](docs/Clinical-Trial-Intelligence-v5.2.0.5-Full-Guide.pdf) · [Verification](docs/v5.2.0.5-release-verification.md)

## Run on Windows with Docker

Open Docker Desktop, extract the complete ZIP and run:

```powershell
.\START_DOCKER_WINDOWS.bat
```

Open http://localhost:8000. Read SETUP_TOKEN from your private .env for the first-owner form, then create a project. PostgreSQL is included. Existing credentials are preserved; never publish .env.

## Included improvements

- Genuine 101,135-record frozen registry source with preserved responses, hashes and derived shards; no duplicated or invented records.
- Larger chronological research experiments, exact source/input contracts and saved approved models usable without startup training.
- Fixed import-to-prediction race, requested-config readiness checks and immutable saved-result visualizations.
- Settings → Model quality and Validation Lab: recomputed saved-row metrics, comparisons, plots, confusion matrices, provenance and report downloads.
- Science Studio: topic-appropriate interactive neurons, DNA, molecular or processing illustrations; editable source captions/narration, camera/style controls, PostgreSQL save/reload and JSON/PNG export.
- Optional configured-provider drafts retain AI origin through edits/transfer; manual explanations work without a key.
- Project roles, private uploads, account/session security and existing activation choices are preserved. New project defaults are manually reviewed research bundles.

## Measured primary results

On 8,299 held-out duration trials, tuning-selected MAE is 244.26 days versus 285.51 for the matched median baseline; RMSE is 313.71 versus 331.78 days. Risk AUROC is 0.8151 and Brier is 0.05257. Phase accuracy is 73.75% on 8,133 held-out trials, with macro-F1 of 0.6768. These larger-cohort results cannot be directly compared with historical 64/59-record test scores.

Risk accuracy at threshold 0.5 is 94.37%, but the always-negative baseline is 96.79%; sensitivity of 20.68%, precision of 17.68% and balanced accuracy of 58.74% expose the imbalance. No 90% discrimination, perfect prediction or prospective clinical validation is claimed. The separately evaluated refinement is described below.

The new default phase refinement achieved 67.93% accuracy versus 66.48% for the original classifier on the same 50,139-record, ID-disjoint partial-start-date subgroup (macro-F1 0.6740 versus 0.6574). This is a different group from the original 8,133-record test and is not chronological/prospective validation. Original models remain selectable; existing project activations are preserved. The extra risk candidates did not improve tuning Brier score, so the original selected risk model stays active. Full frozen evidence and portable dry-run/refit commands are included in the guide.

The acquired count is not the fitted count: duration train/tuning/calibration/test = 8,806/4,624/2,841/8,299; phase = 16,932/14,634/8,133. Current registry snapshots and completed-only selection remain material limitations.

Use GENERATE_MODEL_REPORT_DOCKER_WINDOWS.bat to save real HTML/JSON/CSV analysis under reports/. The full guide explains environment values, every section, training, approval, predictions, tests, backups and Docker DNS troubleshooting. This is research decision support, not clinical or regulatory advice.
