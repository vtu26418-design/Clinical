# Duration and prolonged-risk models (artifact version 2)

This experiment predicts completed-trial duration in days and the probability
that duration exceeds a quantile fitted to the retained training cohort. It is
research decision support. A model recommendation is an observed validation
comparison, not evidence of prospective clinical validity or a promise that a
more complex model is better. Generated software fixtures cannot establish
research performance.

## Models and configuration

All enabled models use exactly the same retained train, validation, and test
trials. The original four branches remain available.

| Model key | Display name | Input mode | Family |
| --- | --- | --- | --- |
| `median_baseline` | Median / prevalence baseline | `baseline` | `constant_baseline` |
| `structured` | Structured linear | `structured` | `ridge_logistic` |
| `text` | Text linear (TF-IDF) | `text` | `ridge_logistic` |
| `multimodal` | Multimodal linear | `multimodal` | `ridge_logistic` |
| `structured_extra_trees` | Structured Extra Trees | `structured` | `extra_trees` |
| `structured_random_forest` | Structured Random Forest | `structured` | `random_forest` |

Each branch has a separate regressor and binary risk classifier. The baseline
uses the training median and training risk prevalence. Linear branches retain
the existing Ridge alpha grid `[1, 10, 100]` and logistic C grid `[0.1, 1, 10]`.
Each nonlinear task evaluates two candidates: `min_samples_leaf` of 2 or 5,
with 64 trees, maximum depth 12, `max_features="sqrt"`, one worker, and the
configured random seed. The selected regression and classification settings
are recorded separately. A one-class training cohort uses a constant training
prevalence classifier; undefined discrimination metrics remain JSON null.

`ExperimentConfig.enable_advanced_models` defaults to `true`. Set the JSON
boolean to `false` in a copied configuration to run only the original four
branches. Strings such as `"false"` are rejected. For example:

```bash
python scripts/train_models.py --help
python scripts/train_models.py --input path/to/canonical.csv --output artifacts/my-run --config configs/research.json
```

Use a new output directory for every experiment. The minimum cohort guard is
a software requirement, not a scientific power calculation.

## Leakage controls and model selection

Whole start-date groups define chronological splits. Training outcomes must
precede the validation cutoff, and validation outcomes must precede the test
cutoff. Rows whose outcomes were unavailable at those cutoffs are purged and
reported. Preprocessors, imputation, categorical encoding, numeric scaling,
TF-IDF vocabulary, PCI parameters, and the prolonged-duration threshold fit on
training records only. Validation records choose candidate settings; models
are not refitted on validation records.

Regressors minimize validation RMSE, equivalently validation mean squared
error. Classifiers minimize validation Brier score. The overall recommendation
is the enabled classifier with the lowest validation Brier score, with model
name as the deterministic exact-tie rule. Recommendation is computed before
test predictions and metrics are produced. It may select the constant
baseline and does not establish which regressor has the lowest duration error.
Test outcomes cannot alter the recommendation or any fitted parameters.

Unverified baseline provenance still means a retrospective snapshot: registry
features and narratives may have been updated after study start. Temporal
splitting alone does not repair that limitation. Completed-only selection
also excludes ongoing/censored trials and can bias the cohort.

## Saved interfaces

The filenames remain `manifest.json`, `models.joblib`, `metrics.json`,
`held_out_predictions.csv`, `cohort_exclusions.csv`, and
`temporal_exclusions.csv`. Both manifest and executable model artifact declare
`artifact_version: 2` and `task: "duration"`. Prediction rejects mismatched task,
version, run ID, or source metadata. Version 1 artifacts should be retrained;
there is no silent migration. Only load trusted local joblib files.

The manifest adds:

```text
recommended_model: model key
recommendation:
  model_name: model key
  metric: "brier"
  split: "validation"
  value: finite number
  reason: explanation of validation-only selection and its limits
models[model key]:
  family: family key from the table above
  input_mode: input mode from the table above
  display_name: human-readable name
  selection: candidate settings and selection rules
  metrics:
    validation: existing regression, classification, calibration, n,
                positive_count, and confidence_intervals fields
    test: same metrics plus by_phase
  diagnostics:
    validation: diagnostic object
    test: diagnostic object
```

Each diagnostic object contains `scatter`, `reliability`, `total_n`, and
`scatter_n`. Scatter points have `{nct_id, actual, predicted}` with durations
in days. When a split has more than 200 trials, the plot uses at most 200
evenly spaced rows in the retained chronological order. This is a display
subset, not a random or representative sample. CSV predictions, reported
metrics, and reliability bins always use every retained trial.

Reliability has `{bins, expected_calibration_error}`. Each nonempty equal-width
probability bin has `{lower, upper, count, mean_probability,
observed_fraction}`. There are at most ten bins, and probability 1 belongs to
the final bin. Expected calibration error is the count-weighted absolute gap
between mean predicted probability and observed positive fraction. These
diagnostics do not perform post-hoc calibration.

`models[name].metrics.test.by_phase` is an array of:

```text
{phase, n, positive_count,
 regression: {mae, rmse, r2},
 classification: {auroc, average_precision, brier},
 caution}
```

Phase labels come from the registry inputs, including unknown or combined
labels. Subgroups have no role in selection. Undefined R-squared, AUROC, and
average precision are null. The caution field explains small samples and
one-class groups. This experiment is separate from the educational clinical
phase classifier, whose artifact names and task differ.

Bootstrap intervals retain the existing paired-trial resampling method.
Validation intervals are descriptive after tuning and model selection; they
do not correct selection optimism or guarantee coverage. Test intervals are
conditional on the fitted model and do not include model-fitting uncertainty
or site/sponsor clustering.

## Prediction explanations

Linear predictions retain coefficient-times-transformed-value contributions:
classification in log-odds and regression in days before clipping. Their
`scope` is `local`. Constant baselines have no feature-specific attribution.

Tree explanations use `{method: "global impurity feature importance",
scope: "global", units: "normalized impurity decrease", features:
[{feature, importance}], note}` for the classifier and regressor separately.
The largest 12 training-fitted feature importances are shown. They summarize
the model globally, can favor high-cardinality features, and do not sum to an
individual trial's probability or duration. They are not local SHAP values
and do not establish causation. A one-class classifier fallback is explicitly
reported as a constant baseline.

## Verification

Run `python -m pytest tests/test_research.py -q`. Regression checks cover
train-only numeric and category transforms, held-out text isolation,
test-outcome invariance of fitting and recommendation, deterministic bounded
tree fitting, model artifact task checks, constant-class behavior, real CSV
versus diagnostic consistency, phase subgroup errors, and the 200-point plot
limit. Test records are generated software fixtures only.
