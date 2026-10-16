# Model-quality implementation and frozen benchmark

No overall accuracy improvement is supported. The new tuning-selected duration branch improves held-out MAE slightly but worsens RMSE; risk predictions exactly reuse the existing text classifier. The candidate must remain opt-in, with no default artifact activation or accuracy-superiority claim.

## Changed files and integration

- `src/clinical_trial_intelligence/research.py`: default-false boolean `ExperimentConfig.enable_accuracy_models`, four model metadata entries, opt-in fitting before calibration/test evaluation, accurate unavailable-attribution handling, and opt-in helper source hash provenance.
- `src/clinical_trial_intelligence/models/accuracy.py`: deterministic CPU training-only estimators and pickle-safe selected-task wrapper; no new dependencies.
- `configs/research-accuracy.json`: explicit opt-in configuration; existing advanced branches and expanded CatBoost search enabled for the fair paired baseline.
- `tests/test_accuracy_models.py`: six focused checks of opt-in validation, cohort/old-prediction preservation, serialized inference replay, calibration/test mutation independence, training phase shrinkage/unseen fallback, one-class probabilities, unavailable calibration/attribution, missing evidence, and helper source provenance.
- Parent integration: forward `enable_accuracy_models` through request schemas, backend config construction, frontend opt-in controls and any explicit config allowlists. The normal default remains false. Only fitted manifest entries belong in the catalog.
- New IDs: `accuracy_mean`, `accuracy_phase_shrinkage`, `accuracy_log_structured`, `accuracy_task_selected`. Composite input_mode is `composite`; derive actual input requirements from its selected components. `selection.regressor_component` and `selection.classifier_component` record independent choices. Generic inference returns real fitted predictions, raw_probability and calibrated_probability separately; unavailable attribution has an empty features array and honest output units.
- The existing duration recommendation uses tuning RMSE, while risk recommendation uses raw tuning Brier. Any legacy registry selection using MAE must retain its default behavior; parent owns opt-in integration. Composite model-name tie-breaking can make the composite the risk recommendation even though its risk predictions exactly equal text.
- No backend/frontend/shared source, dependency lock, Docker file, original examples/data or approved artifact was edited by this task. No commits, installs, subagents or full-suite/build runs.

## Frozen fair protocol

`accuracy-frozen-protocol.json` was written before either new held-out benchmark result was inspected. The declared candidates/settings were not changed after reading test results. All fitted transforms/statistics see training only; all choice rules see the original tuning group only. The existing temporal purge, start-date groups, calibration reserve, labels, threshold and feature whitelist remain unchanged. No train refit on tuning/calibration, no random split, fabricated rows, date predictors, IDs or outcome predictors were added. New candidates use structured baseline-like variables; inherited text branches retain the existing retrospective-provenance warning.

1. Mean/prevalence: arithmetic training duration mean and training prolonged prevalence; no tuning.
2. Phase shrinkage: training phase duration means/prevalences shrunk with a fixed prior mass of 20 training-global pseudo-observations; unseen phases use training global means. No grid.
3. Log structured: training numeric median imputation, log1p nonnegative numeric values, training scaling, categorical one-hot encoding. Regression fits log1p(days), inverse expm1 with no smearing; Ridge alpha grid [10,100]. Risk uses logistic C [.1,1]. Select tasks separately using RMSE in days and raw Brier, first declared parameter wins exact ties. Chosen alpha100, C0.1. No local additive attribution in days is fabricated for inverse-log outputs.
4. Task composite: choose independent minimum tuning RMSE duration and minimum raw tuning Brier risk across all already fitted enabled candidates; model-name exact tie breaker; no new fitting or weights. This run selected log-structured duration and text risk.

The old-enabled run uses the identical configuration except `enable_accuracy_models=False`, including advanced trees and expanded CatBoost. The runner asserted identical retained split objects, target and input digest, then exact equality of every old branch held-out prediction row between runs. This controls implementation/cohort differences and exposes mixed generalization honestly.

Commands/artifacts:
```bash
.venv/bin/python scripts/train_models.py --input data/starter/trials.csv --metadata data/starter/metadata.json --config configs/research-accuracy.json --output results/new-accuracy-candidate
```
- Baseline artifact: `docs/v5204-evidence/accuracy-baseline (evaluation files)`.
- Candidate artifact: `docs/v5204-evidence/accuracy-benchmark (evaluation files)`.
- Full configuration/plan/hashes: `docs/v5204-evidence/accuracy-frozen-protocol.json`.
- Full exact numeric summary and retained IDs: `docs/v5204-evidence/accuracy-benchmark-summary.json`.

## Actual 800-record result

800 input records; 312 eligible; 488 excluded for unchanged eligibility rules; 123 temporally purged. Training105 (26 prolonged), tuning9 (0 prolonged), calibration11 (0 prolonged), test64 (6 prolonged). Training prolonged threshold1101 days. Validation cutoff2019-10-10; test cutoff2021-09-14. Source baseline provenance is false; these are retrospective convenience samples, not prospective validation.

| Model | Tuning RMSE days | Tuning raw Brier | Test MAE days | Test RMSE days | Test R² | Test raw Brier | Test AUROC |
|---|---:|---:|---:|---:|---:|---:|---:|
| median_baseline | 288.767688250915 | 0.061315192744 | 351.187500000000 | 419.229389773666 | -0.049625372540 | 0.108636621315 | 0.500000000000 |
| structured | 535.118679842240 | 0.071532295911 | 372.676784379647 | 432.383764137867 | -0.116528040458 | 0.119592899402 | 0.612068965517 |
| text | 445.861579418717 | 0.019658155297 | 314.700946205859 | 366.982336836915 | 0.195694197108 | 0.077569356655 | 0.807471264368 |
| multimodal | 458.544071495197 | 0.031926409548 | 332.998017527858 | 399.283242584801 | 0.047877022626 | 0.093413591838 | 0.761494252874 |
| structured_extra_trees | 520.323170080609 | 0.065202192281 | 354.218210015867 | 418.790404164045 | -0.047428345313 | 0.108817297358 | 0.670977011494 |
| structured_random_forest | 543.225842916991 | 0.074264539065 | 350.549950496000 | 428.373289424127 | -0.095911905377 | 0.112787161037 | 0.672413793103 |
| structured_gradient_boosting | 643.233101412137 | 0.124767024350 | 372.388791835394 | 491.098837985564 | -0.440352170819 | 0.134105854004 | 0.543103448276 |
| structured_hist_gradient_boosting | 647.589281842584 | 0.103200848408 | 447.139369893117 | 589.992694058499 | -1.078854749150 | 0.162656462478 | 0.574712643678 |
| multimodal_late_fusion | 466.315355265560 | 0.030206851980 | 317.130006985977 | 374.878032239875 | 0.160712293751 | 0.087705745362 | 0.755747126437 |
| structured_catboost | 583.608952151326 | 0.079273768842 | 350.237914916277 | 454.499269786444 | -0.233665040941 | 0.118060144274 | 0.698275862069 |
| accuracy_mean | 529.685337702082 | 0.061315192744 | 385.744642857143 | 440.035286808480 | -0.156394153003 | 0.108636621315 | 0.500000000000 |
| accuracy_phase_shrinkage | 512.172035101437 | 0.054503951956 | 359.325416227276 | 420.214320391246 | -0.054563111151 | 0.104841626958 | 0.663793103448 |
| accuracy_log_structured | 256.829375934575 | 0.087797451836 | 345.304547488668 | 428.893705865464 | -0.098576296578 | 0.124806253866 | 0.517241379310 |
| accuracy_task_selected | 256.829375934575 | 0.019658155297 | 345.304547488668 | 428.893705865464 | -0.098576296578 | 0.077569356655 | 0.807471264368 |

Old tuning-selected duration was median_baseline: RMSE419.229389773666 and MAE351.1875 days on test. New tuning-selected log duration: RMSE428.893705865464 and MAE345.304547488668. Model-minus-old deltas: RMSE +9.664316091798 days; MAE −5.882952511332 days. The paired 200-resample conditional 95% bootstrap MAE-delta interval is [−29.408825193987, +19.230931215627], crossing zero. This is not dependable improvement.

Old/new tuning-selected risk is the same text classifier (the new composite aliases it), with test Brier0.07756935665479858 and AUROC0.8074712643678161. There is no new risk gain. The composite improvement over a median/prevalence baseline reflects inherited text risk, not a new accuracy breakthrough. The existing text duration model scores better on test than the new duration selection, but was not selected by the frozen tuning RMSE rule; switching to it based on these test results would contaminate selection.

All tuning and calibration risk labels are zero. Risk ranking therefore has very weak support; sigmoid calibration is unavailable because calibration lacks both classes, even with11 rows. Raw probabilities remain available and are never silently described as calibrated. Nominal90% split-conformal duration coverage for the new composite is only56.25% (36/64) on the shifted test cohort; this explicitly fails a future-coverage interpretation. Small samples, conditional bootstrap intervals, completed-only selection, convenience sampling and narrative updates rule out clinical/prospective conclusions.

## Recovered 1800-record feasibility (no new fitting or score inspection)

`recovered-cohort-feasibility.json` records the exact IDs. Only source metadata, cohort eligibility, IDs and temporal availability were inspected; no recovered prediction or outcome-performance metric was computed. Source is an interrupted ClinicalTrials.gov convenience acquisition with missing strata, unknown original retrieval timestamps and false historical baseline provenance.

Recovered raw1800 IDs overlap the original800 by20 IDs. Only155 recovered rows pass unchanged actual/day-precision eligibility;1645 are excluded. Of eligible records,152 have IDs absent from all800 original records. Their start dates run2000-03-22 00:00:00 to2011-12-28 00:00:00. There are ZERO eligible nonoverlap records at/after the original2021-09-14 test cutoff, so this recovered source cannot supply a new temporal external test cohort.

139 nonoverlap eligible outcomes are already complete before the original2019-10-10 validation cutoff. A separately frozen future experiment could enlarge training from105 to244 rows without moving that cutoff; the other13 nonoverlap eligible outcomes are unavailable at that cutoff and must not be added. Such a study changes training composition and likely its duration threshold, so it is a separately labelled data-augmentation study, not the matched-cohort improvement above. The existing64-row test is now known and must not be reused to tune or justify promotion. Credible generalization needs a new untouched later cohort with verifiable baseline snapshots, sufficient observed outcomes and both prolonged-risk classes. No missing dates or values should be invented to inflate eligibility.

## Verification executed

- Initial red run: 3 intended failures because enable_accuracy_models was absent; missing-artifact test passed.
- `python -m pytest tests/test_accuracy_models.py tests/test_research.py tests/test_catboost_models.py -q`: 57 passed, 1 skipped in31.72s before two extra edge tests were added. The skip is optional SHAP (`pytest.importorskip("shap")`). Log: model-tests.log.
- Final focused `python -m pytest tests/test_accuracy_models.py -q`: 6 passed in3.8s (see accuracy-focused-tests.log for exact runtime). Includes helper hash and unavailable-attribution assertions.
- Python compileall on accuracy helper and test; git diff --check for research.py: passed. No changes under tracked examples/data in git diff.
- Tests require disposable PostgreSQL env even for model tests because root conftest enforces it; `/workspace/v5202-runtime.env` was silently sourced with export enabled. An initial invocation without export failed conftest and was corrected before the intentional red run.
- Benchmark runner completed both actual runs and exact legacy-prediction/cohort assertions with exit0. No full suite/build executed under delegated scope.

## Provenance hashes

`manifest.additional_model_source_sha256["models/accuracy.py"]` is present only as a populated dictionary for opt-in runs (empty for default). Main pipeline hash continues its existing meaning. Helper classes use importable module names and artifacts reload/replay successfully.
```json
{
  "frozen_source_hashes": {
    "src/clinical_trial_intelligence/research.py": "741cd27ebabbd7070799ce25000b0368d35f4a14c7f3bfccc8e1ff29e5edb527",
    "src/clinical_trial_intelligence/models/accuracy.py": "57f7fa2f945099fdb18c1e84c043c23f6afb4e48131df413e6461c282fbb6911",
    "data/starter/trials.csv": "d096795e303b5a103e0aba8bd79ffe7e85609827ea810d1c08e8e0811b5496d2",
    "data/starter/metadata.json": "558c4be24196136df64dd5609df226ef0cca2f43f595d6a048413f53c1c1b49c"
  },
  "candidate_additional_model_source_sha256": {
    "models/accuracy.py": "57f7fa2f945099fdb18c1e84c043c23f6afb4e48131df413e6461c282fbb6911"
  },
  "recovered_csv_sha256": "5c963d4b1b4faea165aad57c097b3608304e400673dd41854204740883433148"
}
```

## Exact retained split IDs

Identical in old and new experiment manifests; chronological order preserved.

### train: 105 rows

```text
NCT00006107
NCT00501020
NCT00480805
NCT00043823
NCT00092937
NCT00096551
NCT00398541
NCT00128102
NCT00679770
NCT00436956
NCT00589420
NCT00500760
NCT00541970
NCT00874874
NCT00678561
NCT00765973
NCT00857883
NCT00871351
NCT00976066
NCT00910624
NCT01004003
NCT01220856
NCT01176461
NCT01284920
NCT01351623
NCT01675297
NCT01640080
NCT01682759
NCT01709305
NCT01677780
NCT01755156
NCT01805453
NCT01850641
NCT02058576
NCT02007629
NCT02115373
NCT02224729
NCT02245256
NCT02152761
NCT02100423
NCT03340870
NCT02262026
NCT03462173
NCT02151682
NCT02517866
NCT02654054
NCT06082596
NCT04141241
NCT02603705
NCT02573012
NCT02735122
NCT03743896
NCT02800642
NCT02801071
NCT02671383
NCT02833545
NCT02896127
NCT02959983
NCT02967159
NCT02679573
NCT02982161
NCT02980042
NCT03005288
NCT03050151
NCT03036605
NCT04380324
NCT03127956
NCT03067727
NCT03096457
NCT03523988
NCT03139279
NCT03151720
NCT04089605
NCT03150082
NCT03257930
NCT03272425
NCT03418727
NCT03345979
NCT07223073
NCT03413020
NCT03372629
NCT03833570
NCT03406702
NCT03563846
NCT03070483
NCT03531229
NCT03531697
NCT03051256
NCT03798899
NCT03589066
NCT03551288
NCT03378323
NCT03496571
NCT03583346
NCT03466073
NCT03740659
NCT03664882
NCT03733561
NCT03729973
NCT03990480
NCT03817346
NCT05469113
NCT03910088
NCT03934203
NCT03977805
```

### validation: 9 rows

```text
NCT04091646
NCT05132270
NCT04235270
NCT05712642
NCT04282746
NCT04370262
NCT04542694
NCT04400682
NCT05821543
```

### calibration: 11 rows

```text
NCT04733001
NCT05244759
NCT04482270
NCT04745273
NCT04669262
NCT04686669
NCT04667156
NCT04680273
NCT05851027
NCT04712396
NCT04969497
```

### test: 64 rows

```text
NCT04892342
NCT04814381
NCT04922554
NCT04727970
NCT07343323
NCT05123196
NCT05184062
NCT04795427
NCT06232005
NCT06874140
NCT04924166
NCT05206370
NCT05059327
NCT05169671
NCT05299476
NCT05412446
NCT05878899
NCT05389696
NCT05362110
NCT05939622
NCT05335005
NCT05280496
NCT05387941
NCT05404724
NCT05327296
NCT06564961
NCT05448469
NCT05465460
NCT05491759
NCT05516953
NCT05515796
NCT05543369
NCT05546762
NCT05889351
NCT05594602
NCT05523141
NCT05559554
NCT07212946
NCT06494007
NCT05642923
NCT07077954
NCT05680870
NCT06486623
NCT07014631
NCT05905120
NCT05830799
NCT05883124
NCT05812417
NCT05834023
NCT05660954
NCT05901961
NCT05891262
NCT05864846
NCT05506488
NCT05968482
NCT05595369
NCT05891483
NCT05970354
NCT06086886
NCT06181370
NCT06148272
NCT06173466
NCT06218290
NCT05954962
```
