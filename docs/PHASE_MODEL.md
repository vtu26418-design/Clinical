# Registry-phase classifier

This separate supervised experiment estimates a trial's recorded clinical phase from numeric protocol characteristics and redacted protocol text. It is an educational consistency check. It does not assign a regulatory phase, predict phase advancement, estimate treatment benefit, or estimate trial success. The actual registry phase remains visible alongside the prediction.

The classifier uses existing pandas/scikit-learn/joblib dependencies. It does not call an external AI provider or need an API key.

## Run a reproducible experiment

From the project root after installing project dependencies:

```bash
python scripts/train_phase_model.py --input data/processed/my_trials.csv --output artifacts/phase_run_001 --metadata data/processed/my_provenance.json
```

Use a new output directory for each run. CSV and Parquet inputs are accepted. `--metadata` is optional but strongly useful for provenance; existing metadata are preserved and the CLI adds `source_file` and a SHA-256 checksum of the original source file. The model also records a checksum of the canonical input dataframe, its configuration, pipeline source checksum, environment versions, complete split trial IDs, class support, and a model-artifact checksum.

Optional `--config phase_config.json` accepts:

```json
{
  "max_text_features": 20000,
  "logistic_cs": [0.1, 1.0, 10.0],
  "max_iter": 2000,
  "random_seed": 42
}
```

Configuration bounds: 10–50,000 text features, one to eight finite C values between 0.0001 and 100, 100–5,000 solver iterations, and an integer seed between 0 and 4,294,967,295. The chronological split fractions are fixed at 60%/20%/20% of distinct start dates.

## Eligible cohort and inputs

Required columns are `nct_id`, `start_date`, and `phase`. Trial IDs must be present and unique. Dates must establish calendar-day precision; partial and invalid dates are excluded. Timestamps are normalized to a calendar date after UTC parsing, so rows on the same start date are kept together.

Supported targets are `EARLY_PHASE1`, `PHASE1`, `PHASE2`, `PHASE3`, and `PHASE4`. Single-phase aliases such as `Phase 2`, `Phase II`, and `Early Phase 1` are normalized. Combined phases, NA/not-applicable values, missing values, and unknown labels are explicitly excluded and exported with reasons. Labels are not forced into adjacent phases. Recruiting and ongoing trials may qualify: completion status and completed outcome dates are not needed for this task.

At least 40 eligible trials are required, with at least 20 in training and 5 each in validation and test. Training must contain at least two phase classes. These are software guards, not a claim of sufficient statistical power. Distinct chronological date groups determine the split; large groups may cause unequal row counts and can make an otherwise large dataset ineligible.

The feature whitelist is:

| Type | Columns |
| --- | --- |
| Numeric | `enrollment`, `number_of_arms`, `primary_outcomes`, `secondary_outcomes`, `criteria_count` |
| Text | `title`, `brief_summary`, `detailed_description`, `eligibility_criteria` |

IDs, the phase target, status, study type, all date fields, and duration/risk outcomes never enter the fitted features. Non-finite and negative numeric values are treated as missing. Missing numeric columns are allowed and imputed from training data. Empty/redacted text receives a common missing-text token.

Explicit phase mentions are removed from every text field before vectorization, including Arabic and Roman numbers, number words, early-phase labels, common subphase suffixes, and combined forms such as `Phase I/II`. Redaction cannot remove every indirect clue or establish that a registry snapshot reflects the protocol at enrollment. Counts and enrollment may also have changed after trial start. Without independently established baseline provenance, all output carries a retrospective-snapshot warning; chronological ordering alone does not justify prospective claims.

## Fitting and evaluation

The main `phase_logistic` model combines train-fitted median imputation and standard scaling with train-fitted TF-IDF unigrams/bigrams, followed by multiclass logistic regression. C is chosen solely by highest validation macro-F1; the first configured candidate wins ties. Validation is never included in fitting. Test features and labels are not used to choose C. The `majority_baseline` always predicts the most frequent training class.

Validation and test exports contain accuracy, balanced accuracy, macro-F1, per-class support, and a confusion matrix. Confusion matrices always use the five canonical labels: rows are actual labels and columns are predictions. Balanced accuracy averages recall over classes actually present in the evaluated split. Macro-F1 averages the union of actual and predicted labels, with undefined F1 set to zero. The included `macro_f1_labels` records that denominator explicitly; labels absent from both actual and predicted values do not depress macro-F1. This label policy can yield different denominators across splits/models, so inspect class support when comparing.

Held-out labels absent from training are retained and counted as errors, and `unseen_training_labels` identifies them. Models cannot predict unseen training classes; their displayed class probabilities are zero. This is a model limitation, not evidence that the phase is impossible. Logistic probabilities are uncalibrated scores over the training classes. The main model is exposed as `phase_logistic`; its presence or designation as `recommended_model` does not assert that it outperformed the baseline.

Validation scores are affected by hyperparameter selection. The untouched test split provides a held-out estimate for this cohort under the stated snapshot limitations. No confidence intervals, calibration guarantees, or superiority claims are manufactured.

## Output files

| File | Purpose |
| --- | --- |
| `phase_manifest.json` | Completed experiment, source/configuration/environment provenance, all split IDs, metrics, limitations, and artifact checksum |
| `phase_models.joblib` | Fitted main classifier and majority baseline with matching metadata |
| `phase_metrics.json` | Per-model validation and test metrics |
| `phase_held_out_predictions.csv` | All validation/test rows for both models, actual/reported/predicted phase, correctness, and five probability columns |
| `phase_cohort_exclusions.csv` | Excluded IDs, reported phase, and exclusion reasons |
| `phase_error.json` | Failure information if cohort validation or fitting fails; absent after successful completion |

These names and the `task: "phase"` discriminator isolate the task from duration/risk artifacts. Empty or failed experiments provide no prediction. Keep source and model artifacts together in trusted local storage. Joblib can execute Python when loaded: never upload, import, or load a model file from an untrusted source. A checksum detects accidental changes; it is not an authenticity signature.

## Python and HTTP interfaces

```python
from src.clinical_trial_intelligence.phase_model import (
    prepare_phase_cohort, phase_temporal_split,
    train_phase_experiment, predict_phase,
)

cohort, exclusions = prepare_phase_cohort(frame)
splits = phase_temporal_split(cohort)
manifest = train_phase_experiment(frame, "artifacts/phase_run_002", source_metadata)
prediction = predict_phase(frame.iloc[0].to_dict(), "artifacts/phase_run_002")
```

`predict_phase` preserves the raw `reported_phase`, supplies `normalized_reported_phase`, and returns `predicted_phase`, the five `class_probabilities`, `cohort_membership`, `prediction_scope`, and a warning. Membership distinguishes training, validation, test, and records outside retained splits. In-sample and tuned-validation predictions are not untouched test evidence.

Missing, symlinked, corrupt, mismatched, or incompatible artifacts return `status: "unavailable"`, null prediction/probabilities, and a reason. The loader checks task, artifact version, checksum, run ID, source metadata, input digest, configuration, label catalog, training classes, and split membership coherence. The caller must additionally establish that the selected dataset matches the artifact provenance; the server performs that check before making predictions. The direct Python API is for trusted local callers and does not authenticate an arbitrary row's origin.

The HTTP integration uses separate `/api/v1/phase-experiments` and `/api/v1/phase-predictions` endpoints with experiment registry task `phase`. Phase and duration jobs share the server's single training slot. See the runbook for application startup, authentication, dataset upload, and operating instructions.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Fewer than 40 eligible trials | Inspect `phase_cohort_exclusions.csv`; obtain a larger real single-phase cohort with complete start dates. |
| Too few rows in a temporal split | Inspect distinct start-date groups and class support; obtain more data. Do not move held-out rows into training to improve reported test results. |
| Only one training phase class | Obtain a cohort with at least two classes represented before the validation cutoff. |
| Test includes unseen classes | Retain those errors and inspect `unseen_training_labels`; obtain earlier training examples before a separate future experiment. |
| Prediction unavailable | Confirm a completed phase job for the selected matching dataset; preserve the generated manifest and artifact together, then rerun if they are damaged. |
| Existing output directory refused | Choose a new run directory so prior results remain auditable. |
| Probabilities look confident | They are uncalibrated model scores. Inspect held-out errors, class support and snapshot limitations; do not use them as clinical or regulatory decisions. |

Bundled/generated fixtures exist only to exercise software. Their scores are never clinical research evidence.
