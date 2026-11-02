## Week 2 — Features, chronological splits and baseline forecasts
**Goal:** produce honest seven-day reference forecasts without future information.

**Topics:** trend/seasonality, forecast horizon and origin, lag features, shifted rolling statistics, calendar features, data leakage, chronological validation, naive/seasonal-naive baselines, MAE/RMSE/bias/WAPE.

**What to do and how:**
1. Read `src/forecasting.py` and run `python -m src.cli baseline`.
2. Inspect `reports/week02/baseline_report.json` and the per-origin predictions CSV.
3. Manually verify one seven-day seasonal-naive forecast repeats the previous week's corresponding values.
4. Inspect lag-1/7/14 and rolling means in notebook 02. Each series has its own history and every target is excluded from its features.
5. Understand the split: last 28 days are test; preceding 28 are validation; earlier rows are training. Every series needs at least 42 initial training days (98 total days for this workflow).
6. Evaluate four seven-day validation origins. Within a horizon later lags use earlier predictions; observed actuals become available only between origins.
7. Try a zero-demand example and explain why WAPE is null when actual totals are zero. Final test outcomes are not inspected in this stage.

**Day plan:** Day 1 time-series concepts; Day 2 lags; Day 3 rolling features/leakage; Day 4 baselines; Day 5 time splits; Day 6 evaluation; Day 7 mid-review preparation.

**Learn on YouTube:** [codebasics: forecasting channel search](https://www.youtube.com/@codebasics/search?query=time%20series%20forecasting), [StatQuest: training/validation/testing channel search](https://www.youtube.com/@statquest/search?query=training%20validation%20testing).

**Learn on websites:** [Forecasting: Principles and Practice](https://otexts.com/fpp3/), [scikit-learn lagged-feature example](https://scikit-learn.org/stable/auto_examples/applications/plot_time_series_lagged_features.html), [common pitfalls/data leakage](https://scikit-learn.org/stable/common_pitfalls.html).

**GitHub deliverables:** feature and baseline code, notebook 02, split explanation, measured validation metrics, prediction CSV, tests and Week 2 notes. Completion check: explain why a seven-day forecast cannot consume the actual sales from those future seven days.


Record your own observations, commands, measured results, screenshots, mistakes and fixes below.
