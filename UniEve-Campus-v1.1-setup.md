# UniEve Campus — V1.1 web and mobile app

A responsive student workspace combines the existing event system with the attendance application's academic adapters. The new interface includes Home, Attendance, Timetable, Academics, Events, Placements, Campus feed, Student details, Settings, Notifications and a staff Management area. Playground is excluded.

On phones, Home, Attendance, Events and Feed stay on the bottom bar. **More** opens Timetable, Academics, Placements, Student details, Settings and authorized Management. The photo dropdown remains available at the top. The mobile delivery is an **installable progressive web app (PWA)** for Android/iPhone and desktop, not a compiled APK or an App Store binary.

The interface opens in **Demo workspace** so you can review it immediately. Every student, photo, attendance record, notice, company and event in this mode is fictional. Demo changes stay in the current browser; Settings → Account → Reset demo data restores the examples. Demo payments are disabled. The demo role selector only previews screens and cannot change real account permissions.

## What is connected

| Module | Connected behavior |
| --- | --- |
| Student identity | Your own linked academic profile, photo, department, batch, mentor and other available source fields. Missing fields show a clear empty state or initials. |
| Attendance and classes | Existing attendance records, subject totals and timetable; a manual authorized portal sync; last successful sync displayed. Green means confirmed present, red means confirmed absent; unknown and future classes remain neutral. |
| Academics | Existing registered subjects, courses and academic bucket. Results, examinations, fees, documents and requests appear only when those records exist in the academic source database. |
| Events | Existing event documents, free and paid registration, individual QR tickets, scoped organizer check-in and participant lists. |
| Placements | Campus/off-campus opportunities entered by a placement officer, search/filter, saved opportunities and personal application tracking. |
| Campus feed | Persisted text/image posts, likes, saved posts, comments and follow connections. Private academic records stay outside the public feed. |
| Management | Account creation, scoped roles, event publishing/check-in, placement publishing and campus notices according to server permissions. |

This is a first integrated version, not a verified copy of every Home of Vel Tech or AMS feature. The referenced conversation and a complete institution feature inventory were unavailable. Results, fees, document issuance, request processing and additional university services still need institution-supported sources. Missing data is never replaced with demo data in a connected account. Placement tracking records your intent/status; it does not submit a recruiter application for you.

## Package layout

Extract the source ZIP with both folders beside each other:

```text
your-folder/
├── Unieven-AI/
│   ├── campus-web/             # New React/Vite interface
│   ├── backend/campus/         # Campus bridge and event/social API
│   ├── scripts/campus-*.sh     # Install, start and stop
│   └── README-CAMPUS-V1.md
└── Unieve-Attandance-AI/
    └── backend/                # Existing FastAPI academic service
```

The original frontends, event backend and Spring authentication service remain in their original locations. V1 uses existing event/account/registration models and a standalone campus API; the original applications are not required for the demo. JDK 17+ and Maven are optional and needed only if you separately run the original Spring authentication workflow (its POM targets Java 17).

## Requirements

- Linux or macOS with Bash, Node.js **24 LTS** (minimum **22.12**), npm and **Python 3.12**.
- MongoDB Community Server installed locally, or an accessible existing MongoDB connection. The scripts do not download an unverified MongoDB binary. In the provided cloud environment they can use `/workspace/.onboarding/mongod`.
- Python `venv` and pip, or the `uv` package manager. Setup prefers `uv` when available.
- Access to the configured npm/Python package registries during installation. Leave TLS and package verification enabled.

The launch scripts bind to the local machine and use ports **5180** (web), **4100** (campus API), **8000** (academic API), and **27018** (isolated local MongoDB). They never stop an unrelated process occupying these ports. Windows users can run the scripts through WSL2.

## Install and run

```bash
cd Unieven-AI
bash scripts/campus-setup.sh
bash scripts/campus-start.sh
```

Open `http://127.0.0.1:5180` in the browser on that machine. In a remote workspace, use the workspace's supported port preview or forwarding feature; a localhost address on your laptop does not point to the remote machine.

The production build is also served by the campus API at `http://127.0.0.1:4100`. Use that address for local PWA installation/offline checks; Vite development does not register the production service worker. To install on a phone, serve the built app and campus API on the same **HTTPS** origin, then choose Settings → App preferences → Install mobile app. Android Chrome supports Install app; iPhone Safari uses Share → Add to Home Screen. A local laptop address is not an HTTPS phone deployment.

Settings includes Light/Dark/Follow device appearance, larger text, reduced motion, manual/30-second/1-minute/5-minute refresh, browser notification permission, app update checks, secure account connections and sign-out. Preferences contain no account secrets. Refresh reads saved academic data; **Sync AMS** performs a separate authorized portal fetch after manual verification. Browser alerts require device permission and notify about new academic updates while the app is open; their system notification text deliberately contains no private academic details. Offline mode caches app files and fictional demo data. Settings → Device storage can also save a selected academic snapshot encrypted with AES-GCM and a user passphrase derived with PBKDF2. It expires after one or seven days and requires an explicit unlock after reopening. The snapshot omits passwords, authentication tokens, family/contact data and ticket/payment secrets; the unlocked view labels records as saved, not live. API responses, payment orders and private tickets remain outside service-worker caches. Reopening starts with the demo; restore/sign in to your campus session for connected records.

Setup installs the frontend with `npm ci`, builds it, decodes the original UTF-16 Python requirements into a runtime-only UTF-8 file, and installs pinned Python requirements in a virtual environment. It copies both backend sources into a separate runtime and runs `npm ci` there. The original repository has tracked `backend/node_modules`; setup deliberately leaves it untouched.

The runtime defaults to the sibling directory `.campus-runtime`. It contains private env files, dependency caches, copied backend sources, service logs, PID records and local database files. Setup creates random, persistent local encryption/authentication keys with private file permissions. It does not copy original `.env` files, print generated secrets, seed student records, create external projects or deploy anything.

```bash
bash scripts/campus-stop.sh
```

Stop shuts down only the recorded processes whose identities still match, preserving databases and keys. Run it before repeating setup, then start again to apply backend source changes. Frontend source changes reload through Vite. Never delete or rotate the private encryption keys casually: existing encrypted academic links and portal passwords require their original keys.

### Optional paths and database connections

Set these environment variables consistently for setup, start, stop and provisioning:

```bash
export CAMPUS_RUNTIME_DIR=/absolute/path/to/private-campus-runtime
export CAMPUS_ATTENDANCE_DIR=/absolute/path/to/Unieve-Attandance-AI
export CAMPUS_PYTHON=python3.12
export CAMPUS_MONGOD=/absolute/path/to/mongod
```

The default MongoDB databases are `unieve_campus_v1` and `unieve_campus_attendance_v1` on port 27018, keeping this local version separate from existing development data. To use an existing authorized database, configure **both** `MONGODB_URI` in `private/campus.env` and `MONGO_URI`/`MONGO_DB_NAME` in `private/attendance.env`. These files are created once and preserved on subsequent setup runs. Edit them using a local editor or inject the matching environment variables from a secret manager. Existing process environment variables take precedence at startup.

An existing local MongoDB on port 27017 is supported when explicitly configured; the launcher reuses it and does not stop it. For alternate app ports set `CAMPUS_PORT`, `CAMPUS_ACADEMIC_PORT` and `CAMPUS_WEB_PORT`, and update `ACADEMIC_API_URL` plus `CAMPUS_ORIGINS` to match. Setting these before the first setup generates matching local defaults. If private config files already exist, edit the corresponding values or inject all matching environment overrides.

Do not point V1 at production data just to preview the design. The campus API initializes registration counters for pre-existing events, and the academic service initializes its administrator and indexes on startup. Review those effects and back up data before intentionally migrating a real database. Original backend env files are not automatically imported; migrate required bindings explicitly.

## Create the first campus administrator

Start the services first. The following CLI creates a new administrator and refuses to overwrite, reset or promote an existing account. The password comes from a hidden prompt/environment variable, never a command-line argument or source file:

```bash
export CAMPUS_RUNTIME_DIR="${CAMPUS_RUNTIME_DIR:-$(cd .. && pwd)/.campus-runtime}"
export CAMPUS_ENV_FILE="$CAMPUS_RUNTIME_DIR/private/campus.env"
read -r -p 'Administrator email: ' CAMPUS_ADMIN_EMAIL
read -r -p 'Administrator username: ' CAMPUS_ADMIN_USERNAME
read -r -p 'Administrator name: ' CAMPUS_ADMIN_NAME
read -r -s -p 'Administrator password: ' CAMPUS_ADMIN_PASSWORD
printf '\n'
export CAMPUS_ADMIN_EMAIL CAMPUS_ADMIN_USERNAME CAMPUS_ADMIN_NAME CAMPUS_ADMIN_PASSWORD
(cd "$CAMPUS_RUNTIME_DIR/campus-backend" && node campus/provision.js)
unset CAMPUS_ADMIN_PASSWORD
```

Use a password of at least 16 characters and at most 72 UTF-8 bytes containing upper/lowercase letters, a number and a symbol. This avoids bcrypt's password truncation limit. In the web account menu choose **Connect campus account**, sign in, and open **Management**. Create campus users and assign their department/club and role there. Existing UniEven email/username/password accounts can also sign in when you deliberately connect the same database.

### Roles

| Role | Scope |
| --- | --- |
| Student | Own academic records, feed, registrations and placement tracking. |
| Club organizer | Events/check-in for the assigned club **and** department. |
| Department coordinator | Events/check-in and notices for the assigned department. |
| College event manager | College-wide events/check-in and notices. |
| Placement officer | Campus/off-campus placement publishing and notices. |
| Administrator | Campus account/role management and all event/placement scopes. |

Permissions are checked by the backend, including participant access and check-in. A demo selector or browser-edited role cannot grant authority. Legacy unscoped events keep their creator ownership; unrelated faculty accounts do not gain management access. Use consistent department and club identifiers when assigning users and publishing events.

## Connect an academic account and authorized portals

Campus and academic accounts are separate. The email must match in both systems and the student must verify their **academic application password** in Settings before linking. V1 encrypts the academic API token on the campus server; it does not retain that linking password.

For a new local installation, the academic backend creates a separate local administrator. Setup generates its password privately rather than using the original weak default. If you need this admin login, set `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_NAME` and your own strong `DEFAULT_ADMIN_PASSWORD` in `private/attendance.env` **before the first start**. Existing administrators are not automatically reset by a changed env variable. Use the original attendance application's administration workflow or the academic API's authenticated `/api/v1/admin/users` route to create student accounts; its creation body uses `name`, `email` and `temporaryPassword`, with optional student fields. The academic API documentation is available locally at `http://127.0.0.1:8000/docs`.

Then the student can:

1. Sign in to their campus account, open **Settings**, and verify/link the academic account with the same email.
2. Open **Connections** and enter their own authorized VTU/AMS username and portal password under **University portal sync**.
3. Save the portal connection, load and answer the official AMS challenge, then choose **Sync AMS**. Review the last sync and partial-source errors. Home → Sync portal opens this Connections screen.

Portal passwords are encrypted by the academic service with its persistent `PORTAL_CREDENTIAL_ENCRYPTION_KEY`. Live sync uses the existing authorized AMS and parent-portal adapters; it requires valid student credentials, institutional permission, network access to the actual portal destinations, and compatible portal pages. The demo itself does not authenticate a university account. Both V1.1 read-only login attempts using manually supplied challenges were rejected; the cause was not determined and authenticated private retrieval remains unverified. Automatic background sync is off by default. Configure `COLLEGE_ADAPTER_MODE=portal` and the institution's supported settings when connecting live data. If portal HTML or authentication changes, the adapters may require an update; a failed or incomplete sync does not mean the student is absent.

**Live source status in V1.1:** the updated cloud now reaches AMS. `Login.htm` is a static template; the adapter uses the official `Login.aspx` page, preserves its hidden session nonce and requires a **manual CAPTCHA answer before transmitting credentials**. Sign in, link your academic account, save your portal connection, then Settings → Connections → Load AMS challenge → enter the displayed answer → Sync AMS. Each challenge is account-bound, lasts five minutes and can be used once. A successful AMS sync fetches your own profile/photo/courses/timetable; it does not invent attendance. Background password-only AMS sync cannot pass the new CAPTCHA.

The existing Home of Vel Tech parent-login endpoint currently returns HTTP 404 with the supported HTTP client. The official website lists a Parents portal at `https://results.veltech.edu.in/StuLogin/Parent/Login.htm` (returned HTTP 503 during this check) and Student ERP at `https://apps.veltech.edu.in/clique/` (reachable, with browser CAPTCHA verification). These are linked in Connections. Their authenticated data formats are not implemented or verified; V1.1 does not bypass their verification or reuse an AMS password against another login. Attendance continues to show only existing confirmed records until an institution-supported attendance source is available. The official university homepage is fetched independently for public news/events, with its source URL and fetch time. Public news is not private student data. Reachability, successful login and successful data sync are separate states; Settings displays them accordingly. A real authenticated student fetch is not claimed unless its login/challenge completes successfully. Supplied credentials are kept out of the source/packages and used only for the authorized read-only check after a manual answer.

Only source-confirmed per-class records produce present/absent coloring. When a day's subject has multiple periods and the source cannot identify the period, the interface avoids guessing a class's status. Photos appear in the navbar, Home and Student details when a usable source photo is available; otherwise it displays initials.

## Paid events with Razorpay

Paid-event support is implemented around **server-created INR orders** and a signed **`payment.captured` webhook**. Registering creates a pending reservation; only a matching captured payment with the stored order, amount and currency can issue a QR ticket. A browser checkout success callback does not confirm payment.

Begin with the institution's authorized **Razorpay test account**. Configure `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` and a distinct `RAZORPAY_WEBHOOK_SECRET` in the private campus config or your deployment secret manager. Never put the key secret or webhook secret in Vite/browser variables. The server returns the publishable key ID and its verified order information to the checkout UI.

Razorpay webhooks need a publicly reachable HTTPS endpoint:

```text
https://your-institution-domain/api/campus/payments/webhook
```

Configure that endpoint in the merchant dashboard, subscribe to `payment.captured`, and use the same webhook secret. For hosted use, place the campus API behind a trusted reverse proxy, forward the request's original Origin, set `NODE_ENV=production`, set `CAMPUS_ORIGINS` to the exact HTTPS web origin, route the built frontend and API on the same origin, and preserve the webhook request's raw body. Keep the academic service and MongoDB private. The built frontend directory can be supplied through `CAMPUS_WEB_DIST`. Hosting, DNS, merchant onboarding and payment keys are not created by the setup scripts.

Test free registration, a successful test capture, an incorrect amount/signature, duplicate webhooks and organizer check-in before switching to live merchant keys. Live payment processing also needs the college's approved refund/cancellation policy and merchant configuration.

V1 has a deliberate operational limitation: paid orders, including pending orders, cannot be cancelled through the student free-ticket cancellation action. Pending orders hold capacity and there is no automatic expiry/reconciliation/refund job yet. Staff must reconcile abandoned orders and handle refunds through the payment provider with an audited college process. Do not collect real event fees until this operational workflow is agreed and tested. The demo never creates provider orders or charges money.

V1.1 verification: **52 backend tests, 30 academic-service tests, 24 frontend tests**, including CAPTCHA ownership/no automatic credential submission, device encryption/tampering/expiry, event bookmarks, post ownership and fixed download paths. Browser checks cover the updated settings/device/social flows, existing campus workflows, connected local services, PWA privacy/offline behavior and actual attachment downloads. University website news was fetched successfully; AMS private data still needs the manual challenge.

## Device data and project downloads

Settings has Account, Connections, Device storage, App preferences and Downloads categories. Device storage is optional: choose a passphrase of at least 10 characters and save a snapshot of the currently displayed student data. Demo snapshots stay labelled fictional. Unlock with the same passphrase for a read-only view, Lock snapshot to remove plaintext from the view, and Remove snapshot to delete the encrypted device copy. The passphrase is never retained by the app and cannot be recovered. Browser storage clearing also removes the snapshot. This does not cache payments or create offline attendance/registrations.

Events include per-account bookmarks, sharing and calendar exports using the actual event start time in India Standard Time. Calendar files do not invent an unknown end time. The feed includes search, a Following filter and author-only editing/removal; existing media posts keep their original compatibility.

Setup now runs `scripts/export-campus.py` after building and generates sanitized ZIPs and a setup guide in the sibling `artifacts` directory. Settings → Downloads serves these as actual HTTP attachments through the campus API. Set `CAMPUS_DOWNLOAD_DIR` consistently during export and API startup if using another location. The API only allows the fixed package IDs; it cannot download arbitrary server files. To regenerate after source/frontend changes, build first, then run `python3 scripts/export-campus.py`. This keeps working even when a chat client cannot download workspace file links.

The original V1.1 delivery is also listed in the [GitHub release](https://github.com/vtu26418-design/Clinical/releases/tag/unieve-campus-v1.1-20261014): [complete source ZIP](https://raw.githubusercontent.com/vtu26418-design/Clinical/unieve-campus-v1.1-downloads/UniEve-Campus-v1.1-source.zip), [built mobile/web ZIP](https://raw.githubusercontent.com/vtu26418-design/Clinical/unieve-campus-v1.1-downloads/UniEve-Campus-v1.1-mobile-web.zip), and [setup guide](https://raw.githubusercontent.com/vtu26418-design/Clinical/unieve-campus-v1.1-downloads/UniEve-Campus-v1.1-setup.md). These are project downloads; deployment is a separate step. Files are hosted on the separate `unieve-campus-v1.1-downloads` branch. The Clinical main branch and application source are preserved.

## Validation and troubleshooting

```bash
# Frontend build and unit tests
(cd campus-web && npm run build && npm test)

# Syntax-check the launcher scripts
bash -n scripts/campus-setup.sh scripts/campus-start.sh scripts/campus-stop.sh
```

Backend regression tests live in `backend/campus/tests` and `Unieve-Attandance-AI/backend/tests`. The Mongo-backed Node tests use isolated `campus_test_*` databases on port 27017 and delete those test databases at completion; review their targets and use a local test server. They are not part of normal application startup. Run them from the external runtime copy, not the original tracked dependency directory. The Python tests can run with the runtime virtualenv from the attendance backend copy.

```bash
(cd "$CAMPUS_RUNTIME_DIR/campus-backend" && node --test campus/tests/*.test.js)
(cd "$CAMPUS_RUNTIME_DIR/attendance-backend" && "$CAMPUS_RUNTIME_DIR/attendance-venv/bin/python" -m unittest discover -s tests -v)
```

V1 delivery verification on 14 October 2026: **49 Node tests, 25 Python tests, 18 frontend unit tests**, builds of the new frontend and both original frontends, plus **32 browser checks** covering demo workflows, phone settings/navigation, connected local services, production PWA/offline behavior and cache privacy. All recorded checks passed with no browser page errors. The setup/start/stop scripts were tested with an isolated runtime and alternate ports. Real university sync, live payment capture, public hosting and native app-store installation remain unverified.

- **Installation fails:** use the required Node/Python versions and inspect the failed dependency/registry request. Do not disable certificate/signature checks or rewrite the committed lockfiles to make installation pass.
- **Port already in use:** stop your own conflicting service or configure alternate ports and their matching origins/API URL. The launcher never kills unrelated services.
- **MongoDB unavailable:** install MongoDB Community, set `CAMPUS_MONGOD`, or configure an accessible existing database. Check URI names and access without posting credentials in chat.
- **Backend source changed:** stop, run setup again, then start. Runtime copies do not automatically reload edited backend sources.
- **Academic link expired or decryption fails:** verify persistent keys and relink your own academic account. Never replace a key to bypass a decryption error.
- **Partial portal data:** inspect the last sync/error and institutional source availability. Results/fees/documents need additional sources; the UI explicitly marks unavailable integrations.
- **Paid ticket stays pending:** verify the test/live merchant environment, HTTPS webhook delivery and its signature secret. Do not manually mark a browser callback as captured.

Logs are in `.campus-runtime/logs`; keep them private because original portal adapters can include student identifiers in diagnostic messages. Share only relevant redacted errors. Never package `.campus-runtime`, `.env` files, database dumps or actual student uploads.

## Delivery and future versions

The source archive excludes dependencies, Git history, env secrets, database files and generated caches. Original Spring `application.properties` email-password and credential-bearing MongoDB URI literals are replaced **in the delivery copy** with environment placeholders; original tracked files are preserved. Literal example student IDs in the original attendance helpers are replaced with `VTU00000` in the delivery copy. Supply `MAIL_PASSWORD` and `SPRING_MONGODB_URI` securely if you separately run that original service. Original `auth-service/bin` and `auth-service/target` outputs are excluded. The archive includes this guide, both source repositories, lockfiles, tests and setup scripts. The separate mobile/web ZIP contains the ready-built frontend; setup also builds it from source.

To serve only the included built demo without backend services:

```bash
cd UniEve-Campus-v1.1-mobile-web/web
python3 -m http.server 5180 --bind 127.0.0.1
```

Open `http://127.0.0.1:5180` on that machine. This supports the browser-only demo and its hash navigation. **Connect campus account** requires the running campus and academic APIs with configured MongoDB; a static server does not proxy API requests. You can also preview the demo after a frontend install with `npm run preview` from `campus-web`.

Useful next versions include institution-supported results/fee/document sources, college SSO/account provisioning, payment reconciliation/refund tooling, source-specific sync monitoring and reviewed deployment configuration. These require real institutional and merchant access rather than invented data.
