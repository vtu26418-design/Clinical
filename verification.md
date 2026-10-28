# Verification — 2.3.1

Fresh automated checks: **960 passed**, zero failing or skipped tests.

| Suite | Passed |
| --- | ---: |
| Frontend (`npm --prefix frontend test`) | 317 |
| Campus API (`npm --prefix services/campus test`) | 404 |
| Academic service (`python -m unittest discover -s tests`) | 223 |
| Android helpers (`npm --prefix android test`) | 16 |

The production Vite/PWA build passed. The initial campus run exposed a stale
expected download branch in a test; the expectation was corrected to this
release and the full404-test suite then passed. Node test-renderer and Python
UTC deprecation notices remain development warnings; they did not fail tests.

## Corrected behaviours

- Verified portal-only students receive a bcrypt application password verifier
  only after an exact upstream identity match. Subsequent VTU/mailbox sign-in
  uses this verifier without starting AMS verification. Original identity and
  sync timestamps remain unchanged. Explicit upstream challenge submissions stay
  browser-bound. Disabled/malformed bindings and alternate login endpoints fail
  closed. Long passwords are never truncated, and verified recovery changes the
  app password without changing the university binding. Focused40-case auth
  integration and independent review passed. No CAPTCHA solver or bypass exists;
  a new AMS data session still needs official verification if AMS requires it.

- Source AMS timetable produces explicit AM/PM strings; class/calendar code now
  normalizes them instead of discarding every live period. Noon/midnight,
  half-open end times, unknown intervals and staff calendar rules are tested.
- Follow no longer invokes the whole workspace refresh. Per-member revisions
  fence delayed old reads, pending writes, rollback and account switches. Fresh
  later reads remain authoritative. Private content cannot reappear from an old
  relationship result. Inline suggestions scroll horizontally.
- PWA asset refresh preserves active/waiting precaches, sessions and downloads;
  it uses the service-worker lifecycle. Later persists across offline/online
  launches and small device-clock rollback. Android foreground checks coalesce
  and wait15minutes between checks; per-build Later lasts24hours.
- Seating imports validate course code and exact VTU, or one eligible verified
  official name. Missing/ambiguous directory data fails closed. Source row issues
  remain visible. Preview CSV exports round-trip through the actual Python
  importer. Original rosters remain staff-only; each student receives only an own
  published assignment. CSV/XLSX/text PDF supported; legacy XLS needs conversion.
- Mobile page swipes exclude media/controls/horizontal scroll/native edges and
  can be disabled. Transparent3D hybrid artwork and a locally served Inter font
  replace the surrounding circular seal treatment.

## Browser evidence

Regular Playwright with system Chromium was used because no Browser plugin was
available. The final integrated run passed19 checks at320/390/1440 widths with
zero page/runtime exceptions: animated launch/login; password-only returning portal account; real producer-shaped12-hour
class/current+next display; phone tab swipe and preference; responsive Home;
horizontal suggestions; single-request Follow preserving scroll/feed; inline
like/comment; signed APK download and stable local-domain endpoint checksums;
optional refresh Later; login/view preservation across reload; saved offline
workspace; CSV seating review/publication; two-owner seat isolation; Home own
exam/seat; simulated Android update notice and persistent Later on reopen.

The Android launch referrer/version was simulated for browser UI checks; it is
not evidence of a physical Android installation. Anonymous-session HTTP401 and
intentional offline network errors were expected during these flows. Earlier
browser attempts identified the Later clock rollback and inherited modal pointer
handling; both were fixed before final verification. A supplementary five-check mobile modal/events/navigation run is recorded with
the delivery evidence. The simulated Android update dialog was exercised with a
real APK download and its checksum, including actual clickable modal controls.

## Signed release and deployment boundary

A genuine Gradle release build passed. Package `in.velstudents.veltechams`,
version2.3.1/build20301, minimumAndroid7/API24, with the previous local release
certificate retained. The SDK publisher independently rechecked signature,
package/version, non-debug identity, alignment and APK checksum. The actual
same-origin metadata, pinned APK and stable latest APK endpoint were read using
synthetic local services. No external APK redirect is accepted.

The source archive and public deployment release folder contain no signing keys,
passwords, real student database or account sessions. Private signing backups are
retained separately for the owner. See ANDROID-2.3-VERIFICATION.md and
V2.3-UPGRADE.md for the exact checksum and server deployment.

No production AWS/Cloudflare deployment, new live AMS login, physical Android
acceptance, campus-scale load test, fresh PostgreSQL compatibility run or fresh
Docker image build was performed. The existing Docker configuration is included;
native service tests and real local API/browser flows passed. Source availability
still depends on university services and supported layouts. The linked GitHub
Actions APK was inaccessible, so its signing compatibility remains unknown.
Domain association must be verified after deploying Asset Links and the included
public release files. A TWA otherwise may show browser controls. Android owns
installer/Play Protect prompts. Production rollout is manual.
