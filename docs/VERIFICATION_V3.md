# Release verification · v3.0.0

Verified on Linux with Python 3.12.14. Synthetic test fixtures are never scientific evidence.

| Check | Observed result |
|---|---|
| Full core Python suite | 111 passed, 1 optional SHAP skipped; one third-party deprecation warning |
| Dependency consistency | pip check: no broken requirements |
| Fixture smoke script | 5 records validated; expected descriptive PCI and unavailable model predictions |
| TypeScript + production and demo builds | Successful |
| Installation doctor | Python, core modules, compiled UI, starter data and writable storage passed |
| Actual launcher, full local HTTP app | Served page, both compiled assets and health; loaded 800 real records |
| Real duration training via API | Completed six models, matching-source study prediction and held-out CSV download |
| Real phase training via API | Completed classifier/baseline, probabilities, recorded phase and held-out report download |
| Public Vercel v3 preview | READY; opened in supported Chrome cloud browser |
| Browser interactions | Phase III tab changed content/diagram; Step advanced design; Play reached Review and stopped; quiz answer showed correct feedback; duration and phase training preview boundaries worked |
| Source integrity | Frozen raw/canonical checksums and replay tests pass |
| Independent review | Fixed punctuated/Unicode phase redaction, whole-day duration grouping and phase metrics API/export contract |

Browser page identity was Clinical Trial Intelligence Workbench at the published #academy route, with meaningful content and no framework overlay. Desktop screenshot evidence is included with the release delivery. Captured console entries were browser-extension metadata errors, not application errors. No mobile viewport validation is claimed. The real backend was verified over HTTP; the public preview uses fixtures, so it does not exercise a browser connected to that backend.

The real starter training retains 105/20/64 duration rows after purging and 175/57/59 phase rows. Both predicted an actual held-out record through the API. The phase workflow was rerun after the API metrics-filename correction. Full manifests, fitted examples and reports are in examples/, and STARTER_RESULTS.md states exact scores and limitations.

## Reproduce checks

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/doctor.py
python -m pip check
python scripts/run_smoke_test.py
```

Use the supplied virtual environment interpreter. Frontend: npm ci and npm run build in frontend/. The release contains SHA256SUMS.txt; run python scripts/verify_release.py from an extracted copy before editing files.

## Boundaries

- OpenAI request/error contracts are tested with controlled responses. No live provider call was made because no user key was supplied.
- Live ClinicalTrials.gov source acquisition succeeded. The frozen 800-record subset is real but not the whole registry or a representative population.
- No full AACT snapshot, BioBERT weights, Cox analysis or live Neon database was run for v3.
- The optional SHAP test is skipped in this core environment; historical v2 optional-module verification is preserved in VERIFICATION_V2.md.
- Windows batch launchers and Docker configuration are included but were not executed on Windows/Docker here. GitHub CI is supplied but not run remotely.
- No prospective, external or clinical validation is claimed. Tree models were added without claiming universal performance improvement.
- Remote Figma/MagicPath/Notion handoffs reflect v2; the ZIP and hosted preview contain v3. See INTEGRATIONS.md for exact plugin outcomes.
