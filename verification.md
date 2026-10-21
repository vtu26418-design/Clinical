# SMTP and deployment update — 21 October 2026

463 application tests passed with zero failures/skips: 178 frontend and 285 campus API. Eighteen additional tests cover SMTP/TLS configuration, HTML/plain-text delivery, recipient acceptance, sanitized failures, bounded temporary-rejection retry, ambiguous-timeout handling, template escaping, email CLI checks and a real loopback SMTP transaction. Existing browser-bound identity challenges and durable event receipts/reminders pass with the new HTML templates.

The production React/Vite/PWA build and full campus Docker image build passed. The running image verified SMTP and delivered a multipart HTML/plain-text message to the local Mailpit inbox; inbox content was checked for the unique fictional recipient. Fifteen browser checks cover five generated email templates at 320/390/768px, with no page errors or horizontal overflow. The templates load no external tracking images or scripts. Email previews contain fictional records only.

The optional Cloudflare Tunnel Compose overlay resolves with Secure cookies, an exact HTTPS browser origin, a fixed trusted tunnel address, shared MongoDB rate limits, a private single academic worker, a localhost-only campus port and a file-mounted connector token. This is a configuration check using fictional values; no live Cloudflare tunnel or public domain was connected.

Real Internet SMTP delivery, provider approval/quotas, receipt in a student's college inbox, Windows execution and the deployed public hostname require operator checks. No real SMTP credentials were supplied, so only loopback SMTP and injected provider failures were tested. SMTP provider acceptance is not a delivery receipt. No new live AMS login, university write, real payment or signed APK was performed for this update. Academic/Python and Android source are unchanged. See EMAIL-SMTP.md and HOSTING.md for exact configuration and deployment steps.

# Current mobile/admin/PDF update — 21 October 2026

445 automated tests passed with zero failures/skips: 178 frontend and 267 campus API. Production React/Vite/PWA build passed. The package version remains unchanged. Python academic-service and Android source were not changed; earlier test evidence below remains historical.

Browser plugin not available; system Python Playwright and Chromium were used. The mobile screenshot's exact bug was reproduced: the banner photo occupied a 98px side column and clipped the college branding. The same geometry/interaction check now passes 320/390/575/760/1440px: photo stacks below copy on mobile, branding stays inside the photo, the page does not overflow, and price/saved/search filters respond. Thirteen additional browser surfaces cover unified login in light/dark at320/390/1440px, administrator creation, limited management, read-only academics, faculty forms and student results.

Seven actual Node API/MongoDB browser workflows with isolated fictional records passed: single-login/old-URL redirects; owner creation of limited event/support and academic-read-only admins; notice create/edit/delete; limited module visibility and academic 403 denial; issue archive with retained submitter history; automatic faculty/student/academic-only destinations; student institutional-email login, cookie refresh,79% at 8.4 CGPA and semester PDF download. No page exceptions or server 500 responses were observed. A staff-routing race and a suspended support-tab reset were found during these checks and fixed.

Twelve focused server tests cover credential-based role discovery, staff-password isolation from AMS, browser-bound university verification, explicit administrator permissions, owner protection, child-admin permission ceilings, immediate session revocation, academic read/write separation, linked-student password-reset restrictions, form-response privacy, notice CRUD, issue archival and account deactivation. Existing owner administrators retain their permissions; new admin accounts always store an explicit permission list.

PDF checks reproduce the previous one-line heading and top-aligned cells, then verify two balanced university-heading lines, vertically centred column headings, consistent 24pt left margins and all rendered text within A4. The source grade/credit/semester grouping remains unchanged. Existing long-field/multipage and export privacy tests still pass. Published source values retain priority; unavailable summaries remain blank. The requested(CGPA−0.5)×10formula is unchanged.

No new live AMS login or university write was performed. Private source credentials remain private. The browser's university data is a labelled test fixture; the hosted preview is fictional and disables private sign-in/payments. Windows-host execution, real email/payment delivery, physical-phone notification delivery and signed APK publication remain deployment checks for the operator. See ADMIN-ACCESS.md and LOGIN.md for the exact delivered permissions and sign-in flow.

A final phone check also verifies that academic-directory names and IDs occupy separate readable lines. Audit/SMS logs require the audit permission even when an academic proxy path is URL encoded.

---

# Current update — 21 October 2026

432 automated tests passed with zero failures/skips: 177 React/frontend utility tests and 255 campus API tests. The production React/Vite/PWA build passed. No Python academic-service code or Android packaging code changed in this update; their earlier test results below are historical, not a new live check.

Browser plugin tools were unavailable; system Python Playwright and Chromium were used. Actual Node campus API and MongoDB tests used isolated temporary fictional users and source-shaped academic fixtures. Eight connected workflows verified separate sign-in areas, faculty/admin credential login and reload, cookie-backed student restoration, the requested 8.4 CGPA → 79% display, administrator batch overrides, and real PDF/Excel button downloads. Staff workspaces no longer try to connect to a student AMS workspace. Twenty-four light-theme and twelve dark-theme page/viewport checks covered 320px, 390px and desktop, including More navigation, results, Events, About, role sign-ins and batch-rule administration. They produced no page exceptions, server errors or page-width overflow. Dark sign-in tab contrast was corrected during visual review.

The fictional preview passed17 workflows, including semester PDF download, requested manual percentage calculation, results filters/graphs, event registration, reels/comments, source credit export, device downloads and mobile navigation, without private API requests or JavaScript exceptions. Public HTTPS asset responses were obtained with system-CA-verified urllib where Chromium did not trust the managed proxy certificate; TLS verification was not disabled.

The new semester statement uses a public university logo and the provided reference's layout, not its student's identity/marks. Tests cover official/social identity separation, minimal identity whitelist, six subject columns, source summaries, explicit zero totals, incomplete/conflicting records, separate attempts, selected filters, long-page continuation and valid PDF cross-reference offsets. PyMuPDF rendered the browser-downloaded A4 PDF; header, fixture identity, subjects, image and all text bounding boxes were checked. Excel still omits student identity and preserves literal source values.

Percentage defaults to **(CGPA − 0.5) × 10**, supplied by the project owner. Published AMS percentages take priority, then a confirmed exact official batch/programme rule. Admin changes are role-checked and audited. No official regulation formula was independently verified: online secondary sources conflicted and the cited primary PDF returned403.

No new real AMS login, source-layout change, Windows-host run, real email/payment charge, physical-phone push test or compiled APK is claimed in this update. The private academic worker and university's genuine verification/expiry requirements remain unchanged. Supported records depend on the student's live AMS session; unavailable sections stay unavailable. The earlier verification sections below are historical.

---

# Current V1.8 update — 20 October 2026

607 automated tests passed: 163 frontend, 253 campus API, 180 Python and 11 Android configuration tests, with zero failures/skips. Production React/PWA build and rebuilt Docker campus/database/private academic health passed. Browser plugin tools were unavailable; system Python Playwright and Chromium were used. The hosted fictional preview passed15 workflows with no private API requests or page exceptions. Fresh source extraction, frozen npm setup and the production build passed. A final dark-mode check also verified result calculation settings and percentage-card contrast. The earlier verification below remains historical evidence for previous V1.8 builds.

The previous Results-only update moved the graph but did not supply missing numeric inputs. This revision fixes blank-field source credit joins, course/semester normalization, ignored result-row GPA/CGPA/overall percentage, summary-only rendering and standalone labelled result summaries. Explicit published values have priority. Source grades are preserved; the visible editable 10-point scheme and requested CGPA×10 conversion produce labelled estimates only. The S/A/B, S/A+/A and O/A+/A presets expose their mappings; use the one that applies to the regulation. No universal grading/conversion rule is claimed. Unknown grades, conflicting attempts or missing source credits do not produce a complete calculation. Identical report copies and explicit zero-credit audit rows do not block an otherwise complete overview.

The top line graph switches between cumulative CGPA and semester GPA and supports touch/pointer/keyboard readouts and crosshairs. Overall values do not change with detail filters. Five rebuilt-Docker/browser workflows use temporary fictional source-shaped records, including letter-only grades with real credit joins, editable scale persistence, PDF export, source-published summary-only results and keyboard graph selection. They passed at320/390/1440px with no page exceptions or overflow. These are source-shape/integration checks, not a new real AMS login.

Actual HttpOnly-cookie QA verified account restoration across refresh/reload, a simulated service-worker controllerchange reload, transient503 retry without credentials, no private profile in local/sessionStorage and explicit cookie/database session revocation. Account-generation guards discard late successful responses and conflicts from previous accounts. Concurrent restore attempts coalesce. Polling tests observed zero requests while hidden and zero overview reloads for unchanged sync status; visibility resumes polling. The genuine university30-minute/process-local session expiry is unchanged and can require manual upstream sign-in after restart.

Branding QA passed18 page/viewport/theme checks for login, Events and About at320/390/1440px in light/dark themes. The Vel Tech campus photograph loads; official links, search, tabs, recovery, registration/ticket flow and More navigation work. Navy/blue/gold accents add no decorative red. Mobile toast/menu geometry no longer overlaps. No real merchant charge, live university write, Atlas/Windows/physical-phone push validation or compiled APK is claimed. Public preview contains fictional data and no private login/payment access.

---

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

## V1.8 Results-only ZIP update

The version remains 1.8.0. The overall all-semester graph is now the first Results dashboard element, followed by overall CGPA and percentage. These remain independent of selected report/semester/subject/assessment filters below. Published CGPA takes precedence; otherwise complete available course credits and numeric grade points produce a labelled calculated value. Incomplete/repeated records do not produce a calculated CGPA, and percentage conversion is never invented. The top graph plots credit-weighted semester GPA. Detail graphs and existing PDF/Excel exports remain available below the filters.

152 frontend tests passed for this update, including two overall-calculation/provenance regressions; the production build and phone/desktop browser checks passed. Backend/Android code is unchanged from the preceding V1.8 verification; those suites were not rerun for this Results-only change.


## Login welcome screen update

The shared login now shows the animated original logo, then the authenticated account photo/name and available official student ID/department, followed by an indeterminate sync indicator on an animated blue background. Failed credentials and required AMS verification release back to the form. Saved-session restoration uses the same welcome. A continue action appears after 3.5 seconds; an eight-second post-authentication bound prevents slow academic sections from indefinitely blocking the workspace. Background source work continues normally.

All 178 frontend tests passed after this change. The production Vite/PWA build passed. Chromium/Playwright exercised nine sign-in/sync scenarios plus long-name/short-phone and faculty-routing checks: 320×740, 390×844, 1440×1000 and 320×568 viewports; no page errors or relevant console errors/warnings. The checks covered loaded photos, reduced motion, missing-image initials, wrong-password feedback, required verification, slow-sync continuation, automatic release, saved-session restoration and sign-out. The faculty flow made no student academic requests. The Browser plugin was unavailable, so the existing Python Playwright and system Chromium were used.

Screenshots and the short animation preview use fictional records and intercepted API responses, not real student or university login data. No new live AMS login, university performance test, backend regression run, Android compilation or physical phone test is claimed for this frontend update. Backend, SMTP and Android implementation remain the preceding delivered source. Private configuration is excluded from delivery; existing configuration and persistent keys are retained by the operator during upgrade.

## Login, sync and deployment update — 21 October 2026

This entry supersedes the earlier welcome/assessment rendering descriptions. The package remains 1.8.0. The welcome now mounts only after successful authentication (after the manual CAPTCHA when AMS requests it). Open Home is available when core/majority modules update, with a 3.5-second escape for a slow source. Choosing Wait for all sections cancels the normal early/eight-second release and opens the workspace when the current sync reaches a terminal state, including partial/failed. A terminal failure is not presented as successful source completion. Identity remains owner-bound; opening Home does not create another AMS login.

The hard-coded 10-second saved-session timeout was removed. Session reads use a 30-second allowance and at most one transient retry; credential/CAPTCHA POSTs are never automatically resubmitted. Timeouts have actionable messages. One private `/campus/workspace` read replaces seven internal requests on current deployments, with compatibility for older private services. Concurrent frontend reads share only an active same-account request. No source concurrency/admission limit was increased. The new endpoint filters public schemas, isolates optional section failures, checks the active student and sends private/no-store headers.

Final/semester results retain their line graphs, overall CGPA/percentage and selected-semester exports. Assessment/internal views have no graphs or GPA controls; original test/mid/assignment marks, report divisions, filters and exports remain.

**667 automated tests passed, zero failures/skips:** 184 frontend, 289 campus API, 183 Python academic-service and 11 Android packaging/configuration tests. Focused regressions were observed failing before the corresponding timeout/progress/workspace implementations, then passing. The final production Vite/PWA build passed. Existing Python deprecation warnings remain; they are not test failures.

Eleven Chromium/Playwright workflows passed using fictional intercepted API records, with zero JavaScript page exceptions. Browser plugin tools were unavailable. Checks covered CAPTCHA-first gating, the authenticated logo/profile sequence, Wait remaining open past eight seconds and automatic completion after partial sync, Open Home while still syncing, long names at 320×568, 390×844 and desktop geometry, default early release, a slow initial read, saved-session 503 retry without new credentials, faculty routing with no student academic calls, reduced motion, assessment tables/filters/XLSX and semester PDF downloads. Final-result CGPA 8.50 and the requested conversion to 80.00% were checked against fictional numeric fixtures. The reference university records were not used as demo data.

Both Docker images built from the current Dockerfiles with TLS verification enabled. A separate temporary Docker/Mongo stack verified actual campus cookies, private-service bootstrap, the new owner-scoped contract, owned attendance/timetable, session restoration and production web serving. Four synthetic owners made four initial and sixteen concurrent saved-workspace reads with zero failures. Saved-read median/max were 39.7/51.7 ms; maximum first read was 111.7 ms. These are local synthetic measurements, not a university/production throughput claim. Test containers/databases/configuration were removed; existing stacks, private keys and volumes were preserved. The managed Docker client's default proxy values needed explicit private-host bypass flags in the isolated QA invocation; the distributed Compose files already configure their private service names.

No new real AMS login, live Atlas deployment, Internet SMTP delivery, physical phone installation/background push or signed APK is claimed for this update. Upstream university sessions can still expire or require manual verification. Configure your public HTTPS origin and real SMTP before release, follow DEPLOYMENT-UPDATE.md, and complete the operator checks there. The phone deliverable is the installable web/PWA plus Android packaging tools; a signed APK needs the operator's origin/signing identity.
