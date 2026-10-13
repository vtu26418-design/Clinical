# Advanced Clinical Trial Intelligence Workbench

Project title: An Explainable Multimodal AI System for Clinical Trial Protocol Complexity Profiling and Prolonged-Duration Risk Prediction.

User requests upgrade of supplied v1 source, functional browser preview before final ZIP, all source and start-to-finish Windows instructions, OpenAI first with replaceable provider. Preserve source structure and raw data. Existing AGENTS.md applies.

## Architecture
React + TypeScript + Vite interface; FastAPI server; canonical CSV/Parquet ingestion and ClinicalTrials.gov adapter; local persistent dataset registry and optional SQLAlchemy/PostgreSQL persistence; offline reproducible sklearn research pipeline. No secret may reach client build. OpenAI Responses API is optional server-side narrative assistance with bounded record context and no fabricated predictions. No key required for core app.

## Data integrity
Keep existing five sample fixtures, visibly labeled software test data. Never invent research records or metrics. Imports validate atomically, preserve raw bytes and SHA-256, report row errors and missingness; source/snapshot provenance travels with each dataset. Search uses literal strings. CSV export guards spreadsheet formulas. No heuristic probability masquerades as ML. Results unavailable until a compatible trained artifact exists. Latest registry fields may not be baseline features: imported registry experiments explicitly retrospective unless baseline provenance established.

## Research
Temporal train/validation/test splits grouped on dates; only completed known actual outcomes for observed duration; no completion/status input features. Quantile prolonged threshold fit on training subset only. Train structured, TF-IDF, combined and median baseline regression/classification models; log MAE/RMSE/R2, AUROC/AP, Brier/calibration with undefined metrics null. Optional BioBERT, survival and SHAP capabilities should have real implementations and explicit optional dependencies, never fake output. Training generates manifest, test predictions, metrics and serialized preprocessing. Local contributions accurately name method and units.

## Product
Navy sidebar, off-white work area, white bordered panels, teal actions; Overview, Study Explorer, Complexity Lab, Experiments, Data Manager, AI Assistant. Dataset selection; searchable/filterable sortable studies; selected-trial details and comparison; data-derived charts; configurable PCI scenario analysis with assumptions; CSV/JSON/report exports; launch and inspect experiment; upload/import real data; key setup state. Responsive, keyboard accessible, meaningful loading/error states. A browser demo may use bundled sample with explicit preview notice; full local app must use real API.

## Delivery
Source ZIP including dependency locks, sample inputs, full scripts, config, tests, Docker/Windows launchers, original project guides as text, methodology and limitation documentation. Do not include secrets, node_modules, virtualenvs or invented trained weights. Publish preview only with clearly labeled fixture data and no secrets. Verify clean frontend build, backend integration, failure paths, training end-to-end on clearly labeled test fixtures, browser desktop/mobile and critical interactions. State live integrations not exercised without credentials/network.
