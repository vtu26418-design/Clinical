# Verification · veltech-ams-mini 2.0.0

Completed in the cloud workspace with synthetic accounts and isolated databases.
No student's university credentials or live academic records are included in this
source package, screenshots or preview.

| Area | Result |
| --- | --- |
| Frontend behavior/calculation/export checks | 192 passed |
| Campus API, access controls, sessions, events, applications, schedules and release endpoint | 337 passed against MongoDB |
| Python academic/parser/isolation checks | 189 passed |
| Android configuration/generator checks | 11 passed |
| Total final automated checks | 729 passed |
| PostgreSQL/FerretDB compatibility | 336 campus API checks passed; 189 Python checks passed with PostgreSQL-routed real database calls |
| Final academic renewal, directory, schedule and APK endpoint checks on PostgreSQL | 16 passed |
| Production Docker builds | Both campus and academic images built successfully from the supplied Dockerfiles |
| Connected production image smoke checks | 7 passed, using an isolated MongoDB database |
| Connected browser workflow and responsive checks | 24 passed with PostgreSQL-backed campus and academic services; no page errors |
| Browser sizes | 1440 px, 390 px and 320 px, with no document width overflow in checked screens |
| Storage migration | IDs, dates, arrays, indexes and canonical hashes verified; changed destination detected; populated destination rejected |
| Configuration safety | Fresh PostgreSQL config created; repeat setup preserved existing configuration; local/production overlays valid; no database host ports |

The final native API run includes the additional PostgreSQL production-validator
case and all-account sign-in activity recording added after the broad PostgreSQL
compatibility run. The final Docker smoke also checks that activity recording.

The browser workflow exercised separate account sections, official student
records, a full-page free event publication with linked community post, student
placement application and staff shortlist, review notification, schedule
publication, home reminders, event expiry settings, refreshed sign-in, unavailable
APK handling and dark directory navigation. Screenshots use fictional student
identities. Source-unavailable states are intentional where fixtures contain no
university data.

The private bridge can renew managed or durably verified AMS workspace links
without rebinding a student by email. Expired/sealed-token failures, foreign owner
claims, insufficient grants, stale renewal races and unverified legacy links have
regression coverage. New event expiry checks operate on listings and registration
without deleting ticket or payment history.

Limits of this verification:

- No fresh authenticated AMS session was inspected for this update. Live academic
  availability depends on AMS, the student's legitimate verification and its
  current page layouts. Prior cached/source parsing behavior is retained; missing
  records are not invented. University CAPTCHA and outages cannot be bypassed.
- No real SMTP campaign or payment was sent. Configure your provider and test
  delivery/checkout before student launch. An SMTP acceptance does not prove inbox
  delivery.
- The Docker images and configuration were tested on Linux. Windows PowerShell
  setup was reviewed, but a Windows host was not available to execute it.
- Android project generation and update endpoint behavior were tested. A signed
  APK was not built/installed on a physical phone: public HTTPS URL, operator
  signing key, domain association and device testing are still required. A direct
  download cannot silently install an APK or bypass Android confirmation.
- No college-wide concurrency/load result is claimed. The Docker health smoke is
  a local functional check. Measure your actual deployment, source rate limits,
  shared media, backup restoration and capacity before admitting large traffic.
- PostgreSQL is stored through the DocumentDB/FerretDB compatibility path. It is
  not a conversion to a native relational schema or a plain hosted PostgreSQL
  connection. Hosted free plans still impose storage and service limits.

See [setup and upgrade instructions](V2-UPGRADE.md) for configuration, verified
migration, rollback, deployment and signed APK publishing.
