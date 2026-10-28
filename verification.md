# Verification — updated2.3.3, Android20304

Fresh integrated automated checks: **1,004 passed**, zero failing/skipped tests.

| Suite | Passed |
| --- | ---: |
| Frontend (`npm --prefix frontend test`) | 354 |
| Campus API (`npm --prefix services/campus test`) | 406 |
| Academic service (`python -m unittest discover -s tests`) | 228 |
| Android helpers (`npm --prefix android test`) | 16 |

Production Vite/PWA build passed. A genuine native Gradle release compile and SDK
signature, selected-keystore certificate, package/version/launchable/non-debug,
16KiB alignment and checksum verification passed. An independent SDK publisher
reverified the actual APK before creating the public release directory. No private
key or account/configuration data is included. See ANDROID-2.3-VERIFICATION.md.
Existing development-only test renderer/Java/Python warnings were not assertions.

## Same logo design and calmer launch

The existing cap, tassel, curved sides, calendar and centre design remain. Only
colours/finish changed: college maroon/navy, original Attendance blue accent,
satin silver and medium smooth paint reflections. The official web wordmark was
a palette reference, not a replacement design or added seal. All active logo
surfaces and native/PWA/static icons use the revised artwork. Older part-image
URLs are refreshed for cached clients, while new animation code shows one whole
image, never independently flipping/deforming the centre. Startup is bounded to
1.1seconds,180ms for reduced motion; disabled motion is preserved. The post-login
identity appears sooner while record sync continues.

## Actual source refresh and performance

The prior interval reread the whole saved workspace. The new owner-scoped
controller requests fresh AMS work only with authenticated current-source
capability and enabled/visible/online state. A120second source minimum, server
owner cooldown, inflight coalescing, finite TTL/capacity/concurrency and transient
backoff protect source admission. Source status never extends upstream lifetime
or exposes client cookies/credentials. Retry-After crosses both service layers.
CAPTCHA is retained where the university requires it; no password replay or
solver was added.

Only committed module changes trigger academic snapshot reads. Campus notices,
events/registrations/placements have their own bounded update loop. Session,
feed/people and social state are not periodically reloaded. Optimistic follow
counts and account-generation/abort/owner boundaries are preserved. Manual-only
creates no idle status/source work; manually queued jobs still receive progress
checks until completion. Stale cached capability cannot authorize live work.
Inactive/expired source asks for reconnection and retains last-success times.

## Review and fixes

A fresh independent review found two Important progress-monitoring races despite
green focused tests. Root reproduced each RED and fixed them before the full
suite: an older idle/status response could replace newer successful admission
and consume the only progress timer; and a transient status-read failure could
stop manual-only job monitoring. Admission revisions now reject older replies,
overlapping checks retain a follow-up timer, and an admitted job keeps bounded
progress retries. A third regression covers an older active reply arriving after
source409: it cannot revive an expired source or leave false syncing state.
The focused root fix run passed20tests and the full suites above passed. Review
findings are resolved; this does not claim every possible scheduling race is
proved absent.

## Browser evidence

**30 browser checks passed** using system Chromium through regular Playwright;
Browser plugin unavailable. Local production web/API and isolated academic DBs
used fictional users. Normal launch video was recorded without timeline jumps.

- Seven logo/account checks: one-image intact reveal, no distortion/glow filter,
  meaningful phone login, matching post-login mark then identity/Home, same2.3.3
  About version,320/390/1440 layouts, animation opt-out/session refresh and no
  runtime/framework exception.
- Ten public/settings checks: anonymous installation without private hydration,
  responsive sharing, real clipboard own-domain URL, actual pinned signed APK
  checksum, honest requested status, compatibility PNG paths, source labels,
  collapsed PWA alternative and phone notifications.
- Nine source-flow checks used controlled synthetic source transport with the
  real app/account backend. They verified fresh admission at interval, committed
  timetable change arriving in Home, no session/feed/people full reload, source
  request bounds, manual-only/focus pause, manual timeout recovery, source expiry
  and reconnect without app logout, and no offline source admissions. These are
  not evidence of a new authenticated university session or actual campus rows.
- Four Android checks simulated the browser-provided package/referrer and an
  existing20303 install. A transient metadata failure stayed quiet, retried on a
  later foreground after1minute, detected same-version higher20304, downloaded
  exact signed bytes via tappable dialog, and retained Later24h/login on reopen.
  This is JavaScript/browser evidence, not physical-phone installation proof.

Page identity, meaningful content, absent framework overlays, screenshots and
interactions were checked. No runtime exceptions. Expected console errors were
anonymous session401, deliberate transient503 and intentional offline failures.

## Practical limits

No fresh authenticated AMS data comparison, physical-phone acceptance/update,
production deployment, campus-scale load test, new Docker build or fresh
PostgreSQL compatibility run. Active upstream clients remain process-local:
TTL1800seconds/capacity100/concurrency3 and one academic worker. Actual source
availability/verification and supported pages govern freshness. Prior public
checks listed another domain signing certificate; use the original release key
for existing differently signed APKs and publish matching domain association.
Device reputation/security prompts are not suppressed. See the current guide.
