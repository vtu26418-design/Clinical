# Build the Android APK on Windows

This delivery contains the Android packaging tools and source generator. **It does not contain a connected, tested APK yet:** your public deployment URL is intentionally left for you to add. Continue using the web app and the existing Windows/Docker Desktop/Atlas setup while preparing hosting. No Ubuntu commands or manual WSL setup are required for this guide.

The Android app is a **Trusted Web Activity (TWA)** built with pinned Google Bubblewrap tooling. A supported browser, normally current Chrome, renders your HTTPS site. Its origin, cookies, login, camera permission, service worker and web push remain the website's browser features. The app uses the existing logo at `frontend/public/icons/app-512.png`; the web app retains its “Developed by VELSTUDENTS” credit.

The wrapper does not embed student credentials, database keys, API secrets or a JavaScript/native bridge. It requests notification permission for browser notification delegation. Camera access remains a website permission handled by the browser. The fallback opens a browser Custom Tab. Actual login, QR scanning, camera capture and notification delivery still require testing on a phone against your deployment.

## 1. Install the Windows build tools

Install these from their official sites:

- [Node.js](https://nodejs.org/en/download): version 22.12 or newer, preferably a supported LTS release.
- [Eclipse Temurin JDK 21](https://adoptium.net/temurin/releases/?version=21&os=windows): choose the Windows x64 JDK. Set its installer option for `JAVA_HOME`. JDK 17 also works with this direct Gradle build.
- [Android Studio](https://developer.android.com/studio): use **More Actions → SDK Manager** on the welcome screen, or **Settings → Languages & Frameworks → Android SDK** in an open project. Install **Android SDK Platform 36**, **Android SDK Build-Tools 36.1.0**, **Android SDK Platform-Tools**, and **Android SDK Command-line Tools (latest)**. Enable **Show Package Details** to select the exact Build-Tools version. Accept the displayed SDK licenses after reviewing them.

Open a new PowerShell window in the extracted project directory, for example:

```powershell
Set-Location C:\work\veltech-ams-mini
node --version
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
& "$env:JAVA_HOME\bin\java.exe" -version
npm --prefix android ci
npm --prefix android test
```

If `JAVA_HOME` is empty, set it to the actual JDK installation directory, which contains `bin\java.exe`. To find a standard Temurin 21 installation:

```powershell
Get-ChildItem "$env:ProgramFiles\Eclipse Adoptium" -Directory -Filter "jdk-21*"
```

Copy the displayed full directory path into `$env:JAVA_HOME = "YOUR_ACTUAL_JDK_DIRECTORY"`, then repeat the Java version command. Use Java 17 or 21 for this pinned build. Do not point `JAVA_HOME` at `bin`.

If you prefer to install the SDK packages through PowerShell after installing Android Studio's command-line tools:

```powershell
& "$env:ANDROID_HOME\cmdline-tools\latest\bin\sdkmanager.bat" "--sdk_root=$env:ANDROID_HOME" "platform-tools" "platforms;android-36" "build-tools;36.1.0"
& "$env:ANDROID_HOME\cmdline-tools\latest\bin\sdkmanager.bat" --licenses
```

The build uses Bubblewrap core **1.27.0**, Android Browser Helper **2.7.4**, Android Gradle Plugin **8.9.1**, Gradle **8.11.1**, platform **36**, and Build-Tools **36.1.0**. `android/package-lock.json` fixes the npm dependency graph. The bundled official Gradle wrapper JAR and downloaded Gradle distribution are checked against pinned SHA-256 values. The scripts use the generated project's Gradle wrapper, so a global Gradle installation is unnecessary. This fixes tool versions; it does not promise byte-identical APKs across machines.

## 2. Put your URL in this exact file later

Deploy the complete frontend and its existing backend at one public HTTPS origin first. Follow [deployment.md](deployment.md) for hosting, TLS, Atlas, secure cookies, origins, mail and push configuration. A local Docker address or a frontend-only static page cannot replace that deployment. The URL must serve the app at the domain root, not under a subdirectory.

Then run these commands from the project directory:

```powershell
Copy-Item .\android\config.example.json .\android\config.local.json
notepad .\android\config.local.json
```

**Edit line 2 of `android/config.local.json`:** replace only `https://example.invalid` with your actual origin. For example, if your real site is at `https://campus.your-college.edu`, the line becomes:

```json
  "deploymentUrl": "https://campus.your-college.edu",
```

Use your actual hostname. Do not add `/#/home`, `/api`, a path, a port, a username or password. The generator adds `/#/home` automatically and reads the existing `/manifest.webmanifest`, `/icons/app-512.png` and `/sw.js` from that same origin. HTTP, IP addresses, localhost, private DNS answers and reserved example domains are refused for release.

The remaining fields in that file are non-secret release metadata:

| Field | What to change |
| --- | --- |
| `packageId` | Default: `in.velstudents.veltechams`. Choose your own unique reverse-domain identifier before the first release, then preserve it for updates. |
| `appName`, `launcherName` | Full app name and launcher label. The defaults match this project. |
| `versionName`, `versionCode` | Default: `1.8.0` and `18`. Increase `versionCode` for every later APK update. |
| `signingKeyFile`, `signingKeyAlias` | Default: `velstudents-release.keystore` and `velstudents`. The file is always stored inside `android/private/`. Use the same identity for updates. |

`config.local.json`, signing keys, generated source, npm packages and APK output are ignored by `android/.gitignore`. Keep passwords out of this JSON file. If it already exists during an upgrade, edit it; do not overwrite your release metadata with the example.

Check the local config, then generate the Android source:

```powershell
node .\scripts\android-prepare.mjs --dry-run
node .\scripts\android-prepare.mjs
```

The dry run checks local values only. The second command checks public DNS and the live HTTPS app assets, then creates `android/generated/`. It replaces this generated directory on every run. Preserve changes in `config.local.json` and the scripts instead of hand-editing generated files. A missing or placeholder URL stops preparation before creating an app.

## 3. Create and protect your release signing key

Create the key once, on your own Windows computer:

```powershell
New-Item -ItemType Directory -Force .\android\private | Out-Null
& "$env:JAVA_HOME\bin\keytool.exe" -genkeypair -v -storetype PKCS12 -keystore .\android\private\velstudents-release.keystore -alias velstudents -keyalg RSA -keysize 3072 -validity 10000
```

Answer the keytool prompts with your own publisher identity and a strong password. The PKCS12 key uses the same password as the keystore. If you changed the filename or alias in the config, use those exact values in these keytool commands too. Do not regenerate the key when preparing an update.

Back up the keystore and its password separately to protected storage. Restrict access with Windows file permissions and disk encryption. Losing the signing identity can prevent updates to installed APKs. **Never commit, email, upload with the source ZIP, or publish `android/private/` or the password.** `.gitignore` protects ordinary Git operations, not arbitrary ZIP or cloud-sync tools; exclude this directory explicitly from shared archives. Only the signed APK and its public checksum are distribution files.

Display the certificate's public SHA-256 fingerprint:

```powershell
& "$env:JAVA_HOME\bin\keytool.exe" -list -v -keystore .\android\private\velstudents-release.keystore -alias velstudents
```

Copy the complete `SHA256` fingerprint: 32 hexadecimal pairs separated by colons. A certificate fingerprint is public metadata. It is not your password.

## 4. Connect your HTTPS domain to the signed app

Generate the Digital Asset Links file with the fingerprint you copied:

```powershell
node .\scripts\android-assetlinks.mjs --fingerprint "PASTE_THE_FULL_COLON_SEPARATED_SHA256_FINGERPRINT_HERE"
```

This creates `android/out/assetlinks.json` and an Android-specific production Nginx template at `android/out/nginx.conf.template`. Your domain must serve the JSON at exactly:

```text
https://YOUR_REAL_HOSTNAME/.well-known/assetlinks.json
```

It must return **HTTP 200**, `Content-Type: application/json`, no login and no redirect. Its package ID must match `config.local.json`, and its SHA-256 fingerprint must match the certificate signing the installed app. Do not replace it with a debug key fingerprint.

The included campus server has a narrow public JSON route for this file. Copy the generated public statement into the web source, then rebuild your deployed Docker image so the file reaches every campus container:

```powershell
New-Item -ItemType Directory -Force .\frontend\public\.well-known | Out-Null
Copy-Item .\android\out\assetlinks.json .\frontend\public\.well-known\assetlinks.json
docker compose --env-file .env.production -f compose.production.yaml up -d --build --scale campus=3
```

Use those production commands after completing `deployment.md`, on the Docker host with your deployment configuration present. The file contains only public certificate fingerprints and the package ID; it may be committed with the web source. The keystore and passwords must stay private. For a different hosting provider, publish the same JSON through its exact public route.

Alternatively, the supplied Android proxy override serves this one public file directly through the production Nginx proxy without rebuilding the web image:

```powershell
docker compose --env-file .env.production -f compose.production.yaml -f android/compose.assetlinks.yaml config --quiet
docker compose --env-file .env.production -f compose.production.yaml -f android/compose.assetlinks.yaml up -d proxy
```

Use this optional override with the production stack; do not merge it with the localhost `compose.yaml`. Run its commands on the Docker host with this project's generated `android/out/` files present. Keep `-f android/compose.assetlinks.yaml` in future production commands if you choose this method. When the base Nginx template changes, rerun the Asset Links generator before applying the override.

The server's explicit route is required: generic Express static dotfile handling and a SPA fallback can otherwise return the app's HTML instead of the required JSON. Verify the actual public response after deploying.

Check it from PowerShell, substituting the same real origin you configured:

```powershell
$origin = (Get-Content .\android\config.local.json -Raw | ConvertFrom-Json).deploymentUrl
$response = Invoke-WebRequest "$origin/.well-known/assetlinks.json" -MaximumRedirection 0 -UseBasicParsing
$response.StatusCode
$response.Headers['Content-Type']
$response.Content | ConvertFrom-Json
```

## 5. Build and verify the signed APK

Run from the project directory:

```powershell
node .\scripts\android-build.mjs --dry-run
node .\scripts\android-build.mjs
```

The first command prints requirements and paths without building. The second requires Windows, the live HTTPS PWA, the generated project, the private release key and a valid deployed Digital Asset Links statement. It runs the pinned Gradle wrapper, aligns the APK, prompts for the keystore and key passwords, signs it with Android's `apksigner`, and verifies the signature and alignment. Passwords are passed through temporary child-process environment variables and cleared on exit; they are not stored in a file or placed in command-line arguments. Enter the same password at both prompts for the PKCS12 key created above.

The command only publishes its local output after verifying that the APK's signing certificate appears in your live Digital Asset Links file:

```text
android/out/veltech-ams-mini-release.apk
android/out/veltech-ams-mini-release.apk.sha256
android/out/signing-receipt.json
```

The `.sha256` file lets you compare the downloaded APK with your build. This command builds a signed APK for controlled distribution; it does not publish to Google Play. Google Play App Signing uses an app-signing certificate that may differ from your upload key. If you later publish through Play, follow [Play App Signing](https://developer.android.com/studio/publish/app-signing) and add the actual Play app-signing certificate fingerprint to the domain statement before testing that release.

If Windows blocks a downloaded `.ps1`, first review the supplied script, then unblock only that file with `Unblock-File .\scripts\android-build.ps1`. Follow any policy enforced by your organization. If the SDK, Java, TLS or Gradle checks fail, correct that prerequisite and rerun the command; keep certificate verification enabled.

## 6. Test on a real Android phone before sharing

Install a current supported browser such as Chrome. For USB testing, enable Developer options and USB debugging on your own phone, connect it, and authorize that computer:

```powershell
& "$env:ANDROID_HOME\platform-tools\adb.exe" devices
& "$env:ANDROID_HOME\platform-tools\adb.exe" install -r .\android\out\veltech-ams-mini-release.apk
```

Then open the app from the launcher. Check sign-in, the correct student's data, logout, admission-year filters, AMS refresh, QR camera permission, notification permission and a real push delivered by your configured backend. Check a second student account and confirm that sessions and data remain isolated. Denying a permission should leave the rest of the app usable. Background push depends on the browser, Android permission, backend subscription/delivery and device power settings; the wrapper alone cannot guarantee delivery.

Android 12 or newer can report app-link verification after installation:

```powershell
$packageId = (Get-Content .\android\config.local.json -Raw | ConvertFrom-Json).packageId
& "$env:ANDROID_HOME\platform-tools\adb.exe" shell pm verify-app-links --re-verify $packageId
& "$env:ANDROID_HOME\platform-tools\adb.exe" shell pm get-app-links $packageId
```

Allow time for the device's asynchronous verification. If a browser address bar remains visible, check the live domain statement, signing certificate, package ID, browser support and the phone's network access. Do not disable domain verification to hide that symptom.

For a phone-only sideload, Android may ask whether to allow installation from the app opening the APK. Distribute through a trusted channel and let recipients review that choice. Signing and HTTPS improve provenance; they do not guarantee a malware-free app, remove Play Protect warnings or bypass Android's security checks. Do not ask recipients to disable Play Protect. Broader distribution should use an appropriate reviewed store release.

## Updates and what has been checked

Keep the same package ID, keystore and key alias for updates. Increase `versionCode`, update `versionName`, regenerate source and build again. A domain change requires editing `deploymentUrl` on line 2, deploying Digital Asset Links at the new domain, generating a new APK and retesting. Website changes at the same origin normally arrive through the existing web deployment and service-worker update flow.

The delivery checks cover config rejection, public/private address handling, hash-route launch, certificate metadata, complete Bubblewrap source/icon generation, Gradle checksums, the production JSON route and both script dry runs. Tests use local fixtures; they do not establish that your future deployment or a phone works.

**An actual Gradle compile, APK installation, production TLS/domain verification, real AMS sign-in, camera capture, and push delivery have not been run for this unconfigured delivery.** The deployment URL and your own private signing key are still required. The build scripts stop at those prerequisites instead of creating a placeholder connected APK.

Official references: [Trusted Web Activities](https://developer.chrome.com/docs/android/trusted-web-activity/), [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap/tree/main/packages/cli), [Digital Asset Links](https://developers.google.com/digital-asset-links/v1/getting-started), [Android app signing](https://developer.android.com/studio/publish/app-signing), and [Gradle wrapper verification](https://docs.gradle.org/8.11.1/userguide/gradle_wrapper.html#sec:verification).
