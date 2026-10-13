# Research methods and reproducibility

This repository is an executable research workbench, not a scientifically validated predictor. The v4 release bundles actual retrospective starter-cohort results and fitted example artifacts; see `STARTER_RESULTS_V4.md`. The v4 tuning/calibration and uncertainty extension is specified in `V4_MODELS.md`, which supersedes the older three-role duration description below. These are not clinically validated models. The five sample rows and deterministic records generated in tests are software fixtures only. Passing software tests says nothing about predictive or clinical validity.

## Data acquisition and canonicalization

Use an explicitly dated AACT snapshot, retaining the original archive and extracted flat files unchanged. AACT's official [download page](https://aact.ctti-clinicaltrials.org/downloads/snapshots?type=flatfiles) and [schema](https://aact.ctti-clinicaltrials.org/schema) describe the acquisition route and relational structure. Account access may be required. No account, credentials, full snapshot or BioBERT weights are included here. Do not put credentials or signed download URLs into source metadata.

The supported adapter reads UTF-8, headered, pipe-delimited `.txt` or comma-delimited `.csv` exports. It requires `studies` with `nct_id`, `overall_status`, `start_date`, `completion_date` and `completion_date_type`. Table headers and parseability are verified and SHA-256 is computed in chunks. Additional schema versions must be mapped explicitly; the adapter will not select an arbitrary CSV or silently guess a table.

| Canonical field | Source and transformation |
| --- | --- |
| `nct_id` | Unique `studies.nct_id`; duplicate study rows are rejected |
| `title`, `status` | `studies.brief_title`, `studies.overall_status` |
| `start_date`, `completion_date`, date types | Preserve reported study fields; normalize type/status case |
| `study_type`, `phase`, `enrollment`, `enrollment_type` | Study fields; numeric coercion only |
| `number_of_arms` | Study field, with available `design_groups` row count as a fallback |
| `primary_outcomes`, `secondary_outcomes` | Counts by `design_outcomes.outcome_type`; results-table `outcomes` is excluded |
| `eligibility_criteria` | `eligibilities.criteria`, joined once per trial |
| `criteria_count` | Count bullet/numbered eligibility lines; missing if no enumerated lines; an auditable proxy, not clinical NLP |
| `brief_summary`, `detailed_description` | Narrative protocol tables aggregated once per trial |
| `conditions`, `sponsor` | Condition names and lead sponsor, for descriptive display only |

One-to-many tables are aggregated before joining, so multiple outcomes or criteria cannot multiply study rows. An absent table yields missing values. Zero outcome rows in a present, complete design-outcome table produce zero counts; supplying incomplete table extracts violates this assumption. Source metadata records each selected table's hash, row count, column list, absent optional tables, missingness and mapping version. Results tables are never model features.

AACT registry snapshots describe the latest fields at the snapshot date. Enrollment, protocol text and even design fields may have been revised after start. Setting `baseline_provenance` requires actual supporting acquisition/history evidence, not merely a start date. The workbench defaults to a retrospective warning. A normalized date in an export may have lost original month/day precision; audit the raw registry history and exclude such records before making exact-duration claims. The pipeline rejects visibly partial ISO date strings rather than assuming day 1.

Example from the project root (activate the environment first):

```powershell
# Option A: acquire the ZIP manually through AACT's official account/download flow.
# Option B: download an exact HTTPS URL with an independently recorded SHA-256.
python scripts/download_aact.py --url "https://YOUR_AUTHORIZED_EXACT_SNAPSHOT_URL" --sha256 "YOUR_64_HEX_SHA256" --snapshot-date "2025-01-01" --output data/raw/20250101_aact.zip
# Extract the verified archive into a NEW directory, preserving the archive.
Expand-Archive -Path data/raw/20250101_aact.zip -DestinationPath data/raw/aact_20250101
python scripts/verify_aact.py --path data/raw/aact_20250101 --output data/processed/aact_20250101_checksums.json
python scripts/build_features.py --input data/raw/aact_20250101 --output data/processed/aact_20250101 --snapshot-date "2025-01-01"
# Subsequent checksum comparison detects changes to selected frozen source tables.
python scripts/verify_aact.py --path data/raw/aact_20250101 --expected data/processed/aact_20250101_checksums.json
```

The URL/hash values above are user-supplied placeholders, not working credentials or a claim that this snapshot was downloaded. A locally recorded hash provides future integrity checks; authenticity needs an independently trusted acquisition record. The download command checks HTTPS, expected SHA-256 and ZIP format, refuses overwrite, and records a URL with query parameters removed. It does not automate login or claim publisher verification. Flat-file extraction holds selected protocol fields in memory, so full snapshots need suitable RAM; ZIP extraction uses the operating system before feature extraction.

## Main experiment

`train_experiment(df, output_dir, source_metadata=None, config=...)` runs the same cohort and held-out splits for all models. It refuses fewer than 30 eligible completed trials and, after temporal purging, fewer than 12 training or three validation/test trials. These are software guards, not a power calculation or adequate evidence for publication. Existing experiment artifacts cannot be overwritten.

1. **Observed outcomes.** Require unique IDs, status `COMPLETED`, known day-level start and completion dates, and a positive interval. Completion must be `ACTUAL`, or a separately documented source guarantee must establish actual completion when the type field is absent. Estimated completion never supplies a duration label. Exclusions and reasons are saved.
2. **Temporal groups.** Sort whole unique UTC calendar-day start groups (timestamp hours never separate a day). Default cutoffs use 60%, 20%, 20% of date groups, not a random row split. Training outcomes must finish strictly before the validation cutoff. Validation outcomes must finish strictly before the test cutoff. Purged IDs and reasons are exported. The test period uses only observed completed outcomes in the frozen source.
3. **Target.** Duration is `(completion_date − start_date)` in days. The prolonged threshold is the training duration 75th percentile; positive labels require duration strictly above that threshold. Ties are negative. The same frozen threshold applies to validation and test.
4. **Inputs.** Whitelist enrollment, arm count, primary/secondary outcome counts, eligibility-line count, study type and phase; concatenate title, summary, description and eligibility text. IDs, statuses, dates and labels are excluded as features. Narrative leakage and post-start updates still require acquisition-level control.
5. **Train-only fitting.** Numeric medians and scaling, categorical vocabulary, TF-IDF vocabulary/IDF and research PCI scaling are fitted on training rows only. Missing or punctuation-only narratives receive a documented missing-text token. Negative/nonfinite numeric inputs become missing. Never pre-impute or normalize the full dataset.
6. **Models.** Two bounded structured nonlinear branches (64-tree Extra Trees and Random Forest) supplement the models below; see `V3_MODELS.md` for their validation-only tuning and global importance interpretation. Median duration and training-prevalence baseline; structured-only; TF-IDF-only; and structured + TF-IDF multimodal. The last three fit Ridge duration regression and logistic prolonged classification. Ridge alpha in `{1,10,100}` minimizes validation RMSE; logistic C in `{0.1,1,10}` minimizes validation Brier score. The selected pipeline remains trained only on the training split. There is no train+validation refit and no test-set selection. A one-class training target uses an explicit constant prevalence fallback.
7. **Evaluation.** Export validation and untouched test predictions and MAE/RMSE/R², AUROC, average precision, Brier score, ten-bin reliability information, expected calibration error and per-metric 95% bootstrap percentile intervals. Undefined discrimination in a one-class set and R² without target variation are JSON `null`; no invented fallback score is used. Bootstrap defaults to 200 paired per-trial draws with a fixed seed and reports valid resample counts. Intervals condition on the fitted model, assume independent trials, and exclude model fitting and clustered-sponsor/site uncertainty. Validation metrics are optimistic after tuning. Logistic probabilities are not post-hoc calibrated.

```powershell
python scripts/train_models.py --input data/processed/aact_20250101/trials.csv --metadata data/processed/aact_20250101/source_metadata.json --config configs/research.json --output artifacts/experiment_001
python scripts/evaluate_models.py --experiment artifacts/experiment_001 --output artifacts/experiment_001/recomputed_report.json
```

The manifest contains source metadata, canonical input digest, pipeline source digest, environment versions, configuration, membership IDs, cutoffs, threshold, model-selection rules and actual computed metrics. `models.joblib` includes fitted preprocessing, models and PCI state. `held_out_predictions.csv`, exclusion CSVs and `metrics.json` support independent inspection. `evaluate_models.py` recomputes saved predictions without fitting. A failure produces `error.json`; absent/incompatible models yield null predictions.

Joblib deserialization can execute Python. Use only artifacts generated and stored by this trusted local application; do not upload or load arbitrary model files. Prediction checks manifest/artifact run ID and source metadata consistency. The API additionally binds predictions to the active dataset's ID and checksum.

## PCI and explanations

Two explicitly distinct descriptive indexes are available:

- The UI's exploratory PCI uses fixed, documented component ceilings and configurable scenario weights. It is available for software fixtures. Missing fields contribute zero, so incomplete records can look artificially simple.
- The research experiment fits medians and min/max ranges for five numeric inputs on training only, clips to those ranges and gives equal weights. Constant training components contribute zero. This index is cohort-relative and is exported with predictions; it is not an extra outcome feature, a risk probability or a validated clinical score.

`build_pci.py --input ... --output ...` exports the UI index and a methodology sidecar. Add `--experiment artifacts/experiment_001` to use the fitted research index. The two scales have different component meanings and should not be compared as interchangeable values.

The default explanation is an exact linear decomposition: transformed feature value times fitted coefficient. Classification contributions are **log-odds**, with intercept and sum of all contributions; the top twelve are displayed. Duration contributions are days before nonnegative clipping. These values are not SHAP, percentage-point risk effects or causal effects. The optional SHAP adapter uses actual `shap.LinearExplainer` with an explicitly supplied original training background, and identifies its background size, method and units. No SHAP result is returned when the dependency or supported fitted model is absent.

## Optional BioBERT and survival

Install the optional dependency file described in the runbook before using these capabilities. The core pipeline does not download weights or claim these methods were executed.

**BioBERT:** `BioBERTEncoder` loads a selected model with an exact 40-character commit revision; a moving `main` revision is rejected. Defaults to local weights, CPU, frozen evaluation mode, batches of eight and 256 tokens. It performs attention-mask mean pooling without fine-tuning. Token truncation may lose protocol detail. `--allow-download` is an explicit opt-in to retrieving model files.

```powershell
python scripts/build_embeddings.py --input data/processed/aact_20250101/trials.csv --output artifacts/biobert_001 --model dmis-lab/biobert-base-cased-v1.2 --revision YOUR_EXACT_40_HEX_MODEL_COMMIT --allow-download
```

This writes actual embeddings, row IDs and a model/source manifest. It is a feature extraction capability; BioBERT training, comparison or superiority is not claimed by the default TF-IDF experiment. If using these frozen features in further research, align by ID and retain the same splits and train-only downstream fitting.

**Cox survival:** A separate analyst-curated CSV must contain `nct_id`, day-precise `start_date`, observed `followup_date`, binary `event_observed` and baseline numeric covariates. Event 1 means an observed endpoint at follow-up; event 0 means censoring at a documented last-observed date. Do not turn anticipated completion into follow-up or treat termination/withdrawal as independent censoring without an appropriate competing-risks design. Metadata must explain the event, censoring and follow-up ascertainment.

```powershell
python scripts/train_survival.py --input data/processed/curated_survival.csv --metadata data/processed/survival_metadata.json --cutoff "2020-01-01" --output artifacts/survival_001
```

Training events on or after the cutoff are administratively censored at that cutoff. Test trials start on/after it. A penalized Cox proportional-hazards model uses training-only imputation/scaling and drops training-constant numeric covariates. Outputs are relative completion hazards, test Harrell concordance (null if undefined), coefficients and serialized state. Higher hazard means earlier completion, not greater prolonged-duration probability. Independent censoring, endpoint consistency and proportional hazards need a separate substantive assessment. This analysis has a different cohort/estimand from completed-only regression, no automated tuning or confidence intervals, and must not be presented as a directly comparable classifier score.

## Scientific limits and next validation

The completed-only cohort excludes ongoing and discontinued studies and can introduce substantial follow-up and selection bias, especially in later start periods. Actual completion date is not the same as results posting date. A start-date split cannot repair a feature collected after that start date. Registry omissions and administrative changes can affect both descriptive PCI and targets. Sponsor/site/condition overlap may warrant additional grouped or external validation. Calibration, subgroup performance, sensitivity to the duration quantile, date precision and censoring all require a prespecified real-data study. This repository makes such analyses inspectable; it does not supply their conclusions.


## v3 phase and learning extension

The separate phase classifier removes the target field and explicit Arabic/Roman/word phase mentions, including punctuation and Unicode forms, from input features. It uses whole-day chronological train/validation/test groups, train-only preprocessing and validation macro-F1 tuning. See `PHASE_MODEL.md`. It is not a regulatory phase-assignment system. The independent `PHASE_ACADEMY.md` guide describes the primary-source conceptual animations and quiz.

## v4 scientific extension

See V4_MODELS.md and FORMULA_SPECIFICATION.md. Duration artifact version3 adds Gradient Boosting, independent calibration, split-conformal residual intervals, separately labeled sigmoid-calibrated probabilities when class support permits, and training-support flags. Exact decimal alpha determines the finite-sample conformal rank. Phase feature aliases (Roman/Arabic, pipe/slash combined labels) are normalized consistently for fitting and hypothetical queries; combined phases remain distinct from single phases. The Phase Model pipeline remains its separate artifact version1.
