# Android 2.2.0 build verification

Logo refresh built 27 October 2026 for https://app.veltech-mini-ams.me/. This is a genuine compiled and signed release APK, not a source archive or debug build.

| Check | Result |
| --- | --- |
| Gradle 8.11.1 assembleRelease | Passed with full Temurin JDK 21 and SDK 36 |
| Package | `in.velstudents.veltechams` |
| Version | `2.2.0` / `20201` |
| Minimum Android | 7.0/API 24 (required by pinned Browser Helper 2.7.4) |
| APK bytes | 1869870 |
| SHA-256 | `ae70e241f1b83b58f9b3efc1f595a1d4a5f82c612283877630e369b6fb0984b2` |
| APK signature | Android apksigner verifies v2 and v3; one signer |
| Selected keystore | APK certificate matches public certificate exported from selected private keystore |
| Release identity | aapt confirms expected package/version and launchable activity; no debuggable flag |
| Alignment | zipalign -c -P 16 passes |
| Native icon | Original project logo inside the college-style seal, from current local app-512.png |
| Local publish helper | Independently rechecked signature/identity/alignment; local directory only |
| Public release API metadata | Available true from the locally published intact APK; APK metadata/download are intentionally public before sign-in and contain no private account information |
| Public domain association | Pending manual deployment; Cloudflare403/error1010 prevented live association verification |
| Physical phone installation/camera/push | Not performed; user acceptance testing remains |

Public certificate SHA-256: `3B:44:DD:8A:C3:15:56:4A:27:A7:FA:2D:03:5C:3E:58:1A:FF:20:5A:7C:B6:E6:2C:E4:5E:28:3B:28:E4:C7:68`. Public Digital Asset Links JSON is in `frontend/public/.well-known/assetlinks.json` and `android/out/assetlinks.json`. Deploy the website and that statement before expecting the 2.2 web UI and verified immersive TWA. Until then the installable APK opens the currently live site and may show browser controls.

Public build outputs are `android/out/veltech-ams-mini-release.apk`, its `.sha256` file and `signing-receipt.json`. The source archive excludes generated build directories and all private signing material. See [ANDROID.md](ANDROID.md) for existing-key backup and future update instructions, and [AWS-CLOUDFLARE-MOBILE.md](AWS-CLOUDFLARE-MOBILE.md) for manual hosting upgrade checks.

Verification used the managed proxy and CA with TLS enabled. No AWS/DNS/production writes, real AMS access or SMTP sends were performed. CI is supplied but was not dispatched. Windows PowerShell remains supported in source; this successful compile/signature check was performed on Linux.
