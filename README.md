# Clinical Trial Intelligence Workbench — v5.2.0.3

A PostgreSQL-backed research application for trial records, protocol complexity, saved-model prediction, evidence review and grounded conversations. The complete ZIP includes editable source, the prebuilt interface, frozen 800-record public registry cohort, saved models and an end-to-end guide.

## Windows: run without Docker

1. Install [Python 3.12](https://www.python.org/downloads/windows/) with its Python launcher and [PostgreSQL for Windows](https://www.postgresql.org/download/windows/). Remember the `postgres` administrator password you choose during installation; the usual database port is 5432.
2. Extract the complete ZIP into a writable folder, such as `C:\CTI`. Run `SETUP_WINDOWS.bat` once.
3. Run `CONNECT_DATABASE_WINDOWS.bat`. Accept the local defaults, retain the generated application password with Enter, and enter your PostgreSQL administrator password at its hidden prompt. Wait for **Application database login verified.**
4. Run `START_WINDOWS.bat`, then open http://localhost:8000. Keep the terminal open.
5. Read `SETUP_TOKEN` from your private local `.env`, create the first owner and a project, then use More tools → Data Manager to load the 800-record starter cohort.
6. Review Overview and use Prediction Studio. Bundled predictions do not require training.

The connector creates only missing application roles/databases, preserves existing data/passwords and verifies the application login. Docker and Node are optional for the packaged Windows workflow. PostgreSQL is required; there is no SQLite fallback.

[Start here](START-HERE.md) · [Full operating guide](docs/v5.2.0.3-full-guide.md) · [Downloadable guide PDF](docs/Clinical-Trial-Intelligence-v5.2.0.3-Full-Guide.pdf) · [Changes](docs/v5.2.0.3-changelog.md)

## Included

- All 26 research routes, 12 configurable full-cohort graphs, study comparison and exports.
- Guided 3D explanations with exact evidence captions, accessible 2D fallbacks, reduced motion and optional click-to-read browser narration.
- Phase Academy with optional Phase 0 and phases I–IV, source links, quizzes and recorded examples.
- Project/session restoration after reload; browser appearance, spacing, scene and narration settings with preference import/export/reset.
- PostgreSQL accounts, memberships, role enforcement, sessions, audit, feedback and chat.
- Streamed assistant replies for general and evidence-grounded questions, up to 32,768 input characters; new projects have no daily application quota by default. Provider/context/output and abuse limits still apply.
- Preserved approved models plus optional basic or expanded CatBoost candidate search and genuine native TreeSHAP. Training does not activate a candidate.

## Evidence and limits

Source records, hashes, historical evidence and approved artifacts remain preserved. Expanded search is an evaluated capability, not a guaranteed accuracy improvement. Unknown recruitment/date values stay unknown; SHAP attribution does not establish causation. Completed-only retrospective cohorts and small retained splits limit interpretation. Bundled models do not validate clinical success, treatment effects, recruitment risk or amendment risk.

For current release-check status, consult `docs/v5.2.0.3-release-verification.md`; the v5.2.0.2 reports describe that historical release.

## Other installation and development paths

Linux/macOS native: install Python 3.12 and PostgreSQL, run `python3.12 scripts/setup.py`, `.venv/bin/python scripts/configure_postgres.py`, then `.venv/bin/python scripts/start.py`. Docker remains available through `START_DOCKER_WINDOWS.bat` or `python3.12 scripts/initialize_env.py --start`.

Development: `scripts/setup.py --dev` installs test dependencies. Node.js 22 is needed only to modify/rebuild the frontend (`npm ci`, `npm run dev` / `npm run build` in `frontend/`). Automated tests require a separate disposable PostgreSQL database configured as `TEST_DATABASE_URL`; run `.venv/bin/python scripts/run_tests.py`. See the guide for Windows commands and the 37-step acceptance workflow.

Provider keys and account-supported API model IDs belong in the private server `.env`. Never include `.env`, credentials, logs or runtime databases in shared ZIPs. Back up PostgreSQL and research files together. This application is research decision support, not clinical or regulatory advice.
