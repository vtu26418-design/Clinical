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
