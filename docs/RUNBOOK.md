# Start-to-finish operating guide · v4

The complete full PDF manual is `Clinical-Trial-Intelligence-v4-Full-Guide.pdf`; its editable source is `V4_FULL_GUIDE.md`. It includes acceptance checks for all 12 screens. New workflows are detailed in `V4_RESEARCHER.md`.

## 1. Install and launch

Use Python 3.12 (64 bit). Allow several GB for dependencies and more for real datasets. Start with a modest cohort; laptop RAM and experiment time scale with cohort size and text vocabulary.

Windows: extract the ZIP, run `SETUP_WINDOWS.bat`, then `START_WINDOWS.bat`. macOS/Linux: run `bash setup.sh`, then `bash start.sh`. Go to http://127.0.0.1:8000. Keep the terminal open. Setup downloads Python dependencies; the frontend is already built in the ZIP.

The first launch creates `data/workbench/` and registers `data/sample/trials.csv`. Raw imported files are preserved in each dataset folder. Restarting retains datasets and experiment history. Jobs interrupted by a restart are marked failed and can be rerun.

## 2. Learn the workspace with fixtures

Open **Study Explorer**, type part of an ID/title, apply a phase filter, select two rows and press **Compare**. Click a study ID for its descriptive PCI and source fields. In **Complexity Lab**, vary enrollment or weights and export a scenario. These adjustments never mutate the source record.

The sample has five synthetic software-test records. It cannot train a research model. An unavailable prediction is intentional, not an installation error.

## 3. Import your real cohort

For a first complete workflow, click **Data Manager → Load starter cohort**. This registers the 800 bundled real records without a network request, retains their acquisition provenance, and selects them. Repeating the action selects the same starter dataset. Read `STARTER_DATA.md` for sampling and precision limits.

For your own data, download the CSV template in **Data Manager**. Supply one row per unique `nct_id` with a title. Preserve missing values as blank; do not fabricate dates or counts. CSV and Parquet are supported. Validation is atomic: malformed imports are refused without registering partial datasets.

Alternatively, use **ClinicalTrials.gov** search in Data Manager, choose a limit (50–1000) and import. This makes a real network request. Registries can be unavailable or rate-limited; errors are shown without substituting sample records. Imported snapshots are retrospective and may contain post-start updates.

Select the imported dataset at the top right. Check row count, missingness and field values. The UI study selector in Complexity Lab and Assistant loads the first 100 records plus records opened in Explorer. Explorer itself has pagination for the full cohort.

## 4. Run an experiment

Go to **Experiments → Run experiment**. The software requires at least 30 completed eligible studies, full start/completion dates and ACTUAL completion, and at least 12/3/3 records in train/validation/test after outcome purging. Long trials and narrowly spaced dates can leave too few records even in a large input. Improve the cohort rather than bypassing the guard.

Wait for status **completed**. The page polls every five seconds. Review test metrics, warnings, split cutoffs and IDs. Undefined classification metrics appear as a dash, not zero. Download the manifest. Full files are under `data/workbench/experiments/<run-id>/` including `models.joblib`, `manifest.json`, `metrics.json`, held-out predictions and exclusions.

The median/prevalence baseline, structured-only, TF-IDF-only, combined linear, Extra Trees, Random Forest and Gradient Boosting pairs use the same temporal holdout. The raw tuning Brier recommendation is for prolonged risk, not necessarily the best duration regressor. Click a model to inspect scatter/reliability charts and test errors by phase. Model choices use the tuning partition; later reserved calibration rows fit supported uncertainty/calibration, and test performance never selects models. “Prolonged” means above the training cohort's 75th percentile duration. Read RESEARCH_METHODS before interpreting results.

Open a study again to inspect a prediction; or use **Experiments → Compare a study prediction** to choose a specific model. Linear contributions are local; tree impurity importance is global. Predictions on training records are in-sample; use held-out aggregate metrics for evaluation. Raw joblib/pickle artifacts execute Python when loaded: load only your own locally generated artifacts, never downloaded/untrusted models.

## 4a. Understand and model clinical phases

**Phase Academy** works without data or a key. Select optional Phase 0 or I–IV. Use Play/Pause, Step, speed and Reset; arrows/Home/End navigate the stage tabs. Reduced-motion preferences disable autoplay. These are conceptual study diagrams, not real patient outcomes. Complete the five-question quiz or reset it.

**Phase Model → Train phase model** creates a separate supervised experiment. It needs 40 eligible records, exact start dates, single supported phase labels, 20/5/5 split rows and at least two training classes. It excludes combined/NA/unknown phases; phase field and explicit phase mentions are removed from model inputs. No completion outcome is required. Select a record and **Compare phase** after training. The original registry label remains visible. Scores are uncalibrated and do not assign a regulatory phase. Review validation/test metrics, class support and confusion matrix.

Both tasks share one training slot. If another experiment is running, wait. Phase files use the `phase_` prefix. The bundled starter has no Early Phase 1 examples, so its fitted classifier cannot learn that class.

## 5. Ask an AI provider questions

Edit root `.env`, add OPENAI_API_KEY, GEMINI_API_KEY or ANTHROPIC_API_KEY, keep AI_PROVIDER=auto, restart, then choose **AI Assistant**. Multiple keys follow AI_PROVIDER_PRIORITY with configurable fallback; the dropdown can pin one. See AI_PROVIDERS.md for custom services and model settings. Select a study or dataset overview. Each question is independent; prior chat turns are displayed locally but are not sent as conversation history. Only bounded selected context is sent when you press Send. Use public registry data, not patient records.

The assistant does not train models, browse the web or compute new research predictions. Provider errors are returned safely. No key means the core app works and AI calls are unavailable.

## 6. Export and preserve your work

Study Explorer exports CSV; the top report button downloads a self-contained HTML report in the full app. Open the downloaded HTML and use Print → Save as PDF. CSV formula-prefix escaping protects spreadsheet opening. Exported descriptions are HTML-escaped.

To back up, stop the app and copy the entire `data/workbench`, your immutable `data/raw`, processed cohorts, `models`, `results` and configuration. Keep `.env` private. With PostgreSQL, also use a database backup: metadata alone does not contain the raw files or models. Never move only `registry.sqlite3` while the app is writing; stop it before copying the whole store.

## 7. Optional research modules

Install optional dependencies only as needed:

```bash
.venv/bin/python -m pip install -r requirements-shap.txt
.venv/bin/python -m pip install -r requirements-research.txt
```

On Windows use `.venv\Scripts\python.exe`. SHAP adapters require the original training background. BioBERT requires a model directory/repository and a pinned 40-character revision; downloads are explicit and can be large. BioBERT generates embeddings, not an integrated neural prediction head. Cox survival needs a separately curated event/censoring cohort and lifelines. Refer to each script's `--help` and RESEARCH_METHODS for exact usage and assumptions.

## 8. AACT workflow

Obtain a frozen **flat-file** snapshot (not a PostgreSQL dump) from AACT. Keep the original archive unchanged and record its SHA-256 and snapshot date. Extract to a new `data/raw/aact_snapshot` directory. Then run:

```bash
.venv/bin/python scripts/verify_aact.py --path data/raw/aact_snapshot
.venv/bin/python scripts/build_features.py --input data/raw/aact_snapshot --output data/processed/cohort-v1 --snapshot-date YYYY-MM-DD
.venv/bin/python scripts/train_models.py --input data/processed/cohort-v1/trials.csv --output results/cohort-v1 --config configs/research.json --metadata data/processed/cohort-v1/source_metadata.json
.venv/bin/python scripts/evaluate_models.py --experiment results/cohort-v1
```

Replace YYYY-MM-DD with the actual snapshot date. Inspect `--help` for supported flags. For GUI experiment history, import the canonical CSV in Data Manager and train there; independent CLI runs are not automatically added to the GUI registry.

`download_aact.py` supports an exact HTTPS snapshot URL plus an independently recorded expected checksum. If no trusted expected checksum exists, obtain and document the download manually; do not invent a checksum.

## 9. Neon and remote hosting

Local SQLite works without another account. To use Neon metadata storage, install `requirements-postgres.txt`, put the connection string with `sslmode=require` in `DATABASE_URL`, then restart. This creates registry tables; it does not migrate existing SQLite records. Start a new store or implement a reviewed migration. Raw files and models still require persistent disk.

The full app is deliberately single-process; do not run multiple Uvicorn workers. Public production needs a durable job queue, object storage, proper per-user authentication and authorization, quotas and migrations before scaling. The supplied shared bearer token is suitable only for a small trusted workspace.

## 10. Make future changes

Create a Git repository from the folder and keep `.gitignore`. Start a feature branch. Edit components in `frontend/src/components`, API routes in `backend/app/main.py`, services in `backend/app/services`, and models in `src/clinical_trial_intelligence`. Run tests, rebuild the UI, verify the user workflow, then commit. `.github/workflows/ci.yml` provides a test/build gate when you push to your own repository.

To add another assistant provider later, implement an adapter with the same safe request/response contract as `openai_service.py`, add an explicit server configuration choice, test errors/timeouts, and retain server-only keys. No other provider is active in this release.

## 11. Verify and update your installation

Run `CHECK_WINDOWS.bat` on Windows. Else run `.venv/bin/python scripts/doctor.py` and `.venv/bin/python -m pip check`. Diagnostics check Python, required modules, built UI, data and writable storage; they do not validate a live provider key. Never share `.env` or a database URL.

To upgrade from v2, stop it and back up the whole `data/workbench` directory and private `.env`. Extract v3 into a new folder, run setup, then copy your backed-up store and settings into it. Start once and verify dataset counts. Retrain duration models because v3 uses artifact version 2; old runs remain history but incompatible artifacts are not loaded. Do not copy an old virtual environment or node_modules.

To get a fresh starter snapshot without overwriting the release: `python scripts/download_starter_data.py --output-dir data/new-starter`. Import its CSV as a new dataset. Do not change the frozen `data/starter` files.

## Troubleshooting

| Symptom | Action |
|---|---|
| Phase training refused | Use single supported phases, exact start dates and sufficient records/classes; inspect `/api/v1/readiness?dataset_id=YOUR_ID` |
| AUROC/AP shown as — | A split may have only one outcome class. This is mathematically undefined; the bundled duration validation split has zero positives |
| Starter examples absent from history | CLI/example artifacts are intentionally separate. Load the starter dataset and train through the GUI |
| Python launcher missing | Install Python 3.12 with the launcher; run `py -3.12 --version` on Windows |
| Dependency install fails | Check internet/proxy/disk; read the first pip error; retry setup |
| Port 8000 already in use | Stop the other process or set `API_PORT=8001` in `.env` and restart |
| Cannot reach API | Keep backend terminal open; confirm `/api/v1/health` loads; use the documented URL |
| Unauthorized | Set the same API_BEARER_TOKEN in server `.env` and Connection settings |
| OpenAI configured but request fails | Check key permissions, account access, chosen model and provider quota locally |
| Experiment refused | Review actual dates, statuses, time span, exclusions and split sizes |
| Models unavailable after upgrade | Rerun experiments in the new version; do not force incompatible artifacts |
| UI edits do not appear | `npm ci`, `npm run build` in frontend; restart backend and refresh |
| Docker cannot start | Ensure Docker is running and `.env` exists; inspect `docker compose logs` |


## v4 researcher workflow

Research Hub unifies actual source, PCI, matching-model evidence and bounded similar-trial retrieval. Digital Twin saves immutable hypothetical protocol scenarios and explicit planning assumptions; history persists in the full local app. Formula Studio animates the actual six PCI terms. Validation Lab visualizes train/tune/calibrate/test roles and recorded counts. All animation controls offer manual operation and reduced-motion support.

Recruitment and amendment model probabilities require curated outcomes and remain unavailable. The planning arithmetic is an assumption-based calculation. Run `node scripts/check_frontend_formulas.mjs` after formula edits, rebuild frontend and run Python tests. Duration artifact version 3 requires retraining v3 duration artifacts; preserve the old release/store for rollback. Phase artifacts retain their task version.
