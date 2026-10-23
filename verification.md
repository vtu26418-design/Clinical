# Verification — veltech-ams-mini 2.1.0

Verified on 23 October 2026 using fictional campus accounts and isolated academic databases. No production university records were changed and no real email recipients were contacted.

## Automated checks

| Suite | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Campus API — node --test --test-concurrency=2 campus/tests/*.test.js | 390 | 0 | 0 |
| Frontend — npm --prefix frontend test | 253 | 0 | 0 |
| Academic — python -m unittest discover -s tests | 220 | 0 | 0 |
| Android helpers — npm --prefix android test | 11 | 0 | 0 |
| Total | **874** | **0** | **0** |

The Python suite passed all 220 cases, including the supplied reference PDF check using the retained byte-identical original download. The production Vite build and both Docker images built with TLS verification enabled. Six Docker smoke checks exercised startup/health, staff access separation, reviewed publishing, missing-course rejection, exact protected-course matching and withdrawal over the ordinary Docker bridge. The API tests were run with bounded concurrency. Earlier interrupted runs after the cloud restart/disk exhaustion were discarded; this table refers to completed runs after restoring the synthetic database and clearing disposable build cache.

## Browser checks

The Browser plugin was unavailable; regular Playwright with system Chromium exercised real campus and private academic services. The completed main run has 20 checks with no page errors; five additional checks cover event creation and logout.

- Imported the supplied reference schedule, 35 rows. Row 1 and Row 21 remain visible on desktop and phone, with continuous pagination numbering. Parsed dates/session times retain review warnings rather than inventing corrections.
- Saved and published a course-targeted schedule. Student examination data remains visible through a background poll, with the active academic section retained.
- Published a private staff document through the actual file upload. The eligible student downloaded byte-identical PDF data; a student registered for another course could not see it.
- Refreshed the saved signed-in workspace without replaying the welcome animation. Disabled the browser network, refreshed, opened saved academic sections, and downloaded a previously saved owner-scoped PDF byte-for-byte.
- Offline logout remained logged out after refresh and reconnect; server logout reconciled without automatically signing in.
- Used all five event creation steps to publish hybrid format, venue, meeting link, structured agenda and attendance instructions. Nonparticipants could not read the meeting link through list or detail responses.
- Exam import, document registry, publishing directory, event creator, student home and academic pages fit 1440, 390 and 320 pixel widths without page horizontal overflow. The Home layout was retained; exam announcements use the existing reminder section.

Focused tests additionally cover 24-hour announcements / 72-hour reminders in IST, session expiry, official department aliases, ambiguous/unknown choices, cross-owner device cache rejection, read-only mutations, duplicate/overlapping sessions, concurrent publication, private attachment signatures, file bounds and admin action ceilings.

Visual review compared the generated event-creation concept with rendered screenshots: navy navigation, pale blue canvas, white surfaces, blue/teal actions, readable hierarchy and a collapsible mobile preview. Existing navigation and real campus imagery were retained. The concept's unimplemented draft control was not added.

## Limits

This release did not perform a new live AMS login, inspect a currently authenticated university browser or verify every upstream page. The document parser changes were checked against bounded deidentified fixtures. Unsupported source sections show unavailable data and preserve prior supported records. AMS verification cannot be bypassed. Older accounts need one successful source sync to populate protected official audience fields.

New API/Python integration and Docker smoke checks used isolated MongoDB storage. Prior PostgreSQL/DocumentDB/FerretDB compatibility and migration checks are in VERIFICATION-PREVIOUS-V2.md; a fresh PostgreSQL or campus-scale load test was not run for this update. The default Docker storage configuration is retained. No production migration was executed.

Device cache is read-only, account-scoped, encrypted at rest and expires after 24 hours. Same-origin scripts can use the device key; this is not a replacement for authentication or protection against a compromised browser. Downloaded copies already on a student's device cannot be remotely withdrawn. Empty/new devices need an online visit first.

Windows PowerShell, a signed APK and physical-phone notifications were not tested in this Linux cloud. PWA installation needs HTTPS; Android release requires the user's public URL, signing key and domain association. SMTP provider delivery, upstream service availability and free-hosting quotas require deployment acceptance checks. No unlimited storage, capacity, or zero-error guarantee is made.

Start with V2.1-UPGRADE.md. Detailed administration, SMTP and hosting guides remain included.
