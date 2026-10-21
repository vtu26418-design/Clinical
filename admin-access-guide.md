# Manage accounts and limited administrators

Sign in on the shared login page. The existing administrator created by Setup is an **owner administrator** and retains the original college-wide administration permissions. No database reset or new owner password is required for an upgrade.

## Create a staff or administrator account

1. Open **Management → Roles & accounts → Create account**.
2. Enter the name, college email, username and initial application password. Usernames use 3–30 lowercase letters, numbers, underscores or dots. Passwords require at least 12 characters and at most 72 UTF-8 bytes.
3. Choose **Faculty** and assign its department, or choose **Limited administrator**.
4. For a limited administrator, select only the required permissions, then save. New administrators have no permissions unless explicitly selected.
5. Give the initial credentials to the staff member through your institution's approved private process. They use the same login page as everyone else. Their first assigned workspace opens automatically.

## Permission matrix

| Permission | Allows |
| --- | --- |
| Events and check-in | Event creation/updates, participants, analytics and scoped check-in |
| Student and faculty accounts | Provision/manage ordinary app accounts; excludes administrator escalation |
| Create and manage limited admins | Create explicitly limited administrators within the grantor's own permissions |
| Placements | Manage campus and off-campus opportunities |
| College notices | Publish, edit and delete app notices |
| Community reports | Review and resolve community reports |
| Faculty forms and evidence | Author/manage official app forms and access submitted evidence |
| App issues and feedback | Review, reply, update status and archive app issues |
| Calendar and room overrides | Publish app calendar policies and timetable room overrides |
| Faculty examinations | Manage app-published examination schedules |
| View academic workspaces | Read supported student-workspace profiles, courses, attendance and timetable data |
| Edit app academic records | Manage the app's academic records; also permits reading those workspaces |
| Batch percentage rules | Confirm and manage exact batch/programme conversion rules |
| Audit history | View management/academic audit history and SMS delivery logs |

These administrator permissions cover the selected app modules across the college. Department/club-specific event duties should use the existing department coordinator or club organizer roles instead. Faculty forms remain restricted to assigned department/club scopes.

## Change or revoke access

Use **Assign role** to change a limited administrator's permissions. Changed roles/permissions revoke that account's existing sessions. Use **Deactivate** to remove access and close sessions while retaining records, tickets and audit history; the API's account deletion action uses the same deactivation behavior. Reactivate only when access is required again.

Owners are protected against demotion/deactivation through these controls. A limited administrator cannot change its own permissions, manage owners/other administrators outside its own created hierarchy, or grant a permission it does not hold. Giving administrator-management permission never creates another unrestricted owner. Administrator requests are checked on the server; hidden buttons are not the authorization boundary.

An account-management-only administrator cannot reset a linked student's password to gain academic access. Linked account password changes additionally require academic write permission. Official profile fields stay separate from social edits.

## University data and app operations

AMS remains the university's source of record. Academic read permission is required to access the protected academic proxy; read-only accounts have disabled editing controls and server-enforced write denial. Editing app academic workspaces, calendars or room overrides does **not** submit changes to the university AMS database. Unsupported fees/documents/results remain unavailable until the source returns supported records.

Source passwords, sealed academic tokens and campus encryption keys are not exposed to administrators. Student document downloads retain their existing owner checks. The college should grant academic and form-evidence permissions only to authorized staff. Role changes, account changes, notices, academic changes and support actions are audited.

## Issues and notices

Use **Management → App issues** to review feedback, save a response/status or archive a closed issue. Archiving removes it from the staff inbox; its submitter retains the closed history. Use **Noticeboard** to publish, edit or delete college announcements. These controls require their corresponding assigned permissions.
