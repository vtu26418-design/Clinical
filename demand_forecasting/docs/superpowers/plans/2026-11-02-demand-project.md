# Demand Forecasting Implementation Plan

> **For agentic workers:** Execute inline with superpowers:executing-plans. The user requested immediate construction of the four ZIP milestones.

**Goal:** Deliver one reproducible four-week learning project as cumulative working ZIPs.

**Architecture:** Shared src modules, argparse CLI, Streamlit UI and optional FastAPI service. Snapshot each tested stage without virtual environments or Git metadata.

**Tech Stack:** Python 3.12, pandas, NumPy, scikit-learn, matplotlib, Streamlit, Plotly, pytest, FastAPI.

**Spec:** docs/SPEC.md

## Global Constraints
- Synthetic practice results explicitly labelled; real Kaggle input supported.
- Unique nonnegative finite daily observations; no silent filling or inventory fabrication.
- Seven-day recursive predictions use available history only; validation chooses the model.
- Four cumulative stages share one folder structure; weekly guides contain tasks and learning links.

## Review Focus
- Missing days, duplicates and malformed IDs must not silently distort forecasts.
- A recursive seven-day forecast must never read the seven actual target values.
- Final test values must never affect model selection or training fit.
- Inventory assumptions must not be presented as measured stock data.
- ZIPs must run after extraction without paths into the build workspace.

## Task 1: Data and EDA
Files: src/data.py, src/cli.py, tests/test_data.py, docs/week01.md.
Interface: validate_sales(frame)->DataFrame; audit(frame)->dict; prepare(input,output)->dict.
- [ ] Write and run failing validation tests for duplicates, gaps, nonfinite sales and invalid IDs.
- [ ] Implement strict CSV loading, provenance, EDA and seeded synthetic practice data.
- [ ] Run tests and CLI prepare; capture cumulative Week 1 snapshot.

## Task 2: Forecast fundamentals
Files: src/forecasting.py, tests/test_forecasting.py, docs/week02.md.
Interface: features(history,date,store,item)->dict; baseline(history,horizon,kind)->DataFrame; metrics(actual,predicted)->dict; backtest(frame,kind,origins,horizon)->DataFrame.
- [ ] Write and run failing group isolation, hand-calculated baseline, zero-metric and recursive-history tests.
- [ ] Implement lag features, evaluation windows, baselines and plots.
- [ ] Run full suite and CLI baseline; capture cumulative Week 2 snapshot.

## Task 3: Models and inventory
Files: src/modeling.py, src/inventory.py, tests/test_modeling.py, tests/test_inventory.py, docs/week03.md.
Interface: train(frame,output,horizon)->dict; forecast(frame,bundle,horizon)->DataFrame; inventory(forecast,inputs)->dict.
- [ ] Write and run failing temporal-boundary, persistence, held-out choice and known inventory arithmetic tests.
- [ ] Implement pipelines, validation-only selection, later test evaluation, version/hash artifacts and scenarios.
- [ ] Run full suite and CLI train/forecast/scenario; capture cumulative Week 3 snapshot.

## Task 4: App and delivery
Files: app/streamlit_app.py, src/api.py, tests/test_app.py, docs/week04.md, README.md, learning guides and packaging script.
- [ ] Write and run failing real UI/API workflow tests.
- [ ] Implement dashboard, optional API, CSV exports and SQL summary.
- [ ] Run full suite, UI interactions and HTTP checks.
- [ ] Extract all snapshots independently; run their documented commands and tests.
- [ ] Produce four weekly ZIPs, full-month ZIP, SHA256SUMS and user download links.
