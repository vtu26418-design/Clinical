"""Generate local PostgreSQL/setup credentials without exposing them on stdout.

Uses only the Python standard library; usable before dependency installation.
Existing operator values are preserved. The generated .env is never a release
asset and is private on POSIX. Use --start for the Docker application workflow.
"""
from pathlib import Path
import argparse
import os
import re
import secrets
import shlex
import subprocess
import time
from urllib.request import urlopen
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def read_env(path):
    values = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        name = name.strip().removeprefix('export ').strip()
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*', name):
            continue
        if value.strip().startswith(('"', "'")):
            parts = shlex.split(value, comments=True)
            value = parts[0] if parts else ''
        else:
            value = value.split(' #', 1)[0].strip()
        values[name] = value
    return values


def prepare_env(root=ROOT):
    root = Path(root)
    destination = root / '.env'
    source = destination if destination.exists() else root / '.env.example'
    contents = source.read_text(encoding='utf-8')
    values = read_env(source)

    def supply(name, value):
        nonlocal contents
        if values.get(name):
            return
        pattern = r'^\s*(?:export\s+)?' + re.escape(name) + r'\s*=.*$'
        line = name + '=' + value
        contents = re.sub(pattern, lambda _: line, contents, flags=re.MULTILINE) if re.search(pattern, contents, flags=re.MULTILINE) else contents.rstrip() + '\n' + line + '\n'
        values[name] = value

    supply('SETUP_TOKEN', secrets.token_urlsafe(32))
    supply('POSTGRES_USER', 'cti')
    supply('POSTGRES_DB', 'cti')
    supply('POSTGRES_PORT', '5432')
    supply('POSTGRES_PASSWORD', secrets.token_urlsafe(32))
    user, password, database = (quote(values[name], safe='') for name in ('POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB'))
    supply('DATABASE_URL', f'postgresql+psycopg://{user}:{password}@127.0.0.1:{values["POSTGRES_PORT"]}/{database}')
    supply('COMPOSE_DATABASE_URL', f'postgresql+psycopg://{user}:{password}@postgres:5432/{database}')
    supply('TEST_DATABASE_URL', f'postgresql+psycopg://{user}:{password}@127.0.0.1:5433/cti_test')
    if not destination.exists() or destination.read_text(encoding='utf-8') != contents:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(contents)
    if os.name != 'nt':
        destination.chmod(0o600)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', action='store_true', help='Build and start PostgreSQL and the web app with Docker Compose.')
    args = parser.parse_args()
    prepare_env()
    print('Private .env prepared. Existing settings preserved; credential values are not displayed.')
    if args.start:
        subprocess.run(['docker', 'compose', 'up', '-d', '--build', 'workbench'], cwd=ROOT, check=True)
        port = '8000'  # Docker Compose publishes the application on port 8000.
        address = f'http://localhost:{port}'
        deadline = time.monotonic() + 120
        while True:
            try:
                with urlopen(address + '/api/v5/bootstrap', timeout=3) as response:
                    if response.status == 200:
                        break
            except Exception:
                if time.monotonic() >= deadline:
                    raise SystemExit('Startup has not completed. Run docker compose logs workbench and follow the guide troubleshooting steps.')
                time.sleep(1)
        print(f'Application ready: {address}. Read SETUP_TOKEN from your local .env for the first owner account.')
    else:
        print('Next: docker compose up -d --build workbench, or run the native setup described in START-HERE.md.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
