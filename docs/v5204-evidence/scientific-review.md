# Independent scientific and security review — v5.2.0.4

Reviewed the uncommitted working tree against `fef38ca`, including new files that do not appear in ordinary `git diff`. Scope: accuracy candidates, research training/inference integration, model analysis/report exports/API, project/token forwarding, composite inference and downstream visualization metadata. No source edits, commits, full-suite run, or new benchmark/model training were performed.

## Important finding

### I1 — The selected-task model is displayed as having no feature branches, despite consuming structured and text features

Locations: `backend/app/services/visualization_service.py:35`–47 (integration point for newly added `input_mode='composite'` in `src/clinical_trial_intelligence/research.py:58`); misleading user-facing fallback at `frontend/src/components/animations/guidedEvidence.ts:32`.

The new `accuracy_task_selected` prediction correctly exposes each task's selected component through its explanations, and `_input_mode()` correctly resolves the union for saved inference. The visualization adapter does not resolve composite components: it accepts the new static metadata, marks fusion `available`, but only populates branches for `structured`, `text`, or `multimodal`. Consequently, the main new candidate is represented with empty branches/components, and the guided explanation says: “No supported feature branches are supplied; a constant baseline does not use feature encoders.” This is false for the real frozen candidate, whose duration predictor uses log-transformed structured features and whose risk predictor uses TF-IDF text. Absence of an additive duration explanation is also propagated as the architectural combination method, conflating unavailable attribution with the actual task-selection mechanism.

Reproduction (executed successfully using the existing artifact, no fitting):

```python
import json
from pathlib import Path
import pandas as pd
from src.clinical_trial_intelligence.research import predict_trial
from backend.app.services.visualization_service import study_visualization

folder = Path('docs/v5204-evidence/accuracy-benchmark (evaluation files)')
manifest = json.loads((folder / 'manifest.json').read_text())
frame = pd.read_csv('data/starter/trials.csv')
row = frame.loc[frame.nct_id == 'NCT04892342'].iloc[0].to_dict()
prediction = predict_trial(row, folder, 'accuracy_task_selected')
packet = study_visualization({'study': row, 'duration': prediction, 'provenance': {}})
print(manifest['models']['accuracy_task_selected']['selection']['regressor_component'])
print(manifest['models']['accuracy_task_selected']['selection']['classifier_component'])
print(packet['fusion'])
```

Observed selections: `accuracy_log_structured` / `text`. Prediction status: `available`. Fusion output: `status='available', input_mode='composite', family='task_selection', method='local attribution unavailable', branches=[], components=[], reason=None`.

Fix: pass actual selected regressor/classifier component metadata to the visualization packet, resolve their input requirements, and describe independent task selection as the architecture. Continue showing unavailable local attribution honestly. Do not invent fusion weights: these are two independently selected tasks, not a weighted ensemble. A small regression test should exercise this real shape and assert that a nonconstant composite is not rendered with the constant-baseline fallback. Also ensure the new phase-shrinkage branch is described as training phase statistics rather than numeric scaling/categorical encoding, which it does not perform.

## Minor observations

- `model_analysis.py:230`–272: duration reports provide overall split metrics but omit duration/risk subgroups by phase. Existing duration CSVs lack phase, so omitting rather than copying unchecked `by_phase` aggregates is appropriate; explicitly state that subgroup evidence is unavailable from these stored prediction columns. This is a completeness limitation, not incorrect arithmetic. New experiment formats may retain a verified phase column in future; do not change legacy artifacts.
- The report's selected-model metadata names recommendations but does not include the new composite's individual component selection details or helper source hash. This limits reproducibility detail without changing computed scores; including these manifest fields would improve the report.

## Verified / no actionable defect found

- New fitting is opt-in by default (`False`), trained preprocessing sees training data only, and task selection uses original tuning RMSE/raw Brier only. Calibration/test enter after component selection. The code and frozen benchmark notes support no general accuracy gain, and no default approved-artifact activation was added.
- Existing baseline model candidates and default registry MAE selection remain intact; opt-in registry branch selection intentionally uses the independent selected-task composite.
- Selected-task inference delegates to saved estimators. The actual frozen candidate replay succeeded and returned the correct selected duration component with honest unavailable output-unit attribution. No fitted values or prediction metrics were invented.
- Report metrics are recomputed from stored prediction rows without joblib loading; membership, target consistency, raw/calibrated separation, finite values and phase probabilities are checked. Phase macro conventions, binary one-class handling, duration day errors and R² were inspected.
- Report HTML text/SVG labels are escaped; CSV formula prefixes are guarded. The new routes attach the existing token dependency. Platform `/api/v1` gateway supplies project membership/verified-email scoping; project experiment paths and trusted bundle paths are constrained, and internal report filenames cannot escape the directory.
- `enable_accuracy_models` is carried through frontend request, request schema, experiment record and backend config.

Executed verification:

```text
.venv/bin/python -m pytest --confcutdir=tests/model_analysis tests/model_analysis -q
21 passed in 1.16s
```

The tests include both bundled model report formats without deserialization, arithmetic, one-class cases, tampered/missing evidence, pairing restrictions, escaping and output safety. This review does not replace the parent’s project/session API integration, browser, Docker and full validation work.

## Fix verification addendum

**I1 resolved.** Re-reviewed the targeted visualization adapter, guided fallback and report metadata changes. Re-ran the exact saved-artifact reproduction above using `NCT04892342`; no fitting was performed.

Observed and asserted:

- Fusion is available with both actual structured/log1p and TF-IDF narrative branches.
- `task_components` identifies duration → `accuracy_log_structured`, risk → `text`.
- Architecture method is `Independent tuning-selected duration and risk branches`.
- `components` remains empty; no ensemble weights are fabricated.
- Duration attribution remains explicitly unavailable in the separate explanation packet.
- Phase-shrinkage visualization code now specifies only `phase` and training phase statistics.
- Nonbaseline missing architecture metadata no longer triggers the constant-baseline fallback.
- Recomputed actual candidate report includes helper source hashes, selected component metadata, and an explicit duration-by-phase evidence limitation.

No remaining Critical/Important issue found in these targeted fixes. Inspected the three targeted architecture tests; parent reports those tests passed and the related integration suite passed (not rerun here). The real-artifact assertions and report checks above were independently executed and passed.

Minor optional wording polish: the last guided fusion step still says saved component “weights and predictions below provide the numerical evidence” for every architecture; a composite has no weights. The preceding method now correctly describes independent tasks, so this is no longer the Important misrepresentation above, but conditional wording would make the explanation fully consistent. The duration-subgroup limitation is also emitted in phase-only reports, where it is irrelevant; it can be conditioned on task in a future cleanup.
