# Verification — 2.3.2

Fresh integrated automated checks: **976 passed**, zero failing or skipped tests.

| Suite | Passed |
| --- | ---: |
| Frontend (`npm --prefix frontend test`) | 332 |
| Campus API (`npm --prefix services/campus test`) | 405 |
| Academic service (`python -m unittest discover -s tests`) | 223 |
| Android helpers (`npm --prefix android test`) | 16 |

The production Vite/PWA build passed. An early campus run found an old expected
hosted-package branch in the download test; its release expectation was updated
and the full405-test suite then passed. An intermediate frontend run under
simultaneous implementation/test load hit an existing offline-resource test's
bounded polling check; its isolated rerun and the final complete332-test run
passed without changing the production cache or weakening that assertion.
Existing React test-renderer and Python deprecation notices are development
warnings, not failed tests.

## Changes verified

- The same cap/ribbon/calendar logo design is recoloured navy, emerald and
  platinum. Five aligned transparent animation layers include an independent
  university emblem; both opening and post-login sequences use them. Launch is
  bounded at2.8seconds; reduced motion uses a short static image. New PWA/static
  icons and the actual APK derive from the same artwork.
- Public /#/install renders without private workspace hydration or sign-in.
  APK is primary; optional PWA installation is separately named and collapsed.
  Same-origin pinned APK attachments replace Blob downloads, and sharing uses
  the deployed app domain. The UI reports a request rather than claiming a file
  was saved or installed. Server hash/signature publication checks remain.
- A busy upstream503 retains an unused verification challenge for manual retry.
  Rejected verification is reset. Source reconnection has the same bounded
  source-login allowance as initial sign-in; no credentials are auto-retried.
- University/staff/device data labels remain distinct. Offline snapshots cannot
  claim active source sync. Partial refreshes are not green success, and
  previous records retained after unsupported/failed refreshes are marked.
- Existing verified returning app password sign-in, source identity binding,
  session persistence, social optimistic actions and own-seat privacy remain.

## Browser evidence

**34 browser checks passed** using system Chromium and regular Playwright;
Browser plugin was unavailable. Local production web/API and a separate
academic service ran with fictional preverified users and isolated test DBs.
No real university account or SMTP delivery was used.

The19-flow regression run verified mobile login, layered logo rendering,
password-only returning app sign-in, real producer-format12-hour class values,
IST current/next rooms, navigation swipe and its setting,320/390/1440 layouts,
horizontal suggestions, a single Follow write without full workspace refetch,
inline like/comment, same-origin actual signed APK bytes, safe update Later,
refresh persistence, offline own records, reviewed seating import and two-user
private-seat isolation, Home exam/seat reminders and Android-update deferral.
A5-check run verified real update-dialog taps/download/close, Events at three
widths, mobile More navigation and persisted animation opt-out.
A10-check run verified anonymous public installation without session/academic
reads, responsive install/share, real clipboard own-domain link, actual pinned
APK checksum, honest requested status, all five logo assets, three source types,
collapsed PWA alternative and the phone notification inbox.

Page identity, meaningful content, absent framework overlays, responsive
screenshots and real interactions were checked. There were no browser runtime
exceptions. Expected console network errors were anonymous session401, deliberate
offline network failures and denied whole-roster access. Early browser attempts
used outdated label selectors and one navigated before sign-in's route handoff;
the harness was corrected and the final full flows passed. Production identity
and privacy filters were not relaxed to make fixtures pass.

The launch/sign-in/installation preview video records the natural animation
rather than jumping its timeline. Android package/referrer/version evidence is
simulated in browser tests; this is not physical-device acceptance evidence.

## Android binary

A genuine Gradle release compile passed in31seconds from current local
production assets and the approved-origin config. SDK apksigner verified the
signature and selected-keystore certificate; aapt verified package/version,
launchable activity and non-debug identity; zipalign verified16KiB alignment.
A separate SDK publisher rechecked the actual APK before public metadata was
written. See ANDROID-2.3-VERIFICATION.md for exact hashes/bytes.

The normal network-gated build initially stopped on local DNS resolution for
the configured domain. The release was then compiled/signed with the normal
Gradle/SDK tools against the already-generated current local resources, retaining
all signature/package/alignment verification. No source network check was
removed or falsified, and local packaging does not establish live association.

Public read-only checks on28October2026 found the website reachable, release
metadata `available:false`, and a public domain certificate different from this
workspace's retained signing identity. V2.3.2-UPGRADE.md explains publishing and
using the original key for any differently signed installed APK. TLS/proxy
verification stayed enabled; no production files were changed.

## Independent review and limits

An independent fresh-context review found no material regression and separately
passed26focused frontend checks and3APK endpoint checks. Those overlap the full
suites and are not added to the976 total.

Not performed: a fresh authenticated AMS login/live record comparison, a real
phone installation or same-key update, production AWS deployment, campus-scale
load test, fresh Docker image build or fresh PostgreSQL-compatibility run.
Existing modules/configurations are retained; passing synthetic tests cannot
prove every university page or device behavior. Public HOV/AMS research found
no published separate Home API and a current official AMS verification form.
Mandatory source verification and Android/browser reputation prompts are not
bypassed or promised away. Private keys/configuration/accounts are excluded.
