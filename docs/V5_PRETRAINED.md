# v5 saved research model registry and inference

## Immediate inference

The normal workflow is **upload/import → schema validation → approved saved model → predict → saved batch**. No training, preprocessing fit or recalibration runs at startup, import or inference. New records need not share the training dataset ID or hash. Each prediction retains the selected artifact version and digest and clearly distinguishes the query dataset from the training dataset.

`examples/approved-models-v5.json` is a trusted server release catalog. It names the two genuine, locally trained v5 starter artifacts and pins SHA-256 hashes of both their manifests and executable joblib files. The release uses the frozen authentic 800-record ClinicalTrials.gov starter. Its approval is permission to use a retrospective research artifact, **not clinical, regulatory or prospective validation**. Do not change or accept this catalog from an uploaded dataset. A missing, incompatible or changed artifact fails closed without training a replacement.

The saved duration experiment includes baseline, linear, tree and fusion branches. The inference registry selects the minimum finite **validation duration MAE**; it never examines test scores to select a branch. For the supplied release this selects `median_baseline`. Returning a constant baseline is intentional when it wins the stated validation objective; the interface must not describe it as an individualized biological or clinical forecast. The accompanying prolonged-duration probability is from that same branch and is not claimed to be the best risk classifier. The experiment manifest separately records risk-Brier and duration-RMSE recommendations for research comparison. Phase inference uses the manifest's validation-selected phase classifier; it predicts registry phase consistency, not clinical success or progression.

## API contract

All routes use the existing session and `X-Project-ID` access boundary. Local mode explicitly uses the offline local project. Dataset IDs, candidates and saved batches are project scoped.

| Route | Behavior |
|---|---|
| `GET /api/v5/models` | Returns `items`, `active: {duration,phase}`, and warnings. Reads manifests and hashes; does not deserialize models or fit anything. |
| `POST /api/v5/inference/batch` | Saves a real batch; returns HTTP 201. Body: `{dataset_id, model_id:"active", task:"duration", limit:100, mode:"retrospective"}`. Task may be `phase`; limit is 1–1000. |
| `GET /api/v5/inference?dataset_id=...` | Returns at most the newest 100 saved batches in the selected project, optionally filtered by dataset. |
| `GET /api/v5/inference/{id}` | Returns the exact persisted batch, including the inference-time model and data provenance. |
| `POST /api/v5/models/{id}/approve` | Owner only. Body: `{notes, research_only_acknowledged:true}`. Approves an eligible completed local experiment without changing the active model. |
| `POST /api/v5/models/{id}/activate` | Owner only. Body: `{notes}`. Atomically changes the active pointer to an approved model; selecting an older approved model performs rollback. |

A model item includes `id`, `name`, `task`, `branch`, `status`, `active`, `artifact_version`, `run_id`, `artifact_sha256`, `manifest_sha256`, `training_dataset`, `validation_metrics`, `test_metrics`, `selection`, `features`, `approval_scope`, `approval`, `gates`, and `warnings`. Unavailable models have a minimal item and a visible reason. Pending experiments never replace the active artifact.

Each saved batch contains `id`, `created_at`, `mode`, `model`, `dataset`, `items`, `summary`, and `warnings`. An item has `nct_id`, `status`, `prediction`, and `availability_warnings`. Available predictions are actual saved-model outputs with the existing duration/phase semantics, uncertainty status, cohort membership and explanation metadata. Nonlinear/global explanations may have no local feature contributions. Blocked pretrial rows contain `prediction:null`; unavailable outputs never substitute invented probabilities. Summary counts are `requested`, `available`, `blocked`, `unavailable`.

The `GET /api/v1` research views and existing duration/phase prediction routes use the same approved resolver when served by the v5 platform. Standalone legacy research workers retain their previous behavior for compatibility; the platform remains the public access boundary.

## Owner training and approval

Training is an independent owner workflow through the existing `/api/v1/experiments` and `/api/v1/phase-experiments` endpoints. A new experiment writes a new artifact folder. Training a candidate does not modify approval records or active pointers. Once training completes, its registry ID is `project-<experiment-id>`.

Approval requires a completed local run, compatible artifact version, matching registered training dataset ID and hash, nonfixture source metadata, valid pipeline/input hashes, and real finite validation/test task metrics with nonempty held-out splits. Optional mathematically undefined metrics such as single-class AUROC may remain null. The gate checks reproducibility and operational compatibility; it does not impose a performance threshold or establish clinical utility. The owner must review the actual metrics, cohort biases, temporal limitations and intended use before acknowledging research-only approval.

Approval pins the exact manifest and executable artifact digests in the metadata database, with owner ID, timestamp and notes. Activation is a separate persisted operation and audit event. To rollback, activate a previously approved model. A changed approved file is rejected; generate a new local experiment rather than replacing approved bytes. Uploaded joblib files, provider URLs and client-supplied model paths are unsupported.

The active pointer, approvals and batches use the same SQLAlchemy-backed platform database as project metadata. SQLite is an offline development option; production uses configured PostgreSQL. Model artifacts still require durable private filesystem/object storage as documented in the operating guide. Database persistence alone does not preserve model files.

## Schema and temporal availability

Imports undergo the existing scalar, finite numeric, identifier, date and duplicate validation. Inference additionally requires nonempty `nct_id` and `title` and observed inputs for the selected modality. Missing individual features use the already fitted training imputers, with availability warnings. Inputs with no meaningful structured values or protocol narrative are rejected rather than silently scoring empty records. Saved software fixtures cannot produce scientific inference.

`retrospective` is the default and is visibly labeled. Current registry snapshots can contain post-start changes. Held-out cohort membership describes how a training artifact used that identifier; it is not evidence that a newly uploaded row was prospectively validated. Out-of-distribution warnings and uncertainty are model diagnostics, not guarantees.

`pretrial` requires a valid per-row `prediction_as_of`, an exact day-level `start_date`, and `<feature>_available_at` for every observed feature used by the selected model modality. The cutoff must be no later than trial start, and every feature timestamp must be no later than the cutoff. Missing, invalid, partial-start-date or late availability evidence blocks the row. For example, an observed enrollment requires `enrollment_available_at`; observed title text requires `title_available_at` for a text or multimodal model. Missing feature values may still use training-only imputers. These checks enforce the submitted chronology; they do not independently verify the truth of user-supplied provenance, and they do not convert the retrospective starter model into a prospectively validated model.

## Internal integration

`app.state.model_registry` exposes:

- `list_models(project_id, dataset_registry)` and `resolve(project_id, dataset_registry, task="duration", model_id="active")`;
- `infer_rows(project_id, dataset_registry, rows, dataset, *, task="duration", model_id="active", mode="retrospective")`, returning the batch object without saving it;
- `save_batch(project_id, user_id, result)` for callers such as reviewed protocol workflows;
- `approve(...)` and `activate(...)`, which must only be called behind the owner access check.

The resolved internal object contains a trusted local `directory`, the complete `manifest`, selected `branch`, and the public `model`. Filesystem paths are not returned to the browser. The platform injects `dataset_registry.approved_model_resolver` into legacy duration and phase services.

## Verification

`tests/test_v5_inference.py` covers startup with fitting forbidden, new-dataset inference with fitting forbidden, genuine v5 release inference, query/training provenance, real explanation metadata, saved batch reproducibility, activation persistence, schema rejection, approval before serving, separate training continuity, rollback, checksum rejection before deserialization, pretrial timestamp blocking, role enforcement, project isolation, rejection of fixture/model-path uploads, task compatibility, and validation-only selection. Tests reuse existing genuine frozen artifacts; no artificial metrics are represented as scientific evidence.

Run from the v5 root: `.venv/bin/python -m pytest tests/test_v5_inference.py -q`. Full regression command: `.venv/bin/python -m pytest -q`.

The v5 batch endpoint permits owner, researcher and reviewer roles; viewers can read saved batches but cannot create one.
