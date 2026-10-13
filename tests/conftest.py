"""PostgreSQL integration isolation; no application database fallback.

Set TEST_DATABASE_URL to a disposable PostgreSQL database before pytest. Legacy
test configurations with an empty URL are explicitly injected here, never in
application code. Every storage directory receives private, run-scoped schemas.
"""
import hashlib
import os
import tempfile
import uuid

import pytest

_URL = os.environ.get('TEST_DATABASE_URL', '')
if not _URL:
    raise pytest.UsageError('Tests require TEST_DATABASE_URL for a disposable PostgreSQL database.')
_PREFIX = 'cti_t_' + uuid.uuid4().hex[:8] + '_'
_temporary_storage = tempfile.TemporaryDirectory(prefix='cti-pg-tests-')
os.environ['DATABASE_URL'] = _URL
os.environ['DATABASE_SCHEMA'] = _PREFIX + 'global'
os.environ['STORAGE_DIR'] = _temporary_storage.name

from backend.app.config import Settings

_original_init = Settings.__init__


def _postgres_test_settings(self, **values):
    values.setdefault('_env_file', None)
    if not values.get('database_url'):
        values['database_url'] = _URL
    if not values.get('database_schema'):
        storage = str(values.get('storage_dir', 'global'))
        values['database_schema'] = _PREFIX + hashlib.sha256(storage.encode()).hexdigest()[:10]
    _original_init(self, **values)


Settings.__init__ = _postgres_test_settings


def pytest_sessionfinish(session, exitstatus):
    """Remove only schemas created by this pytest run, retaining unrelated data."""
    from sqlalchemy import create_engine, text
    url = _URL.replace('postgres://', 'postgresql+psycopg://', 1).replace('postgresql://', 'postgresql+psycopg://', 1)
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            names = conn.execute(text('SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE :prefix'), {'prefix': _PREFIX.replace('_', '\\_') + '%'}).scalars().all()
        for name in names:
            # Releasing each schema's locks avoids exhausting PostgreSQL's
            # shared lock table when a full suite creates hundreds of schemas.
            with engine.begin() as conn:
                conn.execute(text('DROP SCHEMA "' + name + '" CASCADE'))
    finally:
        engine.dispose()
        _temporary_storage.cleanup()
