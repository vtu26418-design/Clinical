# V1.3 verification — 15 October 2026

The current recovered source was tested again; results from the lost workspace were not reused.

- Node campus API: 131 tests passed, zero failures. Includes authentication/OTP, CSRF, privacy, original collection compatibility, stories/reels/recommendations, registration concurrency, payment validation, event archives/media ownership and admin account lifecycle.
- Python academic service: 76 tests passed, zero failures. Includes conservative AMS parsing, authenticated own imports, source labeling, identity boundaries, photo limits and push endpoint validation.
- React utility/data-flow suite: 34 tests passed, zero failures. Includes class boundaries, missing marks, stale-account protection, course planning, encrypted device snapshots, Axios multipart and privacy-limited home facts.
- React production build passed. Node backend and frontend production npm audits report zero advisories in the checked dependency graph.
- Playwright Chromium: 17 preview route/layout checks and 16 connected-account desktop/phone checks passed with no page exceptions. Browser plugin was not available. Checked 1512×1060 and 390×844 layouts; login modal, ten home facts, own import, fees/course display, actual post upload, session restoration, bottom navigation and More drawer. A controlled browser clock verified next class at12:00, advancement after14:35 and current class at14:50 without a portal refresh.
- Docker: both images built; APIs and isolated Mongo fixture passed health requests. Processes run as nonroot users. Actual local SMTP→Mailpit OTP delivery/verification passed after the Nodemailer upgrade. Protected file bytes, video ranges, anonymous/other-user denial and media persistence after container replacement were checked.
- PowerShell configuration/startup flow tests ran with PowerShell7 on Linux, including persistent keys, partial configuration refusal, literal password characters, unsafe TLS options, administrator handling and development inbox selection.
- Independent review findings were fixed and covered by regressions: new event attachments require owned uploads; same-scope editors' replacement media stays readable to its event audience; predictable SSO usernames cannot block a verified student's first sign-in; downloads use V1.3 packages.

All populated integration records and email addresses were synthetic fixtures in isolated test databases. They are excluded from the exported project. This does not verify a student's live AMS login, private Home of VelTech API, real Atlas cluster, Windows Docker Desktop, merchant capture/refunds or Internet email/SMS delivery. Missing source modules remain explicit. Configure those providers on the machine where you run the app. This is an installable web app, not an APK.
