# Demand Forecasting & Inventory Optimization — Week 4

**Cumulative milestone 4/4.** Complete project: all earlier features plus Streamlit, CSV upload/export, optional API, SQL and functional tests.

Start with [WEEKLY_LEARNING_PLAN.md](WEEKLY_LEARNING_PLAN.md) for what to do, how to do it, what to learn, YouTube/website links, real-data acquisition and GitHub tasks. Your current guide is [weeks/week04/README.md](weeks/week04/README.md).

## Requirements
Python **3.12** (tested), pip and an initial Internet connection to install packages. Normal CPU execution; no paid services, GPU, API key or runtime Internet needed for the bundled example. Use a new virtual environment. The optional API is a local learning service, not an authenticated deployment.

## Install on Windows PowerShell
Run inside the extracted `demand_forecasting` folder:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe run_week.py
.\.venv\Scripts\python.exe -m pytest -q
```
For other commands below, use `.\.venv\Scripts\python.exe` in place of `python`; no PowerShell activation-policy change is needed.

## Install on macOS/Linux
```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python run_week.py
python -m pytest -q
```
`requirements.txt` lists pinned direct requirements; `requirements-lock.txt` records the tested clean environment. Use the lock for the closest reproduction. OS-specific optional package details can differ; Python 3.12 is the supported target.

## Commands available in this milestone
```bash
python -m src.cli prepare
python -m src.cli baseline
python -m src.cli train
python -m src.cli forecast
python -m src.cli inventory --store 1 --item 1 --lead-days 3 --on-hand 20 --daily-std 5
python -m src.cli sql
python -m streamlit run app/streamlit_app.py
```
`run_week.py` runs this milestone's command-line stages in order; it does not start persistent servers. For help use `python -m src.cli --help`.

## Data and evidence
The included CSV is clearly labelled SYNTHETIC PRACTICE DATA, not genuine retail sales. Source/hash/seed metadata is supplied alongside it. Real Kaggle historical CSV is supported; follow docs/DATA_GUIDE.md. Do not submit generated practice results as real business findings. No inventory records are bundled: recommendations use explicit what-if assumptions.

Raw input is never cleaned in place. Missing daily records and duplicate keys are rejected. Every forecast uses only history available at its origin; later steps consume earlier predictions. A seven-day horizon is evaluated over four origins per validation/test block. Models are selected using validation MAE only. Reported test results belong to initial evaluation fits; the serving model is refitted after evaluation on all known history. Re-running many experiments against the same test set makes it development data; use a genuinely new holdout for final research claims.

## Outputs and reproducibility
- reports/week01/: audit JSON, cleaned CSV, summary tables, EDA PNG.
- reports/week02/: validation baseline report/predictions (Week 2 onward).
- outputs/demo/: model manifest, validation/test predictions, serving artifact and future CSV (Week 3 onward).
- outputs/demo/results.sqlite: SQL exercise (Week 4).

Run commands to generate outputs locally. Verified example reports are included under reports/reference when available. Future dates follow the included historical dataset, not today's calendar. A baseline is allowed to outperform a learned model. Load only your own trusted locally generated joblib artifacts.

## Weekly ZIP upgrades and GitHub
All four archives share this project root. Later ZIPs include earlier source and guides. Compare and copy changes into the same Git repository, preserving .git, your edits, raw private data and local outputs. No virtual environment or fabricated Git history is shipped. Weekly milestones/tags complement the daily activity requirements in your execution PDF. See docs/GITHUB_AND_REVIEWS.md.

## Troubleshooting
- No module named src: run from the project root, not src/ or app/.
- Missing columns: use canonical date,store,item,sales. M5 requires a separate wide-to-long mapping.
- Missing days/duplicates: investigate source meaning; do not automatically insert zeros or sum duplicate daily observations.
- Insufficient history: every selected series needs at least 98 continuous days for full evaluation.
- Plot cache permissions: set MPLCONFIGDIR to a writable temporary directory if your environment restricts the home folder.
- Local tests hanging in a managed command sandbox: API/Streamlit functional tests require local sockets; run in a permitted local environment.
- Large Kaggle file: select a small store/item subset before modeling; the dashboard imposes learning-scale limits.
- Notebook use: install JupyterLab in your environment (`python -m pip install jupyterlab`) and select that environment's kernel. Notebooks are optional; all core work runs through the CLI.

## Attribution and use
Created as a learning/reference implementation for the supplied four-week demand-forecasting requirements. Application code may be adapted under LICENSE. Third-party datasets and learning resources keep their own terms. Distinguish your contributions and measured findings in your internship report.
