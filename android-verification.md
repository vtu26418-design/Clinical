# Android release verification — 2.3.1

- Package: `in.velstudents.veltechams`
- Version: `2.3.1` / code`20301`
- APK bytes: `2590766`
- APK SHA-256: `d8a94e6cc56846599c9ea7a11f1c08c7f73e1dbe88b0beb88b03b4b060d828ed`
- Certificate SHA-256: `3B:44:DD:8A:C3:15:56:4A:27:A7:FA:2D:03:5C:3E:58:1A:FF:20:5A:7C:B6:E6:2C:E4:5E:28:3B:28:E4:C7:68`

Actual Gradle release compilation succeeded; v2/v3 signature, selected-keystore
certificate match, package/version, non-debug flags, alignment and checksum were
verified. A separate publisher independently rechecked the actual APK before
writing the public release directory. This certificate matches the earlier
locally prepared2.2.0 APK; the inaccessible user-linked Actions artifact was not
verified. No private keys are included in any public delivery.

Deploy the public release directory to your AWS server and serve it through
`https://app.veltech-mini-ams.me/api/campus/app-release/latest.apk`.
Settings uses same-domain checksum-pinned downloads. This release does not
publish a standalone APK on GitHub. Domain association remains pending public
Asset Links verification and physical-phone testing; neither was claimed here.
