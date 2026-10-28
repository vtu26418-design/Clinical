# Android release verification — 2.3.2

- Package: `in.velstudents.veltechams`
- Version: `2.3.2` / code `20302`
- APK bytes: `2562094`
- APK SHA-256: `922ec17ef29ec220c5c002f60bc710f1fbd5d7ba101dcf03df758b488f788678`
- Certificate SHA-256: `3B:44:DD:8A:C3:15:56:4A:27:A7:FA:2D:03:5C:3E:58:1A:FF:20:5A:7C:B6:E6:2C:E4:5E:28:3B:28:E4:C7:68`

A genuine Gradle release compilation succeeded in31seconds from current local
production assets and the approved-origin Android config. SDK signature,
selected-keystore certificate, package/version/launchable/non-debug identity,
16KiB alignment and checksum verification passed. An independent publisher
rechecked the actual APK before writing the public release directory. Native
launcher/splash resources derive from the current recoloured transparent logo.

This certificate matches previous locally prepared releases. The currently
published domain statement lists a different certificate (`0F:F3:49:D9:…:54:78`),
and its release API reported available:false on28October2026. This does not prove
the certificate of the user's previously installed APK. The actual Actions APK
was not accessible. Use the original signing key to update any differently
signed installed APK; see V2.3.2-UPGRADE.md. Do not overwrite/discard either
private signing identity. No private material is in public artifacts.

The normal network-gated build stopped at local DNS lookup. Local packaging
kept Gradle/SDK signature/identity/alignment checks, with domain association
explicitly pending. No live deployment verification was invented. Real phone
installation/update, Play Protect acceptance and Android/browser prompts remain
untested and cannot be controlled by the website.

Deploy the intended same-key public release directory to AWS. Students use
https://app.veltech-mini-ams.me/#/install or
https://app.veltech-mini-ams.me/api/campus/app-release/latest.apk .
This delivery has no standalone APK on the GitHub branch; only the owner ZIP
contains the public deployment directory. Domain downloads never redirect there.
