# Android release: Windows, Linux and CI

The approved origin is **https://app.veltech-mini-ams.me/**. The release configuration is `android/config.release.json`: package **in.velstudents.veltechams**, version **2.2.0**, Android versionCode **20200**. The user confirmed there is no earlier APK, so this release establishes a new signing identity. Preserve that identity for every update.

Minimum Android version is 7.0/API 24: the pinned Browser Helper 2.7.4 requires API 24. This is a Google Bubblewrap Trusted Web Activity (TWA), using the deployed HTTPS app in a supported browser, normally Chrome. It does not bundle the website or store student credentials in native code. Website changes require deploying the web release. The launcher icon can be generated from the new local `frontend/public/icons/app-512.png` before that web release is deployed. Browser camera and notification permissions still require real phone testing.

There are two separate results: APK signature/identity/alignment verification, and live domain association. A signed APK is installable while association is pending; browser controls may remain visible until the matching Digital Asset Links statement is deployed and the browser verifies it. Neither a successful build nor a live JSON check proves that installation, AMS, camera or push works on a physical phone.

## Local prerequisites

Use Node >=22.12, JDK 17 or 21, Android SDK platform 36, Build-Tools 36.1.0 and platform-tools. Android Studio's SDK Manager installs them on Windows; official command-line tools also work on Linux/macOS. Set `JAVA_HOME` and `ANDROID_HOME` to the real installation directories. Review and accept the SDK licenses. The project pins Bubblewrap 1.27.0, Android Browser Helper 2.7.4, AGP 8.9.1 and Gradle 8.11.1. The wrapper JAR and Gradle distribution have pinned official checksums. These pinned tools provide repeatable build steps; byte-identical APK output is not promised.

```sh
npm --prefix android ci
npm --prefix android test
node scripts/android-prepare.mjs --config android/config.release.json --dry-run
node scripts/android-prepare.mjs --config android/config.release.json --local-icon frontend/public/icons/app-512.png
```

The generator checks public DNS, HTTPS, the manifest launch route, service worker and icon. It never disables TLS verification. `--local-icon` explicitly uses the release's local PNG for native icons while retaining the checked public deployment origin. Use it when the deployed website still has the preceding version's icon. Omitting it uses the live icon. Generated files are replaced on preparation; change source scripts/configuration instead of editing them by hand. `android/config.example.json` intentionally contains an invalid placeholder; `--config android/config.release.json` selects the real origin.

## Signing identity and backup

**Do not generate a replacement key for an update.** The release generated in this session uses a private 3072-bit RSA PKCS12 keystore outside the project at `/workspace/.campus-mobile-v22/android-private/velstudents-release.keystore`; alias `velstudents`. Its strong random password is separately stored in that same protected session directory as `keystore-password` (mode 0600, parent 0700). Neither file belongs in source, ZIPs, screenshots, GitHub artifacts, public release storage or logs. They are deliberately absent from the delivery archive.

Before this workspace expires, the project owner must transfer the keystore through their private authenticated workspace access into encrypted backup storage, and put the password in a private password manager. Maintain a second encrypted backup, restrict access and verify that `keytool -list` can read the restored key. Keep the password separately from the backup. This document does not contain the key or password. A public signed APK or fingerprint cannot recover a lost private key.

On your computer, restore this existing key under `android/private/velstudents-release.keystore`, or set `CAMPUS_ANDROID_KEY_DIRECTORY` to the external protected folder containing it. The config allows only a keystore filename, never arbitrary credential paths or passwords. Do not commit `config.local.json` if you use it for your own origin. Preserve existing deployment cookie/encryption/VAPID/academic-link keys during upgrades.

For a genuinely new independent app only, create its own identity once (the delivered app already has one):

```sh
keytool -genkeypair -storetype PKCS12 -keystore android/private/velstudents-release.keystore -alias velstudents -keyalg RSA -keysize 3072 -validity 10000
```

Answer the prompts; never put a password directly in a command argument or JSON file.

## Build on Windows PowerShell

```powershell
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
node .\scripts\android-build.mjs --config .\android\config.release.json --dry-run
node .\scripts\android-build.mjs --config .\android\config.release.json
```

The PowerShell helper prompts securely for the existing keystore and key passwords (the PKCS12 passwords are the same). If the reviewed `.ps1` is blocked, unblock only that file using `Unblock-File .\scripts\android-build.ps1`, subject to your organization policy. Windows scripts remain supported.

## Build on Linux/macOS

Set `ANDROID_HOME` and `JAVA_HOME` to your installations. Supply signing passwords only in the local process environment; the following Bash prompts hide input and clear the variables after building:

```bash
read -rsp 'Keystore password: ' CAMPUS_ANDROID_STORE_PASSWORD; echo
export CAMPUS_ANDROID_STORE_PASSWORD
export CAMPUS_ANDROID_KEY_PASSWORD="$CAMPUS_ANDROID_STORE_PASSWORD"
node scripts/android-build.mjs --config android/config.release.json
unset CAMPUS_ANDROID_STORE_PASSWORD CAMPUS_ANDROID_KEY_PASSWORD
```

`CAMPUS_ANDROID_KEY_DIRECTORY` selects the external key folder when needed. In a managed execution environment, use its configured HTTP(S) proxy and CA. Node 24 supports `NODE_USE_ENV_PROXY=1` with `NODE_EXTRA_CA_CERTS` pointing to the supplied certificate. Java/Gradle require their own proxy properties and a truststore extending the standard JDK roots with the supplied CA; retain TLS checks. Use a writable `ANDROID_USER_HOME` and `GRADLE_USER_HOME` in restricted workspaces. These session-specific files belong outside the delivery. Do not solve network errors by disabling TLS, changing the origin to HTTP or bypassing the proxy.

A successful build produces only these public distribution outputs:

- `android/out/veltech-ams-mini-release.apk`
- `android/out/veltech-ams-mini-release.apk.sha256`
- `android/out/signing-receipt.json`

The build runs Gradle `assembleRelease`, 16 KiB zip alignment, Android `apksigner` signing and verification, checks the APK signing certificate against the selected keystore, checks its package/version/launchable activity, rejects a debug APK, and verifies final alignment. Its receipt includes the independently computed APK checksum and separate `domainAssociation` result. Add `--require-domain-association` to require a matching live association; if association is pending, the valid local APK is retained and the command exits nonzero for that gate.

## Digital Asset Links

Generate the public certificate statement from the verified receipt:

```bash
node scripts/android-assetlinks.mjs --config android/config.release.json --fingerprint "FULL_COLON_SEPARATED_SHA256_CERTIFICATE_FINGERPRINT"
```

This writes `android/out/assetlinks.json` and an optional exact-route Nginx template. Deploy only the JSON, at **https://app.veltech-mini-ams.me/.well-known/assetlinks.json**, HTTP 200, `Content-Type: application/json`, no redirects, authentication or challenge. Copy it to `frontend/public/.well-known/assetlinks.json` before rebuilding the site; the campus server already has an exact public route. Alternatively use the supplied `android/compose.assetlinks.yaml` proxy overlay with its generated files. Do not replace or publish TLS private keys or Android keystores. The fingerprint is public metadata.

An APK built before the web upgrade still opens the current website at the approved origin. Deploying the 2.2 website and this statement is necessary to receive the 2.2 web UI and complete domain verification. Website upgrade and APK availability are separate deployment actions; no production upload is performed by these build scripts.

## Publish the APK to the existing app API

On a machine with the SDK, independently verify and prepare a **local** release directory:

```bash
node scripts/publish-android-release.mjs --apk=android/out/veltech-ams-mini-release.apk --receipt=android/out/signing-receipt.json --out=app-releases --notes="Mobile campus 2.2.0"
```

This rechecks the actual APK with Android's signature/identity/alignment tools rather than trusting receipt text, copies the checksum-named APK and atomically replaces `release.json`. Copy only this public release directory into persistent server media storage using your normal private deployment method. Set `CAMPUS_APK_DIRECTORY` to its **container-visible** path (for the existing media volume, `/app/media/app-releases`) and `CAMPUS_ANDROID_PACKAGE_ID=in.velstudents.veltechams`. Every campus replica must read the same release directory. Preserve old APKs until rollout is checked; clients with a changed checksum get a retry rather than the wrong binary. Source and Android keys remain separate.

The public `/api/campus/app-release` API returns available only for a valid published manifest with an intact APK. The public `/api/campus/app-release/apk?sha=...` endpoint serves it as an APK attachment with no-store and nosniff. Both endpoints intentionally work before sign-in and expose only distributable APK files and public release metadata, with no account or private academic information. Do not add an account-login gate to APK delivery. Academic and account APIs retain their existing authentication and authorization requirements. The Install & updates screen leads with this release, validates metadata and checksum before saving, shows downloading/error/saved states and leaves installation confirmation to Android. Browser web-app installation remains a separate secondary action. URL parameters alone never establish that the APK is installed.

## CI option

`.github/workflows/android-release.yml` is a manually dispatched Linux build, using the same scripts and pinned SDK versions. Configure a protected `android-release` GitHub environment with secrets `ANDROID_KEYSTORE_BASE64`, `ANDROID_STORE_PASSWORD`, `ANDROID_KEY_PASSWORD`, containing the **existing** identity. Base64 encodes the binary; it is not encryption. Add it privately through repository settings, never source. The workflow restores the keystore under the runner's temporary directory, uploads only the APK/checksum/public receipt/assetlinks, then removes signing material. It does not deploy to AWS or publish releases. The strict domain gate defaults to true; disabling it records association as pending. This workflow has not been dispatched from this workspace.

## Real device verification and updates

Install a supported browser on a test phone, download/open the APK and follow Android's install prompts; do not disable Play Protect. With an authorized USB device, `adb install -r android/out/veltech-ams-mini-release.apk` also works. Test launcher, login/logout, two-account isolation, saved sessions, navigation, AMS sync, QR/camera permission, browser notifications and real push against your configured deployment. Denied permissions must leave the rest usable. Android 12+ supports `adb shell pm verify-app-links --re-verify in.velstudents.veltechams` then `adb shell pm get-app-links in.velstudents.veltechams`. Browser verification can be asynchronous.

Keep the same package/signing key and increase `versionCode` on every APK update. Changing the origin requires a new APK and association at the new domain. An APK cannot silently install itself from a website; Android always controls confirmation. Phone installation and device-specific behavior remain user acceptance checks even after the build signature passes.
