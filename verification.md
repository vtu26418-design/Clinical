# Verification — 2.3.3 sky-blue logo update

This patch keeps the prior project behavior and changes logo assets, restrained
animation lighting, release identifiers and their download-package references.

Fresh automated suites: **753 passed**, zero failing/skipped tests.

| Suite | Passed |
| --- | ---: |
| Frontend (`npm --prefix frontend test`) | 332 |
| Campus (`npm --prefix services/campus test`) | 405 |
| Android helpers (`npm --prefix android test`) | 16 |

The academic Python implementation is unchanged; its223-test run and broader
2.3.2 verification are historical evidence in VERIFICATION-V2.3.2.md, not added
to this patch's fresh total. No database/authentication behavior was changed.
Production Vite/PWA build passed. Genuine Gradle/SDK Android release compile,
signing, selected-key certificate, package/version/launchable/non-debug identity,
16KiB alignment and checksum checks passed. The independent SDK publisher
reverified the APK. Domain association is pending; no physical-phone installation
or production upload was performed.

## Logo coverage

The existing hybrid cap, sides, calendar and official centre-emblem design remains.
The palette is the user's original Attendance sky blue #0EA5E9, softer #7DD3FC and
#BAE6FD tints, and satin silver/slate #F1F5F9. Original evidence is in
Unieve-Attandance-AI/frontend/src/pages/Login.jsx and Timetable.jsx; UniEven also
uses blue controls and #F1F5F9/#F8FAFC surfaces. No outer orange, purple or green.
Centre-emblem identifying maroon/navy/white details remain intact.

The smooth low-glare paint edit replaces strong white specular streaks. No glow
halo, bloom or animated brightness pulse is added. All five transparent aligned
parts and static/favicon/PWA icons derive from the same edited master. Cap/side
movement and independent centre reveal remain in both launch sequences, with
reduced-motion/disabled-animation paths. Android launcher and splash resources
were rebuilt using the new current icon. Preserved original artwork is an unused
source reference, not an active displayed logo.

## Browser checks

**17 checks passed** in real Chromium through regular Playwright, at320/390/1440
widths. Browser plugin was unavailable. Local production frontend/API and an
isolated academic service used fictional users, not real university credentials.

Seven logo checks verify loaded five-part assembly; independently visible emblem
with CSS filter none; meaningful phone login and bounded launch; matching
post-login artwork; shared About/shell assets and correct release; responsive
Home; persisted animation opt-out/session; and no runtime/framework exceptions.
The preview records natural animation, without timeline jumping.
Ten public/settings checks verify anonymous /#/install without account/academic
hydration, responsive guide/sharing controls, actual own-domain clipboard link,
real same-origin pinned APK download and matching checksum, honest requested
status, all five PNG assets, clear university/staff/device labels, collapsed PWA
alternative and responsive notification inbox. Expected anonymous session401 is
not a runtime failure.

## Limits

No fresh authenticated AMS comparison, physical Android acceptance, live source
CAPTCHA-free guarantee, production AWS deployment, campus-scale load test,
new Docker build or fresh PostgreSQL compatibility run. Prior read-only domain
checks found no published APK and a different certificate from the retained
workspace key. Follow V2.3.3-UPGRADE.md before updating existing APK installs.
Android/browser reputation prompts remain controlled by the device.
