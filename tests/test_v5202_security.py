"""Regression tests for PostgreSQL and the public project security boundary."""
import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.middleware.rate_limiter import RateLimiterMiddleware
from backend.app.platform_store import PlatformStore
from backend.app.services.data_service import DatasetRegistry

PASSWORD = 'secure regression password 123456'
TOKEN = 'security-regression-setup-token-123456'


@pytest.mark.parametrize('url', ['', 'sqlite:///:memory:', 'mysql://localhost/db'])
@pytest.mark.parametrize('store', [PlatformStore, DatasetRegistry])
def test_all_metadata_stores_require_postgresql(tmp_path, url, store):
    config = Settings(storage_dir=str(tmp_path), _env_file=None).model_copy(update={'database_url': url})
    with pytest.raises(ValueError, match='PostgreSQL'):
        store(config)
    assert not list(tmp_path.rglob('*.sqlite*'))


def test_untrusted_forwarding_headers_cannot_choose_rate_limit_identity():
    limiter = RateLimiterMiddleware(None)
    request = Request({'type': 'http', 'method': 'GET', 'path': '/', 'headers': [(b'x-forwarded-for', b'203.0.113.42')], 'client': ('198.51.100.7', 1)})
    assert limiter._get_client_ip(request) == '198.51.100.7'


def test_trusted_proxy_uses_nearest_untrusted_peer_and_rejects_invalid_chains():
    limiter = RateLimiterMiddleware(None, trusted_proxy_hosts='10.0.0.0/8')
    scope = {'type':'http','method':'GET','path':'/','client':('10.0.0.2',1),
             'headers':[(b'x-forwarded-for',b'203.0.113.99, 198.51.100.7, 10.0.0.1')]}
    assert limiter._get_client_ip(Request(scope)) == '198.51.100.7'
    scope['headers'] = [(b'x-forwarded-for',b'invalid-forwarded-peer')]
    assert limiter._get_client_ip(Request(scope)) == '10.0.0.2'


@pytest.mark.parametrize('store',[PlatformStore,DatasetRegistry])
def test_database_schema_identifier_cannot_inject_sql(tmp_path,store):
    config=Settings(storage_dir=str(tmp_path)).model_copy(update={'database_schema':'cti_example; DROP SCHEMA public'})
    with pytest.raises(ValueError,match='schema'):
        store(config)


@pytest.fixture
def owner(tmp_path):
    config = Settings(storage_dir=str(tmp_path), setup_token=TOKEN, auth_mode='session',
                      openai_api_key='', anthropic_api_key='', gemini_api_key='', compatible_api_key='')
    with TestClient(create_app(config)) as client:
        assert client.post('/api/v5/auth/setup', json={'email': 'owner@example.org', 'password': PASSWORD, 'name': 'Owner', 'setup_token': TOKEN}).status_code == 201
        project = client.post('/api/v5/projects', json={'name': 'Security regression'}).json()
        client.headers['X-Project-ID'] = project['id']
        yield client, project


@pytest.mark.parametrize('role', ['researcher', 'reviewer', 'viewer'])
def test_capabilities_match_server_permissions(owner, role):
    client, project = owner
    token = client.post('/api/v5/projects/' + project['id'] + '/members', json={'email': role + '@example.org', 'role': role}).json()['invitation_token']
    with TestClient(client.app) as member:
        assert member.post('/api/v5/auth/accept-invite', json={'token': token, 'password': PASSWORD, 'name': role}).status_code == 200
        member.headers['X-Project-ID'] = project['id']
        bootstrap_project = member.get('/api/v5/bootstrap').json()['projects'][0]
        assert bootstrap_project['capabilities']['train_models'] is False
        assert bootstrap_project['capabilities']['write_research'] is (role == 'researcher')
        assert bootstrap_project['capabilities']['chat'] is (role != 'viewer')
        assert member.post('/api/v1/experiments', json={}).status_code == 403
        assert member.post('/api/v1/phase-experiments', json={}).status_code == 403
        # Validation may reject an empty body, but a read capability must reach
        # its endpoint rather than be denied as a mutation by the gateway.
        for path in ['/api/v1/predictions', '/api/v1/phase-predictions', '/api/v1/explain', '/api/v1/overview/graphs']:
            assert member.post(path, json={}).status_code != 403
        assert member.post('/api/v5/conversations', json={'title': 'Review'}).status_code == (403 if role == 'viewer' else 201)


def test_rate_limiter_wraps_project_research_forwarding(owner):
    client, _ = owner
    seen = []
    for index in range(65):
        response = client.get('/api/v1/datasets', headers={'X-Forwarded-For': '203.0.113.' + str(index + 1)})
        seen.append(response.status_code)
    assert 429 in seen
    assert response.headers.get('X-RateLimit-Remaining') == '0'


def test_session_login_rotates_existing_browser_session(owner):
    client, _ = owner
    old_cookie = client.cookies.get('cti_session')
    assert client.post('/api/v5/auth/login', json={'email': 'owner@example.org', 'password': PASSWORD}).status_code == 200
    assert client.cookies.get('cti_session') != old_cookie
    with TestClient(client.app) as stale:
        stale.cookies.set('cti_session', old_cookie)
        assert stale.get('/api/v5/auth/me').status_code == 401


def test_password_change_and_logout_all_revoke_other_sessions(owner):
    client, _ = owner
    with TestClient(client.app) as other:
        assert other.post('/api/v5/auth/login', json={'email':'owner@example.org','password':PASSWORD}).status_code == 200
        assert client.post('/api/v5/auth/password', json={'current_password':'incorrect password','new_password':'a replacement secure password'}).status_code == 401
        assert client.post('/api/v5/auth/password', json={'current_password':PASSWORD,'new_password':'a replacement secure password'}).status_code == 200
        assert other.get('/api/v5/auth/me').status_code == 401
        assert other.post('/api/v5/auth/login', json={'email':'owner@example.org','password':PASSWORD}).status_code == 401
        assert other.post('/api/v5/auth/login', json={'email':'owner@example.org','password':'a replacement secure password'}).status_code == 200
        assert client.post('/api/v5/auth/logout-all').status_code == 200
        assert other.get('/api/v5/auth/me').status_code == 401


def test_concurrent_password_change_cannot_issue_a_session_for_stale_credentials(owner,monkeypatch):
    from backend.app import platform
    client, _ = owner
    store=client.app.state.platform_store
    original=platform.verify_password
    def verify_then_change(password,encoded):
        verified=original(password,encoded)
        store.execute('UPDATE v5_users SET password_hash=:hash',{'hash':platform.hash_password('new concurrent secure password')})
        return verified
    monkeypatch.setattr(platform,'verify_password',verify_then_change)
    with TestClient(client.app) as login:
        assert login.post('/api/v5/auth/login',json={'email':'owner@example.org','password':PASSWORD}).status_code == 401
        assert login.cookies.get('cti_session') is None


def test_final_owner_is_protected_and_member_revocation_is_immediate(owner):
    client, project = owner
    owner_id = client.get('/api/v5/auth/me').json()['user']['id']
    members = '/api/v5/projects/' + project['id'] + '/members'
    assert client.delete(members + '/' + owner_id).status_code == 409
    assert client.post(members, json={'email':'owner@example.org','role':'viewer'}).status_code == 409
    token = client.post(members, json={'email':'revoked@example.org','role':'researcher'}).json()['invitation_token']
    with TestClient(client.app) as member:
        user_id = member.post('/api/v5/auth/accept-invite', json={'token':token,'password':PASSWORD,'name':'Member'}).json()['user']['id']
        member.headers['X-Project-ID'] = project['id']
        assert member.get('/api/v1/datasets').status_code == 200
        assert member.delete(members + '/' + owner_id).status_code == 403
        assert client.delete(members + '/' + user_id).status_code == 200
        assert member.get('/api/v1/datasets').status_code == 403
