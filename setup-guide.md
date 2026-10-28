# Update, install and share veltech-ams-mini

This package is **2.3.3**, Android build **20303**. It keeps the same application
ID, `in.velstudents.veltechams`. The logo design is retained with the original Attendance project sky blue
#0EA5E9, lighter ice-blue tints and satin silver. The paint finish is smooth with
restrained reflections; there is no glow halo or animated brightness pulse. The
centre university emblem animates independently.
Login, navigation, settings, launch, favicon, PWA icons, Android launcher and
native splash use the updated artwork.

## Read this before updating an installed APK

The APK included in this package is signed with the same private identity as
the APKs previously prepared in this workspace. Its public certificate is:

```text
3B:44:DD:8A:C3:15:56:4A:27:A7:FA:2D:03:5C:3E:58:1A:FF:20:5A:7C:B6:E6:2C:E4:5E:28:3B:28:E4:C7:68
```

A read-only check on 28 October 2026 found your public domain listing a **different** certificate:

```text
0F:F3:49:D9:8A:0F:71:DA:1D:EF:4B:49:31:86:17:49:82:C2:27:32:31:2A:80:8D:DA:4D:82:92:7E:5F:54:78
```

That public statement does not establish the certificate of an installed APK.
Check your existing APK with Android SDK `apksigner verify --print-certs`.
Android permits an in-place update only with the same package and compatible
signing identity. If your distributed APK uses the second certificate, rebuild
this source with **your original GitHub Actions signing secrets**, then publish
that workflow's `public-release` directory and generated `assetlinks.json`.
Do not replace the original key, disable signature checks, or force students to
erase their app as an update workaround. Website/PWA installations are separate
from signed APK installations.

## Files in the full ZIP

- `veltech-ams-mini/`: the combined React frontend, campus and academic services,
  Android source/build scripts, Docker files and configuration examples.
- `android-release/`: verified public `release.json` and its SHA-256-named APK.
- `START-HERE.md`: entry instructions.

The private signing key, real account credentials, server secrets, databases and
student records are excluded. Preserve your current `.private` files, production
environment and persistent volumes. Back them up privately before replacing
source. Do not run `docker compose down -v` during an upgrade.

## Windows local setup — Docker Desktop

Extract the full ZIP. Open PowerShell inside `veltech-ams-mini` and run:

```powershell
.\Setup.ps1
.\Start.ps1
```

Follow [the setup guide](V2-UPGRADE.md) if you need the individual configuration
steps. Docker Desktop must be running. No Ubuntu terminal or locally installed
MongoDB/Python/Node is required for the Docker run. Use your existing database
configuration when upgrading; this patch does not require a database migration.

## Deploy the website and API on AWS / Cloudflare

Update your existing source without overwriting private configuration. Keep the
same Compose project name, database, volumes and session/signing keys. Build and
start using the **same Compose files you already deploy**. For the supplied
production PostgreSQL configuration, from the extracted source directory:

```sh
docker compose --env-file .env.production -f compose.production.yaml -f compose.postgres.production.yaml up -d --build
```

For a different existing configuration, use its current file list instead.
Keep the academic service at one worker: its active university sessions are
process-local. Campus replicas must share release/media storage and the existing
production rate-limit store. Do not increase upstream concurrency to hide source
congestion or start multiple automatic credential retries.

Keep these server settings in `.private/campus.env`:

```dotenv
CAMPUS_PUBLIC_URL=https://app.veltech-mini-ams.me
CAMPUS_ORIGINS=https://app.veltech-mini-ams.me
CAMPUS_COOKIE_SECURE=true
CAMPUS_APK_DIRECTORY=/app/media/app-releases
CAMPUS_ANDROID_PACKAGE_ID=in.velstudents.veltechams
```

Keep existing private keys and email/database settings. These are server
settings, not `VITE_*` frontend variables. Never place SMTP passwords, database
credentials, session keys or Android signing passwords in the frontend.

## Publish the APK to your domain

The prior read-only metadata check on 28 October 2026 returned `available:false`: the site
was reachable, but its server had no published APK available. Deploying the web
frontend alone does not publish the APK.

Choose the directory signed with the correct identity first. Copy its APK
completely, then publish its matching manifest. For the supplied Docker volume,
the following example uses the same production Compose file list as above:

```sh
docker compose --env-file .env.production -f compose.production.yaml -f compose.postgres.production.yaml exec -T campus mkdir -p /app/media/app-releases
docker compose --env-file .env.production -f compose.production.yaml -f compose.postgres.production.yaml cp ../android-release/. campus:/app/media/app-releases/
docker compose --env-file .env.production -f compose.production.yaml -f compose.postgres.production.yaml up -d --no-deps campus
```

For an Actions build, substitute its `public-release` directory for
`../android-release`. Retain the old APK until the rollout is checked. All campus
replicas must read the same published release. The included public files are
readable; preserve read permission if using a different transfer tool. Do not
change permissions on private keys or environment files.

Configure Cloudflare to preserve `Cache-Control: no-store`, query strings and
attachment responses for `/api/campus/app-release*`. Do not serve a browser
challenge or HTML fallback instead of release metadata/APK bytes. Keep private
account/academic authentication and caching protections intact. Review security
events and scope any needed public-path exception narrowly.

Publish the `assetlinks.json` generated for the APK's **actual** certificate at
`https://app.veltech-mini-ams.me/.well-known/assetlinks.json`, publicly readable
as JSON without redirect, login or browser challenge. The bundled public file
matches the bundled APK; it does not match the different certificate previously
listed by your server. If supporting multiple independently verified release
keys, maintain the appropriate certificate list deliberately. A domain statement
does not make differently signed APKs compatible with in-place updates.

## Check it before sharing

1. Open `https://app.veltech-mini-ams.me/api/campus/app-release`. It must report
   `available:true`, the intended package, version, certificate and SHA-256.
2. Download the exact `url` from that response. Confirm its SHA-256 matches the
   manifest and the HTTP response is an APK attachment, with no external redirect.
3. Open the public install page while logged out. It must show the Android APK
   without requesting an account or university verification.
4. Check the public Asset Links file against the APK's certificate. Test the
   website, APK installation and same-key update on a real Android phone.
5. Keep existing sessions, personal records and downloads. Refreshing website
   assets uses the safe service-worker update flow; it does not erase app data.

The browser may apply icon changes to an existing PWA later. Updating an installed
APK's launcher/splash icon requires installing the new correctly signed APK.

## Share links using your own domain

Share this page with students:

**https://app.veltech-mini-ams.me/#/install**

Or share the direct APK attachment:

**https://app.veltech-mini-ams.me/api/campus/app-release/latest.apk**

Settings → **Android app & updates** provides **Share download page** and
**Copy APK link**. The Android APK is the primary action; optional browser/PWA
installation is in a separately labelled collapsed section. The page reports
“Download requested”; Android confirms whether installation succeeds. Students
do not need GitHub access.

Your screenshot's “From Chrome” identifies a Chrome-managed web installation.
The device's “Unable to find information” message is a reputation/information
warning, not an error the website can dismiss. Android, Chrome, Play Protect and
the device vendor control these messages. Signed HTTPS distribution and correct
domain association verify important parts of delivery, but do not guarantee
warning-free sideloading. A Play Store release can provide a familiar reviewed
distribution route; acceptance and warning suppression are not guaranteed.
Do not disable device protections. Stop if the package, source or signature
does not match the release you intended to install.

## University records and login

**University records** are the authorized AMS records, **Staff updates** are
examinations/notices/documents published in this app, and **Saved on this device**
is an offline copy with its original successful sync time. They are labelled
separately without changing record ownership or pretending old rows are live.

Previously verified returning accounts can use the existing password-only app
login. That opens the app; it does not create a new upstream AMS session.
The public AMS sign-in page currently includes its own verification. Home of
VelTech publicly describes connecting directly to AMS and does not publish a
separate integration API. A new or expired upstream session can therefore still
require official verification. This patch does not bypass it, store raw university
passwords, or claim continuously live data without an authenticated source.

Busy-source responses now retain an unused challenge for a manual retry. Invalid
answers are reset. Reconnection has the same bounded source-login deadline as
initial sign-in; credentials are not automatically resubmitted. Offline records
do not show a live syncing spinner, partial refreshes do not appear as successful,
and previous records retained after a failed source refresh stay clearly marked.

Read [APK installation details](ANDROID-INSTALL-SHARE.md),
[Android build instructions](ANDROID.md),
[AWS/Cloudflare checks](AWS-CLOUDFLARE-MOBILE.md) and
[verification evidence](VERIFICATION.md). SMTP configuration remains in
[EMAIL-SMTP.md](EMAIL-SMTP.md).

Developed by VEL STUDENTS.


# Install and share the Android APK

Share this public page with students:

**https://app.veltech-mini-ams.me/#/install**

It provides the Android APK, current release details, and installation instructions before sign-in. Settings → Android app & updates offers the same APK actions. **Share download page** uses the device share sheet when available and otherwise copies the guide link. **Copy APK link** copies the stable direct attachment:

`https://app.veltech-mini-ams.me/api/campus/app-release/latest.apk`

Both URLs use the app’s own domain. The direct URL always selects the latest locally published verified release and does not redirect to GitHub or another download host. Do not distribute CI artifact URLs or links to authenticated settings pages.

## On an Android phone

1. Open the public page above and select **Download Android APK**.
2. Open the browser’s Downloads and open `veltech-ams-mini-<version>.apk`. If Android asks, review the source and allow this browser to install the file.
3. Review and confirm **Install** or **Update** in Android. Open the app from Android’s app drawer. Existing APK users need an update signed with the same certificate and a higher Android version code.

The website reports **Download requested** after the link is pressed. It cannot confirm that the browser saved the APK or Android installed it. If nothing downloads, check the release again. If the server reports that the release changed, refresh the release details and use the new button.

Chrome’s menu item **Install app** or **Add to Home screen** installs a separate browser web app. Android may describe it as **From Chrome**, using the web manifest’s short name **Veltech mini**. That browser installation does not establish the Android package identity `in.velstudents.veltechams`. Browser standalone mode and URL query flags are never treated as proof that the APK is installed. The APK is a Trusted Web Activity: it uses a compatible browser to display the website, while its signed Android package and app-drawer entry are distinct from a Chrome-installed web app. Removing a browser web app is optional; the APK does not require deleting saved website data.

Android, the browser, and Play Protect control prompts and reputation warnings. A valid signature and working domain association cannot guarantee that a device suppresses warnings. Review warnings and stop if the source or package identity differs. Do not turn off Play Protect or other device protections. The web page cannot install silently or override the device’s decision.

## Delivery and integrity

Release metadata at `/api/campus/app-release` is public and contains no account information. The UI validates the package, version, size, SHA-256, and exact relative pinned URL `/api/campus/app-release/apk?sha=<sha256>` before exposing its primary download. The browser downloads this same-origin attachment directly, preserving the website origin in the download manager instead of using a JavaScript Blob URL. The server serves only the local APK named by its checked publication manifest, checks its SHA-256, and requires the expected checksum on the pinned endpoint. A changed checksum returns HTTP 409. The stable share link selects the latest verified release at the time it is opened.

The browser does not repeat the hash check in JavaScript before saving. HTTPS protects transport; server publication and hash checks protect release selection; Android verifies the APK’s signature during installation. Operators can independently compare the downloaded file to the displayed SHA-256. No remote redirect, caller-supplied file URL, new account permission, or new authentication mechanism is used. The exported byte-verification helper remains available for independent checks and existing tests.

## Deployment checks

Deploy the frontend, the verified release directory, and the generated `/.well-known/assetlinks.json` for **app.veltech-mini-ams.me** using the existing deployment guide. Metadata and both APK routes must work without signing in. Preserve `Cache-Control: no-store`, APK content type and attachment disposition. Bypass edge caching and HTML/challenge substitution for these existing public release endpoints; keep account and academic API protections intact. Do not publish signing keys or put them into Docker images.

Check the public metadata version/package/hash, download its exact pinned URL and compare the file’s SHA-256. Confirm the stable link returns the APK without an external redirect. Check an old checksum returns 409 after publishing a new release. Verify `/.well-known/assetlinks.json` over public HTTPS without redirects or challenge pages and with the expected package and signing certificate; a local signing receipt is not proof that the public association is live. Then test an actual Android installation and same-key update. A website deployment alone cannot replace an APK already on a phone.

Asset refresh and **Later** retain their existing behavior: website updates use the service worker lifecycle, retain sessions/private caches/saved downloads, and never reset or reinstall the native app.


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
