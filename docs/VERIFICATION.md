# Release verification · v4.0.1 provider update

Verified 8 October 2026 on Python 3.12.14. The core suite now reports **244 passed, 1 optional SHAP skipped**, with one third-party Starlette/AnyIO deprecation warning. This includes 27 new provider tests and the retained OpenAI contract tests. No live keys were supplied; every paid-provider response in tests is controlled.

New checks cover single-key selection for each native provider, configurable priority, manual pinning, missing-key behavior, Gemini/Claude/compatible wire formats and headers, bounded context, actual provider/model attribution, fallback for 401/403/404/408/429/5xx/network errors, disabled fallback, no rerouting of refusal/blocked/empty/bad-request responses, safe key/error handling, clean HTTPS custom endpoints and Gemini-only API health/chat. Existing core formula and model tests still pass.

Production TypeScript/Vite and fixture builds pass. All 26 shared JavaScript PCI cases plus planning/metric known answers pass. pip check is clean and the installation doctor reports ready. The updated PDF was rendered and inspected. The packaged ZIP includes rebuilt full frontend, updated offline preview, new AI_PROVIDERS.md and revised PDF. No new provider SDK dependencies were added; Gemini/Claude/compatible adapters use the pinned HTTP client already present.

Provider code does not change fitted research-model logic, formulas, source data or artifact versions. The existing v4 model examples are retained. The hosted Sites URL is the original v4.0.0 fixture preview and has not been republished for this ZIP-only provider patch. New rendered browser interaction checks, Windows/Docker execution and live-provider calls are unverified. Build checks and mock contracts do not guarantee provider account access. Model quality is not ranked from keys; Auto uses an explicit editable priority.

Reproduce provider checks with `python -m pytest -q tests/test_assistant_providers.py tests/test_api.py`. Configure a real key privately for an optional live check. See AI_PROVIDERS.md.

---

# Original v4.0.0 verification (historical)

Verified 8 October 2026 on Linux with Python 3.12.14. Software fixtures are never scientific evidence. Historical v3 verification is retained in VERIFICATION_V3.md.

| Check | Observed result |
|---|---|
| Full core Python suite | 217 passed, 1 optional SHAP skipped; one third-party Starlette/AnyIO deprecation warning |
| Shared frontend numerical checks | 26 PCI cases, invalid inputs, custom weights, planning and metric known answers passed |
| Python/JavaScript PCI parity | 805 rows compared: 800 real starter records and five software fixtures; score/category/missing fields/formula ID/methodology matched; components within 1e-13 |
| Dependencies and installation doctor | pip check clean; Python, core modules, compiled UI, starter data, configuration and writable storage passed |
| Fixture smoke test | All five fixture scores matched 25.50, 55.40, 12.60, 41.05 and 52.90; no invented fitted predictions |
| TypeScript and builds | Production build and fixture build completed successfully; offline HTML bundle has no external local-asset references |
| Actual launcher / HTTP app | Served root, both compiled assets and health version 4.0.0; loaded 800 actual registry records |
| Real duration training | All seven branches completed on 105 train / 9 tuning / 11 calibration / 64 test records; matching-source held-out prediction and report download passed |
| Real phase training | Classifier and baseline completed on 175 train / 57 validation / 59 test records; matching-source held-out prediction and report download passed |
| Research scenarios / evidence | Enrollment 120, sites 10, rate 2 gave 6 recruitment months and 21 total with startup 3/follow-up 12; source unchanged, one immutable saved scenario, valid evidence digest |
| Final model example generation | Real workflows rerun after combined-phase alias and exact conformal-rank corrections; current fitted files and reports included in examples/starter-duration-v4 and examples/starter-phase-v4 |
| Independent review fixes | Combined phase aliases retain exact combinations, unknown labels retain diagnostic spelling, exact decimal conformal ranks, and selected Research Hub study carries into Digital Twin |
| Manual | 38-page PDF generated, all-page contact sheets inspected plus detailed formula/model pages; no text outside page bounds |
| Hosted v4 fixture preview | Sites publication succeeded; private owner preview URL below. Vercel update blocked by 403 scope access; no CLI credential available |
| Release archive | ZIP integrity and extracted-file SHA256 verification recorded by the included packaging/verification tools |

## Preview and browser boundaries

https://clinical-trial-workbench-v4.nicespice2.chatgpt.site/#digital-twin

This fixture preview contains all 12 screens and interactive formula/planning/learning features. It cannot fit Python models, import real datasets, persist server history or call OpenAI. Those operations run in the full local project.

New v4 rendered-browser interaction testing was not completed: the local cloud-browser preview route was blocked, and the Sites preview infrastructure does not permit navigating the cloud browser to deployed private Sites. Build/type checks and source review are not substitutes for browser interaction tests. The PDF includes manual acceptance checks for every screen. No v4 screenshot or mobile viewport validation is claimed. The full backend and compiled asset serving were tested over actual HTTP independently of a browser. v3's earlier browser checks are historical only.

## Numerical and scientific boundaries

Exact decimal half-up PCI rounding changes 142 of the 800 real starter scores upward by 0.01 compared with v3 binary-floating rounding; all five fixture scores remain unchanged. The shared specification documents weights, caps, missing inputs, rounding and custom sensitivity modes. Known-answer arithmetic does not establish clinical validity.

The real starter's tuning/calibration partitions each have zero prolonged-duration positives, so sigmoid calibration is unavailable. Raw probabilities and conformal duration intervals are available with caveats. The recommendation uses raw tuning Brier and never test selection; read STARTER_RESULTS_V4.md for all observed scores, coverage and small-cohort limitations. No prospective/external/clinical validation or universal model improvement is claimed.

## Reproduce

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/doctor.py
python -m pip check
python scripts/run_smoke_test.py
node scripts/check_frontend_formulas.mjs
```

Use the supplied virtual environment interpreter; frontend build is `npm ci` then `npm run build` in frontend/. Load the real starter and run both model tasks to register fresh trusted local runs. Before editing a freshly extracted release, use `python scripts/verify_release.py` to validate SHA256SUMS.txt.

## Untested external / operating-system paths

OpenAI request and safe error handling are tested with controlled responses; no live provider call was made without a user key. The frozen ClinicalTrials.gov source is real; a new live acquisition was not needed for v4. No full AACT dump, BioBERT model, Cox analysis, hosted PostgreSQL/Neon or Supabase deployment was run. Optional SHAP is skipped in this core environment. Windows launchers and Docker configuration are included but were not executed on those platforms here. GitHub CI is supplied but not run remotely. Figma has an editable v4 handoff; older design/provider handoffs are historical, as documented in V4_INTEGRATIONS.md.
