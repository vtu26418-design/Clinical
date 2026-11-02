# Four-week demand forecasting project

User-authorized deliverables: four cumulative weekly ZIPs and one complete month ZIP, all using the same project root; runnable code; weekly tasks, explanations, learning websites and YouTube links; real-data acquisition instructions. Follow the uploaded Data Science PDF's demand-forecasting phases and the execution PDF's GitHub/review requirements.

Architecture: Python CLI stages and a final Streamlit dashboard, optional FastAPI scoring service. CSV contract date,store,item,sales. Preserve source bytes. Strictly validate daily regular series, finite nonnegative sales and unique keys; never silently fill missing days. Include reproducible synthetic practice data visibly identified as synthetic, with no claim of real retail performance. Support real Kaggle CSV without fabricating inventory fields. Seven-day recursive models and same-origin naive/seasonal baselines. Chronological validation and test blocks; model selected exclusively on validation MAE. Multi-series lags stay within groups; predictions feed later forecast steps. Store actual measured metrics, manifest, raw-data hash and package versions. Inventory scenarios require explicit assumed inputs and cannot forecast beyond available horizon. Fail clearly on invalid inputs. No public publishing, GitHub pushing, or changes to the existing Clinical repository.

Week 1: data audit/cleaning/EDA, synthetic practice source, CLI and tests.
Week 2: leakage-safe features, recursive baselines, metrics, backtesting and tests.
Week 3: regression/forest candidates, validation-only choice, held-out evaluation, saved forecasting, explicit inventory scenarios and tests.
Week 4: Streamlit dashboard with CSV import, charts/exports/evaluation/inventory, optional scoring API, SQL report, functional tests and cross-platform instructions. Package cumulative snapshots and verify each after extraction.
