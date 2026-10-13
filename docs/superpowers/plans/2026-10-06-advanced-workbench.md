# Advanced Workbench Implementation Plan

Goal: turn the supplied v1 foundation into a functioning research workbench and distributable source project.
Architecture and spec: ../specs/2026-10-06-advanced-workbench.md.
Tech: React/Vite/TypeScript; FastAPI/Pydantic; pandas/sklearn; optional SHAP/BioBERT/lifelines/PostgreSQL.

Global constraints: preserve title, no fabricated real data/metrics, raw immutability, train-only preprocessing, no secrets in frontend.
Review focus: missing/invalid dates, duplicate IDs, tiny or one-class temporal cohorts, mismatched model and active dataset, unavailable credentials or network.

- [x] Research pipeline: src/clinical_trial_intelligence/research.py, scripts/train_models.py, tests/test_research.py; train_experiment(df, output_dir, source_metadata) writes real manifest and artifacts; predict_trial(row, artifact_dir) returns null until trained. Test temporal boundary isolation, undefined metrics, no leakage, synthetic fixture end-to-end.
- [x] Backend: backend/app and tests/test_api.py; dataset ingestion/registry, study search/detail, statistics, CSV export, CT.gov import, experiment launching/listing and OpenAI chat with safe configured-key state. Test atomic invalid import, literal search, persistence, no-model predictions, no-key assistant and export.
- [x] UI: frontend/src components, API client, styling and explicitly labeled static preview adapter. Implement dataset selection, study selection/filter/compare, PCI scenarios, experiments, data import, assistant, exports. Build and browser-test desktop; mobile CSS provided, viewport testing not executed.
- [x] Operations: Windows scripts, Docker, lockfiles, configs, README/RUNBOOK, source requirements matrix and plugin status. Validate documented commands.
- [x] Review: fresh reviewer assesses integrated source; fix blockers, execute clean verification, deliver browser preview then ZIP.

Ruling: proceed with concrete build now under user's explicit request to build and preview before handoff; routine implementation choices are authorized. Deliver downloadable source and verify fixture execution while clearly distinguishing unavailable scientific results.
