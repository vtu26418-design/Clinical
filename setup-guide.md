# veltech-ams-mini 2.1.0 — setup and upgrade

This release improves saved-session restoration, background updates, read-only offline access, examination imports, campus documents and event publishing. The existing student Home layout is retained.

## Windows with Docker Desktop

1. Back up the database, `.env`, `.private`, media/uploads and any Android signing files. Keep the same session/link/service keys. Extract this release into a fresh folder; copy your configuration and private files into it. Never commit those files.
2. Start Docker Desktop in Linux-container mode. You do not need Ubuntu, a local Node/Python installation or a local MongoDB server.
3. In PowerShell, open the extracted project folder and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start.ps1
```

4. Open `http://localhost:4100`. On an existing deployment run `docker compose up -d --build` after the backup and configuration review.

Existing detailed setup, SMTP, hosting and Android steps are in [V2-UPGRADE.md](V2-UPGRADE.md), [EMAIL-SMTP.md](EMAIL-SMTP.md), and [DEPLOYMENT-UPDATE.md](DEPLOYMENT-UPDATE.md). This upgrade does not migrate an existing external database automatically. Keep the existing storage URL and follow the documented migration procedure when changing providers.

## Student updates

- Returning students can open their saved workspace while their session is checked. Background updates keep the selected page, tab and records visible. A confirmed expired/revoked session clears private saved data and requires sign-in.
- After a verified online visit, supported academic records are cached for up to 24 hours in this browser/device. The private cache is encrypted and separated by account. Student details, attendance, results, timetable, published exams and document metadata are available only if previously loaded. Previously downloaded files can be opened offline from Downloads. A new device or cleared browser needs an online sign-in first.
- Offline mode is read-only. Publishing, registration, payments, uploads and fresh AMS sync require a connection. AMS authentication and verification requirements still apply; this release does not bypass university controls.
- Local sign-out immediately clears saved private records and downloads. If offline, it blocks session restoration until the server sign-out can be completed after reconnecting.
- Existing home reminders announce new exam/schedule publications for 24 hours. Exam reminders return within 72 hours of the start and distinguish tomorrow, today and in progress. Ended exams disappear. No extra Home cards are added.

## Publishing and imports

- Imported schedule rows display Row 1, Row 2, etc. on desktop and phone, continuing across pages of 20 rows.
- Duplicate/overlapping course sessions for the same audience are rejected across current publications. Different sections and adjacent sessions remain valid. Older duplicate records are collapsed for the student after official academic audience matching.
- Departments & clubs in administration lets an account administrator maintain known labels and aliases. Publishing inputs suggest known choices; a possible typo must be resolved by choosing a matching entry. They do not silently publish to another audience. Faculty remain within their assigned department.
- Campus documents can be published, updated or deleted by staff with the assigned academic permissions. Documents can target a department, semester, section, batch and registered course. AMS documents remain separately labeled. Source files are protected and checked when downloaded; previously downloaded copies can still exist on a student's device.
- Event creation includes on-campus, online or hybrid format, end time, structured agenda, contact details, accessibility notes and attendance instructions. Meeting links are limited to managers and confirmed participants. Review and Publish / Publish & post are real actions; existing payment restrictions remain in force.

## Configuration

No new secret is required for this upgrade. Keep the existing `.env` values. Set your deployed public HTTPS URL and allowed origins before hosting; use secure cookies and the documented trusted proxy subnet. Configure SMTP in the server `.env` only, then run the supplied mail check to your own test mailbox. Never put SMTP passwords, AMS credentials, service keys or database credentials into a Vite `VITE_*` variable.

The default Docker deployment uses the existing PostgreSQL/DocumentDB/FerretDB configuration. A free database or hosting plan has storage, connection, traffic and sleep limits; no free service provides unlimited storage or guaranteed performance. Test with your expected student concurrency before a campus-wide launch.

For installation on phones, use the PWA from HTTPS. A distributable Android APK requires your public URL and your own signing key; add them following `android/README.md`. The source ZIP is not a signed APK. Keep the same package and signing identity for updates. Browser/device access controls and OS installation behavior cannot be guaranteed on every phone.

## Before publishing

Check the included verification record, take a backup, test SMTP delivery, sign in as a limited administrator and as two different students, verify academic targeting, publish/correct/withdraw a test exam, download a document, then check refresh and offline access. Confirm the official AMS data for a real consenting student in your deployment. Fixture verification is not proof that every university page layout is supported.


# veltech-ams-mini · 2.0.0 setup and upgrade

## New Windows installation

1. Install Docker Desktop and start its Linux container engine. No Ubuntu terminal,
   manual WSL distribution, Python, MongoDB installation or Node installation is
   needed for the Docker setup. Docker Desktop may manage its own WSL backend.
2. Extract the **full source ZIP** to a new folder. Open PowerShell there.
3. Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1
```

New installations use PostgreSQL 17 + DocumentDB + FerretDB. Setup generates
random credentials and persistent keys in `.private`, builds the web/API services,
starts the private database, and prompts for the first owner administrator. Use a
real email and a strong password. Keep the owner account private. Open
**http://localhost:4100**. Use the same login page for students, faculty and admins.
The server finds their account type; the user cannot choose elevated access.

Later:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Stop.ps1
```

For Vite development only, install Node 24, run `npm run setup`, `npm run dev` and
open the printed Vite URL. Keep Docker running the API and database. Never put
SMTP, database passwords or academic keys in `VITE_*` variables.

## Existing installation: keep accounts and keys

Back up both application databases, the `campus-media` volume and the complete
`.private` directory before replacing code. Extract this delivery into a new folder
and restore your existing `.private` configuration. Setup detects existing files
and **does not change the database**. Continue using the existing MongoDB/Atlas
connection until the migration below is verified. Do not regenerate
`CAMPUS_LINK_KEY`, `CAMPUS_SERVICE_KEY`, `JWT_SECRET` or
`PORTAL_CREDENTIAL_ENCRYPTION_KEY`: old encrypted records depend on them.

Existing PostgreSQL installations must also retain `postgres.enabled`,
`postgres.env`, `ferretdb.env` and the original Compose project/volume identity.
If you change the folder name, Docker Compose still uses the fixed project name
`veltech-ams-mini`. Do not run old and new app services against the same records
simultaneously during the upgrade.

## PostgreSQL storage: what changed

The persistent database is PostgreSQL. FerretDB translates the existing BSON
queries to PostgreSQL's DocumentDB extension, retaining object IDs, dates,
indexes and existing application records. Mongoose and PyMongo remain the API
clients; the compatibility connection settings therefore still use `mongodb://`.
This is **not** a rewritten relational SQL schema. Do not paste a plain
`postgresql://` URL into `MONGODB_URI` or `MONGO_URI`.

The matching images are pinned to FerretDB 2.7.0 and PostgreSQL DocumentDB
17-0.107.0-ferretdb-2.7.0. Keep their supported versions paired. A normal free
Supabase/Neon PostgreSQL instance does not necessarily provide this extension.
The supplied stack self-hosts it with Docker; neither database port is published.
Use private networking, encrypted disks, backups, and TLS for any remote database
hop. Restrict administrative PostgreSQL access to the operator.

PostgreSQL software has no storage subscription fee. Disk, backups, hosting and
bandwidth still have limits/costs. No provider offers guaranteed unlimited fast
storage for free. This release does not provision a free cloud server or promise
performance for an unmeasured student load. Run a realistic load test on the
actual deployment before opening college-wide access.

## Copy an existing MongoDB installation to PostgreSQL

Do this in a maintenance window with student writes and sync jobs stopped.
Never delete the old database as part of migration.

1. Back up database data, `.private`, media, and APK signing keys separately.
2. Keep your current campus and academic env files. Create `.private/postgres.env`
   and `.private/ferretdb.env` with your own random hex password:

```dotenv
# .private/postgres.env
POSTGRES_USER=campus
POSTGRES_PASSWORD=YOUR_RANDOM_HEX_PASSWORD
POSTGRES_DB=postgres
```

```dotenv
# .private/ferretdb.env (same password)
FERRETDB_POSTGRESQL_URL=postgres://campus:YOUR_RANDOM_HEX_PASSWORD@postgres:5432/postgres
```

3. Start only the new stores:

```powershell
docker compose -f compose.yaml -f compose.postgres.yaml up -d --wait postgres ferretdb
```

4. Create **private** `.private/migration.env`. Use the actual existing database
   names, not the placeholder names below. Preserve the academic service's
   `MONGO_DB_NAME` exactly. The script connects by database name explicitly.

```dotenv
SOURCE_CAMPUS_URI=mongodb+srv://YOUR_OLD_CREDENTIALS/YOUR_CAMPUS_DB
TARGET_CAMPUS_URI=mongodb://campus:YOUR_RANDOM_HEX_PASSWORD@ferretdb:27017/?authSource=postgres
CAMPUS_DATABASE=YOUR_CAMPUS_DB
SOURCE_ACADEMIC_URI=mongodb+srv://YOUR_OLD_CREDENTIALS/YOUR_ACADEMIC_DB
TARGET_ACADEMIC_URI=mongodb://campus:YOUR_RANDOM_HEX_PASSWORD@ferretdb:27017/?authSource=postgres
ACADEMIC_DATABASE=YOUR_ACADEMIC_DB
```

5. Stop the old app and academic workers; leave their source database reachable.
   Make an empty `migration-reports` folder. Run the script inside the Python
   service image; Windows needs no Python installation:

```powershell
New-Item -ItemType Directory -Force migration-reports | Out-Null
docker compose -f compose.yaml -f compose.postgres.yaml run --rm --no-deps --entrypoint python -v "${PWD}/scripts/migrate-storage.py:/migration.py:ro" -v "${PWD}/.private:/migration-config:ro" -v "${PWD}/migration-reports:/reports" academic /migration.py --config /migration-config/migration.env --report /reports/result.json
```

For a local source database outside Docker, use the proper reachable private host
or `host.docker.internal`, not `localhost`. Ensure source TLS verification stays
on for Atlas. The destination must be empty; the script never overwrites records.
If interrupted, leave the old application on the source and inspect the partial
copy before explicitly clearing only that migration destination and retrying.

6. Require `verified: true` for **both** databases in `result.json`. Counts and
   canonical per-collection SHA-256 hashes must match, and source records must
   remain stable during the copy. The script copies supported indexes before
   records. Run again with `--verify-only` to compare without changing data.
7. Only after verification, change campus `MONGODB_URI` to the target gateway URI
   with the **same campus database name**. Change academic `MONGO_URI` similarly
   and retain `MONGO_DB_NAME`. Keep every encryption key unchanged. Add the
   `.private/postgres.enabled` marker, then run `Start.ps1`.
8. Verify existing owner/student login, attendance, results, tickets, media,
   academic access and notification delivery. Retain the old database read-only
   during your rollback window. Do not switch back after accepting new writes
   without reconciling those records. Never use `docker compose down -v` as an
   upgrade command.

## Accounts, roles and student records

People & accounts separates Students, Faculty and Administrators, with a Roles &
permissions link. Select **View details** to open an account page. Academic
records require both `accounts:view` and `academics.read:view`; event history,
placement applications and recorded activity need their respective module/view
grants. Activity requires `audit:view`. Activity includes account login/logout and completed recorded changes,
not continuous surveillance of a person's screen.

The owner can create limited administrators and update their action limits later.
A delegated creator can grant only actions they already hold; owner access cannot
be created through the public account endpoint. Access changes revoke old
sessions. The application does not let an admin overwrite official AMS identity.

Managed academic sessions renew through the private identity-checked bridge.
Existing AMS login links can migrate on renewal only if the durable, verified AMS
principal and exact academic ID match. Unverified legacy connections are never
claimed by email. A lost upstream AMS session or CAPTCHA still requires the
student's legitimate university verification. An unavailable source shows its
status and saved data; this application cannot restore a university outage.

## Event publishing and history

Create/Edit opens a dedicated page. Set audience, location/time (IST), seats,
free/paid entry, registration deadline, eligibility, instructions and manual rules.
Upload your own poster/video; adjust poster fit/focus/accent. `Publish & post event`
adds one linked community post. Repeated posting does not duplicate it. Uploaded
media remains subject to ownership and access checks.

Settings → Appearance & alerts → Event history & expiry controls the default
1–120 months for new events. An event can use a custom date or stay listed until
archived. Expiry hides it and closes new registration and check-in; records/tickets remain.
Archived history also includes expired listings. Paid checkout still needs your
configured payment provider and verified webhook. Free events need no payment
configuration. Archive and expiry do not issue refunds automatically.

## Placements and schedules

The placement office can publish opportunities with salary, mode, eligibility,
skills, rounds, batches, deadline and openings. Eligibility fields describe the
criteria; staff verify the official record during review. Students bookmark,
submit an application/portfolio and track their own stage. Authorized staff
shortlist/interview/select/reject and send a student-visible review note. Students
cannot view another applicant's application. Archive retains history.

Calendar-authorized admins and assigned academic faculty/coordinators publish
semester/examination schedules with dates, instructions and an HTTPS document
link. Faculty stay within their assigned department. Optional section/semester
audiences use verified academic details; unavailable matching details do not
broaden restricted publications. These staff publications are labelled separately
from the AMS timetable. Withdrawing a publication removes it from student view.
Student home reminds them of upcoming exams, available own-seat details and
published schedules. Existing private PDF/Excel seating import and authorization
remain in Exams & seating.

## SMTP and public deployment

See `docs/EMAIL-SMTP.md` and `config/smtp.example.env`. Set in `.private/campus.env`:
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `CAMPUS_MAIL_FROM` and
`SMTP_REQUIRE_TLS=true`. Provider app passwords/free quotas vary. Keep STARTTLS
and certificate validation enabled. Domain/DNS SPF, DKIM and DMARC are managed
with your mail provider. Run `npm run email:check` only when you want to send the
configured diagnostic email. No real mail is sent by the included QA fixtures.

Deploy behind HTTPS with `compose.production.yaml` plus
`compose.postgres.production.yaml`, retaining `.private` and media. Set
`.env.production` `CAMPUS_SERVER_NAME` and `CAMPUS_TLS_DIR`; set campus
`CAMPUS_ORIGINS` to the exact HTTPS origin, `CAMPUS_COOKIE_SECURE=true` and
`CAMPUS_TRUST_PROXY=172.29.240.2/32`. Keep the academic service private. Use one
academic process for its pending AMS challenge sessions. Campus API replicas
share the database rate limiter/session store and a shared media volume. For
multiple physical servers, provision shared durable media and validate proxy
addresses; a machine-local Docker volume is not shared between hosts.

After configuring production, run `node scripts/production-check.mjs --postgres --url=https://YOUR_HOST` from a machine with Node and Docker access. The check prints pass/fail messages without credentials and requires your real SMTP/TLS settings.

## Android installation and direct updates

Your public deployment URL is intentionally left for you to add later in
**`android/config.local.json` → `deploymentUrl`**, copied from
`android/config.example.json`. Follow `docs/ANDROID.md` to generate the TWA,
configure your real HTTPS domain/Digital Asset Links and build a signed APK on
Windows. Keep the existing package ID and signing key for an upgrade; increase
`versionCode`. The current example release is 2.1.0 / 20100. Do not lose the signing key.

After `npm --prefix android run build:release` has verified the APK and produced
`android/out/signing-receipt.json`, publish its public files:

```powershell
node scripts/publish-android-release.mjs --apk=android/out/veltech-ams-mini-release.apk --receipt=android/out/signing-receipt.json --out=app-releases
```

Copy the generated `release.json` and checksum-named `.apk` into the server's
private media volume at `/app/media/app-releases`. Set campus
`CAMPUS_APK_DIRECTORY=/app/media/app-releases` and
`CAMPUS_ANDROID_PACKAGE_ID=in.velstudents.veltechams` (or your actual unchanged
package ID), then recreate the campus service. In Docker, one way to copy is:

```powershell
docker compose exec campus mkdir -p /app/media/app-releases
docker compose cp ./app-releases/. campus:/app/media/app-releases
docker compose exec -u root campus chown -R node:node /app/media/app-releases
```

Create that directory as the container's `node` user first if needed. With a
production overlay, use the same Compose files/`--env-file .env.production` for
all commands. Both release files must be readable by the campus service user.
Keep keystores, signing passwords and private env files off the web server.

Settings shows the release only when metadata and the actual APK checksum agree.
Download streams the binary directly from the app origin; it does not redirect to
a hosting page. Android's browser download manager saves it and Android asks the
user to approve installation. Silent installation is not provided. TWA launcher
metadata identifies the installed release; older wrappers may show version unknown.
Web installation does not prove that an APK is installed elsewhere on the device.

Updating preserves the same-origin browser session and restores it on reopening;
no password is saved and no forced logout is performed. An intentionally revoked
or expired sign-in still requires authentication. This ZIP includes Android
packaging source, **not a signed APK**: your HTTPS URL and operator-owned signing
key are still required. Test the built APK and update on real phones before
student distribution.

## What to upload to GitHub

Upload the extracted source files, shared/, frontend/, services/, scripts/, android
source/config.example.json, docker/, compose files and docs. Do not upload
`.private`, `.env*` with real values, node_modules, private media, database dumps,
migration configuration/reports containing private identifiers, APK keystores,
`android/config.local.json` or generated build caches. Keep the supplied
`.gitignore`. Publish the APK/release metadata through the controlled binary
endpoint after signing. Generated web ZIP is a static build; connected accounts
still need the combined backend on the same origin.


# SMTP email setup

The application sends branded HTML **and plain-text** emails for verification/password reset, recovery-email verification, event registration confirmation, event reminders, moderation reasons and campus/event announcements. Templates use the app's navy, blue and teal colours. Private check-in QR codes are not embedded in emails; the ticket opens after sign-in.

## Where to put the values

Run `Setup.ps1` once to create the application's private configuration. Add or update only the email entries in **`.private/campus.env`**. Keep its existing Atlas URI, encryption keys and other settings. Do not replace that entire file with the example.

The root `.env` contains the local Compose port; it is not the mail configuration file. Never put credentials in `frontend/.env`, a `VITE_` variable, source code, this guide or GitHub.

On a managed hosting dashboard, enter these variables in the **campus/backend service's environment/secrets**, not the static frontend. Dashboard values normally omit the quotation marks shown in `.env` files.

## Option A — free personal Gmail SMTP for a small demonstration

1. Use a Gmail account controlled by the project operator.
2. Enable **2-Step Verification** in that Google account.
3. Create an **App password** at <https://myaccount.google.com/apppasswords>. Some managed college accounts disable this feature; use another permitted provider if it is unavailable.
4. Paste the generated app password into `SMTP_PASS`, without the display spaces. Do not use a student AMS password or your normal Google password.
5. Use the same Gmail address as `SMTP_USER` and the sender address in `CAMPUS_MAIL_FROM`.

```dotenv
CAMPUS_PUBLIC_URL="https://campus.your-domain.edu"
CAMPUS_MAIL_FROM="veltech-ams-mini <your-sender@gmail.com>"
CAMPUS_MAIL_REPLY_TO="your-sender@gmail.com"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="465"
SMTP_SECURE="true"
SMTP_REQUIRE_TLS="true"
SMTP_USER="your-sender@gmail.com"
SMTP_PASS="YOUR_GOOGLE_APP_PASSWORD"
```

Replace the public URL with the app's actual HTTPS origin, with no path, query or fragment. For local-only testing it may be omitted; email app buttons are then omitted. Port **587** is an alternative: set `SMTP_SECURE="false"` and keep `SMTP_REQUIRE_TLS="true"`.

Gmail has sending and anti-abuse limits. Google's personal-account guidance describes a limit around 500 emails/day; delivery can be restricted earlier. It is not a bulk-mail service or a guarantee that a college-wide workload will fit for free.

## Option B — free Brevo transactional SMTP

Create an account, complete its sending approval and verify the sender/domain as required by Brevo. Copy the **SMTP server, SMTP login and SMTP key from its SMTP dashboard**. The SMTP key is different from its REST API key. Use port 587 with STARTTLS, or a provider-supported TLS port. Keep the same variable names above and replace the Gmail values.

Brevo's published free plan allows **up to 300 emails/day after account approval**. OTPs, receipts and reminders all use that allowance. Check the current limits in your provider account.

If the hosting provider blocks SMTP, this project also supports Brevo's HTTPS API: clear `SMTP_HOST`, `SMTP_USER` and `SMTP_PASS`, keep the verified `CAMPUS_MAIL_FROM`, and set `BREVO_API_KEY` in the backend secrets. An incomplete SMTP configuration is reported rather than silently selecting another provider.

## Restart the updated campus service

For the localhost development stack:

```powershell
docker compose -f compose.yaml up -d --build --no-deps --force-recreate campus
```

For the optional public tunnel stack, use its exact Compose files instead:

```powershell
docker compose --env-file .env.tunnel -f compose.yaml -f compose.tunnel.yaml up -d --build --no-deps --force-recreate campus
```

For the Nginx production topology, use `.env.production` and `compose.production.yaml`. Updating only campus avoids unnecessarily restarting the academic worker and its pending AMS verification sessions.

Do not merge `compose.dev-mail.yaml` into a live deployment. Mailpit is a local test inbox and does not send Internet email; its development override deliberately uses `NODE_ENV=development`.

## Check configuration and delivery

From the project folder, after `npm run setup`:

```powershell
npm run email:check
npm run email:check -- --verify
npm run email:check -- --send-to=YOUR_OWN_REAL_EMAIL
```

The first command checks configuration without connecting. `--verify` checks SMTP connection/TLS/authentication without sending a message. `--send-to` explicitly sends the branded test message to the address you supply. No password or provider response containing secrets is printed.

Check the **actual running container** as well:

```powershell
docker compose -f compose.yaml exec -T campus node campus/scripts/mail-check.js --verify
docker compose -f compose.yaml exec -T campus node campus/scripts/mail-check.js --send-to=YOUR_OWN_REAL_EMAIL
```

For the tunnel deployment, prefix those `exec` commands with the tunnel's `--env-file .env.tunnel -f compose.yaml -f compose.tunnel.yaml` options. For Brevo HTTPS, use `--send-to` directly; SMTP verification does not apply to the REST API.

**Accepted** means the provider accepted the message, not that the inbox has confirmed it. Check Inbox and Spam/Junk. College mail filters, quotas, sender approval and DNS affect final delivery. Custom domains should have the SPF/DKIM/DMARC records recommended by the provider. Gmail sends as your permitted Gmail sender, not an invented `@veltech.edu.in` address.

## Password reset and delivery failures

- The app's forgot-password flow requires a verified recovery address or an authenticated VTU principal mapped to its official campus mailbox. It sends a six-digit, single-use code valid for five minutes and bound to the requesting browser.
- Application password reset does **not** change the university's AMS password. Keep a verified recovery email on the account before relying on application recovery.
- A temporary explicit SMTP rejection gets one short retry. Authentication failures and ambiguous post-DATA timeouts are not blindly retried.
- Confirmed event receipts/reminders use the existing durable MongoDB delivery queue, retry/backoff and duplicate-claim protection. A provider outage leaves a queued retry instead of inventing a delivered status. Repeated failures eventually require operator investigation.
- The server must remain running for scheduled reminders. Sleeping free hosts cannot guarantee on-time background reminders.

Troubleshooting: authentication failure → check the app password/SMTP key and sender; timeout → check the host's outbound SMTP rules and port; sender rejected → finish provider approval; accepted but no inbox message → check Spam, provider logs, quotas and college filters. Never disable TLS certificate verification to fix delivery.

Admin messages use the separate durable `admin_messages`/`admin_deliveries` queue. They send individual emails and record in-app delivery independently. SMTP outages leave mail queued; sender access is checked again before announcements are sent. Messages & email shows current delivery states. See [ADMIN-WORKSPACE.md](ADMIN-WORKSPACE.md) for audiences, permissions, limits and operator actions.

Template source: `services/campus/campus/services/mail-templates.js`. Editable examples and previews are included in `config/smtp.example.env` and `docs/email-previews/`.

Official references: [Google app passwords](https://support.google.com/accounts/answer/185833), [Gmail limits](https://support.google.com/mail/answer/22839), [Brevo pricing](https://www.brevo.com/pricing/). Checked 21 October 2026; provider limits may change.
