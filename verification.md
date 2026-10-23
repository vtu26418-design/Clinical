# Verification — administration and examination update

Project version remains **2.0.0**. Verification completed with controlled fixture accounts; the supplied university schedule was used for document parsing. No production university records or real email recipients were changed.

## Fresh automated checks

| Suite | Passed | Failed |
|---|---:|---:|
| Campus Node API (`services/campus`: `npm test`) | 362 | 0 |
| React helpers/components (`frontend`: `npm test`) | 220 | 0 |
| Private academic service (`python -m unittest discover -s tests`) | 217 | 0 |
| Android packaging helpers (`android`: `npm test`) | 11 | 0 |
| Total | **810** | **0** |

The frontend production build and both production Docker image builds succeeded. Six production-image smoke checks passed over the ordinary Docker bridge: startup/health, staff registry isolation, reviewed publication, missing-registration denial, private protected-course matching, and removal. Docker's client proxy defaults overrode the smoke script's env-file `NO_PROXY`; explicit private-peer `NO_PROXY` corrected the harness. The shipped Compose files already define it explicitly. TLS verification remained enabled; no host-network workaround was used.

Existing dependency deprecation notices (Starlette TestClient/httpx and legacy datetime.utcnow uses) remain in test output. They did not fail the suites.

## Browser coverage

The Browser plugin was unavailable; regular Playwright with system Chromium was used. Actual signed-in fixture accounts exercised the campus API and private academic service, not a fabricated frontend-only success response.

- Import the actual two-page reference PDF: **35 rows**, correct merged date groups (26–30 October and 2 November 2026), 16:30–18:00. OCR/title ambiguity remains visible for staff review.
- Create draft, review, publish, edit draft without changing live student rows, republish, remove and revoke student access.
- Two students with different protected registered courses receive different, exact matching examinations. AMS examination announcements are excluded from the student app examination list.
- Downloaded original schedule PDF matches the uploaded file bytes.
- Generate a bulk seating draft from a multi-course roster, exact course filter, rooms/capacity, review, publish; own-seat-only visibility, private original, stale revision revocation.
- Calendar holiday and Saturday-following-Monday behavior, student reminders, current-date attendance isolation, independent calendar refresh.
- Admin overview/navigation, role presets/action ceilings, form editing with stable question IDs, response locking and state-only changes after answers, event mutation control visibility.
- Screens at **1440, 390 and 320 pixels**: no page horizontal overflow; no browser page errors in completed checks.

Visual review compared the generated admin registry concept against rendered registry/screens: navy grouped navigation, white surfaces/pale-blue canvas, blue/teal actions, readable hierarchy, responsive stacked controls. Actual data and existing branding replace concept fixture copy. Long import review notes collapse into an accessible expandable list.

## Important limits and upgrade behavior

- New protected AMS audience caches deliberately do not trust older mutable/imported profile/course fields. Existing verified students need **one successful AMS refresh** to populate these caches. Missing regulation/batch/semester/section is not guessed. This update did not perform a new live AMS login or verify upstream availability.
- This update ran API/Python integration tests against isolated MongoDB databases and production Docker services. Version 2.0.0 PostgreSQL/FerretDB compatibility and migration checks are recorded in `VERIFICATION-PREVIOUS-V2.md`; a new PostgreSQL capacity/load test was not performed here. No database migration or existing production data destruction occurred.
- Published schedule corrections create a new examination revision. Old seating is hidden and must be reviewed/released for the new examinations rather than silently reused after a changed date/audience.
- Source parsers are bounded and reviewed, not universal OCR. Unsupported/image-only documents need a structured CSV/XLSX transcription. University publications are split into schedules of at most 500 exams; bulk seating is at most 5,000 students per release.
- No load-test or unlimited/free-hosting capacity claim. SMTP provider delivery, production HTTPS, browser camera/location permissions and real device notification behavior require the deployment's own configuration and acceptance checks.
- Windows scripts/configuration are included; this Linux cloud did not execute Windows PowerShell. A signed APK was not built or installed on a physical device. Domain association/signing and the user's later HTTPS address remain required. The built web package is a PWA preview, not an APK.

See `UNIVERSITY-PUBLISHING.md`, `V2-UPGRADE.md`, `EMAIL-SMTP.md` and `DEPLOYMENT-UPDATE.md` for operation/configuration.
