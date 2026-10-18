# veltech-ams-mini V1.7

A combined React application for academics, attendance, campus events, student community and placements, using the original UniEve logo. One project contains the React frontend, campus API and private academic API.

[Open the public web preview](https://html-preview.github.io/?url=https://raw.githubusercontent.com/vtu26418-design/Clinical/acbf18873d418947c7086bf57fde03adabf476f3/preview.html#/home) · fictional student and event data; private login/payments are disabled.

## V1.7 · 18 October 2026

- Posts and reels respond immediately to likes, saves and comments, reconcile server counts and restore failed actions. Comments include inline replies, five-minute edits, deletion and draft recovery while staying in the current feed/viewer.
- Results retain AMS report, examination-session and semester divisions. The stock-style line/area graph supports touch, pointer and keyboard inspection. Credit Earned Details preserves the source's exact headings and separates course rows from category summaries. CGPA requires published values or complete explicit credits/grade points; mark ranges do not become invented grade points.
- Verified AMS sign-in opens the workspace before the longer academic reports finish. Individual sections appear as they arrive, with live sync status and automatic completion updates. Owner-bound jobs are limited to three concurrent upstream syncs and one pending/running job per owner. Logout/expiry cancels that owner's job.
- Timetable shows an actual date and all seven weekdays. Sunday/holiday labels appear on Home and Timetable; source Saturday periods remain working days. Authorized administrators can declare a holiday, follow another weekday or add special classes for selected verified students. Department coordinators stay in their assigned campus department.
- Fixed narrow-screen wrapping, the More menu contrast, stale sync responses and account changes across browser tabs.

The authorized read-only AMS check on18 October returned student fields, five current courses,173 result/assessment rows and71 credit rows (62 courses and9 category rows). Fees and documents did not return supported records in this account. No separate supported Home of VelTech data API is configured; unavailable data remains explicitly unavailable.

## Run the React project on Windows

Install **Node.js 24 LTS** and **Docker Desktop**. Start Docker Desktop with Linux containers. You do not need an Ubuntu distribution, Bash scripts, Python, or a local MongoDB installation. MongoDB runs in your own **Atlas cloud cluster**.

1. Extract the **source ZIP** into `P:\Intenship\veltech-ams-mini`.
2. In Atlas, create a database user with read/write access to `unieve_campus_v1` and `unieve_campus_attendance_v1`. These database names are retained for upgrades from V1.2. Add your current public IP in Atlas Network Access. Copy **Connect → Drivers → Node.js** `mongodb+srv://...` URI and replace its password placeholder; URL-encode reserved password characters. Your Atlas website password is different from the database user's password.
3. Open Windows PowerShell in the extracted folder and run:

```powershell
cd "P:\Intenship\veltech-ams-mini"
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1
npm run setup
npm run dev
```

Setup asks for the Atlas URI using hidden input, generates private encryption keys, builds the Docker APIs and React production bundle, and creates your first administrator. Choose a separate campus administrator password: at least 16 characters, upper/lowercase, number and symbol; at most 72 UTF-8 bytes. Open **http://localhost:5173** for the React development app. The built application is also served at **http://localhost:4100** by Docker.

After the first setup, start the APIs with `npm run dev:api` or `Start.ps1`, then start React with `npm run dev`. Run `npm run doctor` to check dependencies, Docker, private configuration and API/database health. `npm run build` builds the React frontend. Changes to backend code require `docker compose build`, then `Start.ps1`.

```powershell
# Start or stop the Docker application later
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Stop.ps1

# Change Atlas or the production web/API port
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1 -ReconfigureAtlas
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1 -Port 4200

# Match a changed API port when running Vite
$env:CAMPUS_PORT = "4200"
npm run dev
```

`-ConfigureOnly` writes private configuration without building or starting. `-UseExistingAdministrator` requires an administrator already in the selected database. Scripts preserve existing private keys. `Stop.ps1` retains Atlas data and uploaded media; avoid `docker compose down -v` unless you intentionally want to remove local media. Keep secure backups of `.private` and the `campus-media` Docker volume. Never upload them with your project.

## Upgrade an existing V1.6 or V1.7 folder

Back up the existing project, `.private` configuration and persistent media first. Stop the app with `Stop.ps1` and replace application files with this ZIP's contents. Keep the original `.private`, `.env`, production settings, database names and Docker volumes; do not regenerate encryption keys or remove volumes. Then run from the updated folder:

```powershell
npm run setup
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1
npm run dev
```

Setup reuses existing private configuration and checks whether an administrator is already present. A service restart ends its temporary AMS connection, so sign into AMS again to refresh source records. An installed PWA may show **Reload update**; use it to load the new shell. App accounts and stored database records are retained.

## Accounts, email and the development inbox

The campus account and AMS account serve different purposes. Campus accounts control community, events and roles. An AMS connection accesses only the student's own academic records. Staff permissions come from an administrator's assignments, never an email prefix or a browser-selected role.

Email verification and password reset require SMTP or Brevo. Configure your provider only in `.private/campus.env`; see [provider settings](docs/providers.md). Without a provider the API reports that email is unavailable; it does not reveal verification codes in responses or logs.

For college demonstrations, an optional **local development inbox** receives OTP and event emails without sending Internet email:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1 -DevelopmentInbox
```

Open **http://localhost:8025** on the same Windows computer. This inbox contains local test messages and must not be used as a public email service. It does not prove delivery to real student email accounts. The override exposes only the inbox's web port on loopback; SMTP remains inside Docker. To disable it, stop the application, remove `.private\dev-mail.enabled`, run `docker compose -f compose.yaml -f compose.dev-mail.yaml stop mailpit`, and start again. Configure real SMTP before relying on account recovery for real users.

## University data and course registration

AMS is reached at `https://ams.veltech.edu.in/Default.aspx`. This application starts with your username/password and prepares its own server session. If AMS requests CAPTCHA, you must complete that verification in this app. Being signed into AMS in another browser does not sign this application's server in. Enter only your own credentials in the app. Never put them in source, screenshots, ZIPs or support logs.

**Live AMS was verified for one authorized account:** the fresh18 October read returned21 profile fields (including image metadata), five current courses,173 result/assessment records and71 credit records:62 course rows plus9 category rows. Earlier16 October evidence also verified22 timetable entries, five attendance summaries and284 dated class marks. The date/hour attendance layout uses Student Session as its denominator; planned Total Session and Overall % are not attendance totals. Read-only year/result-type report selections retrieve regular, arrear/revaluation, internal and assessment reports when records exist. This account exposed no fee statement, receipt history, documents or examination schedule; those sections correctly remain unavailable. This check does not establish every account or future layout. Home of VelTech is a separate student-developed AMS client; no supported separate API was found. The retired parent portal is unused.

The adapter reads supported labeled profile, course, attendance, timetable, results, credits, examination, fee and document tables from the authenticated AMS session. It follows only explicitly discovered safe AMS links and the three inspected read-only report-selection forms. It never submits feedback, university registrations or payments. Changed layouts need an adapter update; unknown sections remain unavailable. Results, fees and documents in the active academic screen require AMS provenance. Legacy imports may remain in storage, but are not presented as current AMS results/fees/documents. Sync status shows each module's attempt, success, source and retained-data state. A failed section can retain previously successful records with their timestamp; it does not become “live” merely because another section succeeded.

Explicitly associated PDF/JPEG/PNG receipt or document links can be cached privately, subject to file signatures, same-origin checks, no redirects and owner authorization. This is bounded: four files of up to 2 MB per source refresh, at most eight files / 16 MB per student across current fees and documents, without an accumulating version history. Unavailable/oversized files remain unavailable rather than fabricated.

Course planning and an official portal handoff do not constitute university course submission. No guessed or undocumented endpoint is used to submit registrations. Complete official submission in the university portal unless a supported integration explicitly confirms it.

Class colors follow actual dated present/absent marks; missing or ambiguous marks stay neutral. The next class uses the current India time and known source start/end times. An attendance total alone cannot determine whether an individual class was attended.

## Faculty forms, event evidence and permissions

Administrators provision faculty accounts or scoped event organizers. In Management → Roles & accounts, create the account, then choose Account type Faculty, campus role Student and its department. That grants the faculty forms/examination workspace without granting campus-wide event management. Students also need an administrator-assigned campus department to receive department-specific faculty publications; editing a social department cannot grant that scope. Under Feedback & forms, authorized staff can create a feedback/registration-evidence form, set required fields and submission dates, and optionally require proof or a location radius. Students see forms in their permitted scope and submit only for themselves. Proof images are private and separate from social media uploads. Students capture any proof in the live camera flow, then submit within two minutes; the server binds the one-use challenge to the account and form and rejects gallery uploads, expired captures and replay. Browser camera provenance cannot be guaranteed cryptographically. Form links preserve the response page while students sign in. Authorized faculty can export all scoped responses as a formula-safe Excel workbook (up to 10,000 rows per export). Faculty review is required before a linked event registration is marked attended.

Location is supporting evidence and can be spoofed. The server validates the fresh one-use challenge, coordinates, accuracy, time and allowed range; do not use GPS as sole proof of identity. Browser permission checks happen only on request. Faculty may scan active event tickets only within their assigned event/department scope; already consumed tickets are rejected. Camera scanning needs a supported BarcodeDetector browser; manual secure QR entry remains available. HTTPS is required outside localhost. No continuous location tracking is used.

## Events, community and payments

Events, posts/reels, registrations, staff permissions and management tools use the campus API and Atlas. Uploaded images/video use protected server storage in a persistent Docker volume. Private academics are separate from the public campus profile. See the feature and verification documents included in the release for the exact delivered coverage.

Paid events require your own Razorpay merchant keys and a public HTTPS webhook. A browser payment callback alone cannot confirm a paid ticket. Configure and test your merchant account, webhook, reconciliation and refund procedures before taking real money. Local OTP inbox checks do not exercise real payments.

## Mobile and device storage

This is an installable **PWA**, not an Android APK. Mobile navigation is at the bottom. Settings → Downloads keeps files generated or downloaded inside the application in this browser's IndexedDB, scoped to the signed-in account. It can save a copy again, delete individual copies or clear this account's copies. It stores up to 100 files / 50 MB, with a 15 MB per-file limit, subject to the browser's actual quota. Your browser's normal download also saves the file to the device. Files from other websites and the operating system's Downloads folder cannot be read automatically. Clear local copies on shared devices. Clearing browser data removes these copies. Official student information has no export action. Install the PWA from a supported browser after HTTPS deployment.

The default Docker port binds only to Windows loopback. A phone cannot open your computer's localhost. For public deployment use a real HTTPS domain and reverse proxy, set `CAMPUS_COOKIE_SECURE=true`, and set `CAMPUS_ORIGINS` to the exact HTTPS origin. Expose only the campus service through that proxy; keep the academic API private. Atlas access must allow the deployment server's actual IP. See [deployment notes](docs/deployment.md).

## Database and deployment choices

The default Windows setup keeps MongoDB Atlas; its [free plan limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/) are finite. Metadata and the private AMS file cache consume database quota. Social media and form captures use finite disk in a persistent Docker volume. There is no unlimited free hosted database or media service.

For a fresh deployment with operator-provided disk, the optional self-hosted MongoDB Community setup generates random private credentials without printing them:

```powershell
node scripts/prepare-self-hosted.mjs --origin=https://campus.your-college.edu
```

It refuses existing private configuration. Follow [storage.md](docs/storage.md) for installation/migration/backups and [deployment.md](docs/deployment.md) for TLS, SMTP, preflight checks and multiple campus containers. The delivered topology is one Docker host with shared database/media and a single academic worker; it is not a tested multi-host or unlimited-capacity service.

```powershell
node scripts/production-check.mjs --self-hosted
docker compose --env-file .env.production -f compose.production.yaml -f compose.mongo.yaml up -d --build --scale campus=3
```

Configure a real domain/certificate and mail provider before these checks pass. Real Atlas credentials, Windows Desktop, additional student-account layouts, actual merchant payments and production load remain operator checks.

## Troubleshooting

- **`bash` / WSL errors:** use the PowerShell scripts in this folder. No Ubuntu setup is required.
- **Missing `Setup.ps1`:** extract the source ZIP and enter the folder that contains `compose.yaml`.
- **Docker unavailable:** start Docker Desktop, select Linux containers and check `docker version` and `docker compose version`.
- **Atlas timeout/authentication:** check the database user's permissions, password encoding, current IP and cluster connectivity. The app keeps TLS verification enabled. Do not paste the URI into issues or screenshots.
- **Port occupied:** stop the old app, or use `Setup.ps1 -Port 4200` and set `CAMPUS_PORT` before running Vite.
- **Vite opens but connected actions fail:** run `npm run doctor`; start the Docker APIs and check the configured API port. A static frontend alone cannot fetch private data.
- **Unhealthy service:** inspect `docker compose ps` and `docker compose logs --tail 80`. Redact personal information before sharing logs.
- **OTP not received:** use the configured mail provider or optional local inbox. The app deliberately does not return the OTP to the browser.
- **AMS challenge rejected:** load a fresh challenge in this app and use its code once; another browser's challenge cannot be reused.
- **Encrypted data fails after upgrade:** restore the original `.private` encryption keys. Setup refuses partial private configuration rather than replacing keys silently.

## Project structure and checks

| Folder | Purpose |
|---|---|
| `frontend/` | React/Vite PWA and frontend tests |
| `services/campus/` | Node campus REST API, events, community, account/session controls |
| `services/academic/` | Private FastAPI service and student academic adapters |
| `docker/`, `compose.yaml` | Nonroot containers and private service network |
| `scripts/`, `Setup.ps1` | Windows Atlas configuration and development helpers |
| `docs/` | Setup, deployment, source coverage and technology notes |

```powershell
npm run test
npm run build
# Python checks are optional for Docker-only users:
# python -m unittest discover -s tests -v   (in services/academic)
```

The source tree includes legacy modules for compatibility and reference; their presence does not mean their old routes are mounted. The active API uses permission, CSRF, identity and media checks. Dependencies are locked; use `npm ci` through `npm run setup` for repeatable installs. See [technology chart](docs/technology.md).

See [active feature coverage](docs/FEATURES.md) for the exact source/provider limits and [technology chart](docs/technology.md) for the implemented stack.

## College photograph

The About page uses the public [Vel Tech library photograph](https://www.veltech.edu.in/wp-content/uploads/2024/10/library-ban.jpg) from the university website. It identifies the college setting; the application is an independent student project.
