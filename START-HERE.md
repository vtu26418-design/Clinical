# Start here — Clinical Trial Intelligence v5.2.0.3

**Windows, no Docker required.** Use the complete release ZIP; extract it before running a launcher.

1. Install [Python 3.12 for Windows](https://www.python.org/downloads/windows/). Include the Python launcher (`py`). Install [PostgreSQL for Windows](https://www.postgresql.org/download/windows/); choose and remember the `postgres` administrator password and port (normally 5432). Ensure its Windows service is running.
2. Extract All into a writable folder, for example `C:\CTI`, and open the folder containing `SETUP_WINDOWS.bat`.
3. Double-click `SETUP_WINDOWS.bat`. Let dependency installation finish. It creates `.venv` and a private `.env`; Node is unnecessary with the included prebuilt interface.
4. Double-click `CONNECT_DATABASE_WINDOWS.bat`. For a fresh installation accept host `127.0.0.1`, port `5432`, application role/database `cti` and administrator/maintenance database `postgres`. Press Enter at the application-password prompt to retain the generated private password. Enter the administrator password you chose during PostgreSQL installation at the hidden prompt.
5. Wait for **Application database login verified.** The helper creates missing application role/database objects and preserves existing data and role passwords.
6. Double-click `START_WINDOWS.bat`. Leave that terminal open; visit http://localhost:8000 when startup finishes.
7. Open your own local `.env` in a text editor, copy the `SETUP_TOKEN` value and create the first owner with a unique password of at least 12 characters. Keep `.env` private.
8. Create/open a project. More tools → Data Manager → load the **800-record starter cohort**. Select that dataset instead of the five software fixtures.
9. Open Overview, then Prediction Studio. Use an approved bundled model to predict; training is optional. More tools → Experiments is the owner-only training workflow. Review held-out metrics, approve and explicitly activate a candidate only when appropriate.

On later visits, start the PostgreSQL service and run `START_WINDOWS.bat`; setup and database creation do not need repeating. `CONNECT_DATABASE_WINDOWS.bat --check` performs a read-only connection check. Use `--configure` to deliberately select different connection settings.

Assistant replies need a private provider key and an API model ID your provider account supports. Put those values in the server `.env`, restart, and enable the project assistant. Never put keys in the browser or share them in a ZIP.

[Read the full guide](docs/v5.2.0.3-full-guide.md) or open [the PDF guide](docs/Clinical-Trial-Intelligence-v5.2.0.3-Full-Guide.pdf). It includes remote PostgreSQL/TLS, optional Docker, Linux/macOS, all 26 sections, model evaluation, roles, 3D/2D settings, assistant accounts, tests, backups and troubleshooting.
