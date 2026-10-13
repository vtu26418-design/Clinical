# Observed starter results · v4.0.0

These are actual local API runs on the bundled frozen 800-record ClinicalTrials.gov subset. They are retrospective software/research examples, not clinical validation. Full precision values are retained in the JSON/CSV artifacts.

## Duration / prolonged-duration task

Retained partitions: **105 train, 9 tuning, 11 calibration, 64 test**. `splits.validation` denotes tuning. Each test metric below is evaluated on the same 64 records. Test has six prolonged-duration positives; tuning and calibration each have zero. Probability calibration is therefore unavailable, with its reason recorded; raw probabilities remain available.

| Model | MAE (days) | RMSE (days) | R² | Raw AUROC | Raw Brier | Interval coverage (test) |
|---|---:|---:|---:|---:|---:|---:|
| median_baseline | 351.188 | 419.229 | -0.0496 | 0.5000 | 0.10864 | 48/64 |
| structured | 372.677 | 432.384 | -0.1165 | 0.6121 | 0.11959 | 60/64 |
| text | 314.701 | 366.982 | 0.1957 | 0.8075 | 0.07757 | 63/64 |
| multimodal | 332.998 | 399.283 | 0.0479 | 0.7615 | 0.09341 | 61/64 |
| structured_extra_trees | 354.218 | 418.790 | -0.0474 | 0.6710 | 0.10882 | 58/64 |
| structured_random_forest | 350.550 | 428.373 | -0.0959 | 0.6724 | 0.11279 | 58/64 |
| structured_gradient_boosting | 372.389 | 491.099 | -0.4404 | 0.5431 | 0.13411 | 61/64 |

Recommended by the declared **raw tuning Brier** rule: `text`. This is not selection on test results. Tuning has only nine rows and one class, so ranking is particularly unstable. The added Gradient Boosting branch does not outperform the simpler text model in this snapshot. Negative R² values explicitly show performance below the test-mean reference.

Intervals target nominal marginal coverage 0.90 using 11 calibration residuals (rank 11, the maximum). The table reports observed coverage; it is not a future guarantee. Wide intervals can cover many outcomes while being operationally imprecise. Time shift can invalidate exchangeability. Tuning outcomes are purged before the test cutoff but are not guaranteed available before calibration starts; this is a retrospective evaluation, not an online simulation.

## Clinical-phase task

Retained partitions: **175 train, 57 validation, 59 test**. Phase names are redacted from text; mixed-phase and unsupported records are excluded.

| Model | Test accuracy | Balanced accuracy | Macro F1 |
|---|---:|---:|---:|
| majority_baseline | 0.3729 | 0.2500 | 0.1358 |
| phase_logistic | 0.5593 | 0.4818 | 0.4752 |

There are no Early Phase 1 examples in the retained starter training/test partitions. No performance claim is made for that class. Reported registry phase remains the source label; classifier output does not establish regulatory phase.

## Reproduce and interpret

Load the bundled real starter in Data Manager, run Experiments and Phase Model, and inspect their manifests/downloaded metrics. The GUI uses `ExperimentConfig` defaults; CLI configuration files may differ. Use the saved manifest configuration to reproduce an exact run. Source hashes, package versions, selected candidates, split membership and source-code fingerprints are in the included manifests.

The snapshot is a convenience subset of completed trials, with latest-state fields rather than independently reconstructed baseline protocols. Completion-only selection, changing protocols and temporal shift limit generalization. No external/prospective validation has been run. Never load an untrusted joblib artifact.
