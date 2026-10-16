"""Evidence integrity contracts; synthetic records exercise software only."""
import json
import os
import uuid
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.services.data_service import DatasetRegistry, SAMPLE_ID
from backend.app.services.shap_adapter import explain_prediction, get_demo_shap_values
from src.clinical_trial_intelligence.research import predict_trial


@pytest.fixture
def client(tmp_path):
    schema = 'cti_evidence_' + uuid.uuid4().hex[:20]
    settings = Settings(storage_dir=str(tmp_path), database_url=os.environ['TEST_DATABASE_URL'],
                        database_schema=schema, _env_file=None)
    registry = DatasetRegistry(settings)
    app = FastAPI()
    app.state.registry = registry
    from backend.app.v4_routes import attach_v4_routes
    from backend.app.v521_routes import attach_v521_routes
    attach_v4_routes(app, registry, settings)
    attach_v521_routes(app, registry, settings)
    with TestClient(app) as value:
        yield value
    registry.engine.dispose()
    from sqlalchemy import create_engine, text
    engine = create_engine(settings.database_url.replace('postgresql://', 'postgresql+psycopg://'))
    with engine.begin() as connection:
        connection.execute(text('DROP SCHEMA ' + schema + ' CASCADE'))
    engine.dispose()


def register(client, rows):
    return client.app.state.registry.register_bytes(pd.DataFrame(rows).to_csv(index=False).encode(), 'software-test.csv')


def test_fixture_explanation_never_fabricates_prediction_or_attribution(client):
    study = client.app.state.registry.frame(SAMPLE_ID).iloc[0]['nct_id']
    response = client.post('/api/v1/explain', json={'dataset_id': SAMPLE_ID, 'nct_id': study})
    assert response.status_code == 200, response.text
    value = response.json()
    assert value['status'] == 'unavailable'
    assert value['predicted_value'] is None
    assert value['shap_values'] is None
    assert value['features'] == []
    assert value['is_demo'] is False


def test_default_starter_explain_does_not_treat_dataset_id_as_experiment(client):
    registry = client.app.state.registry
    dataset = registry.register_bytes((PROJECT_ROOT / 'data/starter/trials.csv').read_bytes(), 'starter.csv',
                                      dataset_id='clinicaltrials-starter-v3')
    study = registry.frame(dataset['id']).iloc[0]['nct_id']
    response = client.post('/api/v1/explain', json={'dataset_id': dataset['id'], 'nct_id': study})
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'unavailable'


def test_constant_saved_baseline_has_zero_effects_and_actual_prediction():
    prediction = predict_trial({'enrollment': 100, 'phase': 'PHASE2'}, PROJECT_ROOT / 'examples/starter-duration-v5', 'median_baseline')
    assert prediction['status'] == 'available'
    explanation = explain_prediction(prediction, {'enrollment': 100, 'phase': 'PHASE2'})
    assert explanation['method'] == 'constant training baseline'
    assert explanation['scope'] == 'constant'
    assert explanation['base_value'] == prediction['duration_days']
    assert explanation['sum_all_contributions'] == 0
    assert all(feature['contribution'] == 0 for feature in explanation['features'])
    assert explanation['shap_values'] is None


def test_removed_demo_adapter_returns_unavailable():
    value = get_demo_shap_values({'enrollment': 400}, predicted_value=123)
    assert value['status'] == 'unavailable'
    assert value['predicted_value'] is None
    assert value['features'] == []


def test_whatif_requires_baseline_and_planning(client):
    response = client.post('/api/v1/whatif', json={'dataset_id': SAMPLE_ID, 'enrollment': 200})
    assert response.status_code == 422


def test_whatif_preserves_source_fields_and_scenario_provenance(client):
    dataset = register(client, [{'nct_id': 'A', 'title': 'Original title', 'enrollment': 100, 'phase': 'PHASE2',
                                'brief_summary': 'Source narrative unchanged', 'criteria_count': 20}])
    request = {'dataset_id': dataset['id'], 'nct_id': 'A', 'overrides': {'enrollment': 200},
               'planning': {'sites': 4, 'monthly_rate_per_site': 2, 'startup_months': 3, 'followup_months': 6}}
    response = client.post('/api/v1/whatif', json=request)
    assert response.status_code == 200, response.text
    value = response.json()
    assert value['scenario']['study'] == {**value['base']['study'], 'enrollment': 200}
    assert value['scenario']['duration']['status'] == 'unavailable'
    assert value['scenario']['duration']['duration_days'] is None
    assert value['changes']['duration_days'] is None
    assert value['planning']['recruitment_months'] == 25
    assert value['provenance']['sha256'] == dataset['sha256']
    assert 'evidence_sha256' in value
    assert client.app.state.registry.frame(dataset['id']).iloc[0].enrollment == 100
    missing = client.post('/api/v1/whatif', json={**request, 'nct_id': 'MISSING'})
    assert missing.status_code == 404
    unsupported = client.post('/api/v1/whatif', json={**request, 'overrides': {'number_of_sites': 10}})
    assert unsupported.status_code == 422


def test_graphs_aggregate_full_cohort_and_zero_enrollment(client):
    rows = [{'nct_id': f'T{i}', 'title': f'Trial {i}', 'phase': 'PHASE2', 'status': 'COMPLETED',
             'enrollment': i, 'start_date': '2020-01-01', 'completion_date': '2020-04-10',
             'completion_date_type': 'ACTUAL'} for i in range(125)]
    dataset = register(client, rows)
    response = client.post('/api/v1/overview/graphs', json={'dataset_id': dataset['id'],
                           'graphs': ['phase_distribution', 'pci_scatter', 'enrollment_histogram', 'duration_box', 'timeline_gantt']})
    assert response.status_code == 200, response.text
    value = response.json()
    assert value['row_count'] == 125
    assert value['source_sha256'] == dataset['sha256']
    graphs = value['computed_data']
    assert len(graphs['pci_scatter']['points']) == 125
    assert len(graphs['timeline_gantt']['trials']) == 125
    assert sum(graphs['enrollment_histogram']['values']) == 125
    assert graphs['duration_box']['groups'][0]['values'] == [100] * 125
    assert graphs['duration_box']['reporting_rows'] == 125


def test_missing_and_partial_dates_do_not_become_observed_durations(client):
    dataset = register(client, [
        {'nct_id': 'A', 'title': 'Partial dates', 'phase': 'PHASE2', 'enrollment': 5,
         'start_date': '2020-01', 'completion_date': '2021', 'completion_date_type': 'ACTUAL'},
        {'nct_id': 'B', 'title': 'Estimated completion', 'phase': 'PHASE2', 'start_date': '2020-01-01',
         'completion_date': '2021-01-01', 'completion_date_type': 'ESTIMATED'},
        {'nct_id': 'C', 'title': 'Unknown dates', 'phase': 'PHASE3'},
    ])
    graphs = client.post('/api/v1/overview/graphs', json={'dataset_id': dataset['id'],
                          'graphs': ['duration_box', 'timeline_gantt', 'missingness', 'start_year_activity']}).json()['computed_data']
    assert graphs['duration_box']['status'] == 'unavailable'
    assert graphs['duration_box']['groups'] == []
    assert graphs['timeline_gantt']['trials'][2]['start_date'] is None
    assert all(row['observed_duration_days'] is None for row in graphs['timeline_gantt']['trials'])
    assert graphs['start_year_activity']['labels'] == ['2020']
    assert graphs['start_year_activity']['values'] == [2]
    missing = {row['field']: row for row in graphs['missingness']['fields']}
    assert missing['enrollment']['missing_rows'] == 2
    assert missing['start_date']['missing_rows'] == 1


def test_graph_filtering_and_unknown_graph_validation(client):
    dataset = register(client, [{'nct_id': 'A', 'title': 'Alpha', 'phase': 'PHASE2', 'status': 'COMPLETED'},
                                {'nct_id': 'B', 'title': 'Beta', 'phase': 'PHASE3', 'status': 'RECRUITING'}])
    body = {'dataset_id': dataset['id'], 'graphs': ['phase_distribution'], 'phase': 'Phase II'}
    value = client.post('/api/v1/overview/graphs', json=body).json()
    assert value['source_rows'] == 2
    assert value['row_count'] == 1
    assert value['computed_data']['phase_distribution']['values'] == [1]
    assert client.post('/api/v1/overview/graphs', json={**body, 'graphs': ['invented_risk']}).status_code == 422


def test_missing_recruitment_stages_stay_unknown_and_target_is_separate(client):
    dataset = register(client, [{'nct_id': 'A', 'title': 'Planned study', 'enrollment': 50, 'enrollment_type': 'ESTIMATED'},
                                {'nct_id': 'B', 'title': 'Actual study', 'enrollment': 40, 'enrollment_type': 'ACTUAL'}])
    value = client.get('/api/v1/recruitment/' + dataset['id']).json()
    stages = {row['stage']: row for row in value['stages']}
    assert stages['Screening']['count'] is None
    assert stages['Eligibility']['count'] is None
    assert stages['Completion']['count'] is None
    assert stages['Enrollment']['count'] == 40
    assert value['target_enrollment'] == 50
    assert value['average_retention_rate'] is None


def test_study_visualization_returns_source_workspace_and_unknown_stages(client):
    dataset = register(client, [{'nct_id': 'A', 'title': 'Source study', 'enrollment': 30, 'start_date': '2020-03'}])
    response = client.get('/api/v1/visualizations/study', params={'dataset_id': dataset['id'], 'nct_id': 'A'})
    assert response.status_code == 200, response.text
    value = response.json()
    assert value['workspace']['study']['title'] == 'Source study'
    assert value['timeline']['dates'][0]['value'] == '2020-03'
    assert value['timeline']['dates'][0]['precision'] == 'month'
    assert value['timeline']['observed_duration_days'] is None
    assert value['recruitment']['sites'] is None
    assert value['fusion']['status'] == 'unavailable'


def test_pipeline_status_uses_lifecycle_without_invented_percentages(client):
    registry = client.app.state.registry
    registry.save_experiment({'id': 'job1', 'dataset_id': SAMPLE_ID, 'status': 'running', 'task': 'duration',
                              'created_at': '2026-10-13T00:00:00Z', 'started_at': '2026-10-13T00:01:00Z'})
    value = client.get('/api/v1/pipeline-status').json()
    assert value['status'] == 'running'
    assert value['overall_progress'] is None
    assert value['experiment']['id'] == 'job1'
    assert value['current_step'] == 'Training experiment'


def test_old_feedback_route_cannot_write_client_named_files(client):
    response = client.post('/api/v1/assistant/feedback', json={'dataset_id': SAMPLE_ID,
                           'message_id': '../../foreign/file', 'rating': 5})
    assert response.status_code == 410
    assert not (client.app.state.registry.root / 'feedback').exists()


def test_release_health_reports_version_and_postgresql(client, monkeypatch):
    from backend.app import config
    monkeypatch.setattr(config, 'settings', client.app.state.registry.config)
    from backend.app.main import create_research_app
    app = create_research_app(client.app.state.registry.config)
    with TestClient(app) as api:
        value = api.get('/api/v1/health').json()
    assert value['version'] == '5.2.0.4'
    assert value['database'] == 'postgresql'


@pytest.mark.parametrize('model_name,method,scope', [
    ('text', 'linear feature contributions', 'local'),
    ('structured_random_forest', 'global impurity feature importance', 'global'),
    ('multimodal_late_fusion', 'weighted late fusion', 'model'),
    ('structured_hist_gradient_boosting', 'histogram gradient boosting; local attribution unavailable', 'model'),
])
def test_real_saved_explanation_retains_its_method_and_semantics(model_name, method, scope):
    row = {'enrollment': 100, 'phase': 'PHASE2', 'title': 'Cancer treatment protocol',
           'brief_summary': 'Adults with cancer', 'number_of_arms': 2}
    prediction = predict_trial(row, PROJECT_ROOT / 'examples/starter-duration-v5', model_name)
    assert prediction['status'] == 'available'
    actual = prediction['duration_explanation']
    value = explain_prediction(prediction, row)
    assert value['method'] == method
    assert value['scope'] == scope
    assert value['features'] == actual['features']
    assert value['components'] == actual.get('components', [])
    assert value['predicted_value'] == prediction['duration_days']
    assert value['shap_values'] is None
    if method == 'weighted late fusion':
        assert sum(item['weight'] * item['prediction'] for item in value['components']) == pytest.approx(prediction['duration_days'])


def test_experiment_opt_in_reaches_actual_training_configuration(client, monkeypatch):
    from backend.app import config
    from src.clinical_trial_intelligence import research
    monkeypatch.setattr(config, 'settings', client.app.state.registry.config)
    from backend.app.main import create_research_app
    app = create_research_app(client.app.state.registry.config)
    rows = [{'nct_id': f'CB{i}', 'title': 'Software test protocol', 'phase': 'PHASE2', 'status': 'COMPLETED',
             'enrollment': 100 + i, 'start_date': (date(2010, 1, 1) + timedelta(days=120 * i)).isoformat(),
             'completion_date': (date(2010, 1, 1) + timedelta(days=120 * i + 30 + i % 20)).isoformat(),
             'completion_date_type': 'ACTUAL'} for i in range(60)]
    dataset = app.state.registry.register_bytes(pd.DataFrame(rows).to_csv(index=False).encode(), 'software-test.csv')
    observed = []

    def check_configuration(frame, output, source_metadata, config=None):
        observed.append(config)
        raise ValueError('Software test stops before fitting; genuine fitting is covered by model tests.')

    monkeypatch.setattr(research, 'train_experiment', check_configuration)
    with TestClient(app) as api:
        response = api.post('/api/v1/experiments', json={'dataset_id': dataset['id'], 'enable_catboost': True})
        assert response.status_code == 202, response.text
        record = api.get('/api/v1/experiments/' + response.json()['id']).json()
    assert record['enable_catboost'] is True
    assert len(observed) == 1
    assert observed[0].enable_catboost is True
    assert observed[0].enable_advanced_models is True


def test_native_tree_shap_adapter_preserves_actual_fitted_values():
    from src.clinical_trial_intelligence.models.catboost_compat import CTICatBoostRegressor as CatBoostRegressor
    from sklearn.pipeline import Pipeline
    from src.clinical_trial_intelligence.research import ExperimentConfig, _features, _preprocessor, _model_explanation
    rows = pd.DataFrame([{'enrollment': 10 + i, 'phase': 'PHASE2', 'number_of_arms': 1 + i % 2} for i in range(20)])
    features = _features(rows)
    model = Pipeline([('preprocess', _preprocessor('structured', ExperimentConfig(), dense=True)),
                      ('model', CatBoostRegressor(iterations=5, depth=2, thread_count=1, verbose=False, allow_writing_files=False))])
    model.fit(features, [50 + i for i in range(20)])
    predicted = float(model.predict(features.iloc[[0]])[0])
    genuine = _model_explanation(model, features.iloc[[0]], 'days (before nonnegative clipping)')
    explanation = explain_prediction({'status': 'available', 'duration_days': predicted, 'duration_explanation': genuine}, rows.iloc[0].to_dict())
    assert explanation['status'] == 'available'
    assert explanation['method'] == 'TreeSHAP'
    assert explanation['shap_values'] == [item['contribution'] for item in genuine['features']]
    assert explanation['base_value'] + sum(explanation['shap_values']) == pytest.approx(predicted)


def test_model_comparison_preserves_saved_metrics_and_actual_test_denominators(client):
    registry = client.app.state.registry
    manifest = json.loads((PROJECT_ROOT / 'examples/starter-duration-v5/manifest.json').read_text())
    registry.save_experiment({'id': 'saved-evidence', 'dataset_id': SAMPLE_ID, 'status': 'completed',
                              'task': 'duration', 'manifest': manifest, 'created_at': manifest['created_at']})
    response = client.post('/api/v1/overview/graphs', json={'dataset_id': SAMPLE_ID, 'graphs': ['model_comparison']})
    assert response.status_code == 200, response.text
    graph = response.json()['computed_data']['model_comparison']
    assert len(graph['models']) == len(manifest['models'])
    assert graph['denominator_unit'] == 'held-out predictions'
    assert graph['reporting_rows'] == sum(item['metrics']['test']['n'] for item in manifest['models'].values())
    assert graph['reporting_rows'] != registry.get_dataset(SAMPLE_ID)['row_count']
    for item in graph['models']:
        assert item['metrics'] == manifest['models'][item['model_name']]['metrics']['test']


def test_recruitment_supported_source_counts_are_not_inferred(client):
    dataset = register(client, [{'nct_id': 'A', 'title': 'Source counts', 'screened_count': 50,
                                'eligible_count': 30, 'enrolled_count': 25, 'completed_count': 20,
                                'number_of_sites': 3}])
    value = client.get('/api/v1/recruitment/' + dataset['id']).json()
    assert [stage['count'] for stage in value['stages']] == [50, 30, 25, None, 20]
    assert value['sites'] == 3
    assert all(stage['availability'] == 'available' for stage in value['stages'] if stage['stage'] != 'Follow-up')
    assert value['stages'][3]['availability'] == 'unavailable'
