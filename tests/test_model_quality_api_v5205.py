"""Real PostgreSQL/project gateway checks for saved model quality."""
import json
import shutil

import pytest
from fastapi.testclient import TestClient

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.main import create_app

PASSWORD = 'quality check software test password'
SETUP = 'quality-test-setup-token-123456789'


@pytest.fixture
def quality_owner(tmp_path, monkeypatch):
    def no_load(*args, **kwargs):
        raise AssertionError('Quality inspection must not deserialize an estimator or fit a model')
    monkeypatch.setattr('joblib.load', no_load)
    monkeypatch.setattr('sklearn.pipeline.Pipeline.fit', no_load)
    settings = Settings(storage_dir=str(tmp_path), database_url='', auth_mode='session', setup_token=SETUP, _env_file=None)
    with TestClient(create_app(settings)) as client:
        assert client.get('/api/v1/model-quality').status_code == 401
        response = client.post('/api/v5/auth/setup', json={'email': 'quality-owner@example.org', 'password': PASSWORD, 'name': 'Quality owner', 'setup_token': SETUP})
        assert response.status_code == 201, response.text
        project = client.post('/api/v5/projects', json={'name': 'Quality evidence project'}).json()
        client.headers['X-Project-ID'] = project['id']
        yield client, project


@pytest.mark.parametrize('role', ['viewer', 'reviewer', 'researcher'])
def test_authorized_project_readers_can_inspect_without_training(quality_owner, role):
    owner, project = quality_owner
    invitation = owner.post(f'/api/v5/projects/{project["id"]}/members', json={'email': f'{role}@quality.example.org', 'name': role, 'role': role})
    assert invitation.status_code == 201, invitation.text
    with TestClient(owner.app) as reader:
        accepted = reader.post('/api/v5/auth/accept-invite', json={'token': invitation.json()['invitation_token'], 'password': PASSWORD, 'name': role})
        assert accepted.status_code == 200, accepted.text
        reader.headers['X-Project-ID'] = project['id']
        for task in ('duration', 'phase'):
            response = reader.get('/api/v1/model-quality', params={'task': task})
            assert response.status_code == 200, response.text
            evidence = response.json()
            assert evidence['task'] == task and evidence['selected']['n'] > 0
            assert evidence['integrity']['estimator_deserialized'] is False
        assert owner.app.state.project_registry(project['id']).list_experiments() == []
        reader.headers['X-Project-ID'] = 'f' * 32
        assert reader.get('/api/v1/model-quality').status_code == 403


def test_quality_model_ids_and_query_cannot_cross_project_scope(quality_owner):
    client, first = quality_owner
    registry = client.app.state.project_registry(first['id'])
    data = registry.register_bytes((PROJECT_ROOT / 'data/starter/trials.csv').read_bytes(), 'authentic-existing-evaluation.csv')
    identifier = 'c' * 32
    output = registry.artifact_path(identifier)
    shutil.copytree(PROJECT_ROOT / 'examples/starter-duration-v5', output)
    path = output / 'manifest.json'
    manifest = json.loads(path.read_text())
    manifest['source_metadata'].update(dataset_id=data['id'], sha256=data['sha256'])
    path.write_text(json.dumps(manifest))
    registry.save_experiment({'id': identifier, 'task': 'duration', 'status': 'completed', 'dataset_id': data['id'], 'dataset_sha256': data['sha256'], 'created_at': '2026-10-18T00:00:00Z', 'manifest': manifest})
    model_id = 'project-' + identifier
    approved = client.post(f'/api/v5/models/{model_id}/approve', json={'notes': 'Existing authentic evidence copied for permission test only.', 'research_only_acknowledged': True})
    assert approved.status_code == 200, approved.text
    assert client.get('/api/v1/model-quality', params={'model_id': model_id}).status_code == 200
    second = client.post('/api/v5/projects', json={'name': 'Separate quality scope'}).json()
    client.headers['X-Project-ID'] = second['id']
    assert client.get('/api/v1/model-quality', params={'model_id': model_id}).status_code == 404
    # Query parameters cannot switch away from the header-selected registry.
    assert client.get('/api/v1/model-quality', params={'model_id': model_id, 'project_id': first['id']}).status_code == 404
