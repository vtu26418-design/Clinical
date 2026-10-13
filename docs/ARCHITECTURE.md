# Application architecture

## Runtime

React + TypeScript + Vite compiles to `frontend/dist`. FastAPI serves the compiled interface at `/` and JSON routes at `/api/v1`. Hash navigation needs no rewrite rules. In frontend development, Vite proxies `/api` to port 8000.

Dataset imports are validated before persistence. Each dataset has immutable raw bytes, a canonical CSV, a SHA-256 fingerprint, provenance and a quality report. SQLite stores registry metadata by default. SQLAlchemy supports optional PostgreSQL/Neon metadata; data files and models remain on disk.

A bounded single-process worker launches one experiment at a time. Jobs are persisted as queued/running/completed/failed. Restarted jobs are marked failed rather than silently resumed. This is not a durable distributed queue.

## Module map

| Path | Responsibility |
|---|---|
| `backend/app/main.py` | API, auth dependency, experiment lifecycle, exports, static UI |
| `backend/app/services/data_service.py` | Canonical validation and dataset registry |
| `backend/app/services/clinicaltrials_service.py` | Bounded, paginated ClinicalTrials.gov v2 ingestion |
| `backend/app/services/pci_service.py` | Fixed-reference descriptive PCI |
| `backend/app/services/prediction_service.py` | Trusted artifact matching and prediction fallback |
| `backend/app/services/assistant_service.py` | Native OpenAI/Gemini/Claude and compatible-service routing, bounded prompts, safe fallback and metadata |
| `backend/app/services/openai_service.py` | Legacy OpenAI-only compatibility wrapper |
| `src/clinical_trial_intelligence/research.py` | Cohort, temporal splits, fitting, evaluation, diagnostics and linear/global tree explanations |
| `src/clinical_trial_intelligence/phase_model.py` | Separate multiclass phase task and trusted artifacts |
| `backend/app/services/phase_service.py` | Dataset/task matching for phase predictions |
| `backend/app/services/training_preflight.py` | Shared readiness guards |
| `src/.../ingestion/aact.py` | Frozen AACT flat-file verification and one-row-per-trial extraction |
| `src/.../nlp/biobert.py` | Optional pinned frozen embeddings |
| `src/.../models/survival.py` | Optional explicitly curated Cox survival experiment |
| `src/.../explainability/shap_adapter.py` | Optional real SHAP adapter |
| `frontend/src/components` | Eight research and learning screens and shared controls |
| `tests` | API, validation, training, temporal leakage and software-fixture tests |

## Research boundary

The baseline training comparison is structured-only, TF-IDF-only and concatenated multimodal (structured + TF-IDF), with Ridge duration regression and logistic prolonged-duration classification, plus median/prevalence baselines. BioBERT extraction and Cox survival are separate optional scripts; no neural fusion predictor is claimed.

Preprocessing and research PCI normalization fit only on training records. Validation selects hyperparameters. The final test set does not select models. Retrospective snapshots still cannot prove availability of features at trial start; manifests and UI warn about that limitation.

Only artifacts generated under the local experiments directory can be loaded through the API. Dataset IDs and checksums must agree. Joblib is executable serialization: protect the server filesystem and never introduce untrusted model artifacts.

## Extension boundaries

- AI providers: native OpenAI/Gemini/Claude plus configurable Chat Completions compatibility; new protocols still require adapters. See AI_PROVIDERS.md.
- Larger experiments: replace the in-process worker with a durable queue, retaining immutable inputs and manifests.
- Multi-user hosting: add identity, per-dataset authorization, quotas, object storage and migrations.
- Vercel: use for the static fixture demo or frontend. The supplied persistent Python backend needs a suitable long-running host.
- GitHub CI: tests Python on Linux and Windows and builds the frontend. No deployment secrets or production push are configured.

## v4 research workspace

`backend/app/v4_routes.py` attaches authenticated `/api/v1/research` routes before the static frontend. `research_workspace.py` owns bounded TF-IDF retrieval and immutable source-bound scenario/evidence records; scenario payloads are stored in the same SQLite/Postgres metadata registry. `configs/formulas.json` is shared by Python and TypeScript fixed-reference PCI. Four new screens compose around the existing dataset context. Preview workspaces are generated through the real service by `scripts/build_demo_research.py`; static scenarios use the shared browser formulas and remain in page memory. The full local API persists scenario history.
