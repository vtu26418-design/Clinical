"""Cross-platform setup; Node is unnecessary when the prebuilt UI is present."""
from pathlib import Path
import argparse
import os
import re
import secrets
import subprocess
import sys
import venv
ROOT = Path(__file__).resolve().parents[1]


def prepare_env(root=ROOT):
    """Preserve operator configuration and supply a unique first-owner secret."""
    from scripts.initialize_env import prepare_env as initialize
    return initialize(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dev', action='store_true', help='Also install test dependencies')
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.exit(1, 'Please install Python 3.12 and run this setup with it.\n')
    environment = ROOT / '.venv'
    print('Creating the local Python environment...', flush=True)
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / ('requirements-dev.txt' if args.dev else 'requirements.txt'))], check=True)
    # Use the environment we just installed; the Python launcher itself need
    # not have python-dotenv installed.
    subprocess.run([str(python), '-c', 'from scripts.setup import prepare_env; prepare_env()'], cwd=ROOT, check=True)
    if not (ROOT / 'frontend/dist/index.html').exists():
        print('UI missing. Install Node.js 22, then run npm ci and npm run build in frontend/.')
        return 1
    print('Python setup complete. Start PostgreSQL: docker compose up -d postgres')
    print('Then run START_WINDOWS.bat or .venv/bin/python scripts/start.py')
    print('First owner: open .env in a text editor, copy SETUP_TOKEN, and use it in the first-run form. Keep .env private.')
    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        sys.exit(f'Installation failed (exit {exc.returncode}). Check your network and retry setup.')
