# Clinical Trial Intelligence Workbench — v5.2.0.2

A PostgreSQL-backed research application for trial records, protocol complexity, saved-model prediction, evidence review and grounded conversations.

## Run

Install Python 3.12 and Docker Desktop, extract the ZIP, then:

```bash
python3.12 scripts/initialize_env.py --start
```

Windows: double-click `START_DOCKER_WINDOWS.bat`. Open http://localhost:8000 after startup. Use the generated local setup token, create an owner and project, then load the starter cohort from Data Manager.

[Start here](START-HERE.md) · [Full guide](docs/V5_2_0_2_FULL_GUIDE.md) · [Guide PDF](docs/Clinical-Trial-Intelligence-v5.2.0.2-Full-Guide.pdf)

## Included

- Navy/teal interface with restrained textured navigation, Projects launcher, responsive charts and appearance/motion settings.
- Twelve selectable full-cohort overview graphs, filters, study comparison, ordering/fullscreen and exports.
- Seven accessible visual explanations: pipeline, phases/dates, actual attribution, recruitment availability, model-backed scenarios, supported text/metadata fusion and a decorative helix.
- PostgreSQL accounts, sessions, memberships, audit, feedback, chat and research metadata. No SQLite fallback.
- Server-enforced owner/researcher/reviewer/viewer capabilities, invitations, password/session controls and request limits.
- Readable streamed assistant replies, source references, configurable budgets, copy/export and reviewed corrections.
- Nine existing research branches plus opt-in CatBoost fitting and genuine native TreeSHAP.
- Frozen 800-record public registry cohort, verified artifacts, source hashes, tests, setup scripts and guide PDF.

## Evidence

The approved baseline remains selected; the CatBoost candidate is evaluated without claiming guaranteed accuracy gains. Observational charts disclose missingness. No invented SHAP, confidence intervals, recruitment counts or silent simulation fallback are substituted for evidence.

Completed-only retrospective analysis and small retained splits limit interpretation. Clinical-success, treatment-effect, recruitment-risk and amendment-risk probabilities are not validated bundled tasks. See the guide and release evidence.

## Development

```bash
python3.12 scripts/setup.py --dev
docker compose up -d postgres
.venv/bin/python scripts/start.py
```

Frontend: `npm ci`, `npm run dev` / `npm run build` in `frontend/`. Tests: start `docker compose --profile test up -d postgres-test`, then `.venv/bin/python scripts/run_tests.py`. Windows uses `.venv\Scripts\python.exe`.

Provider keys/API model IDs belong in the private server `.env`; they are not included in browser assets or release downloads. Provider/email/remote deployment access requires operator configuration.
