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
