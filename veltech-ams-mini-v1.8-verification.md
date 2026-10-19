# V1.8 verification — 19 October 2026

590 automated tests passed with zero failures/skips: 150 frontend, 253 campus API, 176 Python academic-service and 11 Android configuration/packaging tests. The production React/Vite/PWA build passed. Final Docker images passed functional campus HTTP/database and private academic health checks. The original two repositories, private keys and database/media volumes were preserved.

Browser plugin tools were unavailable; system Python Playwright and Chromium were used. Public HTTPS responses used system-CA-verified urllib where Chromium did not trust the managed proxy CA. TLS verification was never disabled. The fictional public preview passed 15 workflows without JavaScript page exceptions or private API requests; private sign-in/payments are disabled.

## Results and mobile layout

Results retain source report, semester, examination session and final-grade versus assessment divisions. Filters cover subject/code and supported test, mid-test, lab, assignment and internal fields. All-assessment tables keep separate columns; a separate graph selector prevents combining different mark scales. Numeric zero remains valid, while absent/non-numeric marks leave gaps.

Large score readouts, labelled points, explicit units and touch/pointer/keyboard selection improve readability. Phone graphs scroll inside their panel and keep the selected point visible. Three focused browser workflows checked 320px layout, label/readout sizes, separate assessment lines and PDF export. Additional results coverage exercised 15 browser checks including report grouping, assessment filters and PDF/OOXML downloads. Selected-semester PDF uses a standard A4 layout; an exact reference layout was not supplied. PDF fonts support Latin text; Excel preserves Unicode and separates source reports into sheets.

Published CGPA/percentage require unambiguous source-labelled values. A complete credit-weighted source average is labelled separately from official CGPA and an individual course score. Mark ranges never become an invented grade-point scale or percentage formula. Original earned-credit headings and course/category divisions remain intact.

Twenty mobile event checks covered events/details/free and paid registration at 320, 360, 390, 844 and 1440px without page overflow. Three timetable viewport workflows checked Full-grid scrolling, room save/reload/restore and Day/Week navigation. Notification browser checks cover filters/actions, responsive layout, initial-load silence, source recovery and new-update handling; five focused partial-academic recovery checks retain earlier notifications and suppress historical recovery alerts. Workspace errors clear when their corresponding section recovers.

## Actual connected workflows

Fourteen checks used temporary fictional campus users and labelled academic records through rebuilt Docker APIs and Chromium. They cover normalized legacy course-registration metadata, source courses/warnings in the phone UI, persisted absence opt-in, student/admin boundaries, feedback submission and retry deduplication, administrator responses, contextual notification links, device sound persistence and exact-slot room update/restoration. Temporary accounts and their owned records were removed. No university traffic or writes were made.

Full timetable supplements existing Day/Week views using actual source intervals. Room overrides require a unique exact source selector and assigned academic department; social-profile edits never grant permission. Calendar holidays, follow-weekday policies and selected-student special classes remain supported without inventing attendance marks.

Feedback notifications use a durable pending event key. Regressions simulate a failure after saving a reply, then verify retry/inbox recovery delivers one alert. Source visibility and owner permissions are revalidated for social notifications. New-absence alerts require explicit opt-in, current India-date AMS absences and a durable period key; historical records and repeated checkpoints do not create fresh alerts. Sound requires user opt-in/browser interaction; phone background behavior depends on browser/OS and configured push delivery.

## Login, sync and concurrency

Valid encrypted owner-bound academic tokens are reused; simultaneous renewal is coalesced and cannot overwrite a concurrently changed link. Twelve simultaneous owner requests are covered by regressions. Accepted report checkpoints appear during sync; later contradictory grades restore the pre-job baseline.

Source-login admission permits four active attempts and eight queued, with a five-second queue deadline. Busy attempts return HTTP 503 and Retry-After before consuming a challenge. Retained and legacy manual syncs share three report slots; the legacy wait is bounded. Synthetic tests exercised 100 sign-in owners (four active, eight queued, 88 busy) and 36 sync owners with cancellation and per-owner isolation. No university load test was performed.

An actual local Docker benchmark used 24 fictional accounts and eight concurrent student flows: 144 requests, zero failures, 5.0 seconds total. Password-login p50/p95 was 591.0/1019.9ms; private workspace reads were 117.1/1631.2ms. It exercised the campus service/private academic bridge without AMS traffic. These measurements are not a production throughput or upstream latency guarantee.

Campus sessions remain rolling 30-day HttpOnly sessions, revocable at logout. Upstream clients expire after 30 minutes and are capped at 100 owners. Keep one academic worker: upstream sessions are process-local. Same-host campus replicas share Mongo sessions/rate limits and media. Multi-host session routing/object storage remain separate work.

## Historical live-source evidence

No fresh live AMS sign-in is claimed for V1.8. The authorized 18 October read returned 21 profile fields including image metadata, five courses, 173 result/assessment rows (62 final-grade, 111 assessment/internal) and 71 earned-credit rows (62 course, nine category). Exact credit headings/divisions were inspected without placing private values in fixtures. Earlier 16 October evidence included 22 timetable entries, five attendance summaries and 284 dated marks. These counts do not establish current data for every account.

That account supplied no supported Course Material document rows or Payment.aspx fee ledger. Unsupported/missing sections remain unavailable or retained with actual timestamps. No separate supported Home of VelTech private API is configured; the retired parent portal is unused. Course registration submission stays in official AMS. AMS verification remains required when AMS requests it. No private captures, credentials or cookies are included.

## Packaging and operator validation

The complete source ZIP excludes private configuration, real student records, uploads, caches, generated Android state, signing keys and APK output. Source integrity, fresh-extraction locked setup and production build are checked during delivery. The static mobile/web ZIP needs the combined backend for private accounts. Previous releases and repository main are preserved.

Windows uses PowerShell, Node 24, Docker Desktop Linux containers and the user's Atlas cluster; no Ubuntu distribution or local MongoDB is required. The supplied GitHub workflow has not run on GitHub in this task. Android includes pinned Bubblewrap tooling, a verified official Gradle wrapper, config validation, signing commands and Digital Asset Links handling. Its source generator ran against fictional fixtures and 11 packaging tests passed. No real APK was compiled, signed or installed: add the public HTTPS origin at line 2 of android/config.local.json and follow ANDROID.md with your SDK and private signing identity.

Actual Windows Desktop, live Atlas, physical camera/GPS, phone background push/sound, Internet email/SMS, merchant capture/refunds, production traffic and failover need operator validation. Free quotas are finite; camera/location checks cannot guarantee physical presence. This evidence does not claim perfect operation or unlimited capacity.
