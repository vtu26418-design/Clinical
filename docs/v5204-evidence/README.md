# Actual model evaluation and application evidence

The approved model/source files in `examples/` and `data/starter/` are unchanged. The new candidates are optional training capabilities; none was silently promoted.

- `current-duration-analysis/` and `current-phase-analysis/`: recomputed HTML/JSON/CSV and optional PDF summaries for the approved bundles.
- `candidate-analysis/`: recomputed evaluation of the new opt-in candidates and paired comparison to the matched old-enabled run.
- `accuracy-benchmark/` and `accuracy-baseline/`: complete saved evaluation manifests, aggregate metrics, per-record predictions and exclusion evidence. These folders do not contain inference artifacts and are not approved registry models.
- `accuracy-frozen-protocol.json`, `accuracy-benchmark-summary.json`: declared candidates, original split IDs, exact outcomes, all model scores and source hashes.
- `recovered-cohort-feasibility.json`: eligibility/date/overlap feasibility only; no fitting or new holdout selection.
- Screenshots and MP4: actual application captures; clinic figures illustrate workflow and are not actual patients.

The matched result is mixed: MAE improves but RMSE worsens. Existing approved defaults remain. The independently selected risk component reproduces the prior text recommendation. No perfect accuracy or prospective clinical validity is claimed.

Regenerate the candidate analysis without deserializing an estimator:

```bash
.venv/bin/python scripts/generate_model_report.py --run-dir docs/v5204-evidence/accuracy-benchmark --baseline-dir docs/v5204-evidence/accuracy-baseline --output-dir reports/new-comparison
```

To fit a new reproducible comparison, run `scripts/train_models.py` with the frozen `data/starter/trials.csv`, `data/starter/metadata.json` and `configs/research-accuracy.json`, writing to a new result folder. Model training is separate from report generation and owner approval. Do not retune to the inspected test set; further validation requires a new untouched cohort.
