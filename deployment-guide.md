# Setup, update and install

This is the complete combined **veltech-ams-mini** application. The package stays at **1.8.0**. Use a current Node.js 24 LTS and Docker Desktop with Linux containers on Windows. No Ubuntu distribution or Bash setup script is required. MongoDB Atlas remains supported.

## Existing Windows installation

1. Stop the application with your existing `Stop.ps1`. Back up your existing `.private` directory and database/media data privately.
2. Extract the source ZIP into a new directory. Copy the existing `.private` directory into that new project directory. Preserve all keys, Atlas database names and SMTP settings. Never upload `.private` or production env files to GitHub.
3. In PowerShell, open the extracted directory that contains `package.json`, `Start.ps1` and `compose.yaml`:

```powershell
Set-Location P:\Intenship\veltech-ams-mini
docker compose -f compose.yaml build
powershell -ExecutionPolicy Bypass -File .\Start.ps1
```

The build command updates both service images; `Start.ps1` starts them and checks health. Open the localhost URL printed by the script. Do not delete volumes or generate new encryption keys for an upgrade. Rebuild the private academic service as well as the frontend/campus service to use the faster combined workspace endpoint.

## Fresh Windows setup

```powershell
Set-Location P:\Intenship\veltech-ams-mini
powershell -ExecutionPolicy Bypass -File .\Setup.ps1
powershell -ExecutionPolicy Bypass -File .\Start.ps1
```

The setup prompts for your own Atlas connection and keeps generated configuration in `.private`. Add your deployment IP to Atlas network access. The private examples document all variables. For React development, `npm run setup`, then `npm run dev:api` and `npm run dev` in separate PowerShell windows. A frontend-only preview does not provide live student records; the academic service must also be running for those.

## Deploy the complete app

Follow [HOSTING.md](HOSTING.md) for a Docker host with an HTTPS tunnel or [deployment.md](deployment.md) for Nginx/TLS and multiple campus replicas. The web ZIP is a production frontend build; live sign-in requires the backend and `/api/campus` routing at the same public origin.

Set these in the existing **private** files, using your actual values:

| File | Values to configure |
| --- | --- |
| `.private/campus.env` | `MONGODB_URI`, persistent `CAMPUS_LINK_KEY`, matching `CAMPUS_SERVICE_KEY`, exact `CAMPUS_ORIGINS=https://your-domain`, `CAMPUS_COOKIE_SECURE=true`, `ACADEMIC_API_URL=http://academic:8000/api/v1`, real SMTP sender/settings |
| `.private/academic.env` | Atlas `MONGO_URI`, original `MONGO_DB_NAME`, persistent `JWT_SECRET` and source encryption keys, matching `CAMPUS_SERVICE_KEY` |
| `.env.production` | Real DNS hostname and certificate directory when using the production Nginx topology |

Do not enable secure cookies on plain localhost HTTP. Do enable them for hosted HTTPS. Keep one academic worker because university browser sessions are process-local. Campus replicas can share durable Mongo sessions and media under the documented same-host configuration. Existing queue limits prevent a burst of students from opening unlimited AMS sessions.

Configure SMTP using [EMAIL-SMTP.md](EMAIL-SMTP.md). Put credentials only in private configuration. Test your real sender and password recovery after deployment; free provider limits and outbound SMTP availability depend on the chosen host. Mailpit is only for local development.

Before releasing the URL, check public health with the supplied production checker, then test your own login, reload, logout, one source sync, recovery email, downloads and a phone install. Keep the private academic API and MongoDB inaccessible from the public Internet. No deployment URL or real provider credentials are embedded in the downloadable project.

## Install on a phone

After hosting the complete application at a stable HTTPS address:

- Android Chrome: open the URL, then **Install app** or **Add to Home screen** in the browser menu.
- iPhone Safari: open the URL, tap **Share → Add to Home Screen**.

The PWA uses the existing logo, standalone display and service worker. Sign-in uses the existing rolling HttpOnly session; refresh and app updates restore a valid session. Do not clear browser/app site data if you want to retain that session. Actual logout, expiry or revoked sessions require sign-in again. AMS may separately request official verification when its upstream session expires.

For a signed Android APK/TWA, follow [ANDROID.md](ANDROID.md). Add your real origin on line 2 of `android/config.local.json` after copying `android/config.example.json`. Keep signing keys private and publish the required Digital Asset Links on your site. This package includes Android build tooling; it does not include a signed, connected APK without your domain and signing identity.

## What changed

The welcome starts after verified login; Wait for all sections overrides early exit; Open Home allows continued use while sync runs. The main academic workspace now needs one private request, overlapping reads are shared, and transient saved-session failures receive one bounded retry. Assessment marks retain their tables/exports without graphs; semester/final-result graphs remain.

See [VERIFICATION.md](VERIFICATION.md) for the recorded checks and their limits. The college's availability and free-host resource limits remain outside the app's control; an unavailable source is shown accurately instead of inventing records.
