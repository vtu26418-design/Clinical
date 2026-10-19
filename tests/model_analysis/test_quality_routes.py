"""Project resolver and token boundaries, with synthetic saved evidence."""
import hashlib
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from test_model_analysis import experiment


def client_for(path, *, resolver_error=None):
    from backend.app.model_quality_routes import attach_model_quality
    artifact = path / 'models.joblib'
    artifact.write_bytes(b'not a deserializable estimator; quality inspection must not load it')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    public = {'id': 'project-approved', 'task': 'duration', 'branch': 'model', 'status': 'approved',
              'manifest_sha256': sha(path / 'manifest.json'), 'artifact_sha256': sha(artifact),
              'warnings': [], 'approval_scope': 'research_only'}
    calls = []
    def resolver(task, model_id='active'):
        calls.append((task, model_id))
        if resolver_error:
            raise HTTPException(resolver_error, 'Model is not approved in this project.')
        if model_id not in {'active', 'project-approved'}:
            raise HTTPException(404, 'Model not found in this project.')
        return {'directory': path, 'branch': 'model', 'task': task, 'model': public}
    def auth(authorization: str = Header(default='')):
        if authorization != 'Bearer project-reader':
            raise HTTPException(401, 'Authentication required.')
    app = FastAPI()
    attach_model_quality(app, SimpleNamespace(approved_model_resolver=resolver), auth)
    return TestClient(app), calls


def get(client, **params):
    return client.get('/api/v1/model-quality', params=params, headers={'Authorization': 'Bearer project-reader'})


def test_quality_uses_real_rows_and_preserves_token_and_resolver_scope(tmp_path):
    path = experiment(tmp_path)
    client, calls = client_for(path)
    assert client.get('/api/v1/model-quality').status_code == 401
    assert not calls
    response = get(client)
    assert response.status_code == 200, response.text
    quality = response.json()
    assert quality['selected']['n'] == 2
    assert quality['selected']['regression']['mae_days'] == 10
    assert quality['selected']['classification']['auroc'] == 1
    assert quality['integrity']['artifact_and_manifest'] == 'verified_against_approval'
    assert quality['baseline'] is None
    assert quality['endpoint']['prolonged_threshold_days'] == 15
    assert str(tmp_path) not in json.dumps(quality)
    assert calls == [('duration', 'active')]
    assert get(client, model_id='project-other-project').status_code == 404
    assert get(client, model_id='../private').status_code == 422


@pytest.mark.parametrize('name', ['manifest.json', 'models.joblib'])
def test_quality_rechecks_manifest_and_estimator_checksums_without_loading(tmp_path, name):
    path = experiment(tmp_path)
    client, _ = client_for(path)
    with (path / name).open('ab') as stream:
        stream.write(b' ')
    response = get(client)
    assert response.status_code == 409
    assert str(path) not in response.text


def test_quality_rejects_invalid_or_symlinked_prediction_evidence(tmp_path):
    path = experiment(tmp_path)
    client, _ = client_for(path)
    predictions = path / 'held_out_predictions.csv'
    outside = tmp_path / 'external.csv'
    predictions.rename(outside)
    predictions.symlink_to(outside)
    assert get(client).status_code == 409


def test_quality_propagates_project_approval_failure_and_disallows_train_split(tmp_path):
    path = experiment(tmp_path)
    client, _ = client_for(path, resolver_error=403)
    assert get(client).status_code == 403
    client, _ = client_for(path)
    assert get(client, split='train').status_code == 422


def test_quality_downloads_use_identical_recomputed_selection(tmp_path):
    client, _ = client_for(experiment(tmp_path))
    response = get(client, format='html')
    assert response.status_code == 200, response.text
    assert 'attachment;' in response.headers['content-disposition']
    assert 'default-src' in response.headers['content-security-policy']
    assert 'RMSE' in response.text
    csv = get(client, format='csv')
    assert csv.status_code == 200 and 'median_absolute_error_days' in csv.text


def test_quality_labels_recorded_bootstrap_intervals_separately_from_recomputed_metrics(tmp_path):
    path = experiment(tmp_path)
    manifest_path = path / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['models']['model']['metrics'] = {'test': {'confidence_intervals': {
        'method': 'paired trial bootstrap percentile', 'level': .95, 'requested_resamples': 200,
        'random_seed': 42, 'mae': {'lower': 9, 'upper': 11, 'valid_resamples': 200}}}}
    manifest_path.write_text(json.dumps(manifest))
    client, _ = client_for(path)
    response = get(client)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report['selected']['regression']['mae_days'] == 10
    intervals = report['uncertainty']['metric_confidence_intervals']
    assert intervals['status'] == 'recorded_not_recomputed'
    assert intervals['recorded']['mae']['lower'] == 9
    assert 'not independently recomputed' in intervals['reason']
