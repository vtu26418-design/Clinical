"""Research API contracts against isolated immutable local sources.

Every cohort here is synthetic software-test data, never scientific evidence.
"""
import hashlib
import json
import math
from datetime import datetime, timedelta

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.services.data_service import DatasetRegistry


def make_client(tmp_path, token=''):
    config = Settings(storage_dir=str(tmp_path / 'store'), database_url='', openai_api_key='', api_bearer_token=token, _env_file=None)
    app = FastAPI()
    registry = DatasetRegistry(config)
    app.state.registry = registry
    app.state.settings = config
    from backend.app.v4_routes import attach_v4_routes
    attach_v4_routes(app, registry, config)
    return TestClient(app)


@pytest.fixture
def client(tmp_path):
    with make_client(tmp_path) as value:
        yield value


def register(client, rows=None):
    rows = rows or [
        {'nct_id': 'A', 'title': 'Alpha cancer protocol', 'phase': 'Phase II', 'enrollment': 120, 'number_of_arms': 2,
         'primary_outcomes': 2, 'secondary_outcomes': 4, 'criteria_count': 8, 'text_complexity': 3,
         'brief_summary': 'Cancer alpha treatment repeated alpha', 'eligibility_criteria': 'Adults with cancer'},
        {'nct_id': 'B', 'title': 'Alpha cancer protocol', 'phase': 'PHASE2', 'enrollment': 80,
         'brief_summary': 'Cancer alpha treatment repeated alpha', 'eligibility_criteria': 'Adults with cancer'},
        {'nct_id': 'C', 'title': 'Alpha cancer protocol', 'phase': 'PHASE3', 'enrollment': 200,
         'brief_summary': 'Cancer alpha treatment repeated alpha', 'eligibility_criteria': 'Adults with cancer'},
        {'nct_id': 'D', 'title': 'Unrelated cardiac exercise', 'phase': 'PHASE2', 'enrollment': None,
         'brief_summary': 'Cardiac exercise rehabilitation', 'eligibility_criteria': 'Cardiac participants'},
    ]
    raw = pd.DataFrame(rows).to_csv(index=False).encode()
    return client.app.state.registry.register_bytes(raw, 'software-test.csv')


def query(dataset, nct='A'):
    return {'dataset_id': dataset['id'], 'nct_id': nct}


def scenario_body(dataset, **updates):
    return {'dataset_id': dataset['id'], 'nct_id': 'A', 'overrides': {'enrollment': 240},
            'planning': {'sites': 10, 'monthly_rate_per_site': 2, 'startup_months': 3, 'followup_months': 6},
            'name': 'Software test plan', **updates}


def digest(value):
    content = {key: item for key, item in value.items() if key != 'evidence_sha256'}
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def test_workspace_returns_source_and_honest_availability(client):
    dataset = register(client)
    response = client.get('/api/v1/research/workspace', params=query(dataset))
    assert response.status_code == 200, response.text
    value = response.json()
    assert value['study']['nct_id'] == 'A'
    assert value['duration']['status'] == 'unavailable'
    assert value['phase']['status'] == 'unavailable'
    assert value['risk_availability']['recruitment']['probability'] is None
    assert value['risk_availability']['amendment']['status'] == 'unavailable'
    assert value['provenance']['sha256'] == dataset['sha256']
    assert value['pci']['missing_fields'] == []
    assert value['phase_context']['count'] == 3
    assert value['phase_context']['median_enrollment'] == 100
    assert 'TF-IDF' in value['similar']['method']


@pytest.mark.parametrize('method,path', [
    ('GET', '/workspace'), ('GET', '/similar'), ('GET', '/scenarios'), ('GET', '/evidence'), ('POST', '/scenarios'),
])
def test_all_research_routes_require_bearer(tmp_path, method, path):
    with make_client(tmp_path, token='secret-test-token') as client:
        dataset = register(client)
        kwargs = {'json': scenario_body(dataset)} if method == 'POST' else {'params': query(dataset)}
        for auth in (None, 'Bearer wrong', 'bearer secret-test-token', b'Bearer secre\xc5\xa3-test-token'):
            headers = {'Authorization': auth} if auth else {}
            response = client.request(method, '/api/v1/research' + path, headers=headers, **kwargs)
            assert response.status_code == 401
            assert response.headers['www-authenticate'] == 'Bearer'
        response = client.request(method, '/api/v1/research' + path, headers={'Authorization': 'Bearer secret-test-token'}, **kwargs)
        assert response.status_code == 200, response.text


def test_similar_exact_normalized_phase_excludes_self_and_orders_deterministically(client):
    dataset = register(client)
    response = client.get('/api/v1/research/similar', params={**query(dataset), 'same_phase': True, 'limit': 10})
    assert response.status_code == 200, response.text
    data = response.json()
    assert [entry['study']['nct_id'] for entry in data['items']] == ['B']
    assert data['items'][0]['similarity'] == pytest.approx(1.0)
    assert all(0 <= entry['similarity'] <= 1 for entry in data['items'])
    assert data['scope']['dataset_id'] == dataset['id']
    assert data['scope']['self_excluded'] is True
    all_phases = client.get('/api/v1/research/similar', params={**query(dataset), 'same_phase': False}).json()
    assert [entry['study']['nct_id'] for entry in all_phases['items']][:2] == ['B', 'C']
    assert client.get('/api/v1/research/similar', params={**query(dataset), 'limit': 11}).status_code == 422


def test_similar_unknown_phase_does_not_merge_distinct_labels(client):
    dataset = register(client, [
        {'nct_id': 'A', 'title': 'Identical protocol', 'phase': 'NA'},
        {'nct_id': 'B', 'title': 'Identical protocol', 'phase': 'Not reported'},
        {'nct_id': 'C', 'title': 'Identical protocol', 'phase': 'NA'},
    ])
    value = client.get('/api/v1/research/similar', params=query(dataset)).json()
    assert [item['study']['nct_id'] for item in value['items']] == ['C']


def test_scenario_exact_planning_preserves_source_and_persists_history(client, tmp_path):
    dataset = register(client)
    registry = client.app.state.registry
    before = registry.frame(dataset['id']).copy(deep=True)
    raw = registry.raw_path(dataset['id']).read_bytes()
    canonical = (registry.dataset_path(dataset['id']) / 'canonical.csv').read_bytes()
    response = client.post('/api/v1/research/scenarios', json=scenario_body(dataset))
    assert response.status_code == 200, response.text
    value = response.json()
    assert value['planning']['target_enrollment'] == 240
    assert value['planning']['recruitment_months'] == 12
    assert value['planning']['total_months'] == 21
    assert value['base']['study']['enrollment'] == 120
    assert value['scenario']['study']['enrollment'] == 240
    assert value['changes']['pci'] == pytest.approx(1.2)
    assert value['changes']['duration_days'] is None and value['changes']['probability'] is None
    assert value['scenario']['duration']['hypothetical'] is True
    assert value['evidence_sha256'] == digest(value)
    assert value['provenance']['dataset_id'] == dataset['id']
    pd.testing.assert_frame_equal(before, registry.frame(dataset['id']))
    assert registry.raw_path(dataset['id']).read_bytes() == raw
    assert (registry.dataset_path(dataset['id']) / 'canonical.csv').read_bytes() == canonical
    second = client.post('/api/v1/research/scenarios', json=scenario_body(dataset, name='Second test')).json()
    assert second['id'] != value['id']
    history = client.get('/api/v1/research/scenarios', params=query(dataset)).json()['items']
    assert len(history) == 2 and history[-1] == value
    assert client.get('/api/v1/research/scenarios', params=query(dataset, 'B')).json()['items'] == []
    with make_client(tmp_path) as restarted:
        assert restarted.get('/api/v1/research/scenarios', params=query(dataset)).json()['items'] == history


def test_scenario_source_target_fallback_and_missing_target_refusal(client):
    dataset = register(client)
    response = client.post('/api/v1/research/scenarios', json=scenario_body(dataset, overrides={}))
    assert response.status_code == 200, response.text
    assert response.json()['planning']['target_enrollment'] == 120
    missing = client.post('/api/v1/research/scenarios', json=scenario_body(dataset, nct_id='D', overrides={}))
    assert missing.status_code == 422
    assert 'enrollment' in missing.text.lower()
    supplied = client.post('/api/v1/research/scenarios', json=scenario_body(dataset, nct_id='D', overrides={'enrollment': 40}))
    assert supplied.status_code == 200
    assert supplied.json()['planning']['recruitment_months'] == 2


@pytest.mark.parametrize('overrides', [
    {'status': 'COMPLETED'}, {'completion_date': '2030-01-01'}, {'nct_id': 'B'}, {'title': 'Mutated'},
    {'enrollment': -1}, {'enrollment': 10_000_001}, {'enrollment': 'NaN'}, {'enrollment': None},
    {'enrollment': True}, {'enrollment': '200'}, {'number_of_arms': 1.2}, {'number_of_arms': 1001},
    {'primary_outcomes': 10001}, {'secondary_outcomes': -1}, {'criteria_count': 100001},
    {'text_complexity': 10001}, {'phase': 'invented clinical phase'},
])
def test_scenario_rejects_invalid_or_outcome_overrides(client, overrides):
    dataset = register(client)
    response = client.post('/api/v1/research/scenarios', json=scenario_body(dataset, overrides=overrides))
    assert response.status_code == 422, response.text
    assert client.get('/api/v1/research/scenarios', params=query(dataset)).json()['items'] == []


@pytest.mark.parametrize('field,bad', [
    ('sites', 0), ('sites', -1), ('sites', 1.5), ('sites', True), ('sites', 100001),
    ('monthly_rate_per_site', 0), ('monthly_rate_per_site', -1), ('monthly_rate_per_site', 'Infinity'),
    ('monthly_rate_per_site', 1000001), ('startup_months', -1), ('followup_months', 1201),
])
def test_scenario_rejects_invalid_planning(client, field, bad):
    dataset = register(client)
    body = scenario_body(dataset)
    body['planning'][field] = bad
    assert client.post('/api/v1/research/scenarios', json=body).status_code == 422


@pytest.mark.parametrize('endpoint', ['workspace', 'similar', 'scenarios', 'evidence'])
def test_research_validates_source_and_study_ids(client, endpoint):
    dataset = register(client)
    prefix = '/api/v1/research/' + endpoint
    assert client.get(prefix, params=query(dataset, 'absent')).status_code == 404
    assert client.get(prefix, params={'dataset_id': '../private', 'nct_id': 'A'}).status_code == 422
    assert client.get(prefix, params={'dataset_id': 'missing-source', 'nct_id': 'A'}).status_code == 404
    assert client.get(prefix, params={**query(dataset), 'nct_id': 'x' * 101}).status_code == 422


def test_evidence_digest_contains_snapshot_and_scenario_history(client):
    dataset = register(client)
    saved = client.post('/api/v1/research/scenarios', json=scenario_body(dataset)).json()
    response = client.get('/api/v1/research/evidence', params=query(dataset))
    assert response.status_code == 200, response.text
    packet = response.json()
    assert packet['workspace']['study']['nct_id'] == 'A'
    assert packet['scenarios'] == [saved]
    assert packet['generated_at']
    assert packet['evidence_sha256'] == digest(packet)
    assert packet['scope']['source_sha256'] == dataset['sha256']
    assert packet['scope']['clinical_equivalence'] is False
    packet['workspace']['study']['enrollment'] = 1000
    assert packet['evidence_sha256'] != digest(packet)


def test_cache_tracks_canonical_fingerprint_and_is_bounded(client):
    dataset = register(client)
    first = client.get('/api/v1/research/similar', params=query(dataset)).json()
    registry = client.app.state.registry
    path = registry.dataset_path(dataset['id']) / 'canonical.csv'
    frame = registry.frame(dataset['id'])
    frame.loc[frame.nct_id.eq('B'), 'title'] = 'Totally novel word sequence'
    frame.loc[frame.nct_id.eq('B'), ['brief_summary', 'eligibility_criteria']] = ''
    frame.to_csv(path, index=False)
    second = client.get('/api/v1/research/similar', params=query(dataset)).json()
    assert first['scope']['canonical_sha256'] != second['scope']['canonical_sha256']
    assert first['items'] and second['items'] == []
    for _ in range(5):
        other = register(client)
        assert client.get('/api/v1/research/similar', params=query(other)).status_code == 200
    from backend.app.services.research_workspace import MAX_CACHE_ENTRIES
    assert len(client.app.state.research_workspace._similar_cache) <= MAX_CACHE_ENTRIES


def test_scopes_do_not_mix_identical_raw_source_uploads(client):
    dataset = register(client)
    other = register(client)
    assert dataset['sha256'] == other['sha256']
    client.post('/api/v1/research/scenarios', json=scenario_body(dataset))
    assert client.get('/api/v1/research/scenarios', params=query(other)).json()['items'] == []
    evidence = client.get('/api/v1/research/evidence', params=query(other)).json()
    assert evidence['workspace']['provenance']['dataset_id'] == other['id']
    assert evidence['scenarios'] == []


def test_storage_errors_are_safe(client, monkeypatch):
    dataset = register(client)
    def unavailable(*args, **kwargs):
        raise OSError('private path and private credentials')
    monkeypatch.setattr(client.app.state.registry, 'frame', unavailable)
    response = client.get('/api/v1/research/workspace', params=query(dataset))
    assert response.status_code == 503
    assert 'private' not in response.text


def test_zero_overlap_and_empty_text_are_omitted(client):
    dataset = register(client, [
        {'nct_id': 'A', 'title': 'alpha', 'phase': 'PHASE2'},
        {'nct_id': 'B', 'title': 'beta', 'phase': 'PHASE2'},
        {'nct_id': 'C', 'title': '!!!', 'phase': 'PHASE2'},
    ])
    for nct in ('A', 'C'):
        response = client.get('/api/v1/research/similar', params=query(dataset, nct))
        assert response.status_code == 200
        assert response.json()['items'] == []


def test_planning_independent_known_answer_four_sites(client):
    dataset = register(client)
    body = scenario_body(dataset)
    body['planning'].update(sites=4, monthly_rate_per_site=5)
    result = client.post('/api/v1/research/scenarios', json=body)
    assert result.status_code == 200
    assert result.json()['planning']['recruitment_months'] == 12
    assert result.json()['planning']['total_months'] == 21


@pytest.mark.parametrize('field,nonfinite', [('enrollment', math.nan), ('enrollment', math.inf), ('text_complexity', -math.inf)])
def test_raw_nonfinite_json_is_safe_validation_error(client, field, nonfinite):
    dataset = register(client)
    body = scenario_body(dataset, overrides={field: nonfinite})
    response = client.post('/api/v1/research/scenarios', content=json.dumps(body), headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert client.get('/api/v1/research/scenarios', params=query(dataset)).json()['items'] == []


def test_tf_idf_cosine_independent_known_answer(client):
    # Three documents give all unigrams identical df=2 and each bigram df=1.
    dataset = register(client, [
        {'nct_id': 'A', 'title': 'alpha beta', 'phase': 'PHASE2'},
        {'nct_id': 'B', 'title': 'alpha gamma', 'phase': 'PHASE2'},
        {'nct_id': 'C', 'title': 'beta gamma', 'phase': 'PHASE2'},
    ])
    value = client.get('/api/v1/research/similar', params=query(dataset)).json()
    unigram_idf, bigram_idf = 1 + math.log(4 / 3), 1 + math.log(4 / 2)
    known_cosine = unigram_idf ** 2 / (2 * unigram_idf ** 2 + bigram_idf ** 2)
    assert value['items'][0]['similarity'] == pytest.approx(known_cosine)
    assert value['items'][1]['similarity'] == pytest.approx(known_cosine)


def test_fitted_scenario_queries_changed_features_with_source_provenance(client):
    from src.clinical_trial_intelligence.research import ExperimentConfig, predict_trial, train_experiment
    rows = []
    for index in range(80):
        start = datetime(2000, 1, 1) + timedelta(days=180 * index)
        duration = 30 + 12 * (index % 8)
        rows.append({'nct_id': f'TEST-ONLY-{index:03}', 'title': f'Synthetic software test protocol {index % 8}',
                     'brief_summary': 'Synthetic software test data only', 'phase': 'PHASE2',
                     'study_type': 'INTERVENTIONAL', 'enrollment': 20 + 40 * (index % 8),
                     'number_of_arms': 1 + index % 4, 'primary_outcomes': 1, 'secondary_outcomes': 2,
                     'criteria_count': 4 + index % 8, 'text_complexity': 3, 'status': 'COMPLETED',
                     'completion_date_type': 'ACTUAL', 'start_date': start.date().isoformat(),
                     'completion_date': (start + timedelta(days=duration)).date().isoformat()})
    dataset = register(client, rows)
    registry = client.app.state.registry
    source_before = registry.frame(dataset['id']).copy(deep=True)
    run_id = 'a' * 32
    directory = registry.artifact_path(run_id)
    manifest = train_experiment(source_before, directory,
                                {'dataset_id': dataset['id'], 'sha256': dataset['sha256'], 'is_fixture': True},
                                config=ExperimentConfig(bootstrap_samples=0, enable_advanced_models=False))
    # Select one genuinely fitted branch for an unambiguous service query.
    manifest['recommended_model'] = 'structured'
    (directory / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    registry.save_experiment({'id': run_id, 'dataset_id': dataset['id'], 'dataset_sha256': dataset['sha256'],
                              'task': 'duration', 'status': 'completed', 'created_at': '2024-01-01'})
    nct = 'TEST-ONLY-079'
    response = client.post('/api/v1/research/scenarios', json=scenario_body(dataset, nct_id=nct, overrides={'enrollment': 500_000}))
    assert response.status_code == 200, response.text
    result = response.json()
    prediction = result['scenario']['duration']
    expected = predict_trial(result['scenario']['study'], directory, model_name='structured')
    assert prediction['status'] == 'available'
    assert prediction['duration_days'] == pytest.approx(expected['duration_days'])
    assert prediction['probability'] == pytest.approx(expected['probability'])
    assert prediction['duration_days'] != result['base']['duration']['duration_days']
    assert prediction['source_cohort_membership'] == 'test'
    assert prediction['run_id'] == manifest['run_id']
    assert prediction['probability_semantics'] == 'raw'
    assert prediction['extrapolation']['outside_training_support'] is True
    assert prediction['uncertainty']['hypothetical'] is True
    assert 'Hypothetical' in prediction['uncertainty']['prediction_scope']
    assert 'Held-out' in prediction['source_prediction_scope']
    assert result['changes']['duration_days'] == pytest.approx(prediction['duration_days'] - result['base']['duration']['duration_days'])
    assert result['evidence_sha256'] == digest(result)
    pd.testing.assert_frame_equal(source_before, registry.frame(dataset['id']))
    # Identical raw bytes still define distinct registered source scopes.
    second_dataset = register(client, rows)
    assert second_dataset['sha256'] == dataset['sha256']
    separate = client.get('/api/v1/research/workspace', params=query(second_dataset, nct)).json()
    assert separate['duration']['status'] == 'unavailable'


def test_large_source_target_refuses_planning_without_explicit_bounded_override(client):
    dataset = register(client, [{'nct_id': 'A', 'title': 'Synthetic large input', 'enrollment': 1e200}])
    body = scenario_body(dataset, overrides={})
    assert client.post('/api/v1/research/scenarios', json=body).status_code == 422
    body['overrides'] = {'enrollment': 240}
    response = client.post('/api/v1/research/scenarios', json=body)
    assert response.status_code == 200
    assert response.json()['planning']['recruitment_months'] == 12


def test_saved_scenario_insert_collision_never_overwrites_history(client, monkeypatch):
    from types import SimpleNamespace
    from backend.app.services import research_workspace
    dataset = register(client)
    monkeypatch.setattr(research_workspace.uuid, 'uuid4', lambda: SimpleNamespace(hex='f' * 32))
    first = client.post('/api/v1/research/scenarios', json=scenario_body(dataset))
    assert first.status_code == 200
    second = client.post('/api/v1/research/scenarios', json=scenario_body(dataset, name='Would overwrite'))
    assert second.status_code == 503
    history = client.get('/api/v1/research/scenarios', params=query(dataset)).json()['items']
    assert history == [first.json()]


def test_oversized_evidence_and_scenarios_return_safe_bounded_error(client, monkeypatch):
    from backend.app.services import research_workspace
    dataset = register(client)
    monkeypatch.setattr(research_workspace, 'MAX_EVIDENCE_BYTES', 512)
    assert client.post('/api/v1/research/scenarios', json=scenario_body(dataset)).status_code == 413
    assert client.get('/api/v1/research/scenarios', params=query(dataset)).json()['items'] == []
    assert client.get('/api/v1/research/evidence', params=query(dataset)).status_code == 413


def test_combined_phase_aliases_preserve_exact_combination():
    from backend.app.schemas_v4 import ProtocolOverrides
    from backend.app.services.research_workspace import normalized_phase
    for text in ['PHASE1|PHASE2', 'PHASE1/PHASE2', 'Phase I|Phase II', 'Phase I/Phase II']:
        assert ProtocolOverrides(phase=text).phase == 'PHASE1/PHASE2'
        assert normalized_phase(text) == 'PHASE1/PHASE2'
    assert normalized_phase('PHASE1|PHASE2') != normalized_phase('PHASE1')
    assert normalized_phase('PHASE2|PHASE3') == 'PHASE2/PHASE3'
