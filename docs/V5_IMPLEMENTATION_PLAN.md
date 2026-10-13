# Clinical Trial Intelligence v5 Implementation Plan

**Goal:** Extend the preserved v4 research workflow into a project-scoped, reproducible v5 workbench.
**Architecture:** Existing research engine with an authenticated project gateway and PostgreSQL-compatible platform services; React shell retains existing screens and adds platform/evidence capabilities.
**Tech stack:** Python 3.12, FastAPI, SQLAlchemy/psycopg, scikit-learn, React 19, Vite.
**Spec:** docs/V5_DESIGN.md

## Global constraints
- Original v4 folder unchanged; verify SHA256 manifest at release.
- Never fabricate clinical data, accuracy, production readiness, current API model names or live connection tests.
- No frontend secrets. Enforce project/role access on the server.
- Preserve v4 formula semantics and evidence of missingness.
- User requested deployment later; preview may be published separately and labelled.

## Review focus
- Changing projects must invalidate cached studies, conversations and model status.
- Viewer/reviewer cannot bypass role limits by calling an older v1 route directly.
- Concurrent or expired sessions cannot access another user's conversations.
- URL imports cannot fetch internal hosts or redirect to private addresses.
- Historical outcomes and test labels must not select or fit a model.

## Tasks
- [ ] 1. Audit all four PDFs, map requirements, and checksum v4.
- [ ] 2. Write failing platform authorization/persistence tests, implement auth/projects/roles/settings and scoped research gateway, verify.
- [ ] 3. Write failing chat/import tests, implement saved provider chat and bounded import APIs, verify.
- [ ] 4. Implement React project/login/settings/chat/import views; test rendered state transitions.
- [ ] 5. Write model evaluation tests, implement additional candidates/OOD/metric uncertainty, acquire more real data if reachable, train and report results.
- [ ] 6. Add protocol review/version comparison, evidence animations and stale-status fix; verify calculations and integration.
- [ ] 7. Run regression/security/browser tests and independent review; resolve material findings.
- [ ] 8. Produce preview, complete PDF guide, verified ZIP and continuation checkpoint.

## Continuation ledger
2026-10-08: v4 copied to source/clinical-trial-intelligence-workbench-v5. No original source edits. Four supplied PDFs extracted to analysis-v5; Context7 SQLAlchemy docs consulted. Shared API contract above is authoritative; agents must report deviations.
