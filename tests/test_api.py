"""API contracts exercised against isolated local persistent state."""
import csv
import io
import json
from pathlib import Path
from datetime import datetime, timedelta

import httpx
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_research_app as create_app


@pytest.fixture
def client(tmp_path):
    config = Settings(storage_dir=str(tmp_path / 'store'), database_url='', openai_api_key='', api_bearer_token='', _env_file=None)
    with TestClient(create_app(config)) as client:
        yield client


def upload(client, payload, name='cohort.csv'):
    return client.post('/api/v1/datasets/upload', files={'file': (name, payload, 'text/csv')})


def test_sample_is_labeled_and_predictions_are_unavailable(client):
    ds = client.get('/api/v1/datasets').json()['items'][0]
    assert ds['id'] == 'sample-fixture' and ds['is_fixture'] is True
    page = client.get('/api/v1/studies').json()
    assert page['total'] == 5
    assert all(x['prolonged_risk'] is None for x in page['items'])
    detail = client.get('/api/v1/studies/NCT-SAMPLE-001').json()
    assert detail['prediction']['status'] == 'unavailable'
    assert detail['prediction']['probability'] is None


def test_atomic_upload_and_persistent_provenance(client):
    invalid = upload(client, b'nct_id,title,enrollment\nNCT1,Test,-2\n')
    assert invalid.status_code == 422
    assert {row['id'] for row in client.get('/api/v1/datasets').json()['items']} == {'sample-fixture', 'registry-v5205'}
    raw = b'nct_id,title,enrollment,start_date\nNCT1,Good trial,12,2024-01-01\n'
    response = upload(client, raw)
    assert response.status_code == 201
    dataset = response.json()
    assert dataset['row_count'] == 1 and dataset['sha256'] and not dataset['is_fixture']
    from backend.app.services.data_service import DatasetRegistry
    registry = DatasetRegistry(client.app.state.settings)
    assert registry.get_dataset(dataset['id'])['sha256'] == dataset['sha256']
    assert registry.raw_path(dataset['id']).read_bytes() == raw
    assert {row['id'] for row in client.get('/api/v1/datasets').json()['items']} == {'sample-fixture', 'registry-v5205', dataset['id']}


def test_validation_rejects_duplicates_invalid_dates_and_nonfinite(client):
    for payload in [b'nct_id,title\nA,One\nA,Two\n', b'nct_id,title,start_date\nA,One,2024-02-31\n', b'nct_id,title,enrollment\nA,One,inf\n']:
        assert upload(client, payload).status_code == 422
    assert {row['id'] for row in client.get('/api/v1/datasets').json()['items']} == {'sample-fixture', 'registry-v5205'}


def test_literal_search_filters_pagination_and_dataset_isolation(client):
    result = upload(client, b'nct_id,title,phase,status\nA,Trial [test],PHASE2,COMPLETED\nB,Other,PHASE1,RECRUITING\n').json()
    query = {'dataset_id': result['id'], 'q': '['}
    response = client.get('/api/v1/studies', params=query)
    assert response.status_code == 200 and response.json()['total'] == 1
    assert client.get('/api/v1/studies', params={'dataset_id':result['id'],'offset':1,'limit':1}).json()['items'][0]['nct_id'] == 'B'
    assert client.get('/api/v1/studies', params={'dataset_id':result['id'],'phase':'PHASE1'}).json()['total'] == 1
    assert client.get('/api/v1/studies').json()['total'] == 5
    assert client.get('/api/v1/studies', params={'offset':'bad'}).status_code == 422
    assert client.get('/api/v1/studies', params={'dataset_id':'../../etc'}).status_code == 404


def test_no_key_assistant_and_fixture_training_fail_explicitly(client):
    response = client.post('/api/v1/assistant', json={'message':'Explain this study','dataset_id':'sample-fixture'})
    assert response.status_code == 503
    assert client.get('/api/v1/health').json()['openai_configured'] is False
    response = client.post('/api/v1/experiments', json={'dataset_id':'sample-fixture'})
    assert response.status_code == 422
    assert '30' in response.json()['detail']


def test_exports_guard_formulas_and_escape_html(client):
    result = upload(client, b'nct_id,title\nA,=HYPERLINK("x")\nB,<script>alert(1)</script>\n').json()
    response = client.get('/api/v1/exports/studies.csv', params={'dataset_id':result['id']})
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert rows[0]['title'].startswith("'=")
    report = client.get('/api/v1/exports/report.html', params={'dataset_id':result['id']}).text
    assert '<script>' not in report and '&lt;script&gt;' in report


def test_configured_bearer_token_protects_nonhealth_routes(tmp_path):
    config = Settings(storage_dir=str(tmp_path), database_url='', openai_api_key='', api_bearer_token='unit-test-token', _env_file=None)
    with TestClient(create_app(config)) as client:
        assert client.get('/api/v1/health').status_code == 200
        assert client.get('/api/v1/datasets').status_code == 401
        assert client.get('/api/v1/datasets', headers={'Authorization':'Bearer unit-test-token'}).status_code == 200


def test_duplicate_csv_headers_rejected_before_pandas_renaming(client):
    response = upload(client, b'nct_id,title,enrollment,enrollment\nA,One,10,20\n')
    assert response.status_code == 422
    assert {row['id'] for row in client.get('/api/v1/datasets').json()['items']} == {'sample-fixture', 'registry-v5205'}


def test_csv_rows_cannot_silently_shift_into_an_implicit_index(client):
    response = upload(client, b'nct_id,title\nA,One,Unexpected third field\n')
    assert response.status_code == 422
    assert {row['id'] for row in client.get('/api/v1/datasets').json()['items']} == {'sample-fixture', 'registry-v5205'}


def test_canonical_text_and_partial_dates_survive_reload(client):
    response = upload(client, b'nct_id,title,phase,start_date\n0001,0007,NA,2024\n0002,Other,,\n')
    assert response.status_code == 201
    dataset = response.json()
    detail = client.get('/api/v1/studies/0001', params={'dataset_id': dataset['id']})
    assert detail.status_code == 200
    assert detail.json()['study']['title'] == '0007'
    assert detail.json()['study']['phase'] == 'NA'
    assert detail.json()['study']['start_date'] == '2024'
    assert dataset['quality']['missingness']['phase'] == 1
    assert dataset['quality']['missingness']['status'] == 2
    assert dataset['quality']['partial_date_values'] == 1


def test_partial_dates_retain_uncertainty_in_date_order_validation(client):
    # An unspecified day/month is not evidence that completion preceded start.
    response = upload(client, b'nct_id,title,start_date,completion_date\nA,Partial software fixture,2024-06-01,2024\n')
    assert response.status_code == 201
    assert response.json()['quality']['partial_date_values'] == 1
    definitely_invalid = upload(client, b'nct_id,title,start_date,completion_date\nB,Invalid software fixture,2024,2023\n')
    assert definitely_invalid.status_code == 422


def test_parquet_timestamp_upload_preserves_raw_and_normalizes_dates(client):
    stream = io.BytesIO()
    pd.DataFrame({'nct_id':['PQ1'], 'title':['Parquet software test'], 'start_date':[pd.Timestamp('2024-01-01')], 'enrollment':[12]}).to_parquet(stream, index=False)
    raw = stream.getvalue()
    response = upload(client, raw, 'cohort.parquet')
    assert response.status_code == 201
    dataset = response.json()
    assert client.app.state.registry.raw_path(dataset['id']).read_bytes() == raw
    study = client.get('/api/v1/studies/PQ1', params={'dataset_id':dataset['id']}).json()['study']
    assert study['start_date'] == '2024-01-01'


def test_overview_requires_present_compatible_artifacts(client):
    dataset = upload(client, b'nct_id,title,enrollment\nA,One,10\nB,Two,20\n').json()
    registry = client.app.state.registry
    registry.save_experiment({'id':'a'*32, 'dataset_id':dataset['id'], 'dataset_sha256':dataset['sha256'], 'status':'completed', 'created_at':'2024-01-01'})
    result = client.get('/api/v1/overview', params={'dataset_id':dataset['id']}).json()
    assert result['predictions_available'] is False
    assert result['enrollment_total'] == 30
    assert result['status_counts'] == {'Unknown':2}


def software_test_cohort(rows=60, duration=30):
    """Generated records are software fixtures only; never research evidence."""
    return pd.DataFrame([{
        'nct_id':f'SOFTWARE-TEST-{i:03d}', 'title':f'SOFTWARE TEST ONLY protocol {i}',
        'phase':'PHASE2', 'study_type':'INTERVENTIONAL', 'status':'COMPLETED',
        'completion_date_type':'ACTUAL', 'enrollment':10+i,
        'number_of_arms':1+i%3, 'primary_outcomes':1, 'secondary_outcomes':i%4,
        'criteria_count':5+i%8, 'text_complexity':1,
        'brief_summary':'Generated software test fixture. Not a real trial.',
        'start_date':(datetime(2010, 1, 1)+timedelta(days=i*60)).date().isoformat(),
        'completion_date':(datetime(2010, 1, 1)+timedelta(days=i*60+duration+i%10)).date().isoformat(),
    } for i in range(rows)])


def test_training_preflight_rejects_outcomes_unavailable_at_cutoff(client):
    dataset = upload(client, software_test_cohort(duration=6000).to_csv(index=False).encode()).json()
    result = client.post('/api/v1/experiments', json={'dataset_id':dataset['id']})
    assert result.status_code == 422
    assert client.get('/api/v1/experiments').json()['items'] == []


def test_upload_training_prediction_and_cross_dataset_artifact_isolation(client):
    # Full real fitting is tested on generated software fixtures, never real evidence.
    raw = software_test_cohort().to_csv(index=False).encode()
    dataset = upload(client, raw, 'SOFTWARE-TEST-ONLY.csv').json()
    result = client.post('/api/v1/experiments', json={'dataset_id':dataset['id']})
    assert result.status_code == 202, result.text
    experiment = client.get('/api/v1/experiments/'+result.json()['id']).json()
    assert experiment['status'] == 'completed', experiment
    assert set(experiment['metrics']) == {'median_baseline','structured','text','multimodal','structured_extra_trees','structured_random_forest','structured_gradient_boosting','structured_hist_gradient_boosting','multimodal_late_fusion'}
    assert experiment['manifest']['source_metadata']['sha256'] == dataset['sha256']
    result = client.post('/api/v1/predictions', json={'dataset_id':dataset['id'], 'nct_id':'SOFTWARE-TEST-059'})
    assert result.status_code == 200
    prediction = result.json()
    assert prediction['status'] == 'available'
    assert 0 <= prediction['probability'] <= 1
    assert prediction['duration_days'] >= 0
    assert prediction['model_name'] == experiment['manifest']['recommended_model']
    tree = client.post('/api/v1/predictions', json={'dataset_id':dataset['id'], 'nct_id':'SOFTWARE-TEST-059', 'model_name':'structured_extra_trees'}).json()
    assert tree['status'] == 'available' and tree['explanation']['scope'] == 'global'
    assert client.get('/api/v1/overview', params={'dataset_id':dataset['id']}).json()['predictions_available'] is True
    # Identical bytes uploaded to a different dataset must not inherit a model.
    other = upload(client, raw, 'SECOND-SOFTWARE-TEST.csv').json()
    isolated = client.post('/api/v1/predictions', json={'dataset_id':other['id'], 'nct_id':'SOFTWARE-TEST-059'}).json()
    assert isolated['status'] == 'unavailable' and isolated['probability'] is None
    manifest_path = client.app.state.registry.artifact_path(experiment['id'])/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['source_metadata']['sha256'] = 'not-the-dataset'
    manifest_path.write_text(json.dumps(manifest))
    mismatched = client.post('/api/v1/predictions', json={'dataset_id':dataset['id'], 'nct_id':'SOFTWARE-TEST-059'}).json()
    assert mismatched['status'] == 'unavailable'


def test_upload_size_and_storage_failure_are_atomic(tmp_path, monkeypatch):
    config = Settings(storage_dir=str(tmp_path), max_upload_bytes=1024, database_url='', openai_api_key='', api_bearer_token='', _env_file=None)
    with TestClient(create_app(config)) as limited:
        assert upload(limited, b'x'*1025).status_code == 413
    # A database failure after staging cannot leave a registered partial dataset.
    registry = limited.app.state.registry
    original = registry._execute
    def fail_insert(sql, *args, **kwargs):
        if sql.startswith('INSERT INTO datasets'):
            raise RuntimeError('simulated database write failure')
        return original(sql, *args, **kwargs)
    monkeypatch.setattr(registry, '_execute', fail_insert)
    response = upload(limited, b'nct_id,title\nA,Atomic upload test\n')
    assert response.status_code == 503
    assert [p.name for p in (tmp_path/'datasets').iterdir()] == ['sample-fixture']
    assert {row['id'] for row in registry.list_datasets()} == {'sample-fixture', 'registry-v5205'}


def mock_registry_http(monkeypatch, handler):
    """Replace only the registry's HTTP transport; parsing/persistence stay real."""
    from backend.app.services import clinicaltrials_service
    actual_client = httpx.Client
    monkeypatch.setattr(clinicaltrials_service.httpx, 'Client', lambda **kwargs: actual_client(transport=httpx.MockTransport(handler), **kwargs))


def registry_test_page(identifier, **extra):
    # Explicit software-only payload with the ClinicalTrials.gov v2 shape.
    return {'studies':[{'protocolSection':{
        'identificationModule':{'nctId':identifier, 'briefTitle':'SOFTWARE TEST registry response'},
        'designModule':{'studyType':'INTERVENTIONAL', 'phases':['PHASE1'], 'enrollmentInfo':{'count':20,'type':'ACTUAL'}},
        'statusModule':{'overallStatus':'COMPLETED','startDateStruct':{'date':'2020-01-01','type':'ACTUAL'}, 'completionDateStruct':{'date':'2021-01-01','type':'ACTUAL'}},
        'outcomesModule':{'primaryOutcomes':[{'measure':'Software test'}]},
        'armsInterventionsModule':{'armGroups':[{'label':'Software arm'}]},
        'descriptionModule':{'briefSummary':'Generated adapter test fixture, not clinical evidence.'},
        'eligibilityModule':{'eligibilityCriteria':'Software fixture text'},
    }}], **extra}


def test_registry_import_paginates_and_preserves_source_pages(client, monkeypatch):
    pages = [registry_test_page('CT-TEST-1', nextPageToken='second'), registry_test_page('CT-TEST-2')]
    def handle(request):
        assert request.url.host == 'clinicaltrials.gov'
        assert request.url.params['query.term'] == 'software fixture'
        index = 1 if request.url.params.get('pageToken') == 'second' else 0
        return httpx.Response(200, json=pages[index])
    mock_registry_http(monkeypatch, handle)
    response = client.post('/api/v1/datasets/import/clinicaltrials', json={'query':'software fixture','max_studies':2})
    assert response.status_code == 201, response.text
    dataset = response.json()
    assert dataset['row_count'] == 2
    assert dataset['provenance']['response_pages'] == 2
    assert dataset['provenance']['baseline_provenance'] is False
    raw = json.loads(client.app.state.registry.raw_path(dataset['id']).read_bytes())
    assert [json.loads(page) for page in raw['raw_response_pages']] == pages
    rows = client.get('/api/v1/studies', params={'dataset_id':dataset['id']}).json()['items']
    assert rows[0]['number_of_arms'] == 1
    assert rows[0]['criteria_count'] is None
    assert rows[0]['completion_date_type'] == 'ACTUAL'


@pytest.mark.parametrize('mode', ['unavailable','malformed','empty','repeat-token'])
def test_registry_errors_never_publish_partial_dataset(client, monkeypatch, mode):
    def handle(request):
        if mode == 'unavailable':
            return httpx.Response(503, text='Upstream unavailable')
        if mode == 'malformed':
            return httpx.Response(200, json={'unrelated':'payload'})
        if mode == 'empty':
            return httpx.Response(200, json={'studies':[]})
        return httpx.Response(200, json=registry_test_page('DUPLICATE-TEST', nextPageToken='same'))
    mock_registry_http(monkeypatch, handle)
    result = client.post('/api/v1/datasets/import/clinicaltrials', json={'query':'software fixture','max_studies':3})
    assert result.status_code == 502
    assert {row['id'] for row in client.get('/api/v1/datasets').json()['items']} == {'sample-fixture', 'registry-v5205'}


def test_assistant_uses_responses_with_bounded_context_and_redacts_provider_errors(client, monkeypatch):
    import openai
    real_openai = openai.OpenAI
    config = client.app.state.settings
    config.openai_api_key = 'unit-test-secret-never-a-real-key'
    requests = []
    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={'id':'resp_test','object':'response','created_at':1,'status':'completed','model':config.openai_model,
            'output':[{'id':'msg_test','type':'message','role':'assistant','status':'completed',
                       'content':[{'type':'output_text','text':'Software fixtures cannot support clinical inference.','annotations':[]}]}]})
    monkeypatch.setattr(openai, 'OpenAI', lambda **kwargs: real_openai(http_client=httpx.Client(transport=httpx.MockTransport(handle)), **kwargs))
    response = client.post('/api/v1/assistant', json={'message':'Explain the source','nct_id':'NCT-SAMPLE-001'})
    assert response.status_code == 200
    assert response.json()['reply'] == 'Software fixtures cannot support clinical inference.'
    assert requests[0]['store'] is False
    assert requests[0]['max_output_tokens'] <= 1000
    assert len(requests[0]['input'][0]['content']) < 23000
    assert 'unit-test-secret-never-a-real-key' not in json.dumps(requests)
    def fail(request):
        return httpx.Response(401, json={'error':{'message':'echoed unit-test-secret-never-a-real-key','type':'authentication_error'}})
    monkeypatch.setattr(openai, 'OpenAI', lambda **kwargs: real_openai(http_client=httpx.Client(transport=httpx.MockTransport(fail)), **kwargs))
    failed = client.post('/api/v1/assistant', json={'message':'Explain'})
    assert failed.status_code == 503
    assert config.openai_api_key not in failed.text
    assert config.openai_api_key not in client.get('/api/v1/health').text


def test_built_frontend_serves_without_exposing_backend_files(tmp_path):
    dist = tmp_path/'frontend'
    dist.mkdir()
    (dist/'index.html').write_text('<!doctype html><title>Software Test Workbench</title>')
    config = Settings(storage_dir=str(tmp_path/'store'), frontend_dist=str(dist), database_url='', openai_api_key='', api_bearer_token='', _env_file=None)
    with TestClient(create_app(config)) as client:
        assert 'Software Test Workbench' in client.get('/').text
        assert client.get('/api/v1/health').json()['status'] == 'ok'
        assert client.get('/backend/app/config.py').status_code == 404


def test_training_failure_is_persisted_and_releases_worker(client, monkeypatch):
    from src.clinical_trial_intelligence import research
    dataset = upload(client, software_test_cohort().to_csv(index=False).encode()).json()
    def fail_training(*args, **kwargs):
        raise RuntimeError('test private server details')
    monkeypatch.setattr(research, 'train_experiment', fail_training)
    for _ in range(2):
        response = client.post('/api/v1/experiments', json={'dataset_id':dataset['id']})
        assert response.status_code == 202
        result = client.get('/api/v1/experiments/'+response.json()['id']).json()
        assert result['status'] == 'failed'
        assert 'private server details' not in result['error']


def test_interrupted_experiment_is_failed_on_server_restart(tmp_path):
    config = Settings(storage_dir=str(tmp_path/'store'), database_url='', openai_api_key='', api_bearer_token='', _env_file=None)
    first = create_app(config)
    first.state.registry.save_experiment({'id':'a'*32,'dataset_id':'sample-fixture','dataset_sha256':'test','status':'running','created_at':'2024-01-01','error':None})
    with TestClient(create_app(config)) as restarted:
        result = restarted.get('/api/v1/experiments/'+'a'*32).json()
        assert result['status'] == 'failed'
        assert 'restart' in result['error'].lower()


def test_import_storage_failure_is_service_unavailable(client, monkeypatch):
    mock_registry_http(monkeypatch, lambda request: httpx.Response(200, json=registry_test_page('CT-TEST')))
    def fail(*args, **kwargs):
        raise OSError('private storage path')
    monkeypatch.setattr(client.app.state.registry, 'register_bytes', fail)
    result = client.post('/api/v1/datasets/import/clinicaltrials', json={'query':'software fixture'})
    assert result.status_code == 503
    assert 'private storage path' not in result.text


def test_postgresql_registry_uses_transactional_metadata_storage(tmp_path):
    # Test against the same PostgreSQL backend required by the application.
    from backend.app.services.data_service import DatasetRegistry
    config = Settings(storage_dir=str(tmp_path/'store'), _env_file=None)
    registry = DatasetRegistry(config)
    dataset = registry.register_bytes(b'nct_id,title\nSQL1,SQLAlchemy software fixture\n','cohort.csv')
    registry.save_experiment({'id':'b'*32,'dataset_id':dataset['id'],'status':'queued','created_at':'2024-01-01'})
    registry.save_experiment({'id':'b'*32,'dataset_id':dataset['id'],'status':'failed','created_at':'2024-01-01'})
    registry.engine.dispose()
    reopened = DatasetRegistry(config)
    assert reopened.get_dataset(dataset['id'])['sha256'] == dataset['sha256']
    assert reopened.get_experiment('b'*32)['status'] == 'failed'
    assert reopened.engine.dialect.name == 'postgresql'
    reopened.engine.dispose()


@pytest.mark.parametrize('manifest_change', [{'status': 'failed'}, {'artifact_version': 999}, {}])
def test_overview_does_not_offer_failed_incompatible_or_corrupt_artifacts(client, manifest_change):
    from src.clinical_trial_intelligence.research import ARTIFACT_VERSION
    dataset = upload(client, b'nct_id,title\nA,SOFTWARE TEST ONLY\n').json()
    registry = client.app.state.registry
    experiment = {'id': 'c' * 32, 'dataset_id': dataset['id'], 'dataset_sha256': dataset['sha256'],
                  'status': 'completed', 'created_at': '2024-01-01'}
    registry.save_experiment(experiment)
    directory = registry.artifact_path(experiment['id'])
    directory.mkdir()
    (directory / 'models.joblib').write_bytes(b'corrupt software test artifact')
    manifest = {'run_id': 'software-test-run', 'status': 'completed', 'artifact_version': ARTIFACT_VERSION,
                'source_metadata': {'dataset_id': dataset['id'], 'sha256': dataset['sha256']}, **manifest_change}
    (directory / 'manifest.json').write_text(json.dumps(manifest))
    assert client.get('/api/v1/overview', params={'dataset_id': dataset['id']}).json()['predictions_available'] is False
    result = client.get('/api/v1/studies/A', params={'dataset_id': dataset['id']}).json()['prediction']
    assert result['status'] == 'unavailable'


def test_unusable_latest_artifact_falls_back_to_older_compatible_model(client):
    import shutil
    from src.clinical_trial_intelligence.research import ExperimentConfig, train_experiment
    dataset = upload(client, software_test_cohort().to_csv(index=False).encode()).json()
    registry = client.app.state.registry
    older = {'id': 'd' * 32, 'dataset_id': dataset['id'], 'dataset_sha256': dataset['sha256'],
             'status': 'completed', 'created_at': '2024-01-01'}
    latest = {**older, 'id': 'e' * 32, 'created_at': '2024-02-01'}
    manifest = train_experiment(registry.frame(dataset['id']), registry.artifact_path(older['id']),
                                {'dataset_id': dataset['id'], 'sha256': dataset['sha256'], 'is_fixture': True},
                                config=ExperimentConfig(bootstrap_samples=0))
    registry.save_experiment(older)
    shutil.copytree(registry.artifact_path(older['id']), registry.artifact_path(latest['id']))
    (registry.artifact_path(latest['id']) / 'models.joblib').write_bytes(b'corrupt software test artifact')
    registry.save_experiment(latest)
    result = client.get('/api/v1/studies/SOFTWARE-TEST-059', params={'dataset_id': dataset['id']}).json()['prediction']
    assert result['status'] == 'available'
    assert result['run_id'] == manifest['run_id']
    assert client.get('/api/v1/overview', params={'dataset_id': dataset['id']}).json()['predictions_available'] is True


def test_v3_phase_preflight_training_and_task_isolation(client):
    raw = software_test_cohort()
    raw['phase'] = ['PHASE1', 'PHASE2', 'PHASE3'] * 20
    ds = upload(client, raw.to_csv(index=False).encode()).json()
    check = client.get('/api/v1/readiness', params={'dataset_id':ds['id']}).json()
    assert check['phase']['ready'] is True
    result = client.post('/api/v1/phase-experiments', json={'dataset_id':ds['id']})
    assert result.status_code == 202, result.text
    run = client.get('/api/v1/experiments/'+result.json()['id']).json()
    assert run['status'] == 'completed' and run['task'] == 'phase', run
    assert 'phase_logistic' in run['metrics']
    assert run['manifest']['source_metadata']['sha256'] == ds['sha256']
    prediction = client.post('/api/v1/phase-predictions', json={'dataset_id':ds['id'], 'nct_id':'SOFTWARE-TEST-059'}).json()
    assert prediction['status'] == 'available' and prediction['reported_phase'] == 'PHASE3'
    assert abs(sum(prediction['class_probabilities'].values())-1) < 1e-9
    duration = client.post('/api/v1/predictions', json={'dataset_id':ds['id'], 'nct_id':'SOFTWARE-TEST-059'}).json()
    assert duration['status'] == 'unavailable'
    other = upload(client, raw.to_csv(index=False).encode()).json()
    assert client.post('/api/v1/phase-predictions', json={'dataset_id':other['id'], 'nct_id':'SOFTWARE-TEST-059'}).json()['status'] == 'unavailable'
    exported = client.get(f"/api/v1/experiments/{run['id']}/files/phase_held_out_predictions.csv")
    assert exported.status_code == 200 and 'predicted_phase' in exported.text
    assert client.get(f"/api/v1/experiments/{run['id']}/files/phase_metrics.json").status_code == 200
    assert client.get(f"/api/v1/experiments/{run['id']}/files/phase_models.joblib").status_code == 404


def test_v3_preflight_rejects_small_and_single_class_phase_cohorts(client):
    for df in (software_test_cohort(rows=39), software_test_cohort()):
        ds = upload(client, df.to_csv(index=False).encode()).json()
        assert client.get('/api/v1/readiness', params={'dataset_id':ds['id']}).json()['phase']['ready'] is False
        assert client.post('/api/v1/phase-experiments', json={'dataset_id':ds['id']}).status_code == 422
    assert client.post('/api/v1/phase-experiments', json={'dataset_id':'sample-fixture'}).status_code == 422


def test_v3_starter_load_is_idempotent_and_eligible(client):
    first = client.post('/api/v1/datasets/starter')
    assert first.status_code == 201, first.text
    data = first.json()
    assert data['row_count'] == 800 and not data['is_fixture']
    again = client.post('/api/v1/datasets/starter').json()
    assert data['id'] == again['id'] and data['sha256'] == again['sha256']
    checks = client.get('/api/v1/readiness', params={'dataset_id':data['id']}).json()
    assert checks['duration']['ready'] is True and checks['phase']['ready'] is True
    assert checks['duration']['splits'] == {'train':105,'validation':9,'calibration':11,'test':64}
