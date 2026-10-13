# CTI v5 model card

## Release scope

The bundled frozen artifacts support immediate research inference on compatible uploaded or imported trial features. Uploading a new dataset does not fit or change these models. `examples/approved-models-v5.json` pins each artifact and manifest SHA-256; its approval is a software release decision for research use, not clinical, regulatory or independent scientific certification.

The v4 directory remains separate. v5 retains all seven duration/risk candidates and adds structured histogram gradient boosting and a text/structured late-fusion candidate. Added capacity did not consistently improve this small retrospective benchmark. The duration recommendation remains the training-median baseline because selection uses tuning data, even though other branches have lower errors on the later test cohort.

## Actual data and execution

| Dataset or operation | Observed result |
|---|---|
| Bundled authentic source | 800 ClinicalTrials.gov API v2 records, retrieved 2026-10-07; `data/starter/metadata.json` and raw response hashes |
| Duration cohort | 312 eligible, 488 excluded, 123 additionally purged by outcome-availability cutoffs |
| Duration retained splits | 105 training / 9 tuning / 11 calibration / 64 untouched test |
| Phase cohort | 291 eligible single-phase labels, 509 excluded; 175 training / 57 tuning / 59 test |
| Initial larger acquisition | Requested at most 4,000; preserved 18 pages / 1,800 real records before interruption |
| Second larger acquisition | Requested at most 4,000; preserved 15 pages / 1,500 real records before interruption; overlaps the first attempt |
| Recovered partial dataset | 1,800 records in `data/clinicaltrials-v5-recovered`; 156 have exact start and ACTUAL completion date pairs |
| Unique IDs across starter + recovered partial | 2580; this is a source inventory, not the model training count |
| Optional neural and survival fits | Not executed; no frozen BioBERT weights or suitable observed censored follow-up cohort supplied |

The recovered partial acquisition contains 1,000 starts from 2000–2005 and 800 from 2006–2011; later requested strata are missing. It was not used for the approved artifacts. Most preserved older registry dates have month-level precision; increasing raw counts therefore did not establish a larger eligible duration benchmark. No missing dates, labels, strata or trial records were invented.

The attempts were bounded at 240 and 600 seconds and interrupted before manifest finalization. Their final process exit status and original retrieval timestamps were not preserved; this is not reported as a proven HTTP/network denial. Per-page checksums and exact counts are recorded in each acquisition directory’s `ACQUISITION_INTERRUPTED.json` and `examples/v5-evidence/model-verification.json`. Recovery timestamps describe recovery only; unknown original retrieval timestamps remain null.

Duration fitting completed in approximately 8.83 seconds from cohort-file write to final manifest with native numerical threads limited to one. Phase fitting completed in approximately 29.03 seconds by the same file-time measure during concurrent work. These are local observed intervals, not hardware-normalized benchmarks or total download/install times. Core environment: Python 3.12.14, pandas 2.2.3, NumPy 2.3.5, scikit-learn 1.8.0, joblib 1.5.3; CPU execution, no neural/GPU training.

## Endpoint, inputs and leakage boundaries

Duration means known actual completion minus start date in days, restricted to completed trials with day-precision dates and positive durations. Prolonged duration means greater than the training cohort’s 75th percentile: 1,101 days. This is not delay relative to an original planned completion date, clinical success, enrollment success or regulatory approval probability.

The numeric whitelist is enrollment, number of arms, primary outcomes, secondary outcomes and criteria count. Categories are study type and normalized phase. Text combines title, brief summary, detailed description and eligibility criteria. Identifiers, statuses, outcome dates and derived outcomes are excluded from predictors. Median imputation, scaling, category levels, TF-IDF vocabulary, PCI ranges and distribution warnings are learned only from training rows.

Whole start-date groups are separated chronologically. Training outcomes must be available before the original validation cutoff; validation outcomes must be available before test. Earlier retained validation groups tune hyperparameters and fusion weights; later groups calibrate when at least ten rows are available. Neither tuning nor calibration rows refit the base models. Test labels are used only for evaluation.

All source records are latest registry snapshots. Feature timestamps and as-of provenance were not established. Excluding explicit outcomes cannot prevent indirect leakage from post-start text or registry updates. Row-level feature_timestamp <= prediction_timestamp certification is unavailable; these artifacts are retrospective and cannot claim prospective pretrial validity.

## Candidates and selection

- The four original candidates are median/prevalence baseline, structured Ridge/logistic, text TF-IDF Ridge/logistic, and concatenated structured+TF-IDF Ridge/logistic.
- Existing nonlinear candidates are Extra Trees, Random Forest and conventional Gradient Boosting, fitted on structured inputs.
- New histogram gradient boosting uses 100 iterations, at most 15 leaf nodes, learning rate 0.05, L2 regularization 1 and tuning-selected minimum leaf size 2 or 5. Dense preprocessing is limited to structured inputs. Internal randomized early stopping is disabled; chronological tuning remains the selection boundary.
- New late fusion combines the already fitted histogram structured branch and text linear branch. Structured weights 0.25, 0.50 and 0.75 are evaluated separately for duration and classification on tuning only. It is a convex blend, not deep learning or stacking trained on test predictions.
- Risk recommendation: lowest raw tuning Brier score, here `text`. Duration recommendation: lowest tuning RMSE, here `median_baseline`. Ties use model name. A single-branch response contains that branch’s two predictions; a risk-selected branch is not automatically the duration-selected branch.

## Untouched duration test results

Test n=64, with six prolonged outcomes. All candidates use the same retained rows, endpoints and splits. Lower MAE, RMSE and Brier are better. This table reports observed results, without selecting a new model based on the test scores.

| Candidate | MAE (days) | RMSE (days) | AUROC | Brier |
|---|---:|---:|---:|---:|
| Median / prevalence baseline | 351.19 | 419.23 | 0.5000 | 0.10864 |
| Structured linear | 372.68 | 432.38 | 0.6121 | 0.11959 |
| Text linear (TF-IDF) | 314.70 | 366.98 | 0.8075 | 0.07757 |
| Multimodal linear | 333.00 | 399.28 | 0.7615 | 0.09341 |
| Structured Extra Trees | 354.22 | 418.79 | 0.6710 | 0.10882 |
| Structured Random Forest | 350.55 | 428.37 | 0.6724 | 0.11279 |
| Structured Gradient Boosting | 372.39 | 491.10 | 0.5431 | 0.13411 |
| Structured Histogram Boosting | 447.14 | 589.99 | 0.5747 | 0.16266 |
| Text + Histogram Boosting Fusion | 317.13 | 374.88 | 0.7557 | 0.08771 |

## Uncertainty and paired comparisons

The test metrics include 95% percentile intervals from 200 paired per-trial bootstrap resamples with seed 42. The same sampled trials supply candidate and baseline losses in each comparison. Negative model-minus-baseline loss differences favor the candidate. These intervals condition on the fitted models, assume independent trials, omit model-fitting uncertainty and sponsor/site clustering, and do not adjust for comparing multiple branches.

| Candidate vs baseline | MAE difference, days (95% interval) | Brier difference (95% interval) |
|---|---:|---:|
| Text linear (TF-IDF) | -36.49 (-93.52, 23.50) | -0.03107 (-0.04296, -0.01646) |
| Structured Histogram Boosting | 95.95 (12.05, 209.48) | 0.05402 (0.01069, 0.09861) |
| Text + Histogram Boosting Fusion | -34.06 (-102.01, 31.01) | -0.02093 (-0.03298, -0.00699) |

Text-model test AUROC is 0.8075 with bootstrap interval 0.5976–0.9626; raw Brier is 0.07757 with interval 0.04195–0.11592. A nine-row tuning set, six positive test labels and unverified narrative baseline availability sharply limit interpretation. New histogram boosting has worse observed errors than the baseline here; the added branch is not presented as more accurate.

Split-conformal duration residuals use the independent 11-row calibration split at nominal 90% coverage. For the text branch the residual radius is 783.82 days; observed test coverage is 63/64 (98.44%) and mean interval width is 1,440.22 days after nonnegative lower-bound clipping. These broad intervals reflect limited precision. Exchangeability under temporal shift is not established; observed coverage does not guarantee future or individual coverage. Finite-sample ranks beyond calibration size are explicitly unbounded, with null interval bounds.

Primary classification probabilities remain raw. Separate sigmoid calibration is available only with at least ten reserved calibration rows and two outcomes of each class. Inspect per-model calibration status; calibration-fitting diagnostics are not independent validation.

## Distribution and explanation behavior

New inputs are compared with training numeric min/max, central 98% marginal ranges, known categorical levels, and narrative character-length ranges. Flags are descriptive warnings rather than OOD probabilities or input-validity guarantees. The marginal tail rules are heuristic and not multiplicity adjusted; text length does not detect semantic novelty. Missing numeric features are disclosed. The manual cross-dataset check uses a new identifier and out-of-range values and verifies warnings without refitting.

Linear feature contributions and global tree impurity importances retain their existing meanings. Histogram boosting reports local attribution unavailable. Fusion reports actual component predictions and fitted weights, not fabricated feature attributions. SHAP and causal claims are not substituted.

## Phase model

The separate registry-phase consistency classifier excludes phase itself from predictors and masks direct phase-label terms in text. The untouched 59-row test yields logistic accuracy 0.5593, macro-F1 0.4752 and balanced accuracy 0.4818; the majority baseline has accuracy 0.3729 and macro-F1 0.1358. EARLY_PHASE1 has no test examples. Indirect narrative cues and latest-snapshot leakage remain possible. Outputs are uncalibrated registry-label probabilities, not clinical success probabilities or a recommended regulatory phase. No phase confidence intervals or clinical validation are claimed.

## Reproduction and scaling

Install the pinned core dependencies, then run from the repository root in a fresh output location:

```bash
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python scripts/download_starter_data.py --replay-from data/starter --output-dir data/starter-replayed
python scripts/train_models.py --input data/starter/trials.csv --metadata data/starter/metadata.json --config configs/research.json --output examples/duration-reproduced
python scripts/train_phase_model.py --input data/starter/trials.csv --metadata data/starter/metadata.json --output examples/phase-reproduced
python scripts/download_starter_data.py --per-period 1000 --output-dir data/new-registry-acquisition
python scripts/recover_registry_acquisition.py --source data/clinicaltrials-v5-acquisition --output data/recovery-reproduced --requested-per-period 1000
python -m pytest tests/test_research.py tests/test_v5_models.py tests/test_v5_acquisition.py tests/test_phase_model.py tests/test_starter_download.py -q
```

Live API acquisition is a new changing convenience sample; exact replay requires preserved source pages. A larger production research effort should supply curated as-of baseline features, sufficient outcome follow-up, external or historical validation cohorts and censored endpoint ascertainment. The completed-only starter must not be converted into a survival cohort by inventing censoring dates.

Optional frozen biomedical embeddings are implemented by `scripts/build_embeddings.py` and `src/clinical_trial_intelligence/nlp/biobert.py`. Install `requirements-research.txt`, supply a verified exact 40-character upstream model revision and cached weights, or explicitly allow downloading. This extracts attention-mask mean-pooled frozen embeddings with a 256-token truncation cap; it does not fine-tune a deep clinical model or connect embeddings to the approved duration pipeline.

Optional survival analysis is implemented by `scripts/train_survival.py` and `src/clinical_trial_intelligence/models/survival.py`. It requires curated `nct_id,start_date,followup_date,event_observed`, baseline numeric features, a temporal cutoff and metadata defining endpoint, censoring and follow-up ascertainment. Training administratively censors at the cutoff; test evaluation reports concordance for completion hazard. Termination may be a competing event. Survival curves, P25/P50/P75/P90 calibration and reliable censored clinical deployment are not delivered by the completed-only artifacts.

## Verification and authoritative references

- Model/research/phase/source tests: 98 passed, one skipped in 22.11 seconds. The skip is the optional lifelines fit check when the dependency is unavailable. New acquisition recovery/replay test: one passed in 0.77 seconds. Full application-suite verification is recorded separately by the release workflow.
- Tests mutate test outcomes and input extremes to ensure fitted preprocessing, selected branches, fusion weights, calibration and conformal quantiles do not change. Tests validate bootstrap pairings, zero-resample null intervals, dense structured preprocessing, one-class handling and cross-dataset warning semantics.
- Artifacts, predictions, cohort exclusions, split membership, metrics and provenance are retained under `examples/starter-duration-v5` and `examples/starter-phase-v5`. Release digests are in `examples/approved-models-v5.json`.
- ClinicalTrials.gov API documentation: https://clinicaltrials.gov/data-api/api
- scikit-learn Histogram Gradient Boosting reference: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html
- scikit-learn ensemble methods and resource behavior: https://scikit-learn.org/stable/modules/ensemble.html
- Split-conformal finite-sample framework: https://arxiv.org/abs/2107.07511

PCI remains the explicitly labelled existing five-feature descriptive training-relative index. The seven-domain protocol-complexity construct, amendment probability, delay-vs-original-plan labels, recruitment success models, external validation and row-level prospective provenance certification remain separate work requiring appropriate data and validation.
