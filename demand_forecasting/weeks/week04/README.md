## Week 4 — Dashboard, SQL, optional API, tests and handover
**Goal:** run an application another person can understand and reproduce.

**Topics:** Streamlit widgets/session state, Plotly, CSV/JSON export, input validation, SQL aggregation, API schemas, functional testing, package versions and technical communication.

**What to do and how:**
1. Run `python -m streamlit run app/streamlit_app.py`. Click Train / evaluate. Open all four tabs: Sales overview, Forecasts, Inventory scenarios, Model performance.
2. Change store/item selections and verify the result changes appropriately. Changing the training dataset invalidates stale model outputs.
3. Upload a licensed real-data subset; document its source and limitations. Train separately from the bundled practice example.
4. Export forecasts, held-out predictions, evaluation manifest and inventory scenario. Verify downloaded values against displayed results.
5. Run `python -m src.cli sql`; inspect `outputs/demo/results.sqlite`. Example: `SELECT model, AVG(ABS(prediction-actual)) AS mae FROM test_predictions GROUP BY model;` This is descriptive reporting after selection.
6. Optional API: `python -m uvicorn src.api:app --host 127.0.0.1 --port 8000`. Use `/docs` locally to test `/forecast` and `/inventory`. Default forecasts use seasonal naive; method `selected` uses the model produced by CLI training. Set DEMAND_SALES_CSV and DEMAND_MODEL_PATH for your own data. Keep this unauthenticated educational service on loopback; no production deployment is included.
7. Run `python -m pytest -q`. Tests exercise data errors, recursive forecasts, zero-denominator metrics, holdout independence, inventory arithmetic, API responses and actual Streamlit interactions.
8. Recreate a clean environment from requirements-lock.txt. Complete the final report, README and slides. Explain which results use synthetic versus real data.

**Day plan:** Day 1 layout/widgets; Day 2 charts/forecast; Day 3 inventory/export; Day 4 tests/SQL/API; Day 5 final real-data evaluation; Day 6 report/slides; Day 7 demo and fixes. Prepare earlier if your assigned review is earlier.

**Learn on YouTube:** [Data Professor: Streamlit](https://www.youtube.com/@DataProfessor/search?query=streamlit), [Corey Schafer: Python testing](https://www.youtube.com/@coreyms/search?query=testing), [freeCodeCamp: SQL](https://www.youtube.com/@freecodecamp/search?query=sql%20beginners).

**Learn on websites:** [Streamlit](https://docs.streamlit.io/get-started), [Plotly](https://plotly.com/python/), [pytest](https://docs.pytest.org/en/stable/getting-started.html), [SQLBolt](https://sqlbolt.com/), [FastAPI](https://fastapi.tiangolo.com/tutorial/).

**GitHub deliverables:** runnable dashboard, export/API/SQL code, tests, pinned requirements, reproducibility instructions, final report and presentation. Completion check: a new user can run the app and explain the baseline comparison and assumptions.


Record your own observations, commands, measured results, screenshots, mistakes and fixes below.
