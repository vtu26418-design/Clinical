# Clinical Trial Intelligence Workbench — v5.2.0.3

A PostgreSQL-backed research application for trial records, protocol complexity, saved-model prediction, evidence review and grounded conversations. The complete ZIP includes editable source, the prebuilt interface, frozen 800-record public registry cohort, saved models and an end-to-end guide.

## Windows: run with Docker Desktop

1. Open Docker Desktop and wait until its engine is running. Use Linux containers. Install [Python 3.12](https://www.python.org/downloads/windows/) with its Python launcher if it is not already installed.
2. Extract the full ZIP into a writable folder, such as `C:\CTI`. Open the extracted folder containing `START_DOCKER_WINDOWS.bat`.
3. Double-click `START_DOCKER_WINDOWS.bat`. It prepares a private `.env`, preserves existing settings, builds the application and starts both PostgreSQL and the web application. The first build can take several minutes.
4. Wait for **Application ready: http://localhost:8000**, then open that address if the browser does not open automatically.
5. Open your private `.env`, copy its `SETUP_TOKEN` value and create the first owner. If setup is already complete, sign in with your existing account.
6. Create/open a project. More tools → Data Manager → load the 800-record starter cohort, select it and use Overview and Prediction Studio.

If you already ran `SETUP_WINDOWS.bat`, the next step is `START_DOCKER_WINDOWS.bat`. Docker supplies PostgreSQL; a separate native PostgreSQL installation is unnecessary for this workflow. Docker installs Python/Node application dependencies inside the image. Your host Python launcher is used only to initialize settings and launch Compose.

Later starts: open Docker Desktop, then run `START_DOCKER_WINDOWS.bat`. Stop with `docker compose down` from the project folder. Keep the named volumes to retain projects and data. For optional native operation, use `CONNECT_DATABASE_WINDOWS.bat` then `START_WINDOWS.bat`, as explained in the guide.

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

Linux/macOS native: install Python 3.12 and PostgreSQL, run `python3.12 scripts/setup.py`, `.venv/bin/python scripts/configure_postgres.py`, then `.venv/bin/python scripts/start.py`. Docker is the recommended Windows workflow; Linux/macOS can use `python3.12 scripts/initialize_env.py --start`.

Development: `scripts/setup.py --dev` installs test dependencies. Node.js 22 is needed only to modify/rebuild the frontend (`npm ci`, `npm run dev` / `npm run build` in `frontend/`). Automated tests require a separate disposable PostgreSQL database configured as `TEST_DATABASE_URL`; run `.venv/bin/python scripts/run_tests.py`. See the guide for Windows commands and the 37-step acceptance workflow.

Provider keys and account-supported API model IDs belong in the private server `.env`. Never include `.env`, credentials, logs or runtime databases in shared ZIPs. Back up PostgreSQL and research files together. This application is research decision support, not clinical or regulatory advice.
