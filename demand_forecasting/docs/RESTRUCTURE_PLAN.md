# Models and project layout update

User request: explain existing model location and deliver the same project organized similarly to the supplied repository/screenshot. Keep the existing evaluated seven-day workflow and weekly learning material. Reference repository inspected read-only at commit 36d6f7ae1b361a3fc068f49e710d24e2dae7f82c. Only folder/entrypoint organization is a reference; no code, artifacts, dataset or reported metrics are copied.

Implementation:
1. Add tests proving that training writes both learned-model artifacts, baseline specifications, selected artifact, registry and model card, with source/hash/version metadata; verify replay and tamper rejection.
2. Extend train(..., model_directory=None) while keeping legacy output/model.joblib compatibility. CLI defaults: reports/evaluation/demo and models/demo. Refit both candidates only after validation-based choice/test evaluation; published artifacts are serving refits, not independent test evidence.
3. Canonical API entrypoint api/main.py and dashboard app/dashboard.py, preserving older src.api and app/streamlit_app.py commands. Add tests for entrypoints and saved-run loading.
4. Store dashboard-trained runs under models/runs/<dataset-hash> and reports/runs/<dataset-hash>. Load a matching published run across restarts; never apply mismatched dataset metrics. Add a Models tab with filenames, method, selected status and provenance. Do not silently retrain on startup.
5. Train demo artifacts using this project's own synthetic practice data; package those genuine artifacts in complete/Week 3/Week 4 ZIPs. Document original vs new locations, exact model contents and startup/retraining commands, reference differences, and dataset limitations. Retain Weeks 1–2 as foundation stages.
6. Run suite, replay saved forecasts, verify extracted archives, push the updated branch and verify actual GitHub downloads. No new repository or changes to main.

User steering: use the PDF's technology stack and Python/Jupyter Notebook application languages. Add complete four-week executable notebooks, statsmodels diagnostics, pinned Jupyter dependencies and a pure-Python dashboard launcher. Do not manipulate GitHub language statistics or aim for the reference's percentages. XGBoost is optional ("where appropriate" in the PDF); retain CPU-friendly Linear Regression and Random Forest models, with the choice documented. SQL is implemented through Python's SQLite interface. No JavaScript, TypeScript, HTML frontend, batch or shell implementation files.
