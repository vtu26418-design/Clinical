# Saved models: where to look

The complete and Week 3/4 ZIPs include actual weights in models/demo/, fitted by this project's src/modeling.py on the labelled synthetic practice CSV. No reference-repository weights are copied.

- linear_regression.joblib: encoding/scaling and fitted Linear Regression.
- random_forest.joblib: preprocessing and fitted Random Forest (60 trees, seed 42).
- selected_model.joblib: selected serving pipeline/baseline bundle; inspect registry rather than assuming a winner.
- naive.json and seasonal_naive.json: saved baseline rules, recent history and provenance.
- registry.json: artifact SHA-256, methods, selected flag and evaluation metrics.
- model_card.json: intended use, source, cutoff, dependency versions and limitations.
- manifest.json: split dates and evaluation provenance.

The original release generated outputs/demo/model.joblib after training. The current version supplies weights here. Rebuilding also creates a legacy report-directory model.joblib alias; use selected_model.joblib going forward.

Dashboard jobs persist under models/runs/<dataset-id>/ and reports/runs/<dataset-id>/. Matching saved runs reload after restart without fitting. Use models/retail/ for separate licensed real-data experiments. Local runs are excluded from Git by default.

Regenerate practice weights with python -m src.cli train or notebook 03. Inspect the dashboard's Models tab or GET /models. Install requirements-lock.txt and deserialize only trusted artifacts.
