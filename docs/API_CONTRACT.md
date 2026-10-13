# API contract (v4)

Base: `/api/v1`. All study/data requests accept `dataset_id`; omitted means `sample-fixture`, always labeled software-test data. Dataset selection is request-local. No API endpoint changes a shared active dataset. Optional `API_BEARER_TOKEN` protects all routes except health. Use `Authorization: Bearer ...` when configured. OpenAI and database credentials stay on the server.

| Method/path | Input | Response |
| --- | --- | --- |
| GET `/health` | — | `status,version,openai_configured,assistant_enabled,auth_required,database,configuration` (no secrets) |
| GET `/datasets` | — | `{items:[Dataset],active_default:"sample-fixture"}` |
| POST `/datasets/upload` | multipart `file` CSV/Parquet, optional `name` | Dataset (201); validation 422; size 413 |
| POST `/datasets/import/clinicaltrials` | `{query,max_studies:100,name?}` | Dataset (201); upstream failure 502 |
| GET `/studies` | `dataset_id,q,phase,status,sort_by,sort_dir,offset,limit` | `{items:[Study],total,offset,limit}` |
| GET `/studies/{nct_id}` | `dataset_id` | `{study,pci:{score,category,components,methodology},prediction}` |
| GET `/overview` | `dataset_id` | `{dataset,total_studies,median_pci,phase_counts,status_counts,enrollment_total,quality,predictions_available,pci_distribution,methodology}` |
| GET `/experiments` | optional `dataset_id` | `{items:[Experiment]}` |
| POST `/experiments` | `{dataset_id}` | Experiment (202), insufficient cohort 422, busy 409 |
| GET `/experiments/{id}` | — | Experiment with persisted status, metrics and manifest |
| POST `/predictions` | `{dataset_id,nct_id,model_name:"multimodal"}` | Prediction plus nct_id |
| POST `/assistant` | `{message,dataset_id,nct_id?,provider?}` | `{reply,provider,provider_id,model,fallback_used,attempted_providers}`; missing key/provider failure 503 |
| GET `/exports/studies.csv` | `dataset_id` | CSV download, formula-guarded cells |
| GET `/exports/studies.json` | `dataset_id` | JSON download with provenance |
| GET `/exports/report.html` | `dataset_id` | Escaped self-contained descriptive report |

Dataset: `id,name,row_count,source,created_at,sha256,is_fixture,columns,original_filename,provenance,quality`. Quality: `missingness:{column:count},warnings:[string],duplicate_ids,validation_errors,partial_date_values`. Counts in overview map labels to numbers. PCI distribution has up to 100 `{nct_id,title,pci}` records. List Study preserves canonical fields and adds `pci,complexity,prolonged_risk:null`; actual model inference happens in study detail.

Prediction: `status` available/unavailable, `probability` number/null, `duration_days` number/null, `model_name`, `explanation`, optional `reason`. No heuristic risk fallback. Artifact metadata must match the selected dataset ID and raw SHA-256. Only server-generated local experiment directories are accepted.

Experiment: `id,dataset_id,dataset_sha256,status` queued/running/completed/failed, `created_at,started_at?,completed_at?,error,metrics,manifest`. Poll GET after 202. The local API runs one bounded experiment at a time, at most 20,000 records by default. This in-process worker requires a single local server process; use one Uvicorn worker. Interrupted queued/running records become failed at server startup and can be retried as new experiments. Registry and immutable files persist under `STORAGE_DIR`; SQLite defaults there. Optional `DATABASE_URL` selects PostgreSQL metadata, while raw/canonical/artifact files remain in persistent server storage.

CSV/Parquet required columns: `nct_id,title`. CSV column names must be unique and each record must match the header width. Optional numeric fields: `enrollment,number_of_arms,primary_outcomes,secondary_outcomes,criteria_count,text_complexity` (finite, nonnegative). Date fields: `start_date,completion_date` (ISO YYYY-MM-DD, YYYY-MM, YYYY); Parquet date/timestamp values at midnight normalize to YYYY-MM-DD. Invalid/order-inverted dates fail atomically. Training requires completed actual outcomes (`status=COMPLETED,completion_date_type=ACTUAL`) and at least 30 eligible records; temporal partitioning and outcome-availability purging must leave at least 12 training and 3 validation/test records. Missing numeric/date components remain missing in canonical data; quality missingness counts are captured before categorical display defaults, and PCI explicitly reports its zero-contribution assumption.

Partial dates retain their interval uncertainty during upload date-order checks. Duration training excludes rows without exact day precision for both start and completion; missing days are never silently imputed into observed labels.

Assistant uses native OpenAI Responses (`store=False`), Gemini generateContent, Claude Messages or a configured compatible Chat Completions endpoint. All share bounded context/message/output and make no provider calls without a matching server key. Imported narrative text is treated as untrusted data. Exact raw upload bytes, SHA-256, canonical rows, validation warnings and source query/snapshot provenance are preserved.

Completed predictions additionally expose `prolonged_threshold_days`, `warning`, `cohort_membership` (train/validation/test/not_in_retained_splits) and readable `prediction_scope`. Training-record estimates are in-sample. Overview confirms a usable prediction rather than trusting artifact file presence. Corrupt/incompatible recent candidates fall back to older compatible local runs.


## Retained v3 endpoints

- `GET /api/v1/readiness?dataset_id=…`: safe duration/phase eligibility and split counts.
- `POST /api/v1/datasets/starter`: idempotently registers the bundled frozen real cohort.
- `POST /api/v1/phase-experiments`: `{"dataset_id":"…"}`; same lifecycle/shared training slot as duration.
- `POST /api/v1/phase-predictions`: `{"dataset_id":"…","nct_id":"…"}`; original label, predicted label, uncalibrated class probabilities and provenance.
- Experiment records include `task: duration | phase`. GET experiments returns both; clients filter by task.
- `POST /api/v1/predictions` model_name accepts recommended (default), median_baseline, structured, text, multimodal, structured_extra_trees and structured_random_forest.
- `GET /api/v1/experiments/{id}/files/{filename}` serves allowlisted JSON/CSV evidence for completed runs, with CSV formula escaping; binary model download is not exposed.
- Duration manifests now use artifact version 3 (v4 release). Phase artifacts retain their separate version 1 and filenames.

All new non-health routes use the configured shared bearer-token guard.


## v4 researcher endpoints and model semantics

- `GET /research/workspace?dataset_id=...&nct_id=...`: source study, fixed PCI with missing-field metadata, compatible duration/phase predictions, same-phase retrieval/context, explicit risk availability and source provenance.
- `GET /research/similar?dataset_id=...&nct_id=...&same_phase=true&limit=6`: TF-IDF cosine matches, self excluded and positive similarity only; limit 1–10.
- `POST /research/scenarios`: bounded protocol overrides and explicit planning assumptions; returns an immutable scenario with base/scenario outputs, exact planning arithmetic, provenance and SHA-256 digest. Source outcomes and identity cannot be overridden.
- `GET /research/scenarios?dataset_id=...&nct_id=...`: `{items,total,limit}` for matching current source fingerprints. History returns at most 100 rows.
- `GET /research/evidence?dataset_id=...&nct_id=...`: bounded `{workspace,scenarios,generated_at,scope,evidence_sha256}` JSON packet. The digest omits only its own top-level digest field.

All paths above are relative to `/api/v1` and share the optional bearer guard. Exact request bounds and response fields are in `V4_RESEARCHER.md`, `schemas_v4.py`, and the generated `/docs` OpenAPI page. Invalid nonfinite input is rejected without reflecting NaN/Infinity into a JSON error response.

Duration `model_name` also accepts `structured_gradient_boosting`. Duration `probability`, `raw_probability`, primary metrics and recommendation use raw model scores; `calibrated_probability` is separate and nullable. Uncertainty includes finite-sample residual intervals, support/fallback reasons and descriptive test coverage. `splits.validation` is tuning; `splits.calibration` is an independent reserved calibration subset. Cohort membership can now also be `calibration`. These are retrospective split roles, not an online/prospective simulation. See `V4_MODELS.md`.


## v4.0.1 assistant routing

Assistant provider may be auto, openai, anthropic, gemini or compatible; omitted uses AI_PROVIDER. Auto tries configured providers in AI_PROVIDER_PRIORITY; eligible access/network/quota failures may fall back when AI_AUTO_FALLBACK=true. Explicit provider selection never switches. The response names the actual provider/model and attempted provider IDs. Health adds assistant routing status and sets assistant_enabled for the server-selected configuration across providers; openai_configured remains a legacy OpenAI-only presence flag. These are configuration indicators, not live authentication results. See AI_PROVIDERS.md for exact protocols and failure behavior.
