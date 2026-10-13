"""Model choices expose only actual approved branches, never imaginary models."""
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.platform import create_app


def test_model_branch_catalog_and_scenario_use_actual_selected_branch(tmp_path):
    app = create_app(Settings(storage_dir=str(tmp_path), auth_mode='local', _env_file=None))
    with TestClient(app) as client:
        response = client.get('/api/v1/model-branches')
        assert response.status_code == 200
        names = {item['id'] for item in response.json()['items']}
        assert {'median_baseline','structured','text','multimodal_late_fusion'} <= names
        assert 'structured_catboost' not in names  # Only present after candidate approval.
        graph = client.post('/api/v1/overview/graphs', json={'dataset_id':'sample-fixture','graphs':['model_comparison']})
        assert graph.status_code == 200
        model_evidence = graph.json()['computed_data']['model_comparison']
        assert model_evidence['status'] == 'available'
        assert any(item['model_name']=='median_baseline' for item in model_evidence['models'])
        assert model_evidence['denominator_unit'] == 'held-out predictions'
        assert model_evidence['denominator'] > 5
        starter = client.post('/api/v1/datasets/starter').json()
        study = client.get('/api/v1/studies', params={'dataset_id':starter['id'],'limit':1}).json()['items'][0]
        view = client.get('/api/v1/visualizations/study', params={'dataset_id':starter['id'],'nct_id':study['nct_id'],'model_name':'multimodal'})
        assert view.status_code == 200
        assert view.json()['workspace']['duration']['model_name'] == 'multimodal'
        assert {branch['id'] for branch in view.json()['fusion']['branches']} == {'structured','text'}
        result = client.post('/api/v1/research/scenarios', json={
            'dataset_id':starter['id'],'nct_id':study['nct_id'],'model_name':'structured',
            'overrides':{'enrollment':123.0},'planning':{'sites':5,'monthly_rate_per_site':2.0,'startup_months':1.0,'followup_months':3.0}})
        assert result.status_code == 200
        packet = result.json()
        assert packet['base']['duration']['model_name'] == 'structured'
        assert packet['scenario']['duration']['model_name'] == 'structured'
        assert packet['model_name'] == 'structured'
        assert packet['scenario']['study']['title'] == study['title']
        assert packet['scenario']['duration']['hypothetical'] is True


def test_visualization_provenance_includes_selected_model(tmp_path):
    app = create_app(Settings(storage_dir=str(tmp_path), auth_mode='local', _env_file=None))
    with TestClient(app) as client:
        dataset=client.post('/api/v1/datasets/starter').json()
        study=client.get('/api/v1/studies',params={'dataset_id':dataset['id'],'limit':1}).json()['items'][0]
        response=client.get('/api/v1/visualizations/study',params={'dataset_id':dataset['id'],'nct_id':study['nct_id'],'model_name':'structured'})
        assert response.status_code==200
        packet=response.json()
        duration=packet['workspace']['duration']
        assert packet['provenance']['model_name']=='structured'
        for key in ('model_name','run_id','artifact_sha256','manifest_sha256'):
            assert packet['provenance'][key]==duration.get(key)
