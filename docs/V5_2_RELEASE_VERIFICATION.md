# v5.2.0 release verification

Verified 11 October 2026 against the supplied repository checkout, base commit `0563af1cf49906558859f027dee29915f77658b5`, plus the v5.2 changes in this release. No push or deployment was performed.

## Results

| Check | Observed result |
| --- | --- |
| Python environment | Python 3.12.14; pinned core/dev/docs dependencies installed; pip check passed |
| Repeatable cloud installation | Setup script rerun successfully; existing private configuration preserved |
| Full Python suite | **368 passed, 1 skipped**, 60.55 seconds; optional SHAP test skipped |
| Native provider streaming | 34 automated cases cover four providers, completion, limits, refusal, disconnect, timeout, authorization, quotas and transaction rollback; mock transports |
| Browser SSE parser | 8 checks passed: fragmented bytes, Unicode, CRLF, incomplete stream, errors, HTTP failure and output limit |
| Shared frontend formulas | 26 shared PCI cases plus invalid input, custom-weight, planning and metric known-answer checks passed |
| Frontend | Production and preview TypeScript/Vite builds passed |
| Software smoke | Five labelled fixtures passed; no scientific validation claimed |
| Live application | 11 acceptance checks passed; no browser page errors |
| Public research sources | ClinicalTrials.gov, PubMed and openFDA each returned two cited records in live requests |
| Desktop/mobile | Home, pipeline controls, source notice, prediction evidence, scenario save and mobile navigation passed; 390px viewport had 390px document width |
| Standalone HTML | Home, prediction evidence and scenario flow passed with no additional network requests or page errors |
| Guide | 19-page PDF generated; cover and representative table page visually inspected |
| Independent review | Spec and code/security review passed with no outstanding important or critical findings |
| Startup | Current application started using scripts/start.py; HTTP health and account bootstrap passed |
| Packaged extraction | All 355 packaged source/asset hashes matched; extracted server health, first-owner bootstrap and built UI passed using the verified Python environment |
| Archive hygiene | ZIP integrity, unique safe paths, runtime/dependency exclusions and exact known local-secret scan passed |

The full suite emits one existing Starlette/AnyIO deprecation warning. The intentionally self-contained preview bundle emits a Vite size warning (about 712 kB of JavaScript); the production bundle is about 641 kB. These are warnings, not build failures. The cloud browser policy blocks direct file:// navigation; the exact standalone HTML was tested over a loopback static server, with no external assets or API requests. Direct desktop file opening was not exercised by this browser.

## Live workflow checked

An isolated temporary account store was used to create the first owner, sign in, create a project, import the authentic 800-record starter cohort, predict two records with the approved saved artifact, and retrieve the persisted prediction batch with source/model hashes. Both requested predictions were available. A live PubMed result was searched, saved using canonical server evidence and retrieved from the project library.

Browser checks covered the authenticated home, inference, sources and saved library. A controlled SSE transport fixture checked Markdown/table rendering and confirmed raw script HTML remained inert. This fixture did not contact a paid provider. Missing mail configuration produced an explicit unavailable response. Temporary acceptance accounts and data are excluded from the archive.

## Models and training

Saved artifact verification reproduced 756 duration prediction rows across nine branches and 232 phase prediction rows across two branches. All saved point metrics replayed within numerical tolerance; source identifiers, raw-page reconstruction and hashes passed. Approved model artifacts were not modified.

The documented duration training command also completed into a separate candidate directory: 800 input rows, 312 eligible rows, 488 excluded rows and 123 temporally purged rows. All nine experiment branches were produced. This checks that the workflow runs; it is not a claim of improved accuracy or independent generalization. The candidate was not promoted and is not bundled as an approved model.

Cohort monitoring compared the 800-record starter source with the recovered 1,800-record incomplete acquisition. It found 20 shared trial IDs and requested review. Its ten tests include categorical missingness changes and all-missing inputs. No automatic training or activation occurs.

## Reproduce

From the project root after setup:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .venv/bin/python -m pytest -q
.venv/bin/python scripts/run_smoke_test.py
.venv/bin/python scripts/verify_v5_models.py
node scripts/check_frontend_formulas.mjs
node scripts/check_stream_parser.mjs
cd frontend
npm ci
npm run build
```

The Node checks require frontend dependencies. The PDF additionally uses requirements-docs.txt. For a packaged extraction, run `python3.12 scripts/verify_release.py` before editing files. The ZIP includes a manifest of every packaged source/asset file; the adjacent release checksum/receipt identifies the ZIP itself. Checksums demonstrate integrity, not publisher authenticity.

Machine-readable receipts and rendered screenshots are under docs/v52-evidence. Public API results are time-dependent. Integration behavior is covered by the repository tests; browser acceptance is described above and in its receipt.

## Boundaries

Paid AI access, real email delivery, remote PostgreSQL concurrency, Docker builds, hosting and production deployment were not exercised. The uploaded v5.1 ZIP exceeded the transfer tool's 32 MiB limit, so this is an upgrade of the selected v5 Git checkout, not a verified v5.1 merge. See V5_2_CHANGELOG.md for requested features needing further datasets or infrastructure.

Cloud setup/start instructions and seven API hostnames were saved to the environment configuration draft. Review/save the environment settings and publish to retain them for future tasks. Processes must restart in a new environment. Core saved inference requires no external service key.
