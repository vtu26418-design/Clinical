# UniEve Campus V1.2

One project for student details, attendance, timetable, academics, campus events, placements and a student community. The responsive web app includes phone bottom navigation, dark/light settings, a student photo across the header/home/profile, QR event tickets, role-scoped management, and optional encrypted device snapshots.

## Windows: Docker Desktop + MongoDB Atlas

No Ubuntu terminal, local Node/Python installation, or local MongoDB installation is required. Docker Desktop runs Linux containers internally; you do not need an Ubuntu distribution or Bash setup scripts.

1. Install Docker Desktop for Windows, enable Linux containers, open it and wait for the engine to start. In PowerShell, check `docker version` and `docker compose version`.
2. In MongoDB Atlas, create a cluster and a **database user**. Give that user read/write access to both `unieve_campus_v1` and `unieve_campus_attendance_v1`. Add your current Windows public IP in Network Access. Copy the **Drivers → Node.js** `mongodb+srv://` connection string and replace its password placeholder. URL-encode reserved password characters. Your Atlas website login is different from this database user.
3. Extract the source ZIP. Open PowerShell in the folder containing `Setup.ps1` and `compose.yaml`:

```powershell
cd "P:\Intenship\UniEve-Campus"
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1
```

Setup prompts for the Atlas URI with hidden input, builds both containers, checks the selected database for an administrator, and prompts for a first administrator when needed. Choose a 16+ character administrator password with upper/lowercase letters, a number and a symbol, at most 72 UTF-8 bytes. Keep this account separate from your AMS account. Then open **http://localhost:4100 on your Windows computer**.

After initial setup:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\Stop.ps1
```

`Stop.ps1` stops containers; Atlas data and `.private` keys are retained. Rerunning setup reuses keys and checks the database again. To update Atlas connection settings or use another port:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1 -ReconfigureAtlas
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1 -Port 4200
```

Use `-ConfigureOnly` to save settings without building/starting. `-UseExistingAdministrator` requires an administrator already present in the selected database. ExecutionPolicy Bypass applies to that PowerShell process only.

## First use

The opening preview is explicitly fictional. Choose **Connect campus account** to sign in with the administrator you created. In **Management → Accounts**, create student accounts and assign staff roles and department/club scopes. New campus accounts automatically receive their own private academic workspace, using the same campus login.

As a student, open **Settings → Connections**, save your own AMS username/password, load a fresh AMS challenge, type its code, and select **Sync AMS**. Saving credentials only encrypts them locally on the server; it does not attempt an automatic portal login. Each challenge lasts five minutes, belongs to that student's server session and is single use. A challenge from another browser/session will not work.

Live means the app requests its backend and displays the last successful university sync. Campus content refreshes at the interval in App preferences. AMS requires manual verification; private university records cannot silently refresh without an accepted authenticated session.

## University data coverage

| Module | V1.2 behavior |
|---|---|
| Name, department, batch, semester, mentor and photo | Displayed when provided by an accepted AMS profile. Missing fields remain unavailable. |
| Registered courses and timetable | Existing AMS adapter; source rows retain the source's period identifier. |
| Attendance totals, dated period marks, course grades | Optional conservative reader of labeled HTML tables reached through links discovered in the authenticated AMS dashboard. Unknown layouts are skipped; totals do not generate daily marks. |
| Green/red classes | Only an unambiguous, matching present/absent record. On duty is distinct; missing/conflicting records are neutral. |
| Home of VelTech | Student-developed AMS client, according to its Play listing/privacy policy. No independent documented API was found. |
| Fees, official documents, exams, mess menu | No verified connected parser available in this delivery. No invented live data. University systems remain the source for these modules. |
| University news | Read-only public university website feed. |
| Retired parent portal | Removed from active source checks and student sync. Legacy sync endpoint returns HTTP 410. |

**Live private AMS retrieval is unverified:** the portal was reachable, but manually answered login attempts were rejected. No private student records were imported for delivery. Attendance/results parsing is tested with synthetic fixtures; it is not a claim of full Home/AMS parity.

A failed or empty source response retains earlier stored rows. Each imported academic row records its source update time. Partial successful imports merge supported rows; they do not imply that all records are current.

## Events, social features and roles

Free registration produces a persisted QR ticket. Paid events use Razorpay order creation and server-side payment/webhook verification; no ticket is confirmed solely from a browser callback. Configure your own merchant keys in `.private/campus.env` (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`), restart the app and configure an HTTPS webhook before accepting real payments. Live merchant transactions/refunds were not exercised; review reconciliation, refund and pending-order expiry policies before production payments.

Students can publish/edit/delete their own posts, like/comment/save content, connect with other members, bookmark events, and track on/off-campus opportunities. Private academic data is separate from the campus profile. Club organizers manage their own club/department events; department coordinators manage department events; college event managers manage college events; placement officers manage opportunities; administrators assign roles and accounts. Permissions are enforced by the API.

## Device storage and mobile installation

Settings includes appearance, motion, refresh preferences, device snapshots and downloads. Device snapshots are opt-in, encrypted with a passphrase and relocked after reload. Do not forget that passphrase. Clear the snapshot in Device storage. Session tokens and AMS passwords are not part of exported snapshots.

This delivery is an installable **PWA**, not an APK. Desktop localhost supports development. For phone installation and connected mobile use, deploy the Docker app behind an HTTPS domain. Set `CAMPUS_COOKIE_SECURE=true` and `CAMPUS_ORIGINS=https://your-domain` in private config, use a reverse proxy, and publish the campus service only through that proxy. The default Compose port binds to Windows loopback; a phone cannot open the computer's localhost. The built mobile/web ZIP is a static preview unless served with the campus backend under the same origin.

## Upgrade safely

Extract V1.2 into a new `UniEve-Campus` folder. Do not run the old Bash scripts or start the old attendance/events folders for this version. For existing data, keep the same Atlas database names and preserve your original `CAMPUS_LINK_KEY`, academic `JWT_SECRET`, and `PORTAL_CREDENTIAL_ENCRYPTION_KEY` in the new private env files before starting. Keep the newly generated matching `CAMPUS_SERVICE_KEY` in both files. Back up private configuration securely; never include it in a ZIP or source control. V1.1 users with existing academic accounts verify that account password once in Settings to migrate ownership; email alone never claims an existing account.

## Troubleshooting

- `bash`/WSL errors: use the PowerShell commands above from the new combined project folder.
- `Setup.ps1` missing: extract the **source ZIP**, then enter the folder with `compose.yaml`.
- Docker daemon unavailable: start Docker Desktop and select Linux containers. No Ubuntu installation is needed.
- Atlas authentication/DNS/timeout: check the database username/password, percent-encoding, current IP entry and access to both databases. Allow outbound Atlas traffic from Windows; consult Atlas diagnostics for your actual cluster. Do not paste credentials into logs or tickets.
- Port occupied: stop the old campus app or run setup with `-Port 4200`.
- Service unhealthy: run `docker compose ps` and `docker compose logs --tail 80`. Redact private data before sharing logs.
- Existing encrypted connections cannot decrypt: restore the original private encryption keys. Setup intentionally refuses incomplete private files rather than silently replacing keys.
- CAPTCHA rejected: load a fresh challenge and enter the code from that challenge. A reachable portal is not proof of a successful student login.

## Developer checks

Source is organized as `web/`, `services/campus/` and `services/academic/` under one Compose project. Optional native developer checks use the locked Node/Python dependencies; Windows users do not need these toolchains for Docker startup.

```text
npm --prefix web ci
npm --prefix web test
npm --prefix web run build
npm --prefix services/campus ci
node --test services/campus/campus/tests/*.test.js
python -m unittest discover -s tests -v  (from services/academic)
```

Database tests use disposable local MongoDB databases with test prefixes, not your Atlas project. PowerShell configuration/flow checks are in `tests/powershell.ps1` and `tests/setup-flow.ps1`. V1.2 verification lists cloud Docker and Playwright checks and distinguishes live, synthetic, Windows and Atlas limitations.
