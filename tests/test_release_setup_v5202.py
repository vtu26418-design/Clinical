"""Release setup must create unique credentials and preserve operator edits."""
from pathlib import Path
import importlib.util


def initializer():
    path = Path(__file__).parents[1] / 'scripts' / 'initialize_env.py'
    spec = importlib.util.spec_from_file_location('cti_initialize_env', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_initialize_env_creates_unique_postgresql_credentials_and_is_repeatable(tmp_path):
    (tmp_path / '.env.example').write_text('SETUP_TOKEN=\nPOSTGRES_USER=cti\nPOSTGRES_DB=cti\nPOSTGRES_PASSWORD=\nPOSTGRES_PORT=5432\nDATABASE_URL=\nTEST_DATABASE_URL=\nOPENAI_API_KEY=\n')
    module = initializer()
    env = module.prepare_env(tmp_path)
    values = module.read_env(env)
    assert len(values['SETUP_TOKEN']) >= 24
    assert len(values['POSTGRES_PASSWORD']) >= 24
    assert values['DATABASE_URL'].startswith('postgresql+psycopg://cti:')
    assert values['DATABASE_URL'].endswith('@127.0.0.1:5432/cti')
    assert values['TEST_DATABASE_URL'].endswith('@127.0.0.1:5433/cti_test')
    assert values['OPENAI_API_KEY'] == ''
    contents = env.read_text()
    assert module.prepare_env(tmp_path).read_text() == contents


def test_initialize_preserves_existing_remote_url_and_credentials(tmp_path):
    content = 'SETUP_TOKEN=operator-configured-token-is-long-enough\nPOSTGRES_PASSWORD=operator-password-is-also-long-enough\nPOSTGRES_USER=custom\nPOSTGRES_DB=research\nPOSTGRES_PORT=6543\nDATABASE_URL=postgresql+psycopg://operator@example.invalid/research?sslmode=require\nOPENAI_API_KEY=operator-test-value\n'
    (tmp_path / '.env').write_text(content)
    module = initializer()
    values = module.read_env(module.prepare_env(tmp_path))
    assert values['DATABASE_URL'] == 'postgresql+psycopg://operator@example.invalid/research?sslmode=require'
    assert values['OPENAI_API_KEY'] == 'operator-test-value'
    assert values['POSTGRES_PASSWORD'] == 'operator-password-is-also-long-enough'


def test_compose_failure_returns_friendly_status_without_traceback(monkeypatch,capsys):
    import subprocess,sys
    module=initializer()
    monkeypatch.setattr(sys,'argv',['initialize_env.py','--start'])
    monkeypatch.setattr(module,'prepare_env',lambda:None)
    def failed(*args,**kwargs):raise subprocess.CalledProcessError(1,['docker','compose'])
    monkeypatch.setattr(module.subprocess,'run',failed)
    assert module.main()==1
    assert 'Docker Compose failed' in capsys.readouterr().out
