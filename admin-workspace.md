# Campus administration guide

Use the existing shared login. Your saved account role opens either the student workspace, faculty tools or the separate navy administrator workspace. A typed email or username never grants a role. The setup-created owner retains full administration; an upgrade does not need another owner or a database reset.

## Update on Windows with Docker Desktop

1. Extract the complete source ZIP into a new folder. Copy your existing `.private` folder and root environment files into it privately; preserve their encryption keys. Do not copy `node_modules`, old frontend builds or uploaded media into source control.
2. Keep the same Compose project name and existing `campus-media` volume. If changing folder names, use the old project name with `docker compose -p YOUR_EXISTING_PROJECT` consistently. The volume contains uploaded images and private examination files. Atlas retains the database separately.
3. From PowerShell in the project folder, run `docker compose -f compose.yaml up -d --build`. For a production/tunnel installation, use the exact Compose files and environment file from your existing deployment instead; see README.md and docs/HOSTING.md. This rebuilds both APIs and the React bundle without Ubuntu commands.
4. Check `docker compose -f compose.yaml ps`, then open `http://localhost:4100`. Sign in with your existing owner account. Reload an installed PWA when the update notice appears.
5. For React development, run `npm run setup`, start the Docker APIs with `Start.ps1`, then `npm run dev`. The combined production app is still the Docker service on port 4100.

No new environment variables are required for the admin update. Keep your Atlas, private service key, JWT/encryption keys, exact public origin and HTTPS cookie configuration. SMTP settings belong in `.private/campus.env` locally or the campus backend's secret environment on your host. See docs/EMAIL-SMTP.md. No SMTP password or AMS password belongs in a `VITE_` variable.

## People and administrator limits

Open **People & access → Manage roles & access → Create account**. Select Faculty with a department, or Limited administrator. Choose its modules and individual **View, Create, Update, Delete/deactivate, Export** actions. A newly selected area initially enables only View. New limited admins receive no unrestricted owner flag.

Named roles are **Event administrator**, **Examination administrator**, **Community moderator**, **News editor**, **Student support administrator**, and **Account and access administrator**. Select a role to apply its allowed actions automatically. The list includes only capabilities the creating admin can grant. A manual permission change switches the label to **Custom access**; named roles cannot carry unrelated hidden permissions. Neither a role name nor account creation can create an unrestricted owner.

| Role | Initial areas |
| --- | --- |
| Event administrator | Events, entry operations and participant exports |
| Examination administrator | Examination publications/seating; calendar view/create/update |
| Community moderator | Content review/removal; support view/update |
| News editor | Notices and campus communications |
| Student support administrator | Account view, support view/update and academic read |
| Account and access administrator | Student/faculty account management and limited-admin management |
| Custom access | Only the module/actions explicitly selected |

Every role is intersected with the grantor's current permissions. A restricted creator cannot use a template to grant extra actions. Only the owner or an admin with **Create and manage limited admins → Create** may create admin accounts. Department-scoped duties still use the faculty/coordinator/organizer roles; these admin templates apply to their selected app modules.

Use **Assign role** on the same account to edit these limits later. Saving role/permission changes closes that account's sessions. Deactivation closes sessions and blocks login while retaining records and tickets. Owner administrators cannot be demoted/deactivated through this page. A limited admin can manage only its directly created admins whose grants remain within its own current granting ceiling. Grants are independent explicit assignments, not inherited from the creator; changing the creator does not silently change another admin's saved grants. The owner can review/change each administrator directly.

Use the directory filters to find students, faculty and administrators. Reading another student's saved official profile/attendance needs both account View and academic View access. Academic administration retains existing server-side write restrictions. Admin settings never reveal passwords, sealed university tokens or encryption keys. Official university records are not edited by changing an app event, exam or calendar.

## Events and attendance

Create/edit an event with date/time in IST, scope, capacity, paid/free entry, instructions, eligibility, contact email and up to 20 rules. New registrations must acknowledge the rules. Payment-dependent tickets remain unavailable for entry until payment is confirmed.

Open **Event operations**, choose the event, and assign an active faculty/admin account. QR scanning, manual check-in and participant messaging are separate editable grants that apply to that event only. A grantor cannot confer a capability it does not hold. Ordinary students cannot be appointed to check in others. Revoking a grant takes effect on the next API operation.

QR scanning needs HTTPS and camera permission on supported browsers. Paste ticket QR data if a scanner is unavailable. Manual entry requires the assigned staff member to check the college ID and enter a note; it records the staff member, time and method. Duplicate, unpaid, cancelled or expired QR tickets are rejected. The roster shows registered/attended status. Existing analytics, receipt and refund controls remain available through event management.

## Community moderation

Open **Community moderation → Posts & reels**, select Review removal and enter a clear reason. Removal archives/locks the content, records the moderator/reason, notifies its owner and queues a branded individual email. The owner cannot restore moderated content through their archive. Existing self-archive/restore continues to work for content the owner archived themselves. Student reports and support remain available for follow-up.

The in-app notice survives removal of the source post. A temporary SMTP outage does not erase the reason; queued email delivery retries. Queue status is available under Messages & email. Email acceptance is a provider response, not an inbox receipt.

## Messages and email

Administrators with communications Create can queue updates to all active students, all active members, an assigned department, scoped event registrants/attendees or explicit external email addresses. Faculty can message only their assigned department or events where they hold email access. Pick email and/or in-app delivery; external addresses use email only. Recipients do not receive one another's addresses.

Each request uses an idempotency key so retrying the same form does not recreate its deliveries. Delivery status, cancellation of pending messages and retry of failed delivery require their corresponding permissions. Sender/audience access is rechecked when an announcement is sent. Mail already accepted by a provider cannot be recalled. A normal campaign is limited to 5,000 app accounts or 500 explicit external addresses; split larger audiences into departments/events. Background jobs require the campus backend to remain running. Provider quotas still apply.

## Exams and student seating

1. Open **Exams & seating**. Publish an examination with department, course, date, time, semester/section and instructions.
2. Select **Seating & documents**. Download the template or upload one CSV, XLSX worksheet or text PDF, up to 8 MB/5,000 students. Required headers: `VTU Number, Room, Seat`; optional: `Hall, Reporting Time, Notes`.
3. Check and correct the entire imported preview. Image-only or unrecognized PDFs require manual row entry. Duplicate VTUs, formulas and active PDF content are rejected. One document covers one examination. Do not publish until the original attachment agrees with the checked rows.
4. Select whether assigned students may download the **whole original document**, then confirm the review and Publish seating.
5. In **Academics → Examinations**, each student sees only the row matching their verified university principal. A typed query/social ID cannot choose another student. If full-document download is enabled, matching students can download the complete attachment as requested; turn it off for lists the institution should not disclose in full.
6. Reopen Review/edit to change seating, or Withdraw to remove it. Student views refresh in the foreground; a previously copied private file URL is checked on every request. Withdrawing the exam also removes seating and blocks its file download. A downloaded local copy cannot be recalled.

Publication uses a per-exam database lease, a revision check and staged rows before exposing the new exam pointer. A stale tab must reload; concurrent publish/withdraw operations do not silently overwrite newer work. Private originals are stored in the existing persistent `campus-media` storage, outside public media URLs. Keep the media volume backed up with Atlas.

## Other campus operations

- **News & notices:** publish, edit or remove app news; updates appear in the students' noticeboard and notification refresh.
- **Calendar & holidays:** publish holidays, substitute weekdays or selected-student special classes; existing timetable/room overrides remain available.
- **Forms & responses:** create scoped faculty forms, share sign-in links, enforce existing live proof/location/QR rules, review evidence, export Excel, close/archive a form while retaining response history. Students' answer drafts are not reset by background list polling.
- **Placements:** create, update and archive app opportunities. Student lists omit archived items while application history is retained.
- **Issues & feedback:** review, reply, update status and archive resolved issues. Audit and sign-in history require the Audit permission.

Connected student forms, faculty exams and seating poll while visible and refresh on focus. Other workspace information follows the existing refresh setting and notification poll. Updates require connectivity; there is no claim of an instantaneous push socket for every screen. Missing university data stays unavailable rather than being invented.

## Database and deployment

Application users/password hashes stay in the existing protected User collection. Additional admin flow collections are `admin_accounts`, `admin_login_events`, `admin_messages`, `admin_deliveries`, `moderation_actions`, `event_staff_grants`, `exam_seating_releases`, and `exam_seating_entries`. Admin metadata and login history do not duplicate plaintext passwords or session tokens. Schemas/indexes initialize at startup; no destructive migration is needed.

Production requires configured Atlas access, persistent media, correct HTTPS origins/cookies, one private academic-service worker for its process-local university sessions, running scheduled delivery jobs, and a permitted mail provider. Use the existing production reverse proxy for multiple campus API replicas; retain shared Mongo rate limits and storage. Do not expose the academic-service port publicly. See docs/HOSTING.md, docs/GITHUB.md and docs/ANDROID.md for hosting, safe source upload and the later Android public-URL configuration.

The included browser recording uses fictional isolated accounts and captured test mail. Live AMS availability, real inbox delivery, Windows execution, college authorization, load capacity and signed Android publication require deployment checks with your own configuration.
