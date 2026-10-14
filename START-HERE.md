# Start here — Clinical Trial Intelligence v5.2.0.3 Docker edition

**You have Docker: use this startup path.** The application version, features, datasets and approved models stay v5.2.0.3.

1. Open **Docker Desktop**. Wait for **Engine running**. Use its Linux-container engine and complete any requested WSL2/restart setup.
2. Confirm Python 3.12 is installed with its launcher: `py -3.12 --version`. Install it from [python.org](https://www.python.org/downloads/windows/) if needed.
3. Right-click the downloaded project ZIP → **Extract All**. Open the folder containing `START_DOCKER_WINDOWS.bat`.
4. Double-click **START_DOCKER_WINDOWS.bat**. If you previously ran `SETUP_WINDOWS.bat`, you can go straight to this step.
5. Leave the window open while images download and the application builds. The launcher generates missing credentials in your private `.env`, preserves existing values, and starts both PostgreSQL and the application.
6. Wait for **Application ready: http://localhost:8000**. The browser opens automatically. If it does not, open that address manually.
7. Open the extracted folder's `.env` in a text editor. Copy only the value after `SETUP_TOKEN=` into the first-owner form. Enter your name, email and a unique password of at least 12 characters. Keep `.env` private. If an owner already exists, sign in instead.
8. Create/open a project. More tools → Data Manager → load the **800-record starter cohort** and select it. Review Overview and use Prediction Studio with a bundled approved model. Training is optional.

Docker provides PostgreSQL and installs application dependencies inside the image. You do not need a separate PostgreSQL installation or Node on Windows for this path. `CONNECT_DATABASE_WINDOWS.bat` and `START_WINDOWS.bat` are the optional native path, documented separately in the guide.

From PowerShell in the extracted project folder, the launcher is:

```powershell
.\START_DOCKER_WINDOWS.bat
```

To check or stop the services:

```powershell
docker compose ps
docker compose down
```

Keep Docker Desktop running while using the app. Later starts use the same launcher. Named Docker volumes preserve PostgreSQL and research files; do not delete them when you want to keep your work.

If port 5432 is occupied, set `POSTGRES_PORT=5434` in your private `.env` and rerun the Docker launcher. If port 8000 is occupied by a native workbench, stop that process before starting Docker. Check `docker compose logs --tail 100 workbench postgres` for a startup failure; do not share logs containing secrets.

Assistant replies need your provider key and an account-supported API model ID in the private `.env`. After changing those settings, run `docker compose up -d --force-recreate workbench` from the project folder. Provider keys stay on the server.

[Full operating guide](docs/v5.2.0.3-full-guide.md) · [Illustrated PDF guide](docs/Clinical-Trial-Intelligence-v5.2.0.3-Full-Guide.pdf)
