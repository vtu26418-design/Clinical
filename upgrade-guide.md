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
.\Start.ps1
.\Stop.ps1
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
`versionCode`. The example release is 2.0.0 / 20000. Do not lose the signing key.

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
