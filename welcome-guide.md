# Login welcome screen

The existing shared sign-in now opens a full-screen, mobile-friendly welcome:

1. The application logo enters with orbit and glow animations while sign-in runs.
2. After authentication, the signed-in account's photo and name replace the logo. Available official student ID and department appear below. Accepted AMS profile changes update this view as they arrive.
3. An indeterminate syncing indicator sits underneath. The full-screen background adds blue light gradients, a subtle grid and floating academic icons.
4. The workspace opens after the first usable records. Remaining source work continues through the existing background sync and dashboard status.

The logo phase lasts about 650 ms when animation is enabled. A newly available identity or photo remains visible for about 650 ms before the screen closes. These timers do not delay authentication or source requests. A **Continue to workspace** button appears after 3.5 seconds following authentication; the screen releases automatically after eight seconds even if a section is still loading. This timeout does not mark unavailable records as synced.

No percentage is fabricated. Missing photos use the existing initials fallback. No demo profile or previous account is read for this screen, and identity is not saved to additional browser storage. Sign-out clears its state. Failed sign-in and university verification return to the actionable login form. Staff accounts use their existing assigned destination and do not gain student academic requests.

Existing **Settings → Appearance** controls for opening/background animation are honoured. Both the app's reduced-motion preference and the operating system's reduced-motion preference stop welcome motion. Safe-area padding, wrapping names and short-screen scrolling support phones and installed PWAs. This remains a web/PWA update; Android signing and the public HTTPS address are configured separately as documented in `ANDROID.md`.

No new environment variables, dependencies, database migration or university permissions are needed. Keep your existing `.private` configuration and persistent keys when updating. Rebuild the frontend/container and accept the normal PWA update notice.

For a local Windows React preview, use PowerShell:

```powershell
npm run setup
npm run dev:api
```

In a second PowerShell window:

```powershell
npm run dev
```

Use the existing Docker setup/start scripts for the complete campus and private academic services; see `README.md`. This source ZIP contains no private SMTP credentials, student passwords, session cookies or Atlas connection strings.

Validation uses the actual React application with fictional, intercepted API responses. It covers 320/390-pixel phones and desktop, the logo-before-identity sequence, late profile arrival, actual image loading, failed credentials, required verification, reduced motion, slow sync, automatic release, saved-session restoration and sign-out. These checks do not establish a new live AMS login or performance guarantee for the university's server.
