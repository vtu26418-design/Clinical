# Verification — 2.2.0 logo refresh

The displayed application version remains2.2.0. Android's internal build counter is20201, allowing the same signing identity to update20200.

The user's final instruction was to retain their own logo and improve/hybridize it. The original project cap, curved sides, calendar and star were retained rather than replaced with an AI crest. A college-style circular frame and restrained indigo/emerald/silver accents surround the original artwork. The source original remains `frontend/public/assets/project-original-logo.png`; editable frame/composition sources are in `frontend/branding-source`.

Launch and post-login graphics use four independent layers. Sides rise from40ms to1390ms. The cap drops from above the viewport and settles by1620ms. Centre/calendar and seal details appear from1700ms to2300ms. The app opens at2600ms. Reduced motion uses a static mark and a short180ms delay; disabling opening animation bypasses it. The existing same-tab no-replay and secure login/sync flow remain.

Fresh checks:292 frontend tests,16 Android helper tests and the1 hosted-download route test passed. The production Vite/PWA build passed. Six real Chromium/Playwright checks passed at320/390/1440, including computed CSS transforms/opacity at0/800/1650/2350ms, release to login, no route/refresh replay, reduced motion, and actual fictional-account post-login assembly before identity/Home. No page errors were recorded. Browser plugin was unavailable. Stage screenshots and recorded preview are included with delivery.

A new real signed APK was compiled with the updated local icons, version2.2.0/code20201, package `in.velstudents.veltechams`. The publisher independently verified v2/v3 signature, package/version, absence of debug flag, alignment and checksum. Its certificate matches the preceding2.2.0 release; no private key was replaced. See ANDROID-2.2-VERIFICATION.md for the current checksum. Private signing files remain excluded from all public packages.

This was a branding-only update. The preceding919-test full feature verification and production Docker/browser coverage are preserved in VERIFICATION-V2.2-INITIAL.md; backend/academic suites and a new Docker image build were not repeated for this visual change. No fresh real AMS login, production AWS write, Cloudflare change, physical Android test or campus-scale load test occurred. Domain association remains pending manual verification as described in AWS-CLOUDFLARE-MOBILE.md. Use the same private signing backup and deployment configuration.
