# Clinical Trial Intelligence v5.2.0.2

1. Extract the ZIP, for example into `C:\CTI`.
2. Install Python 3.12 and Docker Desktop; start Docker Desktop.
3. Windows: double-click `START_DOCKER_WINDOWS.bat`. Other systems: `python3.12 scripts/initialize_env.py --start`.
4. Open http://localhost:8000 when ready.
5. Copy `SETUP_TOKEN` from your private `.env` into the first-owner form. Create your account/project.
6. More tools → Data Manager → load the 800-record starter cohort.
7. Open Overview or Prediction Studio. Bundled predictions do not require training.

Read [the full guide](docs/V5_2_0_2_FULL_GUIDE.md) or open `docs/Clinical-Trial-Intelligence-v5.2.0.2-Full-Guide.pdf` for environment values, roles, every section, fitting, tests and troubleshooting.

PostgreSQL is required. The interface is prebuilt; Node is needed only for frontend development. Commercial AI replies need your server-side provider key and usable API model ID.
