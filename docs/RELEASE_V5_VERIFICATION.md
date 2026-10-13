# V5 release verification

Date: 2026-10-09. Separate upgrade; original v4 preserved.

| Check | Actual result |
|---|---|
| Full Python regression | 299 passed, 1 optional SHAP dependency test skipped; 95.87 seconds |
| Dependency consistency | pip check: no broken requirements |
| Frontend | TypeScript and Vite production + preview builds passed |
| Saved artifacts | All saved point metrics and predictions reproduced by scripts/verify_v5_models.py |
| No training on upload/inference | Pipeline.fit and ColumnTransformer.fit_transform forbidden during real saved-model preview generation; API predictions and persistence passed |
| Authentic preview | Three chronological IDs shared by both untouched test cohorts, not selected for performance |
| v4 preservation | 261 original file hashes unchanged |
| PDF | 28 pages rendered; every page visually reviewed in contact sheets; no clipping observed |
| ZIP | 319-file archive clean extraction; all 318 listed checksums match. Extracted UI/setup/login/project/upload/approved inference/restart persistence passed; no training created |

## Exercised boundaries
Session setup/login/logout, password/session storage, CSRF origin checks, project isolation, invitations and roles, owner-only training, JSON/Excel/CSV import validation, unsafe URL denial, source preservation, persisted chat/provider transport mocks, protocol source hash/review/version isolation, approved artifact gates, restart persistence, schema rejection, no implicit activation, rollback, strict pretrial timestamp blocking, calibration/formula/temporal tests.

## Limits of verification
Native Windows and Docker were not run in this Linux environment. Paid OpenAI/Gemini/Anthropic/compatible calls and a real remote PostgreSQL account were not tested; provider tests use controlled transports. The PostgreSQL schema/driver are implemented but require your account setup and acceptance checks. Production hosting is deferred. The hosted preview is static, with browser-local interface fixtures and explicitly frozen genuine model evidence; it is not a deployed Python API or cloud database.

A browser automation capability allowed by the preview environment was unavailable, so rendered web interactions on desktop/mobile remain a manual acceptance check. Compilation is not a substitute for browser validation. Use the guide's every-screen checklist. One upstream Starlette/anyio deprecation warning is retained; no test failed.

## Scientific limits
The 800-record source is authentic; the fitted duration holdout is 64 and phase holdout is 59. The simple median baseline wins validation duration MAE and is the active duration branch. Added nonlinear branches do not establish improved accuracy. Strict pretrial mode cannot establish prospective validity from latest-state registry snapshots. No clinical, regulatory, causal or market-uniqueness claim is made. Research-only release approval is operational, not clinical certification.
