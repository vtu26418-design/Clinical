# Verification — veltech-ams-mini 2.2.0

Completed 27 October 2026. Tests used fictional students/staff, isolated databases and local services. No real AMS login, SMTP delivery, AWS deployment or production records were changed.

## Automated results

| Suite | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Frontend helpers/components (`npm --prefix frontend test`) | 292 | 0 | 0 |
| Campus API (`node --test --test-concurrency=2 campus/tests/*.test.js`) | 391 | 0 | 0 |
| Private academics (`python -m unittest discover -s tests`) | 220 | 0 | 0 |
| Android packaging helpers (`npm --prefix android test`) | 16 | 0 | 0 |
| Total | **919** | **0** | **0** |

The initial parallel run exposed an existing test wait based on100 event-loop turns, which could end before asynchronous browser-cache crypto completed under load. Its unchanged state assertion now has a bounded two-second wall-time wait. The completed full run above passed. The reference PDF test used the retained byte-identical supplied schedule rather than skipping its attachment check. Expected failure-injection logs and existing datetime/httpx deprecation warnings remain; they did not fail the suites.

The production Vite/PWA build passed. The campus Docker image was rebuilt with the final source; the unchanged private academic image was reused. Nine production Docker bridge checks passed: health, staff registry isolation, reviewed publication, missing-course rejection, protected-course matching, withdrawal, public checksum-verified APK download, public Asset Links JSON, and rejection of anonymous academic reads. TLS remained enabled for external tooling; no host-network bypass was used.

## Rendered app verification

Browser plugin was unavailable, so regular Playwright/system Chromium was used. Nineteen integrated checks ran against the real campus API and private academic service with zero page errors. Eight additional mobile route checks also passed. A separate focused settings/inbox fixture run exercised partial mutation failure and browser history; the independent reviewer ran28 regressions and9 final notification-routing checks.

Integrated flows: new logo launch then login; mobile banner hidden; password visibility; separate recovery view and Back; one Home live hub with exact own exam/seat; separate mobile settings index/detail and Back/Forward; read/all-read without a full workspace request; seating notification → Examinations → refresh retaining linked section; actual APK bytes downloaded and SHA verified; persistent session without animation replay; offline hub records; second student denied another student's seat; admin navigation/install.

Viewports:1440×960,390×844 and320×844. Additional attendance/timetable/academics/events/community/connections/profile/about checks at390 and320 had meaningful content, no framework overlay, no horizontal document overflow and no page errors. This is not exhaustive mobile/device acceptance.

Visual reference: `exec-42a44003-3084-4edd-b24a-ba80c65f783c.png`, a generated coordinated mobile settings/inbox concept. It and the latest rendered screenshots were inspected with view_image. Comparison points checked: Manrope text hierarchy; navy/blue/teal contrast; white grouped settings rows; blue unread treatment and contextual actions; pale canvas/dividers; consistent icons and bottom navigation; separate category/detail layout. The implementation faithfully applies this reference design system. Intentional differences retain the existing application header/noticeboard, real source labels and actual dynamic content instead of concept fixture copy. The unread summary uses factual copy. Desktop navigation is retained. The new hybrid emblem was generated from the existing project mark and the embedded public university reference; it is student-app branding, not a replacement official university seal. PDF marksheet typography/layout was not changed.

## Measured performance regressions

Synthetic fixture measurements, not live university benchmarks:

- Overlapping same-owner ordinary JSON GET consumers:2 transports →1, with cancellation isolated per consumer and no completed-result cache crossing users.
- Progress/error/final-state-only sync transitions:0 extra full overviews; a committed module-version change triggers1. Superseded rejected snapshots do not mark content applied.
- Equal workspace responses retain profile/academic/schedule references. Hidden work pauses; transient failures back off. Actual visible-clock consumers still update.
- Incremental source updates no longer feed a merged official profile back as the editable campus identity.
- Notification mutations update affected rows, roll back failures and preserve account boundaries; they do not refresh the full academic workspace.

## Android release

A genuine signed release APK was compiled for `https://app.veltech-mini-ams.me` with the final local hybrid icons. Package `in.velstudents.veltechams`, version2.2.0/code20200, minimum Android7/API24, size2,058,286bytes.

SHA-256: `a1557f1106414a6c0d6463346130215348ea44bc2ba577de5cb4bcaca03c5b4c`.

Root independently ran apksigner v2/v3 verification, compared the certificate/receipt checksum, checked release identity and absence of debug flag with aapt, and checked16KiB alignment with zipalign. The publisher also independently checks the binary before producing public metadata. The APK's public certificate and Asset Links are included. Private keystore/passwords remain outside all public deliverables and must be retrieved/backed up privately by the workspace owner for future updates.

Domain association remains pending manual deployment. Read-only probes of the existing public origin returned Cloudflare403/error1010, including the metadata path. That is not proof that every normal browser is blocked. The guide explains a narrowly scoped public Asset Links exception. No physical Android install/notification/camera acceptance test was performed. Until association succeeds, browser controls may be shown; the APK uses whatever website version is currently deployed.

## Limits

No new live AMS end-to-end source validation, fresh PostgreSQL compatibility/capacity test, campus-scale load test or production SMTP acceptance was performed. Existing PostgreSQL/DocumentDB/FerretDB configuration is retained; prior migration evidence is in VERIFICATION-PREVIOUS-V2.md. Native/API tests used isolated MongoDB storage. No database migration or secret rotation occurred.

Saved academic data remains account-scoped, read-only and expires after24hours. Newly retrieved data still depends on upstream availability and verification. Same-origin script access is not defeated by convenience device encryption. Already downloaded copies cannot be remotely withdrawn. Browser and OS permissions, Cloudflare rules, actual phone behavior, signing-key backup and free-hosting quotas require deployment acceptance checks. No zero-error or unlimited-capacity guarantee is made.

Start with V2.2-UPGRADE.md, AWS-CLOUDFLARE-MOBILE.md and ANDROID.md. The full bundle includes public APK release files separately from clean source and signing material.
