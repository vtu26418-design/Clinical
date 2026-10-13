"""Load the private test-database configuration and run the complete suite."""
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from scripts.initialize_env import read_env
    if (ROOT / '.env').exists():
        value = read_env(ROOT / '.env').get('TEST_DATABASE_URL')
        if value:
            os.environ.setdefault('TEST_DATABASE_URL', value)
    if not os.environ.get('TEST_DATABASE_URL'):
        raise SystemExit('Configure TEST_DATABASE_URL for a disposable PostgreSQL database. See the guide.')
    return subprocess.run([sys.executable, '-m', 'pytest', '-q', *sys.argv[1:]], cwd=ROOT).returncode


if __name__ == '__main__':
    raise SystemExit(main())
