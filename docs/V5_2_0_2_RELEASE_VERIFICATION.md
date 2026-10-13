# v5.2.0.2 release verification

The final PostgreSQL suite passed **433 tests**, with one optional external SHAP-library test skipped. Native CatBoost fitting and TreeSHAP additivity tests passed. Frontend TypeScript/Vite production build, 12 animation checks and 9 SSE parser checks passed. Dependency consistency passed.

Fresh Docker build used frozen npm dependencies, pinned Python packages and normal TLS verification. Runtime runs as UID 10001 and passed first-owner setup, project creation, authenticated PostgreSQL persistence, actual 800-record starter import, saved-model duration prediction and CatBoost/new-module imports. Runtime source permissions are readable by the unprivileged application account. The Dockerfile combines runtime copying to reduce VFS disk use.

Playwright was used because no Browser plugin was available. Desktop/tablet/mobile checks cover all 12 selectable graphs, source denominators, filters, persistent reordering, exports, fullscreen keyboard access, skip-link focus, mobile dataset switching, dark contrast, reduced motion, prediction/scenario study handoff, phase-history objective and actual local XAI waterfalls/provenance. No runtime errors were reported in the final reviewed flows. Server role and isolation checks are covered separately by PostgreSQL integration tests.

A clearly named local test responder verified completed streaming, real800-cohort grounding, Markdown tables, clipboard copy, reply export, attributed feedback, owner approval and reviewed guidance in the next prompt. No commercial provider was contacted; this validates application integration, not general LLM answer accuracy. The test responder is not included in application source or release assets.

The existing approved models and data are preserved. Replayed bundled duration/phase point metrics and saved predictions match within 1e-10 numerical tolerance. CatBoost was fitted on the authentic frozen cohort using the same temporal partitions; its tuning results did not beat the median baseline, which remains recommended. The fresh CatBoost manifest, metrics, held-out predictions and exclusions are included in docs/v5202-evidence. Site/stage recruitment values remain unknown when absent. A selected trial does not traverse every educational phase.

Commercial provider keys/account-supported API model IDs, mail configuration, remote TLS PostgreSQL deployment and Windows GUI operation remain operator/infrastructure checks. No production deployment or clinical validation is implied.

The extracted release also passed anonymous-access denial, first-owner/project creation, actual cohort loading, saved inference, UI serving and branch-catalog checks. All packaged file checksums are verified; private runtime files are excluded.

The end-to-end guide has 20 pages and covers setup, environment values, every section, data import, predictions, model training/review/activation, roles, assistant configuration, feedback, tests, backup and troubleshooting.

## Visual design verification

| Area | Final implementation | Evidence |
|---|---|---|
| Palette | Deep navy, teal, cool white/gray surfaces and restrained chart accents | overview-desktop.png |
| Texture | Subtle navy grain on navigation/authentication; plain chart surfaces | launcher-desktop.png, overview-desktop.png |
| Hierarchy | Compact grouped navigation, Projects launcher, clear chart headings | launcher-desktop.png |
| Evidence clarity | Genuine source counts, partial coverage, saved results and additive waterfall | prediction-desktop.png, xai-waterfall.png |
| Accessibility | Mobile dataset selector, dark text contrast, focus management and reduced motion | overview-mobile.png and final browser report |

Design concepts informed the layout. Final phase categories and all numerical chart values use real source evidence; additional More tools navigation preserves the existing research flows. The downloadable preview contains screenshots from the tested application.
