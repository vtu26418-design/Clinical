# veltech-ams-mini

Combined student, faculty and administrator workspace · **2.0.0**.

Start with [the Windows Docker setup and upgrade guide](docs/V2-UPGRADE.md). New installations use PostgreSQL through FerretDB. Existing configuration is preserved until you complete a verified migration.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1
```

Open **http://localhost:4100** after setup. The same login identifies the account role. No Ubuntu terminal is required.

- [Upgrade, migration, roles, events, placements and app updates](docs/V2-UPGRADE.md)
- [SMTP configuration](docs/EMAIL-SMTP.md)
- [Android signing and packaging](docs/ANDROID.md)
- [Verification and limitations](docs/VERIFICATION.md)

The source package excludes secrets, student data, database files and signing keys. A connected signed APK needs your deployment URL and signing key. PostgreSQL software is free; hosted disk and service limits still apply.

For the original Atlas setup only, choose `Setup.ps1 -Database Atlas`. Existing Atlas installations can continue using their original configuration.

Developed by VEL STUDENTS.
