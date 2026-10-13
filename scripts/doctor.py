"""Offline installation diagnostics. Never prints keys or database credentials."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main():
    checks = []
    def add(name, ok, detail):
        checks.append({'check': name, 'ok': bool(ok), 'detail': detail})
    add('Python 3.12', sys.version_info[:2] == (3, 12), sys.version.split()[0])
    required = ['fastapi', 'uvicorn', 'pandas', 'numpy', 'sklearn', 'joblib', 'pyarrow', 'pydantic_settings', 'httpx', 'openai', 'sqlalchemy', 'psycopg', 'pypdf', 'openpyxl', 'defusedxml', 'catboost']
    missing = [name for name in required if importlib.util.find_spec(name) is None]
    add('Dependencies', not missing, 'Missing: ' + ', '.join(missing) if missing else 'Core modules installed; use pip check for dependency consistency.')
    add('Built interface', (ROOT / 'frontend/dist/index.html').is_file(), 'Run npm ci and npm run build in frontend if missing.')
    add('Starter data', (ROOT / 'data/starter/trials.csv').is_file(), 'Bundled real data can be loaded from Data Manager.')
    if not missing:
        try:
            from backend.app.config import Settings
            from backend.app.services.assistant_service import assistant_status
            settings = Settings()
            settings.store_path.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=settings.store_path) as stream:
                stream.write(b'CTI storage check')
            add('Writable storage', True, 'Local storage is writable.')
            from sqlalchemy import create_engine, text
            engine = create_engine(settings.database_url, connect_args={'connect_timeout':5})
            try:
                with engine.connect() as connection:
                    connection.execute(text('SELECT 1'))
                add('PostgreSQL connection', True, 'Authenticated database connection succeeded.')
            except Exception:
                add('PostgreSQL connection', False, 'Start PostgreSQL and verify DATABASE_URL; credentials are not displayed.')
            finally:
                engine.dispose()
            routing = assistant_status(settings)
            add('Server configuration', True, f"Port {settings.api_port}; assistant: {routing['selected_label']}; configured providers: {', '.join(p['label'] for p in routing['providers'] if p['configured']) or 'none'}; remote database configured: {bool(settings.database_url)}. Provider credentials not tested.")
        except Exception:
            add('Server configuration / storage', False, 'Check .env value types and local storage permissions. No secrets are printed.')
    print(json.dumps({'ready': all(item['ok'] for item in checks), 'checks': checks}, indent=2))
    return 0 if all(item['ok'] for item in checks) else 1

if __name__ == '__main__':
    raise SystemExit(main())
