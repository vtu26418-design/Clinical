# veltech-ams-mini V1.5

A combined React application for academics, attendance, campus events, student community and placements, using the original UniEve logo. One project contains the React frontend, campus API and private academic API.

[Open the public web preview](https://html-preview.github.io/?url=https://raw.githubusercontent.com/vtu26418-design/Clinical/026eb711b5a47d0755cb574bc250a99897dbe79f/preview.html#/home) · fictional student and event data; private login/payments are disabled.

## What changed in V1.5

- Current/next class is clear at the top of Home and scrolls normally. Home reels are optional under Settings → Social. Ten source student facts, a subtle academic background, a brief phone opening logo and “Developed by VEL STUDENTS” are included.
- Community mixes posts, reels and connection suggestions, with a refreshed order. Full-screen reels and contextual comments preserve your place. Comment edits expire after five minutes on the server. Three-dot controls include save, share, report and owned-content actions; administrators review persisted reports.
- Attendance keeps full subject pages, filters, calculator/formulas and PDF/Excel exports. Calendar dates support a touch-hold summary of present, absent, OD and unmarked source periods. The overview target card is removed.
- Settings has dedicated account, connection, social, appearance, permission, device, downloads and about pages. Connections has no import flow. An optional encrypted device library holds selected owned academic records and handles expiry and browser quota.
- Academics has authenticated AMS readers for explicitly discovered results, fees/receipts and document sections, owner-only bounded file downloads, and individual module sync state. Missing or unsupported sections say “Data not available”; this release does not claim a successful private AMS login.
- Only faculty/admin can create official forms and export scoped response workbooks. All new proof attachments use fresh private camera challenges; normal gallery uploads are rejected. Faculty can also scan permitted event tickets. Official student information remains read-only and separate from the editable social profile.

The public preview uses fictional student, event and academic data. Private login and payments are disabled there. Run the full source to configure your own accounts and university connection.

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

## Accounts, email and the development inbox

The campus account and AMS account serve different purposes. Campus accounts control community, events and roles. An AMS connection accesses only the student's own academic records. Staff permissions come from an administrator's assignments, never an email prefix or a browser-selected role.

Email verification and password reset require SMTP or Brevo. Configure your provider only in `.private/campus.env`; see [provider settings](docs/providers.md). Without a provider the API reports that email is unavailable; it does not reveal verification codes in responses or logs.

For college demonstrations, an optional **local development inbox** receives OTP and event emails without sending Internet email:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1 -DevelopmentInbox
```

Open **http://localhost:8025** on the same Windows computer. This inbox contains local test messages and must not be used as a public email service. It does not prove delivery to real student email accounts. The override exposes only the inbox's web port on loopback; SMTP remains inside Docker. To disable it, stop the application, remove `.private\dev-mail.enabled`, run `docker compose -f compose.yaml -f compose.dev-mail.yaml stop mailpit`, and start again. Configure real SMTP before opening sign-up to real users.

## University data and course registration

AMS is reached at `https://ams.veltech.edu.in/Default.aspx`. Its login requires a fresh manual verification challenge from the app's own server session. Being signed into AMS in another browser does not sign this application's server in. Enter only your own credentials in the app. Never put them in source, screenshots, ZIPs or support logs.

A reachable portal is not proof of a successful student login. **Private live AMS retrieval and complete Home of VelTech coverage remain unverified.** Home of VelTech is a separate student-developed AMS client; no supported separate public API was found. The retired parent portal is not used. This app does not share another browser's AMS cookies.

The adapter reads supported labeled profile, course, attendance, timetable, results, examination, fee and document tables from the authenticated AMS session. It follows only explicitly discovered safe AMS links. Changed layouts need an adapter update; unknown sections remain unavailable. Results, fees and documents in the active academic screen require AMS provenance. Legacy imports may remain in storage, but are not presented as current AMS results/fees/documents. Sync status shows each module's attempt, success, source and retained-data state. A failed section can retain previously successful records with their timestamp; it does not become “live” merely because another section succeeded.

Explicitly associated PDF/JPEG/PNG receipt or document links can be cached privately, subject to file signatures, same-origin checks, no redirects and owner authorization. This is bounded: four files of up to 2 MB per section refresh, at most eight files / 16 MB per student across current fees and documents, without an accumulating version history. Unavailable/oversized files remain unavailable rather than fabricated.

Course planning and an official portal handoff do not constitute university course submission. No guessed or undocumented endpoint is used to submit registrations. Complete official submission in the university portal unless a supported integration explicitly confirms it.

Class colors follow actual dated present/absent marks; missing or ambiguous marks stay neutral. The next class uses the current India time and known source start/end times. An attendance total alone cannot determine whether an individual class was attended.

## Faculty forms, event evidence and permissions

Administrators provision faculty accounts or scoped event organizers. In Management → Roles & accounts, create the account, then choose Account type Faculty, campus role Student and its department. That grants the faculty forms/examination workspace without granting campus-wide event management. Students also need an administrator-assigned campus department to receive department-specific faculty publications; editing a social department cannot grant that scope. Under Feedback & forms, authorized staff can create a feedback/registration-evidence form, set required fields and submission dates, and optionally require proof or a location radius. Students see forms in their permitted scope and submit only for themselves. Proof images are private and separate from social media uploads. Students capture any proof in the live camera flow, then submit within two minutes; the server binds the one-use challenge to the account and form and rejects gallery uploads, expired captures and replay. Browser camera provenance cannot be guaranteed cryptographically. Form links preserve the response page while students sign in. Authorized faculty can export all scoped responses as a formula-safe Excel workbook (up to 10,000 rows per export). Faculty review is required before a linked event registration is marked attended.

Location is supporting evidence and can be spoofed. The server validates the fresh one-use challenge, coordinates, accuracy, time and allowed range; do not use GPS as sole proof of identity. Browser permission checks happen only on request. Faculty may scan active event tickets only within their assigned event/department scope; already consumed tickets are rejected. Camera scanning needs a supported BarcodeDetector browser; manual secure QR entry remains available. HTTPS is required outside localhost. No continuous location tracking is used.

## Events, community and payments

Events, posts/reels, registrations, staff permissions and management tools use the campus API and Atlas. Uploaded images/video use protected server storage in a persistent Docker volume. Private academics are separate from the public campus profile. See the feature and verification documents included in the release for the exact delivered coverage.

Paid events require your own Razorpay merchant keys and a public HTTPS webhook. A browser payment callback alone cannot confirm a paid ticket. Configure and test your merchant account, webhook, reconciliation and refund procedures before taking real money. Local OTP inbox checks do not exercise real payments.

## Mobile and device storage

This is an installable **PWA**, not an Android APK. Mobile navigation is at the bottom. The optional device library encrypts selected basic profile, attendance, timetable and academic metadata with your passphrase (AES-GCM). It expires after one or seven days and can be removed in Settings. It excludes passwords, sessions, keys, private proof bytes, document bytes and contact/family data; there is no student-information export action. Forgetting the passphrase requires removing and recreating the library. Browser storage can be cleared by the device and has a finite quota. Install the PWA from a supported browser after deploying it on HTTPS.

The default Docker port binds only to Windows loopback. A phone cannot open your computer's localhost. For public deployment use a real HTTPS domain and reverse proxy, set `CAMPUS_COOKIE_SECURE=true`, and set `CAMPUS_ORIGINS` to the exact HTTPS origin. Expose only the campus service through that proxy; keep the academic API private. Atlas access must allow the deployment server's actual IP. See [deployment notes](docs/deployment.md).

## Storage and free plans

MongoDB Atlas is the cloud database; use a free tier for a small demonstration and check its current [plan limits](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/). Free storage is finite, not unlimited. Database metadata **and the bounded private AMS file cache** consume that quota. Social images, videos and private form captures use the persistent Docker media volume, whose capacity is your server's disk. Large video storage requires separately provisioned capacity or a configured storage provider; the app does not include unlimited free media hosting. Monitor usage, backups and retention before enrolling a whole college.

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
