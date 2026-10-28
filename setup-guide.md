# Update and deploy 2.3.1

The project, website and Android app remain one application. This release uses
`https://app.veltech-mini-ams.me/`, package `in.velstudents.veltechams`, Android
version **2.3.1 / 20301**. Keep your current database, private configuration,
volumes and signing identity. No account migration or fresh AMS connection is
required solely because of this release.

## Update your existing deployment

Back up the current database, uploaded files and private configuration. Extract
the new project into your normal release directory and preserve `.private`,
`.env.production`, database/media volumes and existing session/link keys. Do not
run `down -v` or a new setup over your existing production secrets.

Use the same Compose files and environment file you currently deploy. For the
provided PostgreSQL production configuration:

```sh
docker compose --env-file .env.production -f compose.production.yaml -f compose.postgres.production.yaml config --quiet
docker compose --env-file .env.production -f compose.production.yaml -f compose.postgres.production.yaml up -d --build
```

Keep Atlas installations on their existing database configuration. This update
does not require changing databases. Fresh Windows development installations can
run `Setup.ps1` with Docker Desktop; no Ubuntu installation is needed.

## Serve the APK from your own domain

The ZIP includes `android-release/release.json` and its SHA-256-named signed APK.
These are public deployment files, verified against the actual binary signature,
package, version and alignment. The private signing key is not included.

Add or retain these values in **`.private/campus.env`** on your AWS server:

```dotenv
CAMPUS_APK_DIRECTORY=/app/media/app-releases
CAMPUS_ANDROID_PACKAGE_ID=in.velstudents.veltechams
CAMPUS_PUBLIC_URL=https://app.veltech-mini-ams.me
CAMPUS_ORIGINS=https://app.veltech-mini-ams.me
CAMPUS_COOKIE_SECURE=true
```

Use the existing media volume. With the same Compose options as your deployment,
copy the public folder into it; the example assumes your terminal is in the
extracted `veltech-ams-mini` source directory:

```sh
docker compose --env-file .env.production -f compose.production.yaml -f compose.postgres.production.yaml exec -T campus mkdir -p /app/media/app-releases
docker compose --env-file .env.production -f compose.production.yaml -f compose.postgres.production.yaml cp ../android-release/. campus:/app/media/app-releases/
docker compose --env-file .env.production -f compose.production.yaml -f compose.postgres.production.yaml up -d --no-deps campus
```

The included **public** APK/manifest files have read permission so the runtime
can serve them after copying. If another transfer method changes permissions,
restore read permission on those public files only; do not change permissions on
private environment files or signing keys.

If you use several campus replicas, copy through one replica or your normal
volume-maintenance job and ensure every replica reads the same media volume. A
separate host directory can instead be mounted read-only; use its container path
for `CAMPUS_APK_DIRECTORY`. Ensure the campus process can read the public files.
Keep the old APK until rollout is checked. Publish a new manifest only after its
new APK has finished copying.

After deployment, the public URLs are:

- Latest APK: **https://app.veltech-mini-ams.me/api/campus/app-release/latest.apk**
- Update details: https://app.veltech-mini-ams.me/api/campus/app-release
- Android association: https://app.veltech-mini-ams.me/.well-known/assetlinks.json

Settings downloads the checksum-pinned APK through this same domain. The stable
latest link also serves the verified local APK as an attachment. Neither route
redirects to GitHub or accepts an arbitrary external APK address. Without the
release files mounted, Settings correctly reports that no Android release is
available. The Actions artifact link is for the owner to retrieve build outputs;
it is never used as a student APK link.

Bypass Cloudflare caching/challenge substitution for `/api/campus/app-release*`,
preserve `Cache-Control: no-store`, and do not rewrite API errors to SPA HTML.
Keep normal account/academic authentication and WAF controls. Publish the included
public Asset Links JSON without login or a browser challenge. See
[AWS-CLOUDFLARE-MOBILE.md](AWS-CLOUDFLARE-MOBILE.md).

The build retains the certificate from the APK previously prepared here. The
provided GitHub Actions artifact could not be accessed, so its signing identity
was not verified. If a phone has a differently signed copy, Android will reject
an in-place update. Verify that copy before rollout; never replace or discard
your signing key to work around it. Installer and Play Protect prompts belong to
Android and cannot be suppressed by the website.

## What students see

- Returning AMS-linked students can sign into the workspace using their last
  verified password, without starting another university login or CAPTCHA. After
  the upgrade, legacy AMS-only accounts need one successful AMS verification to
  establish that password verifier, or use their already verified recovery email.
  Only a secure hash is stored. This does not change the university password,
  renew an expired AMS session or mark cached records as newly synced. A new
  university data session still needs official verification if AMS requires it.
  Existing signed-in app sessions stay open.

- The live reminder understands explicit AMS AM/PM times and shows the current
  class, next class and relevant staff publications. Missing times stay unknown.
  Staff holidays, follow-day policies and special classes still apply.
- Follow updates in place. Delayed background reads cannot undo a newer action
  or restore private content after unfollow. Suggestions scroll horizontally.
- Phone swipes switch adjacent main tabs without capturing media, form controls,
  horizontal carousels or native back gestures. Disable them in Settings →
  Appearance & alerts → Swipe between pages.
- The blue/teal/silver 3D hybrid logo has no surrounding circle or stamp. Its
  sides rise, cap lands, then the centre appears. Reduced motion is respected.
  Text uses a locally served Inter font.
- A known older Android build receives an optional update notice after sign-in.
  Later defers that release for24hours. Web update Later is consistent across
  offline/online launches. An unknown installed Android version is labelled
  unknown. Android confirms installation; the website never claims it installed.
- Settings → Install & updates → Refresh app assets offers a confirmed refresh
  without deleting sessions, saved student records or downloads. There is no
  automatic destructive reset or forced logout after an update.

## Seating imports

Authorized staff open an examination's seating workspace and upload CSV, XLSX
or an extractable-text PDF. Use Course Code, VTU Number or Name, Room and Seat.
The downloadable template and exported preview include the exact course code.
Inspect source row numbers, matching methods and excluded issues before
publishing. Exact VTU is preferred. Names must match one verified eligible AMS
student; ambiguous or incomplete identity data is excluded. Reimport corrected
files or correct rows in the review table. The student endpoint returns only
that student's eligible published assignment. Original full rosters stay
staff-only. Legacy XLS must be saved as XLSX/CSV; scanned PDFs need reviewed OCR
or CSV conversion. The project does not silently invent missing seats.

## Verify before student rollout

Check the three domain URLs above, expected2.3.1/20301 metadata and checksum.
Install on a test Android phone; test update/Later, login persistence, class
times, one real AMS read-only sync, private Follow behaviour, and seating with two
students. Test notification permissions on the actual deployment. The supplied
[verification record](VERIFICATION.md) distinguishes automated checks from phone,
production and upstream university acceptance work. SMTP values remain in
[EMAIL-SMTP.md](EMAIL-SMTP.md); this update does not replace email secrets.

Developed by VEL STUDENTS.


# Android and web update deployment

The Android application ID stays `in.velstudents.veltechams`. Keep the existing
private signing key outside source/export archives; never regenerate it for an
update. Android requires the same signing certificate and a higher versionCode.
The supplied Actions artifact URL returned 404 during verification: its package,
version and signing certificate could not be established. Do not claim this
release can replace that unknown APK without checking it independently.

## Manual AWS / Cloudflare deployment

1. Build signed Android release using the existing signing identity and the
   documented Android build commands. The `Build signed Android release` workflow
   restores that key from environment secrets and independently verifies the APK.
   Download its artifact and retain the whole `public-release` directory. It has
   `release.json` and a SHA-256-named APK. The workflow artifact URL is an
   authenticated CI download, not a public student download link.
2. Alternatively, generate the same directory locally with the Android SDK set:

   ```sh
   node scripts/publish-android-release.mjs --apk=android/out/veltech-ams-mini-release.apk --receipt=android/out/signing-receipt.json --out=/tmp/public-release
   ```

3. Copy the verified directory to an AWS server path readable by the campus
   process, e.g. `/srv/veltech/app-releases`. Preserve the APK and manifest
   together. Set these **server** environment variables before restarting campus:

   ```dotenv
   CAMPUS_APK_DIRECTORY=/srv/veltech/app-releases
   CAMPUS_ANDROID_PACKAGE_ID=in.velstudents.veltechams
   ```

   For Docker mount it read-only and set `CAMPUS_APK_DIRECTORY=/app-releases`:
   `-v /srv/veltech/app-releases:/app-releases:ro`. The manifest is read on each
   request, so a later release can replace `release.json` atomically after its
   APK is copied. Keep old SHA-named APKs until the rollout is checked.
4. Deploy the frontend build and route `/api/campus/*` on the same HTTPS origin
   through Cloudflare to the campus server. Bypass Cloudflare caching for
   `/api/campus/app-release*`; preserve query
   strings and `Cache-Control: no-store`. Do not rewrite API errors to index.html.
5. Verify `GET /api/campus/app-release` returns `available:true`, expected package,
   version, certificate and checksum. Download its exact `url`, compare its
   SHA-256 with the manifest, then test an actual device upgrade. Publish the
   generated `assetlinks.json` at `/.well-known/assetlinks.json` for the real
   origin using the existing signing certificate. Never publish private keys.

Settings always checks the latest server metadata and validates downloaded bytes
before opening the browser download. Android alone confirms installation and may
show installer or Play Protect prompts. An unknown installed version is labelled
unknown; URL parameters alone cannot establish installation. A verified Android
launch enables a global release check per authenticated owner, while
visible and online. Returning to the foreground or reconnecting checks again
after a 15-minute cooldown; simultaneous events share one in-flight request. Later defers that release for that owner for 24 hours.

The stable public install address is
`https://app.veltech-mini-ams.me/api/campus/app-release/latest.apk`.
It serves the local verified APK directly. No GitHub download or external
redirect is used for the APK. See [V2.3-UPGRADE.md](V2.3-UPGRADE.md) for the included
public release folder and exact Docker copy commands.

Web updates support Later for 24 hours per owner across pending web updates. Accepting the
update checks the service worker registration, waits for installation when needed,
activates the waiting worker and reloads after control changes. Settings offers
“Refresh app assets” to Android and web users with an explicit confirmation and
Later. It checks for new website assets and reloads without native reset or APK
reinstallation. Active and waiting Workbox workers can share a precache, so this
flow never deletes caches, cookies, local storage, IndexedDB or private downloads.
A failed update check leaves the app running; declining never reloads. No real AMS
or production writes are part of this process.


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
