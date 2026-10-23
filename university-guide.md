# University publishing and administration

This update retains version **2.0.0**. Existing attendance, results, community, events, account and deployment features remain in the combined project.

## Upgrade on Windows with Docker Desktop

1. Back up your database and persistent uploads. Keep your existing `.private` folder and encryption/signing keys. Extract this source into a new folder; copy the existing `.private` folder into that extracted project. Do not run two copies against the same database while upgrading.
2. Open PowerShell in the extracted `veltech-ams-mini` folder. Start Docker Desktop, then run:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1
   powershell -NoProfile -ExecutionPolicy Bypass -File .\Start.ps1
   ```

   The scripts use Docker; Ubuntu and a local MongoDB install are not required. See `docs/V2-UPGRADE.md` for PostgreSQL-backed storage, preserving an existing Atlas database, backups and verified migration. Do not switch an existing database URI without the migration checks.
3. Open `http://localhost:4100`. Use the existing single login; the account's assigned role opens its workspace.
4. Students who used an older release need one successful AMS refresh to populate the new protected audience cache. They do not need to create a new account. AMS verification is requested only when the upstream service requires it. Imported/personal records cannot grant access to another academic audience. Missing official fields stay unavailable rather than being guessed.

## Publish examinations

1. Open **Exam schedules → New schedule**. Enter title, exam type, year and term. Choose university-wide or an assigned department. Optional batch, regulation, semester and section restrictions must match the student's official AMS fields. A missing field will not be treated as a match.
2. Create the draft. Import a PDF, `.xlsx` or UTF-8 CSV, or add rows. Templates are available in the page and `docs/templates/`. Maximum: 8 MB and 500 examination rows per schedule. Split a larger university release into schools/terms. Excel imports may contain supported tables across worksheets; only explicit merged cells carry dates across rows.
3. Check every course code, date, time and audience against the original. PDF text/OCR may confuse `I`, `1`, `O` and `0`. The importer preserves ambiguous characters and displays review notes. Image-only/unsupported layouts need an Excel/CSV transcription. A session such as AN alone never supplies an invented time.
4. Confirm the review and publish. Students see only exact normalized registered course codes plus all applicable audience restrictions. The original generic schedule document becomes available only to an eligible signed-in student.
5. To correct a released schedule, edit and save its draft, then **Save & republish**. Students continue seeing the previous published revision until the new complete revision is released. Recheck seating after republishing: old revision seating is hidden rather than silently attached to changed examinations. **Withdraw publication** hides it while retaining the schedule. **Delete schedule** removes it from active lists and student access while retaining audit history. A removed schedule is read-only.

### Your supplied schedule

The two-page reference was tested: 35 rows; merged date groups from 26 October to 2 November 2026; 16:30–18:00 IST. Its visible heading says **Test-II and Mid Term Test-I**, while the filename says Test III/Mid II. Select the correct title/type from the issued document during review. The reference is not automatically published or seeded into your deployment.

## Bulk seating without entering every student

1. Open the published schedule and select **Seating & documents** for its examination.
2. Upload the examination roster as CSV or one XLSX worksheet. Required column: `VTU Number`. Optional: `Name`, `Course Code`. Use the exact-course filter when the file covers several subjects. An explicit roster is required; the app does not guess eligibility from social profiles.
3. Enter rooms, halls, capacities and optional seat prefixes. Students are ordered by VTU and fill rooms in the configured order. Up to 100 rooms, 1,000 seats per room and 5,000 students per release. Insufficient capacity stops generation without changing the existing published release.
4. Generate the draft; search, check and correct its assignments, or download the preview CSV. Confirm and publish. Each student sees only their own verified VTU seat for a matching current examination. An already assigned PDF/Excel/CSV seating list can still be imported.
5. Keep full original-document download disabled when the roster contains other students' details. Bulk rosters start private. Room/seat publication sends the existing in-app seating notification; it does not silently email a private roster.

## Calendar and student reminders

Publish holidays, substitute working days or selected-student special classes under **Calendar & holidays**. A Saturday/Sunday following Monday uses Monday's recurring classes on the actual date; it does not copy Monday's attendance marks. Holiday hides classes for that date. Individual updates override department updates, then university updates. Home reminders show actual dates and weekdays. Calendar and room changes refresh about every 25 seconds while the page is visible, and on focus, even when full academic auto-refresh is off. Exams poll about every 20 seconds. Network failures retain the last successful displayed data and surface the request error.

## Correcting other publications

Events, news, placements, calendar and semester schedules retain their edit/archive/remove controls with action permissions. Published forms can be edited at their full-page editor before responses arrive. After responses exist, close/reopen is supported; their questions and audience are locked to preserve submitted answers. Archiving hides a form while retaining responses. Already delivered email cannot be recalled; send a correction through Messages when needed.

## Roles and scope

Use **People & access** for students, faculty and administrators. Presets are a starting point; grouped module/action choices show exactly what is granted. An administrator cannot grant actions above their own limits. Faculty/coordinators retain their department/ownership scopes. The server checks every action, including POST publish/import/withdraw and bulk seating allocation. Audit/sign-in history is retained; deleting a publication does not erase the accountability record.

## Hosting and installation

Existing SMTP, HTTPS, domain, database and Android packaging configuration is unchanged; use `README.md`, `docs/DEPLOYMENT-UPDATE.md` and `docs/EMAIL-SMTP.md`, plus `docs/V2-UPGRADE.md`. Keep the academic service private, use persistent database/media volumes, secure cookies on your HTTPS domain and a shared rate-limit store for multiple campus instances. Back up before production upgrades. The web app can be installed as a PWA over HTTPS. A signed Android APK still needs your later HTTPS domain, domain association, Android build tools and signing key; no signed APK is included or claimed tested here. Free hosting/database tiers have provider limits and are not unlimited university-scale capacity.

## Verification scope

See `docs/VERIFICATION.md` for fresh automated and browser checks. The supplied PDF and controlled fixture accounts were used for read-only parsing and app publication tests. No real university records, real email recipients, or production accounts were changed. Live AMS login, provider availability and physical Android installation were not tested in this update.
