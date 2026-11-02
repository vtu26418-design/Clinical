## Week 3 — Modeling, evaluation and inventory scenarios
**Goal:** choose a forecasting method using validation evidence and document inventory assumptions.

**Topics:** supervised regression, linear regression, Random Forest, categorical encoding, scaling/pipelines, overfitting, validation-based model selection, recursive multi-step inference, persistence/checksums, inventory position, safety stock, service-level assumptions, reorder point and pack rounding.

**What to do and how:**
1. Run `python -m src.cli train`. Four methods are compared: naive, seasonal naive, linear regression and Random Forest.
2. Inspect `reports/evaluation/demo/manifest.json`. Selection uses validation MAE exclusively; test results are computed after that choice. The same initial training-only fitted models are evaluated across validation/test origins.
3. Inspect actual per-row validation/test prediction CSVs. Calculate one model's MAE manually or with pandas. A baseline is allowed to win.
4. Read notebook 03 and change one justified model setting in a separate experiment. Do not repeatedly tune against the final test set.
5. After evaluation, the selected approach is refitted on all known history for serving. Its future predictions are not an independently validated performance claim.
6. Run `python -m src.cli forecast` and inspect `reports/evaluation/demo/new_forecast.csv`.
7. Run `python -m src.cli inventory --store 1 --item 1 --lead-days 3 --on-hand 20 --daily-std 5`. These numbers are explicit scenario assumptions, not real stock observations.

**Inventory equations:** inventory position = on hand + outstanding orders − backorders; reorder point = lead-time forecast demand + safety stock; order toward lead-plus-review forecast demand + safety stock when the reorder trigger is met. Round up to pack size and minimum order when supplied. Safety stock uses z × daily demand SD × sqrt(fixed lead time), assuming independent daily demand and a normal approximation. A desired service level is not a validated guarantee. Lead-plus-review days cannot exceed the available forecast.

**Day plan:** Day 1 regression; Day 2 Random Forest; Day 3 validation comparison; Day 4 inference/persistence; Day 5 inventory calculations; Day 6 tests/error analysis; Day 7 results/assumptions report.

**Learn on YouTube:** [StatQuest: linear regression](https://www.youtube.com/@statquest/search?query=linear%20regression), [StatQuest: Random Forest](https://www.youtube.com/@statquest/search?query=random%20forest), [reorder point/safety-stock worked examples](https://www.youtube.com/results?search_query=reorder+point+safety+stock+worked+example).

**Learn on websites:** [scikit-learn MOOC](https://inria.github.io/scikit-learn-mooc/), [Random Forest reference](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestRegressor.html), [evaluation metrics](https://scikit-learn.org/stable/modules/model_evaluation.html), [MIT OCW inventory search](https://ocw.mit.edu/search/?q=inventory).

**GitHub deliverables:** modeling, forecast, inventory and evaluation code; notebook 03; actual metric tables; plots; assumptions; tests and Week 3 notes. Do not redistribute untrusted pickle/joblib artifacts or load model files supplied by strangers. Completion check: reproduce the selected model and a hand-checked inventory calculation.


Record your own observations, commands, measured results, screenshots, mistakes and fixes below.
