# v4 duration models and uncertainty

Duration artifacts use schema version **3** and task `duration`; v3 duration artifacts (version 2) require retraining. Phase artifacts have their own independent version/task contract. Predictions verify matching artifact/manifest run ID, task, version, source metadata, input hash and pipeline-source hash. Only load trusted application-produced joblib files.

## Comparable experiments

The six v3 branches remain: median/prevalence baseline; structured, text and multimodal Ridge/Logistic models; structured Extra Trees; and structured Random Forest. A seventh `structured_gradient_boosting` branch adds GradientBoostingRegressor/Classifier. Advanced branches are enabled by default and may all be disabled with `enable_advanced_models=false`, preserving the four original modalities.

Gradient Boosting uses 64 estimators, maximum depth 3, learning rate 0.05, and the configured random seed. A bounded grid tries minimum leaf sizes 2 and 5 separately for regression and classification. Extra Trees/Random Forest retain 64 trees, maximum depth 12, leaf sizes 2 and 5, and one worker. Linear branches retain Ridge alpha 1/10/100 and Logistic C 0.1/1/10. A training cohort with one risk class uses a fitted prevalence classifier.

Only training fits imputers, numeric scaling, one-hot levels, TF-IDF vocabulary, PCI ranges and the prolonged-duration threshold. The threshold is the configured training duration quantile; a duration strictly above it is positive. Structured inputs are enrollment, arms, primary/secondary outcome counts, criteria count, study type and phase. Text uses protocol TF-IDF, not a language-model encoder. Regression estimates are clipped at zero before selection, evaluation, residual calibration and serving.

## Tuning, calibration and test roles

The original temporal split uses whole start-date calendar-day groups. Training outcomes must precede the original validation cutoff; original validation outcomes must precede the test cutoff. Existing outcome-availability purges are retained.

The retained original validation groups are split near their halfway group: earlier groups tune models; later groups calibrate. To preserve existing clients, `splits.validation` means **tuning**, with `role=tuning`; `splits.calibration` is the independent later subset. The manifest `validation_partition` records original row IDs/counts, group count, actual partition counts/cutoff and fallback reason. No date group is divided and no retained validation row is lost.

At least 10 later calibration rows and one earlier tuning row are required. If unavailable, all original validation rows tune and calibration is empty. Duration uncertainty and probability calibration are explicitly unavailable. The minimum training/validation/test cohort guards remain; small calibration support does not itself fail an otherwise valid experiment.

Only tuning labels select hyperparameters (minimum RMSE or raw Brier) and the recommended risk model (minimum **raw tuning Brier**, exact ties by model name). Calibration never selects models, and models are not refitted on tuning/calibration. Tuning outcomes are available at the test cutoff, not necessarily at the calibration start date; this design is a retrospective holdout evaluation, not an online prospective simulation.

## Split-conformal duration interval

For the selected training-fitted regressor of each branch, reserve calibration absolute residuals `r_i = |y_i - max(0, prediction_i)|`. For `n` residuals and miscoverage `alpha`, the finite-sample rank is:

`k = ceil((n + 1) * (1 - alpha))`.

If `k <= n`, use the **kth ordered observed residual**, without interpolation. The served interval is `[max(0, predicted_days - q), predicted_days + q]`. The default alpha is 0.1 (nominal marginal coverage 0.9), configurable as `uncertainty_alpha` in `configs/research.json`.

If `k > n`, the mathematically correct quantile is infinite: JSON reports `residual_quantile_days=null`, both interval bounds `null`, `status=available` and `bounded=false`. This differs from insufficient calibration, reported as `status=unavailable` with a reason. No nonfinite JSON numbers are exported.

Nominal marginal coverage requires exchangeability between calibration and future observations. Chronological shift, sponsor/site clustering, incomplete outcomes and unverified baseline registry features can violate it. No clinical, individual or prospective coverage guarantee is made. Manifest model uncertainty reports descriptive `test_diagnostics`: sample size, covered count, observed coverage and mean interval width. Infinite intervals trivially cover all finite test outcomes; width is null. Test outcomes only assess coverage and never fit the quantile.

## Probability calibration and metric semantics

Primary prediction `probability` (also `raw_probability`) and CSV `prolonged_probability` stay **raw**, with `probability_semantics=raw`. Primary classification metrics, reliability bins, phase subgroup metrics and the recommendation use those raw probabilities.

When calibration has at least 10 rows and at least **two labels of each class**, fit a sigmoid by LogisticRegression (C=1, deterministic seed) to clipped raw-probability logits using only the calibration subset. Probability clipping uses epsilon 0.000001. This regularized sigmoid is a post-hoc transform; the original classifier stays unchanged.

Prediction `calibrated_probability` and CSV `calibrated_prolonged_probability` are separate nullable fields. Test/calibration metrics add `calibrated_classification` and `calibrated_reliability` when fitted. Calibration metrics assess the same cohort used to fit the sigmoid and are explicitly labeled in-sample. Test calibrated metrics use the untouched test labels; they cannot change recommendation. The original raw classifier explanation continues to describe raw fitted-model behavior, not the sigmoid-calibrated probability.

`calibration` metadata exposes status, method, calibration sample/class counts, minimum guards and reason. Insufficient rows or one/under-supported class leaves calibrated probabilities null. It never disables otherwise available raw predictions.

## Extrapolation and provenance

Training-only `training_support` stores observed finite numeric minima/maxima and categorical levels. Served `extrapolation` reports numeric out-of-range values, unseen categories, missing numeric fields and `outside_training_support`. A numeric field with no finite training values flags any new finite value. Missing numeric values use training imputation and are separately disclosed. These descriptive flags are **not an OOD probability**; an in-range record can still differ from the training distribution, especially in text or correlated inputs.

Prediction `cohort_membership` is train, validation (tuning), calibration, test or outside retained splits. Scope text identifies in-sample training, selected tuning, calibration-fitting and held-out test roles. A hypothetical query retaining a source trial identifier still retains its source cohort membership; membership does not establish that an edited scenario was observed or validated.

Research PCI in these artifacts is equal-weight training-fitted min-max complexity, clipped to training ranges, with training-median imputation and zero contribution for constant components. It differs from the fixed-reference PCI displayed elsewhere in the workbench. Neither is a calibrated risk probability or causal clinical score.

## Scientific checks and limits

`tests/test_research.py` includes independently hand-checked MAE/RMSE/R2/binary Brier values and conformal ranks, date-group/no-row-loss checks, training-only preprocessing, calibration/test mutation tests, capacity bounds, class-support fallback, raw/calibrated serving-to-CSV-to-metric agreement, empirical interval coverage, JSON unbounded intervals, extrapolation flags and artifact/source/hash/task incompatibility checks. Software fixtures verify computation only; their metrics are not research evidence.

Undefined R2/AUROC/average precision remain JSON null. Bootstrap confidence intervals are descriptive and conditional on fixed fitted models; they omit fitting uncertainty and clustering. Completed-only outcomes create follow-up/selection bias. Registry narratives and feature updates may contain post-start information unless independently curated baseline provenance is established. Recruitment/amendment probabilities, survival inference, BioBERT and SHAP are not added by this extension.

Run the fresh core checks with `.venv/bin/python -m pytest`. Retrain using the normal experiment workflow and a new output directory; completed experiment directories remain immutable.

Phase design features normalize recognized Arabic/Roman labels and pipe/slash combined aliases before fitting and serving. Combined phases remain distinct. Conformal rank uses exact decimal-alpha rational arithmetic to avoid floating-point boundary errors (n=9, alpha=0.7 gives rank3; n=39, alpha=0.825 gives rank7). GUI experiments use ExperimentConfig defaults; CLI JSON changes apply only when passed with --config.
