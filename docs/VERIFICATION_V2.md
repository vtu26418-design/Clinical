# Release verification · v2.0.0

Verification performed on Linux with Python 3.12. Software fixtures are synthetic and are not scientific evidence.

| Check | Observed result |
|---|---|
| Complete test suite with optional SHAP installed | **59 passed**, one third-party deprecation warning |
| New isolated virtual environment, installed from requirements-dev.txt | Install succeeded; **58 passed, 1 skipped** (optional SHAP absent) |
| Dependency consistency | `pip check`: no broken requirements |
| Fixture smoke script | Five records validated; PCI computed; predictions correctly unavailable |
| TypeScript and Vite production build | Successful for full UI and fixture preview |
| Actual launcher in clean environment | Served UI, both compiled assets, health endpoint and five fixture records over HTTP |
| Public Vercel demo | Deployment READY and actual page opened in supported cloud browser |
| Desktop browser workflows | Search reduced to the matching study; two-study comparison; study details; no-model state; equal-weight/enrollment scenario; JSON download; experiment restriction; assistant setup and data manager inspected |
| Exported browser scenario | Download inspected: equal weights, +10 enrollment, PCI 26.83 for the selected fixture |
| Figma handoff | Editable reference imported, returned node IDs and screenshot inspected |
| Independent code review | No critical issues; strict AACT parsing, prediction fallback, warning display and dataset filter reset issues fixed |

Tests cover atomic invalid imports, duplicate IDs/headers, malformed row widths, partial dates, invalid numerics, CSV/Parquet parity, source preservation, persisted metadata, literal search, auth, safe export, CT.gov pagination/failures, OpenAI request/error contracts, experiment lifecycle, temporal purging, train-only transforms, artifact matching/corruption fallback, cohort-membership disclosure, and real fitting on deterministic test data.

A Starlette test-client warning about AnyIO's deprecated BlockingPortal alias remains; it did not fail the suite.

## Boundaries

- No live OpenAI call: no user API key was supplied. The SDK request and failures are tested with controlled provider responses.
- No live Neon/PostgreSQL service provisioned. SQLite and the metadata engine contract were tested locally.
- ClinicalTrials.gov adapter tested with representative mocked HTTP responses; a real registry network import was not exercised.
- No full real AACT snapshot downloaded or scientific performance calculated.
- BioBERT weights and Cox survival model not executed. Optional dependency and metadata guards are covered; no research superiority claimed.
- Windows batch files and Docker build supplied but not executed on those platforms here. CI configuration includes Windows tests after repository push; that hosted CI has not run yet.
- The actual local app was checked via HTTP/API tests. Its local browser URL was blocked by browser policy; the public fixture-only UI was used for browser checks. No authenticated live-backend browser integration or mobile viewport run is claimed.
- The tldraw live board view did not connect, so its remote board remains empty; editable diagram source is included.

The exact clean Python environment is recorded in `verified-python-environment.txt`; frontend versions are locked in `frontend/package-lock.json`. Optional requirements are intentionally separate. Before publication, evaluate a curated real cohort and independently validate methods and claims.
